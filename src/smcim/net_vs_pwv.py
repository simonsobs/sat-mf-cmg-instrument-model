"""Telescope NET as a function of PWV: the instrument model, and the
model overlaid on the measured PWV-binned NET.

``compute_model`` is the only expensive part (it runs jbolo per wafer,
per bounding sim, per PWV point); the CLI caches its result to a .npy so
re-runs can just reload it. jbolo is imported lazily inside
``compute_model`` so the cached path works without it.

PWV dependence comes entirely from jbolo's atmosphere table lookup in
``run_optics``; PWV/elevation are set on the sim through ``run_wafer``'s
``additional_functions`` hook (the per-wafer configs no longer carry a
measured P_opt-vs-PWV fit).
"""
import os

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

from sotodlib import core

from .config import resolve, save_key, data_dir, plot_dir
from .conventions import (
    bands, chmap, colors, titles, telescope_order, wafer_order, formats,
)
from .plotting import PlotWriter


def _section(cfg):
    return cfg.get("net_vs_pwv", {})


def _plot_cfg(cfg):
    return _section(cfg).get("plot", {})


def _run_tag(cfg):
    """The obs_aman run tag -- used for both the measured telescope NET and
    the measured per-wafer yield (they come from the same files)."""
    return _section(cfg)["run_tag"]


def _writer(cfg):
    return PlotWriter(
        plot_dir=plot_dir(cfg),
        save_key=save_key(cfg),
        save_type=cfg["paths"].get("save_type", "pdf"),
    )


def _pwv_grid(cfg):
    g = _section(cfg)["pwv_grid"]
    return (
        g["elevation_deg"],
        np.linspace(g["pwv_min_mm"], g["pwv_max_mm"], g["n_pwv"]),
    )


def model_cache_path(cfg):
    """Path to the cached model .npy. An explicit ``net_vs_pwv.model_cache``
    wins (point ``--use-cached`` at an older run with it); otherwise it is
    ``{data_dir}/net_vs_pwv_{save_key}.npy``."""
    explicit = _section(cfg).get("model_cache")
    if explicit:
        return resolve(cfg, explicit)
    return os.path.join(data_dir(cfg), f"net_vs_pwv_{save_key(cfg)}.npy")


def load_cached_model(path):
    """Load the model dict saved by :func:`compute_model`."""
    return np.load(path, allow_pickle=True).item()


def compute_model(cfg):
    """Run the per-wafer NET(pwv) models and combine them per telescope.

    Returns a dict with ``pwv_vals_mm``, ``elevation_deg``,
    ``per_wafer_net_C[tel][kind][wafer][band]``,
    ``telescope_net[tel][kind][band]`` and ``yield_curves``.
    """
    import yaml
    from jbolo.utils import load_sim
    from . import run_models

    elevation_deg, pwv_vals_mm = _pwv_grid(cfg)

    sim_list = run_models.sim_list()
    telescope_configs = run_models.telescope_configs()

    def run_wafer_at_pwv(sim_file, configs, wafer, pwv_um, yield_overrides=None):
        """``run_models.run_wafer`` with PWV/elevation (and any per-channel
        yield overrides) set via the ``additional_functions`` hook. jbolo's
        run_bolos prefers a per-channel ``yield`` over the wafer-level one,
        so an override swaps the static manufacturing yield for the
        measured, PWV-dependent one on a per-band basis."""
        def _set_atmosphere(sim):
            sim['sources']['atmosphere']['pwv'] = pwv_um
            sim['sources']['atmosphere']['elevation'] = elevation_deg
            if yield_overrides:
                for ch, y in yield_overrides.items():
                    sim['channels'][ch]['yield'] = y

        return run_models.run_wafer(
            sim_file, configs, wafer, additional_functions=[_set_atmosphere],
        )

    def load_measured_yield_data():
        """Each telescope's obs_aman.wafer_yield_binned (raw ndets vs PWV
        bin, per wafer/band), saved by telescope_nets_analysis.py."""
        base_dir = data_dir(cfg)
        tag = _run_tag(cfg)

        measured = {}
        for tel in telescope_configs:
            path = os.path.join(base_dir, f"obs_aman_{tel}_{tag}.h5")
            aman = core.AxisManager.load(path)
            wy = aman.wafer_yield_binned
            measured[tel] = {
                'pwv_bin_centers': np.asarray(wy.pwv),
                'wafers': list(wy.wafers.vals),
                'bands': list(wy.bands.vals),
                'ndets_binned': np.asarray(wy.ndets_binned),
            }
        return measured

    def measured_yield_curve(measured, tel, wafer, band, num_det_per_wafer):
        """Interpolate a wafer/band's measured ndets(pwv)/num_det_per_wafer
        onto pwv_vals_mm. An all-NaN curve where there is too little
        measured data (fewer than 2 valid PWV bins, or the wafer/band is
        absent) -- that wafer/band then contributes NaN to the telescope
        NET rather than being backfilled with the in-lab yield."""
        nan_curve = np.full(len(pwv_vals_mm), np.nan)

        entry = measured.get(tel)
        if entry is None or wafer not in entry['wafers'] or band not in entry['bands']:
            return nan_curve

        w_idx = entry['wafers'].index(wafer)
        b_idx = entry['bands'].index(band)
        ndets = entry['ndets_binned'][w_idx, b_idx, :]
        bin_pwv = entry['pwv_bin_centers']

        valid = ~np.isnan(ndets)
        if valid.sum() < 2:
            return nan_curve

        return np.interp(
            pwv_vals_mm, bin_pwv[valid], ndets[valid] / num_det_per_wafer,
        )

    def compute_per_wafer_net_vs_pwv():
        measured = load_measured_yield_data()

        per_wafer_net = {}
        yield_curves = {}
        for tel in telescope_configs:
            configs = yaml.safe_load(open(telescope_configs[tel], 'r'))
            per_wafer_net[tel] = {}
            yield_curves[tel] = {}

            for kind, sim_file in sim_list.items():
                per_wafer_net[tel][kind] = {}

                num_det_per_wafer = {
                    band: load_sim(sim_file)['channels'][chmap[band]]['num_det_per_wafer']
                    for band in bands
                }

                for wafer in wafer_order[tel]:
                    if wafer not in yield_curves[tel]:
                        manufacturing_yield = configs['wafers'][wafer]['yield']
                        yield_curves[tel][wafer] = {
                            band: {
                                'manufacturing': manufacturing_yield,
                                'measured': measured_yield_curve(
                                    measured, tel, wafer, band,
                                    num_det_per_wafer[band],
                                ),
                            }
                            for band in bands
                        }

                    per_band = {b: np.zeros(len(pwv_vals_mm)) for b in bands}
                    for i, pwv_mm in enumerate(pwv_vals_mm):
                        pwv_um = int(round(1000 * pwv_mm))

                        yield_overrides = {
                            chmap[band]: yield_curves[tel][wafer][band]['measured'][i]
                            for band in bands
                        }

                        sim = run_wafer_at_pwv(
                            sim_file, configs, wafer, pwv_um,
                            yield_overrides=yield_overrides,
                        )
                        for band in bands:
                            per_band[band][i] = (
                                sim['outputs'][chmap[band]]['NET_C_wafer']
                            )
                    per_wafer_net[tel][kind][wafer] = per_band
        return per_wafer_net, yield_curves

    def combine_wafers_to_telescope(per_wafer_net):
        """Inverse-variance combination of independent per-wafer
        NET_C(pwv) into a per-telescope NET(pwv):
            1 / NET_tel^2 = sum_wafers ( 1 / NET_wafer^2 )
        """
        tel_net = {}
        for tel in per_wafer_net:
            tel_net[tel] = {}
            for kind in per_wafer_net[tel]:
                tel_net[tel][kind] = {}
                for band in bands:
                    inv_var_sum = sum(
                        1.0 / per_wafer_net[tel][kind][wafer][band] ** 2
                        for wafer in per_wafer_net[tel][kind]
                    )
                    tel_net[tel][kind][band] = 1.0 / np.sqrt(inv_var_sum)
        return tel_net

    per_wafer_net, yield_curves = compute_per_wafer_net_vs_pwv()
    tel_net = combine_wafers_to_telescope(per_wafer_net)
    return {
        'pwv_vals_mm': pwv_vals_mm,
        'elevation_deg': elevation_deg,
        'per_wafer_net_C': per_wafer_net,
        'telescope_net': tel_net,
        'yield_curves': yield_curves,
    }


def load_measured(cfg):
    """Each telescope's obs_aman (pwv_binned nested inside), saved by
    telescope_nets_analysis.py."""
    base_dir = data_dir(cfg)
    tag = _run_tag(cfg)
    skip = _plot_cfg(cfg).get("skip_datasets", [])

    obs_amans = {}
    for tel in telescope_order:
        if tel in skip:
            continue
        path = os.path.join(base_dir, f"obs_aman_{tel}_{tag}.h5")
        obs_amans[tel] = core.AxisManager.load(path)
    return obs_amans


def make_telescope_net_plot(model, cfg, writer=None, save_tag="net_vs_pwv_telescope"):
    writer = writer or _writer(cfg)
    skip = _plot_cfg(cfg).get("skip_datasets", [])

    pwv = model['pwv_vals_mm']
    tel_net = model['telescope_net']
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.5), dpi=150, sharey=True)
    for ax, band in zip(axes, bands):
        for tel in telescope_order:
            if tel in skip:
                continue
            lower = tel_net[tel]['lower'][band] * 1e6
            upper = tel_net[tel]['upper'][band] * 1e6
            lo, hi = np.minimum(lower, upper), np.maximum(lower, upper)
            ax.fill_between(pwv, lo, hi, color=colors[tel], alpha=0.3, lw=0)
            ax.plot(
                pwv, 0.5 * (lower + upper),
                color=colors[tel], lw=1.5, label=titles[tel],
            )
        ax.set_xlabel("PWV (mm)", size='large')
        ax.set_title(band)
        ax.set_xlim(pwv.min(), pwv.max())
        ax.set_ylim(0, None)
    axes[0].set_ylabel(
        r"Telescope NET ($\mathrm{\mu K}\sqrt{\mathrm{s}}$)", size='large'
    )
    axes[0].legend(loc='best', fontsize='small')
    fig.suptitle(
        f"Telescope NET vs PWV (elevation={model['elevation_deg']}$^\\circ$)"
    )

    return writer.save(save_tag)


def make_model_vs_measured_plot(model, obs_amans, cfg, writer=None,
                                save_tag="net_vs_pwv_model_vs_measured"):
    writer = writer or _writer(cfg)
    pc = _plot_cfg(cfg)
    skip = pc.get("skip_datasets", [])

    pwv_vals_mm = model['pwv_vals_mm']
    # left -> right: Pre-Retrofit, SAT1, SAT3 (deliberately not
    # telescope_order, which is used elsewhere for the opposite ordering).
    column_order = ['satp1_iso', 'satp1_retrofit', 'satp3_iso']
    tel_cols = [tel for tel in column_order if tel not in skip]

    fig, axes = plt.subplots(
        len(bands), len(tel_cols), figsize=(6.5, 4.2), dpi=150, sharex='col',
    )

    for r, band in enumerate(bands):
        for c, tel in enumerate(tel_cols):
            ax = axes[r, c]

            # --- model: jbolo lower-upper band ---
            lower = model['telescope_net'][tel]['lower'][band] * 1e6
            upper = model['telescope_net'][tel]['upper'][band] * 1e6
            lo, hi = np.minimum(lower, upper), np.maximum(lower, upper)
            ax.fill_between(
                pwv_vals_mm, lo, hi, color=colors[tel], alpha=0.25, lw=0,
                zorder=1,
            )
            ax.plot(
                pwv_vals_mm, 0.5 * (lower + upper), color=colors[tel],
                lw=1.0, ls='--', zorder=2,
            )

            # --- measured: PWV-binned telescope NET ---
            obs_aman = obs_amans[tel]
            b = list(obs_aman.bands.vals).index(band)
            pmsk = obs_aman.pwv_binned.pwv < pc["pwv_max"]

            net = obs_aman.pwv_binned.neq_cmb_binned[b][pmsk] / np.sqrt(2)
            corr_err = obs_aman.pwv_binned.neq_cmb_binned_corr_err[b][pmsk] / np.sqrt(2)
            stat_err = obs_aman.pwv_binned.neq_cmb_binned_stat_err[b][pmsk] / np.sqrt(2)
            pwv_bins = obs_aman.pwv_binned.pwv[pmsk]
            xerr = np.mean(np.diff(obs_aman.pwv_binned.pwv)) / 2 * np.ones_like(pwv_bins)

            ax.fill_between(
                pwv_bins, net - corr_err, net + corr_err,
                color=colors[tel], alpha=0.7, zorder=3,
            )
            ax.errorbar(
                pwv_bins, net, yerr=stat_err, xerr=xerr,
                fmt=formats[tel], ms=4, lw=1.5, markeredgecolor='k',
                ecolor='k', color=colors[tel], zorder=4,
            )

            ax.set_xlim(*pc["xlim"])
            ax.set_ylim(0, pc["ylim"][band])
            if r == 0:
                ax.set_title(titles[tel])
            if r == len(bands) - 1:
                ax.set_xlabel("PWV (mm)", size='large')
            if c == 0:
                ax.set_ylabel(
                    band + "\n" +
                    r"NET $\left(\mathrm{\mu K_{CMB} \sqrt{s}}\right)$",
                    size='large',
                )

    style_handles = [
        Patch(facecolor='gray', alpha=0.25, label='Instrument Model (upper to lower)'),
        Line2D([0], [0], color='k', marker='o', linestyle='', label='Measured (PWV-binned)'),
        Patch(facecolor='gray', alpha=0.7, label='Calibration Uncertainty'),
    ]
    fig.legend(
        handles=style_handles, loc='lower center', ncol=3,
        bbox_to_anchor=(0.5, -0.08),
        fontsize='small', frameon=False,
    )

    return writer.save(save_tag, bbox_inches='tight')


def print_summary(model, cfg):
    pwv_vals_mm = model['pwv_vals_mm']
    tel_net = model['telescope_net']
    skip = _plot_cfg(cfg).get("skip_datasets", [])
    for tel in telescope_order:
        if tel in skip:
            continue
        for band in bands:
            lower = tel_net[tel]['lower'][band]
            upper = tel_net[tel]['upper'][band]
            i_mid = len(pwv_vals_mm) // 2
            print(
                f"{tel} {band}: NET(pwv={pwv_vals_mm[i_mid]:.2f}mm) = "
                f"{1e6*upper[i_mid]:.2f}-{1e6*lower[i_mid]:.2f} uK.rt(s)"
            )

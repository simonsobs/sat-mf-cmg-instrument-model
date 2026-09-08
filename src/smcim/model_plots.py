"""Per-wafer instrument-model paper figures: NEP, abscal, photon NEP,
optical loading, and the model-response comparisons.

Every ``make_*`` function takes a :class:`smcim.plotting.PlotWriter` as
its first argument and writes one figure through it. The ``build_*`` and
``print_*`` helpers derive intermediate quantities and write nothing.
"""
import numpy as np

from astropy import units as u, constants as const

from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from .conventions import bands, chmap, colors, telescope_order, wafer_order


def per_wafer_plot(
        writer,
        plot_func,
        per_band_extra=None,
        per_tel_extra=None,
        textx={'f090': 2.0, 'f150': 4},
        save_tag=None,
        figsize=(7.5, 5.5),
        show_x_grid=True,
    ):
    fig = plt.figure(figsize=figsize, dpi=150)

    for b, band in enumerate(['f090', 'f150']):
        ax = plt.subplot(1, 2, 1 + b)

        for i, k in enumerate(telescope_order):
            for wx, wafer in enumerate(wafer_order[k][::-1]):
                plot_func(ax, i * 7 + wx, k, wafer, band)
            if per_tel_extra is not None:
                per_tel_extra(ax, band, 7 * i + np.arange(7), k)

        if per_band_extra is not None:
            per_band_extra(ax, band)

        plt.yticks(np.arange(21),
                   [f"{sid.capitalize()}" for k in telescope_order for sid in wafer_order[k][::-1]])

        t1 = plt.text(textx[band], 20, f'SAT1\nPre-retrofit\n{band}', size=11, va='top')
        t2 = plt.text(textx[band], 13, f'SAT1\n{band}', size=11, va='top')
        t3 = plt.text(textx[band], 6, f'SAT3\n{band}', size=11, va='top')

        for t in [t1, t2, t3]:
            t.set_bbox(dict(facecolor='white', alpha=0.75, edgecolor='white'))

        ax.yaxis.set_minor_locator(ticker.FixedLocator([6.5, 13.5]))
        ax.yaxis.grid(which='major', visible=False)
        ax.yaxis.grid(which='minor', visible=True, linestyle='-', lw=0.75, color='k')
        ax.xaxis.grid(which='major', visible=show_x_grid)

        plt.ylim(-0.5, 20.5)

    if save_tag is not None:
        writer.save(save_tag)


def make_nep_plot(writer, noise_data, sims, per_wafer_models):
    def per_wafer_neps(ax, y_val, k, wafer, band):
        ch_wafer = per_wafer_models[k]['lower'][wafer]['channels'][chmap[band]]
        nep_base = 1e18 * per_wafer_models[k]['lower'][wafer]['outputs'][chmap[band]]['NEP_NC_total']
        nep_upper = 1e18 * per_wafer_models[k]['upper'][wafer]['outputs'][chmap[band]]['NEP_NC_total']
        ax.fill_betweenx(
            [y_val - 0.4, y_val + 0.4],
            x1=nep_base,  # +1e18*ch_wafer['NEP_vib_shift'],
            x2=nep_upper,  # +1e18*ch_wafer['NEP_vib_shift'],
            color=colors[k], alpha=0.75, ec=None,
        )

    def per_tel_boxes(ax, band, y_vals, k):
        ax.boxplot(
            [noise_data[k][band][f"ufm_{wafer}"]['median'] for wafer in wafer_order[k][::-1]],
            orientation='horizontal',
            positions=y_vals,
            tick_labels=[f"{w.capitalize()}" for w in wafer_order[k][::-1]],
            flierprops={
                'marker': '.',
            }, whis=[1, 99], widths=0.75,
            medianprops={'color': 'k', 'linewidth': 1},
        )

    def x_labels(ax, band):
        xmin = {'f090': 0, 'f150': 0}
        xmax = {'f090': 60, 'f150': 80}

        ax.set_xlim(xmin[band], xmax[band])
        ax.set_xlabel("Median per-detector NEP ($\\mathrm{aW} / \\sqrt{\\mathrm{Hz}}$)", size='large')

    per_wafer_plot(
        writer,
        per_wafer_neps,
        per_band_extra=x_labels,
        per_tel_extra=per_tel_boxes,
        save_tag="nep",
    )


def make_abscal_plot(writer, sims, abscal_data):
    """Per-wafer photometric calibration factor (bottom x-axis) with the
    corresponding optical efficiency overlaid on a twin top x-axis.

    abscal_data comes from convert_abscal_pickles.py and has the same
    key convention as noise_data:
        abscal_data[telescope][band][f"ufm_{wafer}"] = {
            'cal', 'cal_unc', 'eta', 'eta_unc'
        }
    """
    ax2_cache = {}  # id(ax) -> twin axis, created lazily per band panel

    def per_wafer_abscal(ax, y_val, k, wafer, band):
        entry = abscal_data[k][band].get(f"{wafer}")
        if entry is None:
            print(f"{wafer} entry not found in abscal_data")
            return

        color = colors[k] if k != 'satp1_iso' else 'gray'

        ax.errorbar(
            [entry['cal'].to(u.pW / u.K).value], [y_val],
            xerr=[entry['cal_unc'].to(u.pW / u.K).value],
            marker='.',
            ms=10,
            capsize=5,
            capthick=1.5,
            elinewidth=1.5,
            linestyle='none',
            color=color,
        )

        if not np.isnan(entry['eta']):
            if id(ax) not in ax2_cache:
                ax2 = ax.twiny()
                # twiny() shares the y-axis and turns its tick labels back
                # on by default, which duplicates the wafer labels onto the
                # right side of the eta axis -- suppress them here.
                ax2.tick_params(axis='y', which='both',
                                left=False, right=False,
                                labelleft=False, labelright=False)
                ax2_cache[id(ax)] = ax2
            ax2 = ax2_cache[id(ax)]

            ax2.errorbar(
                [entry['eta']], [y_val],
                xerr=[entry['eta_unc']],
                mec=color,
                mew=1,
                ms=5,
                ecolor=color,
                # alpha=0.7,
                elinewidth=1.5,
                capsize=0,
                linestyle='none',
            )

    def per_band_extra(ax, band):
        band_entries = [
            e for k in telescope_order for e in abscal_data[k][band].values()
        ]
        cal_vals = np.array(
            [e['cal'].to(u.pW / u.K).value for e in band_entries],
            dtype=float
        )
        cal_uncs = np.array(
            [e['cal_unc'].to(u.pW / u.K).value for e in band_entries],
            dtype=float
        )
        eta_vals = np.array([e['eta'] for e in band_entries], dtype=float)

        xlim = [0, np.nanmax(cal_vals) + 0.025 + np.nanmax(cal_uncs)]
        ax.set_xlim(xlim)
        ax.set_xlabel(r"Photometric Calibration Factor $\left(\mathrm{pW}/\mathrm{K}\right)$", size='large')

        lower = 1e12 * sims['lower']['outputs'][chmap[band]]['dpdt_rj']
        upper = 1e12 * sims['upper']['outputs'][chmap[band]]['dpdt_rj']
        ax.axvline(lower, color='grey', lw=1, ymin=0, ymax=1, alpha=0.5)
        ax.axvline(upper, color='grey', lw=1, ymin=0, ymax=1, alpha=0.5)
        ax.axvspan(lower, upper, color='grey', alpha=0.05)

        ax2 = ax2_cache.get(id(ax))
        if ax2 is not None:
            ratio = np.nanmean(cal_vals / eta_vals)
            ax2.set_xlim([0, xlim[1] / ratio])
            ax2.set_xlabel(r"Optical Efficiency, $\mathrm{\eta_{opt}}$", size='large')

    per_wafer_plot(
        writer,
        per_wafer_abscal,
        per_band_extra=per_band_extra,
        # tuned for the 0-~0.3 pW/K calibration-factor scale, not the
        # default NEP-plot scale -- nudge these if the labels overlap points
        textx={'f090': 0.015, 'f150': 0.02},
        # figsize=(6.25, 5.5),
        show_x_grid=False,
        save_tag="abscal",
    )


def make_abscal_per_wafer_plot(writer, per_wafer_models, abscal_data):
    """Per-wafer photometric calibration factor (bottom x-axis) with the
    corresponding optical efficiency overlaid on a twin top x-axis.

    abscal_data comes from convert_abscal_pickles.py and has the same
    key convention as noise_data:
        abscal_data[telescope][band][f"ufm_{wafer}"] = {
            'cal', 'cal_unc', 'eta', 'eta_unc'
        }
    """
    ax2_cache = {}  # id(ax) -> twin axis, created lazily per band panel

    def per_wafer_abscal(ax, y_val, k, wafer, band):
        entry = abscal_data[k][band].get(f"{wafer}")
        if entry is None:
            print(f"{wafer} entry not found in abscal_data")
            return

        # color = colors[k] if k != 'satp1_iso' else 'C0'

        out_base = per_wafer_models[k]['lower'][wafer]['outputs'][chmap[band]]
        out_upper = per_wafer_models[k]['upper'][wafer]['outputs'][chmap[band]]

        ax.fill_betweenx(
            [y_val - 0.4, y_val + 0.4],
            x1=1e12 * out_base['dpdt_rj'],
            x2=1e12 * out_upper['dpdt_rj'],
            color=colors[k], alpha=0.75, ec=None,
        )

        mk_color = 'k'
        ax.errorbar(
            [entry['cal'].to(u.pW / u.K).value], [y_val],
            xerr=[entry['cal_unc'].to(u.pW / u.K).value],
            marker='.',
            ms=8,
            capsize=5,
            capthick=1.2,
            elinewidth=1.2,
            linestyle='none',
            color=mk_color,
        )

        if not np.isnan(entry['eta']):
            if id(ax) not in ax2_cache:
                ax2 = ax.twiny()
                # twiny() shares the y-axis and turns its tick labels back
                # on by default, which duplicates the wafer labels onto the
                # right side of the eta axis -- suppress them here.
                ax2.tick_params(axis='y', which='both',
                                left=False, right=False,
                                labelleft=False, labelright=False)
                ax2_cache[id(ax)] = ax2
            ax2 = ax2_cache[id(ax)]

            ax2.errorbar(
                [entry['eta']], [y_val],
                xerr=[entry['eta_unc']],
                mec=mk_color,
                mew=1,
                ms=5,
                ecolor=mk_color,
                alpha=0.7,
                elinewidth=1.2,
                capsize=0,
                linestyle='none',
            )

    def per_band_extra(ax, band):
        band_entries = [
            e for k in telescope_order for e in abscal_data[k][band].values()
        ]
        cal_vals = np.array(
            [e['cal'].to(u.pW / u.K).value for e in band_entries],
            dtype=float
        )
        cal_uncs = np.array(
            [e['cal_unc'].to(u.pW / u.K).value for e in band_entries],
            dtype=float
        )
        eta_vals = np.array([e['eta'] for e in band_entries], dtype=float)

        xlim = [0, np.nanmax(cal_vals) + 0.025 + np.nanmax(cal_uncs)]
        ax.set_xlim(xlim)
        ax.set_xlabel(r"Photometric Calibration Factor $\left(\mathrm{pW}/\mathrm{K}\right)$", size='large')

        ax2 = ax2_cache.get(id(ax))
        if ax2 is not None:
            ratio = np.nanmean(cal_vals / eta_vals)
            ax2.set_xlim([0, xlim[1] / ratio])
            ax2.set_xlabel(r"Optical Efficiency, $\mathrm{\eta_{opt}}$", size='large')

    per_wafer_plot(
        writer,
        per_wafer_abscal,
        per_band_extra=per_band_extra,
        # tuned for the 0-~0.3 pW/K calibration-factor scale, not the
        # default NEP-plot scale -- nudge these if the labels overlap points
        textx={'f090': 0.015, 'f150': 0.02},
        # figsize=(6.25, 5.5),
        save_tag="abscal_per_wafer",
    )


def get_photon_loading(bandcenter, bandwidth, photon_nep):
    """ Equations since I've messed this up before
    $$
    NEP^2_{tot} = NEP^2_{dark} + 2 h \\nu_0 P_\\gamma + 2 P_\\gamma^2/\\Delta_\\nu
    NEP^2_\\gamma = 2 h \\nu_0 P_\\gamma + 2 P_\\gamma^2/\\Delta_\\nu
    0 = -NEP^2_\\gamma +  2 h \\nu_0 P_\\gamma + 2 P_\\gamma^2/\\Delta_\\nu
    $$
    """
    delta_nu = bandwidth  # *u.Hz
    nu_0 = bandcenter  # *u.Hz

    a = (2 / delta_nu)
    b = (2 * const.h * nu_0).to(u.aW / u.Hz)

    c = -(photon_nep ** 2)  # *u.aW /u.Hz**(0.5))**2
    return ((-b + np.sqrt(b ** 2 - 4 * a * c)) / (2 * a)).to(u.pW)


def build_implied_photon_NEP(noise_data, per_wafer_models):
    implied_photon_NEP = {}
    for k in per_wafer_models:
        implied_photon_NEP[k] = {}
        for kind in per_wafer_models[k]:
            implied_photon_NEP[k][kind] = {}

            for wafer in per_wafer_models[k][kind]:
                implied_photon_NEP[k][kind][wafer] = {}
                for band in bands:
                    ch_dict = per_wafer_models[k][kind][wafer]['channels'][chmap[band]]
                    out_dict = per_wafer_models[k][kind][wafer]['outputs'][chmap[band]]

                    dark_modeled_NEP = 1e18 * out_dict['NEP_dark']
                    measured_NEP = np.median(noise_data[k][band][f"ufm_{wafer}"]['median'])  # aW/rt.Hz

                    ## remove the shift in median NEP present due to high noise vibration tails
                    measured_NEP = measured_NEP - 1e18 * ch_dict['NEP_vib_shift']

                    implied_photon_NEP[k][kind][wafer][band] = np.sqrt(measured_NEP ** 2 - dark_modeled_NEP ** 2)
    return implied_photon_NEP


def build_nep_optical_loading(implied_photon_nep, per_wafer_models):
    optical_loading_from_NEP = {}
    for k in per_wafer_models:
        optical_loading_from_NEP[k] = {}
        for kind in per_wafer_models[k]:
            optical_loading_from_NEP[k][kind] = {}
            for wafer in per_wafer_models[k][kind]:
                optical_loading_from_NEP[k][kind][wafer] = {}
                for band in bands:
                    out_dict = per_wafer_models[k][kind][wafer]['outputs'][chmap[band]]
                    optical_loading_from_NEP[k][kind][wafer][band] = get_photon_loading(
                        out_dict['det_bandcenter'] * u.Hz,
                        out_dict['det_bandwidth'] * u.Hz,
                        implied_photon_nep[k][kind][wafer][band] * u.aW / (u.Hz ** 0.5),
                    ).to(u.pW).value
    return optical_loading_from_NEP


def make_photon_NEP_plot(writer, implied_photon_nep, per_wafer_models):
    def wafer_photon_NEPs(ax, y_val, k, wafer, band):
        out_base = per_wafer_models[k]['lower'][wafer]['outputs'][chmap[band]]
        out_upper = per_wafer_models[k]['upper'][wafer]['outputs'][chmap[band]]

        ax.plot([1e18 * out_base['NEP_photonNC'],
                 1e18 * out_upper['NEP_photonNC']],
                [y_val, y_val], '|-', color='k')

        ax.plot([np.mean([implied_photon_nep[k]['lower'][wafer][band],
                          implied_photon_nep[k]['upper'][wafer][band]])],
                [y_val], 'o', color=colors[k])
        ax.fill_betweenx(
            [y_val - 0.5, y_val + 0.5],
            x1=implied_photon_nep[k]['lower'][wafer][band],
            x2=implied_photon_nep[k]['upper'][wafer][band],
            color=colors[k], alpha=0.9, ec=None,
        )

    def nep_legends(ax, band):
        xmin = {'f090': 0, 'f150': 0}
        xmax = {'f090': 60, 'f150': 80}

        legend_handles = [
            Line2D([0], [0], color='k', marker='|', linestyle='-',
                   label='Instrument Model'),
            Line2D([0], [0], color='k', marker='o', linestyle='',
                   label='From Measured'),
        ]

        ax.legend(handles=legend_handles, loc='best')
        ax.set_xlim(xmin[band], xmax[band])
        ax.set_xlabel(
            "Implied Photon NEP ($\\mathrm{aW} / \\sqrt{\\mathrm{Hz}}$)", size='large'
        )

    per_wafer_plot(
        writer,
        wafer_photon_NEPs,
        nep_legends,
        save_tag="photon_nep",
    )


def make_optical_loading_plot(writer, optical_loading_from_nep, per_wafer_models):
    def wafer_optical_loading(ax, y_val, k, wafer, band):
        out_base = per_wafer_models[k]['lower'][wafer]['outputs'][chmap[band]]
        out_upper = per_wafer_models[k]['upper'][wafer]['outputs'][chmap[band]]

        from_NEP_base = optical_loading_from_nep[k]['lower'][wafer][band]
        from_NEP_upper = optical_loading_from_nep[k]['upper'][wafer][band]

        ax.plot(
            [from_NEP_base, from_NEP_upper],
            [y_val, y_val], 'o-', color=colors[k]
        )

        ax.plot([1e12 * out_base['P_opt'],
                 1e12 * out_upper['P_opt']],
                [y_val, y_val], '|-', color='k')

    def popt_legends(ax, band):
        xmin = {'f090': 0, 'f150': 0}
        xmax = {'f090': 5, 'f150': 8}

        if band == 'f150':
            legend_handles = [
                Line2D([0], [0], marker='o', linestyle='-', color='gray',
                       label='Measured\nfrom NEP'),
                Line2D([0], [0], marker='|', linestyle='-', color='k',
                       label='Instrument\nModel'),
            ]

            ax.legend(handles=legend_handles, loc='best')

        ax.set_xlim(xmin[band], xmax[band])
        ax.set_xlabel(
            "Optical Loading ($\\mathrm{pW}$)", size='large'
        )

    per_wafer_plot(
        writer,
        wafer_optical_loading, popt_legends,
        textx={'f090': 0.2, 'f150': 0.2},
        save_tag="optical_loading",
    )


def build_model_response(per_wafer_models):
    """
    model response is the slope of dpdt_rj and P_opt as a function of
    detector efficiency
    """
    model_response = {}
    for k in telescope_order:
        model_response[k] = {}
        for kind in per_wafer_models[k]:
            model_response[k][kind] = {}
            for band in bands:
                model_response[k][kind][band] = {}
                model = []
                for wx in wafer_order[k]:
                    sid = f'ufm_{wx}'
                    ch_wafer = per_wafer_models[k][kind][wx]['channels'][chmap[band]]
                    out_wafer = per_wafer_models[k][kind][wx]['outputs'][chmap[band]]

                    model.append(
                        (ch_wafer['det_eff'], 1e12 * out_wafer['dpdt_rj'], 1e12 * out_wafer['P_opt'])
                    )
                model = np.array(model)
                model_response[k][kind][band]['dpdt_rj'], x = np.polyfit(
                    model[:, 0], model[:, 1], deg=1
                )
                assert np.isclose(x, 0, atol=1e-4)

                model_response[k][kind][band]['P_opt'], x = np.polyfit(
                    model[:, 0], model[:, 2], deg=1
                )
                assert np.isclose(x, 0, atol=1e-4)
    return model_response


def make_calibration_comparison_plot(
    writer, abscal_data, per_wafer_models, model_response, sims,
    save_tag="reponse",
):
    plt.figure(figsize=(7.5, 3.25))
    effs = np.linspace(0, 1, 11)
    for b, band in enumerate(bands):
        plt.subplot(1, 2, 1 + b)
        for k in telescope_order[::-1]:
            for wx in wafer_order[k]:
                sid = f'ufm_{wx}'
                ch_wafer = per_wafer_models[k]['lower'][wx]['channels'][chmap[band]]

                plt.errorbar(
                    [ch_wafer['det_eff']],
                    [abscal_data[k][band][wx]['cal'].to(u.pW / u.K).value],
                    yerr=[abscal_data[k][band][wx]['cal_unc'].to(u.pW / u.K).value],
                    fmt='o', color=colors[k] if k != 'satp1_iso' else 'gray'
                )
        ## I am assuming we're still doing the thing where no optical
        ## efficiency parameters change between telescopes
        plt.plot(
            effs, effs * model_response[k]['lower'][band]['dpdt_rj'],
            color='gray', lw=0.5
        )
        plt.plot(
            effs, effs * model_response[k]['upper'][band]['dpdt_rj'],
            color='gray', lw=0.5
        )
        plt.fill_between(
            effs,
            effs * model_response[k]['upper'][band]['dpdt_rj'],
            effs * model_response[k]['lower'][band]['dpdt_rj'],
            alpha=0.2, color='gray',
        )
        for kind in ['lower', 'upper']:
            plt.plot(
                sims[kind]['channels'][chmap[band]]['det_eff'],
                1e12 * sims[kind]['outputs'][chmap[band]]['dpdt_rj'],
                'k^', zorder=20
            )

        plt.xlim(0, 1)
        plt.ylim(0, None)
        plt.xlabel("In-lab Detector Efficiency", size='large')
        plt.ylabel("Photometric Calibration (pW/K)", size='large')
        legend_handles = [
            Line2D([0], [0], color='k', marker='o', linestyle='',
                   label='Measured from Planets'),
            Line2D([0], [0], color='k', marker='^', linestyle='',
                   label='Upper and Lower'),
            Patch(facecolor='gray', alpha=0.2, edgecolor=None,
                  label='Instrument Model'),
        ]

        plt.legend(title=band, handles=legend_handles, loc='best')

    if save_tag is not None:
        writer.save(save_tag)


def make_optical_loading_comparison_plot(
    writer, optical_loading_from_nep, per_wafer_models, model_response,
    save_tag="optical_loading_compare",
):
    plt.figure(figsize=(7.5, 3.25))
    effs = np.linspace(0, 1, 11)
    for b, band in enumerate(bands):
        plt.subplot(1, 2, 1 + b)
        for k in telescope_order[::-1]:
            for wx in wafer_order[k]:
                ch_wafer = per_wafer_models[k]['lower'][wx]['channels'][chmap[band]]

                popt_base = optical_loading_from_nep[k]['lower'][wx][band]
                popt_upper = optical_loading_from_nep[k]['upper'][wx][band]
                popt_meas_nep = np.mean([popt_base, popt_upper])
                plt.errorbar(
                    [ch_wafer['det_eff']],
                    [popt_meas_nep],
                    yerr=[np.abs(popt_upper - popt_meas_nep)],  ## the data point is in the middle
                    fmt='o', color=colors[k] if k != 'satp1_iso' else 'gray'
                )
            plt.fill_between(
                effs,
                effs * model_response[k]['upper'][band]['P_opt'],
                effs * model_response[k]['lower'][band]['P_opt'],
                alpha=0.2, color=colors[k],
            )

        legend_handles = [
            Line2D([0], [0], color='k', marker='o', linestyle='',
                   label='Measured from NEP'),
            Patch(facecolor='gray', alpha=0.2, edgecolor=None,
                  label='Instrument Model'),
        ]

        plt.legend(title=band, handles=legend_handles, loc='best')

        plt.xlim(0, 1)
        plt.ylim(0, None)
        plt.xlabel("In-lab Detector Efficiency", size='large')
        plt.ylabel("Optical Loading (pW)", size='large')

    if save_tag is not None:
        writer.save(save_tag)


def print_optical_loading(per_wafer_models):
    print("Optical Loading from Wafer Models")

    for k in telescope_order:
        for band in bands:
            channels = [per_wafer_models[k]['lower'][wafer]['channels'][chmap[band]] for wafer in wafer_order[k]]
            out_base = [per_wafer_models[k]['lower'][wafer]['outputs'][chmap[band]] for wafer in wafer_order[k]]

            out_upper = [per_wafer_models[k]['upper'][wafer]['outputs'][chmap[band]] for wafer in wafer_order[k]]

            loading_base = [1e12 * o['P_opt'] / c['det_eff'] for o, c in zip(out_base, channels)]
            loading_upper = [1e12 * o['P_opt'] / c['det_eff'] for o, c in zip(out_upper, channels)]
            print(k, band, np.mean(loading_upper), np.mean(loading_base))


def print_optical_efficiency(sims):
    print("Optical Efficiency from Sims")
    for band in bands:
        out_base = sims['lower']['outputs'][chmap[band]]
        out_upper = sims['upper']['outputs'][chmap[band]]

        eff_base = out_base['dpdt_rj'] * (u.W / u.Kelvin) / (const.k_B * out_base['sys_bandwidth'] * u.Hz)
        eff_upper = out_upper['dpdt_rj'] * (u.W / u.Kelvin) / (const.k_B * out_upper['sys_bandwidth'] * u.Hz)
        print(band, eff_base.to(1), eff_upper.to(1))

"""Atmospheric efficiency on a PWV x elevation grid, from the base sim
(no per-wafer configs applied).
"""
import numpy as np
import matplotlib.pyplot as plt

import jbolo.jbolo_funcs as jf
from jbolo.utils import load_sim

from .conventions import chmap


def _run_single(sim_file, pwv_um, elevation_deg):
    sim = load_sim(sim_file)
    sim['sources']['atmosphere']['pwv'] = pwv_um
    sim['sources']['atmosphere']['elevation'] = elevation_deg
    jf.run_optics(sim)
    jf.run_bolos(sim)
    return sim


def generate_atmosphere_grid(sim_file, pwv_vals_mm, elevation_vals_deg):
    """Sweep the base sim over (PWV, elevation) and record the band-averaged
    atmospheric efficiency.

    Returns a dict with ``pwv`` and ``elevation`` meshgrids (rows =
    elevation, columns = PWV) and an ``f090`` / ``f150`` array each.
    """
    pwv_grid, elevation_grid = np.meshgrid(pwv_vals_mm, elevation_vals_deg)

    grid = {
        'pwv': pwv_grid,
        'elevation': elevation_grid,
        'f090': np.zeros_like(pwv_grid),
        'f150': np.zeros_like(pwv_grid),
    }

    for i in range(pwv_grid.shape[0]):
        for j in range(pwv_grid.shape[1]):
            sim = _run_single(
                sim_file,
                int(1000 * pwv_grid[i, j]),
                int(elevation_grid[i, j]),
            )
            for band in ('f090', 'f150'):
                grid[band][i, j] = (
                    sim['outputs'][chmap[band]]['sources']['atmosphere']['effic_avg']
                )
    return grid


def make_atmosphere_plot(grid, save_path):
    pwv_vals = grid['pwv'][0, :]
    elevation_vals = grid['elevation'][:, 0]

    dx = pwv_vals[1] - pwv_vals[0]
    dy = elevation_vals[1] - elevation_vals[0]
    extent = [
        pwv_vals[0] - dx / 2, pwv_vals[-1] + dx / 2,
        elevation_vals[0] - dy / 2, elevation_vals[-1] + dy / 2,
    ]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, band in zip(axes, ['f090', 'f150']):
        im = ax.imshow(
            grid[band],
            origin='lower',        # row 0 = lowest elevation at the bottom
            extent=extent,
            aspect='auto',         # otherwise 1 deg el == 1 mm pwv on screen
            cmap='viridis',
        )
        ax.set_xlabel('PWV [mm]')
        ax.set_title(band)
        fig.colorbar(im, ax=ax, label='Atmospheric Efficiency')
    axes[0].set_ylabel('Elevation [deg]')

    fig.savefig(save_path)
    return save_path

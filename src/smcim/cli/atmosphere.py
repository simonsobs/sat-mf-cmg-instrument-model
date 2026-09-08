"""Entry point: atmospheric efficiency on a PWV x elevation grid.

    smcim-atmosphere configs/config.yaml

Writes ``{data_dir}/atmosphere_model.npy`` and
``{plot_dir}/atmosphere_model.png``.
"""
import os

from ._common import config_arg_parser, load_and_setup


def main(argv=None):
    parser = config_arg_parser(
        "Atmospheric efficiency vs PWV and elevation (base sim)."
    )
    args = parser.parse_args(argv)
    cfg = load_and_setup(args.config)

    import numpy as np

    from ..config import data_dir, plot_dir
    from ..run_models import sim_list
    from .. import atmosphere

    g = cfg["atmosphere"]["grid"]
    pwv_vals_mm = np.linspace(g["pwv_min_mm"], g["pwv_max_mm"], g["n_pwv"])
    elevation_vals_deg = np.linspace(
        g["elevation_min_deg"], g["elevation_max_deg"], g["n_elevation"]
    )

    grid = atmosphere.generate_atmosphere_grid(
        sim_list()["lower"], pwv_vals_mm, elevation_vals_deg
    )

    out_data = data_dir(cfg)
    out_plots = plot_dir(cfg)
    os.makedirs(out_data, exist_ok=True)
    os.makedirs(out_plots, exist_ok=True)

    npy_path = os.path.join(out_data, "atmosphere_model.npy")
    np.save(npy_path, grid)
    print(f"Wrote {npy_path}")

    png_path = atmosphere.make_atmosphere_plot(
        grid, os.path.join(out_plots, "atmosphere_model.png")
    )
    print(f"Wrote {png_path}")


if __name__ == "__main__":
    main()

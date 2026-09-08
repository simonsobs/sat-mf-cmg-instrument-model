"""Entry point: per-wafer instrument-model paper plots.

    smcim-model-plots configs/config.yaml
"""
from ._common import config_arg_parser, load_and_setup


def main(argv=None):
    parser = config_arg_parser("Per-wafer instrument-model paper plots.")
    args = parser.parse_args(argv)
    cfg = load_and_setup(args.config)

    # jbolo-touching imports happen after the environment is set up.
    import numpy as np

    from ..config import resolve, save_key, plot_dir
    from ..conventions import use_paper_style
    from ..plotting import PlotWriter
    from ..run_models import run_all_models
    from .. import model_plots as mp

    use_paper_style()
    writer = PlotWriter(
        plot_dir=plot_dir(cfg),
        save_key=save_key(cfg),
        save_type=cfg["paths"].get("save_type", "pdf"),
    )

    data_files = cfg["model_plots"]["data_files"]
    noise_data = np.load(
        resolve(cfg, data_files["noise_data"]), allow_pickle=True
    ).item()
    abscal_data = np.load(
        resolve(cfg, data_files["abscal_data"]), allow_pickle=True
    ).item()

    sims, per_wafer_models = run_all_models()

    mp.make_nep_plot(writer, noise_data, sims, per_wafer_models)
    mp.make_abscal_plot(writer, sims, abscal_data)

    implied_photon_nep = mp.build_implied_photon_NEP(noise_data, per_wafer_models)
    optical_loading_from_nep = mp.build_nep_optical_loading(
        implied_photon_nep, per_wafer_models
    )

    mp.make_photon_NEP_plot(writer, implied_photon_nep, per_wafer_models)
    mp.make_optical_loading_plot(writer, optical_loading_from_nep, per_wafer_models)

    model_response = mp.build_model_response(per_wafer_models)
    mp.make_calibration_comparison_plot(
        writer, abscal_data, per_wafer_models, model_response, sims
    )
    mp.make_optical_loading_comparison_plot(
        writer, optical_loading_from_nep, per_wafer_models, model_response
    )

    mp.print_optical_loading(per_wafer_models)
    mp.print_optical_efficiency(sims)


if __name__ == "__main__":
    main()

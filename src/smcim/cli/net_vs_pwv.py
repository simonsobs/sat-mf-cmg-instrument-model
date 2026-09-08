"""Entry point: telescope NET vs PWV -- instrument model, and model vs
measured.

    smcim-net-vs-pwv configs/config.yaml              # compute if no cache, else load
    smcim-net-vs-pwv configs/config.yaml --recompute  # force recompute + overwrite cache
    smcim-net-vs-pwv configs/config.yaml --use-cached # require cache, never run jbolo
"""
import os

from ._common import config_arg_parser, load_and_setup


def main(argv=None):
    parser = config_arg_parser(
        "Telescope NET vs PWV: instrument model, and model vs measured."
    )
    cache_grp = parser.add_mutually_exclusive_group()
    cache_grp.add_argument(
        "--recompute", action="store_true",
        help="Always recompute the model, overwriting any existing cache.",
    )
    cache_grp.add_argument(
        "--use-cached", action="store_true",
        help="Require the cached model; never run jbolo (error if missing).",
    )
    args = parser.parse_args(argv)
    cfg = load_and_setup(args.config)

    import numpy as np

    from ..conventions import use_paper_style
    from .. import net_vs_pwv as nvp

    use_paper_style()
    cache_path = nvp.model_cache_path(cfg)

    if args.use_cached:
        if not os.path.exists(cache_path):
            raise SystemExit(
                f"--use-cached given but no cached model at {cache_path}"
            )
        print(f"Loading cached model: {cache_path}")
        model = nvp.load_cached_model(cache_path)
    elif args.recompute or not os.path.exists(cache_path):
        print(
            "Recomputing model (--recompute)."
            if args.recompute
            else f"No cached model at {cache_path}; computing."
        )
        model = nvp.compute_model(cfg)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        np.save(cache_path, model)
        print(f"Wrote model cache: {cache_path}")
    else:
        print(f"Loading cached model: {cache_path}")
        model = nvp.load_cached_model(cache_path)

    nvp.make_telescope_net_plot(model, cfg)

    obs_amans = nvp.load_measured(cfg)
    nvp.make_model_vs_measured_plot(model, obs_amans, cfg)

    nvp.print_summary(model, cfg)


if __name__ == "__main__":
    main()

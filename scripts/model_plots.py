#!/usr/bin/env python
"""Thin wrapper around `smcim.cli.model_plots` (installed as
`smcim-model-plots`). Run from a checkout without installing the console
script, e.g.:

    python scripts/model_plots.py configs/config.yaml
"""
from smcim.cli.model_plots import main

if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Thin wrapper around `smcim.cli.atmosphere` (installed as
`smcim-atmosphere`). Run from a checkout without installing the console
script, e.g.:

    python scripts/generate_atmospheric_model.py configs/config.yaml
"""
from smcim.cli.atmosphere import main

if __name__ == "__main__":
    main()

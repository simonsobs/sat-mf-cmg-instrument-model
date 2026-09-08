#!/usr/bin/env python
"""Thin wrapper around `smcim.cli.net_vs_pwv` (installed as
`smcim-net-vs-pwv`). Run from a checkout without installing the console
script, e.g.:

    python scripts/net_vs_pwv.py configs/config.yaml --use-cached
"""
from smcim.cli.net_vs_pwv import main

if __name__ == "__main__":
    main()

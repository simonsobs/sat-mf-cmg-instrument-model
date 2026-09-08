"""Shared CLI plumbing: the config positional argument and load+env setup."""
import argparse

from ..config import load_config, setup_environment


def config_arg_parser(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "config",
        help="Path to the YAML config file (see configs/config.yaml).",
    )
    return parser


def load_and_setup(config_path):
    """Load the config and set the jbolo environment variables from it."""
    cfg = load_config(config_path)
    setup_environment(cfg)
    return cfg

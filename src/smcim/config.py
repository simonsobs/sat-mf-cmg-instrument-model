"""Config loading, repo-root resolution, and jbolo environment setup.

Per-system config files (``configs/*.yaml``) express paths relative to
the instrument-model checkout. That root is, in priority order:

  1. the config's top-level ``root:`` key, if set;
  2. the ``SMCIM_ROOT`` environment variable, if set;
  3. the default ``~/software/sat-mf-cmg-instrument-model``.

Absolute paths in a config are always used as-is.
"""
import os
import datetime as dt

import yaml

DEFAULT_ROOT = os.path.join(
    os.path.expanduser("~"), "software", "sat-mf-cmg-instrument-model"
)


def repo_root(cfg=None):
    """Directory that repo-relative config paths resolve against."""
    if cfg and cfg.get("root"):
        cand = cfg["root"]
    else:
        cand = os.environ.get("SMCIM_ROOT", DEFAULT_ROOT)
    return os.path.abspath(os.path.expanduser(cand))


def load_config(path):
    """Read a YAML config file into a dict."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


def resolve(cfg, path):
    """Resolve one config path: absolute stays absolute, relative joins
    onto :func:`repo_root`."""
    path = os.path.expanduser(str(path))
    if os.path.isabs(path):
        return path
    return os.path.join(repo_root(cfg), path)


def save_key(cfg):
    """The date stamp used in output filenames -- ``paths.save_key`` if
    set, else today as YYYYMMDD."""
    key = cfg.get("paths", {}).get("save_key")
    return str(key) if key else dt.datetime.now().strftime("%Y%m%d")


def data_dir(cfg):
    """Resolved ``paths.data_dir``."""
    return resolve(cfg, cfg["paths"]["data_dir"])


def plot_dir(cfg):
    """Resolved ``paths.plot_dir``."""
    return resolve(cfg, cfg["paths"]["plot_dir"])


def setup_environment(cfg):
    """Set the env vars the jbolo stack reads, from ``environment.env_vars``.

    Each entry is one of::

        {repo_relative: true, path: "model"}          -> <repo_root>/model
        {home_relative: true, path: "software/jbolo"} -> $HOME/software/jbolo
        {path: "/abs/path"}                           -> used as-is
    """
    root = repo_root(cfg)
    home = os.path.expanduser("~")
    for name, spec in cfg.get("environment", {}).get("env_vars", {}).items():
        if spec.get("repo_relative"):
            value = os.path.join(root, spec["path"])
        elif spec.get("home_relative"):
            value = os.path.join(home, spec["path"])
        else:
            value = os.path.expanduser(spec["path"])
        os.environ[name] = value

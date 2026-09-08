"""Shared plot-output helper."""
import os
from dataclasses import dataclass

import matplotlib.pyplot as plt


@dataclass
class PlotWriter:
    """Writes figures to ``{plot_dir}/{save_key}_{save_tag}.{save_type}``."""

    plot_dir: str
    save_key: str
    save_type: str = "pdf"

    def path(self, save_tag):
        return os.path.join(
            self.plot_dir, f"{self.save_key}_{save_tag}.{self.save_type}"
        )

    def save(self, save_tag, fig=None, **savefig_kwargs):
        os.makedirs(self.plot_dir, exist_ok=True)
        target = fig if fig is not None else plt
        out = self.path(save_tag)
        target.savefig(out, **savefig_kwargs)
        return out

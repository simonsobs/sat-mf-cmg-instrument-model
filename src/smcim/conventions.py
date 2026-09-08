"""Shared naming, ordering and plot-style conventions for the paper plots.

Importing this module imports ``socolors``, which registers the ``apj``
matplotlib style; call :func:`use_paper_style` to activate it.
"""
import socolors  # noqa: F401  -- registers the 'apj' matplotlib style
import matplotlib.pyplot as plt
from socolors.sat import colors as _sat_colors

bands = ["f090", "f150"]

# band -> jbolo channel name
chmap = {"f090": "MF_1", "f150": "MF_2"}

# the 'lower'/'upper' bounding sims are run in parallel throughout to
# bracket a plausible range rather than quote a single point estimate.
kinds = ["lower", "upper"]

telescope_order = ["satp3_iso", "satp1_retrofit", "satp1_iso"]

wafer_order = {
    "satp1_iso": ["mv19", "mv18", "mv22", "mv29", "mv7", "mv9", "mv15"],
    "satp1_retrofit": ["mv19", "mv48r1", "mv50r2", "mv22", "mv18", "mv52r1", "mv51"],
    "satp3_iso": ["mv5", "mv27", "mv35", "mv12", "mv23", "mv33", "mv17"],
}

titles = {
    "satp1_iso": "SAT1 Pre-Retrofit",
    "satp3_iso": "SAT3",
    "satp1_retrofit": "SAT1",
}

colors = {
    "satp1_iso": "C6",
    "satp3_iso": _sat_colors.satp3,
    "satp1_retrofit": _sat_colors.satp1,
}

# marker per telescope for the model-vs-measured overlay
formats = {"satp1_iso": "x", "satp3_iso": "o", "satp1_retrofit": "o"}


def use_paper_style():
    """Activate the ``apj`` matplotlib style used for the paper figures."""
    plt.style.use("apj")

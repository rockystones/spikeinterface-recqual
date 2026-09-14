"""Regenerate the consensus-longitudinal figure from the consensus tables.

C1 was first drawn by an uncommitted inline snippet during the overnight
session -- a provenance gap: the figure existed with no script to point at.
This is that script, reading only the committed consensus outputs, so the
figure is reproducible from `data/derived/ns5/consensus/` alone.

Run from repo root:

    uv run python notebooks/scratch_consensus_figures.py

See docs/notes/multisorter_agreement.md and docs/notes/data_inspection.md.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
CONS = REPO / "data" / "derived" / "ns5" / "consensus"
FIG = REPO / "figures" / "consensus"


def load_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-stem mean agreement, and the ladder joined to mean unit counts."""
    per = pd.read_parquet(CONS / "consensus_per_stem.parquet")
    lad = pd.read_parquet(CONS / "consensus_ladder.parquet")
    per["date"] = pd.to_datetime(per.date)
    lad["date"] = pd.to_datetime(lad.date)

    # ladder as a fraction of the mean single-sorter unit count, so arrays
    # with different yields share one axis
    runs = pd.concat([pd.read_parquet(p) for p in sorted(
        (CONS / "shards").glob("*.parquet"))], ignore_index=True)
    runs = runs[runs.kind == "run"]
    mean_units = (runs.dropna(subset=["n_units"])
                      .groupby("stem").n_units.mean().rename("mean_units"))
    lad = lad.merge(mean_units, on="stem")
    lad["frac"] = lad.n_units / lad.mean_units
    return per, lad


def fig_c1(per: pd.DataFrame, lad: pd.DataFrame, out: Path) -> None:
    """Two panels: pairwise agreement over time; the >=3-sorter core."""
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.2))
    keys = sorted(per.groupby(["subject", "implant", "array"]).groups)
    for k in keys:
        g = per[(per.subject == k[0]) & (per.implant == k[1])
                & (per.array == k[2])].sort_values("date")
        axes[0].plot(g.date, g.mean_agreement, marker="o", ms=4, lw=1.2,
                     label=f"{k[0]} {k[1]} {k[2]}")
    axes[0].set_ylabel("mean pairwise fraction matched")
    axes[0].set_title("Four-sorter agreement, 48 stems", fontsize=10)
    axes[0].tick_params(axis="x", labelrotation=45, labelsize=7)
    axes[0].grid(alpha=0.25)
    axes[0].legend(fontsize=6)

    g3 = lad[lad.min_agreement == 3]
    for k in keys:
        g = g3[(g3.subject == k[0]) & (g3.implant == k[1])
               & (g3.array == k[2])].sort_values("date")
        axes[1].plot(g.date, g.frac, marker="o", ms=4, lw=1.2)
    axes[1].set_ylabel("units found by >= 3 sorters / mean units per sorter")
    axes[1].set_title("The consensus core over time", fontsize=10)
    axes[1].tick_params(axis="x", labelrotation=45, labelsize=7)
    axes[1].grid(alpha=0.25)

    fig.suptitle("Agreement structure as a longitudinal metric "
                 "(dips are the arrays' documented declines)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    per, lad = load_tables()
    print(f"{per.stem.nunique()} stems; agreement median "
          f"{per.mean_agreement.median():.3f}, "
          f"min {per.mean_agreement.min():.3f}")
    fig_c1(per, lad, FIG / "C1_agreement_longitudinal.png")
    print(f"wrote {FIG / 'C1_agreement_longitudinal.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Verification figure for the Nigel/Fisk stripe coating maps (D-014).

One panel per array: the CMP grid in Blackrock orientation (col
left-to-right, row bottom-to-top, WIRE BUNDLE ON THE RIGHT), each
connected electrode colored by its stripe condition and annotated with
its electrode ID. Unconnected positions are blank. L1-carrying
conditions are saturated, non-L1 pale; per the owner's phase ruling
the L1 stripes start at the column OPPOSITE the wire bundle (col 0,
even columns).

Uses surface_map() from scratch_surface_conditions.py, i.e. exactly
the assignment the analysis pipeline uses - so what the owner confirms
here is what the code computes with.

Output: figures/surface/stripe_coating_maps.png
Run: uv run python notebooks/scratch_stripe_map_figure.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrow, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scratch_surface_conditions import surface_map  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "figures" / "surface" / "stripe_coating_maps.png"

# panel order: (serial, subject, pedestal/anatomy label)
PANELS = [
    ("1025-001496", "Nigel", "Anterior pedestal / Lateral array"),
    ("1025-001473", "Nigel", "Posterior pedestal / Medial array"),
    ("1025-001498", "Fisk SN1498", "Anterior pedestal / Lateral array"),
    ("1025-001504", "Fisk SN1504", "Posterior pedestal / Medial array"),
]
# saturated = carries L1, pale = its non-L1 neighbour stripe
COLORS = {
    "TNP L1": "#1f5fa8",           # saturated blue
    "TNP only": "#aecbe8",         # pale blue
    "EDCNHS L1": "#1e7d34",        # saturated green
    "Non-treated Ctrl": "#d9d9d9",  # pale gray
}


def main() -> int:
    fig, axes = plt.subplots(2, 2, figsize=(13, 11))
    for ax, (serial, subject, ped) in zip(axes.ravel(), PANELS):
        d = surface_map(serial)
        fams = sorted(d.condition.unique())
        for r in d.itertuples():
            ax.add_patch(Rectangle((r.col - 0.5, r.row - 0.5), 1, 1,
                                   facecolor=COLORS[r.condition],
                                   edgecolor="white", lw=1.5))
            ax.text(r.col, r.row, str(r.channel_id), ha="center",
                    va="center", fontsize=7,
                    color="white" if r.has_l1 else "black")
        # unconnected positions: light hatch so absences are visible
        present = set(zip(d.col, d.row))
        for c in range(10):
            for rw in range(10):
                if (c, rw) not in present:
                    ax.add_patch(Rectangle((c - 0.5, rw - 0.5), 1, 1,
                                           facecolor="none",
                                           edgecolor="#bbbbbb",
                                           hatch="///", lw=0.5))
        # wire bundle on the RIGHT in CMP orientation
        ax.add_patch(Rectangle((9.6, 3.5), 0.5, 3, facecolor="#444444"))
        ax.annotate("wire\nbundle", (9.85, 5), ha="center", va="center",
                    fontsize=8, color="white")
        ax.annotate("", xy=(10.9, 5), xytext=(10.15, 5),
                    arrowprops=dict(arrowstyle="-", lw=3, color="#444"))
        # L1 phase marker under the treated columns
        for c in range(0, 10, 2):
            ax.annotate("L1", (c, -1.05), ha="center", va="center",
                        fontsize=8, fontweight="bold", color="#7a1010")
        ax.set_xlim(-0.7, 11.2)
        ax.set_ylim(-1.6, 9.7)
        ax.set_aspect("equal")
        ax.set_xticks(range(10))
        ax.set_yticks(range(10))
        ax.set_xlabel("CMP col  (L1 stripes start opposite the bundle)")
        ax.set_ylabel("CMP row")
        ax.set_title(f"{subject} - {ped}\n{serial}:  "
                     f"{' vs '.join(fams)}", fontsize=10)
    handles = [Rectangle((0, 0), 1, 1, facecolor=c, edgecolor="gray")
               for c in COLORS.values()]
    fig.legend(handles, list(COLORS), loc="lower center", ncol=4,
               fontsize=10, frameon=False)
    fig.suptitle("Stripe coating maps as the pipeline computes them "
                 "(owner ruling D-014, 2026-09-17) - numbers are "
                 "electrode IDs, hatched cells unconnected",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

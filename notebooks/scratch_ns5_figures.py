"""Figures for the multi-sorter comparison, which ran and was never drawn.

`scratch_ns5_resort.py` re-detects units from continuous data with four modern
sorters and writes one shard per session to `data/derived/ns5/shards/`. 110
sessions, 380 jobs, on Nigel and Rocky. The numbers went into
[[robustness]] as text and no figure was ever made.

This is the layer CLAUDE.md's sorter policy is about: *"multi-sorter consensus
is the goal; single-sorter output is never the primary result"*. What it shows
is how far apart four reasonable sorters land on the same recording, which is
the honest error bar on every unit count elsewhere in the project.

    M1_counts      unit count per sorter over time, per array
    M2_spread      how far apart the sorters land on the same session
    M3_recovery    how much of the NEV's own detection each sorter recovers
    M4_agreement   pairwise, so the disagreement can be attributed

Run from repo root:

    uv run python notebooks/scratch_ns5_figures.py

See:
- docs/notes/robustness.md
- docs/notes/kilosort4_gpu.md
"""

from __future__ import annotations

import glob
import sys
import warnings
from itertools import combinations
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))

SHARDS = str(REPO / "data" / "derived" / "ns5" / "shards" / "*.parquet")
FIG = REPO / "figures" / "sorters"

SORTER_COLOR = {"mountainsort5": "#1f77b4", "tridesclous2": "#2ca02c",
                "spykingcircus2": "#ff7f0e", "kilosort4": "#d62728"}


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def load() -> pd.DataFrame:
    d = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(SHARDS))],
                  ignore_index=True)
    d["date"] = pd.to_datetime(d.date)
    return d


# %%
def fig_counts(ok: pd.DataFrame, out: Path) -> None:
    """Unit count per sorter over time, one panel per array."""
    keys = sorted({(s, a) for s, a in zip(ok.subject, ok.array, strict=True)})
    fig, axes = plt.subplots(1, len(keys), figsize=(4.2 * len(keys), 4.4),
                             squeeze=False)
    for j, (sub, arr) in enumerate(keys):
        ax = axes[0, j]
        g = ok[(ok.subject == sub) & (ok.array == arr)]
        for srt, c in g.groupby("sorter"):
            c = c.sort_values("date")
            ax.plot(c.date, c.n_units, "o-", ms=3.4, lw=1,
                    color=SORTER_COLOR.get(srt, "0.4"), alpha=0.85,
                    label=f"{srt} (n={len(c)}, med {c.n_units.median():.0f})")
        ax.set_ylabel("units found")
        ax.set_title(f"{sub} {arr}", fontsize=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.grid(alpha=0.25)
        ax.legend(fontsize=7)
    fig.suptitle("Four sorters on the same continuous recordings. "
                 "Kilosort4 sits roughly 2x above the others — CLAUDE.md's "
                 "recorded over-splitting gotcha.", fontsize=11)
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_spread(ok: pd.DataFrame, out: Path) -> pd.DataFrame:
    """How far apart the sorters land on one session.

    The spread is the ratio of the highest to the lowest unit count on the
    *same* recording, so it is a pure method effect -- the tissue, the
    amplifier and the day are identical across the four numbers being
    compared. It is the error bar that belongs on every single-sorter count.
    """
    piv = ok.pivot_table(index=["subject", "array", "stem", "date"],
                         columns="sorter", values="n_units")
    three = [s for s in ("mountainsort5", "tridesclous2", "spykingcircus2")
             if s in piv.columns]
    sub3 = piv[three].dropna()
    spread3 = (sub3.max(axis=1) / sub3.min(axis=1).replace(0, np.nan)).dropna()
    allp = piv.dropna()
    spread4 = ((allp.max(axis=1) / allp.min(axis=1).replace(0, np.nan)).dropna()
               if len(allp) else pd.Series(dtype=float))

    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.4))
    ax = axes[0]
    bins = np.arange(1.0, 4.05, 0.1)
    ax.hist(spread3, bins=bins, alpha=0.75, color="#1f77b4",
            label=f"3 CPU sorters (n={len(spread3)})")
    if len(spread4):
        ax.hist(spread4, bins=bins, alpha=0.6, color="#d62728",
                label=f"all 4, incl. KS4 (n={len(spread4)})")
    ax.axvline(float(spread3.median()), color="#1f77b4", ls="--", lw=1.4)
    ax.set_xlabel("max / min unit count on the same session")
    ax.set_ylabel("sessions")
    ax.set_title(f"median {spread3.median():.2f}x, "
                 f"p90 {spread3.quantile(0.9):.2f}x", fontsize=10)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[1]
    s = spread3.reset_index()
    s.columns = [*s.columns[:-1], "spread"]
    for (sub, arr), g in s.groupby(["subject", "array"]):
        g = g.sort_values("date")
        ax.plot(g.date, g.spread, "o-", ms=3.2, lw=0.9, alpha=0.8,
                label=f"{sub} {arr}")
    ax.axhline(1.0, color="k", lw=1)
    ax.set_ylabel("spread (max/min)")
    ax.set_title("does the disagreement grow as yield falls?", fontsize=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7.5)

    ax = axes[2]
    order = [c for c in ("mountainsort5", "tridesclous2", "spykingcircus2",
                         "kilosort4") if c in piv.columns]
    groups = [piv[c].dropna() for c in order]
    ax.boxplot(groups, tick_labels=[f"{c}\nn={len(g)}"
                                    for c, g in zip(order, groups,
                                                    strict=True)],
               widths=0.55, showfliers=False)
    for i, (c, g) in enumerate(zip(order, groups, strict=True), start=1):
        ax.scatter(np.random.default_rng(2).normal(i, 0.06, len(g)), g, s=10,
                   alpha=0.45, color=SORTER_COLOR.get(c, "0.3"))
    ax.set_ylabel("units per session")
    ax.set_title("per-sorter distribution", fontsize=10)
    ax.grid(alpha=0.25, axis="y")
    ax.tick_params(labelsize=7.5)

    fig.suptitle("Method spread on identical recordings — the error bar that "
                 "belongs on any single-sorter unit count.", fontsize=11)
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return pd.DataFrame(dict(
        scope=["3 CPU sorters", "all 4"],
        n=[len(spread3), len(spread4)],
        median=[float(spread3.median()),
                float(spread4.median()) if len(spread4) else np.nan],
        p90=[float(spread3.quantile(0.9)),
             float(spread4.quantile(0.9)) if len(spread4) else np.nan]))


def fig_recovery(ok: pd.DataFrame, out: Path) -> None:
    """How much of the NSP's own detection each sorter finds again.

    `frac_nev_recovered` is the share of NEV threshold crossings a sorter's
    spikes land on, and `chance_nev_recovered` is what the same comparison
    scores on shuffled times. The gap between them is the part that is not
    coincidence -- without the chance line the raw fraction is unreadable,
    because a sorter that fires everywhere recovers everything.
    """
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.4))
    order = [c for c in SORTER_COLOR if c in set(ok.sorter)]
    ax = axes[0]
    for i, srt in enumerate(order, start=1):
        g = ok[ok.sorter == srt]
        ax.scatter(np.random.default_rng(3).normal(i, 0.07, len(g)),
                   g.frac_nev_recovered, s=14, alpha=0.6,
                   color=SORTER_COLOR.get(srt, "0.3"))
        ax.scatter(np.random.default_rng(4).normal(i, 0.07, len(g)),
                   g.chance_nev_recovered, s=10, alpha=0.4, color="0.6")
    ax.set_xticks(range(1, len(order) + 1))
    ax.set_xticklabels(order, fontsize=8)
    ax.set_ylabel("fraction of NEV crossings recovered")
    ax.set_title("coloured = real, grey = chance on shuffled times",
                 fontsize=10)
    ax.grid(alpha=0.25, axis="y")

    ax = axes[1]
    for srt in order:
        g = ok[ok.sorter == srt].dropna(subset=["frac_nev_recovered"])
        lift = g.frac_nev_recovered - g.chance_nev_recovered
        ax.hist(lift, bins=np.arange(-0.1, 1.05, 0.05), alpha=0.55,
                color=SORTER_COLOR.get(srt, "0.3"),
                label=f"{srt}: median {lift.median():+.2f}")
    ax.axvline(0, color="k", lw=1)
    ax.set_xlabel("recovered minus chance")
    ax.set_ylabel("sessions")
    ax.set_title("the part that is not coincidence", fontsize=10)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7.5)
    fig.suptitle("Agreement with the NSP's own threshold detection",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_agreement(ok: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Pairwise unit counts, so the spread can be attributed to a pair."""
    piv = ok.pivot_table(index=["subject", "array", "stem"], columns="sorter",
                         values="n_units")
    order = [c for c in SORTER_COLOR if c in piv.columns]
    pairs = list(combinations(order, 2))
    ncol = min(3, len(pairs))
    nrow = int(np.ceil(len(pairs) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.2 * ncol, 4.0 * nrow),
                             squeeze=False)
    rows = []
    for k, (a, b) in enumerate(pairs):
        ax = axes[k // ncol, k % ncol]
        p = piv[[a, b]].dropna()
        if not len(p):
            ax.set_visible(False)
            continue
        ax.scatter(p[a], p[b], s=18, alpha=0.65, color="#7f4fa0")
        hi = max(p[a].max(), p[b].max()) * 1.05
        ax.plot([0, hi], [0, hi], color="0.5", lw=1.2, ls="--")
        ax.set_xlabel(a, fontsize=9)
        ax.set_ylabel(b, fontsize=9)
        ratio = float((p[b] / p[a].replace(0, np.nan)).median())
        r = float(p[a].corr(p[b], method="spearman"))
        ax.set_title(f"{b}/{a} = {ratio:.2f}   rho {r:+.2f}   n={len(p)}",
                     fontsize=9)
        ax.grid(alpha=0.25)
        rows.append(dict(a=a, b=b, n=len(p), ratio=ratio, rho=r))
    for k in range(len(pairs), nrow * ncol):
        axes[k // ncol, k % ncol].set_visible(False)
    fig.suptitle("Every sorter pair on the same sessions. A pair on the "
                 "dashed line agrees on how many units are there.",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return pd.DataFrame(rows)


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    d = load()
    ok = d[d.error.isna()] if "error" in d else d

    banner("1. Coverage and success")
    print(d.groupby("sorter").agg(
        attempted=("stem", "size"),
        succeeded=("error", lambda s: int(s.isna().sum())),
        median_units=("n_units", "median"),
        median_seconds=("seconds", "median")).to_string())
    print()
    print(ok.groupby(["subject", "array"]).agg(
        sessions=("stem", "nunique"), first=("date", "min"),
        last=("date", "max")).to_string())
    if "error" in d and d.error.notna().any():
        print("\n  failure modes:")
        print(d[d.error.notna()].error.astype(str).str.slice(0, 60)
              .value_counts().head(5).to_string())

    banner("2. Unit counts")
    fig_counts(ok, FIG / "M1_counts.png")

    banner("3. Method spread")
    sp = fig_spread(ok, FIG / "M2_spread.png")
    print(sp.round(3).to_string(index=False))

    banner("4. Recovery of the NEV's own detection")
    fig_recovery(ok, FIG / "M3_recovery.png")
    print(ok.groupby("sorter")[["frac_nev_recovered",
                                "chance_nev_recovered"]].median()
          .round(3).to_string())

    banner("5. Pairwise")
    ag = fig_agreement(ok, FIG / "M4_agreement.png")
    print(ag.round(3).to_string(index=False))

    print("\n  wrote 4 figures to figures/sorters/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

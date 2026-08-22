"""Five clustering methods at three timepoints, across three animals.

`scratch_rocky_deepdive.py` re-clusters every electrode of a session five ways
and applies the noise gate and UnitRefine to each cluster. It was Rocky-only;
it now takes `--subject`. This collects the results.

The question it answers is not "which method is right" — there is no ground
truth here — but **how much of a longitudinal trend is the array and how much
is the method**. The answer differs sharply between animals, and one specific
disagreement is worth more than the aggregate.

    D1_trajectory   gate-passing units per method at each timepoint
    D2_divergence   does method disagreement grow as an array dies? (no)

Run from repo root:

    uv run python notebooks/scratch_deepdive_compare.py

See:
- docs/notes/snippet_sorting.md
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
DERIVED = REPO / "data" / "derived"
FIG = REPO / "figures" / "deepdive"

METHODS = ["isosplit", "gmm_bic", "hdbscan", "kmeans_sil", "ofs"]
METHOD_COLOR = {"isosplit": "#1f77b4", "gmm_bic": "#ff7f0e",
                "hdbscan": "#2ca02c", "kmeans_sil": "#d62728",
                "ofs": "#7f7f7f"}

# Transcribed from the three deep-dive runs. Re-deriving these means
# re-clustering 96 electrodes x 5 methods x 2 arrays x 3 timepoints per
# animal, which is minutes of compute for numbers that do not change; the
# figure regenerates from here instead.
TRAJECTORY = [
    # subject, array, tag, date, isosplit, gmm_bic, hdbscan, kmeans_sil, ofs
    ("Nigel", "Anterior", "T1", "2023-01-24", 0, 0, 0, 0, 0),
    ("Nigel", "Posterior", "T1", "2023-01-24", 47, 48, 93, 30, 117),
    ("Nigel", "Anterior", "T2", "2023-12-15", 62, 152, 69, 84, 71),
    ("Nigel", "Posterior", "T2", "2023-12-15", 22, 54, 28, 28, 22),
    ("Nigel", "Anterior", "T3", "2024-10-28", 7, 30, 7, 58, 7),
    ("Nigel", "Posterior", "T3", "2024-10-28", 0, 1, 0, 27, 0),
    ("Fisk", "SN1498", "T1", "2023-06-05", 39, 60, 46, 43, 27),
    ("Fisk", "SN1504", "T1", "2023-06-05", 77, 95, 91, 81, 50),
    ("Fisk", "SN1498", "T2", "2024-04-10", 96, 125, 112, 74, 63),
    ("Fisk", "SN1504", "T2", "2024-04-10", 95, 194, 121, 121, 104),
    ("Fisk", "SN1498", "T3", "2025-05-07", 108, 169, 119, 126, 93),
    ("Fisk", "SN1504", "T3", "2025-05-07", 137, 255, 162, 145, 132),
]


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def trajectory() -> pd.DataFrame:
    df = pd.DataFrame(TRAJECTORY, columns=["subject", "array", "tag", "date",
                                           *METHODS])
    df["date"] = pd.to_datetime(df.date)
    return df


def rocky_cells() -> pd.DataFrame:
    """Rocky's five-method counts per session, from the full methods pass.

    41 dates, 23% of its event corpus, but representative: median cohort yield
    is 0.260 units per electrode in this sample against 0.271 outside it, and
    it reaches down to 2 gate-passing units. That matters, because it is the
    only sample large enough to test a claim about method disagreement.
    """
    p = DERIVED / "rocky" / "methods_long.parquet"
    if not p.exists():
        return pd.DataFrame()
    d = pd.read_parquet(p)
    g = (d[d.pass_gate].groupby(["date", "array", "method"]).size()
         .unstack("method").reindex(columns=METHODS).fillna(0).reset_index())
    g["date"] = pd.to_datetime(g.date)
    g["subject"] = "Rocky"
    return g


# %%
def fig_trajectory(t: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Yield per method over each implant's life.

    Every method has to move the same way for a trend to be about the array
    rather than about the clustering. On Fisk they do; on Nigel they do until
    the array dies and then one of them does not.
    """
    cells = [(s, a) for s in ("Nigel", "Fisk")
             for a in sorted(t[t.subject == s].array.unique())]
    fig, axes = plt.subplots(1, len(cells), figsize=(3.5 * len(cells), 4.2),
                             squeeze=False)
    for ax, (subj, arr) in zip(axes[0], cells, strict=True):
        g = t[(t.subject == subj) & (t.array == arr)].sort_values("date")
        for m in METHODS:
            ax.plot(range(len(g)), g[m], "o-", ms=6, lw=1.6,
                    color=METHOD_COLOR[m], label=m)
        ax.set_xticks(range(len(g)))
        ax.set_xticklabels([f"{r.tag}\n{r.date:%Y-%m}" for r in
                            g.itertuples()], fontsize=8)
        ax.set_ylabel("gate-passing units")
        ax.set_title(f"{subj} · {arr}", fontsize=10)
        ax.grid(alpha=0.25)
    axes[0][0].legend(fontsize=7.5)

    fig.suptitle("Five clustering methods over two years — Nigel collapses, "
                 "Fisk climbs", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)

    t = t.copy()
    t["median"] = t[METHODS].median(axis=1)
    t["min"] = t[METHODS].min(axis=1)
    t["max"] = t[METHODS].max(axis=1)
    return t[["subject", "array", "tag", "date", *METHODS, "min", "median",
              "max"]]


# %%
def fig_divergence(rk: pd.DataFrame, t: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Does method disagreement grow as an array dies? No — it is flat.

    The hypothesis came from one Nigel cell where four methods report 0 or 1
    unit and `kmeans_sil` reports 27. Tested against 60 Rocky session-array
    cells spanning 2017 to 2023 and reaching down to 2 units, it fails.

    **The statistic matters more than the answer here.** `max/min` is the
    obvious spread measure and it is undefined whenever a method reports zero
    — which happens in exactly the 7 dying cells the hypothesis is about.
    Dropping them leaves `max/min` rising with yield (rho +0.44, p=0.001),
    which is a censoring artefact, not a result. The coefficient of variation
    across the five counts is defined whenever their mean exceeds zero, keeps
    all 60 cells, and says there is **no relationship at all**: rho -0.02,
    p=0.89, CV sitting near 0.5-0.6 across the whole yield range.

    So relative disagreement between methods is a constant of the pipeline,
    not a function of how healthy the array is. Rocky never produces the Nigel
    pattern either: zero of 60 cells have one method at 0 while another
    exceeds 10.
    """
    from scipy.stats import spearmanr

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))
    ax = axes[0]
    out_rows = pd.DataFrame()
    if len(rk):
        rk = rk.copy()
        rk["median"] = rk[METHODS].median(axis=1)
        rk["mn"] = rk[METHODS].min(axis=1)
        rk["mean"] = rk[METHODS].mean(axis=1)
        # CV, not max/min: defined even when a method reports zero, which is
        # precisely the case this figure exists to look at
        rk["cv"] = rk[METHODS].std(axis=1) / rk["mean"].replace(0, np.nan)
        fin = rk[rk["mean"] > 0]
        dying = fin[fin.mn == 0]
        ax.scatter(fin["median"], fin.cv, s=28, alpha=0.7, color="#1f77b4",
                   label=f"Rocky (n={len(fin)})")
        ax.scatter(dying["median"], dying.cv, s=70, marker="^",
                   facecolors="none", edgecolors="#1f77b4", lw=1.5,
                   label=f"Rocky, a method at 0 (n={len(dying)})")
        r, p = spearmanr(fin["median"], fin.cv)
        ax.set_title(f"no relationship  (rho {r:+.2f}, p={p:.2f})",
                     fontsize=10)

        q = pd.qcut(rk["median"], 4,
                    labels=["lowest", "low", "high", "highest"],
                    duplicates="drop")
        out_rows = rk.groupby(q).agg(
            cells=("median", "size"), median_yield=("median", "median"),
            cv=("cv", "median"),
            a_method_at_zero=("mn", lambda x: int((x == 0).sum())),
            kmeans_sil=("kmeans_sil", "median"),
            isosplit=("isosplit", "median")).round(3).reset_index()

    tt = t.copy()
    tt["median"] = tt[METHODS].median(axis=1)
    tt["mn"] = tt[METHODS].min(axis=1)
    tt["mean"] = tt[METHODS].mean(axis=1)
    tt["cv"] = tt[METHODS].std(axis=1) / tt["mean"].replace(0, np.nan)
    for subj, col, mk in (("Nigel", "#2ca02c", "s"), ("Fisk", "#d62728", "D")):
        g = tt[(tt.subject == subj) & (tt["mean"] > 0)]
        ax.scatter(g["median"], g.cv, s=60, marker=mk, color=col,
                   edgecolors="k", lw=0.6, label=subj)
    ax.set_xlabel("median gate-passing units across the five methods")
    ax.set_ylabel("coefficient of variation across methods")
    ax.legend(fontsize=7.5)
    ax.grid(alpha=0.25)

    # the specific disagreement that prompted the question
    ax = axes[1]
    row = t[(t.subject == "Nigel") & (t.array == "Posterior")
            & (t.tag == "T3")]
    if len(row):
        vals = [float(row.iloc[0][m]) for m in METHODS]
        ax.bar(range(len(METHODS)), vals,
               color=[METHOD_COLOR[m] for m in METHODS])
        for i, v in enumerate(vals):
            ax.text(i, v + 0.6, f"{v:.0f}", ha="center", fontsize=10)
        ax.set_xticks(range(len(METHODS)))
        ax.set_xticklabels(METHODS, fontsize=9, rotation=15, ha="right")
        ax.set_ylabel("gate-passing units")
        ax.set_title("Nigel Posterior, 2024-10-28 — four methods say the "
                     "array is dead", fontsize=10)
        ax.grid(alpha=0.25, axis="y")

    fig.suptitle("Relative method disagreement is constant across the yield "
                 "range — but one method can still stand alone", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out_rows


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    t = trajectory()
    rk = rocky_cells()

    banner("1. Trajectory, per method")
    tab = fig_trajectory(t, FIG / "D1_trajectory.png")
    print(tab.to_string(index=False))

    banner("2. Fold change from first to last timepoint")
    for (s, a), g in t.groupby(["subject", "array"]):
        g = g.sort_values("date")
        first, last = g.iloc[0], g.iloc[-1]
        fc = [(last[m] / first[m]) if first[m] else np.nan for m in METHODS]
        lo = np.nanmin(fc) if np.isfinite(fc).any() else np.nan
        hi = np.nanmax(fc) if np.isfinite(fc).any() else np.nan
        print(f"  {s:6s} {a:10s}  " +
              "  ".join(f"{m}={v:.2f}x" if np.isfinite(v) else f"{m}=n/a"
                        for m, v in zip(METHODS, fc, strict=True)) +
              (f"   [range {lo:.2f}-{hi:.2f}]" if np.isfinite(lo) else ""))

    banner("3. Does disagreement grow as an array dies?")
    q = fig_divergence(rk, t, FIG / "D2_divergence.png")
    if len(q):
        print(q.to_string(index=False))
    print("\n  Rocky cells where one method is 0 and another exceeds 10:",
          int(((rk[METHODS].min(axis=1) == 0)
               & (rk[METHODS].max(axis=1) > 10)).sum()) if len(rk) else "n/a",
          f"of {len(rk)}")

    print("\n  wrote 2 figures to figures/deepdive/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

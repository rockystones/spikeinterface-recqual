"""Figures for the LFP layer, and the acquisition fault it found.

`scratch_lfp_quality.py` derives LFP from Fisk's `.ns6` by filtering and
decimating, and measures three things the spike layer structurally cannot see
(see docs/notes/lfp_quality.md). The headline result is not a longitudinal
trend: it is a **dateable 60 Hz grounding fault in Feb-Mar 2025** that a
degradation analysis without this layer would have scored as array death.

    L1_coverage    which streams carry LFP at all, and why most do not
    L2_line        60 Hz contamination over time, per array
    L3_episode     the Feb-Mar 2025 fault, and what it did to the spike layer
    L4_longitudinal band composition and cross-channel correlation over time

Run from repo root:

    uv run python notebooks/scratch_lfp_figures.py

See:
- docs/notes/lfp_quality.md
- docs/notes/cohort_longitudinal.md
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
LFP = REPO / "data" / "derived" / "lfp" / "lfp_quality.parquet"
COHORT = REPO / "data" / "derived" / "cohort" / "cohort_sessions.parquet"
FIG = REPO / "figures" / "lfp"

# Above this fraction of total LFP power at 60 Hz, the session is treated as
# contaminated. Chosen from the data, not from convention: 113 sessions before
# the fault never exceed 0.045, so 0.05 separates cleanly rather than cutting
# through a distribution.
LINE_THRESHOLD = 0.05
ARRAY_COLOR = {"Lateral": "#d62728", "Medial": "#1f77b4"}


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    """All LFP rows, and the subset joined to the spike layer."""
    d = pd.read_parquet(LFP)
    d["date"] = pd.to_datetime(d.date)
    ok = d[d.error.isna()].copy()
    # The cohort table names arrays by serial (SN1498); the LFP layer names
    # them by anatomy (Lateral). The last four digits of the serial are the
    # join key that survives both.
    ok["arr_key"] = "SN" + ok.serial.astype(str).str[-4:]
    co = pd.read_parquet(COHORT)
    co["date"] = pd.to_datetime(co.date)
    joined = ok.merge(co, left_on=["subject", "arr_key", "date"],
                      right_on=["subject", "array", "date"], how="inner",
                      suffixes=("", "_sp"))
    joined["contaminated"] = joined.line_frac_med > LINE_THRESHOLD
    return d, joined


# %%
def fig_coverage(d: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Why 638 of 766 streams produced nothing.

    This is the figure that justifies the layer's scope. Every bar except the
    first is a stream whose suffix says LFP or broadband and whose header says
    otherwise.
    """
    reason = d.error.fillna("LFP derived").astype(str)
    # collapse the band rejections to their corner, keeping the count
    reason = reason.str.replace(r"^no LFP in this stream: high-pass at ",
                                "high-passed at ", regex=True)
    reason = reason.str.replace(r"^band unknown.*", "band unreadable",
                                regex=True)
    counts = reason.value_counts()

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))
    ax = axes[0]
    colors = ["#2ca02c" if k == "LFP derived" else "#bbbbbb"
              for k in counts.index]
    ax.barh(range(len(counts)), counts.values, color=colors)
    ax.set_yticks(range(len(counts)))
    ax.set_yticklabels(counts.index, fontsize=9)
    ax.invert_yaxis()
    for i, v in enumerate(counts.values):
        ax.text(v + 6, i, str(v), va="center", fontsize=9)
    ax.set_xlabel("streams")
    ax.set_xlim(0, counts.max() * 1.15)
    ax.set_title("the suffix does not tell you the band", fontsize=10)
    ax.grid(alpha=0.25, axis="x")

    # per subject: how much of each subject's data is reachable
    ax = axes[1]
    tab = (d.assign(has_lfp=d.error.isna())
             .groupby(["subject", "has_lfp"]).size().unstack(fill_value=0))
    for col in (False, True):
        if col not in tab:
            tab[col] = 0
    idx = np.arange(len(tab))
    ax.bar(idx, tab[True], color="#2ca02c", label="LFP derived")
    ax.bar(idx, tab[False], bottom=tab[True], color="#bbbbbb",
           label="no LFP in the stream")
    ax.set_xticks(idx)
    ax.set_xticklabels(tab.index, fontsize=9)
    ax.set_ylabel("streams")
    ax.set_title("only Fisk has a Blackrock LFP source", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25, axis="y")

    fig.suptitle("LFP coverage — 638 of 766 streams carry no LFP at all",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return pd.DataFrame(dict(outcome=counts.index, streams=counts.values))


# %%
def fig_line(ok: pd.DataFrame, out: Path) -> None:
    """60 Hz power over time. The fault is a step, not a trend."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4),
                             gridspec_kw={"width_ratios": [2.2, 1]})
    ax = axes[0]
    for arr, g in ok.groupby("array"):
        g = g.sort_values("date")
        ax.plot(g.date, g.line_frac_med, "o-", ms=4, lw=0.9, alpha=0.85,
                color=ARRAY_COLOR.get(arr, "0.4"), label=arr)
    ax.axhline(LINE_THRESHOLD, color="k", ls="--", lw=1)
    ax.text(ok.date.min(), LINE_THRESHOLD * 1.15, "5% threshold", fontsize=8)
    ax.set_yscale("log")
    ax.set_ylabel("60 Hz power / total LFP power")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.set_title("two years quiet, then four contaminated sessions",
                 fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    for lab in ax.get_xticklabels():
        lab.set_rotation(30)
        lab.set_ha("right")

    # the distribution, so the threshold is visibly not cutting a continuum
    ax = axes[1]
    bins = np.logspace(-4, 0, 40)
    for arr, g in ok.groupby("array"):
        ax.hist(g.line_frac_med, bins=bins, alpha=0.6,
                color=ARRAY_COLOR.get(arr, "0.4"), label=arr)
    ax.axvline(LINE_THRESHOLD, color="k", ls="--", lw=1)
    ax.set_xscale("log")
    ax.set_xlabel("60 Hz power fraction")
    ax.set_ylabel("sessions")
    ax.set_title("bimodal — the threshold sits in the gap", fontsize=10)
    ax.grid(alpha=0.25)

    fig.suptitle("Mains contamination, which no spike-layer metric can see",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)


# %%
def fig_episode(j: pd.DataFrame, out: Path) -> pd.DataFrame:
    """What the fault did to the spike layer, and that it fully recovered.

    Two independent arguments that this is the rig and not the tissue.

    **Dose-response.** Same rig, same days, two arrays: the one carrying
    0.64-0.76 line fraction drops from 0.90 to 0.08 units per electrode, the
    one at 0.11-0.16 from 1.14 to 0.60.

    **Interleaving.** A single clean session on 2025-03-05 sits between two
    contaminated ones and reads 0.84 units per electrode at 9.6 uV noise --
    baseline on both arrays. Nothing physical recovers and re-fails weekly.
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))

    # 1. dose-response, every session
    ax = axes[0]
    for arr, g in j.groupby("arr_key"):
        ax.scatter(g.line_frac_med, g.noise_med, s=26, alpha=0.75,
                   label=arr, color=ARRAY_COLOR.get(
                       "Lateral" if arr.endswith("1498") else "Medial", "0.4"))
    ax.set_xscale("log")
    ax.set_xlabel("60 Hz power fraction")
    ax.set_ylabel("spike-band noise floor (uV)")
    ax.axvline(LINE_THRESHOLD, color="k", ls="--", lw=1)
    ax.set_title("the fault raises the noise floor 3x", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    ax = axes[1]
    for arr, g in j.groupby("arr_key"):
        ax.scatter(g.line_frac_med, g.units_per_electrode, s=26, alpha=0.75,
                   label=arr, color=ARRAY_COLOR.get(
                       "Lateral" if arr.endswith("1498") else "Medial", "0.4"))
    ax.set_xscale("log")
    ax.set_xlabel("60 Hz power fraction")
    ax.set_ylabel("units per electrode")
    ax.axvline(LINE_THRESHOLD, color="k", ls="--", lw=1)
    ax.set_title("and takes the yield with it", fontsize=10)
    ax.grid(alpha=0.25)

    # 2. the episode itself, alternating session to session
    ax = axes[2]
    w = j[j.date >= "2024-12-15"].sort_values("date")
    for arr, g in w.groupby("arr_key"):
        c = ARRAY_COLOR.get("Lateral" if arr.endswith("1498") else "Medial",
                            "0.4")
        ax.plot(g.date, g.units_per_electrode, "o-", ms=5, lw=1.1, color=c,
                label=arr)
        bad = g[g.contaminated]
        ax.scatter(bad.date, bad.units_per_electrode, s=150, facecolors="none",
                   edgecolors="k", lw=1.4, zorder=5)
    ax.set_ylabel("units per electrode")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.set_title("circled = contaminated; Mar 05 sits clean between two",
                 fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    for lab in ax.get_xticklabels():
        lab.set_rotation(30)
        lab.set_ha("right")

    fig.suptitle("The Feb–Mar 2025 grounding fault — an acquisition "
                 "problem that reads as array death", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)

    cols = [c for c in ("noise_med", "n_candidates", "pass_fraction",
                        "n_units", "amp_med", "snr_med", "units_per_electrode")
            if c in j]
    return j.groupby("contaminated")[cols].median().round(3).reset_index()


# %%
def fig_longitudinal(ok: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Band composition and cross-channel correlation over the implant's life.

    Correlation is the one with no spike-layer equivalent: a bridging or
    common-reference fault drives it toward 1, and nothing in the spike band
    would show it.
    """
    from scipy.stats import spearmanr

    bands = [c for c in ok.columns if c.endswith("_frac")
             and not c.startswith("line")]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))

    ax = axes[0]
    for arr, g in ok.groupby("array"):
        g = g.sort_values("date")
        ax.plot(g.date, g.corr_med, "o-", ms=4, lw=0.9, alpha=0.85,
                color=ARRAY_COLOR.get(arr, "0.4"), label=arr)
    ax.set_ylabel("median cross-channel correlation")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.set_title("rises on Lateral — no spike-layer equivalent",
                 fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    ax = axes[1]
    for arr, g in ok.groupby("array"):
        g = g.sort_values("date")
        ax.plot(g.date, g.rms_uv, "o-", ms=4, lw=0.9, alpha=0.85,
                color=ARRAY_COLOR.get(arr, "0.4"), label=arr)
    ax.set_ylabel("LFP rms (uV)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.set_title("amplitude", fontsize=10)
    ax.grid(alpha=0.25)

    ax = axes[2]
    med = ok.groupby("array")[bands].median()
    idx = np.arange(len(bands))
    width = 0.38
    for k, (arr, row) in enumerate(med.iterrows()):
        ax.bar(idx + k * width - width / 2, row.values, width,
               color=ARRAY_COLOR.get(arr, "0.4"), label=arr)
    ax.set_xticks(idx)
    ax.set_xticklabels([b.replace("_frac", "") for b in bands], fontsize=9)
    ax.set_ylabel("fraction of total power")
    ax.set_title("band composition", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25, axis="y")

    for a in axes[:2]:
        for lab in a.get_xticklabels():
            lab.set_rotation(30)
            lab.set_ha("right")

    fig.suptitle("Fisk LFP over two years", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)

    # Trends are computed on CLEAN sessions only: the fault is an acquisition
    # artefact and leaving it in would let four sessions write the slope.
    rows = []
    clean = ok[ok.line_frac_med <= LINE_THRESHOLD]
    for arr, g in clean.groupby("array"):
        x = g.date.map(pd.Timestamp.toordinal)
        for m in ("rms_uv", "corr_med", "line_frac_med", "gamma_frac",
                  "delta_frac"):
            v = g.dropna(subset=[m])
            if len(v) < 10:
                continue
            r, p = spearmanr(v.date.map(pd.Timestamp.toordinal), v[m])
            rows.append(dict(array=arr, n=len(v), metric=m,
                             rho=round(float(r), 3), p=float(p)))
        del x
    return pd.DataFrame(rows)


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    d, j = load()
    ok = d[d.error.isna()].copy()

    banner("1. Coverage")
    cov = fig_coverage(d, FIG / "L1_coverage.png")
    print(cov.to_string(index=False))

    banner("2. Mains contamination")
    fig_line(ok, FIG / "L2_line.png")
    clean = ok[ok.line_frac_med <= LINE_THRESHOLD]
    print(f"  clean sessions      : {len(clean)}  "
          f"median {clean.line_frac_med.median():.5f}  "
          f"max {clean.line_frac_med.max():.5f}")
    bad = ok[ok.line_frac_med > LINE_THRESHOLD]
    print(f"  contaminated        : {len(bad)}  "
          f"median {bad.line_frac_med.median():.4f}  "
          f"max {bad.line_frac_med.max():.4f}")
    print(f"  dates               : "
          f"{bad.date.min().date()} to {bad.date.max().date()}")

    banner("3. What the fault did to the spike layer")
    tab = fig_episode(j, FIG / "L3_episode.png")
    print(tab.to_string(index=False))
    from scipy.stats import mannwhitneyu
    a, b = j[j.contaminated], j[~j.contaminated]
    print(f"\n  n = {len(a)} contaminated, {len(b)} clean")
    for c in ("noise_med", "n_units", "pass_fraction", "units_per_electrode",
              "amp_med", "snr_med"):
        if c not in j:
            continue
        x, y = a[c].dropna(), b[c].dropna()
        if len(x) < 3 or len(y) < 3:
            continue
        _, p = mannwhitneyu(x, y)
        print(f"    {c:22s} {x.median():9.3f} vs {y.median():9.3f}  p={p:.3g}")

    banner("4. Longitudinal, on clean sessions only")
    tr = fig_longitudinal(ok, FIG / "L4_longitudinal.png")
    print(tr.to_string(index=False))

    print("\n  wrote 4 figures to figures/lfp/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

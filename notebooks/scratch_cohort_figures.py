"""Longitudinal figures for every subject, from one shared definition.

Rocky's figures were written by a Rocky-specific script over several sessions
and have drifted: some predate the 2023-08-11 date repair, and none of them
carry the measurement floor from S09. This regenerates the longitudinal set for
**all** subjects from `cohort_sessions.parquet`, so a Nigel panel and a Rocky
panel are the same figure with different data rather than two scripts that
happen to look alike.

Figures, per subject:

    C1_yield        units per electrode over time, both arrays, with the S09
                    operator floor drawn as a band so a reader can see at a
                    glance which movements are larger than the measurement
    C2_metrics      the six-metric grid: yield, coverage, amplitude, SNR,
                    noise floor, gate pass fraction
    C3_screen       what the acquisition screen removed and why
    C4_snr_vs_yield the headline result -- SNR flat while yield falls

Plus one cross-subject figure:

    C0_cohort       every array-implant on one axis, aligned at its own first
                    session

Run from repo root:

    uv run python notebooks/scratch_cohort_figures.py

See:
- docs/notes/cohort_longitudinal.md
- docs/notes/measurement_floor.md
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
sys.path.insert(0, str(REPO / "notebooks"))

SESSIONS = REPO / "data" / "derived" / "cohort" / "cohort_sessions.parquet"
TRENDS = REPO / "data" / "derived" / "cohort" / "cohort_trends.parquet"
FLOOR = REPO / "data" / "derived" / "floor" / "wf_pairs.parquet"
FIG_ROOT = REPO / "figures"

# Metric -> (label, whether a fractional floor band is meaningful).
PANELS = [
    ("units_per_electrode", "units / electrode", True),
    ("elec_coverage", "electrodes with units (frac)", True),
    ("amp_med", "median unit amplitude (uV)", True),
    ("snr_med", "median unit SNR", True),
    ("noise_med", "noise floor (uV)", False),
    ("pass_fraction", "gate pass fraction", False),
]
ARRAY_COLOR = {0: "#1f77b4", 1: "#d62728", 2: "#2ca02c", 3: "#9467bd"}
# Consecutive sessions further apart than this are a recording gap, not a
# measurement. Rocky has a two-year hiatus in 2020-21; joining across it
# draws a flat line that reads as a stable plateau.
GAP_DAYS = 120


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === The measurement floor, as a drawable band ===
def operator_floor() -> dict[str, float]:
    """Median relative operator disagreement per metric, gated (S09).

    Returned as a fraction, so a band of +/- floor/2 around a local level shows
    how much of a movement is attributable to who did the sorting.
    """
    if not FLOOR.exists():
        return {}
    p = pd.read_parquet(FLOOR)
    op = p[p.kind == "operator"]
    # S09 measured counts, not rates. A per-electrode rate is the count over a
    # constant, so its *relative* floor is the count's -- the denominator
    # cancels. Same for coverage against electrodes-with-units.
    alias = {"units_per_electrode": "n_units",
             "elec_coverage": "n_elec_with_units"}
    out = {}
    for m, _, _ in PANELS:
        col = f"rel_{alias.get(m, m)}_gated"
        if col in op.columns:
            v = op[col].median()
            # A zero floor means "no measurable disagreement"; drawing a
            # zero-width band just adds a misleading line.
            if np.isfinite(v) and v > 0:
                out[m] = float(v)
    return out


def break_gaps(dates: pd.Series, y: pd.Series) -> pd.Series:
    """Blank the line across recording gaps, leaving the markers alone.

    Rocky has a two-year hiatus in 2020-21 and Nigel a terminal session eleven
    months after the previous one. Joining across those draws a flat segment
    that reads as a stable plateau. Blanking `y` outright also *hides* the
    isolated session, so this is used for the line only and the markers are
    drawn from the untouched series.
    """
    out = y.copy()
    out[dates.diff().dt.days > GAP_DAYS] = np.nan
    return out


def draw_floor(ax, y: pd.Series, floor: float | None) -> None:
    """Shade +/- half the operator floor around the series' own median."""
    if not floor or not len(y.dropna()):
        return
    mid = float(y.median())
    half = mid * floor / 2
    ax.axhspan(mid - half, mid + half, color="0.85", zorder=0,
               label=f"operator floor ({floor:.0%})")


# %%
# === Per-subject figures ===
def fig_yield(s: pd.DataFrame, subject: str, implant: str, floor: dict,
              out: Path) -> None:
    g = s[(s.subject == subject) & (s.implant == implant)]
    arrays = sorted(g.array.dropna().unique())
    fig, ax = plt.subplots(figsize=(11, 4.2))
    draw_floor(ax, g.units_per_electrode,
               floor.get("units_per_electrode"))
    for i, arr in enumerate(arrays):
        a = g[g.array == arr].sort_values("date")
        keep = a[~a.high_noise].copy()
        drop = a[a.high_noise]
        y = keep.units_per_electrode
        ax.plot(keep.date, break_gaps(keep.date, y), "-", lw=1.1,
                color=ARRAY_COLOR[i % 4], alpha=0.85)
        ax.plot(keep.date, y, "o", ms=3.2,
                color=ARRAY_COLOR[i % 4], label=arr, alpha=0.85)
        if len(drop):
            ax.plot(drop.date, drop.units_per_electrode, "x", ms=6,
                    color=ARRAY_COLOR[i % 4], alpha=0.6,
                    label=f"{arr}: high-noise, screened")
    ax.set_ylabel("units / electrode")
    ax.set_title(f"{subject} {implant} — gate-passing yield "
                 f"(Plexon -01, acquisition-screened)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, ncol=3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_metrics(s: pd.DataFrame, subject: str, implant: str, floor: dict,
                out: Path) -> None:
    g = s[(s.subject == subject) & (s.implant == implant) & (~s.high_noise)]
    arrays = sorted(g.array.dropna().unique())
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharex=True)
    for ax, (metric, label, banded) in zip(axes.ravel(), PANELS, strict=True):
        if metric not in g.columns:
            ax.set_visible(False)
            continue
        draw_floor(ax, g[metric], floor.get(metric) if banded else None)
        for i, arr in enumerate(arrays):
            a = g[g.array == arr].sort_values("date")
            ax.plot(a.date, break_gaps(a.date, a[metric]), "-", lw=0.9,
                    color=ARRAY_COLOR[i % 4], alpha=0.85)
            ax.plot(a.date, a[metric], "o", ms=2.6,
                    color=ARRAY_COLOR[i % 4], label=arr, alpha=0.85)
        ax.set_ylabel(label, fontsize=9)
        ax.grid(alpha=0.25)
        ax.tick_params(labelsize=8)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle(f"{subject} {implant} — longitudinal metrics; grey band is "
                 f"the S09 operator floor for that metric", fontsize=11)
    for ax in axes[-1]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_screen(s: pd.DataFrame, subject: str, implant: str, out: Path) -> None:
    """What the acquisition screen removed, and that it is not outcome-based."""
    g = s[(s.subject == subject) & (s.implant == implant)]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    for i, arr in enumerate(sorted(g.array.dropna().unique())):
        a = g[g.array == arr].sort_values("date")
        ax.plot(a.date, break_gaps(a.date, a.noise_med), "-", lw=0.9,
                color=ARRAY_COLOR[i % 4], alpha=0.85)
        ax.plot(a.date, a.noise_med, "o", ms=2.6,
                color=ARRAY_COLOR[i % 4], label=arr, alpha=0.85)
        ax.axhline(2 * a.noise_baseline.iloc[0], ls="--", lw=1,
                   color=ARRAY_COLOR[i % 4], alpha=0.7)
    ax.set_ylabel("session noise floor (uV)")
    ax.set_title("screen threshold = 2x that array's median")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[1]
    ax.scatter(g[~g.high_noise].noise_med, g[~g.high_noise].units_per_electrode,
               s=12, alpha=0.65, label="kept")
    ax.scatter(g[g.high_noise].noise_med, g[g.high_noise].units_per_electrode,
               s=34, marker="x", color="crimson", label="screened out")
    ax.set_xlabel("session noise floor (uV)")
    ax.set_ylabel("units / electrode")
    ax.set_title("the screen cuts on the x axis, never the y")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.suptitle(f"{subject} {implant} — acquisition screen", fontsize=11)
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_snr_vs_yield(s: pd.DataFrame, tr: pd.DataFrame, out: Path) -> None:
    """The cohort headline: yield falls, SNR does not."""
    d = tr[(tr.scope == "screened")
           & (tr.metric.isin(["units_per_electrode", "snr_med"]))]
    piv = d.pivot_table(index=["subject", "implant", "array"],
                        columns="metric", values="rho")
    piv = piv.dropna()
    fig, ax = plt.subplots(figsize=(7.2, 6))
    for (sub, imp, arr), row in piv.iterrows():
        ax.scatter(row["units_per_electrode"], row["snr_med"], s=70,
                   alpha=0.85)
        ax.annotate(f"{sub} {imp}\n{arr}",
                    (row["units_per_electrode"], row["snr_med"]),
                    fontsize=7.5, xytext=(6, -3), textcoords="offset points")
    ax.axhline(0, color="0.5", lw=1)
    ax.axvline(0, color="0.5", lw=1)
    ax.set_xlabel("trend in units per electrode  (Spearman rho)")
    ax.set_ylabel("trend in median unit SNR  (Spearman rho)")
    ax.set_title("Yield falls; SNR does not.\n"
                 "Units are lost, survivors are not degraded.", fontsize=11)
    ax.grid(alpha=0.25)
    ax.set_xlim(-1, 0.6)
    ax.set_ylim(-1, 0.6)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_cohort(s: pd.DataFrame, out: Path) -> None:
    """Every array-implant on one axis, aligned at its own first session."""
    fig, ax = plt.subplots(figsize=(11, 5))
    g = s[~s.high_noise]
    for (sub, imp, arr), a in g.groupby(["subject", "implant", "array"]):
        a = a.sort_values("days_since_first")
        if len(a) < 8:
            continue
        # Rolling median: session-to-session scatter would bury eight series.
        y = a.units_per_electrode.rolling(5, min_periods=2, center=True).median()
        x = a.days_since_first / 365.25
        # Break the line across recording gaps. Rocky has a two-year hiatus in
        # 2020-21 and matplotlib would otherwise draw a straight segment across
        # it that reads as a stable plateau.
        y = y.copy()
        y[a.days_since_first.diff() > GAP_DAYS] = np.nan
        ax.plot(x, y, lw=1.6, label=f"{sub} {imp} {arr}", alpha=0.9)
        # Isolated sessions after a gap would otherwise vanish with the line.
        lone = a.days_since_first.diff() > GAP_DAYS
        if lone.any():
            ax.plot(x[lone], a.units_per_electrode[lone], ".", ms=6,
                    color=ax.lines[-1].get_color(), alpha=0.9)
    ax.set_xlabel("years since that array's first recording")
    ax.set_ylabel("units / electrode  (rolling median of 5)")
    ax.set_title("Eight array-implants, three animals, one method.\n"
                 "Aligned at first recording -- only Rocky implant 2 has a "
                 "surgery date, so this is not implant age.", fontsize=10.5)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main() -> int:
    if not SESSIONS.exists():
        print("  run scratch_cohort_longitudinal.py first")
        return 1
    s = pd.read_parquet(SESSIONS)
    if "error" in s:
        s = s[s.error.isna()]
    tr = pd.read_parquet(TRENDS) if TRENDS.exists() else pd.DataFrame()
    floor = operator_floor()

    banner("Cohort figures")
    print(f"  sessions: {len(s)}   subjects: {sorted(s.subject.unique())}")
    print(f"  operator floor per metric (S09): "
          f"{ {k: round(v, 3) for k, v in floor.items()} }")

    made: list[Path] = []
    for (sub, imp), _ in s.groupby(["subject", "implant"]):
        d = FIG_ROOT / sub.lower() / "cohort"
        d.mkdir(parents=True, exist_ok=True)
        tag = f"{sub}_{imp}"
        jobs = [
            (f"C1_yield_{tag}.png", fig_yield, (s, sub, imp, floor)),
            (f"C2_metrics_{tag}.png", fig_metrics, (s, sub, imp, floor)),
            (f"C3_screen_{tag}.png", fig_screen, (s, sub, imp)),
        ]
        for name, fn, args in jobs:
            p = d / name
            try:
                fn(*args, p)
                made.append(p)
            except Exception as exc:  # noqa: BLE001
                print(f"    FAILED {name}: {type(exc).__name__}: {exc}")

    shared = FIG_ROOT / "cohort"
    shared.mkdir(parents=True, exist_ok=True)
    if len(tr):
        p = shared / "C4_snr_vs_yield.png"
        fig_snr_vs_yield(s, tr, p)
        made.append(p)
    p = shared / "C0_cohort_overlay.png"
    fig_cohort(s, p)
    made.append(p)

    print(f"\n  wrote {len(made)} figures")
    for p in made:
        print(f"    {p.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Anterior vs posterior longitudinal comparison for the Rocky cohort.

Consumes the re-sort output (`units_long.parquet`) and the impedance table,
and produces the figures that answer the actual question: how does unit yield
and signal quality on the anterior array compare with the posterior array
across the implant lifetime, and where does Plexon OFS diverge from a
gate-controlled re-sort.

Two confounds are carried explicitly rather than averaged away:

- **Headstage.** 2018-2019 contain both Analog and Digital recordings, often
  on overlapping dates. The amplifier chain moves the noise floor, which moves
  the crossing count, which moves unit yield.
- **Session duration.** Sessions range from 180 s to ~2970 s. Counts are never
  compared raw; rates and per-electrode yields are.

Run from repo root:

    uv run python notebooks/scratch_rocky_longitudinal.py [--tol-days 14]

See:
- docs/session_plans/session04_rocky_resort.md
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "data" / "derived" / "rocky"
UNITS_IN = OUT_DIR / "units_long.parquet"
IMPEDANCE_IN = OUT_DIR / "impedance_long.parquet"
FIG_DIR = REPO / "figures" / "rocky"
SESSION_OUT = OUT_DIR / "session_summary.parquet"

ARRAY_COLOR = {"Anterior": "#1f77b4", "Posterior": "#d62728"}
HS_MARKER = {"Digital": "o", "Analog": "^", "none": "s"}
N_ELECTRODES = 96


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# === Aggregation ===
def session_summary(units: pd.DataFrame) -> pd.DataFrame:
    """Collapse per-unit rows to one row per (date, array, headstage, method).

    Parameters
    ----------
    units : pandas.DataFrame
        Long-format unit metrics.

    Returns
    -------
    pandas.DataFrame
        Per-session yield and quality summary. ``n_units`` counts only
        gate-passing units; ``n_candidates`` counts everything proposed, so
        the rejection fraction stays visible.
    """
    u = units[units["method"].isin(["resort", "ofs"])].copy()
    u["pass_gate"] = u["pass_gate"].fillna(False).astype(bool)
    keys = ["date", "array", "headstage", "method"]

    passing = u[u["pass_gate"]]
    agg = passing.groupby(keys).agg(
        n_units=("unit_id", "size"),
        n_electrodes_with_units=("electrode_id", "nunique"),
        median_snr=("snr", "median"),
        median_amp_uv=("amplitude_uv", "median"),
        median_rate_hz=("firing_rate_hz", "median"),
        median_noise_uv=("noise_uv", "median"),
        median_isi_viol=("isi_viol_rate", "median"),
        duration_s=("duration_s", "first"),
    ).reset_index()

    cand = u.groupby(keys).agg(n_candidates=("unit_id", "size")).reset_index()
    out = agg.merge(cand, on=keys, how="outer")
    out["n_units"] = out["n_units"].fillna(0)
    out["units_per_electrode"] = out["n_units"] / N_ELECTRODES
    out["pass_fraction"] = out["n_units"] / out["n_candidates"]
    out["date_dt"] = pd.to_datetime(out["date"])
    return out.sort_values(["date_dt", "array", "method"]).reset_index(drop=True)


# === Figures ===
def fig_yield(sess: pd.DataFrame, out: Path) -> None:
    """Units per electrode over time, anterior vs posterior (re-sort only)."""
    d = sess[sess["method"] == "resort"]
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
    for ax, col, lbl in (
        (axes[0], "units_per_electrode", "units per electrode"),
        (axes[1], "n_electrodes_with_units", "electrodes with >=1 unit (of 96)"),
    ):
        for arr, g in d.groupby("array"):
            g = g.sort_values("date_dt")
            ax.plot(g["date_dt"], g[col], "-", lw=0.8, alpha=0.35,
                    color=ARRAY_COLOR.get(arr, "0.4"))
            for hs, gh in g.groupby("headstage"):
                ax.scatter(gh["date_dt"], gh[col], s=26,
                           marker=HS_MARKER.get(hs, "o"),
                           color=ARRAY_COLOR.get(arr, "0.4"),
                           label=f"{arr} / {hs}", alpha=0.85)
        ax.set_ylabel(lbl)
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=8, ncol=3, loc="upper right")
    axes[1].set_xlabel("session date")
    axes[1].xaxis.set_major_locator(mdates.YearLocator())
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("Rocky: unit yield over implant lifetime (gate-passing re-sort)\n"
                 "marker shape = headstage (o Digital, ^ Analog, s none)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_quality(sess: pd.DataFrame, out: Path) -> None:
    """Median SNR, amplitude and noise floor over time, by array."""
    d = sess[sess["method"] == "resort"]
    fig, axes = plt.subplots(3, 1, figsize=(13, 10), sharex=True)
    for ax, col, lbl in (
        (axes[0], "median_snr", "median unit SNR"),
        (axes[1], "median_amp_uv", "median |trough| (uV)"),
        (axes[2], "median_noise_uv", "electrode noise floor (uV)"),
    ):
        for arr, g in d.groupby("array"):
            g = g.sort_values("date_dt")
            ax.plot(g["date_dt"], g[col], "-o", ms=3.5, lw=0.9,
                    color=ARRAY_COLOR.get(arr, "0.4"), label=arr, alpha=0.85)
        ax.set_ylabel(lbl)
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=9)
    axes[2].set_xlabel("session date")
    axes[2].xaxis.set_major_locator(mdates.YearLocator())
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("Rocky: signal quality over implant lifetime (gate-passing re-sort)",
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_resort_vs_ofs(sess: pd.DataFrame, out: Path) -> None:
    """Where Plexon OFS and the gate-controlled re-sort diverge."""
    piv = sess.pivot_table(index=["date_dt", "array"], columns="method",
                           values=["n_units", "n_candidates"]).reset_index()
    piv.columns = ["_".join([c for c in col if c]).strip("_") for col in piv.columns]

    fig, axes = plt.subplots(3, 1, figsize=(13, 10), sharex=True)

    for arr, g in piv.groupby("array"):
        g = g.sort_values("date_dt")
        c = ARRAY_COLOR.get(arr, "0.4")
        if "n_candidates_ofs" in g:
            axes[0].plot(g["date_dt"], g["n_candidates_ofs"], "--", lw=1.0,
                         color=c, alpha=0.75, label=f"{arr} OFS (all units)")
        if "n_units_resort" in g:
            axes[0].plot(g["date_dt"], g["n_units_resort"], "-", lw=1.4,
                         color=c, label=f"{arr} re-sort (passing)")
        if {"n_units_ofs", "n_candidates_ofs"} <= set(g.columns):
            frac = g["n_units_ofs"] / g["n_candidates_ofs"]
            axes[1].plot(g["date_dt"], frac, "-o", ms=3.5, lw=1.0, color=c, label=arr)
        if {"n_units_resort", "n_candidates_ofs"} <= set(g.columns):
            axes[2].plot(g["date_dt"],
                         g["n_candidates_ofs"] - g["n_units_resort"],
                         "-o", ms=3.5, lw=1.0, color=c, label=arr)

    axes[0].set_ylabel("units per session")
    axes[0].legend(fontsize=8, ncol=2)
    axes[1].set_ylabel("fraction of OFS units\npassing the gate")
    axes[1].axhline(0.5, color="0.6", ls=":", lw=1)
    axes[1].set_ylim(0, 1.02)
    axes[1].legend(fontsize=9)
    axes[2].set_ylabel("OFS units minus\nre-sort passing units")
    axes[2].axhline(0, color="0.6", ls=":", lw=1)
    axes[2].legend(fontsize=9)
    for ax in axes:
        ax.grid(alpha=0.3)
    axes[2].set_xlabel("session date")
    axes[2].xaxis.set_major_locator(mdates.YearLocator())
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("Rocky: Plexon OFS vs gate-controlled re-sort\n"
                 "middle panel is the false-positive signature -- OFS units that "
                 "fail SNR/shape/count", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_impedance(units: pd.DataFrame, imp: pd.DataFrame, out: Path,
                  tol_days: int) -> str:
    """Per-electrode 1 kHz impedance against unit yield.

    Returns
    -------
    str
        A one-line verdict on whether impedance tracks yield, for the report.
    """
    res = units[units["method"] == "resort"].copy()
    res["pass_gate"] = res["pass_gate"].fillna(False).astype(bool)
    y = (res[res["pass_gate"]]
         .groupby(["date", "array", "electrode_id"]).size()
         .rename("n_units").reset_index())
    # electrodes with zero passing units still matter -- add them back
    allpairs = (res.groupby(["date", "array", "electrode_id"]).size()
                .rename("_n").reset_index().drop(columns="_n"))
    y = allpairs.merge(y, on=["date", "array", "electrode_id"], how="left")
    y["n_units"] = y["n_units"].fillna(0)

    y["_d"] = pd.to_datetime(y["date"])
    imp = imp.copy()
    imp["_d"] = pd.to_datetime(imp["date"])

    merged = []
    for (arr, eid), grp in y.groupby(["array", "electrode_id"], sort=False):
        cand = imp[(imp["array"] == arr) & (imp["electrode_id"] == eid)]
        if not len(cand):
            continue
        m = pd.merge_asof(
            grp.sort_values("_d"),
            cand.sort_values("_d")[["_d", "z_1khz_ohm"]],
            on="_d", direction="nearest", tolerance=pd.Timedelta(days=tol_days),
        )
        merged.append(m)
    if not merged:
        return "impedance join produced no rows"
    j = pd.concat(merged, ignore_index=True).dropna(subset=["z_1khz_ohm"])
    if len(j) < 50:
        return f"impedance join too sparse ({len(j)} rows)"

    rho, p = spearmanr(j["z_1khz_ohm"], j["n_units"])

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    for arr, g in j.groupby("array"):
        axes[0].scatter(g["z_1khz_ohm"] / 1e3, g["n_units"], s=8, alpha=0.25,
                        color=ARRAY_COLOR.get(arr, "0.4"), label=arr)
    axes[0].set_xscale("log")
    axes[0].set_xlabel("impedance at 1 kHz (kOhm, log)")
    axes[0].set_ylabel("gate-passing units on electrode")
    axes[0].set_title(f"per electrode-session   Spearman rho={rho:+.3f} (p={p:.1e})")
    axes[0].legend(fontsize=9)
    axes[0].grid(alpha=0.3)

    # Binned mean makes the trend legible through the scatter
    j["z_bin"] = pd.qcut(j["z_1khz_ohm"], 12, duplicates="drop")
    b = j.groupby(["z_bin", "array"], observed=True).agg(
        z=("z_1khz_ohm", "median"), n=("n_units", "mean")).reset_index()
    for arr, g in b.groupby("array"):
        axes[1].plot(g["z"] / 1e3, g["n"], "-o", ms=5,
                     color=ARRAY_COLOR.get(arr, "0.4"), label=arr)
    axes[1].set_xscale("log")
    axes[1].set_xlabel("impedance at 1 kHz (kOhm, log)")
    axes[1].set_ylabel("mean units per electrode")
    axes[1].set_title("binned mean (12 quantile bins)")
    axes[1].legend(fontsize=9)
    axes[1].grid(alpha=0.3)

    fig.suptitle(f"Rocky: electrode impedance vs unit yield  "
                 f"(nearest impedance within {tol_days} d, n={len(j)})", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return (f"Spearman rho={rho:+.3f} (p={p:.1e}) over {len(j)} electrode-sessions "
            f"within {tol_days} d")


# === Main ===
def main() -> int:
    """Aggregate the cohort and render the longitudinal figures."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--tol-days", type=int, default=14)
    args = ap.parse_args()
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    units = pd.read_parquet(UNITS_IN)
    banner("Input")
    print(f"  units_long rows : {len(units)}")
    print(f"  methods         : {dict(units['method'].value_counts())}")
    print(f"  sessions        : {units.groupby(['date', 'array']).ngroups}")

    sess = session_summary(units)
    sess.to_parquet(SESSION_OUT, engine="pyarrow", index=False)
    print(f"  session rows    : {len(sess)}  -> {SESSION_OUT.name}")

    banner("Anterior vs Posterior  (gate-passing re-sort)")
    r = sess[sess["method"] == "resort"]
    for arr, g in r.groupby("array"):
        print(f"  {arr}: {len(g)} sessions  {g['date'].min()} .. {g['date'].max()}")
        print(f"    units/electrode  median={g['units_per_electrode'].median():.3f}"
              f"  first={g.sort_values('date_dt')['units_per_electrode'].iloc[0]:.3f}"
              f"  last={g.sort_values('date_dt')['units_per_electrode'].iloc[-1]:.3f}")
        print(f"    median SNR       median={g['median_snr'].median():.2f}")
        print(f"    noise floor uV   median={g['median_noise_uv'].median():.2f}")

    banner("OFS vs re-sort")
    for m, g in sess.groupby("method"):
        print(f"  {m:7s} sessions={len(g):4d}  "
              f"units/session median={g['n_units'].median():7.1f}  "
              f"candidates median={g['n_candidates'].median():7.1f}  "
              f"pass_fraction median={g['pass_fraction'].median():.3f}")
    o = sess[sess["method"] == "ofs"].copy()
    if len(o):
        o["yr"] = o["date_dt"].dt.year
        print()
        print("  fraction of OFS units passing the gate, by year:")
        for yr, g in o.groupby("yr"):
            print(f"    {yr}: {g['pass_fraction'].median():.3f}   (n={len(g)} sessions)")

    banner("Figures")
    fig_yield(sess, FIG_DIR / "05_yield_over_time.png")
    print(f"  wrote {FIG_DIR / '05_yield_over_time.png'}")
    fig_quality(sess, FIG_DIR / "06_snr_over_time.png")
    print(f"  wrote {FIG_DIR / '06_snr_over_time.png'}")
    fig_resort_vs_ofs(sess, FIG_DIR / "07_resort_vs_ofs.png")
    print(f"  wrote {FIG_DIR / '07_resort_vs_ofs.png'}")

    if IMPEDANCE_IN.exists():
        imp = pd.read_parquet(IMPEDANCE_IN)
        verdict = fig_impedance(units, imp, FIG_DIR / "08_impedance_vs_yield.png",
                                args.tol_days)
        print(f"  wrote {FIG_DIR / '08_impedance_vs_yield.png'}")
        print(f"  impedance vs yield: {verdict}")
    else:
        print("  impedance table missing; skipped figure 08")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

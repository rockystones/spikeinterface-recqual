"""Spatial and longitudinal structure of Rocky unit metrics.

Maps every unit back to its physical position on the Utah array via the CMP
file, then asks two questions the per-session summaries cannot answer:

1. **Where on the array** are units lost, and is the loss spatially organised
   (edge vs centre, one region, or diffuse)? Diffuse loss implicates the
   tissue response; organised loss implicates a connector bank, a wire bundle,
   or focal damage.
2. **How do unit properties differ** between the anterior and posterior
   implants over time -- not just how many units, but what kind.

Bank is carried as a first-class grouping because the three Cerebus banks
(A/B/C, 32 electrodes each) are separate physical connectors. A failure
confined to one bank is a hardware fault, not biology; that distinction is
invisible in any per-session average.

Run from repo root:

    uv run python notebooks/scratch_rocky_spatial.py

See:
- docs/notes/utah_channel_mapping.md
- docs/session_plans/session05_methods_comparison.md
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
ROCKY = Path(r"D:\Claude Code\Rocky")
OUT_DIR = REPO / "data" / "derived" / "rocky"
FIG_DIR = REPO / "figures" / "rocky"
UNITS_IN = OUT_DIR / "units_long.parquet"
SPATIAL_OUT = OUT_DIR / "electrode_summary.parquet"

CMP_BY_ARRAY = {
    "Anterior": ROCKY / "preimplant" / "SN 1025-001501.cmp",
    "Posterior": ROCKY / "preimplant" / "SN 1025-001497.cmp",
}
ARRAY_COLOR = {"Anterior": "#1f77b4", "Posterior": "#d62728"}
GRID = 10

# Metrics compared between arrays and over time.
METRICS = [
    ("snr", "SNR"),
    ("amplitude_uv", "|trough| (uV)"),
    ("firing_rate_hz", "firing rate (Hz)"),
    ("peak_trough_ms", "peak-to-trough (ms)"),
    ("isi_viol_rate", "ISI violation rate"),
    ("noise_uv", "noise floor (uV)"),
]


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def parse_cmp(path: Path) -> pd.DataFrame:
    """Parse a CMP into electrode_id -> (col, row, bank, elec, label).

    Returns
    -------
    pandas.DataFrame
        One row per electrode. ``electrode_id = (bank - 'A') * 32 + elec``,
        which is the NEV channel id; ``label`` is the manufacturer's ``elecN``
        and is deliberately NOT the same number (see utah_channel_mapping.md).
    """
    rows = []
    for ln in path.read_text().splitlines():
        p = ln.split()
        if len(p) >= 4 and p[0].isdigit() and p[1].isdigit() and p[3].isdigit():
            col, row, bank, elec = int(p[0]), int(p[1]), p[2].upper(), int(p[3])
            rows.append(dict(
                col=col, row=row, bank=bank, elec=elec,
                label=p[4] if len(p) >= 5 else "",
                electrode_id=(ord(bank) - ord("A")) * 32 + elec,
            ))
    return pd.DataFrame(rows)


def load_units() -> pd.DataFrame:
    """Load gate-passing ISO-SPLIT units with array geometry attached."""
    u = pd.read_parquet(UNITS_IN)
    u = u[u["method"] == "resort"].copy()
    u["pass_gate"] = u["pass_gate"].fillna(False).astype(bool)
    u = u[u["pass_gate"]]
    u["date_dt"] = pd.to_datetime(u["date"])
    u["year"] = u["date_dt"].dt.year

    geo = pd.concat(
        [parse_cmp(p).assign(array=a) for a, p in CMP_BY_ARRAY.items()],
        ignore_index=True,
    )
    return u.merge(geo, on=["array", "electrode_id"], how="left")


def electrode_summary(u: pd.DataFrame) -> pd.DataFrame:
    """Per (array, electrode, year) yield and median metrics."""
    agg = {m: (m, "median") for m, _ in METRICS}
    g = (u.groupby(["array", "electrode_id", "col", "row", "bank", "year"])
         .agg(n_units=("unit_id", "size"), **agg)
         .reset_index())
    # Sessions per array-year, so yield can be normalised to per-session
    sess = (u.groupby(["array", "year"])["date"].nunique()
            .rename("n_sessions").reset_index())
    g = g.merge(sess, on=["array", "year"], how="left")
    g["units_per_session"] = g["n_units"] / g["n_sessions"]
    return g


def fig_spatial_maps(es: pd.DataFrame, out: Path) -> None:
    """Per-year unit-yield maps on the 10x10 grid, both arrays."""
    years = sorted(es["year"].unique())
    fig, axes = plt.subplots(2, len(years), figsize=(2.5 * len(years), 6),
                             squeeze=False)
    vmax = float(np.nanpercentile(es["units_per_session"], 98))
    for ri, arr in enumerate(("Anterior", "Posterior")):
        for ci, yr in enumerate(years):
            ax = axes[ri][ci]
            sub = es[(es["array"] == arr) & (es["year"] == yr)]
            grid = np.full((GRID, GRID), np.nan)
            for _, r in sub.iterrows():
                if np.isfinite(r["col"]) and np.isfinite(r["row"]):
                    grid[int(r["row"]), int(r["col"])] = r["units_per_session"]
            cmap = plt.get_cmap("viridis").copy()
            cmap.set_bad("0.88")
            im = ax.imshow(np.ma.masked_invalid(grid), origin="lower",
                           cmap=cmap, vmin=0, vmax=vmax)
            ax.set_xticks([])
            ax.set_yticks([])
            if ri == 0:
                ax.set_title(str(yr), fontsize=10)
            if ci == 0:
                ax.set_ylabel(arr, fontsize=10)
    fig.colorbar(im, ax=axes, fraction=0.02, pad=0.02,
                 label="units per session per electrode")
    fig.suptitle("Rocky: spatial distribution of unit yield across the array\n"
                 "grey = electrode never carried a gate-passing unit that year",
                 fontsize=12)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_bank(u: pd.DataFrame, out: Path) -> None:
    """Yield and quality by Cerebus bank -- separates hardware from biology."""
    per = (u.groupby(["array", "bank", "date", "date_dt"])
           .agg(n_units=("unit_id", "size"), snr=("snr", "median"),
                noise=("noise_uv", "median"))
           .reset_index())
    fig, axes = plt.subplots(3, 1, figsize=(13, 10), sharex=True)
    styles = {"A": "-", "B": "--", "C": ":"}
    for arr, g in per.groupby("array"):
        for bank, gb in g.groupby("bank"):
            gb = gb.sort_values("date_dt")
            roll = gb.set_index("date_dt")[["n_units", "snr", "noise"]].rolling(
                "90D", min_periods=2).median()
            for ax, col in zip(axes, ("n_units", "snr", "noise"), strict=True):
                ax.plot(roll.index, roll[col], styles.get(bank, "-"),
                        color=ARRAY_COLOR.get(arr, "0.4"), lw=1.3,
                        label=f"{arr[:4]} bank {bank}", alpha=0.85)
    for ax, lbl in zip(axes,
                       ("units per session (90-day median)",
                        "median unit SNR", "median noise floor (uV)"),
                       strict=True):
        ax.set_ylabel(lbl)
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=7, ncol=3)
    axes[2].set_xlabel("session date")
    axes[2].xaxis.set_major_locator(mdates.YearLocator())
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("Rocky: yield and quality by Cerebus bank\n"
                 "banks are separate physical connectors -- a bank-confined "
                 "failure is hardware, not biology", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_metric_trends(u: pd.DataFrame, out: Path) -> None:
    """Unit-property trajectories, anterior vs posterior."""
    fig, axes = plt.subplots(3, 2, figsize=(15, 11), sharex=True)
    for ax, (col, lbl) in zip(axes.ravel(), METRICS, strict=True):
        for arr, g in u.groupby("array"):
            s = (g.groupby("date_dt")[col].median().sort_index()
                 .rolling(5, min_periods=2).median())
            ax.plot(s.index, s.values, "-", lw=1.4,
                    color=ARRAY_COLOR.get(arr, "0.4"), label=arr, alpha=0.9)
        ax.set_ylabel(lbl)
        ax.grid(alpha=0.3)
    axes[0][0].legend(fontsize=9)
    for ax in axes[-1]:
        ax.set_xlabel("session date")
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("Rocky: unit-property trajectories (gate-passing ISO-SPLIT units, "
                 "5-session rolling median)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    """Compute the spatial summary and render the maps."""
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    banner("Load units + array geometry")
    u = load_units()
    print(f"  gate-passing units : {len(u)}")
    print(f"  sessions           : {u.groupby(['date', 'array']).ngroups}")
    missing = int(u["col"].isna().sum())
    print(f"  units without geometry: {missing}")
    assert missing == 0, "CMP join failed for some electrodes"

    banner("Anterior vs Posterior  unit properties (all sessions pooled)")
    print(f"  {'metric':22s} {'Anterior':>12s} {'Posterior':>12s} "
          f"{'ratio':>7s} {'Mann-Whitney p':>16s}")
    for col, lbl in METRICS:
        a = u.loc[u["array"] == "Anterior", col].dropna()
        p = u.loc[u["array"] == "Posterior", col].dropna()
        if len(a) < 10 or len(p) < 10:
            continue
        ma, mp = float(a.median()), float(p.median())
        _, pv = mannwhitneyu(a, p, alternative="two-sided")
        # Some metrics (ISI violation rate) have a median of exactly zero
        ratio = f"{ma / mp:7.2f}" if mp != 0 else "    n/a"
        print(f"  {lbl:22s} {ma:12.3f} {mp:12.3f} {ratio} {pv:16.2e}")

    banner("Trend over time (Spearman rho of per-session median vs date)")
    print(f"  {'metric':22s} {'Anterior rho':>14s} {'Posterior rho':>14s}")
    for col, lbl in METRICS:
        cells = []
        for arr in ("Anterior", "Posterior"):
            g = u[u["array"] == arr]
            s = g.groupby("date_dt")[col].median().dropna()
            if len(s) > 5:
                rho, _ = spearmanr(s.index.astype("int64"), s.to_numpy())
                cells.append(f"{rho:+.3f}")
            else:
                cells.append("  n/a")
        print(f"  {lbl:22s} {cells[0]:>14s} {cells[1]:>14s}")

    banner("Bank breakdown  (A/B/C are separate physical connectors)")
    bk = (u.groupby(["array", "bank"])
          .agg(units=("unit_id", "size"), electrodes=("electrode_id", "nunique"),
               snr=("snr", "median"), noise=("noise_uv", "median"))
          .reset_index())
    print(bk.to_string(index=False))

    banner("Electrode-level summary")
    es = electrode_summary(u)
    es.to_parquet(SPATIAL_OUT, engine="pyarrow", index=False)
    print(f"  rows {len(es)}  -> {SPATIAL_OUT.name}")

    # Is unit loss spatially organised? Correlate yield with distance from the
    # array centre; a strong edge effect would show as a negative rho.
    banner("Is loss spatially organised? (yield vs distance from array centre)")
    for arr in ("Anterior", "Posterior"):
        for yr in sorted(es["year"].unique()):
            sub = es[(es["array"] == arr) & (es["year"] == yr)]
            if len(sub) < 20:
                continue
            d = np.hypot(sub["col"] - 4.5, sub["row"] - 4.5)
            rho, pv = spearmanr(d, sub["units_per_session"])
            mark = "  <-- edge effect" if (pv < 0.01 and rho < -0.3) else ""
            print(f"  {arr:9s} {yr}  rho={rho:+.3f}  p={pv:.1e}  n={len(sub)}{mark}")

    banner("Figures")
    fig_spatial_maps(es, FIG_DIR / "11_spatial_yield_maps.png")
    print(f"  wrote {FIG_DIR / '11_spatial_yield_maps.png'}")
    fig_bank(u, FIG_DIR / "12_bank_breakdown.png")
    print(f"  wrote {FIG_DIR / '12_bank_breakdown.png'}")
    fig_metric_trends(u, FIG_DIR / "13_metric_trends.png")
    print(f"  wrote {FIG_DIR / '13_metric_trends.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Rocky I1 two-array longitudinal comparison: one metric per figure.

Owner spec (2026-09-16): subject Rocky, EARLY arrays only (I1 Anterior vs
Posterior; the 2025 I2 pair excluded), one metric per figure, every
sorting method on the same axes, and sessions where an array yields no
units at all read 0, not NaN. Session identity (the exact stem) rides in
the output table so any point can be traced in the MATLAB workspace.

Metrics (one figure each):
  n_units       total sorted units on the array that session
  mean_max_amp  the owner's legacy metric (nav D-013): per active channel
                take the LARGEST-amplitude unit, then average across the
                active channels; 0 when the array has no units
  yield_pct     % of the 96 wired channels holding >= 1 unit

Methods and their sources / coverage:
  ofs           human Plexon sort, all units, units_long       (~330 s-a)
  resort_gated  full-data ISO-SPLIT + physics gate, units_long (~330 s-a)
  isosplit / gmm_bic / kmeans_sil / hdbscan  the 60-session methods
                subset, gated, methods_long (subsample-clustered)
  ms5/ks4/sc2/tdc2  modern sorters on the continuous ns5, consensus
                shards - TOTAL COUNTS ONLY (their unit->channel
                assignment was never stored outside the provenance
                sessions, so the channel-resolved metrics exclude them)

Amplitude definition: per-unit P2P = peak_uv - trough_uv, the one
definition every snippet table shares. CAVEAT (documented in
longitudinal_metrics.md): this under-reads the exact mean-waveform
global range on ~25% of units; the exact NEV recompute exists for the
ofs method only (cohort/mean_max_p2p.parquet). Comparability across
methods on one axis wins here.

Zero-fill scope: 0 is written only for sessions the method ATTEMPTED
(its own universe) and found nothing; sessions a method never ran on are
absent, not 0.

Outputs:
  data/derived/rocky/two_array_metrics.parquet   (metric, method, date,
                                                  array, stem, value)
  figures/rocky/17_n_units_by_method.png
  figures/rocky/18_mean_max_amp_by_method.png
  figures/rocky/19_channel_yield_by_method.png

Run from repo root:   uv run python notebooks/scratch_two_array_metrics.py
MATLAB twin:          matlab/rocky_two_array_metrics.m
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
DER = REPO / "data" / "derived"
OUT = DER / "rocky" / "two_array_metrics.parquet"
FIG = REPO / "figures" / "rocky"
N_CH = 96
MODERN = ["mountainsort5", "kilosort4", "spykingcircus2", "tridesclous2"]
SURGERY = pd.Timestamp("2017-08-30")   # I1 implant (configs/subjects/rocky)
DAYS_PER_MONTH = 30.44                 # month-post-implant bin width

# Sessions flagged for MANUAL EXAMINATION / exclusion (owner request
# 2026-09-16). Curated from two independent screens - a rolling-median
# robust-z sweep over every (metric, method, array) series (flag at
# z > 5 on >= 3 metric-method combinations) and the S09 session-noise
# screen (measurement_floor.md) - plus the owner's named example. Each
# entry: stem -> short reason. Toggled per figure set below; the flag
# also ships in the output table as is_outlier/outlier_reason.
OUTLIERS = {
    # -- 2017 protocol block: 4916 s sessions, no headstage, ~2.3x noise
    #    (the era confound of longitudinal_metrics.md); every stem here
    #    was flagged by the z-sweep, the noise screen, or both
    "Rocky_Posterior_09-21-2017": "2017 protocol; z-flagged x3",
    "Rocky_Anterior_09-22-2017": "2017 protocol; z-flagged x12",
    "Rocky_Anterior_09-28-2017": "2017 protocol; z-flagged x11",
    "Rocky_Anterior_09-29-2017": "2017 protocol; noise screen",
    "Rocky_Anterior_10-03-2017": "2017 protocol; noise screen",
    "Rocky_Anterior_10-04-2017": "2017 protocol; noise screen; z x4",
    "Rocky_Anterior_10-05-2017": "2017 protocol; noise screen",
    "Rocky_Anterior_10-06-2017": "2017 protocol; noise screen",
    "Rocky_Anterior_10-09-2017": "2017 protocol; noise screen; z x5",
    "Rocky_Anterior_10-11-2017": "2017 protocol; noise screen",
    "Rocky_Anterior_10-12-2017": "2017 protocol; noise screen",
    "Rocky_Posterior_10-19-2017": "2017 protocol; z-flagged x3",
    "Rocky_Posterior_10-23-2017": "2017 protocol; noise screen; z x13",
    "Rocky_Posterior_10-25-2017": "2017 protocol; noise screen; z x3",
    "Rocky_Anterior_10-26-2017": "2017 protocol; noise screen; z x5",
    "Rocky_Anterior_10-27-2017": "2017 protocol; noise screen",
    "Rocky_Posterior_10-30-2017_Baseline": "2017 protocol; z-flagged x5",
    # -- Dec-2018 Posterior Analog pair: degenerate amplitude days (the
    #    2018-12-06 era also holds the 1-channel 3.9 mV exact-P2P peak)
    # (the Analog pair are near-empty files - 1 electrode, ~0 Hz - so
    #  their reason is really "dead recording"; the 3.9 mV blowup
    #  itself is the Digital 12-06 stem, ruled excluded by the owner
    #  2026-09-19)
    "Rocky_Posterior_12-06-2018_Baseline_AnalogHeadstage":
        "amplitude blowup; z x6",
    "Rocky_Posterior_12-13-2018_Baseline_AnalogHeadstage":
        "amplitude blowup; z x6",
    "Rocky_Posterior_12-06-2018_Baseline_DigitalHeadstage":
        "single-channel 3.9 mV NaN-fill peak (owner ruling 2026-09-19)",
    # -- mid-2019 Analog block: railed/elevated sessions (owner example)
    "Rocky_Posterior_03-21-2019_Baseline_AnalogHeadstage":
        "railed artifacts; noise screen; z max 76",
    "Rocky_Anterior_05-17-2019_Baseline_AnalogHeadstage": "noise screen",
    "Rocky_Anterior_05-23-2019_Baseline_AnalogHeadstage":
        "railed day (owner example); noise screen; z x8",
    "Rocky_Posterior_05-23-2019_Baseline_AnalogHeadstage":
        "railed day (owner example); noise screen; z max 362",
    "Rocky_Anterior_05-30-2019_Baseline_AnalogHeadstage":
        "railed; noise screen; z max 61",
    # -- isolated later anomalies
    "Rocky_Posterior_08-24-2020_Baseline_DigitalHeadstage": "noise screen",
    "Rocky_Posterior_2022-08-26_Baseline_DigitalHeadstage":
        "mid-2022 dropout; z x5",
    "Rocky_Posterior_2022-11-17_Baseline_DigitalHeadstage":
        "amplitude spike; z x3",
}


def session_metrics(units: pd.DataFrame, universe: pd.DataFrame,
                    method: str) -> list[dict]:
    """The three metrics for one method, zero-filled over its universe.

    units    per-unit rows (stem, date, array, channel_id, p2p_uv)
    universe every (stem, date, array) the method attempted
    """
    per = (units.groupby(["stem", "date", "array"], observed=True)
           .agg(n_units=("p2p_uv", "size"),
                yield_pct=("channel_id", lambda s: 100 * s.nunique() / N_CH))
           .reset_index())
    # the owner's metric: per channel keep the LARGEST-P2P unit, then
    # average those maxima across the channels that have any unit
    mm = (units.groupby(["stem", "channel_id"], observed=True).p2p_uv.max()
          .groupby("stem").mean().rename("mean_max_amp"))
    per = per.merge(mm, on="stem", how="left")

    rows = []
    have = set(per.stem)
    for r in per.itertuples():
        for metric, v in (("n_units", r.n_units),
                          ("mean_max_amp", r.mean_max_amp),
                          ("yield_pct", r.yield_pct)):
            rows.append(dict(metric=metric, method=method, date=r.date,
                             array=r.array, stem=r.stem, value=float(v)))
    # zero-fill: attempted sessions with no units at all
    for r in universe[~universe.stem.isin(have)].itertuples():
        for metric in ("n_units", "mean_max_amp", "yield_pct"):
            rows.append(dict(metric=metric, method=method, date=r.date,
                             array=r.array, stem=r.stem, value=0.0))
    return rows


def main() -> int:
    rows: list[dict] = []

    # === snippet-layer methods ===========================================
    ee = pd.read_parquet(DER / "rocky" / "events_electrode.parquet",
                         columns=["stem", "date", "array"])
    ee["date"] = pd.to_datetime(ee.date)
    full_universe = ee.drop_duplicates("stem")   # every recorded I1 session

    ul = pd.read_parquet(DER / "rocky" / "units_long.parquet")
    ul["date"] = pd.to_datetime(ul.date)
    ul["p2p_uv"] = ul.peak_uv - ul.trough_uv
    rows += session_metrics(ul[ul.method == "ofs"], full_universe, "ofs")
    res = ul[(ul.method == "resort") & ul.pass_gate.astype(bool)]
    rows += session_metrics(res, full_universe, "resort_gated")

    ml = pd.read_parquet(DER / "rocky" / "methods_long.parquet")
    ml["date"] = pd.to_datetime(ml.date)
    ml["p2p_uv"] = ml.peak_uv - ml.trough_uv
    sub_universe = ml.drop_duplicates("stem")[["stem", "date", "array"]]
    for meth in ("isosplit", "gmm_bic", "kmeans_sil", "hdbscan"):
        g = ml[(ml.method == meth) & ml.pass_gate.astype(bool)]
        rows += session_metrics(g, sub_universe, meth)

    # === modern sorters: n_units only (no stored channel assignment) ====
    shards = sorted((DER / "ns5" / "consensus" / "shards").glob("*.parquet"))
    runs = pd.concat([pd.read_parquet(p) for p in shards],
                     ignore_index=True)
    runs = runs[(runs.kind == "run") & (runs.subject == "Rocky")
                & (runs.implant == "I1") & runs.error.isna()]
    runs["date"] = pd.to_datetime(runs.date)
    for r in runs.itertuples():
        rows.append(dict(metric="n_units", method=str(r.sorter),
                         date=r.date, array=str(r.array), stem=str(r.stem),
                         value=float(r.n_units)))

    t = pd.DataFrame(rows).sort_values(["metric", "method", "array", "date"])
    # exclusion flag + month post implant travel with every row
    t["is_outlier"] = t.stem.isin(OUTLIERS)
    t["outlier_reason"] = t.stem.map(OUTLIERS).fillna("")
    t["month_post"] = ((t.date - SURGERY).dt.days / DAYS_PER_MONTH
                       ).astype(int)
    t.to_parquet(OUT, index=False)
    print(t.groupby(["metric", "method"], observed=True)
           .agg(n=("stem", "size"), med=("value", "median"))
           .round(1).to_string())
    print(f"\noutlier sessions excluded from the clean/monthly sets: "
          f"{t[t.is_outlier].stem.nunique()}")

    # === figures ==========================================================
    color = {m: c for m, c in zip(
        ["ofs", "resort_gated", "isosplit", "gmm_bic", "kmeans_sil",
         "hdbscan"] + MODERN,
        plt.cm.tab10.colors + plt.cm.tab10.colors[:2], strict=False)}
    style = {"Anterior": "-", "Posterior": "--"}
    titles = {"n_units": ("total sorted units per array", "units",
                          "17_n_units_by_method"),
              "mean_max_amp": ("mean max unit amplitude over active "
                               "channels (P2P of unit mean waveform)",
                               "μV", "18_mean_max_amp_by_method"),
              "yield_pct": ("channel yield (% of 96 channels with a unit)",
                            "%", "19_channel_yield_by_method")}

    def plot_set(d: pd.DataFrame, suffix: str, note: str,
                 mark_outliers: bool, monthly: bool) -> None:
        """One figure per metric for one variant of the data."""
        xcol = "month_post" if monthly else "date"
        for metric, (ttl, ylab, base) in titles.items():
            dm = d[d.metric == metric]
            fig, ax = plt.subplots(figsize=(11, 4.6))
            for (meth, arr), g in dm.groupby(["method", "array"],
                                             observed=True):
                if monthly:
                    # bin = median of the session values inside each
                    # month-post-implant bin (zeros included)
                    g = (g.groupby("month_post").value.median()
                         .reset_index().sort_values("month_post"))
                    ax.plot(g.month_post, g.value, style[arr] + "o",
                            color=color[meth], lw=1.0, ms=2.5,
                            label=f"{meth} {arr}")
                else:
                    g = g.sort_values("date")
                    ax.plot(g[xcol], g.value, style[arr],
                            color=color[meth], lw=1.0,
                            label=f"{meth} {arr}")
                    if mark_outliers:
                        o = g[g.is_outlier]
                        ax.plot(o[xcol], o.value, "o", ms=5, mfc="none",
                                mec="red", mew=1.0, label="_nolegend_")
            ax.grid(alpha=0.25)
            ax.set_ylabel(ylab)
            ax.set_xlabel("months post implant" if monthly else "")
            ax.set_title(f"Rocky I1: {ttl}\n(solid = Anterior/coated, "
                         f"dashed = Posterior/uncoated; {note})",
                         fontsize=10)
            ax.legend(fontsize=6, ncol=4, loc="upper right")
            fig.tight_layout()
            fig.savefig(FIG / f"{base}{suffix}.png", dpi=150)
            plt.close(fig)
            print(f"wrote {FIG / (base + suffix + '.png')}")

    clean = t[~t.is_outlier]
    plot_set(t, "", "red circles = flagged for manual examination",
             mark_outliers=True, monthly=False)
    plot_set(clean, "_clean", "outlier sessions excluded",
             mark_outliers=False, monthly=False)
    plot_set(clean, "_monthly", "outliers excluded; median per "
             "month-post-implant bin", mark_outliers=False, monthly=True)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

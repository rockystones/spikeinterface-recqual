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
    t.to_parquet(OUT, index=False)
    print(t.groupby(["metric", "method"], observed=True)
           .agg(n=("stem", "size"), med=("value", "median"))
           .round(1).to_string())

    # === figures: one metric each, color = method, style = array ========
    color = {m: c for m, c in zip(
        ["ofs", "resort_gated", "isosplit", "gmm_bic", "kmeans_sil",
         "hdbscan"] + MODERN,
        plt.cm.tab10.colors + plt.cm.tab10.colors[:2], strict=False)}
    style = {"Anterior": "-", "Posterior": "--"}
    titles = {"n_units": ("total sorted units per array", "units",
                          "17_n_units_by_method.png"),
              "mean_max_amp": ("mean max unit amplitude over active "
                               "channels (P2P of unit mean waveform)",
                               "μV", "18_mean_max_amp_by_method.png"),
              "yield_pct": ("channel yield (% of 96 channels with a unit)",
                            "%", "19_channel_yield_by_method.png")}
    for metric, (ttl, ylab, fname) in titles.items():
        d = t[t.metric == metric]
        fig, ax = plt.subplots(figsize=(11, 4.6))
        for (meth, arr), g in d.groupby(["method", "array"], observed=True):
            g = g.sort_values("date")
            ax.plot(g.date, g.value, style[arr], color=color[meth], lw=1.0,
                    label=f"{meth} {arr}")
        ax.grid(alpha=0.25)
        ax.set_ylabel(ylab)
        ax.set_title(f"Rocky I1: {ttl}\n(solid = Anterior/coated, "
                     "dashed = Posterior/uncoated; zero = attempted, "
                     "no units)", fontsize=10)
        ax.legend(fontsize=6, ncol=4, loc="upper right")
        fig.tight_layout()
        fig.savefig(FIG / fname, dpi=150)
        plt.close(fig)
        print(f"wrote {FIG / fname}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

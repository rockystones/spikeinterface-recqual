"""Longitudinal trends for Oops and Picasso, and how they sit beside Blackrock.

S10 asked whether array yield declines across a cohort and answered it with the
sorting-based layer, because the Blackrock corpus had one. Oops and Picasso do
not: TDT's online sortcode is an accept flag, so the only layer that reaches
all 177 blocks is the sorting-free one.

That turns out to be the more interesting comparison rather than a weaker one.
`scratch_headstage_free.py` computed exactly these quantities, under exactly
these names, on Blackrock NEVs -- and this pass reuses the same
`baseline_noise_uv` from `scratch_rocky_resort`. So the two corpora can be
stacked and the free layer's longitudinal behaviour compared across two
acquisition systems, two rigs, two decades of hardware and four subjects, with
the metric definition held fixed.

Screening follows S09: a session is dropped when *its own noise floor* exceeds
twice its array's median, never when its yield is low, because screening on the
outcome is circular.

One TDT-specific screen is added. The online threshold was not held constant
across this corpus -- Picasso's 2017 blocks carry crossing rates an order of
magnitude above his 2016 ones -- and a threshold change moves every
crossing-derived metric without anything happening to the tissue. Trends are
therefore reported per array *and* per threshold epoch.

Run from repo root:

    uv run python notebooks/scratch_tdt_longitudinal.py

Writes `data/derived/tdt/tdt_trends.parquet`.

See:
- docs/notes/tdt_corpus.md
- docs/notes/cohort_longitudinal.md
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))

FREE = REPO / "data" / "derived" / "tdt" / "free_metrics.parquet"
BR_FREE = REPO / "data" / "derived" / "cohort" / "headstage_free.parquet"
OUT = REPO / "data" / "derived" / "tdt" / "tdt_trends.parquet"

# S09's acquisition screen, restated.
NOISE_SCREEN_MULT = 2.0
# A crossing rate this far from the array's own median cannot be tissue; it is
# the detector threshold moving. Chosen an order of magnitude above the screen
# above so it flags only step changes, not drift.
RATE_EPOCH_MULT = 3.0
# Too few sessions and a rank correlation is noise.
MIN_SESSIONS = 8

TREND_METRICS = ["noise_med", "amp_p50", "amp_p99", "peak_snr_med",
                 "crossing_rate_hz", "frac_elec_active", "n_crossings"]


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === Axes and screens ===
def add_axes(s: pd.DataFrame) -> pd.DataFrame:
    """Days-since-first, the noise screen, and the threshold epoch.

    No surgery date is known for either subject, so `days_since_first` is the
    only honest age axis -- the same fallback the Blackrock cohort used for
    every array but Rocky implant 2.
    """
    s = s.copy()
    s["date"] = pd.to_datetime(s["date"])
    key = ["subject", "array"]
    s["days_since_first"] = s.groupby(key).date.transform(
        lambda d: (d - d.min()).dt.days)
    s["noise_baseline"] = s.groupby(key).noise_med.transform("median")
    s["high_noise"] = s.noise_med > NOISE_SCREEN_MULT * s.noise_baseline
    # Threshold epoch: a step in crossing rate, not a drift in it.
    s["rate_baseline"] = s.groupby(key).crossing_rate_hz.transform("median")
    s["rate_outlier"] = (
        (s.crossing_rate_hz > RATE_EPOCH_MULT * s.rate_baseline)
        | (s.crossing_rate_hz < s.rate_baseline / RATE_EPOCH_MULT))
    return s


def trends(s: pd.DataFrame, group: list[str]) -> pd.DataFrame:
    """Spearman rho per group per metric, screened and unscreened."""
    rows = []
    for keys, g in s.groupby(group):
        keys = keys if isinstance(keys, tuple) else (keys,)
        clean = g[~g.high_noise & ~g.rate_outlier]
        for m in TREND_METRICS:
            if m not in g.columns:
                continue
            for tag, d in (("all", g), ("screened", clean)):
                d = d.dropna(subset=[m, "date"])
                if len(d) < MIN_SESSIONS or d[m].nunique() < 3:
                    continue
                x = d.date.map(pd.Timestamp.toordinal)
                rho, p = spearmanr(x, d[m])
                rows.append(dict(
                    **dict(zip(group, keys, strict=True)),
                    metric=m, scope=tag, n=len(d),
                    rho=round(float(rho), 3), p=float(p),
                    first=float(d.sort_values("date")[m].head(5).median()),
                    last=float(d.sort_values("date")[m].tail(5).median()),
                    span_days=int((d.date.max() - d.date.min()).days),
                ))
    return pd.DataFrame(rows)


# %%
# === Cross-corpus stacking ===
def blackrock_free() -> pd.DataFrame | None:
    """The Blackrock sorting-free table, relabelled to stack with this one.

    `scratch_headstage_free.py` wrote the same metric names from the same
    helper, so the only work is naming the series and dropping the analog
    headstage -- an amplifier the TDT rig has no counterpart for, and one S12b
    showed reads 1.25x noisier.
    """
    if not BR_FREE.exists():
        return None
    b = pd.read_parquet(BR_FREE)
    b = b[b.get("error").isna()] if "error" in b else b
    b = b[b.headstage == "digital"].copy()
    b["date"] = pd.to_datetime(b["date"])
    b["corpus"] = "blackrock"
    b["series"] = b.subject + "/" + b["array"].astype(str)
    return b


def report(s: pd.DataFrame, tr: pd.DataFrame, per_epoch: pd.DataFrame,
           cross: pd.DataFrame | None) -> None:
    banner("1. Series scored")
    t = s.groupby(["subject", "array"]).agg(
        n=("date", "size"), first=("date", "min"), last=("date", "max"),
        span=("days_since_first", "max"),
        high_noise=("high_noise", "sum"), rate_outlier=("rate_outlier", "sum"),
        noise=("noise_med", "median"), amp=("amp_p50", "median"),
        snr=("peak_snr_med", "median"))
    t["first"] = t["first"].dt.date
    t["last"] = t["last"].dt.date
    print(t.to_string())

    banner("2. The online threshold moved, and it is visible")
    print("  Median crossing rate per electrode by year. A detector threshold")
    print("  change moves this without anything happening to the tissue.\n")
    y = s.assign(year=s.date.dt.year)
    print(y.pivot_table(index="year", columns=["subject", "array"],
                        values="crossing_rate_hz",
                        aggfunc="median").round(1).to_string())
    print(f"\n  sessions flagged as a threshold epoch change: "
          f"{int(s.rate_outlier.sum())} of {len(s)}")

    banner("3. Trends, screened")
    sc = tr[tr.scope == "screened"]
    if len(sc):
        piv = sc.pivot_table(index="metric", columns=["subject", "array"],
                             values="rho")
        print(piv.round(3).to_string())
        print("\n  significant (p < 0.05):")
        sig = sc[sc.p < 0.05][["subject", "array", "metric", "n", "rho", "p"]]
        print(sig.to_string(index=False) if len(sig) else "   none")

    banner("4. Screening changes the answer")
    both = tr.pivot_table(index=["subject", "array", "metric"],
                          columns="scope", values="rho")
    both = both.dropna()
    if len(both):
        both["delta"] = (both["screened"] - both["all"]).abs()
        print(both.sort_values("delta", ascending=False).head(10)
              .round(3).to_string())

    if cross is not None and len(cross):
        banner("5. The free layer across two acquisition systems")
        print("  Same metric definitions, same noise estimator, four subjects,")
        print("  two rigs. rho is against date, screened where computed.\n")
        print(cross.round(3).to_string(index=False))
        for m, g in cross.groupby("metric"):
            same = (np.sign(g.rho) == np.sign(g.rho.median())).mean()
            print(f"  {m:20s} median rho {g.rho.median():+.2f}  "
                  f"sd {g.rho.std():.2f}  same sign {same:.0%}  n={len(g)}")

    if len(per_epoch):
        banner("6. Trends within a single threshold epoch")
        print("  Restricted to each series' modal-rate sessions, so the")
        print("  detector setting is held as close to fixed as the data allow.\n")
        pe = per_epoch[per_epoch.scope == "screened"]
        if len(pe):
            print(pe.pivot_table(index="metric",
                                 columns=["subject", "array"],
                                 values="rho").round(3).to_string())


def main() -> int:
    d = pd.read_parquet(FREE)
    d = d[d.get("error").isna()] if "error" in d else d
    s = add_axes(d)

    tr = trends(s, ["subject", "array"])
    # Within-epoch: keep only sessions near each series' modal crossing rate.
    epoch = s[~s.rate_outlier]
    per_epoch = trends(epoch, ["subject", "array"])

    cross = None
    b = blackrock_free()
    if b is not None:
        b2 = add_axes(b.rename(columns={"array": "array"}))
        rows = []
        for tag, frame in (("tdt", s), ("blackrock", b2)):
            t2 = trends(frame, ["subject", "array"])
            t2 = t2[t2.scope == "screened"].copy()
            t2["corpus"] = tag
            rows.append(t2)
        cross = pd.concat(rows, ignore_index=True)[
            ["corpus", "subject", "array", "metric", "n", "rho", "p"]]
        cross = cross[cross.metric.isin(
            ["noise_med", "amp_p50", "peak_snr_med", "crossing_rate_hz",
             "frac_elec_active"])].sort_values(["metric", "corpus", "subject"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tr.to_parquet(OUT, engine="pyarrow", index=False)
    banner("TDT longitudinal -- Oops and Picasso")
    print(f"  session-array rows: {len(s)}")
    report(s, tr, per_epoch, cross)
    print(f"\n  wrote {OUT.relative_to(REPO)}  ({len(tr)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

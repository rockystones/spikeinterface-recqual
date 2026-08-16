"""S12: analog against digital headstage, the same session recorded twice.

121 date-slots on Rocky implant 1 carry both an analog and a digital headstage
recording of the same session. The owner's expectation is that analog is
noisier. That makes the pair a graded benchmark needing no ground truth:

- Any metric that differs between the two is measuring the **amplifier**, not
  the tissue. A sorting-free quality metric that is not stable across the pair
  is not a quality metric.
- The noise asymmetry means the pair measures not just whether a method works
  but how it degrades, which is what separates methods in practice.

Unlike S09 this is **not** a fixed-event comparison: two physical recordings
have different threshold crossings, so nothing here is exact. Only session-level
metrics are compared, which need no spike matching.

Consumes `cohort_sessions.parquet` from S10 rather than re-reading the NEVs.

Run from repo root:

    uv run python notebooks/scratch_headstage_pairs.py

See:
- docs/notes/cohort_longitudinal.md
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, wilcoxon

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))

SESSIONS = REPO / "data" / "derived" / "cohort" / "cohort_sessions.parquet"
OUT = REPO / "data" / "derived" / "cohort" / "headstage_pairs.parquet"

METRICS = ["noise_med", "n_candidates", "n_units", "units_per_electrode",
           "elec_coverage", "amp_med", "amp_p99", "snr_med", "rate_med",
           "pass_fraction"]


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def build_pairs(s: pd.DataFrame) -> pd.DataFrame:
    """One row per (date, array) carrying both headstages."""
    s = s.copy()
    s["hs"] = s.headstage.str.lower().fillna("")
    s = s[s.hs.str.contains("headstage")]
    rows = []
    key = ["subject", "implant", "array", "date"]
    for k, g in s.groupby(key):
        ana = g[g.hs.str.contains("analog")]
        dig = g[g.hs.str.contains("digital")]
        if not len(ana) or not len(dig):
            continue
        a, d = ana.iloc[0], dig.iloc[0]
        row = dict(zip(key, k, strict=True))
        for m in METRICS:
            row[f"{m}_analog"] = a.get(m, np.nan)
            row[f"{m}_digital"] = d.get(m, np.nan)
        row["high_noise_either"] = bool(a.high_noise or d.high_noise)
        rows.append(row)
    return pd.DataFrame(rows)


def report(p: pd.DataFrame) -> None:
    banner("1. The paired set")
    print(f"  date x array slots with both headstages: {len(p)}")
    print(p.groupby(["subject", "implant", "array"]).size().to_string())
    clean = p[~p.high_noise_either]
    print(f"\n  after the S09 acquisition screen on either member: {len(clean)}")

    banner("2. Is analog noisier?  (owner's expectation, tested)")
    print("  Paired Wilcoxon on the screened set, analog minus digital.\n")
    print(f"  {'metric':22s} {'analog':>10s} {'digital':>10s} "
          f"{'ratio':>7s} {'p':>10s}  n")
    rows = []
    for m in METRICS:
        a = clean[f"{m}_analog"]
        d = clean[f"{m}_digital"]
        ok = a.notna() & d.notna()
        if ok.sum() < 8:
            continue
        med_a, med_d = a[ok].median(), d[ok].median()
        try:
            _, pv = wilcoxon(a[ok], d[ok])
        except ValueError:
            pv = np.nan
        ratio = med_a / med_d if med_d else np.nan
        star = "***" if pv < 1e-3 else "**" if pv < 1e-2 else "*" if pv < 0.05 else ""
        print(f"  {m:22s} {med_a:10.2f} {med_d:10.2f} {ratio:7.2f} "
              f"{pv:10.2g} {int(ok.sum()):4d} {star}")
        rows.append(dict(metric=m, analog=med_a, digital=med_d,
                         ratio=ratio, p=pv, n=int(ok.sum())))

    banner("3. Which metrics are amplifier-invariant?")
    print("  A metric that tracks physiology should agree across the pair.")
    print("  Reported as the paired correlation and the typical |relative")
    print("  difference| between the two recordings of one session.\n")
    print(f"  {'metric':22s} {'rho':>7s} {'rel diff':>9s}  reading")
    for m in METRICS:
        a, d = clean[f"{m}_analog"], clean[f"{m}_digital"]
        ok = a.notna() & d.notna()
        if ok.sum() < 8:
            continue
        rho, _ = spearmanr(a[ok], d[ok])
        rel = (abs(a[ok] - d[ok]) / ((a[ok].abs() + d[ok].abs()) / 2)).median()
        reading = ("tracks the session" if rho > 0.7 and rel < 0.2
                   else "amplifier-dominated" if rho < 0.4 or rel > 0.4
                   else "mixed")
        print(f"  {m:22s} {rho:7.2f} {rel:9.2f}  {reading}")

    banner("4. Does the headstage change the longitudinal trend?")
    print("  Same array, same dates, two amplifiers. If a trend is")
    print("  physiological the two should agree on it.\n")
    for arr, g in clean.groupby("array"):
        line = f"  {arr:10s}"
        for m in ("units_per_electrode", "snr_med", "amp_med"):
            x = g.date.map(pd.Timestamp.toordinal)
            ra, _ = spearmanr(x, g[f"{m}_analog"])
            rd, _ = spearmanr(x, g[f"{m}_digital"])
            line += f"   {m}: analog {ra:+.2f} digital {rd:+.2f}"
        print(line)


def main() -> int:
    if not SESSIONS.exists():
        print(f"  {SESSIONS} missing -- run scratch_cohort_longitudinal.py first")
        return 1
    s = pd.read_parquet(SESSIONS)
    if "error" in s:
        s = s[s.error.isna()]
    p = build_pairs(s)
    if not len(p):
        print("  no headstage pairs found")
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    p.to_parquet(OUT, engine="pyarrow", index=False)
    banner("S12 -- analog vs digital headstage")
    report(p)
    print(f"\n  wrote {OUT.relative_to(REPO)}  ({len(p)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

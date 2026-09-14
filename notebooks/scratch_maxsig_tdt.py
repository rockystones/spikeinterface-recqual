"""TDT-era mean-max-amplitude series from monkey_units_compiled.mat.

Extends the D-013 default metric to the TDT animals (Chase, Luigi, Oops,
Picasso). What was verified on 2026-09-14 (nav R-014):

- `unitsort.<monkey>.<array>.unitsum.maxsigM` equals the mean over active
  channels of the per-channel MAX over sorted units of the per-unit
  amplitude `sig` (uV) - exact to float epsilon for all 215 sessions that
  carry `sig` (Luigi stores only the precomputed maxsigM). Structurally
  this is the NaN-fill variant of the legacy Utah metric.
- The FIELD `maxsig` is a trap: it is NOT max(sig) per channel and NOT
  what maxsigM averages (Oops.A 2015_06_12: mean(maxsig)=109.0 vs
  maxsigM=68.2), and it does not match the tank's max single-snippet P2P
  either. Never join eras through it.
- The waveform-level definition of `sig` (P2P of the plain mean waveform,
  as plot_U01_Utaharray line 112 computes) is NOT locally verifiable:
  the compiling sort_*.mat offline sorts are on no local drive, and the
  in-tank sortcode {0,1} partition is a different sort (compiled channels
  carry up to 8 units). Scale is uV with plausible spike amplitudes.
  Rows therefore carry definition="tdt_sig" - comparable in structure,
  not proven identical per unit, to the exact NEV rows.

Output: data/derived/cohort/mean_max_p2p_tdt.parquet
  subject, array, coating, arrayloc, date, max_p2p_mean_nan (=maxsigM),
  max_p2p_se (=maxsigSE), n_active (len(sig), NaN for Luigi), definition.

Run from repo root:

    uv run python notebooks/scratch_maxsig_tdt.py

See docs/notes/longitudinal_metrics.md.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
MAT = Path(r"D:/Claude Code/Monkey Data/Legacy/L1MonkeyData/ephys"
           ) / "monkey_units_compiled.mat"
OUT = REPO / "data" / "derived" / "cohort" / "mean_max_p2p_tdt.parquet"


def per_channel_max(sig_i) -> np.ndarray:
    """Per-channel max over the ragged per-unit amplitude arrays."""
    return np.array([np.max(np.atleast_1d(x).astype(float)) for x in sig_i])


def parse_date(s: str) -> pd.Timestamp:
    """Oops/Picasso use YYYY_MM_DD; Chase/Luigi use MMDDYY (2009-2013)."""
    s = str(s)
    if "_" in s:
        return pd.to_datetime(s, format="%Y_%m_%d")
    return pd.to_datetime(s, format="%m%d%y")


def main() -> int:
    m = loadmat(str(MAT), squeeze_me=True, struct_as_record=False)
    rows = []
    for mk in ("Chase", "Luigi", "Oops", "Picasso"):
        mon = getattr(m["unitsort"], mk)
        for ar in [f for f in dir(mon) if not f.startswith("_")]:
            a = getattr(mon, ar)
            us = a.unitsum
            has_sig = hasattr(us, "sig")
            n = len(np.atleast_1d(us.maxsigM))
            for i in range(n):
                mM = float(np.atleast_1d(us.maxsigM)[i])
                se = float(np.atleast_1d(us.maxsigSE)[i])
                n_active = np.nan
                if has_sig:
                    sig_i = us.sig[i] if n > 1 else us.sig
                    mx = per_channel_max(sig_i)
                    n_active = len(mx)
                    # the verified identity - refuse to export if it breaks
                    assert abs(float(mx.mean()) - mM) < 1e-6 * max(1, abs(mM)), \
                        f"{mk}.{ar} session {i}: maxsigM identity broken"
                # Luigi stores no absolute dates, only days post implant
                date = (parse_date(np.atleast_1d(a.dates)[i])
                        if hasattr(a, "dates") else pd.NaT)
                dpi = (float(np.atleast_1d(a.dayvec)[i])
                       if hasattr(a, "dayvec") else np.nan)
                rows.append(dict(
                    subject=mk, array=str(ar),
                    coating=str(getattr(a, "coating", "")),
                    arrayloc=str(getattr(a, "arrayloc", "")),
                    date=date, days_post_implant=dpi,
                    max_p2p_mean_nan=mM, max_p2p_se=se,
                    n_active=n_active, definition="tdt_sig"))
    t = pd.DataFrame(rows).sort_values(["subject", "array", "date"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    t.to_parquet(OUT, index=False)
    print(t.groupby(["subject", "array", "coating"], observed=True).agg(
        sessions=("date", "size"),
        first=("date", "min"), last=("date", "max"),
        med=("max_p2p_mean_nan", "median")).to_string())
    print(f"\nwrote {OUT}  ({len(t)} sessions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

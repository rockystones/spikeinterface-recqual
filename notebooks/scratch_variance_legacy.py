"""W-020 step 5: legacy-cohort (TDT era) sham-contrast resampling.

Repeats Analysis 1 on the compiled per-channel amplitude sets from
`monkey_units_compiled.mat` (`unitsum.sig`, definition tdt_sig - see
docs/notes/longitudinal_metrics.md). Resampling ONLY: the sig arrays
carry no channel identity across sessions, so channel-month means and
the MoM components are not constructible here.

Coverage and caveats (recorded 2026-09-17):
- Subjects WITH per-channel sig: Chase (1 array), Oops (A/B),
  Picasso (A/B). Luigi stores only the precomputed session mean and is
  excluded. 5 arrays, 2 same-implant pairs, 3 subjects.
- BOTH legacy pairs are coated-vs-uncoated -> contaminated; there is
  no clean-pair column in this cohort.
- month_post: Chase from dayvec; Oops/Picasso anchored at each
  subject's first session (no implant date in the compile) - flagged.
- Cells pool channel values ACROSS the month's sessions (no channel
  identity to average over), so the within-array SD includes vE and
  the between/within efficiency ratios are CONSERVATIVE (understated)
  relative to the modern cohort's channel-mean cells.
- log10 uV, matching R-020's primary scale.

Output: results/05_legacy_resampling.md + .csv
Run: uv run python notebooks/scratch_variance_legacy.py
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scratch_variance_design as svd  # noqa: E402  (shared machinery)

REPO = Path(__file__).resolve().parent.parent
RES = REPO / "results"
MAT = Path(r"D:/Claude Code/Monkey Data/Legacy/L1MonkeyData/ephys"
           ) / "monkey_units_compiled.mat"

# legacy pairs are all coated-vs-uncoated: no clean pair exists
svd.CLEAN_PAIR.update({("Chase", "I1"): False, ("Oops", "I1"): False,
                       ("Picasso", "I1"): False})


def load_legacy_cells() -> dict:
    """month -> array_uid -> pooled per-channel log10 amplitudes."""
    m = loadmat(str(MAT), squeeze_me=True, struct_as_record=False)
    from scratch_maxsig_tdt import parse_date, per_channel_max
    cells: dict = {}
    n_sess = 0
    for mk in ("Chase", "Oops", "Picasso"):
        mon = getattr(m["unitsort"], mk)
        arrays = [f for f in dir(mon) if not f.startswith("_")]
        # per-subject month anchor: dayvec where present, else first date
        anchor = None
        for ar in arrays:
            a = getattr(mon, ar)
            if hasattr(a, "dates"):
                d0 = parse_date(np.atleast_1d(a.dates)[0])
                anchor = d0 if anchor is None else min(anchor, d0)
        for ar in arrays:
            a = getattr(mon, ar)
            us = a.unitsum
            if not hasattr(us, "sig"):
                continue
            n = len(np.atleast_1d(us.maxsigM))
            uid = f"{mk}:I1:{ar}"
            for i in range(n):
                sig_i = us.sig[i] if n > 1 else us.sig
                mx = per_channel_max(sig_i)      # per-channel max sig
                mx = mx[mx > 0]
                if not len(mx):
                    continue
                if hasattr(a, "dayvec"):
                    days = float(np.atleast_1d(a.dayvec)[i])
                else:
                    days = (parse_date(np.atleast_1d(a.dates)[i])
                            - anchor).days
                month = int(days // svd.DAYS_PER_MONTH)
                cells.setdefault(month, {}).setdefault(uid, []).append(
                    np.log10(mx))
                n_sess += 1
    # pool sessions within each (month, array) cell
    out: dict = {}
    for mth, arrays in cells.items():
        for uid, chunks in arrays.items():
            v = np.concatenate(chunks)
            if len(v) >= svd.MIN_ACTIVE:
                out.setdefault(mth, {})[uid] = v
    print(f"legacy: {n_sess} sessions pooled into "
          f"{sum(len(a) for a in out.values())} array-month cells, "
          f"months {min(out)}-{max(out)}")
    return out


def main() -> int:
    RES.mkdir(exist_ok=True)
    cells = load_legacy_cells()
    lines = ["# Analysis 5 - legacy-cohort (TDT) sham resampling, "
             "log10 uV",
             "", "Chase/Oops/Picasso per-channel sig sets; Luigi has no "
             "per-channel data. Both pairs coated-vs-uncoated "
             "(contaminated); cells pool sessions (no channel identity) "
             "so ratios are conservative.", ""]
    recs = []
    for matched in (False, True):
        d = svd.sham_contrasts(cells, matched)
        rows = {}
        for des in ("within", "between_array", "between_subject"):
            rows[des] = svd.sd_with_ci(d, des)
        sw = rows["within"][0]
        for key, (sd, lo, hi, n) in rows.items():
            eff = (sd / sw) ** 2 if sw else np.nan
            recs.append(dict(metric="tdt_sig:logamp",
                             variant="matched" if matched else
                             "realistic", contrast=key, sd=sd,
                             ci_lo=lo, ci_hi=hi, n_units=n,
                             efficiency_vs_within=eff))
            lines.append(
                f"- {'matched' if matched else 'realistic'} / {key}: "
                f"SD={sd:.4f} [{lo:.4f},{hi:.4f}] n_units={n}  "
                f"eff x{eff:.2f}")
        lines.append("")
    pd.DataFrame(recs).to_csv(RES / "05_legacy_resampling.csv",
                              index=False)
    (RES / "05_legacy_resampling.md").write_text("\n".join(lines),
                                                 encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

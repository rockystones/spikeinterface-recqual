"""W-020 step 6: stripe-conditioned variance analyses (unblocked by D-014).

With the stripe map ruled (D-014: col-parity stripes, even columns L1,
Fisk families corrected), the parked analyses run on the per-channel
max-P2P table and the yield indicator, Nigel + Fisk arrays only:

1. STRIPE CONTRAST + TOST. Per (array, month) cell, the paired
   within-cell contrast d = mean(L1 channels) - mean(non-L1) on
   channel month-means (log10 uV; and active fraction for yield).
   Equivalence is tested per array with TOST against two bounds:
   +/-0.041 log10 (the smallest whole-array coating effect measured in
   R-017, ofs 1.08x -> what the L1 literature claims should be there)
   and +/-0.10 log10 (the R-017 legacy-metric effect, 1.26x). The
   row-parity split of the same channels is the KNOWN-NULL control -
   no treatment runs along rows.
2. CONDITION-VS-TETHER. The stripe-contrast SD against the same-month
   between-array (pedestal) contrast from the main analysis: how large
   is the treatment axis relative to the device axis it is nested in?
3. STRIPE-RESIDUALIZED COMPONENTS. vS and rho for the Nigel/Fisk
   subset with and without removing per-(array, month, stripe-group)
   means - does conditioning on treatment change the variance verdict?
4. SPILLOVER EXPOSURE (structural statement, not an estimate): stripes
   alternate single CMP columns at 400 um pitch, so EVERY control
   electrode is adjacent to a treated column. The within-array
   contrast therefore estimates (treatment - spillover); phi itself
   needs the histology radial bins (cross-repo, parked).

Caveat carried from surface_conditions.md: col-parity contrasts ride
on smooth col gradients; the gradient-corrected second-difference
estimator lives in the surface pipeline. Here the row-parity control
quantifies how much a no-treatment parity split moves on the same
channels - read the stripe contrast against that yardstick.

Output: results/06_stripe_conditioned.md + .csv
Run: uv run python notebooks/scratch_variance_stripes.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scratch_variance_design as svd  # noqa: E402
from scratch_surface_conditions import surface_map  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
RES = REPO / "results"

# shard `array` value -> CMP serial (Nigel by anatomy, Fisk by serial)
SERIALS = {("Nigel", "Anterior"): "1025-001496",
           ("Nigel", "Posterior"): "1025-001473",
           ("Fisk", "SN1498"): "1025-001498",
           ("Fisk", "SN1504"): "1025-001504"}
# TOST equivalence bounds on log10 amplitude (see module docstring)
BOUNDS_LOG = (0.041, 0.10)
BOUNDS_YIELD = (0.05, 0.10)          # active-fraction points


def stripe_labels() -> pd.DataFrame:
    """channel_id -> stripe membership per (subject, array)."""
    rows = []
    for (sub, arr), serial in SERIALS.items():
        d = surface_map(serial)[["channel_id", "col", "row", "has_l1",
                                 "condition"]].copy()
        d["subject"], d["array"] = sub, arr
        d["row_even"] = d["row"] % 2 == 0   # the known-null axis
        rows.append(d)
    return pd.concat(rows, ignore_index=True)


def cell_contrasts(t: pd.DataFrame, col: str, split: str
                   ) -> pd.DataFrame:
    """Per (array, month) paired contrast on channel month-means.

    split: 'has_l1' (treatment axis) or 'row_even' (known-null axis).
    """
    cm = (t.groupby(["subject", "array", "month_post", "channel_id",
                     split], observed=True)[col].mean().reset_index())
    rows = []
    for (sub, arr, m), g in cm.groupby(
            ["subject", "array", "month_post"], observed=True):
        a = g.loc[g[split], col]
        b = g.loc[~g[split], col]
        if len(a) < 6 or len(b) < 6:
            continue
        rows.append(dict(subject=sub, array=arr, month=m,
                         d=a.mean() - b.mean(),
                         n_a=len(a), n_b=len(b)))
    return pd.DataFrame(rows)


def tost(d: np.ndarray, bound: float) -> tuple[float, float, float]:
    """Paired TOST across cells: mean, 90% CI half-width, p_equiv."""
    n = len(d)
    m, se = float(np.mean(d)), float(np.std(d, ddof=1) / np.sqrt(n))
    p_lo = stats.t.sf((m + bound) / se, n - 1)     # H0: m <= -bound
    p_hi = stats.t.sf(-(m - bound) / se, n - 1)    # H0: m >= +bound
    p = max(p_lo, p_hi)
    hw = stats.t.ppf(0.95, n - 1) * se             # 90% CI half-width
    return m, hw, p


def main() -> int:
    RES.mkdir(exist_ok=True)
    labs = stripe_labels()

    # amplitude table (Nigel + Fisk only) and the yield table
    ta = svd.load_table()
    ta = ta[ta.subject.isin(["Nigel", "Fisk"])].merge(
        labs, on=["subject", "array", "channel_id"], how="inner")
    ty = svd.load_yield_table()
    ty = ty[ty.subject.isin(["Nigel", "Fisk"])].merge(
        labs, on=["subject", "array", "channel_id"], how="inner")
    print(f"amplitude rows {len(ta)}, yield rows {len(ty)} "
          f"(4 arrays, stripe-labelled)")

    lines = ["# Analysis 6 - stripe-conditioned (D-014 map)", "",
             "Paired within-(array,month) contrasts, channel "
             "month-means; row-parity = known-null control on the "
             "same channels. TOST bounds: amplitude +/-0.041 and "
             "+/-0.10 log10 (R-017's smallest and legacy coating "
             "effects); yield +/-0.05 and +/-0.10 active-fraction.",
             ""]
    recs = []

    # --- 1: stripe contrast + TOST, per array -----------------------
    for name, t, col, bounds in (("amplitude_log10", ta, "logamp",
                                  BOUNDS_LOG),
                                 ("yield_fraction", ty, "active",
                                  BOUNDS_YIELD)):
        for split, axis in (("has_l1", "stripe"),
                            ("row_even", "row_control")):
            cc = cell_contrasts(t, col, split)
            for (sub, arr), g in cc.groupby(["subject", "array"],
                                            observed=True):
                d = g.d.to_numpy()
                for bound in bounds:
                    m, hw, p = tost(d, bound)
                    recs.append(dict(metric=name, axis=axis,
                                     subject=sub, array=arr,
                                     n_cells=len(d), mean=m,
                                     ci90_lo=m - hw, ci90_hi=m + hw,
                                     bound=bound, p_equiv=p))
                m, hw, p1 = tost(d, bounds[0])
                _, _, p2 = tost(d, bounds[1])
                lines.append(
                    f"- {name} / {axis} / {sub} {arr}: "
                    f"d={m:+.4f} [{m - hw:+.4f},{m + hw:+.4f}] "
                    f"(n={len(d)} cells)  "
                    f"p_equiv(+/-{bounds[0]})={p1:.3g}, "
                    f"(+/-{bounds[1]})={p2:.3g}")
        lines.append("")

    # --- 2: condition vs tether -------------------------------------
    # stripe-contrast SD across cells vs the between-array (pedestal)
    # contrast SD on the same subjects/months, from the main machinery
    cc = cell_contrasts(ta, "logamp", "has_l1")
    cells = svd.cell_values(ta, "logamp")
    ba = svd.sham_contrasts(cells, matched=False)
    sd_stripe = float(cc.d.std(ddof=1))
    sd_arr = float(ba[ba.design == "between_array"].d.std(ddof=1))
    lines += [f"- condition-vs-tether (log10 amp, Nigel+Fisk): stripe-"
              f"contrast SD {sd_stripe:.4f} vs between-array SD "
              f"{sd_arr:.4f} -> device axis {sd_arr / sd_stripe:.1f}x "
              f"the treatment axis", ""]
    recs.append(dict(metric="amplitude_log10", axis="stripe_sd",
                     subject="all", array="all", n_cells=len(cc),
                     mean=sd_stripe))
    recs.append(dict(metric="amplitude_log10", axis="between_array_sd",
                     subject="all", array="all",
                     n_cells=int((ba.design == "between_array").sum()),
                     mean=sd_arr))

    # --- 3: stripe-residualized components on the Nigel/Fisk subset --
    c0 = svd.variance_components(ta, "logamp")
    tr = ta.copy()
    grp = ["array_uid", "month_post", "has_l1"]
    tr["logamp"] = (tr.logamp
                    - tr.groupby(grp, observed=True).logamp
                    .transform("mean")
                    + tr.groupby(["array_uid", "month_post"],
                                 observed=True).logamp
                    .transform("mean"))
    c1 = svd.variance_components(tr, "logamp")
    lines += [f"- components (Nigel+Fisk subset), raw vs stripe-"
              f"residualized: vS {c0['vS']:.4f} -> {c1['vS']:.4f}, "
              f"vE {c0['vE']:.4f} -> {c1['vE']:.4f}, "
              f"rho {c0['rho']:.3f} -> {c1['rho']:.3f}", "",
              "- spillover: stripes alternate single 400-um columns, "
              "so every control electrode neighbours a treated "
              "column; the stripe contrast estimates "
              "(treatment - spillover). phi needs the histology "
              "radial bins (cross-repo, parked)."]

    pd.DataFrame(recs).to_csv(RES / "06_stripe_conditioned.csv",
                              index=False)
    (RES / "06_stripe_conditioned.md").write_text("\n".join(lines),
                                                  encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

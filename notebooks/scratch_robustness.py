"""How much can a longitudinal conclusion be trusted, per metric and per layer.

Four questions the owner asked, answered from what the earlier sessions already
measured rather than from impressions:

  Q2  does post-sorting curation help, and how much?
  Q3  how robust is the sorting-based layer for longitudinal work?
  Q4  how robust is the sorting-free layer, and how do the two compare?

(Q1 -- whether the sorter parameters are right -- is *not* answerable from this
data and is treated separately in docs/notes/robustness.md.)

Everything here is a re-cut of existing tables. No NEV is read.

    floor/wf_pairs.parquet          operator and algorithm spread, per metric
    rocky/sensitivity_rho.parquet   trend under 18 gate/method/cohort variants
    rocky/longitudinal_metrics.parquet   both layers, same sessions
    cohort/cohort_trends.parquet    8 array-implants, 3 subjects
    cohort/headstage_free_pairs.parquet  amplifier sensitivity, sorting-free

Run from repo root:

    uv run python notebooks/scratch_robustness.py

See:
- docs/notes/robustness.md
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

D = REPO / "data" / "derived"
OUT = D / "robustness_scorecard.parquet"

# Sorting-free metrics and their nearest sorting-based counterpart, so the two
# layers can be compared on the same underlying quantity rather than in general.
LAYER_PAIRS = [
    ("crossing_rate_med", "rate_med", "event rate"),
    ("noise_med_free", "noise_med", "noise floor"),
    ("free_amp_p50", "amp_med", "typical amplitude"),
    ("free_amp_p99", "amp_p99", "amplitude tail"),
    ("peak_snr_med", "snr_med", "SNR"),
    ("frac_elec_active", "elec_coverage", "electrode coverage"),
]


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === Q2: does curation help? ===
def curation_effect() -> None:
    banner("Q2  Does post-sorting curation help?")
    p = pd.read_parquet(D / "floor" / "wf_pairs.parquet")
    print("  (a) Gating halves the method-dependence of the answer.")
    print("      Ratio of gated spread to ungated spread; below 1 = the gate")
    print("      removes disagreement between whoever did the sorting.\n")
    rows = []
    for kind, g in p.groupby("kind"):
        r = {"kind": kind, "n": len(g)}
        for m in ("n_units", "amp_med", "snr_med"):
            a = g[f"rel_{m}_all"].median()
            b = g[f"rel_{m}_gated"].median()
            r[m] = round(b / a, 2) if a and np.isfinite(a) and a > 0 else np.nan
        rows.append(r)
    print(pd.DataFrame(rows).set_index("kind").to_string())
    print("\n      Every value below 1 except automatic-vs-DS, where gating")
    print("      makes the unit-count disagreement WORSE (1.46).")

    cur = D / "rocky" / "curation_labels.parquet"
    if not cur.exists():
        return
    c = pd.read_parquet(cur)
    print("\n  (b) What the two curation layers actually reject.")
    tot = len(c)
    gate_pass = int(c.pass_gate.sum())
    print(f"      units scored                    : {tot:,}")
    print(f"      pass the physics gate           : {gate_pass:,} "
          f"({gate_pass / tot:.0%})")
    if "ur_neural" not in c:
        return
    neural = int(c.ur_neural.sum())
    print(f"      UnitRefine calls neural         : {neural:,} "
          f"({neural / tot:.2%})")
    print(f"      of those, also pass the gate    : "
          f"{int((c.pass_gate & c.ur_neural).sum()):,}")

    banner("Q2 (c)  UnitRefine does not work on this data, and here is why")
    from scratch_rocky_methods import UNAVAILABLE_FEATURES

    print(f"  p(neural) over {tot:,} units: median "
          f"{c.ur_p_neural.median():.3f}, max {c.ur_p_neural.max():.3f}")
    print("  It never crosses 0.5 for more than a handful of units, so 99.98%")
    print("  are labelled noise. That is not a statement about the units.\n")
    print(f"  {len(UNAVAILABLE_FEATURES)} of the classifier's input features "
          f"cannot be computed here:")
    for f in UNAVAILABLE_FEATURES:
        print(f"      {f}")
    print("""
  Every one is spatial or drift-based. They need a spike to appear on several
  channels, or to be tracked across depth over time. Two reasons neither holds:

    1. Snippet data has no continuous trace, so drift cannot be measured.
    2. **At 400 um pitch a spike appears on ONE channel.** `spread`,
       `velocity_above/below` and `exp_decay` describe how a waveform decays
       across neighbours; with no neighbours they are undefined even given
       continuous data.

  So the imputer fills them and the classifier decides on a mutilated feature
  vector. CLAUDE.md names UnitRefine as the default curation and cites
  validation on Utah arrays -- that validation cannot have been on
  snippet-only input, and the labels in `curation_labels.parquet` should not
  be used. The physics gate is the only curation layer working here.""")


# %%
# === Q3: robustness of the sorting-based layer ===
def sorted_robustness() -> pd.DataFrame:
    banner("Q3  How robust is the sorting-based layer?")
    floor = pd.read_parquet(D / "floor" / "wf_pairs.parquet")
    sens = pd.read_parquet(D / "rocky" / "sensitivity_rho.parquet")
    tr = pd.read_parquet(D / "cohort" / "cohort_trends.parquet")

    print("  (a) Spread from who/what did the sorting (S09, gated, relative):\n")
    t = floor.groupby("kind")[["rel_n_units_gated", "rel_amp_med_gated",
                               "rel_snr_med_gated"]].median().round(3)
    t.columns = ["unit count", "amplitude", "SNR"]
    print(t.to_string())

    print("\n  (b) Trend stability under 18 analysis variants (Rocky):\n")
    rows = []
    for (arr, col), g in sens.groupby(["array", "column"]):
        rows.append(dict(array=arr, metric=col, n_variants=len(g),
                         rho_min=round(g.rho.min(), 2),
                         rho_max=round(g.rho.max(), 2),
                         rho_range=round(g.rho.max() - g.rho.min(), 2),
                         sign_stable=bool((g.rho < 0).all() or (g.rho > 0).all())))
    sv = pd.DataFrame(rows).sort_values("rho_range", ascending=False)
    print(sv.to_string(index=False))

    print("\n  (c) Does the metric behave the same in every array-implant?\n")
    sc = tr[tr.scope == "screened"]
    rows = []
    for m, g in sc.groupby("metric"):
        sig = g[g.p < 0.05]
        rows.append(dict(
            metric=m, n_arrays=len(g),
            rho_median=round(g.rho.median(), 2),
            rho_sd=round(g.rho.std(), 2),
            n_significant=len(sig),
            same_sign=int(max((g.rho > 0).sum(), (g.rho < 0).sum())),
        ))
    cc = pd.DataFrame(rows).sort_values("rho_sd")
    print(cc.to_string(index=False))
    print("\n      A metric with low rho_sd and a high same_sign count behaves")
    print("      the same way in every animal. That is replication, and it is")
    print("      the strongest robustness evidence available without ground")
    print("      truth.")
    return cc


# %%
# === Q4: sorting-free versus sorting-based ===
def free_vs_sorted() -> pd.DataFrame:
    banner("Q4  Sorting-free versus sorting-based, on the same sessions")
    lm = pd.read_parquet(D / "rocky" / "longitudinal_metrics.parquet")
    lm = lm.dropna(subset=["noise_med"])
    keep = lm.groupby("array").noise_med.transform("median") * 2
    lm = lm[lm.noise_med <= keep]           # the S09 acquisition screen

    hp = D / "cohort" / "headstage_free_pairs.parquet"
    hs = pd.read_parquet(hp) if hp.exists() else None

    print("  Do the two layers agree about the trend, session for session?\n")
    print(f"  {'quantity':20s} {'free rho':>9s} {'sorted rho':>11s} "
          f"{'agree':>7s} {'corr':>7s} {'amp ratio':>10s}")
    rows = []
    for free_col, sort_col, label in LAYER_PAIRS:
        if free_col not in lm.columns or sort_col not in lm.columns:
            continue
        d = lm.dropna(subset=[free_col, sort_col]).copy()
        if len(d) < 20:
            continue
        x = d.date_dt.map(pd.Timestamp.toordinal)
        rf = spearmanr(x, d[free_col])[0]
        rs = spearmanr(x, d[sort_col])[0]
        cor = spearmanr(d[free_col], d[sort_col])[0]
        # Amplifier sensitivity of the sorting-free version, from S12b.
        amp = np.nan
        if hs is not None:
            a, b = f"{free_col}_analog", f"{free_col}_digital"
            if a in hs.columns and b in hs.columns:
                amp = float((hs[a] / hs[b]).median())
        # A rho of -0.01 has no sign worth agreeing about; calling it a match
        # would inflate the agreement count with coin flips.
        agree = ("n/a" if min(abs(rf), abs(rs)) < 0.1
                 else "yes" if np.sign(rf) == np.sign(rs) else "NO")
        print(f"  {label:20s} {rf:9.2f} {rs:11.2f} {agree:>7s} {cor:7.2f} "
              f"{amp:10.2f}" if np.isfinite(amp) else
              f"  {label:20s} {rf:9.2f} {rs:11.2f} {agree:>7s} {cor:7.2f} "
              f"{'-':>10s}")
        rows.append(dict(quantity=label, free_col=free_col, sorted_col=sort_col,
                         rho_free=round(rf, 3), rho_sorted=round(rs, 3),
                         sign_agrees=np.sign(rf) == np.sign(rs),
                         cross_corr=round(cor, 3),
                         amp_ratio_free=round(amp, 3) if np.isfinite(amp)
                         else np.nan))
    out = pd.DataFrame(rows)

    print("\n  What each layer is exposed to:\n")
    print("    sorting-based   sorter choice (0.17-0.36 on counts), operator")
    print("                    (0.16), curation threshold, AND everything the")
    print("                    free layer is exposed to")
    print("    sorting-free    the NSP's online threshold, the noise estimate,")
    print("                    the amplifier -- but NO sorter or operator term")
    print("\n  The free layer is a strict subset of the sorted layer's")
    print("  exposures. It cannot be less robust; the question is whether it")
    print("  still measures the thing of interest.")
    return out


def main() -> int:
    curation_effect()
    cc = sorted_robustness()
    fv = free_vs_sorted()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fv.to_parquet(OUT, engine="pyarrow", index=False)
    print(f"\n  wrote {OUT.relative_to(REPO)}  ({len(fv)} rows)")
    print(f"  (cross-array consistency table has {len(cc)} metrics)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

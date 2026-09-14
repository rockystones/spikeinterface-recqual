"""Q2: does the coating contrast survive the choice of metric?

Rocky I1 is the only Blackrock coated/uncoated pair (Anterior = L1-coated
under the lateral pedestal, Posterior = uncoated medial; Nigel and Fisk
are generation 2 with the coating striped within the array, so no
uncoated control exists - see treatment_effect.md). W1-W5 already showed
the OFS-layer contrast (units/electrode 1.160, p < 1e-4) and that ACROSS
ANIMALS the coating axis reverses while the pedestal axis does not.

This script asks the orthogonal robustness question: within Rocky I1,
does the same-direction contrast appear under every measurement chain -

  ofs        human Plexon sort (units/electrode, median amplitude)
  resort     gated ISO-SPLIT resort
  legacy     exact mean-max-P2P (NaN-fill)
  free       sorting-free (crossing rate, amp_p50, noise)
  sorter:*   each modern sorter's unit count (continuous ns5)
  consensus  units found by >=2 / >=3 of the modern pool

Every number is paired inside the session (aggregation rule): per date
with both arrays, ratio = Anterior(coated) / Posterior(uncoated); report
the median ratio, IQR, n pairs, Wilcoxon p on log-ratios. The contrast
is treatment AND position at once - this script tests metric robustness,
not the deconfound (that is W5).

Rerun as the consensus expansion adds stems (reads current tables).

    uv run python notebooks/scratch_coating_metrics.py

Outputs: data/derived/cohort/coating_by_metric.parquet,
         figures/treatment/W6_coating_by_metric.png
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
DER = REPO / "data" / "derived"
OUT = DER / "cohort" / "coating_by_metric.parquet"
FIG = REPO / "figures" / "treatment" / "W6_coating_by_metric.png"
I2_FROM = pd.Timestamp("2025-04-04")     # Rocky implant boundary
N_CH = 96


def per_session(df: pd.DataFrame, col: str, how: str = "median"
                ) -> pd.DataFrame:
    """One value per (date, array): aggregate duplicates (Analog+Digital)."""
    g = (df.groupby(["date", "array"], observed=True)[col]
         .agg(how).reset_index().rename(columns={col: "value"}))
    return g


def paired_ratio(g: pd.DataFrame, family: str, metric: str) -> dict | None:
    """Anterior/Posterior ratio per date; summary row."""
    piv = g.pivot_table(index="date", columns="array", values="value",
                        aggfunc="median")
    if "Anterior" not in piv or "Posterior" not in piv:
        return None
    piv = piv.dropna()
    piv = piv[(piv.Anterior > 0) & (piv.Posterior > 0)]
    if len(piv) < 5:
        return None
    r = piv.Anterior / piv.Posterior
    logs = np.log(r)
    try:
        p = float(wilcoxon(logs).pvalue)
    except ValueError:
        p = np.nan
    return dict(family=family, metric=metric, n_pairs=int(len(r)),
                ratio_med=float(r.median()),
                ratio_q1=float(r.quantile(0.25)),
                ratio_q3=float(r.quantile(0.75)), p_wilcoxon=p)


def main() -> int:
    rows: list[dict] = []

    # === OFS and resort layers (units_long) ===============================
    u = pd.read_parquet(DER / "rocky" / "units_long.parquet")
    u["date"] = pd.to_datetime(u.date)
    u = u[u.date < I2_FROM]
    ofs = u[u.method == "ofs"]
    cnt = (ofs.groupby(["date", "array"], observed=True).size() / N_CH
           ).reset_index(name="value")
    rows.append(paired_ratio(cnt, "ofs", "units_per_electrode"))
    rows.append(paired_ratio(per_session(ofs, "amplitude_uv"),
                             "ofs", "median_unit_amplitude"))
    res = u[(u.method == "resort") & u.pass_gate.astype(bool)]
    cnt = (res.groupby(["date", "array"], observed=True).size() / N_CH
           ).reset_index(name="value")
    rows.append(paired_ratio(cnt, "resort", "gated_units_per_electrode"))

    # === legacy exact mean-max-P2P ========================================
    m = pd.read_parquet(DER / "cohort" / "mean_max_p2p.parquet")
    m = m[(m.subject == "Rocky")].copy()
    m["date"] = pd.to_datetime(m.date)
    m = m[m.date < I2_FROM].rename(columns={"max_p2p_mean_nan": "value"})
    rows.append(paired_ratio(m[["date", "array", "value"]],
                             "legacy", "mean_max_p2p_nan"))

    # === sorting-free layer ===============================================
    ee = pd.read_parquet(DER / "rocky" / "events_electrode.parquet")
    ee["date"] = pd.to_datetime(ee.date)
    ee = ee[ee.date < I2_FROM]
    for col in ("crossing_rate_hz", "amp_p50", "noise_uv"):
        rows.append(paired_ratio(per_session(ee, col), "free", col))

    # === modern sorters (continuous ns5, unit counts) =====================
    s = pd.read_parquet(DER / "ns5" / "ns5_sorters.parquet")
    s = s[(s.subject == "Rocky") & (s.implant == "I1") & s.error.isna()]
    s["date"] = pd.to_datetime(s.date)
    for name, g in s.groupby("sorter", observed=True):
        rows.append(paired_ratio(
            g.rename(columns={"n_units": "value"})[["date", "array",
                                                    "value"]],
            "sorter", str(name)))

    # === consensus ladder =================================================
    lad = pd.read_parquet(DER / "ns5" / "consensus" /
                          "consensus_ladder.parquet")
    lad = lad[(lad.subject == "Rocky") & (lad.implant == "I1")]
    lad["date"] = pd.to_datetime(lad.date)
    for k in (2, 3):
        g = lad[lad.min_agreement == k]
        rows.append(paired_ratio(
            g.rename(columns={"n_units": "value"})[["date", "array",
                                                    "value"]],
            "consensus", f"units_agreed_by_{k}"))

    t = pd.DataFrame([r for r in rows if r])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    t.to_parquet(OUT, index=False)
    print(t.round(3).to_string(index=False))

    # === forest plot ======================================================
    t = t.iloc[::-1].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7.5, 0.42 * len(t) + 2))
    y = np.arange(len(t))
    fam_color = {"ofs": "#1f77b4", "resort": "#17becf", "legacy": "#9467bd",
                 "free": "#2ca02c", "sorter": "#ff7f0e",
                 "consensus": "#d62728"}
    for i, r in t.iterrows():
        c = fam_color.get(r.family, "k")
        ax.plot([r.ratio_q1, r.ratio_q3], [i, i], "-", color=c, lw=2,
                alpha=0.55)
        ax.plot(r.ratio_med, i, "o", color=c, ms=6)
        ax.annotate(f"n={r.n_pairs}  p={r.p_wilcoxon:.1e}",
                    (max(float(r.ratio_q3), float(r.ratio_med)), i),
                    textcoords="offset points", xytext=(8, -3), fontsize=7)
    ax.axvline(1.0, color="k", lw=0.8, ls="--")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r.family}: {r.metric}" for _, r in t.iterrows()],
                       fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("coated (Anterior) / uncoated (Posterior), "
                  "median of within-session ratios")
    ax.set_title("Rocky I1: the coating contrast under every measurement "
                 "chain\n(direction is also anterior/posterior - the "
                 "deconfound lives in W5)", fontsize=10)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG, dpi=150)
    plt.close(fig)
    print(f"\nwrote {OUT}\nwrote {FIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

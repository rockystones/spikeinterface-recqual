"""Apply UnitRefine curation to the Plexon and automatic sortings.

Asks two questions:

1. Can post-hoc curation rescue a bad automatic sort? If Plexon's output is
   mostly false positives, a good classifier should be able to strip them.
2. Does curation help or hurt a sort that is already gate-filtered?

**Method and its limits.** The UnitRefine classifiers are ordinary sklearn
Pipelines, so they can be driven directly from a metric table without a
SortingAnalyzer -- which matters here because a SortingAnalyzer needs
continuous traces that this cohort does not have.

Of the 37 features the models expect, **22 are supplied and 15 are imputed**,
and the two reasons are worth separating:

* **7 are intrinsically impossible on single-channel snippets** --
  `drift_ptp`, `drift_std`, `drift_mad`, `spread`, `velocity_above`,
  `velocity_below`, `exp_decay`. All describe how a waveform moves or decays
  across channels or across a continuous recording. No amount of extra work
  recovers them from this data.
* **8 are computable but not yet computed** -- `amplitude_cv_range`,
  `rp_contamination`, `sliding_rp_violation`, `sync_spike_2/4/8`,
  `nn_hit_rate`, `nn_miss_rate`. These need only more code and are a
  concrete way to improve this analysis later. The script prints them
  explicitly so the gap stays visible rather than being absorbed into a
  single "imputed" count.

That is a real caveat, not a formality: the models were trained on
Neuropixels-like data, and imputing 40% of the feature space pushes every
unit toward the training median. Results are therefore *indicative*, and the
agreement between UnitRefine and the explicit gate is the quantity of
interest rather than either label taken alone.

Run from repo root:

    uv run python notebooks/scratch_rocky_curation.py

See:
- docs/notes/snippet_sorting.md
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scratch_rocky_methods import UNAVAILABLE_FEATURES

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "data" / "derived" / "rocky"
FIG_DIR = REPO / "figures" / "rocky"
METHODS_IN = OUT_DIR / "methods_long.parquet"
CURATION_OUT = OUT_DIR / "curation_labels.parquet"

NOISE_MODEL = "SpikeInterface/UnitRefine_noise_neural_classifier"
SUA_MODEL = "SpikeInterface/UnitRefine_sua_mua_classifier"
TRUSTED = ["numpy.dtype", "sklearn.pipeline.Pipeline"]

# Our metric names -> the names the UnitRefine pipelines expect.
RENAME = {
    "firing_rate_hz": "firing_rate",
    "n_spikes": "num_spikes",
    "isi_viol_rate": "isi_violations_ratio",
    "rp_violations": "isi_violations_count",
    "peak_to_valley_ms": "peak_to_valley",
    "half_width_ms": "half_width",
    "presence_ratio": "presence_ratio",
    "amplitude_median": "amplitude_median",
    "amplitude_cutoff": "amplitude_cutoff",
    "amplitude_cv_median": "amplitude_cv_median",
    "firing_range": "firing_range",
    "snr": "snr",
    "isolation_distance": "isolation_distance",
    "l_ratio": "l_ratio",
    "d_prime": "d_prime",
    "silhouette": "silhouette",
    "peak_trough_ratio": "peak_trough_ratio",
    "repolarization_slope": "repolarization_slope",
    "recovery_slope": "recovery_slope",
    "num_negative_peaks": "num_negative_peaks",
    "num_positive_peaks": "num_positive_peaks",
}


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def build_feature_frame(df: pd.DataFrame, needed: list[str]) -> pd.DataFrame:
    """Assemble the model's feature matrix from our metric table.

    Parameters
    ----------
    df : pandas.DataFrame
        Long-format unit metrics.
    needed : list of str
        ``pipeline.feature_names_in_``.

    Returns
    -------
    pandas.DataFrame
        Columns exactly ``needed``, in order, NaN where unavailable.
    """
    x = pd.DataFrame(index=df.index)
    src = {v: k for k, v in RENAME.items()}
    for feat in needed:
        if feat in df.columns:
            x[feat] = pd.to_numeric(df[feat], errors="coerce")
        elif feat in src and src[feat] in df.columns:
            x[feat] = pd.to_numeric(df[src[feat]], errors="coerce")
        else:
            x[feat] = np.nan
    return x[needed]


def main() -> int:
    """Run both UnitRefine classifiers over every method's units."""
    from spikeinterface.curation import load_model

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(METHODS_IN)
    df = df[df["method"].notna() & df["unit_id"].notna()].copy()
    df["pass_gate"] = df["pass_gate"].fillna(False).astype(bool)
    print(f"units: {len(df)}   methods: {sorted(df['method'].unique())}")

    banner("Load classifiers")
    noise_model, _ = load_model(repo_id=NOISE_MODEL, trusted=TRUSTED)
    sua_model, _ = load_model(repo_id=SUA_MODEL, trusted=TRUSTED)
    needed = list(noise_model.feature_names_in_)
    x = build_feature_frame(df, needed)
    have = [c for c in needed if x[c].notna().any()]
    miss = [c for c in needed if not x[c].notna().any()]
    print(f"  features expected : {len(needed)}")
    print(f"  computable here   : {len(have)}")
    print(f"  imputed (NaN)     : {len(miss)}  -> {miss}")
    unexpected = sorted(set(miss) - set(UNAVAILABLE_FEATURES))
    if unexpected:
        print(f"  NOTE unexpectedly missing (fixable, not intrinsic): {unexpected}")

    banner("Predict")
    # The published models were pickled under scikit-learn 1.4.2 and this
    # project pins 1.8. SimpleImputer.transform in 1.8 reads a private
    # attribute (_fill_dtype) that 1.4-era pickles do not carry, so the
    # pipeline raises AttributeError before reaching the classifier. Restoring
    # it from the fitted statistics is a faithful reconstruction -- it is
    # exactly what 1.8 computes at fit time -- and touches nothing the model
    # learned. The alternative would be pinning an old sklearn just to run
    # inference, which is worse for the rest of the project.
    for model in (noise_model, sua_model):
        for _, step in getattr(model, "steps", []):
            if step.__class__.__name__ == "SimpleImputer" and not hasattr(
                step, "_fill_dtype"
            ):
                stats = getattr(step, "statistics_", None)
                step._fill_dtype = (
                    stats.dtype if stats is not None else np.dtype("float64")
                )

    df["ur_noise"] = noise_model.predict(x)
    df["ur_sua"] = sua_model.predict(x)
    df["ur_neural"] = df["ur_noise"].astype(str).str.lower().ne("noise")
    print(f"  noise/neural labels : {dict(pd.Series(df['ur_noise']).value_counts())}")
    print(f"  sua/mua labels      : {dict(pd.Series(df['ur_sua']).value_counts())}")

    banner("Per method: gate vs UnitRefine")
    rows = []
    for m, g in df.groupby("method"):
        gate = g["pass_gate"]
        neural = g["ur_neural"]
        both = int((gate & neural).sum())
        rows.append(dict(
            method=m, n_units=len(g),
            gate_pass=int(gate.sum()), gate_frac=round(float(gate.mean()), 3),
            ur_neural=int(neural.sum()), ur_frac=round(float(neural.mean()), 3),
            both=both,
            agree=round(float((gate == neural).mean()), 3),
            ur_rescues=int((~gate & neural).sum()),
            ur_rejects=int((gate & ~neural).sum()),
        ))
    summ = pd.DataFrame(rows).sort_values("method")
    print(summ.to_string(index=False))

    banner("Question 1: can curation rescue the Plexon sort?")
    o = df[df["method"] == "ofs"]
    if len(o):
        print(f"  OFS units                       : {len(o)}")
        print(f"  pass the explicit gate          : {int(o['pass_gate'].sum())}"
              f"  ({o['pass_gate'].mean():.1%})")
        print(f"  UnitRefine calls neural         : {int(o['ur_neural'].sum())}"
              f"  ({o['ur_neural'].mean():.1%})")
        print(f"  both agree it is a real unit    : "
              f"{int((o['pass_gate'] & o['ur_neural']).sum())}")
        rescued = o[~o["pass_gate"] & o["ur_neural"]]
        print(f"  UnitRefine keeps, gate rejects  : {len(rescued)}")
        if len(rescued):
            print(f"     their median SNR             : {rescued['snr'].median():.2f}")
            print(f"     their median amplitude uV    : "
                  f"{rescued['amplitude_uv'].median():.1f}")
            print(f"     median noise floor uV        : "
                  f"{rescued['noise_uv'].median():.1f}")
            print("     -> curation cannot manufacture signal: a unit whose")
            print("        amplitude sits at the noise floor stays unusable")
            print("        whatever label it is given.")

    banner("Question 2: does curation help or hurt the automatic sorts?")
    for m in ("isosplit", "gmm_bic", "hdbscan", "kmeans_sil"):
        g = df[df["method"] == m]
        if not len(g):
            continue
        gate_only = g[g["pass_gate"] & ~g["ur_neural"]]
        ur_only = g[~g["pass_gate"] & g["ur_neural"]]
        print(f"  {m}")
        print(f"    gate keeps {int(g['pass_gate'].sum()):5d} | "
              f"UnitRefine keeps {int(g['ur_neural'].sum()):5d} | "
              f"agree {float((g['pass_gate'] == g['ur_neural']).mean()):.1%}")
        if len(gate_only):
            print(f"    gate-only  (n={len(gate_only):4d}) median SNR "
                  f"{gate_only['snr'].median():.2f}")
        if len(ur_only):
            print(f"    UR-only    (n={len(ur_only):4d}) median SNR "
                  f"{ur_only['snr'].median():.2f}")

    banner("Write + figure")
    keep = ["date", "array", "method", "electrode_id", "unit_id", "snr",
            "amplitude_uv", "noise_uv", "firing_rate_hz", "pass_gate",
            "ur_noise", "ur_sua", "ur_neural"]
    df[[c for c in keep if c in df.columns]].to_parquet(
        CURATION_OUT, engine="pyarrow", index=False)
    print(f"  wrote {CURATION_OUT.name}  rows={len(df)}")

    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
    methods = summ["method"].tolist()
    xs = np.arange(len(methods))
    axes[0].bar(xs - 0.2, summ["gate_frac"], 0.4, label="explicit gate")
    axes[0].bar(xs + 0.2, summ["ur_frac"], 0.4, label="UnitRefine 'neural'")
    axes[0].set_xticks(xs, methods, rotation=20)
    axes[0].set_ylabel("fraction of clusters retained")
    axes[0].set_title("what each curation keeps")
    axes[0].legend(fontsize=9)
    axes[0].grid(alpha=0.3, axis="y")

    for m in methods:
        g = df[df["method"] == m]
        if len(g) > 20:
            axes[1].scatter(g["snr"], g["ur_neural"].astype(float)
                            + np.random.default_rng(0).normal(0, 0.03, len(g)),
                            s=4, alpha=0.25, label=m)
    axes[1].set_xscale("log")
    axes[1].set_xlabel("SNR (log)")
    axes[1].set_yticks([0, 1], ["noise", "neural"])
    axes[1].set_title("UnitRefine label vs SNR")
    axes[1].legend(fontsize=8, markerscale=3)
    axes[1].grid(alpha=0.3)

    fig.suptitle("Rocky: UnitRefine curation vs the explicit noise gate\n"
                 "7 of 37 model features are unavailable on snippet data and "
                 "imputed -- results are indicative", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(FIG_DIR / "15_curation_comparison.png", dpi=150,
                bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {FIG_DIR / '15_curation_comparison.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

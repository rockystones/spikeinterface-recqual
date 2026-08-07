"""How much does the analysis choice move the longitudinal trend?

Every longitudinal number in this project is the output of a chain: which
clusterer ran, which gate it was filtered through, whether artifacts were
removed. A trend that only exists under one setting is a property of the
pipeline, not of the implant. This script varies each link and re-derives the
same trends, so the conclusions can be read with their sensitivity attached.

Three sweeps:

1. **Gate sweep** -- full cohort, ISO-SPLIT clusters held fixed, the gate
   re-applied at different thresholds. Possible because `units_long.parquet`
   stores every candidate cluster with its metrics, including the rejected
   ones, so re-gating is arithmetic rather than a re-run.
2. **Method sweep** -- the 60-session stratified subset, gate held fixed, the
   clusterer varied across ISO-SPLIT, GMM+BIC, HDBSCAN, k-means and Plexon.
3. **Artifact sweep** -- the effect of removing cross-channel artifacts,
   digital impulses and railed events, which act almost entirely on the
   amplitude tail.

The headline output is a sign-and-significance table: for each metric, does the
direction of the longitudinal trend survive every setting?

Run from repo root:

    uv run python notebooks/scratch_rocky_sensitivity.py

See:
- docs/notes/longitudinal_metrics.md
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "data" / "derived" / "rocky"
UNITS_IN = OUT_DIR / "units_long.parquet"
METHODS_IN = OUT_DIR / "methods_long.parquet"
EVENTS_IN = OUT_DIR / "events_electrode.parquet"
FIG_DIR = REPO / "figures" / "rocky" / "sensitivity"
SWEEP_OUT = OUT_DIR / "sensitivity_sweep.parquet"
RHO_OUT = OUT_DIR / "sensitivity_rho.parquet"

ARRAY_COLOR = {"Anterior": "#1f77b4", "Posterior": "#d62728"}
N_ELECTRODES = 96
ROLL = 7

# Gate variants. Each is a predicate over the per-cluster metric columns that
# `scratch_rocky_resort.py` already stores for accepted *and* rejected
# clusters, so the whole sweep is a filter over one parquet.
GATE_VARIANTS: dict[str, dict] = {
    "no gate":        dict(snr=0.0, spikes=1, shape=False, isi=None),
    "SNR>=3":         dict(snr=3.0, spikes=50, shape=True, isi=None),
    "SNR>=4 (default)": dict(snr=4.0, spikes=50, shape=True, isi=None),
    "SNR>=5":         dict(snr=5.0, spikes=50, shape=True, isi=None),
    "SNR>=6":         dict(snr=6.0, spikes=50, shape=True, isi=None),
    "no shape test":  dict(snr=4.0, spikes=50, shape=False, isi=None),
    "spikes>=20":     dict(snr=4.0, spikes=20, shape=True, isi=None),
    "spikes>=200":    dict(snr=4.0, spikes=200, shape=True, isi=None),
    "+ ISI<=0.05":    dict(snr=4.0, spikes=50, shape=True, isi=0.05),
}

# Cohort-composition variants. Not an analysis knob in the usual sense, but the
# single largest lever on every trend in this project: the 2017 block was
# recorded on a different protocol (4900 s sessions against 180 s afterwards,
# no headstage token, a visibly higher NSP threshold) and sits ~2.3x above 2018
# in both noise floor and crossing amplitude. Including it turns a mild decline
# into a steep one. Digitisation is identical throughout (gain 0.25 uV/count,
# nbefore 10, 30 kHz on every file checked), so this is acquisition, not units.
COHORT_VARIANTS: dict[str, str] = {
    "all sessions": "all",
    "exclude 2017": "no2017",
    "Digital headstage only": "digital",
    "180 s sessions only": "short",
}

METRICS = [
    ("units_per_electrode", "yield (units / electrode)"),
    ("n_units", "units per session"),
    ("elec_coverage", "electrode coverage"),
    ("amp_med", "median unit amplitude (uV)"),
    ("amp_p99", "p99 unit amplitude (uV)"),
    ("snr_med", "median unit SNR"),
]

METHOD_LABEL = {
    "isosplit": "ISO-SPLIT", "gmm_bic": "GMM+BIC", "hdbscan": "HDBSCAN",
    "kmeans_sil": "k-means+sil", "ofs": "Plexon OFS",
}


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# === Gating ===
def apply_gate(u: pd.DataFrame, spec: dict) -> pd.Series:
    """Boolean mask of clusters passing one gate variant.

    Parameters
    ----------
    u : pandas.DataFrame
        Per-cluster metric table, accepted and rejected alike.
    spec : dict
        ``snr``, ``spikes``, ``shape`` (bool), ``isi`` (float or None).

    Returns
    -------
    pandas.Series
        One boolean per cluster.
    """
    m = (u["snr"] >= spec["snr"]) & (u["n_spikes"] >= spec["spikes"])
    if spec["shape"]:
        # Physiological peak-to-trough duration, and the trough must sit near
        # the alignment point rather than at the snippet edge.
        m &= u["peak_trough_ms"].between(0.15, 1.20)
        m &= u["trough_offset_ms"].abs() <= 0.20
    if spec["isi"] is not None:
        m &= u["isi_viol_rate"] <= spec["isi"]
    return m.fillna(False)


def session_metrics(u: pd.DataFrame, mask: pd.Series, label: str) -> pd.DataFrame:
    """Collapse gated clusters to per-session metrics tagged with the variant."""
    p = u[mask]
    keys = ["date", "array"]
    out = p.groupby(keys).agg(
        n_units=("unit_id", "size"),
        n_elec_with_units=("electrode_id", "nunique"),
        amp_med=("amplitude_uv", "median"),
        amp_p99=("amplitude_uv", lambda s: s.quantile(0.99)),
        snr_med=("snr", "median"),
    ).reset_index()
    out["units_per_electrode"] = out["n_units"] / N_ELECTRODES
    out["elec_coverage"] = out["n_elec_with_units"] / N_ELECTRODES
    out["variant"] = label
    return out


def cohort_subset(u: pd.DataFrame, kind: str) -> pd.DataFrame:
    """Restrict the cohort, isolating the acquisition confounds one at a time."""
    if kind == "no2017":
        return u[u["date"].str[:4] != "2017"]
    if kind == "digital":
        return u[u["headstage"] == "Digital"]
    if kind == "short":
        return u[u["duration_s"] < 600]
    return u


def rho_table(sweep: pd.DataFrame) -> pd.DataFrame:
    """Spearman rho vs elapsed days for every (variant, array, metric)."""
    rows = []
    for (var, arr), g in sweep.groupby(["variant", "array"]):
        g = g.sort_values("date_dt")
        days = (g["date_dt"] - g["date_dt"].min()).dt.days.to_numpy()
        for col, lbl in METRICS:
            v = g[col].to_numpy(dtype=float)
            ok = np.isfinite(v)
            if ok.sum() < 8:
                continue
            rho, p = spearmanr(days[ok], v[ok])
            rows.append(dict(variant=var, array=arr, metric=lbl, column=col,
                             n=int(ok.sum()), rho=rho, p=p,
                             first5=float(np.nanmedian(v[ok][:5])),
                             last5=float(np.nanmedian(v[ok][-5:]))))
    return pd.DataFrame(rows)


# === Figures ===
def fig_sweep(sweep: pd.DataFrame, out: Path, title: str, order: list[str]) -> None:
    """One panel per metric, one line per variant, columns = arrays."""
    cmap = plt.get_cmap("viridis", max(len(order), 2))
    fig, axes = plt.subplots(len(METRICS), 2, figsize=(12.5, 2.1 * len(METRICS)),
                             sharex=True)
    for i, (col, lbl) in enumerate(METRICS):
        for j, arr in enumerate(["Anterior", "Posterior"]):
            ax = axes[i, j]
            for k, var in enumerate(order):
                g = sweep[(sweep["variant"] == var) & (sweep["array"] == arr)]
                if not len(g):
                    continue
                g = g.sort_values("date_dt")
                roll = g.set_index("date_dt")[col].rolling(
                    ROLL, center=True, min_periods=2).median()
                ax.plot(roll.index, roll.values, "-", lw=1.4, color=cmap(k),
                        label=var if (i == 0 and j == 0) else None)
            ax.tick_params(labelsize=7)
            ax.grid(alpha=0.25, lw=0.5)
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            if i == 0:
                ax.set_title(arr, fontsize=10)
            if j == 0:
                ax.set_ylabel(lbl, fontsize=7.5)
    axes[0, 0].legend(fontsize=6.5, ncol=2, loc="upper right")
    fig.suptitle(title, fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_rho_heatmap(rho: pd.DataFrame, out: Path, title: str,
                    order: list[str]) -> None:
    """Trend direction and strength for every variant, side by side per array.

    This is the figure that answers "does the conclusion depend on the
    setting". A column of one colour means the trend is robust; a column that
    changes sign means it is an artefact of the choice.
    """
    fig, axes = plt.subplots(1, 2, figsize=(13, 0.42 * len(order) + 2.6),
                             sharey=True)
    labels = [lbl for _, lbl in METRICS]
    for ax, arr in zip(axes, ["Anterior", "Posterior"], strict=True):
        mat = np.full((len(order), len(labels)), np.nan)
        for i, var in enumerate(order):
            for j, lbl in enumerate(labels):
                s = rho[(rho["variant"] == var) & (rho["array"] == arr)
                        & (rho["metric"] == lbl)]
                if len(s):
                    mat[i, j] = s.iloc[0]["rho"]
        im = ax.imshow(mat, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=7.5)
        ax.set_yticks(range(len(order)))
        ax.set_yticklabels(order, fontsize=7.5)
        ax.set_title(arr, fontsize=10)
        for i in range(len(order)):
            for j in range(len(labels)):
                if np.isfinite(mat[i, j]):
                    ax.text(j, i, f"{mat[i, j]:+.2f}", ha="center", va="center",
                            fontsize=6.5,
                            color="white" if abs(mat[i, j]) > 0.55 else "black")
    fig.colorbar(im, ax=axes, fraction=0.02, pad=0.02,
                 label="Spearman rho vs elapsed days")
    fig.suptitle(title, fontsize=11)
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_artifact_effect(ev: pd.DataFrame, out: Path) -> None:
    """What removing non-neural events does, metric by metric.

    Cross-channel artifacts, single-sample impulses and railed samples are all
    large by construction, so they distort the tail of the amplitude
    distribution and almost nothing else. Shown as the ratio cleaned/raw so a
    flat line at 1.0 means the correction is irrelevant for that metric.
    """
    keys = ["date", "array"]
    g = ev.groupby(keys).agg(
        raw_rate=("crossing_rate_hz", "median"),
        clean_rate=("crossing_rate_clean_hz", "median"),
        raw_p99=("amp_p99", "median"),
        clean_p99=("amp_p99_clean", "median"),
        raw_max=("amp_max", "max"),
        clean_max=("amp_max_clean", "max"),
        frac_artifact=("frac_artifact", "median"),
        n_impulse=("n_impulse_events", "sum"),
        n_railed=("n_railed_events", "sum"),
        n_events=("n_events", "sum"),
    ).reset_index()
    g["date_dt"] = pd.to_datetime(g["date"])
    g = g.sort_values("date_dt")

    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex=True)
    panels = [
        (("clean_rate", "raw_rate"), "crossing rate", axes[0, 0]),
        (("clean_p99", "raw_p99"), "p99 amplitude", axes[0, 1]),
        (("clean_max", "raw_max"), "session max amplitude", axes[1, 0]),
    ]
    for (num, den), lbl, ax in panels:
        for arr, ga in g.groupby("array"):
            ratio = (ga[num] / ga[den]).rolling(ROLL, center=True,
                                                min_periods=2).median()
            ax.plot(ga["date_dt"], ratio, "-", lw=1.5,
                    color=ARRAY_COLOR.get(arr, "0.4"), label=arr)
        ax.axhline(1.0, color="0.7", lw=0.8, ls=":")
        ax.set_ylabel(f"{lbl}\ncleaned / raw", fontsize=8)
        ax.legend(fontsize=7)

    ax = axes[1, 1]
    for arr, ga in g.groupby("array"):
        ax.semilogy(ga["date_dt"],
                    (ga["frac_artifact"]).rolling(ROLL, center=True,
                                                  min_periods=2).median(),
                    "-", lw=1.5, color=ARRAY_COLOR.get(arr, "0.4"),
                    label=f"{arr} artifact")
        ax.semilogy(ga["date_dt"],
                    (ga["n_impulse"] / ga["n_events"]).rolling(
                        ROLL, center=True, min_periods=2).median(),
                    "--", lw=1.2, color=ARRAY_COLOR.get(arr, "0.4"),
                    label=f"{arr} impulse")
    ax.set_ylabel("fraction of events", fontsize=8)
    ax.legend(fontsize=6.5)

    for ax in axes.ravel():
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.25, lw=0.5)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("Effect of removing non-neural events (artifact / impulse / railed)\n"
                 "flat at 1.0 = the correction does not touch that metric",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)


def print_robustness(rho: pd.DataFrame, order: list[str], header: str) -> None:
    """Report, per metric and array, whether the trend direction is unanimous."""
    print()
    print(header)
    print(f"{'metric':30s} {'array':10s} {'rho range':>18s} "
          f"{'sign':>8s} {'all p<0.05':>11s}")
    print("-" * 82)
    for lbl in [x for _, x in METRICS]:
        for arr in ["Anterior", "Posterior"]:
            s = rho[(rho["metric"] == lbl) & (rho["array"] == arr)
                    & (rho["variant"].isin(order))]
            if not len(s):
                continue
            lo, hi = s["rho"].min(), s["rho"].max()
            sign = ("negative" if hi < 0 else
                    "positive" if lo > 0 else "SPLIT")
            allsig = "yes" if (s["p"] < 0.05).all() else "no"
            print(f"{lbl:30s} {arr:10s} {lo:+8.3f} .. {hi:+6.3f} "
                  f"{sign:>8s} {allsig:>11s}")


def main() -> int:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    units = pd.read_parquet(UNITS_IN)
    ev = pd.read_parquet(EVENTS_IN)

    # === Sweep 1: gate ===
    banner("Gate sweep (full cohort, ISO-SPLIT clusters fixed)")
    u = units[units["method"] == "resort"].copy()
    print(f"  candidate clusters: {len(u):,} over "
          f"{u.groupby(['date', 'array']).ngroups} sessions")
    parts = []
    for label, spec in GATE_VARIANTS.items():
        mask = apply_gate(u, spec)
        parts.append(session_metrics(u, mask, label))
        print(f"    {label:20s} -> {int(mask.sum()):7,} units "
              f"({mask.mean() * 100:5.1f}% of candidates)")
    gate_sweep = pd.concat(parts, ignore_index=True)
    gate_sweep["date_dt"] = pd.to_datetime(gate_sweep["date"])

    gate_rho = rho_table(gate_sweep)
    gate_order = list(GATE_VARIANTS)
    fig_sweep(gate_sweep, FIG_DIR / "S1_gate_sweep.png",
              "Longitudinal trends under nine gate settings "
              "(same clusters throughout)", gate_order)
    fig_rho_heatmap(gate_rho, FIG_DIR / "S2_gate_rho.png",
                    "Trend direction under each gate setting", gate_order)
    print_robustness(gate_rho, gate_order,
                     "Robustness of the trend to the gate:")

    # === Sweep 2: clustering method ===
    banner("Method sweep (60-session stratified subset, gate fixed)")
    meth = pd.read_parquet(METHODS_IN)
    meth["pass_gate"] = meth["pass_gate"].fillna(False).astype(bool)
    mparts = []
    for name, g in meth.groupby("method"):
        lbl = METHOD_LABEL.get(name, name)
        mparts.append(session_metrics(g, g["pass_gate"], lbl))
        print(f"    {lbl:14s} -> {int(g['pass_gate'].sum()):6,} units "
              f"of {len(g):7,} candidates over "
              f"{g.groupby(['date', 'array']).ngroups} sessions")
    method_sweep = pd.concat(mparts, ignore_index=True)
    method_sweep["date_dt"] = pd.to_datetime(method_sweep["date"])
    method_rho = rho_table(method_sweep)
    method_order = [METHOD_LABEL.get(m, m) for m in sorted(meth["method"].unique())]
    fig_sweep(method_sweep, FIG_DIR / "S3_method_sweep.png",
              "Longitudinal trends under five clustering methods "
              "(identical gate, identical spikes)", method_order)
    fig_rho_heatmap(method_rho, FIG_DIR / "S4_method_rho.png",
                    "Trend direction under each clustering method", method_order)
    print_robustness(method_rho, method_order,
                     "Robustness of the trend to the clustering method:")

    # === Sweep 3: cohort composition ===
    banner("Cohort sweep (default gate, sessions restricted)")
    default = GATE_VARIANTS["SNR>=4 (default)"]
    cparts = []
    for label, kind in COHORT_VARIANTS.items():
        sub = cohort_subset(u, kind)
        mask = apply_gate(sub, default)
        cparts.append(session_metrics(sub, mask, label))
        print(f"    {label:24s} -> {sub.groupby(['date', 'array']).ngroups:4d} sessions,"
              f" {int(mask.sum()):7,} units")
    cohort_sweep = pd.concat(cparts, ignore_index=True)
    cohort_sweep["date_dt"] = pd.to_datetime(cohort_sweep["date"])
    cohort_rho = rho_table(cohort_sweep)
    cohort_order = list(COHORT_VARIANTS)
    fig_sweep(cohort_sweep, FIG_DIR / "S6_cohort_sweep.png",
              "Longitudinal trends under four cohort restrictions "
              "(same gate, same clusters)", cohort_order)
    fig_rho_heatmap(cohort_rho, FIG_DIR / "S7_cohort_rho.png",
                    "Trend direction under each cohort restriction", cohort_order)
    print_robustness(cohort_rho, cohort_order,
                     "Robustness of the trend to cohort composition:")

    # === Sweep 4: artifact removal ===
    banner("Artifact / impulse / rail removal")
    fig_artifact_effect(ev, FIG_DIR / "S5_artifact_effect.png")
    tot = ev[["n_events", "n_artifact_events", "n_impulse_events",
              "n_railed_events"]].sum()
    print(f"  events                 {int(tot['n_events']):,}")
    for k, lbl in [("n_artifact_events", "cross-channel artifact"),
                   ("n_impulse_events", "single-sample impulse"),
                   ("n_railed_events", "railed (ADC saturation)")]:
        print(f"  {lbl:24s} {int(tot[k]):12,}  "
              f"({tot[k] / tot['n_events'] * 100:.4f}%)")
    raw_max = ev.groupby(["date", "array"])["amp_max"].max()
    clean_max = ev.groupby(["date", "array"])["amp_max_clean"].max()
    print(f"\n  session max amplitude: median {raw_max.median():.0f} uV raw "
          f"-> {clean_max.median():.0f} uV cleaned")
    p99 = ev["amp_p99"].median()
    p99c = ev["amp_p99_clean"].median()
    print(f"  electrode p99         : median {p99:.1f} uV raw -> {p99c:.1f} uV cleaned")

    # === Persist ===
    sweep = pd.concat([gate_sweep.assign(sweep="gate"),
                       method_sweep.assign(sweep="method"),
                       cohort_sweep.assign(sweep="cohort")], ignore_index=True)
    rho = pd.concat([gate_rho.assign(sweep="gate"),
                     method_rho.assign(sweep="method"),
                     cohort_rho.assign(sweep="cohort")], ignore_index=True)
    sweep.to_parquet(SWEEP_OUT, engine="pyarrow", index=False)
    rho.to_parquet(RHO_OUT, engine="pyarrow", index=False)

    banner("Done")
    for p in sorted(FIG_DIR.glob("S*.png")):
        print(f"  {p.name}")
    print(f"  {SWEEP_OUT.name}  ({len(sweep)} rows)")
    print(f"  {RHO_OUT.name}  ({len(rho)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

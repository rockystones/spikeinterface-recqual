"""The giant-event taxonomy across three animals, and what pooling hides.

`scratch_rocky_events.py` classified large-amplitude events on Rocky;
`scratch_giants_cohort.py` ran the same pass on Nigel and Fisk. This compares
them, and the comparison turns almost entirely on one methodological point:

**Pooling every event across sessions is not a summary of the animal.** Session
event counts span two orders of magnitude here, so a pooled ratio is a
statement about the largest few sessions. On Rocky the pooled `local_cluster`
share reads 21.4% against a per-session median of 4.2%; on Fisk the pooled
artifact share reads 29.1% against a per-session median of 0.04%, a factor of
668. Every number below is a per-session median unless it says otherwise.

    X1_composition   class shares, per-session median against the pooled value
    X2_concentration where the artifacts actually are
    X3_rates         giants normalised by time and channel, against the bulk
                     amplitude distribution that does not explain them
    X4_longitudinal  giant rate over each implant's life

Run from repo root:

    uv run python notebooks/scratch_giants_compare.py

See:
- docs/notes/giant_events.md
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
DERIVED = REPO / "data" / "derived"
FIG = REPO / "figures" / "giants"

SUBJECTS = ("Rocky", "Nigel", "Fisk")
SUBJ_COLOR = {"Rocky": "#1f77b4", "Nigel": "#2ca02c", "Fisk": "#d62728"}
# Mutually exclusive; they sum to n_giant_total. axonal_like and regular_shape
# are flags that cut across these, not classes, and are excluded here.
CLASSES = ["isolated", "local_cluster", "scattered_few", "multi_channel",
           "artifact", "impulse", "railed"]
NON_NEURAL = ("artifact", "impulse", "railed")


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def load() -> pd.DataFrame:
    """One row per session x array, from every subject that has been run."""
    out = []
    for s in SUBJECTS:
        p = DERIVED / s.lower() / "events_electrode.parquet"
        if not p.exists():
            print(f"  ! {s}: no events_electrode.parquet, skipping")
            continue
        d = pd.read_parquet(p)
        agg = {"events": ("n_events", "sum"),
               "giants": ("n_giant_total", "sum"),
               "dur": ("duration_s", "first"),
               "nch": ("channel_id", "nunique"),
               "noise": ("noise_uv", "median"),
               "snr": ("peak_snr", "median"),
               "chance_big": ("chance_coincidence_big", "first")}
        for c in CLASSES + ["axonal_like"]:
            col = f"n_giant_{c}"
            if col in d:
                agg[c] = (col, "sum")
        for c in ("amp_p50", "amp_p90", "amp_p99", "amp_max"):
            if c in d:
                agg[c] = (c, "median")
        g = d.groupby(["date", "array"]).agg(**agg).reset_index()
        g["subject"] = s
        out.append(g)
    a = pd.concat(out, ignore_index=True)
    a["date"] = pd.to_datetime(a.date)
    # per-channel, per-second: the only normalisation that is comparable when
    # session length and event density both vary between animals
    a["ev_hz_ch"] = a.events / a.dur / a.nch
    a["giant_hz_ch"] = a.giants / a.dur / a.nch
    for c in CLASSES:
        if c in a:
            a[f"{c}_share"] = a[c] / a.giants.replace(0, np.nan)
            a[f"{c}_hz_ch"] = a[c] / a.dur / a.nch
    return a


# %%
def fig_composition(a: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Class shares, and the pooled value alongside, so the gap is visible."""
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.6))

    ax = axes[0]
    present = [c for c in CLASSES if c in a]
    idx = np.arange(len(present))
    width = 0.26
    for k, s in enumerate(SUBJECTS):
        g = a[a.subject == s]
        if not len(g):
            continue
        med = [g[f"{c}_share"].median() * 100 for c in present]
        ax.bar(idx + (k - 1) * width, med, width,
               color=SUBJ_COLOR[s], label=s)
    ax.set_xticks(idx)
    ax.set_xticklabels(present, fontsize=8.5, rotation=20, ha="right")
    ax.set_ylabel("% of a session's giant events")
    ax.set_title("per-session median — the honest summary", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25, axis="y")

    # the same quantities pooled, which is what a naive concat would report
    ax = axes[1]
    for k, s in enumerate(SUBJECTS):
        g = a[a.subject == s]
        if not len(g):
            continue
        pooled = [100 * g[c].sum() / g.giants.sum() for c in present]
        ax.bar(idx + (k - 1) * width, pooled, width,
               color=SUBJ_COLOR[s], label=s, alpha=0.85, hatch="//")
    ax.set_xticks(idx)
    ax.set_xticklabels(present, fontsize=8.5, rotation=20, ha="right")
    ax.set_ylabel("% of all giant events, pooled")
    ax.set_title("pooled over sessions — dominated by the largest few",
                 fontsize=10)
    ax.grid(alpha=0.25, axis="y")

    fig.suptitle("Giant-event composition: the same data, two normalisations",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)

    rows = []
    for s in SUBJECTS:
        g = a[a.subject == s]
        if not len(g):
            continue
        for c in present:
            rows.append(dict(subject=s, klass=c, n=len(g),
                             median_pct=round(g[f"{c}_share"].median() * 100, 3),
                             pooled_pct=round(100 * g[c].sum() / g.giants.sum(), 3)))
    r = pd.DataFrame(rows)
    r["pooled_over_median"] = (r.pooled_pct / r.median_pct.replace(0, np.nan)).round(1)
    return r


# %%
def fig_concentration(a: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Artifacts are not a background rate. They are a few bad sessions.

    A Lorenz curve over sessions: sort by artifact count and plot the
    cumulative share. If artifacts were spread evenly the curve would be the
    diagonal; in all three animals it is against the wall.
    """
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))

    ax = axes[0]
    rows = []
    for s in SUBJECTS:
        g = a[a.subject == s]
        if not len(g) or "artifact" not in g:
            continue
        v = np.sort(g.artifact.fillna(0).to_numpy())[::-1]
        if v.sum() <= 0:
            continue
        cum = np.cumsum(v) / v.sum()
        x = np.arange(1, len(v) + 1) / len(v)
        ax.plot(x * 100, cum * 100, lw=2, color=SUBJ_COLOR[s],
                label=f"{s} (n={len(v)})")
        k = max(1, int(round(0.05 * len(v))))
        rows.append(dict(subject=s, sessions=len(v), top5pct_sessions=k,
                         share_of_artifacts=round(100 * v[:k].sum() / v.sum(), 1)))
    ax.plot([0, 100], [0, 100], "k--", lw=1, label="if spread evenly")
    ax.set_xlabel("% of sessions, worst first")
    ax.set_ylabel("cumulative % of artifact giants")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 101)
    ax.set_title("the worst 5% of sessions hold >90% of artifacts",
                 fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    # what a per-session artifact count actually looks like
    ax = axes[1]
    for s in SUBJECTS:
        g = a[a.subject == s]
        if not len(g) or "artifact" not in g:
            continue
        v = g.artifact.fillna(0) + 1          # +1 so zeros survive a log axis
        ax.hist(v, bins=np.logspace(0, 6.5, 40), alpha=0.55,
                color=SUBJ_COLOR[s], label=s)
    ax.set_xscale("log")
    ax.set_xlabel("artifact giants per session (+1)")
    ax.set_ylabel("sessions")
    ax.set_title("most sessions have almost none", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    fig.suptitle("Artifact contamination is a session-level flag, "
                 "not a background rate", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return pd.DataFrame(rows)


# %%
def fig_rates(a: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Nigel's deficit is in the far tail only; the bulk distribution matches.

    Three panels, because the conclusion needs all three: the event rate is
    *highest* on Nigel, the giant rate is 13x *lowest*, and on the ordinary
    amplitude percentiles Nigel is never the lowest -- it sits between Rocky
    and Fisk at p90, p99 and max. Any one panel alone invites the wrong
    explanation, and the third is what rules out "Nigel simply has smaller
    spikes": if that were true its percentiles would sit below both.

    Amplitudes are divided by each session's own noise floor, so a gain or
    noise difference cannot masquerade as an amplitude difference.
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    rng = np.random.default_rng(7)

    for ax, metric, label, title in (
            (axes[0], "ev_hz_ch", "events / s / channel",
             "Nigel detects the MOST events"),
            (axes[1], "giant_hz_ch", "giants (>250 uV) / s / channel",
             "and the FEWEST giants, by 13x")):
        for i, s in enumerate(SUBJECTS, start=1):
            v = a[a.subject == s][metric].dropna()
            if not len(v):
                continue
            ax.scatter(rng.normal(i, 0.07, len(v)), v, s=13, alpha=0.45,
                       color=SUBJ_COLOR[s])
            ax.plot([i - 0.28, i + 0.28], [v.median()] * 2, color="k", lw=2)
            ax.text(i + 0.32, v.median(), f"{v.median():.3g}", fontsize=8.5,
                    va="center")
        ax.set_xticks(range(1, len(SUBJECTS) + 1))
        ax.set_xticklabels(SUBJECTS, fontsize=9)
        ax.set_ylabel(label)
        ax.set_title(title, fontsize=10)
        ax.grid(alpha=0.25, axis="y")
    axes[1].set_yscale("log")

    # the bulk distribution, in units of each session's own noise floor, so a
    # gain or noise difference cannot masquerade as an amplitude difference
    ax = axes[2]
    pcts = [c for c in ("amp_p50", "amp_p90", "amp_p99", "amp_max") if c in a]
    idx = np.arange(len(pcts))
    width = 0.26
    for k, s in enumerate(SUBJECTS):
        g = a[a.subject == s]
        if not len(g):
            continue
        vals = [(g[c] / g.noise).median() for c in pcts]
        ax.bar(idx + (k - 1) * width, vals, width, color=SUBJ_COLOR[s],
               label=s)
    ax.set_xticks(idx)
    ax.set_xticklabels([c.replace("amp_", "") for c in pcts], fontsize=9)
    ax.set_ylabel("amplitude / that session's noise floor")
    ax.set_title("but Nigel is never the lowest here", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25, axis="y")

    fig.suptitle("Nigel's giant deficit lives entirely in the far tail",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)

    cols = ["ev_hz_ch", "giant_hz_ch", "noise", "snr"] + pcts
    return a.groupby("subject")[cols].median().round(4).reset_index()


# %%
def fig_longitudinal(a: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Giant rate over each implant's life, and the axon-like class with it."""
    from scipy.stats import spearmanr

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.4))
    for ax, metric, label in ((axes[0], "giant_hz_ch",
                               "giants / s / channel"),
                              (axes[1], "local_cluster_hz_ch",
                               "local clusters / s / channel")):
        if metric not in a:
            continue
        for s in SUBJECTS:
            g = a[a.subject == s].sort_values("date")
            if not len(g):
                continue
            ax.plot(g.date, g[metric].replace(0, np.nan), "o", ms=3.4,
                    alpha=0.55, color=SUBJ_COLOR[s], label=s)
        ax.set_yscale("log")
        ax.set_ylabel(label)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    axes[0].set_title("large events over the implant's life", fontsize=10)
    axes[1].set_title("the axon-like class", fontsize=10)

    fig.suptitle("Giant events longitudinally — Nigel sits a decade below "
                 "the other two", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)

    rows = []
    for s in SUBJECTS:
        for arr, g in a[a.subject == s].groupby("array"):
            for m in ("giant_hz_ch", "local_cluster_hz_ch", "ev_hz_ch"):
                v = g.dropna(subset=[m]) if m in g else g.iloc[:0]
                if len(v) < 12:
                    continue
                r, p = spearmanr(v.date.map(pd.Timestamp.toordinal), v[m])
                rows.append(dict(subject=s, array=arr, metric=m, n=len(v),
                                 rho=round(float(r), 3), p=float(p)))
    return pd.DataFrame(rows)


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    a = load()

    banner("1. Coverage")
    print(a.groupby("subject").agg(
        sessions=("date", "size"), arrays=("array", "nunique"),
        first=("date", "min"), last=("date", "max"),
        events=("events", "sum"), giants=("giants", "sum")).to_string())

    banner("2. Composition — per-session median against pooled")
    comp = fig_composition(a, FIG / "X1_composition.png")
    print(comp.to_string(index=False))

    banner("3. Where the artifacts are")
    conc = fig_concentration(a, FIG / "X2_concentration.png")
    print(conc.to_string(index=False))

    banner("4. Rates, normalised by time and channel")
    rates = fig_rates(a, FIG / "X3_rates.png")
    print(rates.to_string(index=False))

    banner("5. Longitudinal")
    tr = fig_longitudinal(a, FIG / "X4_longitudinal.png")
    print(tr.sort_values(["metric", "subject", "array"]).to_string(index=False))

    print("\n  wrote 4 figures to figures/giants/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

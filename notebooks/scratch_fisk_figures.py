"""Figures for the three Fisk results that existed only as prose.

`fisk_impedance.md`, `fisk_operator_floor.md` and the Fisk section of
`continuous_longitudinal.md` each rest on a table that was never plotted. All
three are findings that a reader has to *see* to believe at the right strength:

- impedance instability is a claim about a **shape** -- a channel wandering
  across 1 MOhm seven times -- and a table of medians cannot show wandering;
- the operator drift is a claim about **two lines diverging**, which is exactly
  what a figure is for;
- the layer disagreement is a **sign flip**, and a sign flip between two
  numbers in a table is easy to read as a rounding accident.

Eight figures, into `figures/fisk/{impedance,operator,layer}/`:

    Z1_instability   one reading cannot classify an electrode
    Z2_quality       impedance against the sorting-free metrics, per array
    Z3_yield         impedance against unit yield -- the strongest link
    Z4_groups        what the 1 MOhm convention would condemn
    O1_floor         14 matched pairs, and where the operators actually differ
    O2_drift         the offset drifts, so the two report opposite trends
    X1_level         snippet noise floor sits above the continuous one
    X2_trend         and the two layers disagree in sign on SNR

Run from repo root:

    uv run python notebooks/scratch_fisk_figures.py

See:
- docs/notes/fisk_impedance.md
- docs/notes/fisk_operator_floor.md
- docs/notes/continuous_longitudinal.md
"""

from __future__ import annotations

import glob
import sys
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))

FISK = REPO / "data" / "derived" / "fisk"
FREE_GLOB = str(REPO / "data" / "derived" / "rocky_ns5" / "free" / "*.parquet")
FIG = REPO / "figures" / "fisk"

# The reporting convention Blackrock's AutoImpedance prints against. Treated
# throughout as a line on a plot, never as a diagnosis -- see Z1 and Z4.
Z_LINE_KOHM = 1000.0
ARRAY_COLOR = {"Lateral": "#1f77b4", "Medial": "#d62728"}


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def rho_label(x: pd.Series, y: pd.Series) -> str:
    """Spearman rho and p as a short annotation, or a blank when undefined."""
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < 5 or d.x.nunique() < 3 or d.y.nunique() < 3:
        return ""
    r, p = spearmanr(d.x, d.y)
    return f"rho {r:+.3f}   p={p:.2g}   n={len(d)}"


# %%
# === Impedance ===
def crossings_per_channel(imp: pd.DataFrame) -> pd.DataFrame:
    """How many times each channel's reading crosses 1 MOhm, in date order.

    A crossing is a change in the boolean `kohm >= 1 MOhm` between consecutive
    measurement dates. If a high reading meant degradation this would be 0 or 1
    for every channel: cross once, stay across.

    Returns
    -------
    pandas.DataFrame
        One row per (array, channel) with `n_cross` and `n_dates`.
    """
    rows = []
    for (arr, ch), g in imp.sort_values("date").groupby(["array", "channel"]):
        b = (g.kohm >= Z_LINE_KOHM).to_numpy()
        rows.append(dict(array=arr, channel=ch, n_dates=len(b),
                         n_cross=int((b[1:] != b[:-1]).sum()),
                         ever=bool(b.any()), always=bool(b.all())))
    return pd.DataFrame(rows)


def fig_z1_instability(imp: pd.DataFrame, out: Path) -> dict:
    """Three views of the same claim: one reading does not classify anything."""
    cross = crossings_per_channel(imp)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))

    # Panel A: every channel's own trace. The point is the wandering, so all
    # 192 are drawn faintly rather than summarised into a band.
    ax = axes[0]
    for arr, g in imp.groupby("array"):
        for _, ch in g.groupby("channel"):
            ch = ch.sort_values("date")
            ax.plot(ch.date, ch.kohm, lw=0.4, alpha=0.18,
                    color=ARRAY_COLOR.get(arr, "0.4"))
    ax.axhline(Z_LINE_KOHM, color="k", ls="--", lw=1.2)
    ax.text(0.02, 0.94, "1 MOhm reporting convention", transform=ax.transAxes,
            fontsize=8)
    ax.set_yscale("log")
    ax.set_ylabel("impedance (kOhm)")
    ax.set_title("every channel, every date", fontsize=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.grid(alpha=0.25)
    for arr, c in ARRAY_COLOR.items():
        ax.plot([], [], color=c, lw=2, label=arr)
    ax.legend(fontsize=8)

    # Panel B: the count that makes the argument.
    ax = axes[1]
    bins = np.arange(-0.5, cross.n_cross.max() + 1.5)
    for arr, g in cross.groupby("array"):
        ax.hist(g.n_cross, bins=bins, alpha=0.6,
                color=ARRAY_COLOR.get(arr, "0.4"),
                label=f"{arr}: median {g.n_cross.median():.0f}, "
                      f"{int((g.n_cross == 0).sum())} never cross")
    ax.set_xlabel("times the channel crosses 1 MOhm")
    ax.set_ylabel("channels")
    ax.set_title("a degrading electrode would cross once", fontsize=10)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    # Panel C: the fleet-level count. Week-to-week scatter is large on both
    # arrays, but only Lateral is trendless -- Medial's count falls, which the
    # published note generalised away from Lateral's numbers alone.
    ax = axes[2]
    for arr, g in imp.groupby("array"):
        n = (g.assign(hi=g.kohm >= Z_LINE_KOHM)
             .groupby("date").hi.sum().sort_index())
        r, p = spearmanr(n.index.map(pd.Timestamp.toordinal), n.values)
        ax.plot(n.index, n.values, "o-", ms=3.5, lw=1.1,
                color=ARRAY_COLOR.get(arr, "0.4"), alpha=0.9,
                label=f"{arr}: rho {r:+.3f}  p={p:.2g}")
    ax.set_ylabel("channels above 1 MOhm")
    ax.set_title("large week-to-week scatter on both;\n"
                 "Medial also falls, Lateral does not", fontsize=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    fig.suptitle("Fisk impedance: a single AutoImpedance reading cannot "
                 "classify an electrode", fontsize=11.5)
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return dict(cross=cross)


def _pooled(q: pd.DataFrame, imp: pd.DataFrame,
            metrics: list[str]) -> pd.DataFrame:
    """Per-channel median impedance against per-channel median quality.

    Pooling on the channel median is what makes the relationship visible at
    all -- a single reading carries enough measurement noise to bury it.

    **The impedance median comes from every measurement date, not from the
    same-day subset.** `impedance_quality` carries only the readings that had a
    recording the same day (70 of 81 files); taking the median from there
    instead moves the group split from 61/131 to 66/126 and shifts the pooled
    rho by ~0.02. This matches `scratch_fisk_impedance_quality.py` so the
    figure and the published table are the same computation.
    """
    med_imp = (imp.groupby(["array", "channel"]).kohm.median()
               .rename("kohm").reset_index())
    med_q = (q.groupby(["array", "channel"])[metrics].median().reset_index())
    return med_q.merge(med_imp, on=["array", "channel"])


def fig_z2_quality(iq: pd.DataFrame, imp: pd.DataFrame,
                   out: Path) -> pd.DataFrame:
    """Impedance against the sorting-free metrics, one column per array."""
    metrics = [("noise_uv", "noise floor (uV)"),
               ("rate_hz", "crossing rate (Hz)"),
               ("amp_med", "amplitude (uV)"),
               ("snr", "peak SNR")]
    p = _pooled(iq, imp, [m for m, _ in metrics])
    arrays = sorted(p.array.unique())
    fig, axes = plt.subplots(len(metrics), len(arrays),
                             figsize=(4.6 * len(arrays), 3.0 * len(metrics)),
                             sharex="col")
    for j, arr in enumerate(arrays):
        g = p[p.array == arr]
        for i, (m, label) in enumerate(metrics):
            ax = axes[i, j]
            ax.scatter(g.kohm, g[m], s=16, alpha=0.7,
                       color=ARRAY_COLOR.get(arr, "0.4"))
            ax.axvline(Z_LINE_KOHM, color="k", ls="--", lw=0.9, alpha=0.6)
            ax.set_xscale("log")
            ax.set_ylabel(label, fontsize=9)
            ax.set_title(rho_label(g.kohm, g[m]), fontsize=8.5)
            ax.grid(alpha=0.25)
            ax.tick_params(labelsize=8)
            if i == 0:
                ax.text(0.5, 1.28, f"{arr}  (n={len(g)} channels)",
                        transform=ax.transAxes, ha="center", fontsize=11)
    for ax in axes[-1]:
        ax.set_xlabel("channel median impedance (kOhm)", fontsize=9)
    fig.suptitle("Impedance against the sorting-free metrics.\n"
                 "The two arrays carry different relationships — Lateral the "
                 "noise, Medial the rate and SNR.", fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.945))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return p


def fig_z3_yield(si: pd.DataFrame, out: Path) -> None:
    """Impedance against unit yield: the strongest link in the corpus."""
    per_ch = (si.groupby(["array", "channel"])
              .agg(kohm=("kohm", "median"), units=("n_units", "median"),
                   gated=("n_gated", "median"), snr=("snr", "median"))
              .reset_index())
    # Per-session rho, which is the version that holds date and amplifier fixed.
    rows = []
    for (arr, sess), g in si.groupby(["array", "session"]):
        d = g.dropna(subset=["kohm", "n_units"])
        if len(d) < 20 or d.n_units.nunique() < 3:
            continue
        r, _ = spearmanr(d.kohm, d.n_units)
        rows.append(dict(array=arr, session=sess, rho=r))
    per_sess = pd.DataFrame(rows)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    for j, arr in enumerate(sorted(per_ch.array.unique())):
        ax = axes[j]
        g = per_ch[per_ch.array == arr]
        ax.scatter(g.kohm, g.units, s=20, alpha=0.75,
                   color=ARRAY_COLOR.get(arr, "0.4"))
        ax.axvline(Z_LINE_KOHM, color="k", ls="--", lw=0.9, alpha=0.6)
        ax.set_xscale("log")
        ax.set_xlabel("channel median impedance (kOhm)")
        ax.set_ylabel("median units on that electrode")
        ax.set_title(f"{arr}\n{rho_label(g.kohm, g.units)}", fontsize=9.5)
        ax.grid(alpha=0.25)

    ax = axes[2]
    for arr, g in per_sess.groupby("array"):
        ax.hist(g.rho, bins=np.arange(-0.8, 0.45, 0.05), alpha=0.6,
                color=ARRAY_COLOR.get(arr, "0.4"),
                label=f"{arr}: median {g.rho.median():+.3f} (n={len(g)})")
    ax.axvline(0, color="k", lw=1)
    ax.set_xlabel("within-session Spearman rho (impedance vs units)")
    ax.set_ylabel("sessions")
    ax.set_title("per session, date and amplifier held fixed", fontsize=9.5)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    fig.suptitle("A high-impedance electrode yields fewer sortable units — "
                 "and Medial carries it far more strongly than Lateral",
                 fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_z4_groups(pooled: pd.DataFrame, out: Path) -> pd.DataFrame:
    """What the 1 MOhm convention would condemn, metric by metric."""
    p = pooled.copy()
    p["group"] = np.where(p.kohm >= Z_LINE_KOHM, ">= 1 MOhm", "< 1 MOhm")
    metrics = [("rate_hz", "crossing rate (Hz)"),
               ("noise_uv", "noise floor (uV)"),
               ("amp_med", "amplitude (uV)"),
               ("snr", "peak SNR")]
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.2))
    summary = []
    for ax, (m, label) in zip(axes, metrics, strict=True):
        lo = p[p.group == "< 1 MOhm"][m].dropna()
        hi = p[p.group == ">= 1 MOhm"][m].dropna()
        ax.boxplot([lo, hi], tick_labels=[f"< 1 MOhm\nn={len(lo)}",
                                          f">= 1 MOhm\nn={len(hi)}"],
                   widths=0.55, showfliers=False)
        for i, v in enumerate((lo, hi), start=1):
            ax.scatter(np.random.default_rng(0).normal(i, 0.055, len(v)), v,
                       s=9, alpha=0.4, color="0.3")
        ratio = hi.median() / lo.median() if lo.median() else np.nan
        _, pv = mannwhitneyu(lo, hi)
        ax.set_ylabel(label, fontsize=9)
        ax.set_title(f"{lo.median():.2f} -> {hi.median():.2f}\n"
                     f"ratio {ratio:.2f}   p={pv:.2g}", fontsize=9.5)
        ax.grid(alpha=0.25, axis="y")
        summary.append(dict(metric=m, lo=lo.median(), hi=hi.median(),
                            ratio=ratio, p=pv, n_lo=len(lo), n_hi=len(hi)))
    fig.suptitle("Grouped on each channel's *median* impedance, both arrays "
                 "pooled.\nYield halves; SNR does not — the convention would "
                 "condemn a third of the working electrodes.", fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return pd.DataFrame(summary)


# %%
# === Operator ===
def fig_o1_floor(op: pd.DataFrame, out: Path) -> None:
    """Where two curators of the same files actually differ."""
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.4))

    # Panel A: every pair as its own line. 14 of 14 slope the same way, which
    # is the claim -- an average would hide whether it is systematic.
    ax = axes[0]
    for r in op.itertuples():
        ax.plot([0, 1], [r.ds_units, r.sidd_units], "-o", ms=4, lw=1.1,
                color=ARRAY_COLOR.get(r.array, "0.4"), alpha=0.8)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["DS", "Sidd"])
    ax.set_ylabel("units kept")
    down = int((op.sidd_units < op.ds_units).sum())
    ax.set_title(f"Sidd keeps fewer in {down} of {len(op)} pairs",
                 fontsize=10)
    ax.grid(alpha=0.25, axis="y")
    for arr, c in ARRAY_COLOR.items():
        ax.plot([], [], color=c, lw=2, label=arr)
    ax.legend(fontsize=8)

    # Panel B: the gap is not one number.
    ax = axes[1]
    groups = [op[op.array == a].ratio_units.dropna()
              for a in sorted(op.array.unique())]
    labels = [f"{a}\nmedian {g.median():.3f}"
              for a, g in zip(sorted(op.array.unique()), groups, strict=True)]
    ax.boxplot(groups, tick_labels=labels, widths=0.5, showfliers=False)
    for i, (a, g) in enumerate(zip(sorted(op.array.unique()), groups,
                                   strict=True), start=1):
        ax.scatter(np.full(len(g), i), g, s=26, alpha=0.75,
                   color=ARRAY_COLOR.get(a, "0.4"))
    ax.axhline(1.0, color="k", lw=1, ls="--", alpha=0.6)
    if len(groups) == 2 and all(len(g) for g in groups):
        _, pv = mannwhitneyu(*groups)
        ax.set_title(f"the gap is array-specific   p={pv:.2g}", fontsize=10)
    ax.set_ylabel("Sidd / DS unit ratio")
    ax.grid(alpha=0.25, axis="y")

    # Panel C: they agree about the spikes, not about inclusion.
    ax = axes[2]
    ax.scatter(op.keep_agree, op.ari_kept, s=40, alpha=0.8,
               c=[ARRAY_COLOR.get(a, "0.4") for a in op.array])
    ax.set_xlabel("agreement on which units to keep")
    ax.set_ylabel("ARI on spikes both kept")
    ax.set_xlim(0.9, 1.005)
    ax.set_ylim(0.9, 1.005)
    ax.plot([0.9, 1.005], [0.9, 1.005], color="0.7", lw=1, ls=":")
    ax.set_title(f"keep {op.keep_agree.median():.3f}   "
                 f"ARI {op.ari_kept.median():.3f}\n"
                 "the partition is shared; the inclusion is not", fontsize=10)
    ax.grid(alpha=0.25)

    fig.suptitle("Fisk operator floor: 14 matched pairs, same sessions, "
                 "both arrays", fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_o2_drift(op: pd.DataFrame, out: Path) -> pd.DataFrame:
    """The offset drifts, so the two curators report opposite trends."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    rows = []

    ax = axes[0]
    for arr, g in op.groupby("array"):
        g = g.sort_values("date")
        ax.plot(g.date, g.ratio_units, "o-", ms=5, lw=1.2,
                color=ARRAY_COLOR.get(arr, "0.4"),
                label=f"{arr}: {rho_label(g.date.map(pd.Timestamp.toordinal), g.ratio_units)}")
    ax.axhline(1.0, color="k", lw=1, ls="--", alpha=0.6)
    ax.set_ylabel("Sidd / DS unit ratio")
    ax.set_title("the two curators grow further apart", fontsize=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7.5)

    # The consequence: each operator's own longitudinal trend, same recordings.
    for j, arr in enumerate(sorted(op.array.unique())):
        ax = axes[j + 1]
        g = op[op.array == arr].sort_values("date")
        x = g.date.map(pd.Timestamp.toordinal)
        for col, name, colour in (("ds_units", "DS", "#2ca02c"),
                                  ("sidd_units", "Sidd", "#9467bd")):
            r, p = spearmanr(x, g[col])
            mark = " *" if p < 0.05 else ""
            ax.plot(g.date, g[col], "o-", ms=5, lw=1.3, color=colour,
                    label=f"{name}: rho {r:+.3f}  p={p:.2g}{mark}")
            rows.append(dict(array=arr, operator=name, rho=r, p=p, n=len(g)))
        ax.set_ylabel("units kept")
        ax.set_title(f"{arr} — same seven recordings", fontsize=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)

    fig.suptitle("A constant operator offset cancels out of a trend. "
                 "A drifting one does not.\n"
                 "Same array, same sessions, same events — opposite "
                 "conclusions about what the array is doing.", fontsize=11.5)
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return pd.DataFrame(rows)


# %%
# === Layer ===
def layer_pairs() -> pd.DataFrame:
    """Snippet and continuous metrics for the same Fisk recordings.

    The snippet side is `layer_compare.parquet`, keyed by session folder; the
    continuous side sits in the shared `rocky_ns5/free/` shards, keyed by the
    same stem. Only sessions carrying both are returned.
    """
    snip = pd.read_parquet(FISK / "layer_compare.parquet")
    cont = pd.concat([pd.read_parquet(p) for p in glob.glob(FREE_GLOB)],
                     ignore_index=True)
    cont = cont[cont.subject == "Fisk"]
    keep = ["array", "date", "noise_med", "peak_snr_med", "crossing_rate_hz"]
    a = snip.rename(columns={"session": "stem"})[["stem", *keep]]
    b = cont[["stem", *keep]]
    m = a.merge(b, on=["stem", "array", "date"], suffixes=("_snip", "_cont"))
    # Both tables store the date as a string; matplotlib would treat it as a
    # category and `Timestamp.toordinal` would refuse it outright.
    m["date"] = pd.to_datetime(m["date"])
    return m


def fig_x1_level(m: pd.DataFrame, out: Path) -> None:
    """The level difference: the snippet estimator sits above the true floor."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))

    ax = axes[0]
    lim = [0, max(m.noise_med_snip.max(), m.noise_med_cont.max()) * 1.05]
    for arr, g in m.groupby("array"):
        ax.scatter(g.noise_med_cont, g.noise_med_snip, s=26, alpha=0.75,
                   color=ARRAY_COLOR.get(arr, "0.4"), label=arr)
    ax.plot(lim, lim, color="0.5", lw=1.2, ls="--", label="equality")
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("continuous noise floor (uV)")
    ax.set_ylabel("snippet noise floor (uV)")
    ratio = (m.noise_med_snip / m.noise_med_cont).median()
    ax.set_title(f"snippet / continuous = {ratio:.2f} (median)", fontsize=10)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    ax = axes[1]
    for arr, g in m.sort_values("date").groupby("array"):
        c = ARRAY_COLOR.get(arr, "0.4")
        ax.plot(g.date, g.noise_med_snip, "o-", ms=3.4, lw=1, color=c,
                alpha=0.9, label=f"{arr} snippet")
        ax.plot(g.date, g.noise_med_cont, "s--", ms=3.4, lw=1, color=c,
                alpha=0.5, label=f"{arr} continuous")
    ax.set_ylabel("noise floor (uV)")
    ax.set_title("the gap is not constant either", fontsize=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7)

    ax = axes[2]
    for arr, g in m.groupby("array"):
        ax.scatter(g.peak_snr_med_cont, g.peak_snr_med_snip, s=26, alpha=0.75,
                   color=ARRAY_COLOR.get(arr, "0.4"), label=arr)
    lim = [min(m.peak_snr_med_cont.min(), m.peak_snr_med_snip.min()) * 0.95,
           max(m.peak_snr_med_cont.max(), m.peak_snr_med_snip.max()) * 1.05]
    ax.plot(lim, lim, color="0.5", lw=1.2, ls="--")
    ax.set_xlabel("continuous peak SNR")
    ax.set_ylabel("snippet peak SNR")
    ax.set_title("SNR inherits the bias, inverted", fontsize=10)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    fig.suptitle(f"Fisk, {len(m)} sessions with both layers computed from the "
                 "same recordings", fontsize=11.5)
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_x2_trend(m: pd.DataFrame, out: Path) -> pd.DataFrame:
    """The sign flip, which is the finding that revises a headline claim."""
    rows = []
    for arr, g in m.groupby("array"):
        for layer, col in (("snippet", "peak_snr_med_snip"),
                           ("continuous", "peak_snr_med_cont")):
            d = g.dropna(subset=[col])
            r, p = spearmanr(d.date.map(pd.Timestamp.toordinal), d[col])
            rows.append(dict(array=arr, layer=layer, metric="peak SNR",
                             rho=r, p=p, n=len(d)))
        for layer, col in (("snippet", "noise_med_snip"),
                           ("continuous", "noise_med_cont")):
            d = g.dropna(subset=[col])
            r, p = spearmanr(d.date.map(pd.Timestamp.toordinal), d[col])
            rows.append(dict(array=arr, layer=layer, metric="noise floor",
                             rho=r, p=p, n=len(d)))
    tr = pd.DataFrame(rows)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))

    ax = axes[0]
    piv = tr[tr.metric == "peak SNR"].pivot_table(
        index="array", columns="layer", values="rho")
    idx = np.arange(len(piv))
    ax.barh(idx - 0.19, piv["snippet"], height=0.36, color="#ff7f0e",
            label="snippet")
    ax.barh(idx + 0.19, piv["continuous"], height=0.36, color="#1f77b4",
            label="continuous")
    ax.set_yticks(idx)
    ax.set_yticklabels(piv.index)
    ax.axvline(0, color="k", lw=1)
    ax.set_xlabel("trend in peak SNR (Spearman rho)")
    ax.set_title("the two layers disagree in sign", fontsize=10)
    ax.grid(alpha=0.25, axis="x")
    ax.legend(fontsize=8)

    for j, arr in enumerate(sorted(m.array.unique())):
        ax = axes[j + 1]
        g = m[m.array == arr].sort_values("date")
        for layer, col, colour in (("snippet", "peak_snr_med_snip", "#ff7f0e"),
                                   ("continuous", "peak_snr_med_cont",
                                    "#1f77b4")):
            d = g.dropna(subset=[col])
            r, p = spearmanr(d.date.map(pd.Timestamp.toordinal), d[col])
            mark = " *" if p < 0.05 else ""
            ax.plot(d.date, d[col], "o-", ms=3.4, lw=1, color=colour,
                    alpha=0.85, label=f"{layer}: rho {r:+.3f} p={p:.2g}{mark}")
        ax.set_ylabel("median peak SNR")
        ax.set_title(f"{arr}", fontsize=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)

    fig.suptitle("Where either layer finds an SNR trend the two flip sign, "
                 "and the snippet side is always the more positive.\n"
                 "The flat-SNR result rests on the snippet layer, whose noise "
                 "estimator is the one with a documented bias.", fontsize=11)
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return tr


def main() -> int:
    imp = pd.read_parquet(FISK / "impedance.parquet")
    iq = pd.read_parquet(FISK / "impedance_quality.parquet")
    si = pd.read_parquet(FISK / "sorted_impedance.parquet")
    op = pd.read_parquet(FISK / "operator_pairs.parquet")
    m = layer_pairs()

    made: list[Path] = []
    d_imp, d_op, d_lay = (FIG / "impedance", FIG / "operator", FIG / "layer")
    for d in (d_imp, d_op, d_lay):
        d.mkdir(parents=True, exist_ok=True)

    banner("1. Impedance")
    z1 = fig_z1_instability(imp, d_imp / "Z1_instability.png")
    made.append(d_imp / "Z1_instability.png")
    # "never cross" means the boolean never changes, which includes the few
    # channels that sit above 1 MOhm throughout -- not just those below it.
    print(z1["cross"].groupby("array").agg(
        channels=("channel", "size"),
        never_cross=("n_cross", lambda s: int((s == 0).sum())),
        always_high=("always", "sum"),
        median_cross=("n_cross", "median"), max_cross=("n_cross", "max"),
    ).to_string())

    pooled = fig_z2_quality(iq, imp, d_imp / "Z2_quality.png")
    made.append(d_imp / "Z2_quality.png")
    print("\n  pooled per-channel rho (impedance vs metric):")
    for arr, g in pooled.groupby("array"):
        parts = [f"{m_}={spearmanr(g.kohm, g[m_])[0]:+.3f}"
                 for m_ in ("noise_uv", "rate_hz", "amp_med", "snr")]
        print(f"    {arr:8s} " + "  ".join(parts))

    fig_z3_yield(si, d_imp / "Z3_yield.png")
    made.append(d_imp / "Z3_yield.png")
    grp = fig_z4_groups(pooled, d_imp / "Z4_groups.png")
    made.append(d_imp / "Z4_groups.png")
    print("\n  grouped on channel median impedance:")
    print(grp.round(3).to_string(index=False))

    banner("2. Operator")
    fig_o1_floor(op, d_op / "O1_floor.png")
    made.append(d_op / "O1_floor.png")
    print(f"  pairs {len(op)}   Sidd<DS in "
          f"{int((op.sidd_units < op.ds_units).sum())}   "
          f"ratio {op.ratio_units.median():.3f}   "
          f"ARI {op.ari_kept.median():.3f}")
    drift = fig_o2_drift(op, d_op / "O2_drift.png")
    made.append(d_op / "O2_drift.png")
    print(drift.round(3).to_string(index=False))

    banner("3. Layer")
    fig_x1_level(m, d_lay / "X1_level.png")
    made.append(d_lay / "X1_level.png")
    print(f"  sessions with both layers: {len(m)}")
    print(f"  snippet/continuous noise ratio: "
          f"{(m.noise_med_snip / m.noise_med_cont).median():.3f}")
    tr = fig_x2_trend(m, d_lay / "X2_trend.png")
    made.append(d_lay / "X2_trend.png")
    print(tr.round(3).to_string(index=False))

    print(f"\n  wrote {len(made)} figures")
    for p in made:
        print(f"    {p.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

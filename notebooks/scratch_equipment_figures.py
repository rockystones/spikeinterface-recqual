"""Figures for the acquisition-equipment comparison, which existed only as prose.

Rocky is the only animal recorded on three configurations of hardware with
overlap between them -- Blackrock with an analog headstage, Blackrock with a
digital one, and TDT -- so it is the only place in this corpus where "does the
equipment change the measurement" can be answered rather than assumed. The
tables were built and never drawn.

`notebooks/scratch_equipment_compare.py` and `scratch_headstage_pairs.py` →
`data/derived/equipment/`, `data/derived/cohort/`. This reads them.

Three results, three figures:

    Q1_regimes   the three configurations side by side in their overlap window
    Q2_pairs     same-day analog/digital pairs, the design that removes the era
    Q3_drift     the analog headstage getting worse against a same-day control

The headline is **two gain regimes with flat SNR**: the analog path reports a
higher noise floor *and* a proportionally higher amplitude, so their ratio is
unchanged. An amplitude in uV is not comparable across headstages; an SNR is.

Run from repo root:

    uv run python notebooks/scratch_equipment_figures.py

See:
- docs/notes/equipment_comparison.md
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr, wilcoxon

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))

EQUIP = REPO / "data" / "derived" / "equipment" / "tdt_vs_blackrock.parquet"
FREE_PAIRS = REPO / "data" / "derived" / "cohort" / "headstage_free_pairs.parquet"
SORTED_PAIRS = REPO / "data" / "derived" / "cohort" / "headstage_pairs.parquet"
FIG = REPO / "figures" / "equipment"

EQUIP_COLOR = {"BR-Analog": "#d62728", "BR-Digital": "#1f77b4",
               "TDT": "#2ca02c"}


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def overlap_window(d: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    """The span where all three configurations were in use.

    Comparing them over their full ranges would confound equipment with
    implant age -- the analog era is early and the TDT era is late. The
    intersection of the three date ranges is the only window where the
    comparison is about hardware.
    """
    lo = d.groupby("equipment").date.min().max()
    hi = d.groupby("equipment").date.max().min()
    return lo, hi


# %%
def fig_regimes(d: pd.DataFrame, out: Path) -> pd.DataFrame:
    """The three configurations, restricted to their common window."""
    lo, hi = overlap_window(d)
    w = d[(d.date >= lo) & (d.date <= hi)]
    metrics = [("noise_med", "noise floor (uV)"),
               ("amp_p50", "median crossing amplitude (uV)"),
               ("peak_snr_med", "peak SNR"),
               ("crossing_rate_hz", "crossing rate (Hz)")]
    order = [e for e in ("BR-Analog", "BR-Digital", "TDT")
             if e in set(w.equipment)]
    fig, axes = plt.subplots(1, len(metrics), figsize=(4.0 * len(metrics), 4.4))
    rows = []
    for ax, (m, label) in zip(axes, metrics, strict=True):
        groups = [w[w.equipment == e][m].dropna() for e in order]
        ax.boxplot(groups, tick_labels=[f"{e}\nn={len(g)}"
                                        for e, g in zip(order, groups,
                                                        strict=True)],
                   widths=0.55, showfliers=False)
        for i, (e, g) in enumerate(zip(order, groups, strict=True), start=1):
            ax.scatter(np.random.default_rng(1).normal(i, 0.06, len(g)), g,
                       s=9, alpha=0.45, color=EQUIP_COLOR.get(e, "0.3"))
            rows.append(dict(metric=m, equipment=e, n=len(g),
                             median=float(g.median())))
        ax.set_ylabel(label, fontsize=9)
        meds = " / ".join(f"{g.median():.2f}" for g in groups)
        ax.set_title(meds, fontsize=9)
        ax.grid(alpha=0.25, axis="y")
        ax.tick_params(labelsize=8)
    fig.suptitle(f"Three acquisition configurations, {lo.date()} to "
                 f"{hi.date()} only.\nNoise and amplitude move together; SNR "
                 "does not — two gain regimes, one signal quality.",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return pd.DataFrame(rows)


def broadband_pairs() -> pd.DataFrame:
    """Same-day analog/digital pairs from the **continuous** layer.

    The distinction matters and it is the whole point of the middle figure.
    The snippet layer inherits the NSP's own threshold, which was set per
    headstage, so an apparent crossing-rate gap between them is partly a
    difference in what the amplifier decided to save. The continuous layer
    re-detects every session at the same `4 x MAD`, which removes that by
    construction -- and the gap goes with it.
    """
    import glob

    files = glob.glob(str(REPO / "data" / "derived" / "rocky_ns5" / "free" /
                          "*.parquet"))
    f = pd.concat([pd.read_parquet(p) for p in files], ignore_index=True)
    f = f[(f.subject == "Rocky") & f.headstage.isin(["Analog", "Digital"])]
    f["date"] = pd.to_datetime(f.date)
    cols = ["noise_med", "amp_p50", "crossing_rate_hz", "peak_snr_med"]
    piv = f.pivot_table(index=["array", "date"], columns="headstage",
                        values=cols)
    out = pd.DataFrame(index=piv.index)
    for c in cols:
        if (c, "Analog") in piv and (c, "Digital") in piv:
            out[f"{c}_analog"] = piv[(c, "Analog")]
            out[f"{c}_digital"] = piv[(c, "Digital")]
    return out.dropna().reset_index()


def fig_pairs(snip: pd.DataFrame, cont: pd.DataFrame, srt: pd.DataFrame,
              out: Path) -> pd.DataFrame:
    """Same-day analog/digital pairs, snippet layer above continuous below.

    The paired design removes era, implant age and animal state -- whatever
    differs within a pair is the hardware. Drawing both layers shows which
    differences are the amplifier and which are the *threshold* the amplifier
    was running.
    """
    metrics = [("noise_med", "noise floor (uV)"),
               ("amp_p50", "crossing amplitude (uV)"),
               ("crossing_rate_hz", "crossing rate (Hz)"),
               ("peak_snr_med", "peak SNR")]
    layers = [("snippet (NSP's own threshold)", snip),
              ("continuous (re-detected at 4x MAD)", cont)]
    fig, axes = plt.subplots(len(layers), len(metrics),
                             figsize=(3.7 * len(metrics), 3.8 * len(layers)),
                             squeeze=False)
    rows = []
    for i, (lname, src) in enumerate(layers):
        for j, (m, label) in enumerate(metrics):
            ax = axes[i, j]
            a, dgt = f"{m}_analog", f"{m}_digital"
            if a not in src or dgt not in src:
                ax.set_visible(False)
                continue
            p = src[[a, dgt]].dropna()
            if not len(p):
                ax.set_visible(False)
                continue
            ax.scatter(p[dgt], p[a], s=20, alpha=0.7, color="#7f4fa0")
            # Log-log. A handful of artifact sessions run two orders of
            # magnitude above the rest -- 8000 uV amplitudes, 650 uV noise --
            # and on linear axes they squeeze every real pair into the corner.
            # They are genuine recordings and the paired test uses them, so
            # they are rescaled rather than dropped.
            pos = pd.concat([p[a], p[dgt]])
            pos = pos[pos > 0]
            lim = [pos.min() * 0.7, pos.max() * 1.4]
            ax.plot(lim, lim, color="0.5", lw=1.2, ls="--")
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_xlim(lim)
            ax.set_ylim(lim)
            ax.set_xlabel(f"digital — {label}", fontsize=8)
            if j == 0:
                ax.set_ylabel(f"{lname}\n\nanalog — {label}", fontsize=8)
            else:
                ax.set_ylabel(f"analog — {label}", fontsize=8)
            ratio = float((p[a] / p[dgt].replace(0, np.nan)).median())
            try:
                _, pv = wilcoxon(p[a], p[dgt])
            except ValueError:
                pv = 1.0
            ax.set_title(f"ratio {ratio:.2f}   p={pv:.2g}   n={len(p)}",
                         fontsize=8.5)
            ax.grid(alpha=0.25)
            ax.tick_params(labelsize=7.5)
            rows.append(dict(layer=lname.split(" (")[0], metric=m, n=len(p),
                             ratio=ratio, p=pv))
    # The sorted layer has no continuous counterpart, so it is reported rather
    # than drawn -- a fifth column would be empty on the bottom row.
    if "units_per_electrode_analog" in srt:
        p = srt[["units_per_electrode_analog",
                 "units_per_electrode_digital"]].dropna()
        if len(p):
            ratio = float((p.iloc[:, 0] /
                           p.iloc[:, 1].replace(0, np.nan)).median())
            _, pv = wilcoxon(p.iloc[:, 0], p.iloc[:, 1])
            rows.append(dict(layer="sorted", metric="units_per_electrode",
                             n=len(p), ratio=ratio, p=pv))
    fig.suptitle("Same-day headstage pairs. Above the line means the analog "
                 "path reports more.\nNoise and amplitude rise together on "
                 "both layers. The crossing-rate gap is a threshold "
                 "difference: it survives the NSP's own detection and "
                 "disappears when both sides are re-detected identically.",
                 fontsize=10.5)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return pd.DataFrame(rows)


def fig_drift(cont: pd.DataFrame, out: Path) -> pd.DataFrame:
    """The analog headstage degrading, with the digital pair as its control.

    A rising noise floor on its own could be the array, the animal or the era.
    Here the digital headstage recorded the same array on the same day, so the
    *ratio* isolates the analog path: if the array were degrading, both sides
    would rise together and the ratio would be flat.

    **The continuous layer, not the snippet one.** Both find the drift and
    agree on its direction, but the snippet ratio also carries the NSP's
    per-headstage threshold and runs steeper -- 1.23 -> 3.99 on Anterior
    against 1.25 -> 2.07 here. The re-detected measurement is the honest one
    and is what [[equipment_comparison]] quotes.
    """
    d = cont.copy()
    d["date"] = pd.to_datetime(d.date)
    d["ratio"] = d.noise_med_analog / d.noise_med_digital.replace(0, np.nan)
    arrays = sorted(d.array.dropna().unique())
    fig, axes = plt.subplots(1, len(arrays) + 1,
                             figsize=(4.4 * (len(arrays) + 1), 4.4))
    rows = []
    for ax, arr in zip(axes, arrays, strict=False):
        g = d[d.array == arr].dropna(subset=["ratio"]).sort_values("date")
        if not len(g):
            continue
        r, p = spearmanr(g.date.map(pd.Timestamp.toordinal), g.ratio)
        ax.plot(g.date, g.ratio, "o-", ms=3.6, lw=1, color="#d62728",
                alpha=0.85)
        ax.axhline(1.0, color="k", lw=1.2, ls="--")
        ax.set_ylabel("analog noise / digital noise, same day")
        # Log y: the last two sessions of each array run at 77x and 90x, which
        # on a linear axis flattens the entire 15-month rise into the baseline.
        ax.set_yscale("log")
        ax.set_title(f"{arr}   rho {r:+.3f}  p={p:.2g}  n={len(g)}\n"
                     f"first 8 {g.ratio.head(8).median():.2f} -> "
                     f"last 8 {g.ratio.tail(8).median():.2f}", fontsize=9.5)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.grid(alpha=0.25)
        rows.append(dict(array=arr, n=len(g), rho=r, p=p,
                         first=float(g.ratio.head(8).median()),
                         last=float(g.ratio.tail(8).median())))

    # The control: the digital side alone over the same window. If it rises
    # too, the array is degrading and the ratio above is the wrong story.
    ax = axes[-1]
    for arr in arrays:
        g = d[d.array == arr].dropna(subset=["noise_med_digital"]) \
            .sort_values("date")
        if not len(g):
            continue
        r, _ = spearmanr(g.date.map(pd.Timestamp.toordinal),
                         g.noise_med_digital)
        ax.plot(g.date, g.noise_med_digital, "o-", ms=3.2, lw=0.9, alpha=0.8,
                label=f"{arr}: rho {r:+.3f}")
    ax.set_ylabel("digital noise floor (uV)")
    ax.set_title("the control side, same sessions", fontsize=9.5)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)

    fig.suptitle("The analog headstage gets worse; the digital one recording "
                 "the same array on the same day does not.", fontsize=11)
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return pd.DataFrame(rows)


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    d = pd.read_parquet(EQUIP)
    d["date"] = pd.to_datetime(d.date)
    free = pd.read_parquet(FREE_PAIRS)
    srt = pd.read_parquet(SORTED_PAIRS)

    banner("1. Coverage")
    print(d.groupby(["equipment", "array"]).agg(
        n=("date", "size"), first=("date", "min"), last=("date", "max"))
        .to_string())
    lo, hi = overlap_window(d)
    print(f"\n  overlap window: {lo.date()} -> {hi.date()}   "
          f"sessions inside: {int(((d.date >= lo) & (d.date <= hi)).sum())}")

    banner("2. The three regimes, in the overlap window")
    reg = fig_regimes(d, FIG / "Q1_regimes.png")
    print(reg.pivot_table(index="metric", columns="equipment",
                          values="median").round(3).to_string())
    w = d[(d.date >= lo) & (d.date <= hi)]
    for m in ("noise_med", "peak_snr_med"):
        a = w[w.equipment == "BR-Analog"][m].dropna()
        t = w[w.equipment == "TDT"][m].dropna()
        if len(a) > 3 and len(t) > 3:
            _, p = mannwhitneyu(a, t)
            print(f"  TDT vs analog {m:14s} ratio "
                  f"{t.median() / a.median():.2f}  p={p:.3g}")

    banner("3. Same-day headstage pairs, both layers")
    cont = broadband_pairs()
    print(f"  snippet pairs {len(free)}   continuous pairs {len(cont)}")
    pr = fig_pairs(free, cont, srt, FIG / "Q2_pairs.png")
    print(pr.round(4).to_string(index=False))

    banner("4. The analog path degrading")
    dr = fig_drift(cont, FIG / "Q3_drift.png")
    print(dr.round(4).to_string(index=False))

    print("\n  wrote 3 figures to figures/equipment/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

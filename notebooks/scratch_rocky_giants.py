"""Forensics of large-amplitude events: what they are, one class at a time.

An earlier pass concluded that units above 800 uV are cross-channel artifacts
and should be excluded. That conclusion was right about the population and
wrong as a rule, because it would also delete two phenomena that are real and
rare: very large waveforms confined to a few neighbouring electrodes with an
atypical positive-led shape, and genuinely huge, normally-shaped spikes.

This script separates them. Amplitude alone cannot: the discriminating
quantities are (a) how many electrodes carry a large deflection at the same
instant, (b) whether those electrodes are physically adjacent, and (c) the
width of the dominant phase, which is what exposes a single-sample digital
impulse masquerading as a 4 mV spike.

Consumes `giant_events.parquet`, `events_electrode.parquet` and the waveform
shards written by `scratch_rocky_events.py`.

Run from repo root:

    uv run python notebooks/scratch_rocky_giants.py

See:
- docs/notes/giant_events.md
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_rocky_resort import open_nev, read_electrode  # noqa: E402
from scratch_rocky_spatial import parse_cmp  # noqa: E402

ROCKY = Path(r"D:\Claude Code\Rocky")
OUT_DIR = REPO / "data" / "derived" / "rocky"
FIG_DIR = REPO / "figures" / "rocky" / "giants"
WF_SHARDS = OUT_DIR / "giant_wf_shards"
SITES_OUT = OUT_DIR / "giant_sites.parquet"

CMP_BY_ARRAY = {
    "Anterior": ROCKY / "preimplant" / "SN 1025-001501.cmp",
    "Posterior": ROCKY / "preimplant" / "SN 1025-001497.cmp",
}
ARRAY_COLOR = {"Anterior": "#1f77b4", "Posterior": "#d62728"}
NON_NEURAL = ("artifact", "impulse", "railed")
SR = 30000.0
NBEFORE = 10
RAIL_UV = 8191.0

CLASS_COLOR = {
    "artifact": "#8c564b", "impulse": "#e377c2", "railed": "#7f7f7f",
    "isolated": "#1f77b4", "local_cluster": "#2ca02c",
    "scattered_few": "#ff7f0e", "multi_channel": "#9467bd",
}
CLASS_ORDER = ["isolated", "local_cluster", "scattered_few", "multi_channel",
               "artifact", "impulse", "railed"]

# A "real giant" must be well below the ADC rail, on an electrode with a
# normal noise floor, and wide enough to be a waveform rather than a glitch.
REAL_AMP = (400.0, 4000.0)
REAL_MAX_NOISE = 30.0
REAL_MIN_Z = 20.0
REAL_MIN_WIDTH = 3


RNG = np.random.default_rng(0)   # jitter for the discrete width axis only


def banner(t: str) -> None:
    print()
    print("=" * 72)
    print(t)
    print("=" * 72)


def time_axis(n: int) -> np.ndarray:
    """Milliseconds relative to the threshold crossing, for an n-sample snippet.

    Snippet length is not constant across this cohort -- most sessions store 30
    samples but some store 48 -- so the axis is derived per waveform rather
    than assumed. ``wf_left_sweep`` is 10 on every file checked.
    """
    return (np.arange(n) - NBEFORE) / SR * 1000.0


def load_waveforms(date: str, array: str) -> tuple[np.ndarray, np.ndarray]:
    """Waveforms and their gids for one session, or empty arrays."""
    p = WF_SHARDS / f"{date}_{array}.npz"
    if not p.exists():
        return np.zeros((0, 30), np.float32), np.zeros(0, np.int64)
    z = np.load(p)
    return z["wf"], z["gid"]


def real_giants(g: pd.DataFrame) -> pd.DataFrame:
    """Subset of neural-plausible giants that survive the sanity filters."""
    return g[(~g["klass"].isin(NON_NEURAL))
             & g["abs_amp_uv"].between(*REAL_AMP)
             & (g["noise_uv"] < REAL_MAX_NOISE)
             & (g["amp_z"] >= REAL_MIN_Z)
             & ((g["width_min"] >= REAL_MIN_WIDTH)
                | (g["width_max"] >= REAL_MIN_WIDTH))]


# === G1: taxonomy ===
def fig_taxonomy(ed: pd.DataFrame, g: pd.DataFrame, out: Path) -> None:
    """Census of the >=250 uV population, against what chance would produce."""
    cols = {c[8:]: c for c in ed.columns
            if c.startswith("n_giant_") and c[8:] in CLASS_ORDER}
    counts = {k: int(ed[v].sum()) for k, v in cols.items()}
    total = int(ed["n_giant_total"].sum())

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))

    ax = axes[0]
    ks = [k for k in CLASS_ORDER if k in counts]
    vals = [counts[k] / total * 100 for k in ks]
    ax.barh(range(len(ks)), vals, color=[CLASS_COLOR[k] for k in ks])
    # Chance expectation for the local-cluster call: P(at least one large
    # coincidence) x P(a random partner is within two grid steps).
    lam = ed["chance_coincidence_big"].median()
    exp_local = (1 - np.exp(-lam)) * (24 / 95) * 100
    ax.axvline(exp_local, color="0.25", ls="--", lw=1.2)
    ax.text(exp_local * 1.08, len(ks) - 0.4,
            f"local_cluster expected\nby chance: {exp_local:.1f}%",
            fontsize=7, color="0.25", va="top")
    ax.set_yticks(range(len(ks)))
    ax.set_yticklabels(ks, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("% of events >= 250 uV", fontsize=8)
    ax.set_title(f"taxonomy of {total / 1e6:.1f}M large events", fontsize=9)

    ax = axes[1]
    for k in CLASS_ORDER:
        s = g[g["klass"] == k]["abs_amp_uv"]
        if len(s) < 30:
            continue
        ax.hist(s, bins=np.logspace(np.log10(250), np.log10(9000), 45),
                histtype="step", lw=1.4, color=CLASS_COLOR[k], label=k,
                density=True)
    ax.axvline(RAIL_UV, color="0.3", ls=":", lw=1.2)
    ax.text(RAIL_UV * 0.97, ax.get_ylim()[1] * 0.6, "int16 rail\n8192 uV",
            fontsize=6.5, ha="right", color="0.3")
    ax.set_xscale("log")
    ax.set_xlabel("|amplitude| (uV)", fontsize=8)
    ax.set_ylabel("density", fontsize=8)
    ax.set_title("amplitude by class (stored sample)", fontsize=9)
    ax.legend(fontsize=6.5)

    ax = axes[2]
    for k in CLASS_ORDER:
        s = g[g["klass"] == k]
        if len(s) < 30:
            continue
        w = np.where(np.abs(s["vmin_uv"]) >= s["vmax_uv"],
                     s["width_min"], s["width_max"])
        ax.scatter(w + RNG.uniform(-0.28, 0.28, len(w)), s["abs_amp_uv"],
                   s=3, alpha=0.25, color=CLASS_COLOR[k], label=k, lw=0)
    ax.set_yscale("log")
    ax.set_xlim(0, 24)
    ax.set_xlabel("width of dominant phase at half amplitude (samples @ 30 kHz)",
                  fontsize=8)
    ax.set_ylabel("|amplitude| (uV)", fontsize=8)
    ax.set_title("width is what exposes the impulses", fontsize=9)
    ax.axvline(1.5, color="0.3", ls="--", lw=1)
    ax.text(1.8, 6000, "<= 1 sample:\nnot a waveform", fontsize=6.5, color="0.3")

    for ax in axes:
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.25, lw=0.5)
    fig.suptitle("Large-amplitude events are not one population", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)


# === G2: gallery ===
def fig_gallery(g: pd.DataFrame, out: Path) -> None:
    """One row per class: what these events actually look like."""
    rows = [
        ("railed", "ADC saturation at 8192 uV", None),
        ("impulse", "single-sample digital glitch", None),
        ("artifact", "synchronous across the array", None),
        ("isolated", "one electrode only, huge, normal shape", "regular"),
        ("local_cluster", "shared with 1-4 adjacent electrodes", "local"),
        ("local_cluster", "positive-led, axon-like", "axon"),
    ]
    fig, axes = plt.subplots(len(rows), 1, figsize=(10, 2.05 * len(rows)),
                             sharex=True)
    for ax, (klass, label, flavour) in zip(axes, rows, strict=True):
        sub = g[g["klass"] == klass]
        if flavour is not None:
            # Neural rows get the sanity filters, or the largest-first pick
            # simply returns near-rail events again and the row says nothing.
            sub = sub[sub["abs_amp_uv"].between(*REAL_AMP)
                      & (sub["noise_uv"] < REAL_MAX_NOISE)
                      & (sub["amp_z"] >= REAL_MIN_Z)]
        if flavour == "regular":
            sub = sub[sub["regular_shape"]]
        elif flavour == "axon":
            sub = sub[(sub["pos_ratio"] > 1.5) & (sub["width_max"] >= 3)]
        elif flavour == "local":
            sub = sub[sub["width_min"] >= REAL_MIN_WIDTH]
        sub = sub.nlargest(600, "abs_amp_uv")
        drawn = 0
        # At most three per session, so the row shows several sites rather than
        # one unit repeated.
        for (date, array), grp in sub.groupby(["date", "array"]):
            if drawn >= 14:
                break
            wf, gid = load_waveforms(date, array)
            if not len(wf):
                continue
            for gg in grp["gid"].to_numpy()[:3]:
                i = np.flatnonzero(gid == gg)
                if not len(i):
                    continue
                w = wf[i[0]]
                ax.plot(time_axis(len(w)), w, lw=0.9, alpha=0.75,
                        color=CLASS_COLOR[klass])
                drawn += 1
                if drawn >= 14:
                    break
        ax.axvline(0, color="0.75", lw=0.7, ls=":")
        ax.axhline(0, color="0.85", lw=0.6)
        ax.set_ylabel("uV", fontsize=8)
        ax.set_title(f"{klass} — {label}   (n drawn = {drawn})", fontsize=9,
                     loc="left")
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.2, lw=0.4)
    axes[-1].set_xlabel("time relative to threshold crossing (ms)", fontsize=8)
    fig.suptitle("What each class of large event looks like", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)


# === G3: the neighbouring-electrode case ===
def fig_pair_case(out: Path, date: str = "2018-04-19", array: str = "Anterior",
                  ea: int = 90, eb: int = 93) -> dict:
    """A large positive-led event seen simultaneously on two electrodes.

    Re-reads the NEV so the *partner* electrode's waveform at the coincident
    timestamp can be drawn, which is the only way to show that the two records
    are the same physical event rather than two unrelated large spikes.
    """
    idx = pd.read_parquet(OUT_DIR / "session_index.parquet")
    row = idx[(idx["date"] == date) & (idx["array"] == array)
              & (idx["kind"] == "OFS")]
    if not len(row):
        return {}
    raw, meta, cbe = open_nev(Path(row.iloc[0]["path"]))
    if ea not in cbe or eb not in cbe:
        return {}
    A = read_electrode(raw, meta, cbe[ea])
    B = read_electrode(raw, meta, cbe[eb])
    if A is None or B is None:
        return {}

    amp_a = np.maximum(np.abs(A["wf"].min(axis=1)), A["wf"].max(axis=1))
    big_a = np.flatnonzero(amp_a >= 400)
    win = 0.0003                                     # 0.3 ms, the shared-event window
    pairs = []
    for i in big_a:
        j = np.searchsorted(B["t"], A["t"][i])
        for k in (j - 1, j):
            if 0 <= k < len(B["t"]) and abs(B["t"][k] - A["t"][i]) <= win:
                pairs.append((i, k, abs(B["t"][k] - A["t"][i])))
                break

    cmp_df = parse_cmp(CMP_BY_ARRAY[array]).set_index("electrode_id")
    t_ms = (np.arange(A["wf"].shape[1]) - meta["nbefore"]) / meta["sr"] * 1000.0

    fig = plt.figure(figsize=(13, 4.4))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.05, 0.75], wspace=0.28)
    for n, (e_id, dat, sel) in enumerate([
            (ea, A, [p[0] for p in pairs]), (eb, B, [p[1] for p in pairs])]):
        ax = fig.add_subplot(gs[0, n])
        for i in sel[:60]:
            ax.plot(t_ms, dat["wf"][i], lw=0.7, alpha=0.5, color="#2ca02c")
        if sel:
            ax.plot(t_ms, dat["wf"][sel].mean(axis=0), lw=2.2, color="#0b3d20",
                    label="mean")
        ax.axvline(0, color="0.75", lw=0.7, ls=":")
        ax.axhline(0, color="0.85", lw=0.6)
        ax.set_title(f"electrode {e_id}  (col {cmp_df.loc[e_id, 'col']}, "
                     f"row {cmp_df.loc[e_id, 'row']})", fontsize=9)
        ax.set_xlabel("ms from crossing", fontsize=8)
        ax.set_ylabel("uV", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.25, lw=0.5)
        ax.legend(fontsize=7)

    ax = fig.add_subplot(gs[0, 2])
    ax.scatter(cmp_df["col"], cmp_df["row"], s=26, c="0.85", edgecolors="0.6",
               lw=0.4)
    for e_id, c in [(ea, "#2ca02c"), (eb, "#0b3d20")]:
        ax.scatter([cmp_df.loc[e_id, "col"]], [cmp_df.loc[e_id, "row"]], s=110,
                   c=c, edgecolors="k", lw=0.6, zorder=3)
        ax.annotate(str(e_id), (cmp_df.loc[e_id, "col"], cmp_df.loc[e_id, "row"]),
                    fontsize=8, xytext=(6, 5), textcoords="offset points")
    ax.plot([cmp_df.loc[ea, "col"], cmp_df.loc[eb, "col"]],
            [cmp_df.loc[ea, "row"], cmp_df.loc[eb, "row"]], "-", color="#2ca02c",
            lw=1.4, zorder=2)
    d = max(abs(cmp_df.loc[ea, "col"] - cmp_df.loc[eb, "col"]),
            abs(cmp_df.loc[ea, "row"] - cmp_df.loc[eb, "row"]))
    ax.set_title(f"{d} grid steps = {d * 400} um apart", fontsize=9)
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    fig.suptitle(f"{array} {date}: the same large positive-led event on two "
                 f"electrodes  ({len(pairs)} coincidences within 0.3 ms)",
                 fontsize=10)
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return dict(n_pairs=len(pairs), n_big_a=len(big_a), grid_steps=int(d),
                lag_us_median=float(np.median([p[2] for p in pairs]) * 1e6)
                if pairs else np.nan)


# === G4: the persistent single-electrode giant ===
def fig_persistent_site(ed: pd.DataFrame, g: pd.DataFrame, out: Path,
                        array: str = "Anterior", elec: int = 61) -> None:
    """One electrode carrying huge, isolated, normally-shaped spikes for years."""
    e = ed[(ed["array"] == array) & (ed["electrode_id"] == elec)].copy()
    e["date_dt"] = pd.to_datetime(e["date"])
    e = e.sort_values("date_dt")
    gg = g[(g["array"] == array) & (g["electrode_id"] == elec)
           & (~g["klass"].isin(NON_NEURAL))]

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4), width_ratios=[1.2, 1, 1])

    ax = axes[0]
    ax.plot(e["date_dt"], e["amp_max_clean"], "o-", ms=3.5, lw=1,
            color="#1f77b4", label="session max (cleaned)")
    ax.plot(e["date_dt"], e["amp_p99"], "o-", ms=3, lw=1, color="#ff7f0e",
            label="p99 crossing amplitude")
    ax.plot(e["date_dt"], e["noise_uv"], "-", lw=1.4, color="0.45",
            label="noise floor")
    ax.set_yscale("log")
    ax.set_ylabel("uV (log)", fontsize=8)
    ax.set_title(f"{array} electrode {elec}: amplitude over the implant life",
                 fontsize=9)
    ax.legend(fontsize=6.5)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    ax = axes[1]
    ax.plot(e["date_dt"], e["n_giant_total"] / e["n_events"] * 100, "o-", ms=3.5,
            lw=1, color="#2ca02c")
    ax.set_ylabel("% of this electrode's crossings >= 250 uV", fontsize=8)
    ax.set_title("how often the giant fires", fontsize=9)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    ax = axes[2]
    years, cmap = sorted(gg["date"].str[:4].unique()), plt.get_cmap("viridis")
    for yi, yr in enumerate(years):
        sub = gg[gg["date"].str[:4] == yr].nlargest(30, "abs_amp_uv")
        drawn = []
        for (date, arr), grp in sub.groupby(["date", "array"]):
            wf, gid = load_waveforms(date, arr)
            for ggid in grp["gid"].to_numpy()[:8]:
                i = np.flatnonzero(gid == ggid)
                # Snippet length varies across the cohort; only average within
                # a consistent length.
                if len(i) and (not drawn or wf.shape[1] == len(drawn[0])):
                    drawn.append(wf[i[0]])
        if drawn:
            ax.plot(time_axis(len(drawn[0])), np.mean(drawn, axis=0), lw=1.6,
                    color=cmap(yi / max(len(years) - 1, 1)), label=yr)
    ax.axvline(0, color="0.75", lw=0.7, ls=":")
    ax.set_xlabel("ms from crossing", fontsize=8)
    ax.set_ylabel("uV", fontsize=8)
    ax.set_title("mean giant waveform, by year", fontsize=9)
    ax.legend(fontsize=6.5, ncol=2)

    for ax in axes:
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.25, lw=0.5)
    fig.suptitle("A persistent single-electrode giant: isolated, huge, and "
                 "present for six years", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)


# === G5: where and when ===
def fig_where_when(ed: pd.DataFrame, out: Path) -> None:
    """Spatial concentration and longitudinal rate of the real giants."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.5))
    ed = ed.copy()
    ed["date_dt"] = pd.to_datetime(ed["date"])
    ed["frac_giant"] = ed["n_giant_total"] / ed["n_events"]

    for j, arr in enumerate(["Anterior", "Posterior"]):
        ax = axes[0, j]
        sub = ed[ed["array"] == arr]
        grid = np.full((10, 10), np.nan)
        agg = sub.groupby(["row", "col"])["frac_giant"].median()
        for (r, c), v in agg.items():
            if np.isfinite(r) and np.isfinite(c):
                grid[int(r), int(c)] = v * 100
        im = ax.imshow(grid, cmap="magma", vmin=0, vmax=np.nanpercentile(grid, 96))
        ax.set_title(f"{arr}: median % of crossings >= 250 uV", fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02)

    ax = axes[1, 0]
    for arr, g in ed.groupby("array"):
        s = g.groupby("date_dt")["frac_giant"].median().rolling(
            7, center=True, min_periods=2).median()
        ax.semilogy(s.index, s * 100, "-", lw=1.5,
                    color=ARRAY_COLOR[arr], label=arr)
    ax.set_ylabel("% of crossings >= 250 uV", fontsize=8)
    ax.set_title("giant rate over the implant lifetime", fontsize=9)
    ax.legend(fontsize=7)

    ax = axes[1, 1]
    conc = []
    for (d, a), g in ed.groupby(["date", "array"]):
        tot = g["n_giant_total"].sum()
        if tot < 100:
            continue
        top = g.nlargest(3, "n_giant_total")["n_giant_total"].sum()
        conc.append(dict(date_dt=pd.to_datetime(d), array=a, share=top / tot))
    c = pd.DataFrame(conc)
    for arr, g in c.groupby("array"):
        s = g.sort_values("date_dt").set_index("date_dt")["share"].rolling(
            7, center=True, min_periods=2).median()
        ax.plot(s.index, s * 100, "-", lw=1.5, color=ARRAY_COLOR[arr], label=arr)
    ax.set_ylabel("% of a session's giants held by its top 3 electrodes",
                  fontsize=8)
    ax.set_title("giants are a property of a few electrodes, not the array",
                 fontsize=9)
    ax.set_ylim(0, 100)
    ax.legend(fontsize=7)

    for ax in axes[1]:
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.25, lw=0.5)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("Where the large events live, and when", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    ed = pd.read_parquet(OUT_DIR / "events_electrode.parquet")
    g = pd.read_parquet(OUT_DIR / "giant_events.parquet")

    banner("Census")
    total = int(ed["n_giant_total"].sum())
    n_ev = int(ed["n_events"].sum())
    print(f"  events in cohort        {n_ev:,}")
    print(f"  events >= 250 uV        {total:,}  ({total / n_ev * 100:.2f}%)")
    for k in CLASS_ORDER:
        c = f"n_giant_{k}"
        if c in ed:
            print(f"    {k:16s} {int(ed[c].sum()):11,}  "
                  f"({ed[c].sum() / total * 100:5.2f}%)")
    lam = ed["chance_coincidence_big"].median()
    exp_local = (1 - np.exp(-lam)) * (24 / 95)
    obs_local = ed["n_giant_local_cluster"].sum() / total
    print(f"\n  local_cluster observed  {obs_local * 100:.2f}%")
    print(f"  expected by chance      {exp_local * 100:.2f}%   "
          f"-> {obs_local / exp_local:.1f}x excess")

    banner("Real giants after the sanity filters")
    rg = real_giants(g)
    print(f"  {len(rg):,} of {len(g):,} stored rows survive "
          f"(400-4000 uV, noise < 30 uV, z >= 20, width >= 3 samples)")
    sites = (rg.groupby(["array", "electrode_id"])
             .agg(n_sessions=("date", "nunique"), n_events=("gid", "size"),
                  first=("date", "min"), last=("date", "max"),
                  amp_med=("abs_amp_uv", "median"), amp_max=("abs_amp_uv", "max"),
                  z_med=("amp_z", "median"), noise=("noise_uv", "median"),
                  frac_axon=("axonal_like", "mean"),
                  frac_regular=("regular_shape", "mean"),
                  frac_local=("klass", lambda s: (s == "local_cluster").mean()))
             .reset_index().sort_values("n_sessions", ascending=False))
    print(f"  {len(sites)} distinct electrode sites; "
          f"{(sites['n_sessions'] >= 5).sum()} recur in >= 5 sessions")
    print()
    print(sites.head(12).round(2).to_string(index=False))
    sites.to_parquet(SITES_OUT, engine="pyarrow", index=False)

    banner("Figures")
    fig_taxonomy(ed, g, FIG_DIR / "G1_taxonomy.png")
    fig_gallery(g, FIG_DIR / "G2_gallery.png")
    info = fig_pair_case(FIG_DIR / "G3_neighbour_pair.png")
    if info:
        print(f"  neighbour pair: {info['n_pairs']} coincidences of "
              f"{info['n_big_a']} large events, {info['grid_steps']} grid steps "
              f"({info['grid_steps'] * 400} um), median lag "
              f"{info['lag_us_median']:.0f} us")
    fig_persistent_site(ed, g, FIG_DIR / "G4_persistent_site.png")
    fig_where_when(ed, FIG_DIR / "G5_where_when.png")
    for p in sorted(FIG_DIR.glob("G*.png")):
        print(f"  {p.name}")

    banner("Done")
    print(f"  {SITES_OUT.name}  ({len(sites)} sites)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

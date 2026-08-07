"""Longitudinal comparison of the headline metrics, anterior vs posterior.

The project's stated goal is longitudinal comparison across arrays. This script
is that comparison, assembled from the two independent measurement layers so
each can check the other:

- **Sorting-based** (CLAUDE.md layer 2), from `units_long.parquet`: unit count,
  yield per electrode, electrode coverage, amplitude central tendency, the
  amplitude tail, and the full amplitude distribution over time.
- **Sorting-free** (CLAUDE.md layer 1), from `events_electrode.parquet`:
  threshold-crossing rate, noise floor, amplitude percentiles and peak SNR,
  computed straight off the NEV event stream with no clustering and therefore
  no gate. If the two layers disagree about a trend, the trend is an artefact
  of the sorter rather than a property of the implant.

Two confounds are carried, never averaged away: **headstage** (2018-2019
contain Analog and Digital recordings on overlapping dates, and the amplifier
chain moves the noise floor) and **session duration** (180 s to ~2970 s, so
counts are never compared raw -- only rates and per-electrode yields).

Run from repo root:

    uv run python notebooks/scratch_rocky_longitudinal_metrics.py

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
EVENTS_IN = OUT_DIR / "events_electrode.parquet"
PANEL_OUT = OUT_DIR / "longitudinal_metrics.parquet"
FIG_DIR = REPO / "figures" / "rocky" / "longitudinal"

ARRAY_COLOR = {"Anterior": "#1f77b4", "Posterior": "#d62728"}
HS_MARKER = {"Digital": "o", "Analog": "^", "none": "s"}
N_ELECTRODES = 96
ROLL = 7                   # sessions in the trend line's centred rolling median

# Amplitude bin edges for the distribution-over-time image. Log-spaced because
# extracellular amplitudes span two decades and a linear axis hides the body of
# the distribution behind the tail.
AMP_BINS = np.logspace(np.log10(15), np.log10(3000), 40)


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# === Assembly ===
def sorted_session_metrics(units: pd.DataFrame, method: str = "resort") -> pd.DataFrame:
    """Per-session sorting-based metrics for one method.

    Parameters
    ----------
    units : pandas.DataFrame
        Long-format per-unit table, including gate-rejected clusters.
    method : str
        ``resort`` (ISO-SPLIT + gate) or ``ofs`` (Plexon).

    Returns
    -------
    pandas.DataFrame
        One row per (date, array, headstage) with counts, yield and the
        amplitude distribution summarised by percentiles.
    """
    u = units[units["method"] == method].copy()
    u["pass_gate"] = u["pass_gate"].fillna(False).astype(bool)
    keys = ["date", "array", "headstage"]
    p = u[u["pass_gate"]]

    out = p.groupby(keys).agg(
        n_units=("unit_id", "size"),
        n_elec_with_units=("electrode_id", "nunique"),
        amp_p10=("amplitude_uv", lambda s: s.quantile(0.10)),
        amp_med=("amplitude_uv", "median"),
        amp_p90=("amplitude_uv", lambda s: s.quantile(0.90)),
        amp_p99=("amplitude_uv", lambda s: s.quantile(0.99)),
        amp_max=("amplitude_uv", "max"),
        snr_med=("snr", "median"),
        rate_med=("firing_rate_hz", "median"),
        noise_med=("noise_uv", "median"),
        duration_s=("duration_s", "median"),
    ).reset_index()

    # Candidate count carries the rejection fraction, which is the single
    # number that says how hard the gate is working in that session.
    cand = u.groupby(keys).size().rename("n_candidates").reset_index()
    out = out.merge(cand, on=keys, how="left")
    out["units_per_electrode"] = out["n_units"] / N_ELECTRODES
    out["elec_coverage"] = out["n_elec_with_units"] / N_ELECTRODES
    out["pass_fraction"] = out["n_units"] / out["n_candidates"]
    out["method"] = method
    return out


def free_session_metrics(ev: pd.DataFrame) -> pd.DataFrame:
    """Per-session sorting-free metrics, aggregated across electrodes.

    Medians across electrodes rather than pooled event statistics: a single
    high-rate electrode would otherwise dominate the session summary. The
    ``_clean`` columns have cross-channel artifacts, digital impulses and
    railed samples removed at event level.
    """
    keys = ["date", "array", "headstage"]
    g = ev.groupby(keys)
    out = g.agg(
        crossing_rate_med=("crossing_rate_hz", "median"),
        crossing_rate_tot=("crossing_rate_hz", "sum"),
        noise_med=("noise_uv", "median"),
        noise_p90=("noise_uv", lambda s: s.quantile(0.90)),
        free_amp_p50=("amp_p50", "median"),
        free_amp_p90=("amp_p90", "median"),
        free_amp_p99=("amp_p99", "median"),
        free_amp_max=("amp_max", "max"),
        free_amp_max_clean=("amp_max_clean", "max"),
        free_amp_p99_clean=("amp_p99_clean", "median"),
        peak_snr_med=("peak_snr", "median"),
        peak_snr_clean_med=("peak_snr_clean", "median"),
        frac_artifact=("frac_artifact", "median"),
        n_events=("n_events", "sum"),
        n_impulse=("n_impulse_events", "sum"),
        n_railed=("n_railed_events", "sum"),
    ).reset_index()

    # Sorting-free proxy for "how many electrodes still carry signal": the
    # crossing amplitude distribution reaches 4x the electrode's own noise.
    active = (ev.assign(active=ev["peak_snr"] >= 4.0)
              .groupby(keys)["active"].mean().rename("frac_elec_active"))
    out = out.merge(active.reset_index(), on=keys, how="left")
    return out


def amplitude_image(units: pd.DataFrame, array: str) -> tuple:
    """Stack per-session unit-amplitude histograms into a date x amplitude image.

    Returns
    -------
    tuple
        ``(dates, image)`` where image is ``(n_bins - 1, n_sessions)`` of
        within-session density, so a session with few units is still visible.
    """
    u = units[(units["array"] == array) & units["pass_gate"].fillna(False)
              & (units["method"] == "resort")]
    dates = sorted(u["date"].unique())
    img = np.full((len(AMP_BINS) - 1, len(dates)), np.nan)
    for j, d in enumerate(dates):
        a = u.loc[u["date"] == d, "amplitude_uv"].dropna()
        if len(a) < 3:
            continue
        h, _ = np.histogram(a, bins=AMP_BINS)
        img[:, j] = h / max(h.sum(), 1)
    return pd.to_datetime(dates), img


# === Figures ===
def _trend(ax, df: pd.DataFrame, col: str, label: str) -> None:
    """Scatter the sessions and overlay a centred rolling median per array."""
    for arr, g in df.groupby("array"):
        g = g.sort_values("date_dt")
        for hs, gh in g.groupby("headstage"):
            ax.plot(gh["date_dt"], gh[col], HS_MARKER.get(hs, "o"),
                    ms=3, alpha=0.35, color=ARRAY_COLOR.get(arr, "0.4"), lw=0)
        roll = g.set_index("date_dt")[col].rolling(ROLL, center=True,
                                                   min_periods=2).median()
        ax.plot(roll.index, roll.values, "-", lw=1.8,
                color=ARRAY_COLOR.get(arr, "0.4"), label=arr)
    ax.set_ylabel(label, fontsize=8)
    ax.tick_params(labelsize=7)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(alpha=0.25, lw=0.5)


def fig_sorted(df: pd.DataFrame, out: Path) -> None:
    """Sorting-based headline metrics over the implant lifetime."""
    panels = [
        ("n_units", "units per session"),
        ("units_per_electrode", "yield (units / electrode)"),
        ("elec_coverage", "electrodes with >=1 unit (frac)"),
        ("amp_med", "median unit |trough| (uV)"),
        ("amp_p99", "p99 unit amplitude (uV)"),
        ("pass_fraction", "clusters passing the gate (frac)"),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharex=True)
    for ax, (col, lbl) in zip(axes.ravel(), panels, strict=True):
        _trend(ax, df, col, lbl)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Sorting-based longitudinal metrics (ISO-SPLIT + gate)\n"
                 "points = sessions (circle Digital, triangle Analog, "
                 f"square none); line = {ROLL}-session rolling median",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_free(df: pd.DataFrame, out: Path) -> None:
    """Sorting-free headline metrics -- no clustering, no gate."""
    panels = [
        ("crossing_rate_med", "crossing rate (Hz / electrode)"),
        ("noise_med", "noise floor (uV, baseline MAD)"),
        ("peak_snr_med", "peak SNR (p99 amp / noise)"),
        ("free_amp_p50", "median crossing |trough| (uV)"),
        ("free_amp_p99", "p99 crossing amplitude (uV)"),
        ("frac_elec_active", "electrodes with peak SNR >= 4 (frac)"),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharex=True)
    for ax, (col, lbl) in zip(axes.ravel(), panels, strict=True):
        _trend(ax, df, col, lbl)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Sorting-free longitudinal metrics (threshold-crossing layer)\n"
                 "computed directly from NEV events: no clustering, no gate",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_amplitude_tail(df: pd.DataFrame, out: Path) -> None:
    """The amplitude tail, before and after removing non-neural events.

    The raw session maximum is the metric most often quoted and the one most
    corrupted: a single railed sample or digital impulse sets it. The cleaned
    trace is the same quantity with cross-channel artifacts, impulses and
    railed events removed at event level.
    """
    fig, axes = plt.subplots(2, 2, figsize=(12, 6.5), sharex=True)
    for j, arr in enumerate(["Anterior", "Posterior"]):
        g = df[df["array"] == arr].sort_values("date_dt")
        ax = axes[0, j]
        ax.semilogy(g["date_dt"], g["free_amp_max"], ".", ms=3, alpha=0.4,
                    color="0.55", label="raw max")
        ax.semilogy(g["date_dt"], g["free_amp_max_clean"], ".", ms=3, alpha=0.7,
                    color=ARRAY_COLOR[arr], label="max after removing\nartifact / impulse / railed")
        ax.set_title(f"{arr}: session max crossing amplitude", fontsize=9)
        ax.set_ylabel("uV (log)", fontsize=8)
        ax.legend(fontsize=6.5, loc="upper right")

        ax = axes[1, j]
        for col, lbl, c in [("free_amp_p50", "p50", "0.3"),
                            ("free_amp_p90", "p90", "#ff7f0e"),
                            ("free_amp_p99", "p99", "#2ca02c")]:
            roll = g.set_index("date_dt")[col].rolling(ROLL, center=True,
                                                       min_periods=2).median()
            ax.plot(roll.index, roll.values, "-", lw=1.5, color=c, label=lbl)
        ax.set_title(f"{arr}: crossing-amplitude percentiles", fontsize=9)
        ax.set_ylabel("uV", fontsize=8)
        ax.legend(fontsize=7)
    for ax in axes.ravel():
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.25, lw=0.5)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("Amplitude tail over the implant lifetime, raw vs cleaned",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_amplitude_distribution(units: pd.DataFrame, out: Path) -> None:
    """Full unit-amplitude distribution as a function of date, per array."""
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    for ax, arr in zip(axes, ["Anterior", "Posterior"], strict=True):
        dates, img = amplitude_image(units, arr)
        if not len(dates):
            continue
        centers = np.sqrt(AMP_BINS[:-1] * AMP_BINS[1:])
        m = ax.pcolormesh(dates, centers, np.ma.masked_invalid(img),
                          cmap="magma", shading="nearest", vmin=0, vmax=0.25)
        ax.set_yscale("log")
        ax.set_ylabel(f"{arr}\nunit |trough| (uV)", fontsize=8)
        ax.tick_params(labelsize=7)
        fig.colorbar(m, ax=ax, fraction=0.02, pad=0.01,
                     label="within-session density")
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("Unit-amplitude distribution over time (gate-passing ISO-SPLIT units)\n"
                 "each column is one session, normalised within the session",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_layer_agreement(df: pd.DataFrame, out: Path) -> None:
    """Do the sorted and sorting-free layers tell the same longitudinal story?

    Each metric is normalised to its own 2018 median so trajectories of very
    different units can share an axis. Divergence between the layers means the
    trend is a property of the sorting, not of the recording.
    """
    pairs = [
        ("units_per_electrode", "crossing_rate_med", "yield vs crossing rate"),
        ("amp_med", "free_amp_p50", "unit amp vs crossing amp"),
        ("snr_med", "peak_snr_med", "unit SNR vs peak SNR"),
    ]
    fig, axes = plt.subplots(len(pairs), 2, figsize=(12, 8), sharex=True)
    for i, (a_col, b_col, title) in enumerate(pairs):
        for j, arr in enumerate(["Anterior", "Posterior"]):
            ax = axes[i, j]
            g = df[df["array"] == arr].sort_values("date_dt")
            base = g[g["date_dt"].dt.year == 2018]
            for col, lbl, c in [(a_col, "sorted", "#1f77b4"),
                                (b_col, "sorting-free", "#ff7f0e")]:
                ref = base[col].median()
                if not np.isfinite(ref) or ref == 0:
                    continue
                roll = (g.set_index("date_dt")[col] / ref).rolling(
                    ROLL, center=True, min_periods=2).median()
                ax.plot(roll.index, roll.values, "-", lw=1.6, color=c, label=lbl)
            ax.axhline(1.0, color="0.7", lw=0.7, ls=":")
            ax.set_ylim(0, 2.2)
            ax.tick_params(labelsize=7)
            ax.grid(alpha=0.25, lw=0.5)
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            if i == 0:
                ax.set_title(arr, fontsize=10)
            if j == 0:
                ax.set_ylabel(f"{title}\n(rel. to 2018)", fontsize=8)
            if i == 0 and j == 0:
                ax.legend(fontsize=7)
    fig.suptitle("Layer agreement: does the sorter invent or hide the trend?",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)


# === Trend statistics ===
def trend_table(df: pd.DataFrame, cols: list[tuple[str, str]]) -> pd.DataFrame:
    """Spearman correlation of each metric against elapsed days, per array."""
    rows = []
    for arr, g in df.groupby("array"):
        days = (g["date_dt"] - g["date_dt"].min()).dt.days.to_numpy()
        for col, lbl in cols:
            v = g[col].to_numpy(dtype=float)
            ok = np.isfinite(v)
            if ok.sum() < 8:
                continue
            rho, p = spearmanr(days[ok], v[ok])
            first = np.nanmedian(v[ok][:5])
            last = np.nanmedian(v[ok][-5:])
            rows.append(dict(array=arr, metric=lbl, column=col, n=int(ok.sum()),
                             rho=rho, p=p, first5=first, last5=last,
                             ratio=last / first if first else np.nan))
    return pd.DataFrame(rows)


def main() -> int:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    units = pd.read_parquet(UNITS_IN)
    ev = pd.read_parquet(EVENTS_IN)

    banner("Assembling per-session metrics")
    sorted_m = sorted_session_metrics(units, "resort")
    ofs_m = sorted_session_metrics(units, "ofs")
    free_m = free_session_metrics(ev)
    keys = ["date", "array", "headstage"]

    df = sorted_m.drop(columns=["method"]).merge(free_m, on=keys, how="outer",
                                                 suffixes=("", "_free"))
    df["date_dt"] = pd.to_datetime(df["date"])
    df = df.sort_values(["array", "date_dt"]).reset_index(drop=True)
    print(f"  sessions with sorted metrics : {len(sorted_m)}")
    print(f"  sessions with free metrics   : {len(free_m)}")
    print(f"  merged rows                  : {len(df)}")
    print(f"  date span                    : {df['date'].min()} .. {df['date'].max()}")

    banner("Figures")
    fig_sorted(df, FIG_DIR / "L1_sorted_metrics.png")
    fig_free(df, FIG_DIR / "L2_free_metrics.png")
    fig_amplitude_tail(df, FIG_DIR / "L3_amplitude_tail.png")
    fig_amplitude_distribution(units, FIG_DIR / "L4_amplitude_distribution.png")
    fig_layer_agreement(df, FIG_DIR / "L5_layer_agreement.png")
    for p in sorted(FIG_DIR.glob("L*.png")):
        print(f"  {p.name}")

    banner("Longitudinal trend statistics (Spearman rho vs elapsed days)")
    cols = [
        ("n_units", "units per session"),
        ("units_per_electrode", "yield per electrode"),
        ("elec_coverage", "electrode coverage"),
        ("amp_med", "median unit amplitude"),
        ("amp_p99", "p99 unit amplitude"),
        ("snr_med", "median unit SNR"),
        ("pass_fraction", "gate pass fraction"),
        ("crossing_rate_med", "crossing rate (free)"),
        ("noise_med", "noise floor (free)"),
        ("peak_snr_med", "peak SNR (free)"),
        ("free_amp_p50", "median crossing amp (free)"),
        ("free_amp_p99", "p99 crossing amp (free)"),
        ("frac_elec_active", "electrodes active (free)"),
    ]
    tt = trend_table(df, cols)
    print(f"{'metric':30s} {'array':10s} {'rho':>7s} {'p':>9s} "
          f"{'first5':>10s} {'last5':>10s} {'ratio':>7s}")
    print("-" * 88)
    for _, r in tt.sort_values(["metric", "array"]).iterrows():
        star = "***" if r["p"] < 1e-3 else ("**" if r["p"] < 0.01 else
                                            ("*" if r["p"] < 0.05 else ""))
        print(f"{r['metric']:30s} {r['array']:10s} {r['rho']:7.3f} "
              f"{r['p']:9.2e} {r['first5']:10.3f} {r['last5']:10.3f} "
              f"{r['ratio']:7.2f} {star}")

    df.to_parquet(PANEL_OUT, engine="pyarrow", index=False)
    tt.to_parquet(OUT_DIR / "longitudinal_trends.parquet", engine="pyarrow",
                  index=False)
    ofs_m.to_parquet(OUT_DIR / "session_metrics_ofs.parquet", engine="pyarrow",
                     index=False)
    banner("Done")
    print(f"  {PANEL_OUT.name}  ({len(df)} sessions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

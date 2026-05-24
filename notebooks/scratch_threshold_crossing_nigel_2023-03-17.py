"""Threshold-crossing baseline (Layer 1 metric) for Nigel 2023-03-17.

First sorter-free quality metric. Per-channel noise floor (MAD + SD),
threshold-crossing rate via local-minimum peak detection at k * MAD with a
1.0 ms refractory, per-peak amplitude summary, and peak SNR. Cross-validated
against session 2's curated per-electrode unit counts (Pearson + Spearman).

Run from repo root:

    uv run python notebooks/scratch_threshold_crossing_nigel_2023-03-17.py

Pipeline applied to seg[1] only (seg[0] = 2.36 s Ripple false-start, dropped
per docs/notes/segment_handling.md). 300 Hz Butterworth order-3 highpass; no
CMR at Layer 1 - see docs/notes/spike_band_filter.md for the rationale.
Scratch-first; no promotion to src/, no Tier 1 tests this session per
docs/notes/testing_policy.md.

See:
- docs/session_plans/session03_threshold_crossing.md
- docs/notes/threshold_crossing.md
- docs/notes/spike_band_filter.md
- docs/notes/segment_handling.md
- docs/notes/sorting_analyzer.md
"""

from __future__ import annotations

import re
import sys
import time
import warnings
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import probeinterface as pi
import spikeinterface
from probeinterface import Probe
from scipy.stats import pearsonr, spearmanr
from spikeinterface.core import (
    BaseRecording,
    get_noise_levels,
    load_sorting_analyzer,
)
from spikeinterface.core.template_tools import get_template_extremum_channel
from spikeinterface.extractors import read_blackrock
from spikeinterface.preprocessing import highpass_filter
from spikeinterface.sortingcomponents.peak_detection import detect_peaks

warnings.filterwarnings(
    "ignore", message="Detected .* undocumented segments within nev data"
)

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "raw"
BASE = "Nigel_Anterior_2023-03-17_Baseline_DigitalHeadstage"

NS5 = DATA / f"{BASE}.ns5"
CMP = DATA / "SN 1025-001496.cmp"

FIG_DIR = REPO / "figures" / "validation"
CACHE_DIR = REPO / "data" / "derived" / "nigel_2023-03-17"
ANALYZER_CACHE = CACHE_DIR / "sorting_analyzer_curated.zarr"
PARQUET_OUT = CACHE_DIR / "threshold_crossings.parquet"
FIGURE_OUT = FIG_DIR / "04_xc_rate_vs_curated_units.png"

UTAH_PITCH_UM = 400.0
SEG_BROADBAND = 1  # session 1: seg[0]=2.36 s false-start, seg[1]=180.01 s

# Session 1's dynamic resolver verified this file's 30 kHz broadband stream
# is id "5". Hard-coded here for brevity; a future session running on a
# different recording should re-verify.
NS5_STREAM_ID = "5"

FILTER_FREQ_HZ = 300.0
FILTER_ORDER = 3              # zero-phase forward-backward doubles effective order
REFRACTORY_MS = 1.0
THRESHOLDS = (3, 4, 5)        # k * MAD threshold-crossing factors
SD_OVER_MAD_FLAG = 2.5        # heavy-tailed / artifact-suspect channel cutoff
EXPECTED_GAIN_UV = 0.25       # Blackrock 16-bit ADC quarter-uV convention


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# === Setup helpers: CMP parsing + probe attach (mirrors sessions 1 + 2) ===
def parse_blackrock_cmp(path: Path) -> list[dict]:
    """Parse a Blackrock per-array .cmp mapfile into per-electrode records.

    Mirror of the parser in scratch_load_nigel_2023-03-17.py - duplicated
    inline per scratch-first scope.

    Parameters
    ----------
    path : Path
        Path to the .cmp file.

    Returns
    -------
    list of dict
        Keys ``col``, ``row``, ``bank``, ``elec``, ``label``, ``electrode_id``.
        See docs/notes/utah_channel_mapping.md.
    """
    rows: list[dict] = []
    for ln in path.read_text().splitlines():
        s = ln.strip()
        if not s or s.startswith("//"):
            continue
        parts = s.split()
        if len(parts) < 4:
            continue
        if not (parts[0].isdigit() and parts[1].isdigit() and parts[3].isdigit()):
            continue
        col, row, bank, elec = int(parts[0]), int(parts[1]), parts[2], int(parts[3])
        label = parts[4] if len(parts) >= 5 else f"bank{bank}_elec{elec}"
        electrode_id = (ord(bank.upper()) - ord("A")) * 32 + elec
        rows.append(
            dict(col=col, row=row, bank=bank, elec=elec, label=label, electrode_id=electrode_id)
        )
    return rows


def build_probe(cmp_rows: list[dict]) -> Probe:
    """Build a probeinterface Probe for the Utah-96 from parsed CMP rows."""
    positions = np.array(
        [[r["col"] * UTAH_PITCH_UM, r["row"] * UTAH_PITCH_UM] for r in cmp_rows], dtype=float
    )
    contact_ids = [str(r["electrode_id"]) for r in cmp_rows]
    probe = Probe(ndim=2, si_units="um")
    probe.set_contacts(
        positions=positions,
        shapes="circle",
        shape_params={"radius": 20.0},
        contact_ids=contact_ids,
    )
    probe.annotate(name="Utah-96", manufacturer="blackrock", serial="SN 1025-001496")
    return probe


def attach_probe(
    rec: BaseRecording, probe: Probe, cmp_rows: list[dict]
) -> BaseRecording:
    """Attach a Utah probe to a recording, mapping contacts by electrode_id."""
    rec_chan_ids = [str(c) for c in rec.channel_ids]
    chan_index_by_eid = {eid: i for i, eid in enumerate(rec_chan_ids)}
    contact_ids = [str(r["electrode_id"]) for r in cmp_rows]
    dev = np.array([chan_index_by_eid[cid] for cid in contact_ids], dtype=int)
    probe.set_device_channel_indices(dev)
    return rec.set_probe(probe, group_mode="by_probe")


# === Summary helpers ===
def summarise_dist(arr: np.ndarray, label: str, units: str = "") -> None:
    """Print median, IQR (P25-P75), min, max for a 1-D array."""
    q25, med, q75 = np.percentile(arr, [25, 50, 75])
    print(
        f"  {label:>18s}  median={med:.3f}  IQR=[{q25:.3f}, {q75:.3f}]  "
        f"min={arr.min():.3f}  max={arr.max():.3f}  {units}"
    )


def render_figure_4(
    rows_df: pd.DataFrame,
    curated_unit_count: Counter,
    out_path: Path,
) -> None:
    """Render figures/validation/04_xc_rate_vs_curated_units.png.

    Three side-by-side scatter panels (one per k). x = curated_unit_count,
    y = rate_hz. Suspect-artifact channels (sd_over_mad > SD_OVER_MAD_FLAG)
    plotted as red 'x'; clean channels as black 'o'. Panel title carries
    Pearson r and Spearman rho.

    Parameters
    ----------
    rows_df : DataFrame
        One row per (electrode_id, threshold_factor). Must have columns
        ``threshold_factor``, ``electrode_id``, ``rate_hz``, ``sd_over_mad``.
    curated_unit_count : Counter
        electrode_id -> number of curated units whose peak-amplitude
        electrode equals that electrode (from session 2 analyzer).
    out_path : Path
        Output PNG path.
    """
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5), sharey=False)
    ks = sorted(rows_df["threshold_factor"].unique())
    for ax, k in zip(axes, ks, strict=True):
        sub = rows_df[rows_df["threshold_factor"] == k].copy()
        sub["count"] = sub["electrode_id"].map(lambda e: curated_unit_count.get(int(e), 0))
        clean_mask = sub["sd_over_mad"] <= SD_OVER_MAD_FLAG
        # Use rho computed across ALL channels for the panel title (suspects
        # included) so the figure title matches the parquet-derived report.
        r_pearson, _ = pearsonr(sub["count"].to_numpy(), sub["rate_hz"].to_numpy())
        rho_spearman, _ = spearmanr(sub["count"].to_numpy(), sub["rate_hz"].to_numpy())
        ax.scatter(
            sub.loc[clean_mask, "count"], sub.loc[clean_mask, "rate_hz"],
            s=24, marker="o", facecolors="none", edgecolors="0.2", label="clean",
        )
        ax.scatter(
            sub.loc[~clean_mask, "count"], sub.loc[~clean_mask, "rate_hz"],
            s=44, marker="x", color="red", label=f"sd/mad > {SD_OVER_MAD_FLAG}",
        )
        ax.set_xlabel("curated units assigned to this electrode")
        ax.set_ylabel("threshold-crossing rate (Hz)")
        ax.set_title(f"k = {k}    r = {r_pearson:.2f}    rho = {rho_spearman:.2f}")
        ax.grid(True, alpha=0.3)
        if not clean_mask.all():
            ax.legend(loc="upper left", fontsize=8)
    fig.suptitle(
        "Threshold-crossing rate vs curated unit count (Nigel 2023-03-17 seg[1])",
        fontsize=12,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# === Main ===
def main() -> int:
    """Build threshold-crossing baseline metrics and cross-validate vs session 2."""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    timings: dict[str, float] = {}

    # === Step 0: print versions ===
    banner("Step 0  versions")
    print(f"python              {sys.version.split()[0]}")
    print(f"spikeinterface      {spikeinterface.__version__}")
    print(f"probeinterface      {pi.__version__}")
    print(f"figures             {FIG_DIR}")
    print(f"parquet out         {PARQUET_OUT}")
    print(f"analyzer cache      {ANALYZER_CACHE}")

    # === Step 1: load .ns5, attach probe, select seg[1] ===
    banner("Step 1  load .ns5, attach probe, select seg[1]")
    rec = read_blackrock(file_path=str(NS5), stream_id=NS5_STREAM_ID)
    sr = rec.get_sampling_frequency()        # sr: sampling rate in Hz (expected 30000.0)
    cmp_rows = parse_blackrock_cmp(CMP)
    probe = build_probe(cmp_rows)
    rec_wp = attach_probe(rec, probe, cmp_rows)
    rec_seg = rec_wp.select_segments([SEG_BROADBAND])
    dur_s = rec_seg.get_num_samples() / sr
    print(f"channels={rec_seg.get_num_channels()}  sr={sr} Hz  duration={dur_s:.2f} s")
    # Per CLAUDE.md: never hardcode gain-to-uV. Assert uniformity so the
    # downstream scalar amplitude scaling is valid.
    gains = rec_seg.get_property("gain_to_uV")
    assert np.allclose(gains, EXPECTED_GAIN_UV, atol=1e-6), (
        f"non-uniform gain_to_uV; got {gains[:5]} expected {EXPECTED_GAIN_UV}"
    )
    print(f"gain_to_uV uniform = {EXPECTED_GAIN_UV} uV/count (asserted)")

    # === Step 2: 300 Hz highpass (Butterworth order 3) ===
    banner("Step 2  highpass filter")
    t0 = time.perf_counter()
    rec_filt = highpass_filter(
        rec_seg, freq_min=FILTER_FREQ_HZ, filter_order=FILTER_ORDER,
    )
    timings["filter_construct"] = time.perf_counter() - t0
    print(f"highpass_filter(freq_min={FILTER_FREQ_HZ}, filter_order={FILTER_ORDER}) - lazy")
    print(f"  filter construction: {timings['filter_construct']:.3f} s")

    # === Step 3: noise levels (MAD + SD, both scaled and raw for MAD) ===
    banner("Step 3  noise levels (MAD and SD)")
    t0 = time.perf_counter()
    # MAD in uV: for reporting + peak_snr denominator
    mad_uv = get_noise_levels(
        rec_filt, method="mad", return_scaled=True, force_recompute=True,
    )
    # MAD in raw int16 counts: fed to detect_peaks (units gotcha - see plan)
    mad_raw = get_noise_levels(
        rec_filt, method="mad", return_scaled=False, force_recompute=True,
    )
    # SD in uV: for reporting + sd/mad heavy-tail diagnostic
    sd_uv = get_noise_levels(
        rec_filt, method="std", return_scaled=True, force_recompute=True,
    )
    timings["noise_levels"] = time.perf_counter() - t0
    sd_over_mad = sd_uv / mad_uv
    print(f"  total noise compute: {timings['noise_levels']:.2f} s")
    summarise_dist(mad_uv, "mad_uv", "uV")
    summarise_dist(sd_uv, "sd_uv", "uV")
    summarise_dist(sd_over_mad, "sd_over_mad", "(~1.4826 under Gaussian)")
    suspect_idx = np.flatnonzero(sd_over_mad > SD_OVER_MAD_FLAG)
    rec_chan_ids = [str(c) for c in rec_seg.channel_ids]
    if suspect_idx.size:
        print(f"  suspect channels (sd_over_mad > {SD_OVER_MAD_FLAG}): "
              f"{[rec_chan_ids[i] for i in suspect_idx]}")
    else:
        print(f"  suspect channels (sd_over_mad > {SD_OVER_MAD_FLAG}): none")

    # === Step 4: detect_peaks at k in (3, 4, 5) ===
    banner("Step 4  detect_peaks (by_channel, peak_sign='neg', refractory 1.0 ms)")
    peaks_by_k: dict[int, np.ndarray] = {}
    timings_peaks: dict[int, float] = {}
    for k in THRESHOLDS:
        t0 = time.perf_counter()
        peaks_k = detect_peaks(
            rec_filt,
            method="by_channel",
            peak_sign="neg",
            detect_threshold=k,
            exclude_sweep_ms=REFRACTORY_MS,
            noise_levels=mad_raw,
        )
        timings_peaks[k] = time.perf_counter() - t0
        peaks_by_k[k] = peaks_k
        print(f"  k={k}: n_peaks={len(peaks_k):>8d}   "
              f"runtime={timings_peaks[k]:.2f} s")
    timings["detect_peaks_total"] = sum(timings_peaks.values())
    # One-line units sanity check at k=3
    p0 = peaks_by_k[THRESHOLDS[0]][0]
    ch0 = int(p0["channel_index"])
    amp_uv = abs(float(p0["amplitude"])) * float(gains[ch0])
    thr_uv = THRESHOLDS[0] * float(mad_uv[ch0])
    print(f"  sanity: first k={THRESHOLDS[0]} peak |amp|={amp_uv:.2f} uV  "
          f"threshold={thr_uv:.2f} uV  (should be >=)")

    # === Step 5: per-channel records (counts, amplitude summaries) ===
    banner("Step 5  per-channel records")
    t0 = time.perf_counter()
    nch = rec_seg.get_num_channels()
    records: list[dict] = []
    by_eid = {r["electrode_id"]: r for r in cmp_rows}
    for k in THRESHOLDS:
        peaks_k = peaks_by_k[k]
        # amp_uv: per-peak |amplitude| in microvolts, using per-channel gain.
        amp_uv_arr = np.abs(peaks_k["amplitude"].astype(np.float64)) * gains[peaks_k["channel_index"]]
        for ch_idx in range(nch):
            mask = peaks_k["channel_index"] == ch_idx
            n_peaks = int(mask.sum())
            ch_id = rec_chan_ids[ch_idx]
            eid = int(ch_id)
            cmp_r = by_eid[eid]
            if n_peaks:
                amps = amp_uv_arr[mask]
                amp_med = float(np.median(amps))
                amp_p10 = float(np.percentile(amps, 10))
                amp_p90 = float(np.percentile(amps, 90))
            else:
                amp_med = amp_p10 = amp_p90 = float("nan")
            peak_snr = amp_med / float(mad_uv[ch_idx]) if n_peaks else float("nan")
            records.append(dict(
                electrode_id=eid,
                channel_id=ch_id,
                channel_index=ch_idx,
                bank=cmp_r["bank"],
                elec_in_bank=cmp_r["elec"],
                mad_uv=float(mad_uv[ch_idx]),
                sd_uv=float(sd_uv[ch_idx]),
                sd_over_mad=float(sd_over_mad[ch_idx]),
                threshold_factor=k,
                n_peaks=n_peaks,
                rate_hz=n_peaks / dur_s,
                peak_amp_median_uv=amp_med,
                peak_amp_p10_uv=amp_p10,
                peak_amp_p90_uv=amp_p90,
                peak_snr=peak_snr,
            ))
    timings["per_channel_records"] = time.perf_counter() - t0
    rows_df = pd.DataFrame(records)
    assert len(rows_df) == nch * len(THRESHOLDS), (
        f"expected {nch * len(THRESHOLDS)} rows, got {len(rows_df)}"
    )
    print(f"  built {len(rows_df)} rows in {timings['per_channel_records']:.2f} s")
    for k in THRESHOLDS:
        rates = rows_df.loc[rows_df["threshold_factor"] == k, "rate_hz"]
        print(f"  k={k}  rate_hz  min={rates.min():.2f}  median={rates.median():.2f}  "
              f"max={rates.max():.2f}")

    # === Step 6: Tier 2 invariant: n_peaks(k=3) >= n_peaks(k=4) >= n_peaks(k=5) ===
    banner("Step 6  Tier 2 invariant  n_peaks(k=3) >= k=4 >= k=5 per channel")
    counts_by_k = {
        k: rows_df.loc[rows_df["threshold_factor"] == k, "n_peaks"].to_numpy()
        for k in THRESHOLDS
    }
    ok_mask = (counts_by_k[3] >= counts_by_k[4]) & (counts_by_k[4] >= counts_by_k[5])
    n_ok = int(ok_mask.sum())
    print(f"  {n_ok} / {nch} channels satisfy the invariant")
    if n_ok < nch:
        fail_idx = np.flatnonzero(~ok_mask)
        print(f"  FAILING channel indices: {fail_idx.tolist()}")
    assert n_ok == nch, "Tier 2 invariant violated"

    # === Step 7: cross-validate vs session 2 cached SortingAnalyzer ===
    banner("Step 7  cross-validation against curated peak-electrode assignment")
    t0 = time.perf_counter()
    sa = load_sorting_analyzer(ANALYZER_CACHE)
    peak_id_by_unit = get_template_extremum_channel(
        sa, peak_sign="neg", mode="peak_to_peak", outputs="id",
    )
    # channel_id strings -> int; tally per electrode
    peak_eid_by_unit = {u: int(cid) for u, cid in peak_id_by_unit.items()}
    curated_unit_count: Counter = Counter(peak_eid_by_unit.values())
    rows_df["curated_unit_count"] = rows_df["electrode_id"].map(
        lambda e: curated_unit_count.get(int(e), 0)
    )
    print(f"  curated units: total={sum(curated_unit_count.values())}  "
          f"electrodes covered={len(curated_unit_count)}")
    correlations: dict[int, dict] = {}
    for k in THRESHOLDS:
        sub = rows_df[rows_df["threshold_factor"] == k]
        x = sub["curated_unit_count"].to_numpy()
        y = sub["rate_hz"].to_numpy()
        r_p, _ = pearsonr(x, y)
        rho_s, _ = spearmanr(x, y)
        correlations[k] = dict(pearson=r_p, spearman=rho_s)
        print(f"  k={k}  Pearson r={r_p:.3f}   Spearman rho={rho_s:.3f}")
    timings["cross_validate"] = time.perf_counter() - t0
    print(f"  cross-validation: {timings['cross_validate']:.2f} s")

    # === Step 8: write parquet ===
    banner("Step 8  write parquet")
    t0 = time.perf_counter()
    rows_df.to_parquet(PARQUET_OUT, engine="pyarrow", index=False)
    timings["parquet_write"] = time.perf_counter() - t0
    size_kb = PARQUET_OUT.stat().st_size / 1024
    print(f"  wrote {PARQUET_OUT}  ({size_kb:.1f} KB)  "
          f"in {timings['parquet_write']:.2f} s")

    # === Step 9: render Figure 4 ===
    banner("Step 9  render Figure 4")
    t0 = time.perf_counter()
    render_figure_4(rows_df, curated_unit_count, FIGURE_OUT)
    timings["figure"] = time.perf_counter() - t0
    print(f"  wrote {FIGURE_OUT}  in {timings['figure']:.2f} s")

    # === Step 10: final report - per-step wall-clock ===
    banner("Final report  per-step wall-clock and headline numbers")
    total = sum(timings.values()) + sum(timings_peaks.values()) - timings["detect_peaks_total"]
    # adjust: detect_peaks_total is sum of timings_peaks; avoid double-counting
    print("  step                       seconds")
    print("  ----------------------    --------")
    print(f"  filter_construct          {timings['filter_construct']:7.3f}")
    print(f"  noise_levels (3 calls)    {timings['noise_levels']:7.3f}")
    for k in THRESHOLDS:
        print(f"  detect_peaks (k={k})       {timings_peaks[k]:7.3f}")
    print(f"  per_channel_records       {timings['per_channel_records']:7.3f}")
    print(f"  cross_validate            {timings['cross_validate']:7.3f}")
    print(f"  parquet_write             {timings['parquet_write']:7.3f}")
    print(f"  figure                    {timings['figure']:7.3f}")
    print(f"  TOTAL (sum of above)      {total:7.3f}")
    print()
    print(f"  suspect channels (sd_over_mad > {SD_OVER_MAD_FLAG}): "
          f"{[rec_chan_ids[i] for i in suspect_idx] if suspect_idx.size else 'none'}")
    print(f"  Tier 2 invariant: {n_ok}/{nch} channels OK")
    print("  Pearson / Spearman per k:")
    for k in THRESHOLDS:
        print(f"    k={k}   r={correlations[k]['pearson']:+.3f}   "
              f"rho={correlations[k]['spearman']:+.3f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

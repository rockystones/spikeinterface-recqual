"""Per-electrode snippet re-sort for the Rocky Utah-array cohort.

The Rocky cohort is snippet-only: NEV files carry pre-detected single-channel
waveform clips ``(n_spikes, 1, 30)`` and no continuous broadband. Every sorter
in CLAUDE.md's pool (MountainSort5, Kilosort4, Tridesclous2, SpykingCircus2)
requires continuous traces and is therefore unusable here.

At 400 um Utah pitch there is no spatial oversampling, so each electrode is an
independent single-channel recording. This script does what Plexon Offline
Sorter does -- per-electrode PCA + clustering -- but substitutes ISO-SPLIT for
T-Dist E-M and adds an explicit noise-cluster rejection gate, which is the fix
for OFS producing too many false-positive units on the noisy later sessions.

Run from repo root:

    uv run python notebooks/scratch_rocky_resort.py --single <path-to-orig.nev>
    uv run python notebooks/scratch_rocky_resort.py --all [--n-jobs -1] [--limit N]

See:
- docs/session_plans/session04_rocky_resort.md
- docs/notes/snippet_sorting.md
"""

from __future__ import annotations

import argparse
import re
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from neo.rawio import BlackrockRawIO
from sklearn.decomposition import PCA

warnings.filterwarnings(
    "ignore", message="Detected .* undocumented segments within nev data"
)

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "data" / "derived" / "rocky"
INDEX_IN = OUT_DIR / "session_index.parquet"
UNITS_OUT = OUT_DIR / "units_long.parquet"
SHARD_DIR = OUT_DIR / "shards"

SPIKE_CHANNEL_NAME_RE = re.compile(r"^ch(?P<elec>\d+)#(?P<unit>\d+)$")

# --- Array / acquisition constants ---
N_ELECTRODES = 96          # Utah-96; NSP exposes aux channels above this
PLEXON_DROP_UNITS = (0, 255)  # 0 = unsorted, 255 = noise (CLAUDE.md gotcha)

# --- Feature extraction ---
N_PCA = 5                  # PCs retained for clustering
ALIGN_WINDOW = 2           # +/- samples searched when re-aligning on the trough
MAX_SPIKES_CLUSTER = 20_000  # subsample cap for ISO-SPLIT; rest assigned after

# --- Noise-rejection gate (tuned in the prototype step, then frozen) ---
MIN_SNR = 4.0              # |trough| / baseline MAD
MIN_SPIKES = 50            # per unit over the session
PT_MS_MIN, PT_MS_MAX = 0.15, 1.20   # physiological peak-to-trough duration
TROUGH_TOL_MS = 0.20       # trough must sit near the alignment point
ISI_REFRACTORY_MS = 1.5    # refractory window for violation rate
ISI_VIOL_MAX = 0.05        # above this the unit is flagged, not deleted


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# === NEV snippet loading ===
def load_snippets(nev_path: Path) -> dict:
    """Load all spike snippets from a NEV, grouped by electrode.

    Pools every Plexon unit id per electrode, so the result is the full set of
    threshold-crossing events regardless of any labels already in the file.
    Electrodes above ``N_ELECTRODES`` are dropped: the NSP exposes auxiliary
    channels (observed up to ch112) that are not array electrodes.

    Parameters
    ----------
    nev_path : Path
        Path to the .nev file.

    Returns
    -------
    dict
        ``sr`` sampling rate, ``gain`` uV/count, ``nbefore`` pre-trigger
        samples, ``duration_s``, and ``by_elec`` mapping
        ``electrode_id -> dict(wf=(n, n_samples) float32 uV,
        t=(n,) float64 seconds, plexon_unit=(n,) int)``.
    """
    raw = BlackrockRawIO(filename=str(nev_path.with_suffix("")))
    raw.parse_header()
    chans = raw.header["spike_channels"]
    nseg = raw.segment_count(block_index=0)
    duration = sum(
        raw.segment_t_stop(0, s) - raw.segment_t_start(0, s) for s in range(nseg)
    )

    first = chans[0]
    gain = float(first["wf_gain"])          # uV per count, read never hardcoded
    nbefore = int(first["wf_left_sweep"])
    sr = float(first["wf_sampling_rate"])

    by_elec: dict[int, dict] = {}
    for i, ch in enumerate(chans):
        m = SPIKE_CHANNEL_NAME_RE.match(str(ch["name"]))
        if not m:
            continue
        elec, unit = int(m["elec"]), int(m["unit"])
        if elec < 1 or elec > N_ELECTRODES:
            continue  # NSP auxiliary channel, not an array electrode
        wfs, ts = [], []
        for s in range(nseg):
            n = raw.spike_count(block_index=0, seg_index=s, spike_channel_index=i)
            if not n:
                continue
            w = raw.get_spike_raw_waveforms(
                block_index=0, seg_index=s, spike_channel_index=i
            )
            t = raw.get_spike_timestamps(
                block_index=0, seg_index=s, spike_channel_index=i
            )
            t = raw.rescale_spike_timestamp(t, dtype="float64")
            wfs.append(np.asarray(w).reshape(n, -1))
            ts.append(np.asarray(t))
        if not wfs:
            continue
        w = np.concatenate(wfs, axis=0).astype(np.float32) * gain  # -> uV
        t = np.concatenate(ts, axis=0)
        u = np.full(len(t), unit, dtype=np.int32)
        if elec in by_elec:
            e = by_elec[elec]
            e["wf"] = np.concatenate([e["wf"], w], axis=0)
            e["t"] = np.concatenate([e["t"], t])
            e["plexon_unit"] = np.concatenate([e["plexon_unit"], u])
        else:
            by_elec[elec] = dict(wf=w, t=t, plexon_unit=u)

    # Restore chronological order within each electrode
    for e in by_elec.values():
        order = np.argsort(e["t"], kind="stable")
        e["wf"], e["t"], e["plexon_unit"] = (
            e["wf"][order], e["t"][order], e["plexon_unit"][order]
        )

    return dict(sr=sr, gain=gain, nbefore=nbefore,
                duration_s=float(duration), by_elec=by_elec)


def open_nev(nev_path: Path) -> tuple:
    """Open a NEV and return (raw, meta, electrode -> spike-channel indices).

    Splitting the open from the read lets callers stream one electrode at a
    time instead of materialising the whole file. A single 2017 session holds
    2.4M snippets (~290 MB as float32); loading all 96 electrodes at once is
    what exhausted RAM under parallel execution.

    Parameters
    ----------
    nev_path : Path
        Path to the .nev file.

    Returns
    -------
    tuple
        ``(raw, meta, chan_by_elec)`` where ``meta`` holds ``sr``, ``gain``,
        ``nbefore``, ``duration_s``, ``n_segments``.
    """
    raw = BlackrockRawIO(filename=str(nev_path.with_suffix("")))
    raw.parse_header()
    chans = raw.header["spike_channels"]
    nseg = raw.segment_count(block_index=0)
    duration = sum(
        raw.segment_t_stop(0, s) - raw.segment_t_start(0, s) for s in range(nseg)
    )
    first = chans[0]
    meta = dict(
        sr=float(first["wf_sampling_rate"]),
        gain=float(first["wf_gain"]),
        nbefore=int(first["wf_left_sweep"]),
        duration_s=float(duration),
        n_segments=nseg,
    )
    chan_by_elec: dict[int, list[tuple[int, int]]] = {}
    for i, ch in enumerate(chans):
        m = SPIKE_CHANNEL_NAME_RE.match(str(ch["name"]))
        if not m:
            continue
        elec, unit = int(m["elec"]), int(m["unit"])
        if elec < 1 or elec > N_ELECTRODES:
            continue  # NSP auxiliary channel, not an array electrode
        chan_by_elec.setdefault(elec, []).append((i, unit))
    return raw, meta, chan_by_elec


def read_electrode(raw, meta: dict, chan_units: list[tuple[int, int]]) -> dict | None:
    """Read every snippet on one electrode, pooling across its Plexon units.

    Parameters
    ----------
    raw : BlackrockRawIO
        Already header-parsed.
    meta : dict
        From :func:`open_nev`.
    chan_units : list of (int, int)
        ``(spike_channel_index, plexon_unit_id)`` pairs for this electrode.

    Returns
    -------
    dict or None
        ``wf`` (n, n_samples) float32 uV, ``t`` (n,) seconds, ``plexon_unit``
        (n,) int. None if the electrode has no events.
    """
    gain, nseg = meta["gain"], meta["n_segments"]
    wfs, ts, us = [], [], []
    for ci, unit in chan_units:
        for s in range(nseg):
            n = raw.spike_count(block_index=0, seg_index=s, spike_channel_index=ci)
            if not n:
                continue
            w = raw.get_spike_raw_waveforms(
                block_index=0, seg_index=s, spike_channel_index=ci
            )
            t = raw.get_spike_timestamps(
                block_index=0, seg_index=s, spike_channel_index=ci
            )
            t = raw.rescale_spike_timestamp(t, dtype="float64")
            wfs.append(np.asarray(w).reshape(n, -1).astype(np.float32) * gain)
            ts.append(np.asarray(t))
            us.append(np.full(n, unit, dtype=np.int32))
    if not wfs:
        return None
    wf = np.concatenate(wfs, axis=0)
    t = np.concatenate(ts)
    u = np.concatenate(us)
    order = np.argsort(t, kind="stable")
    return dict(wf=wf[order], t=t[order], plexon_unit=u[order])


# === Noise floor from pre-trigger baseline ===
def baseline_noise_uv(wf: np.ndarray, nbefore: int) -> float:
    """Estimate the electrode noise floor in uV from snippet pre-trigger samples.

    With no continuous trace there is no MAD-from-traces. But every snippet
    carries ``nbefore`` samples recorded *before* the threshold crossing, which
    are baseline by construction. Their MAD across all snippets is a robust
    per-electrode noise estimate.

    The last two pre-trigger samples are excluded: on a fast-rising spike they
    already contain part of the depolarisation and would bias the estimate up.

    Parameters
    ----------
    wf : np.ndarray
        ``(n_spikes, n_samples)`` waveforms in uV.
    nbefore : int
        Number of pre-trigger samples.

    Returns
    -------
    float
        MAD-based sigma estimate in uV (MAD / 0.6745). Falls back to the
        whole-snippet MAD if too few baseline samples exist.
    """
    stop = max(1, nbefore - 2)
    base = wf[:, :stop]
    if base.size < 32:
        base = wf
    med = np.median(base)
    mad = np.median(np.abs(base - med))
    return float(mad / 0.6745) if mad > 0 else float(np.std(base) or 1.0)


# === Alignment + features ===
def align_on_trough(wf: np.ndarray, nbefore: int, window: int = ALIGN_WINDOW) -> np.ndarray:
    """Roll each waveform so its negative peak sits exactly at ``nbefore``.

    The NSP triggers on threshold crossing, which leaves +/-1-2 samples of
    jitter relative to the true trough. Removing it tightens clusters
    materially and costs one argmin per spike.

    Parameters
    ----------
    wf : np.ndarray
        ``(n_spikes, n_samples)`` in uV.
    nbefore : int
        Index the trough should land on.
    window : int
        Half-width of the search window around ``nbefore``.

    Returns
    -------
    np.ndarray
        Aligned copy, same shape.
    """
    lo, hi = max(0, nbefore - window), min(wf.shape[1], nbefore + window + 1)
    shifts = np.argmin(wf[:, lo:hi], axis=1) + lo - nbefore
    out = np.empty_like(wf)
    for s in np.unique(shifts):
        rows = shifts == s
        out[rows] = np.roll(wf[rows], -int(s), axis=1)
    return out


def cluster_snippets(feats: np.ndarray, seed: int = 0) -> np.ndarray:
    """Cluster PCA features with ISO-SPLIT, subsampling if very large.

    ISO-SPLIT (MountainSort5's clustering) determines the cluster count
    automatically via a non-parametric unimodality test and assumes no cluster
    shape -- the right properties for single-channel snippet data.

    Parameters
    ----------
    feats : np.ndarray
        ``(n_spikes, n_pca)`` feature matrix.
    seed : int
        RNG seed for the subsample.

    Returns
    -------
    np.ndarray
        ``(n_spikes,)`` integer labels, 1-based as ISO-SPLIT returns them.
    """
    import isosplit6

    n = len(feats)
    if n <= MAX_SPIKES_CLUSTER:
        return np.asarray(isosplit6.isosplit6(feats))

    # Fit on a random subsample, then assign the rest to the nearest centroid.
    rng = np.random.default_rng(seed)
    idx = rng.choice(n, MAX_SPIKES_CLUSTER, replace=False)
    sub_lab = np.asarray(isosplit6.isosplit6(feats[idx]))
    labels = np.zeros(n, dtype=int)
    labels[idx] = sub_lab
    cents = np.stack([
        feats[idx][sub_lab == k].mean(axis=0) for k in np.unique(sub_lab)
    ])
    rest = np.setdiff1d(np.arange(n), idx, assume_unique=False)
    d = ((feats[rest][:, None, :] - cents[None, :, :]) ** 2).sum(axis=2)
    labels[rest] = np.unique(sub_lab)[np.argmin(d, axis=1)]
    return labels


# === Per-unit metrics + the noise gate ===
def unit_metrics(
    wf: np.ndarray, t: np.ndarray, noise_uv: float, sr: float,
    nbefore: int, duration_s: float,
) -> dict:
    """Compute waveform and spike-train metrics for one cluster.

    Parameters
    ----------
    wf : np.ndarray
        ``(n_spikes, n_samples)`` in uV for this cluster.
    t : np.ndarray
        Spike times in seconds.
    noise_uv : float
        Electrode noise floor from :func:`baseline_noise_uv`.
    sr : float
        Sampling rate in Hz.
    nbefore : int
        Pre-trigger sample count (the alignment point).
    duration_s : float
        Session duration in seconds.

    Returns
    -------
    dict
        Metrics plus ``pass_gate`` and a human-readable ``reject_reason``.
    """
    n = len(t)
    tmpl = wf.mean(axis=0)                     # tmpl: mean waveform, uV
    trough_idx = int(np.argmin(tmpl))
    trough_uv = float(tmpl[trough_idx])
    # Peak searched only *after* the trough: the repolarisation peak is what
    # defines peak-to-trough duration for an extracellular action potential.
    post = tmpl[trough_idx:]
    peak_rel = int(np.argmax(post)) if len(post) > 1 else 0
    peak_uv = float(post[peak_rel]) if len(post) > 1 else 0.0
    pt_ms = peak_rel / sr * 1000.0
    trough_offset_ms = (trough_idx - nbefore) / sr * 1000.0

    snr = abs(trough_uv) / noise_uv if noise_uv > 0 else 0.0
    rate = n / duration_s if duration_s > 0 else 0.0

    isi = np.diff(np.sort(t))
    isi_viol = float((isi < ISI_REFRACTORY_MS / 1000.0).mean()) if len(isi) else 0.0

    # Presence ratio over 10 equal bins
    if n and duration_s > 0:
        bins = np.linspace(0, duration_s, 11)
        occupied = np.histogram(t, bins=bins)[0] > 0
        presence = float(occupied.mean())
    else:
        presence = 0.0

    reasons: list[str] = []
    if n < MIN_SPIKES:
        reasons.append(f"n_spikes<{MIN_SPIKES}")
    if snr < MIN_SNR:
        reasons.append(f"snr<{MIN_SNR}")
    if not (PT_MS_MIN <= pt_ms <= PT_MS_MAX):
        reasons.append("peak_trough_out_of_range")
    if abs(trough_offset_ms) > TROUGH_TOL_MS:
        reasons.append("trough_off_alignment")

    return dict(
        n_spikes=n,
        duration_s=duration_s,
        firing_rate_hz=rate,
        snr=snr,
        trough_uv=trough_uv,
        peak_uv=peak_uv,
        amplitude_uv=abs(trough_uv),
        peak_trough_ms=pt_ms,
        trough_offset_ms=trough_offset_ms,
        isi_viol_rate=isi_viol,
        isi_contaminated=isi_viol > ISI_VIOL_MAX,
        presence_ratio=presence,
        noise_uv=noise_uv,
        pass_gate=len(reasons) == 0,
        reject_reason=";".join(reasons),
    )


# === Per-file driver ===
def resort_file(nev_path: Path, meta: dict, method_label: str = "resort") -> pd.DataFrame:
    """Re-sort every electrode in one NEV and return a long-format metric table.

    Parameters
    ----------
    nev_path : Path
        Path to the unsorted original .nev.
    meta : dict
        Session metadata (date, array, headstage, ...) copied onto every row.
    method_label : str
        Value written to the ``method`` column.

    Returns
    -------
    pandas.DataFrame
        One row per candidate unit, including gate-rejected ones (so the cut
        is auditable rather than silently applied).
    """
    data = load_snippets(nev_path)
    sr, nbefore, dur = data["sr"], data["nbefore"], data["duration_s"]
    rows: list[dict] = []

    for elec, e in sorted(data["by_elec"].items()):
        wf, t = e["wf"], e["t"]
        if len(t) < MIN_SPIKES:
            continue
        noise = baseline_noise_uv(wf, nbefore)
        wf_al = align_on_trough(wf, nbefore)
        n_pc = min(N_PCA, wf_al.shape[1], max(2, len(wf_al) - 1))
        feats = PCA(n_components=n_pc, random_state=0).fit_transform(wf_al)
        labels = cluster_snippets(feats)

        for k in np.unique(labels):
            sel = labels == k
            m = unit_metrics(wf_al[sel], t[sel], noise, sr, nbefore, dur)
            m.update(meta)
            m.update(dict(method=method_label, electrode_id=int(elec),
                          unit_id=int(k), n_clusters_on_elec=int(len(np.unique(labels)))))
            rows.append(m)

    return pd.DataFrame(rows)


def ofs_metrics_file(nev_path: Path, meta: dict) -> pd.DataFrame:
    """Compute the same metrics on Plexon OFS's own unit labels.

    Plexon is a reference, never ground truth (CLAUDE.md). Units 0 (unsorted)
    and 255 (noise) are dropped, matching the session-1 convention.

    Parameters
    ----------
    nev_path : Path
        Path to the OFS ``-01.nev``.
    meta : dict
        Session metadata copied onto every row.

    Returns
    -------
    pandas.DataFrame
        One row per OFS unit, with ``pass_gate`` evaluated under the *same*
        gate as the re-sort so the two are directly comparable.
    """
    data = load_snippets(nev_path)
    sr, nbefore, dur = data["sr"], data["nbefore"], data["duration_s"]
    rows: list[dict] = []
    for elec, e in sorted(data["by_elec"].items()):
        wf, t, pu = e["wf"], e["t"], e["plexon_unit"]
        if not len(t):
            continue
        noise = baseline_noise_uv(wf, nbefore)
        wf_al = align_on_trough(wf, nbefore)
        for u in np.unique(pu):
            if u in PLEXON_DROP_UNITS:
                continue
            sel = pu == u
            if sel.sum() == 0:
                continue
            m = unit_metrics(wf_al[sel], t[sel], noise, sr, nbefore, dur)
            m.update(meta)
            m.update(dict(method="ofs", electrode_id=int(elec), unit_id=int(u),
                          n_clusters_on_elec=int(len(set(pu.tolist()) - set(PLEXON_DROP_UNITS)))))
            rows.append(m)
    return pd.DataFrame(rows)


def plot_gate_audit(
    nev_path: Path, meta: dict, out_png: Path, n_elec: int = 24
) -> None:
    """Save a figure of every cluster template, coloured by gate outcome.

    The noise gate is only defensible if the rejected waveforms are visibly
    not spikes. This renders the first ``n_elec`` electrodes with at least two
    clusters: green = passed, red dashed = rejected, with the +/-noise band
    shaded so the SNR cut is visually obvious.

    Parameters
    ----------
    nev_path : Path
        Original .nev.
    meta : dict
        Session metadata, used for the title.
    out_png : Path
        Output path.
    n_elec : int
        Maximum electrodes to draw.
    """
    import matplotlib.pyplot as plt

    data = load_snippets(nev_path)
    sr, nbefore, dur = data["sr"], data["nbefore"], data["duration_s"]
    panels = []
    for elec, e in sorted(data["by_elec"].items()):
        if len(e["t"]) < MIN_SPIKES:
            continue
        noise = baseline_noise_uv(e["wf"], nbefore)
        wf_al = align_on_trough(e["wf"], nbefore)
        n_pc = min(N_PCA, wf_al.shape[1], max(2, len(wf_al) - 1))
        feats = PCA(n_components=n_pc, random_state=0).fit_transform(wf_al)
        labels = cluster_snippets(feats)
        clusters = []
        for k in np.unique(labels):
            sel = labels == k
            m = unit_metrics(wf_al[sel], e["t"][sel], noise, sr, nbefore, dur)
            clusters.append((wf_al[sel].mean(axis=0), m))
        panels.append((elec, noise, clusters))
        if len(panels) >= n_elec:
            break

    ncol = 6
    nrow = int(np.ceil(len(panels) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(3 * ncol, 2.3 * nrow), squeeze=False)
    t_ms = (np.arange(next(iter(panels))[2][0][0].shape[0]) - nbefore) / sr * 1000.0
    for ax, (elec, noise, clusters) in zip(axes.ravel(), panels, strict=False):
        ax.axhspan(-noise, noise, color="0.85", zorder=0)
        for tmpl, m in clusters:
            ok = m["pass_gate"]
            ax.plot(t_ms, tmpl, lw=1.4 if ok else 0.9,
                    color="green" if ok else "red",
                    ls="-" if ok else "--",
                    label=f"{'PASS' if ok else 'rej'} snr={m['snr']:.1f} n={m['n_spikes']}")
        ax.set_title(f"elec {elec}  noise={noise:.1f} uV", fontsize=8)
        ax.tick_params(labelsize=6)
        ax.legend(fontsize=5, loc="lower right", framealpha=0.6)
    for ax in axes.ravel()[len(panels):]:
        ax.axis("off")
    fig.suptitle(
        f"Noise-gate audit  {meta.get('stem', nev_path.stem)}\n"
        f"green = passes gate, red dashed = rejected, grey band = +/-1 noise sigma",
        fontsize=11,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=140, bbox_inches="tight")
    plt.close(fig)


def meta_from_row(row: pd.Series) -> dict:
    """Extract the session-identifying fields carried onto every metric row."""
    return dict(
        date=row["date"], array=row["array"], serial=row["serial"],
        headstage=row["headstage"], stem=row["stem"],
    )


def process_combo(ofs_path: str, meta: dict) -> pd.DataFrame:
    """Derive both the re-sort and the OFS scoring from a single NEV read.

    Verified on two sessions spanning the cohort: the ``-01`` file holds an
    event set *identical* to its unsorted original (2,457,967 and 153,763
    events respectively, matching exactly) -- Plexon relabels events, it never
    adds or removes them. Reading only the ``-01`` therefore halves I/O on a
    cohort whose single files reach 513 MB, and has the side benefit of making
    the two methods score literally the same events, so the comparison is
    exact rather than approximate.

    Module-level (not a closure) so joblib's loky backend can pickle it on
    Windows. Failures are captured as an ``error`` column rather than raised,
    so one bad file cannot abort a 332-combo run.

    Parameters
    ----------
    ofs_path : str
        Path to the Plexon ``-01`` file.
    meta : dict
        Session metadata copied onto every row.

    Returns
    -------
    pandas.DataFrame
        Concatenated ``resort`` and ``ofs`` rows for this session.
    """
    try:
        raw, nmeta, chan_by_elec = open_nev(Path(ofs_path))
    except Exception as e:  # noqa: BLE001
        return pd.DataFrame([{**meta, "method": "error",
                              "error": f"load: {type(e).__name__}: {e}"}])

    sr, nbefore, dur = nmeta["sr"], nmeta["nbefore"], nmeta["duration_s"]
    rows: list[dict] = []

    # Stream one electrode at a time. Peak memory is a single electrode
    # (~3 MB) rather than the whole file (~290 MB on 2017 sessions), which is
    # what let parallel workers exhaust RAM on the first attempts.
    for elec in sorted(chan_by_elec):
        e = read_electrode(raw, nmeta, chan_by_elec[elec])
        if e is None:
            continue
        wf, t, pu = e["wf"], e["t"], e["plexon_unit"]
        if len(t) < MIN_SPIKES:
            continue
        noise = baseline_noise_uv(wf, nbefore)
        wf_al = align_on_trough(wf, nbefore)
        del e["wf"], wf

        # --- our re-sort: ignore Plexon labels, cluster from scratch ---
        try:
            n_pc = min(N_PCA, wf_al.shape[1], max(2, len(wf_al) - 1))
            feats = PCA(n_components=n_pc, random_state=0).fit_transform(wf_al)
            labels = cluster_snippets(feats)
            n_cl = int(len(np.unique(labels)))
            for k in np.unique(labels):
                sel = labels == k
                m = unit_metrics(wf_al[sel], t[sel], noise, sr, nbefore, dur)
                m.update(meta)
                m.update(dict(method="resort", electrode_id=int(elec),
                              unit_id=int(k), n_clusters_on_elec=n_cl))
                rows.append(m)
        except Exception as e2:  # noqa: BLE001
            rows.append({**meta, "method": "resort", "electrode_id": int(elec),
                         "error": f"{type(e2).__name__}: {e2}"})

        # --- Plexon's own labels, scored under the identical gate ---
        keep = [u for u in np.unique(pu) if u not in PLEXON_DROP_UNITS]
        for u in keep:
            sel = pu == u
            if not sel.any():
                continue
            m = unit_metrics(wf_al[sel], t[sel], noise, sr, nbefore, dur)
            m.update(meta)
            m.update(dict(method="ofs", electrode_id=int(elec),
                          unit_id=int(u), n_clusters_on_elec=len(keep)))
            rows.append(m)

        del wf_al, t, pu

    return pd.DataFrame(rows)


def shard_path(meta: dict) -> Path:
    """Per-combo output shard path, used to make the full run resumable."""
    return SHARD_DIR / f"{meta['date']}_{meta['array']}.parquet"


def process_combo_shard(ofs_path: str, meta: dict) -> str:
    """Run one combo and write its own parquet shard; skip if already done.

    Sharding makes a 332-combo run resumable: an interrupted run keeps every
    completed combo, and re-invoking picks up only what is missing.

    Parameters
    ----------
    ofs_path : str
        Path to the Plexon ``-01`` file.
    meta : dict
        Session metadata.

    Returns
    -------
    str
        Status string: ``skip``, ``ok:<rows>``, or ``err:<message>``.
    """
    out = shard_path(meta)
    if out.exists():
        return "skip"
    try:
        df = process_combo(ofs_path, meta)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out, engine="pyarrow", index=False)
        return f"ok:{len(df)}"
    except Exception as e:  # noqa: BLE001
        return f"err:{type(e).__name__}: {e}"


# === Main ===
def main() -> int:
    """Prototype on one file, or run the full paired cohort."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--single", type=str, default=None,
                    help="Path to one original .nev to prototype on.")
    ap.add_argument("--ofs", type=str, default=None,
                    help="Matching -01.nev; adds a head-to-head OFS comparison.")
    ap.add_argument("--plot", type=str, default=None,
                    help="Save a gate-audit figure (cluster templates, pass vs reject).")
    ap.add_argument("--all", action="store_true", help="Run all paired combos.")
    ap.add_argument("--n-jobs", type=int, default=-1, help="joblib workers.")
    ap.add_argument("--limit", type=int, default=None, help="Cap files (debug).")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    idx = pd.read_parquet(INDEX_IN)

    if args.single:
        p = Path(args.single)
        row = idx[idx["path"] == str(p)]
        meta = meta_from_row(row.iloc[0]) if len(row) else dict(
            date=None, array=None, serial=None, headstage=None, stem=p.stem
        )
        banner(f"Prototype re-sort: {p.stem}")
        t0 = time.perf_counter()
        df = resort_file(p, meta)
        el = time.perf_counter() - t0
        print(f"  runtime            {el:.1f} s")
        print(f"  electrodes sorted  {df['electrode_id'].nunique()}")
        print(f"  candidate clusters {len(df)}")
        print(f"  passing gate       {int(df['pass_gate'].sum())}")
        if len(df):
            print(f"  units/electrode    "
                  f"{df.loc[df['pass_gate']].groupby('electrode_id').size().mean():.2f} (passing)")
            print()
            print("  rejection reasons:")
            rej = df.loc[~df["pass_gate"], "reject_reason"]
            for r, c in rej.value_counts().head(8).items():
                print(f"    {c:5d}  {r}")
            print()
            print("  passing-unit metric summary:")
            g = df[df["pass_gate"]]
            for c in ("snr", "amplitude_uv", "firing_rate_hz",
                      "peak_trough_ms", "isi_viol_rate", "noise_uv"):
                if len(g):
                    print(f"    {c:16s} median={g[c].median():8.3f}  "
                          f"p10={g[c].quantile(.1):8.3f}  p90={g[c].quantile(.9):8.3f}")

        if args.plot:
            plot_gate_audit(p, meta, Path(args.plot))
            print()
            print(f"  gate-audit figure -> {args.plot}")

        if args.ofs:
            banner(f"Head-to-head vs Plexon OFS: {Path(args.ofs).stem}")
            o = ofs_metrics_file(Path(args.ofs), meta)
            n_ofs = len(o)
            n_ofs_pass = int(o["pass_gate"].sum()) if n_ofs else 0
            n_res_pass = int(df["pass_gate"].sum())
            print(f"  OFS units (excl. unsorted/noise) : {n_ofs}")
            print(f"    passing the same gate          : {n_ofs_pass}"
                  f"  ({n_ofs_pass / n_ofs * 100:.0f}%)" if n_ofs else "")
            print(f"    FAILING the gate               : {n_ofs - n_ofs_pass}"
                  f"  <- OFS units our gate would reject")
            print(f"  re-sort units passing gate       : {n_res_pass}")
            print()
            if n_ofs:
                print("  why OFS units fail:")
                for r, c in o.loc[~o["pass_gate"], "reject_reason"].value_counts().head(6).items():
                    print(f"    {c:5d}  {r}")
                print()
                print("  OFS metric summary (all its units):")
                for c in ("snr", "amplitude_uv", "firing_rate_hz", "isi_viol_rate"):
                    print(f"    {c:16s} median={o[c].median():8.3f}  "
                          f"p10={o[c].quantile(.1):8.3f}  p90={o[c].quantile(.9):8.3f}")
                print()
                print(f"  electrodes with >=1 unit:  resort={df.loc[df['pass_gate'],'electrode_id'].nunique()}"
                      f"   ofs={o['electrode_id'].nunique()}   (of 96)")
        return 0

    if not args.all:
        print("nothing to do: pass --single <path> or --all")
        return 1

    from joblib import Parallel, delayed

    combos = idx.groupby(["date", "array"])["kind"].agg(set)
    paired = combos[combos.apply(lambda s: "ORIG" in s and "OFS" in s)].index
    work = []
    for date, array in paired:
        sub = idx[(idx["date"] == date) & (idx["array"] == array)]
        o = sub[sub["kind"] == "ORIG"]
        f = sub[sub["kind"] == "OFS"]
        if len(o) and len(f):
            work.append((o.iloc[0], f.iloc[0]))
    if args.limit:
        work = work[: args.limit]

    banner(f"Full run: {len(work)} paired date-array combos")
    t0 = time.perf_counter()

    # Only the -01 file is read: it carries the same events as the original
    # plus Plexon's labels, so both methods come from one pass over the data.
    SHARD_DIR.mkdir(parents=True, exist_ok=True)
    n_done = sum(1 for o, _ in work if shard_path(meta_from_row(o)).exists())
    if n_done:
        print(f"  resuming: {n_done}/{len(work)} shards already present")

    stats = Parallel(n_jobs=args.n_jobs, verbose=5)(
        delayed(process_combo_shard)(f["path"], meta_from_row(o)) for o, f in work
    )
    n_err = sum(1 for s in stats if s.startswith("err"))
    if n_err:
        print(f"  ERRORS: {n_err} combos failed")
        for s in [s for s in stats if s.startswith("err")][:5]:
            print(f"    {s}")

    shards = sorted(SHARD_DIR.glob("*.parquet"))
    out = pd.concat(
        [pd.read_parquet(s) for s in shards], ignore_index=True
    ) if shards else pd.DataFrame()
    out.to_parquet(UNITS_OUT, engine="pyarrow", index=False)

    el = time.perf_counter() - t0
    print(f"  shards written: {len(shards)}")
    banner("Done")
    print(f"  runtime  {el / 60:.1f} min  ({el / max(1, len(work)):.1f} s/combo)")
    print(f"  wrote    {UNITS_OUT}  ({UNITS_OUT.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"  rows     {len(out)}")
    if "method" in out:
        print(f"  by method: {dict(out['method'].value_counts())}")
    if "pass_gate" in out:
        g = out[out["method"] == "resort"]
        o = out[out["method"] == "ofs"]
        print(f"  resort passing gate: {int(g['pass_gate'].sum())} / {len(g)}")
        print(f"  ofs    passing gate: {int(o['pass_gate'].sum())} / {len(o)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

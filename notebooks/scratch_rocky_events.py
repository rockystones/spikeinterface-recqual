"""Sorting-free event metrics and a forensic census of large-amplitude events.

Two jobs, one pass over the cohort, because both need the raw event stream
rather than the sorted output.

**Layer 1 without a sorter.** CLAUDE.md's first metrics layer is
threshold-crossing statistics that need no sorter at all. On snippet-only data
the NEV *is* the threshold-crossing record: every stored clip is one crossing
of the NSP threshold. So crossing rate, noise floor, amplitude distribution and
peak SNR all fall out of the event stream directly, with no clustering step and
therefore no gate to argue about.

**Large-amplitude events are not all artifacts.** The earlier analysis found
that units above 800 uV are overwhelmingly cross-channel artifacts, but
discarding on amplitude alone would also throw away two real phenomena the
experimenter has observed: very large waveforms confined to a few *neighbouring*
electrodes with an atypical positive-dominant shape (axon-like), and rare
genuinely huge, normally-shaped spikes. Amplitude cannot separate these; the
number of electrodes firing at the same instant can. This script classifies
every large event by its cross-channel coincidence and its waveform polarity
instead of thresholding it away.

Run from repo root:

    uv run python notebooks/scratch_rocky_events.py --single <path-to--01.nev>
    uv run python notebooks/scratch_rocky_events.py --all [--n-jobs 8]

See:
- docs/notes/snippet_noise_floor.md
- docs/notes/giant_events.md
"""

from __future__ import annotations

import argparse
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))

from scratch_rocky_resort import (  # noqa: E402
    baseline_noise_uv,
    meta_from_row,
    open_nev,
    read_electrode,
)
from scratch_rocky_spatial import parse_cmp  # noqa: E402

ROCKY = Path(r"D:\Claude Code\Rocky")
OUT_DIR = REPO / "data" / "derived" / "rocky"
INDEX_IN = OUT_DIR / "session_index.parquet"
ELEC_OUT = OUT_DIR / "events_electrode.parquet"
GIANT_OUT = OUT_DIR / "giant_events.parquet"
ELEC_SHARDS = OUT_DIR / "event_shards"
GIANT_SHARDS = OUT_DIR / "giant_shards"
WF_SHARDS = OUT_DIR / "giant_wf_shards"

CMP_BY_ARRAY = {
    "Anterior": ROCKY / "preimplant" / "SN 1025-001501.cmp",
    "Posterior": ROCKY / "preimplant" / "SN 1025-001497.cmp",
}

# --- Coincidence detection ---
# Bin width for "fired at the same time". Plexon's own artifact-invalidation
# pass on this cohort used 60 ticks (2 ms at 30 kHz) and a 15 % channel
# criterion; 1 ms is the tighter half of that.
#
# Counting *any* coincident event is far too permissive to identify a shared
# waveform. A 361k-event session gives a chance rate of ~2 electrodes per 1 ms
# window, so "fired within 1 ms on 1-4 other electrodes" describes 14 % of all
# events by coincidence alone -- and produces exactly the number of apparently
# spatially-clustered giants that randomness predicts. The discriminating
# quantity is whether the coincident electrode also shows a *large* deflection,
# because that is what a shared physical event actually looks like.
COINC_WIN_MS = 1.0         # artifact test, matching Plexon's own pass
NEAR_WIN_MS = 0.3          # shared-waveform test: a real one is time-locked tighter
BIG_COINC_UV = 100.0       # a coincident event counts only if this large
ARTIFACT_MIN_ELEC = 15     # >= 15 of 96 electrodes = Plexon's 15 % criterion
BIG_ARTIFACT_MIN = 8       # or this many electrodes showing a big deflection
POISSON_TAIL = 1e-9        # chance-coincidence quantile for the adaptive cut
NEAR_GRID_DIST = 1         # Chebyshev grid steps counted as "adjacent" (400 um)
LOCAL_MAX_DIST = 2         # a local cluster may span at most this many steps
LOCAL_MAX_ELEC = 4         # more big-coincident electrodes than this is not local

# --- Large-event census ---
GIANT_UV = 250.0           # candidate threshold on max(|trough|, peak)
GIANT_STORE = 600          # individual rows kept per session; counts kept in full
WF_PER_SESSION = 80        # waveforms saved per session for visual inspection
AXONAL_RATIO = 1.2         # peak / |trough| above which the event is positive-led

# Two non-neural pathologies live in the extreme tail and must be separated
# from it before anything is concluded about large waveforms.
#
#   Rail       -- int16 saturation at 32768 counts x 0.25 uV/count = 8192 uV.
#                 The recorded value is meaningless; the true amplitude is
#                 unknown and larger.
#   Impulse    -- a single sample at several mV followed by a smooth decay,
#                 with no rising phase at all. Observed pinned near 3.8 mV on
#                 specific electrodes across whole months. A spike at 30 kHz
#                 occupies 10-30 samples; one sample is a digital glitch.
RAIL_UV = 8191.0
IMPULSE_MAX_WIDTH = 1      # samples at >= half amplitude for the dominant phase
NON_NEURAL = ("artifact", "impulse", "railed")

# --- Sorting-free amplitude statistics ---
MAD_MULTIPLES = (3.0, 4.0, 5.0)
AMP_TAIL_UV = (100.0, 250.0, 500.0, 1000.0, 2000.0)


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# === Coincidence ===
def coincidence_counts(
    t: np.ndarray, elec: np.ndarray, win_s: float, subset: np.ndarray | None = None
) -> np.ndarray:
    """Count distinct electrodes firing in the same time bin as each event.

    Two-phase binning (offsets 0 and half a bin, taking the maximum) so an event
    landing near a bin edge is not artificially isolated. Exact pairwise window
    queries would be O(n * k) over up to 2.4M events per session; binning is
    O(n log n) and the half-bin offset removes the only failure mode that
    matters here.

    Parameters
    ----------
    t : np.ndarray
        Event times in seconds, any order.
    elec : np.ndarray
        Electrode id per event, 1..96.
    win_s : float
        Bin width in seconds.
    subset : np.ndarray, optional
        Boolean mask. When given, only events inside the mask are *counted*,
        but a count is still returned for every event. This is how the
        "how many electrodes show a big deflection at this instant" feature is
        computed without a second pass.

    Returns
    -------
    np.ndarray
        ``(n,)`` int32 count of distinct qualifying electrodes in the event's
        bin, including the event's own electrode when it qualifies.
    """
    out = np.zeros(len(t), dtype=np.int32)
    e64 = elec.astype(np.int64)
    for offset in (0.0, win_s / 2.0):
        b = np.floor((t + offset) / win_s).astype(np.int64)
        key = b * 128 + e64                        # electrode ids are < 128
        uniq, inv = np.unique(key, return_inverse=True)
        ubin = uniq // 128
        if subset is None:
            contrib = np.ones(len(uniq), dtype=np.int64)
        else:
            # A (bin, electrode) cell counts once if any of its events qualify.
            contrib = np.zeros(len(uniq), dtype=np.int64)
            np.maximum.at(contrib, inv, subset.astype(np.int64))
        bins, first = np.unique(ubin, return_inverse=True)
        per_bin = np.bincount(first, weights=contrib, minlength=len(bins))
        np.maximum(out, per_bin[first][inv].astype(np.int32), out=out)
    return out


def adaptive_artifact_cut(n_events: int, duration_s: float, win_s: float) -> int:
    """Smallest coincident-electrode count that chance cannot explain.

    Under independence the number of other electrodes firing in a window is
    Poisson with mean ``rate * win``. Sessions in this cohort span 14 Hz to
    >1 kHz of pooled event rate, so a fixed count is defensible on some and
    meaningless on others. The returned cut is the larger of Plexon's own 15 %
    channel criterion and the Poisson upper tail.
    """
    from scipy.stats import poisson

    lam = n_events / max(duration_s, 1e-9) * win_s
    return int(max(ARTIFACT_MIN_ELEC - 1, poisson.isf(POISSON_TAIL, lam) + 1))


# === Per-session processing ===
def event_stats_session(
    nev_path: str, meta: dict, geom: dict[int, tuple[int, int]]
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    """Compute sorting-free electrode metrics and classify large events.

    Parameters
    ----------
    nev_path : str
        Path to the Plexon ``-01`` NEV. It carries the same event set as the
        unsorted original (verified), so one read serves both.
    meta : dict
        Session identity carried onto every output row.
    geom : dict
        ``electrode_id -> (col, row)`` from the array's CMP file.

    Returns
    -------
    tuple
        ``(electrode_table, giant_table, giant_waveforms, giant_ids)``.
    """
    raw, nmeta, chan_by_elec = open_nev(Path(nev_path))
    sr, nbefore, dur = nmeta["sr"], nmeta["nbefore"], nmeta["duration_s"]
    win_s = COINC_WIN_MS / 1000.0

    # Per-event arrays, accumulated across electrodes. Only scalars are kept:
    # a 2017 session holds 2.4M events, and retaining the waveforms would cost
    # ~290 MB per worker (the failure mode that exhausted RAM on the first run).
    all_t: list[np.ndarray] = []
    all_e: list[np.ndarray] = []
    all_vmin: list[np.ndarray] = []
    all_vmax: list[np.ndarray] = []
    all_imin: list[np.ndarray] = []
    all_imax: list[np.ndarray] = []
    all_wmin: list[np.ndarray] = []
    all_wmax: list[np.ndarray] = []
    noise_by_elec: dict[int, float] = {}
    # Waveforms are retained only for candidate giants, which are rare.
    giant_wf: list[np.ndarray] = []
    giant_idx: list[np.ndarray] = []   # position in the pooled event arrays

    n_samples = 0
    offset = 0                          # running start of this electrode's block
    for elec in sorted(chan_by_elec):
        e = read_electrode(raw, nmeta, chan_by_elec[elec])
        if e is None or len(e["t"]) == 0:
            continue
        wf, t = e["wf"], e["t"]
        n_samples = wf.shape[1]
        noise_by_elec[elec] = baseline_noise_uv(wf, nbefore)

        imin = wf.argmin(axis=1).astype(np.int8)
        imax = wf.argmax(axis=1).astype(np.int8)
        vmin = wf[np.arange(len(wf)), imin].astype(np.float32)
        vmax = wf[np.arange(len(wf)), imax].astype(np.float32)

        # Width of each phase at half amplitude, in samples. This is what
        # separates a real spike (10-30 samples at 30 kHz) from a single-sample
        # digital impulse, and no amplitude threshold can do it.
        wmin = (wf <= 0.5 * vmin[:, None]).sum(axis=1).astype(np.int8)
        wmax = (wf >= 0.5 * vmax[:, None]).sum(axis=1).astype(np.int8)

        # Candidate giants: polarity-agnostic, because an axon-like event can
        # be positive-dominant and would be missed by a |trough| threshold.
        absamp = np.maximum(np.abs(vmin), vmax)
        gidx = np.flatnonzero(absamp >= GIANT_UV)
        if len(gidx):
            giant_wf.append(wf[gidx].astype(np.float32))
            giant_idx.append(gidx + offset)
        offset += len(t)

        all_t.append(t)
        all_e.append(np.full(len(t), elec, dtype=np.int16))
        all_vmin.append(vmin)
        all_vmax.append(vmax)
        all_imin.append(imin)
        all_imax.append(imax)
        all_wmin.append(wmin)
        all_wmax.append(wmax)
        del e["wf"], wf

    if not all_t:
        return pd.DataFrame(), pd.DataFrame(), np.zeros((0, 0), np.float32), np.zeros(0, np.int64)

    t = np.concatenate(all_t)
    elec = np.concatenate(all_e)
    vmin = np.concatenate(all_vmin)
    vmax = np.concatenate(all_vmax)
    imin = np.concatenate(all_imin)
    imax = np.concatenate(all_imax)
    wmin = np.concatenate(all_wmin)
    wmax = np.concatenate(all_wmax)
    del all_t, all_e, all_vmin, all_vmax, all_imin, all_imax, all_wmin, all_wmax

    absamp_ev = np.maximum(np.abs(vmin), vmax)
    neg_led = np.abs(vmin) >= vmax
    dom_width = np.where(neg_led, wmin, wmax)
    is_railed = (np.abs(vmin) >= RAIL_UV) | (vmax >= RAIL_UV)
    is_impulse = dom_width <= IMPULSE_MAX_WIDTH
    big = absamp_ev >= BIG_COINC_UV

    near_s = NEAR_WIN_MS / 1000.0
    n_coinc = coincidence_counts(t, elec, win_s) - 1               # any event
    n_big_coinc = (coincidence_counts(t, elec, near_s, subset=big)
                   - big.astype(np.int32))                          # large only

    art_cut = adaptive_artifact_cut(len(t), dur, win_s)
    is_artifact = (n_coinc >= art_cut) | (n_big_coinc >= BIG_ARTIFACT_MIN)
    # "Clean" means neural-plausible: not synchronous across the array, not a
    # digital impulse, not railed. All three are removed together because all
    # three inflate the amplitude tail for non-neural reasons.
    is_bad = is_artifact | is_railed | is_impulse

    # Chance level: expected number of *other* electrodes firing in the window
    # under independence, for any event and for a large one. Recorded per
    # session so every coincidence cut below stays auditable against it.
    total_rate = len(t) / max(dur, 1e-9)
    chance = total_rate * win_s
    chance_big = float(big.sum()) / max(dur, 1e-9) * near_s

    # --- sorting-free per-electrode metrics ---
    absamp_all = np.abs(vmin)      # |trough|, comparable with the sorted tables
    rows = []
    for e_id in sorted(noise_by_elec):
        m = elec == e_id
        n_ev = int(m.sum())
        if n_ev == 0:
            continue
        noise = noise_by_elec[e_id]
        a = absamp_all[m]
        clean = a[~is_bad[m]]
        col, row = geom.get(e_id, (np.nan, np.nan))
        rec = dict(
            **meta,
            electrode_id=e_id,
            col=col,
            row=row,
            duration_s=float(dur),
            n_events=n_ev,
            crossing_rate_hz=n_ev / dur,
            noise_uv=noise,
            amp_p50=float(np.percentile(a, 50)),
            amp_p90=float(np.percentile(a, 90)),
            amp_p99=float(np.percentile(a, 99)),
            amp_max=float(a.max()),
            peak_snr=float(np.percentile(a, 99) / noise) if noise > 0 else np.nan,
            n_artifact_events=int(is_artifact[m].sum()),
            frac_artifact=float(is_artifact[m].mean()),
            n_impulse_events=int(is_impulse[m].sum()),
            n_railed_events=int(is_railed[m].sum()),
            n_events_clean=int(len(clean)),
            crossing_rate_clean_hz=len(clean) / dur,
            amp_p99_clean=float(np.percentile(clean, 99)) if len(clean) else np.nan,
            amp_max_clean=float(clean.max()) if len(clean) else np.nan,
            peak_snr_clean=(
                float(np.percentile(clean, 99) / noise)
                if len(clean) and noise > 0 else np.nan
            ),
            chance_coincidence=float(chance),
            chance_coincidence_big=chance_big,
            artifact_cut=int(art_cut),
        )
        # Fraction of crossings that are meaningfully above the noise floor --
        # a sorter-free proxy for "is there anything real on this electrode".
        for k in MAD_MULTIPLES:
            rec[f"frac_ge_{k:g}mad"] = float((a >= k * noise).mean()) if noise > 0 else np.nan
        # Amplitude-tail profile, raw and cleaned. Kept as counts rather than a
        # stored event list so the full tail survives the per-session row cap.
        for uv in AMP_TAIL_UV:
            rec[f"n_ge_{uv:g}uv"] = int((a >= uv).sum())
            rec[f"n_ge_{uv:g}uv_clean"] = int((clean >= uv).sum()) if len(clean) else 0
        rows.append(rec)
    elec_df = pd.DataFrame(rows)

    # --- large-event classification ---
    if giant_idx:
        gsel = np.concatenate(giant_idx)
        gwf = np.concatenate(giant_wf, axis=0)
    else:
        gsel = np.zeros(0, dtype=np.int64)
        gwf = np.zeros((0, max(n_samples, 1)), dtype=np.float32)
    del giant_wf, giant_idx

    # Exact electrode identities are needed only where the vectorised counts
    # already say the event is shared with a handful of electrodes. Everything
    # else -- artifact or fully isolated -- is decided without a window query.
    bo = np.argsort(t[big], kind="stable")
    tb, eb = t[big][bo], elec[big][bo]

    g_elec = elec[gsel].astype(np.int32)
    g_nc, g_nbc = n_coinc[gsel], n_big_coinc[gsel]
    g_vmin, g_vmax = vmin[gsel], vmax[gsel]
    g_imin, g_imax = imin[gsel].astype(np.int16), imax[gsel].astype(np.int16)
    g_pt = (g_imax - g_imin) / sr * 1000.0
    g_noise = np.array([noise_by_elec.get(int(e), np.nan) for e in g_elec])

    # Precedence: a railed or single-sample event is disqualified on shape
    # before any coincidence question is asked, because its amplitude is not a
    # measurement of anything. Only then does cross-channel structure decide.
    klass = np.full(len(gsel), "isolated", dtype=object)
    need_geom = (g_nbc >= 1) & (g_nbc <= LOCAL_MAX_ELEC)
    klass[g_nbc > LOCAL_MAX_ELEC] = "multi_channel"
    klass[need_geom] = "scattered_few"        # upgraded to local_cluster below
    klass[(g_nc >= art_cut) | (g_nbc >= BIG_ARTIFACT_MIN)] = "artifact"
    klass[is_impulse[gsel]] = "impulse"
    klass[is_railed[gsel]] = "railed"

    max_dist = np.full(len(gsel), -1, dtype=np.int16)
    n_near = np.zeros(len(gsel), dtype=np.int16)
    for k in np.flatnonzero(need_geom & (klass == "scattered_few")):
        gi, e_id = gsel[k], int(g_elec[k])
        if e_id not in geom:
            continue
        lo = np.searchsorted(tb, t[gi] - near_s, side="left")
        hi = np.searchsorted(tb, t[gi] + near_s, side="right")
        others = np.unique(eb[lo:hi])
        c0, r0 = geom[e_id]
        d = [max(abs(geom[int(o)][0] - c0), abs(geom[int(o)][1] - r0))
             for o in others if int(o) != e_id and int(o) in geom]
        if d:
            max_dist[k] = int(max(d))
            n_near[k] = int(sum(1 for x in d if x <= NEAR_GRID_DIST))
            if max_dist[k] <= LOCAL_MAX_DIST:
                klass[k] = "local_cluster"

    giant_df = pd.DataFrame({
        **{c: v for c, v in meta.items()},
        "gid": np.arange(len(gsel)),
        "electrode_id": g_elec,
        "t_s": t[gsel],
        "vmin_uv": g_vmin,
        "vmax_uv": g_vmax,
        "abs_amp_uv": absamp_ev[gsel],
        "pos_ratio": np.where(g_vmin != 0, g_vmax / np.abs(g_vmin), np.inf),
        "amp_z": np.where(g_noise > 0, absamp_ev[gsel] / g_noise, np.nan),
        "noise_uv": g_noise,
        "imin": g_imin,
        "imax": g_imax,
        "pt_ms": g_pt,
        "width_min": wmin[gsel].astype(np.int16),
        "width_max": wmax[gsel].astype(np.int16),
        "n_coincident": g_nc,
        "n_big_coincident": g_nbc,
        "n_coinc_near": n_near,
        "max_grid_dist": max_dist,
        "klass": klass.astype(str),
        "axonal_like": g_vmax > AXONAL_RATIO * np.abs(g_vmin),
        "regular_shape": ((np.abs(g_vmin) >= g_vmax) & (g_pt >= 0.15)
                          & (g_pt <= 1.20) & (np.abs(g_imin - nbefore) <= 3)
                          & (wmin[gsel] > IMPULSE_MAX_WIDTH)),
        "chance_coincidence": chance,
        "chance_coincidence_big": chance_big,
        "artifact_cut": art_cut,
    }) if len(gsel) else pd.DataFrame()

    # Per-electrode giant counts by class, folded into the electrode table so
    # the full census survives even though only a sample of rows is stored.
    if len(giant_df) and len(elec_df):
        wide = (giant_df.pivot_table(index="electrode_id", columns="klass",
                                     values="gid", aggfunc="size")
                .add_prefix("n_giant_"))
        wide["n_giant_total"] = wide.sum(axis=1)
        for flag in ("axonal_like", "regular_shape"):
            wide[f"n_giant_{flag}"] = (
                giant_df[giant_df[flag]].groupby("electrode_id").size()
            )
        elec_df = elec_df.merge(wide.reset_index(), on="electrode_id", how="left")
        for c in [c for c in elec_df.columns if c.startswith("n_giant_")]:
            elec_df[c] = elec_df[c].fillna(0).astype(int)

    # Individual rows are sampled: artifacts are numerous and interchangeable,
    # while the non-artifact giants are the point of the exercise.
    wf_ids = np.arange(len(giant_df), dtype=np.int64)
    if len(giant_df) > GIANT_STORE:
        non_art = giant_df[~giant_df["klass"].isin(NON_NEURAL)]
        art = giant_df[giant_df["klass"].isin(NON_NEURAL)]
        keep = np.concatenate([
            non_art.nlargest(GIANT_STORE - GIANT_STORE // 6, "abs_amp_uv")["gid"].to_numpy(),
            art.nlargest(GIANT_STORE // 6, "abs_amp_uv")["gid"].to_numpy(),
        ])
        giant_df = giant_df[giant_df["gid"].isin(keep)].reset_index(drop=True)
        sel = np.isin(wf_ids, keep)
        gwf, wf_ids = gwf[sel], wf_ids[sel]

    # Waveforms: the most extreme non-artifact events, plus artifacts for contrast.
    if len(giant_df):
        non_art = giant_df[~giant_df["klass"].isin(NON_NEURAL)]
        art = giant_df[giant_df["klass"].isin(NON_NEURAL)]
        keep = np.concatenate([
            non_art.nlargest(WF_PER_SESSION, "abs_amp_uv")["gid"].to_numpy(),
            art.nlargest(WF_PER_SESSION // 4, "abs_amp_uv")["gid"].to_numpy(),
        ])
        sel = np.isin(wf_ids, keep)
        gwf, wf_ids = gwf[sel], wf_ids[sel]

    return elec_df, giant_df, gwf, wf_ids


def shard_paths(meta: dict) -> tuple[Path, Path, Path]:
    """Per-combo output paths, which make the full run resumable."""
    stem = f"{meta['date']}_{meta['array']}"
    return (ELEC_SHARDS / f"{stem}.parquet",
            GIANT_SHARDS / f"{stem}.parquet",
            WF_SHARDS / f"{stem}.npz")


def process_session_shard(nev_path: str, meta: dict, geom: dict) -> str:
    """Run one session and write its shards; skip if already present."""
    pe, pg, pw = shard_paths(meta)
    if pe.exists() and pg.exists():
        return "skip"
    try:
        ed, gd, wf, wid = event_stats_session(nev_path, meta, geom)
        for p in (pe, pg, pw):
            p.parent.mkdir(parents=True, exist_ok=True)
        ed.to_parquet(pe, engine="pyarrow", index=False)
        gd.to_parquet(pg, engine="pyarrow", index=False)
        np.savez_compressed(pw, wf=wf, gid=wid)
        return f"ok:{len(ed)}/{len(gd)}"
    except Exception as exc:  # noqa: BLE001
        return f"err:{type(exc).__name__}: {exc}"


def load_geometry() -> dict[str, dict[int, tuple[int, int]]]:
    """``array -> {electrode_id: (col, row)}`` from the two CMP files."""
    out = {}
    for arr, path in CMP_BY_ARRAY.items():
        cmp_df = parse_cmp(path)
        out[arr] = {
            int(r["electrode_id"]): (int(r["col"]), int(r["row"]))
            for _, r in cmp_df.iterrows()
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--single", type=str, default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--n-jobs", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    idx = pd.read_parquet(INDEX_IN)
    geom_by_array = load_geometry()

    if args.single:
        p = Path(args.single)
        row = idx[idx["path"] == str(p)]
        meta = meta_from_row(row.iloc[0]) if len(row) else dict(
            date=None, array="Anterior", serial=None, headstage=None, stem=p.stem
        )
        banner(f"Event pass: {p.stem}")
        t0 = time.perf_counter()
        ed, gd, wf, _ = event_stats_session(
            str(p), meta, geom_by_array.get(meta["array"], {})
        )
        print(f"  runtime           {time.perf_counter() - t0:.1f} s")
        print(f"  electrodes        {len(ed)}")
        print(f"  events            {int(ed['n_events'].sum()):,}")
        print(f"  chance coincid.   any {ed['chance_coincidence'].iloc[0]:.3f}"
              f"  large {ed['chance_coincidence_big'].iloc[0]:.4f} electrodes/window")
        print(f"  artifact cut      >= {int(ed['artifact_cut'].iloc[0])} coincident electrodes")
        print(f"  crossing rate     median {ed['crossing_rate_hz'].median():.2f} Hz")
        print(f"  noise floor       median {ed['noise_uv'].median():.2f} uV")
        print(f"  peak SNR (p99)    median {ed['peak_snr'].median():.2f}")
        print(f"  artifact fraction median {ed['frac_artifact'].median():.4f}")
        print(f"  giant candidates  {len(gd)}")
        if len(gd):
            print()
            print("  giant classes (full census, per electrode table):")
            for c in [c for c in ed.columns if c.startswith("n_giant_")]:
                print(f"    {int(ed[c].sum()):7,}  {c[8:]}")
            nz = gd[~gd["klass"].isin(NON_NEURAL)]
            print(f"\n  stored rows {len(gd)}   neural-plausible {len(nz)}"
                  f"   axon-like {int(nz['axonal_like'].sum())}"
                  f"   regular {int(nz['regular_shape'].sum())}")
            top = nz.nlargest(6, "abs_amp_uv")
            print("\n  largest non-artifact events:")
            for _, r in top.iterrows():
                print(f"    elec {r['electrode_id']:3.0f}  {r['abs_amp_uv']:8.1f} uV"
                      f"  z={r['amp_z']:6.1f}  big-coinc={r['n_big_coincident']:2.0f}"
                      f"  dist={r['max_grid_dist']:2.0f}  {r['klass']:14s}"
                      f"  {'AXON' if r['axonal_like'] else ''}"
                      f"{'REG' if r['regular_shape'] else ''}")
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
        o, f = sub[sub["kind"] == "ORIG"], sub[sub["kind"] == "OFS"]
        if len(o) and len(f):
            work.append((o.iloc[0], f.iloc[0]))
    if args.limit:
        work = work[: args.limit]

    banner(f"Event pass over {len(work)} paired combos")
    t0 = time.perf_counter()
    stats = Parallel(n_jobs=args.n_jobs, verbose=5)(
        delayed(process_session_shard)(
            f["path"], meta_from_row(o), geom_by_array.get(o["array"], {})
        )
        for o, f in work
    )
    errs = [s for s in stats if s.startswith("err")]
    if errs:
        print(f"  ERRORS: {len(errs)}")
        for s in errs[:5]:
            print(f"    {s}")

    ed = pd.concat(
        [pd.read_parquet(p) for p in sorted(ELEC_SHARDS.glob("*.parquet"))],
        ignore_index=True,
    )
    gd = pd.concat(
        [pd.read_parquet(p) for p in sorted(GIANT_SHARDS.glob("*.parquet"))],
        ignore_index=True,
    )
    ed.to_parquet(ELEC_OUT, engine="pyarrow", index=False)
    gd.to_parquet(GIANT_OUT, engine="pyarrow", index=False)

    banner("Done")
    print(f"  runtime {(time.perf_counter() - t0) / 60:.1f} min")
    print(f"  electrode rows {len(ed):,}  -> {ELEC_OUT.name}")
    print(f"  giant rows     {len(gd):,}  -> {GIANT_OUT.name}")
    if len(gd):
        print()
        for k, c in gd["klass"].value_counts().items():
            print(f"    {c:8,}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

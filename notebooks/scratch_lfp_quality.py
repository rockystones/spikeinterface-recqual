"""The LFP layer: line noise, band power, and how correlated the array is.

CLAUDE.md says LFP is in scope and must be handled alongside spikes rather than
as an afterthought. Nothing had touched it. Fisk carries `.ns3` for all 140
sessions and the TDT corpus carries `pNe` for all 370 blocks, so the data has
been sitting there since the corpus was assembled.

Three quantities, chosen because they say something about the *recording* that
the spike layer cannot:

- **60 Hz line power, as a fraction of total.** Mains contamination is an
  acquisition fault, not a property of the tissue, and it is invisible to a
  spike-band pipeline that high-passes at 300 Hz. A session with a loose
  ground shows here and nowhere else.
- **Band power** (delta through gamma) per channel, normalised, so a shift in
  the spectrum is separable from a change in overall amplitude.
- **Median cross-channel correlation.** An array whose channels are shorted,
  bridged, or riding a common reference shows near-unity correlation in the
  LFP band. A healthy array shows moderate correlation from volume conduction.
  This is the closest thing in the corpus to a direct test for a hardware
  fault, and it has no spike-layer equivalent.

Scaling is checked, not assumed -- the third format in this project where NEO's
units needed verifying. Blackrock `.ns3` carries its gain and comes out in µV;
TDT `pNe` is **int16 ADC counts with no recorded scale**
([[tdt_corpus]]), so its amplitudes are reported in counts and only the
*ratios* -- line fraction, band fractions, correlation -- are comparable across
the two.

Run from repo root:

    uv run python notebooks/scratch_lfp_quality.py [--jobs 2] [--subject Fisk]

Writes `data/derived/lfp/lfp_quality.parquet`.

See:
- docs/notes/lfp_quality.md
"""

from __future__ import annotations

import argparse
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_cohort_io import PROBE_DIR  # noqa: E402
from scratch_ns5_resort import summarise_error  # noqa: E402

OUT_DIR = REPO / "data" / "derived" / "lfp"
OUT = OUT_DIR / "lfp_quality.parquet"
FISK_SESS = REPO / "data" / "derived" / "fisk" / "fisk_sessions.parquet"

# Seconds analysed. LFP is slow and stationary; 60 s at 2 kHz is ample for a
# spectrum and keeps the pass cheap.
SLICE_S = 60.0
# Mains, and the half-width used to integrate around it.
LINE_HZ = 60.0
LINE_HALFWIDTH_HZ = 1.5
BANDS = {"delta": (1, 4), "theta": (4, 8), "alpha": (8, 13),
         "beta": (13, 30), "gamma": (30, 80)}

# Derived-LFP parameters. The low corner sits above the widest band measured
# (gamma, 80 Hz) with room to spare, so the anti-alias filter is doing the
# whole job and the naive decimation below cannot fold anything back in.
LFP_BAND_HZ = (0.5, 250.0)
LFP_TARGET_HZ = 1000.0
# Broadband read granularity. A 30 kHz x 96 ch float32 chunk of this length is
# ~115 MB, so two workers stay well inside the memory envelope; the decimated
# result is 1/30 of it.
CHUNK_S = 30.0
# Filter settling context per chunk. SI's default 5 ms is sized for a 300 Hz
# spike-band corner; a 0.5 Hz high-pass has a ~0.32 s time constant, so a chunk
# boundary without enough context carries a transient into the spectrum.
# Measured on a pure 10 Hz tone, chunked-vs-one-shot error against margin:
#   3 s -> 6.7e-3,  6 s -> 3.4e-4,  10 s -> 5.8e-6,  20 s -> 1.7e-7
# 10 s is where it stops mattering; the cost is a 50 s parent read per 30 s
# of output.
FILTER_MARGIN_MS = 10000.0
# CLAUDE.md: drop anything shorter than this at the IO layer.
MIN_SEGMENT_S = 5.0
# One row per session, so a scoped re-run cannot overwrite the rest.
SHARD_DIR = OUT_DIR / "shards"


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === One session ===
def nsx_filter(path: str, nsx_id: int) -> dict:
    """The stream's own filter corners, from the nsX extended header.

    **Do not assume a stream carries LFP because of its suffix.** Blackrock
    stores corner frequencies in *millihertz*, and Fisk's `.ns3` reports
    `hi_freq_corner = 300000` -- a 300 Hz high-pass -- with a 1000 Hz low-pass.
    That is a spike-band stream sampled at 2 kHz, not LFP, and it contains
    0.2% of its power below 80 Hz. Computing band power from it produces
    numbers that look like data and mean nothing.
    """
    from neo.rawio import BlackrockRawIO

    # load_nev=False: NEO refuses to parse when the .nev and .nsX disagree on
    # segment count, which is true of 28 Rocky sessions whose nsX headers are
    # perfectly readable. The band lives entirely in the nsX extended header,
    # so the .nev is not needed and its consistency check only gets in the way.
    raw = BlackrockRawIO(filename=str(Path(path).with_suffix("")),
                         nsx_to_load=nsx_id, load_nev=False)
    raw.parse_header()
    h = raw._nsx_ext_header[nsx_id][0]
    hp = float(h["hi_freq_corner"]) / 1000.0
    lp = float(h["lo_freq_corner"]) / 1000.0
    return dict(hp_corner_hz=hp, lp_corner_hz=lp,
                # An LFP stream passes the low frequencies. Anything cornered
                # above 30 Hz has removed the band this layer is about.
                is_lfp=hp <= 30.0)


def pick_segment(rec, min_s: float = MIN_SEGMENT_S) -> int:
    """Longest segment at least `min_s` long, chosen explicitly.

    CLAUDE.md forbids defaulting to `segment_index=0`: Blackrock NSPs write a
    brief record-verification segment before the real recording, and on those
    files segment 0 is the artefact rather than the data.
    """
    fs = rec.get_sampling_frequency()
    lens = [rec.get_num_frames(segment_index=i) / fs
            for i in range(rec.get_num_segments())]
    keep = [i for i, L in enumerate(lens) if L >= min_s]
    if not keep:
        raise ValueError(f"no segment >= {min_s:g} s (longest {max(lens):.2f})")
    return max(keep, key=lambda i: lens[i])


def broadband_to_lfp(rec):
    """Band-pass and decimate a 30 kHz broadband stream down to ~1 kHz.

    `bandpass_filter` wraps the recording in a lazy `BandpassFilterRecording`
    -- nothing is read until `get_traces` is called, and each chunk is filtered
    with a margin of context so a chunked read matches a whole-file read.
    `decimate` then wraps that in a `DecimateRecording`, which is plain array
    slicing (`traces[offset::factor]`) and does **no** anti-aliasing of its
    own. That is safe only because the band-pass above already removed
    everything over 250 Hz, well under the 500 Hz Nyquist of the output.

    The alternative is `resample`, which SI's own `decimate` docstring points
    to as the safe choice. It is rejected here for two reasons: it is
    FFT-based, so it wants a whole segment in memory at once -- 96 channels of
    30 kHz broadband -- and the anti-alias filter this layer needs is a filter
    it would have to apply anyway. Filtering first makes the aliasing argument
    explicit rather than delegating it.

    Returns the decimated recording and its true sampling rate; the rate is
    `parent / round(parent / target)`, not the target, because the decimation
    factor is an integer.
    """
    from spikeinterface.preprocessing import bandpass_filter, decimate

    fs = rec.get_sampling_frequency()
    factor = max(1, int(round(fs / LFP_TARGET_HZ)))
    lo, hi = LFP_BAND_HZ
    # The low-pass is the anti-alias filter; assert rather than trust it.
    assert hi < (fs / factor) / 2, "band-pass corner above the output Nyquist"
    filtered = bandpass_filter(rec, freq_min=lo, freq_max=hi,
                               margin_ms=FILTER_MARGIN_MS)
    return decimate(filtered, decimation_factor=factor), fs / factor


def read_lfp_traces(rec, seg: int, seconds: float) -> np.ndarray:
    """Pull `seconds` of a decimated recording in chunks, as float64 uV.

    Chunking bounds the *parent* read: one call for the whole slice would make
    `BandpassFilterRecording` materialise 60 s of 30 kHz broadband at once.
    """
    fs = rec.get_sampling_frequency()
    want = min(rec.get_num_frames(segment_index=seg), int(seconds * fs))
    step = max(1, int(CHUNK_S * fs))
    parts = []
    for a in range(0, want, step):
        b = min(a + step, want)
        parts.append(np.asarray(
            rec.get_traces(segment_index=seg, start_frame=a, end_frame=b,
                           return_scaled=True), dtype=np.float64))
    return np.concatenate(parts, axis=0) if parts else np.empty((0, 0))


def lfp_metrics(job: dict) -> dict:
    """Line contamination, band power and channel correlation for one file."""
    base = {k: v for k, v in job.items() if k not in ("path", "cmp")}
    try:
        import spikeinterface.extractors as se

        # The guard fails CLOSED. It was written to skip on a header error,
        # and that let 28 Rocky sessions through whose .ns5 is high-passed at
        # 250 Hz -- the layer computed delta and gamma fractions from a stream
        # with 0.0000 of its power below 250 Hz, and they looked like data.
        # An unreadable band is a reason to refuse, not a reason to proceed.
        try:
            filt = nsx_filter(job["path"], int(job["stream"]))
        except Exception as exc:  # noqa: BLE001
            return dict(**base, error=f"band unknown: {summarise_error(exc)}")
        base.update(filt)
        if not filt["is_lfp"]:
            return dict(**base, error=(
                f"no LFP in this stream: high-pass at "
                f"{filt['hp_corner_hz']:.0f} Hz"))

        rec = se.read_blackrock(file_path=job["path"], stream_id=job["stream"])
        seg = pick_segment(rec)
        if job.get("source") == "broadband":
            base["parent_sr"] = float(rec.get_sampling_frequency())
            rec, fs = broadband_to_lfp(rec)
        else:
            fs = rec.get_sampling_frequency()
        # return_scaled: Blackrock carries a real gain, so this is uV.
        x = read_lfp_traces(rec, seg, SLICE_S)
        if x.ndim != 2 or x.shape[0] < int(fs * 5):
            return dict(**base, error="too short")
        n = x.shape[0]

        # Welch per channel. nperseg of 4 s gives 0.25 Hz resolution, enough to
        # separate the 60 Hz line from the gamma band around it.
        nper = int(min(4 * fs, x.shape[0]))
        f, pxx = signal.welch(x, fs=fs, nperseg=nper, axis=0)
        total = np.trapezoid(pxx, f, axis=0)
        total = np.where(total <= 0, np.nan, total)

        line = (f >= LINE_HZ - LINE_HALFWIDTH_HZ) & \
               (f <= LINE_HZ + LINE_HALFWIDTH_HZ)
        line_frac = (np.trapezoid(pxx[line], f[line], axis=0) / total
                     if line.any() else np.full(x.shape[1], np.nan))

        out = {}
        for name, (lo, hi) in BANDS.items():
            m = (f >= lo) & (f < hi)
            if not m.any() or hi > fs / 2:
                out[f"{name}_frac"] = np.nan
                continue
            out[f"{name}_frac"] = float(np.nanmedian(
                np.trapezoid(pxx[m], f[m], axis=0) / total))

        # Cross-channel correlation on the LFP itself. A shorted or bridged
        # array approaches 1; volume conduction alone leaves it moderate.
        c = np.corrcoef(x, rowvar=False)
        iu = np.triu_indices(c.shape[0], k=1)
        cc = c[iu]
        cc = cc[np.isfinite(cc)]

        return dict(
            **base, segment_index=int(seg),
            sr=float(fs), duration_s=float(n / fs),
            n_channels=int(x.shape[1]),
            rms_uv=float(np.nanmedian(np.std(x, axis=0))),
            line_frac_med=float(np.nanmedian(line_frac)),
            line_frac_p90=float(np.nanpercentile(line_frac, 90)),
            corr_med=float(np.median(cc)) if cc.size else np.nan,
            corr_p90=float(np.percentile(cc, 90)) if cc.size else np.nan,
            **out,
        )
    except Exception as exc:  # noqa: BLE001
        return dict(**base, error=summarise_error(exc))


def broadband_worklist(subject: str = "") -> list[dict]:
    """Every `.ns5` / `.ns6` the sorter layer already knows how to find.

    Reuses `scratch_ns5_resort.build_worklist` rather than rediscovering the
    corpus: it already resolves the two inventory shapes, the second drop's
    absolute paths, and Fisk's `.ns6` (which the merged inventory never
    indexed). Anything it can sort, this can derive LFP from.
    """
    from scratch_ns5_resort import INV
    from scratch_ns5_resort import build_worklist as ns5_worklist

    jobs: list[dict] = []
    for j in ns5_worklist(pd.read_parquet(INV)):
        if subject and j["subject"] != subject:
            continue
        path = Path(j["ns5"])
        jobs.append(dict(
            subject=j["subject"], array=j["array"], serial=j.get("serial", ""),
            session=j["stem"], date=str(j["date"]), path=str(path),
            # nsX stream ids follow the suffix: .ns5 -> "5", .ns6 -> "6"
            stream=path.suffix[-1], source="broadband"))
    return jobs


def ns3_worklist(subject: str = "") -> list[dict]:
    """Fisk's `.ns3`, one per session folder.

    Kept for the record rather than for results: on this corpus every one of
    these is cornered at 300 Hz and `lfp_metrics` rejects it. See
    docs/notes/lfp_quality.md.
    """
    jobs: list[dict] = []
    if subject in ("", "Fisk") and FISK_SESS.exists():
        sess = pd.read_parquet(FISK_SESS)
        for r in sess[sess.has_lfp].itertuples():
            ns3 = sorted(Path(r.path).glob("*.ns3"))
            if not ns3:
                continue
            jobs.append(dict(
                subject="Fisk", array=r.array, serial=r.serial,
                session=r.session, date=str(pd.Timestamp(r.date).date()),
                path=str(ns3[0]), stream="3", source="ns3",
            ))
    return jobs


def build_worklist(subject: str = "", source: str = "broadband") -> list[dict]:
    """Sessions to measure, from whichever stream the caller asked for."""
    if source == "ns3":
        return ns3_worklist(subject)
    if source == "both":
        return broadband_worklist(subject) + ns3_worklist(subject)
    return broadband_worklist(subject)


def shard_name(j: dict) -> str:
    """Filesystem-safe identity for one session x source."""
    stem = f"{j['subject']}__{j.get('source', 'broadband')}__{j['session']}"
    return "".join(c if c.isalnum() or c in "_-." else "_" for c in stem)


def collect_shards() -> pd.DataFrame:
    files = sorted(SHARD_DIR.glob("*.parquet"))
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def report(d: pd.DataFrame) -> None:
    ok = d[d.get("error").isna()] if "error" in d else d
    banner("1. Coverage")
    print(f"  sessions: {len(ok)} of {len(d)}")
    if len(d) > len(ok):
        print(d[d.error.notna()].error.astype(str).str.slice(0, 60)
              .value_counts().head(3).to_string())
    if not len(ok):
        return
    print(ok.groupby(["subject", "array"]).agg(
        n=("session", "size"), first=("date", "min"), last=("date", "max"),
        sr=("sr", "median"), rms=("rms_uv", "median")).round(1).to_string())

    banner("2. Mains contamination, which the spike layer cannot see")
    print("  60 Hz power as a fraction of total LFP power. A 300 Hz highpass")
    print("  removes this entirely, so a grounding fault is invisible")
    print("  downstream.\n")
    print(ok.groupby(["subject", "array"]).line_frac_med.describe()
          [["50%", "75%", "max"]].round(4).to_string())
    hi = ok[ok.line_frac_med > 0.05]
    print(f"\n  sessions above 5% line power: {len(hi)} of {len(ok)}")
    if len(hi):
        print(hi.nlargest(min(8, len(hi)), "line_frac_med")
              [["array", "date", "line_frac_med", "rms_uv"]]
              .round(4).to_string(index=False))

    banner("3. Cross-channel correlation")
    print("  A shorted or bridged array approaches 1. Volume conduction alone")
    print("  leaves it moderate. This has no spike-layer equivalent.\n")
    print(ok.groupby(["subject", "array"]).corr_med.describe()
          [["min", "50%", "max"]].round(3).to_string())

    banner("4. Band composition")
    cols = [f"{b}_frac" for b in BANDS if f"{b}_frac" in ok]
    if cols:
        print(ok.groupby(["subject", "array"])[cols].median().round(3)
              .to_string())

    banner("5. Longitudinal")
    from scipy.stats import spearmanr
    for (s, a), g in ok.groupby(["subject", "array"]):
        if len(g) < 10:
            continue
        x = pd.to_datetime(g.date).map(pd.Timestamp.toordinal)
        print(f"  {s}/{a}  n={len(g)}")
        for m in ("rms_uv", "line_frac_med", "corr_med", "gamma_frac"):
            if m not in g:
                continue
            v = g.dropna(subset=[m])
            if len(v) < 10:
                continue
            r, p = spearmanr(pd.to_datetime(v.date)
                             .map(pd.Timestamp.toordinal), v[m])
            print(f"    {m:16s} rho {r:+.3f}  p={p:.3g}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--subject", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--source", default="broadband",
                    choices=["broadband", "ns3", "both"])
    ap.add_argument("--redo", action="store_true",
                    help="recompute sessions that already have a shard")
    args = ap.parse_args()

    jobs = build_worklist(args.subject, args.source)
    SHARD_DIR.mkdir(parents=True, exist_ok=True)
    if not args.redo:
        done = {f.stem for f in SHARD_DIR.glob("*.parquet")}
        jobs = [j for j in jobs if shard_name(j) not in done]
    if args.limit:
        jobs = jobs[:args.limit]
    banner("LFP quality layer")
    print(f"  sessions: {len(jobs)}")

    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for i, r in enumerate(ex.map(lfp_metrics, jobs, chunksize=1), 1):
            pd.DataFrame([r]).to_parquet(
                SHARD_DIR / f"{shard_name(r)}.parquet", index=False)
            if i % 20 == 0:
                print(f"    {i}/{len(jobs)}", flush=True)

    # Rebuilt from the shards on disk, never from this run's own frames: a
    # scoped re-run that wrote its own results over the corpus summary has
    # cost this project real data three times (docs/notes/sorter_operations).
    d = collect_shards()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, engine="pyarrow", index=False)
    report(d)
    print(f"\n  wrote {OUT}  ({len(d)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""The sorting-free layer on Rocky's broadband, across 431 sessions.

Every previous sorting-free number for Rocky came from NEV snippets, because
that was all there was. The second drop supplies `.ns5` for 431 of those same
sessions spanning 2017-2023, so the layer can be recomputed the way
[[threshold_crossing]] defines it -- from the continuous trace, with the noise
floor measured rather than inferred from pre-trigger windows.

That matters for two questions at once:

- **Longitudinal.** The snippet noise estimator is biased ~1.1-1.3x high and
  its bias depends on activity ([[snippet_noise_floor]]). On this corpus the
  true floor is available, so Rocky's decline can be re-measured without it.
- **Equipment.** 121 sessions have a same-day analog/digital headstage pair
  with broadband on both sides. S12b could only compare crossing counts the
  NSP had already thresholded; here both members are re-detected identically,
  which removes the acquisition threshold from the comparison entirely.

Detection follows the project's contract exactly: 300 Hz highpass,
`get_noise_levels(method="mad")`, `detect_peaks(method="by_channel")` at
`k * MAD` with a 1 ms refractory. The noise levels handed to the detector are
in **raw** units while those reported are in µV, because `by_channel` compares
against raw traces -- the units gotcha documented in [[threshold_crossing]].

Run from repo root:

    uv run python notebooks/scratch_rocky_ns5_free.py [--jobs 3] [--slice 180]

Writes `data/derived/rocky_ns5/free/<stem>.parquet` shards and
`data/derived/rocky_ns5/ns5_free.parquet`.

See:
- docs/notes/threshold_crossing.md
- docs/notes/snippet_noise_floor.md
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_cohort_io import PROBE_DIR  # noqa: E402
from scratch_ns5_resort import (  # noqa: E402
    FILTER_FREQ_HZ,
    FILTER_ORDER,
    summarise_error,
)

INV = REPO / "data" / "derived" / "newdrop_inventory.parquet"
OUT_DIR = REPO / "data" / "derived" / "rocky_ns5"
SHARD_DIR = OUT_DIR / "free"
SUMMARY = OUT_DIR / "ns5_free.parquet"

# Detection threshold in units of the channel's own MAD. 4 is the project's
# working value; the NSP's own online threshold sits near here too, which is
# what makes the re-detected count comparable with the NEV crossing count.
DETECT_K = 4.0
# Biological absolute refractory, and the window over which a local minimum
# must be the largest. See threshold_crossing.md.
REFRACTORY_MS = 1.0
# Seconds analysed. Bounds a 431-session pass and matches the slice every
# other layer in this project uses.
SLICE_S = 180.0


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === One session ===
def session_free(job: dict) -> dict:
    """Continuous threshold-crossing metrics for one .ns5.

    Column names match `scratch_headstage_free.free_metrics` and
    `scratch_tdt_free.block_metrics` so all three corpora stack in one table,
    with `source="ns5"` marking that these came from a real trace rather than
    from snippet pre-trigger windows.
    """
    base = {k: v for k, v in job.items() if k not in ("ns5", "cmp")}
    try:
        from spikeinterface.core import get_noise_levels
        from spikeinterface.preprocessing import highpass_filter
        from spikeinterface.sortingcomponents.peak_detection import detect_peaks

        from scratch_ns5_resort import open_recording

        rec, info = open_recording(Path(job["ns5"]), Path(job["cmp"]))
        fs = rec.get_sampling_frequency()
        n = min(rec.get_num_frames(), int(job["slice_s"] * fs))
        rec = rec.frame_slice(0, n)
        rec_f = highpass_filter(rec, freq_min=FILTER_FREQ_HZ,
                                filter_order=FILTER_ORDER)
        dur = n / fs

        # Two noise estimates of the same thing in different units. The
        # detector compares against RAW traces, so it must be handed raw
        # levels; everything reported is in uV. Passing the uV levels to the
        # detector would scale the threshold by the gain and detect nothing.
        noise_uv = np.asarray(get_noise_levels(
            rec_f, method="mad", return_scaled=True, force_recompute=True))
        noise_raw = np.asarray(get_noise_levels(
            rec_f, method="mad", return_scaled=False, force_recompute=True))

        peaks = detect_peaks(
            rec_f, method="by_channel", peak_sign="neg",
            detect_threshold=DETECT_K, exclude_sweep_ms=REFRACTORY_MS,
            noise_levels=noise_raw, progress_bar=False)
        ch = peaks["channel_index"]
        # nanmedian, not median: a single dead channel with zero raw noise
        # puts one NaN in this ratio, and `np.median` propagates it to the
        # gain, which makes every amplitude in the session NaN. Six Fisk
        # sessions lost their amplitudes that way while reporting 300-550k
        # perfectly good crossings.
        gain = float(np.nanmedian(noise_uv / np.where(noise_raw == 0, np.nan,
                                                      noise_raw)))
        amp_uv = np.abs(peaks["amplitude"].astype(float)) * gain

        n_ch = rec_f.get_num_channels()
        counts = np.bincount(ch, minlength=n_ch)
        active = counts > 0
        per_ch_snr = []
        for c in np.flatnonzero(active):
            a = amp_uv[ch == c]
            if noise_uv[c] > 0:
                per_ch_snr.append(float(np.median(a) / noise_uv[c]))

        return dict(
            **base, source="ns5", duration_s=float(dur), sr=float(fs),
            n_electrodes=int(n_ch),
            noise_med=float(np.median(noise_uv)),
            noise_p90=float(np.percentile(noise_uv, 90)),
            n_crossings=int(len(ch)),
            crossing_rate_hz=float(len(ch) / dur / max(active.sum(), 1)),
            amp_p50=float(np.percentile(amp_uv, 50)) if len(amp_uv) else np.nan,
            amp_p90=float(np.percentile(amp_uv, 90)) if len(amp_uv) else np.nan,
            amp_p99=float(np.percentile(amp_uv, 99)) if len(amp_uv) else np.nan,
            amp_max=float(amp_uv.max()) if len(amp_uv) else np.nan,
            peak_snr_med=float(np.median(per_ch_snr)) if per_ch_snr else np.nan,
            n_elec_active=int(active.sum()),
            frac_elec_active=float(active.sum() / n_ch),
            detect_k=DETECT_K,
        )
    except Exception as exc:  # noqa: BLE001
        return dict(**base, source="ns5", error=summarise_error(exc))


# %%
# === Worklist ===
def build_worklist(slice_s: float) -> list[dict]:
    """Every broadband file with a registered mapfile.

    Rocky's is `.ns5` and Fisk's `.ns6` -- the suffix is the NSP sampling group
    rather than a version -- so both are collected here and `open_recording`
    resolves the stream id from the file itself.
    """
    # keyed by (subject, implant, array): Rocky carries two implants whose
    # arrays reuse the Anterior/Posterior labels, so a (subject, array) key
    # lets I2 silently overwrite I1 -- the bug that mislabelled 431 I1
    # sessions with I2 serials (see docs/notes/serial_resolution.md)
    serial: dict[tuple[str, str, str], str] = {}
    for cfg in sorted((REPO / "configs" / "subjects").glob("*.json")):
        reg = json.loads(cfg.read_text(encoding="utf-8"))
        for im in reg.get("implants", []):
            for arr, sn in (im.get("arrays") or {}).items():
                if sn:
                    serial[(reg["subject"], im["implant"], arr)] = sn

    inv = pd.read_parquet(INV)
    ns5 = inv[(inv.role == "broadband") & inv.date.notna()]
    jobs: list[dict] = []
    for r in ns5.itertuples():
        sn = serial.get((r.subject, r.implant, r.array))
        if not sn:
            continue
        hits = sorted(PROBE_DIR.glob(f"*{sn}*.cmp"))
        if not hits:
            continue
        jobs.append(dict(
            stem=r.stem, subject=r.subject, implant=r.implant, array=r.array,
            date=str(pd.Timestamp(r.date).date()),
            headstage=r.headstage or "unlabelled",
            ns5=r.path, cmp=str(hits[0]), serial=sn, slice_s=slice_s,
        ))
    jobs.extend(fisk_jobs(serial, slice_s))
    return jobs


def fisk_jobs(serial: dict, slice_s: float) -> list[dict]:
    """Fisk's `.ns6` sessions, which live in per-session folders.

    Fisk is not in the file-level inventories: its recordings sit one session
    per directory under `<array>/Recordings/`, so they are enumerated from the
    session table `scratch_fisk_impedance.py` builds instead.
    """
    sess_path = REPO / "data" / "derived" / "fisk" / "fisk_sessions.parquet"
    if not sess_path.exists():
        return []
    sess = pd.read_parquet(sess_path)
    out: list[dict] = []
    for r in sess[sess.has_broadband].itertuples():
        hits = sorted(PROBE_DIR.glob(f"*{r.serial}*.cmp"))
        if not hits:
            continue
        ns6 = sorted(Path(r.path).glob("*.ns6"))
        if not ns6:
            continue
        out.append(dict(
            stem=r.session, subject="Fisk", implant="I1", array=r.array,
            date=str(pd.Timestamp(r.date).date()),
            headstage="unlabelled", ns5=str(ns6[0]), cmp=str(hits[0]),
            serial=r.serial, slice_s=slice_s,
        ))
    return out


def stratified(jobs: list[dict], n: int) -> list[dict]:
    """Spread over array, headstage and date rather than take a head."""
    if not n or n >= len(jobs):
        return jobs
    df = pd.DataFrame(jobs).sort_values(["array", "headstage", "date"])
    out: list[dict] = []
    for _, g in df.groupby(["array", "headstage"]):
        k = max(1, round(n * len(g) / len(df)))
        idx = np.linspace(0, len(g) - 1, min(k, len(g))).round().astype(int)
        out += g.iloc[idx].to_dict("records")
    return out[:n]


def report(d: pd.DataFrame) -> None:
    ok = d[d.get("error").isna()] if "error" in d else d
    banner("1. Sessions scored")
    print(f"  rows: {len(d)}   failed: {len(d) - len(ok)}")
    if len(d) > len(ok):
        print(d[d.error.notna()].error.value_counts().head(5).to_string())
    if not len(ok):
        return
    print(ok.groupby(["array", "headstage"]).agg(
        n=("stem", "size"), first=("date", "min"), last=("date", "max"),
        noise=("noise_med", "median"), amp=("amp_p50", "median"),
        snr=("peak_snr_med", "median"),
        rate=("crossing_rate_hz", "median")).round(2).to_string())

    banner("2. Headstage, on same-day pairs, re-detected identically")
    print("  Both members thresholded at the same k*MAD from the trace, so")
    print("  the NSP's own acquisition threshold is out of the comparison.\n")
    piv = ok.pivot_table(index=["array", "date"], columns="headstage",
                         values=["noise_med", "amp_p50", "peak_snr_med",
                                 "crossing_rate_hz"])
    for metric in ("noise_med", "amp_p50", "peak_snr_med",
                   "crossing_rate_hz"):
        if (metric, "Analog") not in piv or (metric, "Digital") not in piv:
            continue
        a = piv[(metric, "Analog")]
        dg = piv[(metric, "Digital")]
        m = a.notna() & dg.notna()
        if m.sum() < 8:
            continue
        from scipy.stats import wilcoxon
        try:
            _, p = wilcoxon(a[m], dg[m])
        except ValueError:
            p = np.nan
        print(f"  {metric:18s} analog {a[m].median():8.2f}  "
              f"digital {dg[m].median():8.2f}  "
              f"ratio {a[m].median() / dg[m].median():5.2f}  "
              f"p={p:.2g}  n={int(m.sum())}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--slice", type=float, default=SLICE_S)
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--subject", default="")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    jobs = build_worklist(args.slice)
    if args.subject:
        jobs = [j for j in jobs if j["subject"] == args.subject]
    if args.sample:
        jobs = stratified(jobs, args.sample)
    if args.limit:
        jobs = jobs[:args.limit]
    banner("Rocky broadband -- sorting-free layer")
    print(f"  sessions: {len(jobs)}   slice {args.slice:.0f}s   "
          f"k={DETECT_K}")
    SHARD_DIR.mkdir(parents=True, exist_ok=True)

    from concurrent.futures import ProcessPoolExecutor
    todo = [j for j in jobs
            if not (SHARD_DIR / f"{j['stem']}.parquet").exists()]
    print(f"  already cached: {len(jobs) - len(todo)}")
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for i, row in enumerate(ex.map(session_free, todo, chunksize=1), 1):
            pd.DataFrame([row]).to_parquet(
                SHARD_DIR / f"{row['stem']}.parquet", engine="pyarrow",
                index=False)
            if i % 10 == 0:
                print(f"    {i}/{len(todo)}", flush=True)

    shards = sorted(SHARD_DIR.glob("*.parquet"))
    d = pd.concat([pd.read_parquet(s) for s in shards], ignore_index=True)
    d.to_parquet(SUMMARY, engine="pyarrow", index=False)
    report(d)
    print(f"\n  wrote {SUMMARY}  ({len(d)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""S11: re-detect from continuous data, and see what the NSP threshold cost.

Every comparison in S09 and S10 sits on the NEV's threshold crossings, which
are fixed at acquisition and common-mode to every variant. Nothing in those
sessions can see the detection threshold itself -- and that threshold is the
largest suspected confound in the Rocky series, because it changed between
recording eras.

This is the only regime where detection varies. Three sorters run on the `.ns5`
broadband and produce their own event sets, so comparisons here need spike
matching and are approximate where S09's were exact.

Sorter pool follows CLAUDE.md: MountainSort5 (scheme 2), Tridesclous2,
SpykingCircus2. **Kilosort4 is not installed in this environment** (no GPU
stack), so the pool is three of the policy's four; that is reported rather than
quietly dropped.

Scope: CLAUDE.md says end-to-end on one demo session before scaling, and to
iterate on short slices. This runs a stratified handful and writes per-session
shards so the full 67-session set can resume.

Run from repo root:

    uv run python notebooks/scratch_ns5_resort.py --limit 4
    uv run python notebooks/scratch_ns5_resort.py --limit 0      # everything

See:
- docs/notes/ns5_plan.md
- docs/notes/measurement_floor.md
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from _paths import MONKEY_ROOT  # noqa: E402
from scratch_cohort_io import parse_cmp  # noqa: E402

INV = REPO / "data" / "derived" / "monkey_inventory.parquet"
PROBE_DIR = REPO / "configs" / "probes"
OUT_DIR = REPO / "data" / "derived" / "ns5"
SHARD_DIR = OUT_DIR / "shards"
SUMMARY_OUT = OUT_DIR / "ns5_sorters.parquet"

# CLAUDE.md sorter policy. KS4 is absent from this environment; the run reports
# what it actually had rather than what the policy names.
SORTER_PARAMS: dict[str, dict] = {
    "mountainsort5": dict(scheme="2"),
    "tridesclous2": {},
    "spykingcircus2": {},
}

PITCH_UM = 400.0            # Utah inter-electrode spacing, blackrockneurotech.com
FILTER_FREQ_HZ = 300.0      # docs/notes/spike_band_filter.md
FILTER_ORDER = 3
MIN_SEGMENT_S = 5.0         # docs/notes/segment_handling.md
MATCH_MS = 1.0              # tolerance when matching re-detected to NEV events


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === Recording construction ===
def build_probe(cmp_df: pd.DataFrame):
    """A probeinterface Probe from the array's own mapfile.

    Geometry from the CMP, never hardcoded, and `contact_ids` are channel-id
    strings because that is what `rec.channel_ids` exposes for Blackrock.
    """
    from probeinterface import Probe

    pos = np.array([[r.col * PITCH_UM, r.row * PITCH_UM]
                    for r in cmp_df.itertuples()], dtype=float)
    probe = Probe(ndim=2, si_units="um")
    probe.set_contacts(positions=pos, shapes="circle",
                       shape_params={"radius": 20.0},
                       contact_ids=[str(int(c)) for c in cmp_df.channel_id])
    probe.annotate(name=f"Utah-{len(cmp_df)}", manufacturer="blackrock")
    return probe


def open_recording(ns5: Path, cmp_path: Path):
    """Load one .ns5, attach its probe, and pick the segment to analyse.

    Returns (recording, info). Segments shorter than MIN_SEGMENT_S are dropped
    per the project's segment policy -- they are operator record-verification
    artefacts. `segment_index` is never defaulted: the chosen index is returned
    so the caller records which one it analysed.
    """
    from spikeinterface.extractors import read_blackrock

    # stream_id resolved, not assumed: Fisk has no .ns5 at all and other
    # subjects expose several streams from one file.
    rec = None
    last = None
    for sid in ("5", "ns5", None):
        try:
            rec = (read_blackrock(file_path=str(ns5), stream_id=sid)
                   if sid else read_blackrock(file_path=str(ns5)))
            break
        except Exception as exc:  # noqa: BLE001
            last = exc
    if rec is None:
        raise RuntimeError(f"read_blackrock failed: {last}")

    cmp_df = parse_cmp(cmp_path)
    probe = build_probe(cmp_df)
    ids = [str(c) for c in rec.channel_ids]
    index_by_id = {cid: i for i, cid in enumerate(ids)}
    contact_ids = [str(int(c)) for c in cmp_df.channel_id]
    missing = [c for c in contact_ids if c not in index_by_id]
    if missing:
        raise RuntimeError(f"{len(missing)} mapfile channels absent from the "
                           f"recording, e.g. {missing[:4]}")
    probe.set_device_channel_indices(
        np.array([index_by_id[c] for c in contact_ids], dtype=int))
    rec = rec.set_probe(probe, group_mode="by_probe")

    sr = rec.get_sampling_frequency()
    lengths = [rec.get_num_samples(segment_index=s) / sr
               for s in range(rec.get_num_segments())]
    keep = [i for i, d in enumerate(lengths) if d >= MIN_SEGMENT_S]
    if not keep:
        raise RuntimeError(f"no segment >= {MIN_SEGMENT_S}s; got {lengths}")
    seg = int(max(keep, key=lambda i: lengths[i]))
    info = dict(sr=float(sr), n_channels=int(rec.get_num_channels()),
                n_segments=int(rec.get_num_segments()),
                segment_index=seg, duration_s=float(lengths[seg]),
                dropped_segments=len(lengths) - len(keep))
    return rec.select_segments([seg]), info


# %%
# === NEV reference events ===
def nev_event_times(nev: Path) -> dict[int, np.ndarray]:
    """Threshold-crossing times per channel from the NEV, in seconds."""
    from scratch_monkey_variants import read_packets

    ts, eid, _ = read_packets(nev)
    # NEV timestamps are in clock ticks; the resolution lives in the header.
    import struct
    head = nev.open("rb").read(24)
    res = struct.unpack("<I", head[20:24])[0] or 30000
    out: dict[int, np.ndarray] = {}
    for e in np.unique(eid):
        out[int(e)] = np.sort(ts[eid == e].astype(np.float64) / res)
    return out


def match_rate(a: np.ndarray, b: np.ndarray, tol_s: float) -> float:
    """Fraction of `a` with a partner in `b` within tol. Not symmetric."""
    if not len(a) or not len(b):
        return np.nan
    idx = np.searchsorted(b, a)
    left = np.clip(idx - 1, 0, len(b) - 1)
    right = np.clip(idx, 0, len(b) - 1)
    d = np.minimum(np.abs(b[left] - a), np.abs(b[right] - a))
    return float((d <= tol_s).mean())


# %%
# === One session ===
def run_session(job: dict, sorters: list[str]) -> pd.DataFrame:
    """Every sorter on one recording, plus the NEV comparison."""
    from spikeinterface.preprocessing import highpass_filter
    from spikeinterface.sorters import run_sorter

    rows: list[dict] = []
    base = {k: v for k, v in job.items() if k not in ("ns5", "nev", "cmp")}
    try:
        rec, info = open_recording(Path(job["ns5"]), Path(job["cmp"]))
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame([{**base, "sorter": "load",
                              "error": f"{type(exc).__name__}: {exc}"[:150]}])
    base.update(info)
    rec_f = highpass_filter(rec, freq_min=FILTER_FREQ_HZ,
                            filter_order=FILTER_ORDER)

    nev_times = {}
    if job.get("nev") and Path(job["nev"]).exists():
        try:
            nev_times = nev_event_times(Path(job["nev"]))
        except Exception:  # noqa: BLE001
            nev_times = {}
    nev_total = sum(len(v) for v in nev_times.values())
    base["nev_events"] = nev_total

    for name in sorters:
        folder = (OUT_DIR / "work" / f"{job['stem']}__{name}")
        t0 = time.perf_counter()
        try:
            sorting = run_sorter(
                sorter_name=name, recording=rec_f, folder=str(folder),
                remove_existing_folder=True, verbose=False,
                **SORTER_PARAMS.get(name, {}))
        except Exception as exc:  # noqa: BLE001
            rows.append({**base, "sorter": name,
                         "error": f"{type(exc).__name__}: {exc}"[:150],
                         "seconds": round(time.perf_counter() - t0, 1)})
            continue
        sr = rec_f.get_sampling_frequency()
        spikes = {u: sorting.get_unit_spike_train(u, segment_index=0) / sr
                  for u in sorting.unit_ids}
        n_spikes = sum(len(v) for v in spikes.values())
        allt = np.sort(np.concatenate(list(spikes.values()))) if spikes else \
            np.array([])
        nev_all = (np.sort(np.concatenate(list(nev_times.values())))
                   if nev_times else np.array([]))
        rows.append({
            **base, "sorter": name, "error": None,
            "seconds": round(time.perf_counter() - t0, 1),
            "n_units": int(len(sorting.unit_ids)),
            "n_spikes": int(n_spikes),
            "rate_hz": n_spikes / base["duration_s"] if base["duration_s"] else np.nan,
            # Asymmetric on purpose: "what fraction of the NSP's events did the
            # sorter also find" and "what fraction of the sorter's events did
            # the NSP see" answer different questions, and the second is the
            # one that measures what the online threshold discarded.
            "frac_nev_recovered": match_rate(nev_all, allt, MATCH_MS / 1000),
            "frac_sorter_in_nev": match_rate(allt, nev_all, MATCH_MS / 1000),
        })
    return pd.DataFrame(rows)


def build_worklist(inv: pd.DataFrame) -> list[dict]:
    """Recordings that have both an .ns5 and a registered mapfile."""
    import json

    serial: dict[tuple[str, str], str] = {}
    for cfg in sorted((REPO / "configs" / "subjects").glob("*.json")):
        reg = json.loads(cfg.read_text(encoding="utf-8"))
        for im in reg.get("implants", []):
            for arr, sn in (im.get("arrays") or {}).items():
                if sn:
                    serial[(reg["subject"], arr)] = sn

    ns5 = inv[inv.role == "broadband"]
    nev_by_stem = {(r.subject, r.stem): MONKEY_ROOT / r.rel
                   for r in inv[(inv.role == "snippets")
                                & (inv.chain == "-01")].itertuples()}
    jobs = []
    for r in ns5.itertuples():
        sn = serial.get((r.subject, r.array))
        if not sn:
            continue
        hits = sorted(PROBE_DIR.glob(f"*{sn}*.cmp"))
        if not hits:
            continue
        jobs.append(dict(stem=r.stem, subject=r.subject, implant=r.implant,
                         array=r.array,
                         date=r.date.date() if pd.notna(r.date) else None,
                         ns5=str(MONKEY_ROOT / r.rel), cmp=str(hits[0]),
                         nev=str(nev_by_stem.get((r.subject, r.stem), "")),
                         serial=sn))
    return jobs


def stratified(jobs: list[dict], limit: int) -> list[dict]:
    """Spread the subset over subject, array and time rather than take a head."""
    if not limit or limit >= len(jobs):
        return jobs
    df = pd.DataFrame(jobs).sort_values(["subject", "array", "date"])
    out = []
    for _, g in df.groupby(["subject", "array"]):
        k = max(1, round(limit * len(g) / len(df)))
        idx = np.linspace(0, len(g) - 1, min(k, len(g))).round().astype(int)
        out += g.iloc[idx].to_dict("records")
    return out[:limit]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=4,
                    help="sessions to run (0 = all)")
    ap.add_argument("--sorters", default=",".join(SORTER_PARAMS))
    args = ap.parse_args()

    from spikeinterface.sorters import installed_sorters
    wanted = [s.strip() for s in args.sorters.split(",") if s.strip()]
    have = set(installed_sorters())
    sorters = [s for s in wanted if s in have]
    missing = [s for s in wanted if s not in have]

    inv = pd.read_parquet(INV)
    jobs = stratified(build_worklist(inv), args.limit)

    banner("S11 -- re-detection from continuous data")
    print(f"  sessions with .ns5 and a registered mapfile: "
          f"{len(build_worklist(inv))}")
    print(f"  running: {len(jobs)}")
    print(f"  sorters: {sorters}")
    if missing:
        print(f"  NOT INSTALLED, so absent from this comparison: {missing}")
        print("    CLAUDE.md's pool names Kilosort4; this environment has no")
        print("    GPU stack for it. The result is a 3-sorter consensus.")
    print()
    for j in jobs:
        print(f"    {j['subject']:6s} {j['array']:10s} {j['date']}  {j['stem'][:44]}")

    SHARD_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    for i, j in enumerate(jobs, 1):
        shard = SHARD_DIR / f"{j['subject']}_{j['stem']}.parquet"
        if shard.exists():
            frames.append(pd.read_parquet(shard))
            print(f"  [{i}/{len(jobs)}] cached  {j['stem'][:50]}")
            continue
        print(f"  [{i}/{len(jobs)}] {j['stem'][:50]} ...", flush=True)
        try:
            df = run_session(j, sorters)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            continue
        df.to_parquet(shard, engine="pyarrow", index=False)
        frames.append(df)
        for r in df.itertuples():
            if getattr(r, "error", None):
                print(f"        {r.sorter:16s} ERROR {r.error[:70]}")
            else:
                print(f"        {r.sorter:16s} {r.n_units:4d} units  "
                      f"{r.n_spikes:8d} spikes  {r.seconds:6.1f}s  "
                      f"nev_recovered={r.frac_nev_recovered:.2f}")

    if not frames:
        print("\n  nothing ran")
        return 1
    out = pd.concat(frames, ignore_index=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(SUMMARY_OUT, engine="pyarrow", index=False)

    ok = out[out.error.isna()]
    if len(ok):
        banner("Per-sorter summary")
        print(ok.groupby("sorter").agg(
            n=("n_units", "size"), units_med=("n_units", "median"),
            spikes_med=("n_spikes", "median"),
            nev_recovered=("frac_nev_recovered", "median"),
            in_nev=("frac_sorter_in_nev", "median"),
            secs_med=("seconds", "median")).round(3).to_string())
        print("\n  nev_recovered: fraction of the NSP's threshold crossings the")
        print("  sorter also found. in_nev: fraction of the sorter's spikes the")
        print("  NSP saw -- below 1 means the online threshold discarded them.")
    bad = out[out.error.notna()]
    if len(bad):
        banner("Failures")
        print(bad[["subject", "stem", "sorter", "error"]].to_string(index=False))
    print(f"\n  wrote {SUMMARY_OUT.relative_to(REPO)}  ({len(out)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

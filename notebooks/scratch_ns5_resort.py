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
SpykingCircus2, Kilosort4 with ``do_correction=False``.

**Containers are the default**, as SpikeInterface recommends: sorters pin
conflicting dependency versions and one environment cannot satisfy all of them,
and an image also pins the sorter version for a later re-run. ``--docker auto``
(the default) containerises anything that needs it and runs natively only where
a container buys nothing -- the SI-internal sorters, whose version is the
already-pinned SI version, and mountainsort5, which has no conflicting pins.
``--docker always`` containerises everything; ``--docker never`` still
containerises Kilosort4, which has no native install here.

Scope: CLAUDE.md says end-to-end on one demo session before scaling, and to
iterate on short slices. This runs a stratified handful and writes per-session
shards so the full 67-session set can resume.

Run from repo root:

    uv run python notebooks/scratch_ns5_resort.py --limit 4
    uv run python notebooks/scratch_ns5_resort.py --limit 0            # all
    uv run python notebooks/scratch_ns5_resort.py --docker always

See:
- docs/notes/ns5_plan.md
- docs/notes/measurement_floor.md
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import traceback
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# SpikeInterface 0.102.3 still calls `np.in1d`, which NumPy removed in 2.0
# (deprecated 1.25). Under numpy 2.4 both tridesclous2 and spykingcircus2 die
# partway through clustering with `module 'numpy' has no attribute 'in1d'`.
#
# `np.in1d(a, b)` and `np.isin(a, b)` differ only in that in1d flattens its
# first argument; both SI call sites pass 1-D arrays -- `peak_labels` in
# clustering/merge.py:135 and a `flatnonzero` result in clustering/tools.py:90
# -- so the substitution is exact. tools.py:88 already uses `isin`, so this is
# a migration SI started and did not finish.
if not hasattr(np, "in1d"):
    # setattr, not `np.in1d = ...`: ruff's NPY201 rightly flags the direct
    # assignment as a use of the removed API. Restoring it for a dependency is
    # the one legitimate reason to name it.
    setattr(np, "in1d", np.isin)  # noqa: B010

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from _paths import MONKEY_ROOT  # noqa: E402
from scratch_cohort_io import parse_cmp  # noqa: E402

INV = REPO / "data" / "derived" / "monkey_inventory.parquet"
PROBE_DIR = REPO / "configs" / "probes"
OUT_DIR = REPO / "data" / "derived" / "ns5"
SHARD_DIR = OUT_DIR / "shards"
SUMMARY_OUT = OUT_DIR / "ns5_sorters.parquet"

# CLAUDE.md's sorter policy, in full.
#
# `do_correction=False` is policy, not a default: drift correction is not
# effective at a site pitch above 40 um, which excludes every probe in this
# project (Pachitariu et al., Nat Methods 2024).
SORTER_PARAMS: dict[str, dict] = {
    "mountainsort5": dict(scheme="2"),
    "tridesclous2": {},
    "spykingcircus2": {},
    "kilosort4": dict(do_correction=False),
}

# **Containers are the default**, per SpikeInterface's own recommendation and
# the owner's instruction: sorters pin conflicting dependency versions, and one
# environment cannot satisfy all of them. Running each in its own image also
# pins the sorter version, which a comparison meant to be re-run later needs.
#
# The exceptions are the SI-internal sorters. `tridesclous2` and
# `spykingcircus2` are implemented inside spikeinterface itself, so their
# "version" is the SI version already pinned in pyproject.toml and a container
# buys nothing. `mountainsort5` is a pure-Python package with no conflicting
# pins. Kilosort4 is the opposite case -- torch plus CUDA, no native install
# here -- and only ever runs containerised.
PREFER_NATIVE = ("tridesclous2", "spykingcircus2", "mountainsort5")
REQUIRES_DOCKER = ("kilosort4",)

PITCH_UM = 400.0            # Utah inter-electrode spacing, blackrockneurotech.com
FILTER_FREQ_HZ = 300.0      # docs/notes/spike_band_filter.md
FILTER_ORDER = 3
MIN_SEGMENT_S = 5.0         # docs/notes/segment_handling.md
MATCH_MS = 1.0              # tolerance when matching re-detected to NEV events
# Largest negative excursion divided by the noise MAD, over a 20 s window.
# A good session runs ~9; a session with no neural signal runs ~4.7. 6 sits
# between the two observed populations -- see `signal_check`.
MIN_PEAK_TO_NOISE = 6.0


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


def summarise_error(exc: BaseException) -> str:
    r"""The last useful line of an exception, not its first 150 characters.

    SpikeInterface wraps a sorter failure in a SpikeSortingError whose text
    opens with a remote traceback, so truncating the front yields
    ``Traceback (most recent call last): File "C:\Users\sh`` and hides the
    actual cause -- which cost a whole run to diagnose. Take the last
    exception-looking line instead.
    """
    text = f"{type(exc).__name__}: {exc}"
    # The wrapped trace arrives with literal backslash-n, not real newlines.
    flat = text.replace("\\n", "\n")
    lines = [ln.strip() for ln in flat.splitlines() if ln.strip()]
    cause = next((ln for ln in reversed(lines)
                  if "Error" in ln or "Exception" in ln), "")
    return (f"{type(exc).__name__} | {cause}" if cause else text)[:300]


def fresh_folder(folder: Path) -> Path:
    """A writable output folder, working around Windows file locking.

    `run_sorter(remove_existing_folder=True)` raises `WinError 32 -- the process
    cannot access the file because it is being used by another process` when a
    previous run left a memmap or worker handle open on the binary it wrote.
    That killed two of six sorter runs on the first attempt. Try to clear the
    folder; if the OS still holds it, sidestep to a numbered sibling rather
    than lose the run.
    """
    import shutil

    if not folder.exists():
        return folder
    try:
        shutil.rmtree(folder)
        return folder
    except (OSError, PermissionError):
        for i in range(1, 100):
            alt = folder.with_name(f"{folder.name}__{i}")
            if not alt.exists():
                return alt
    return folder


def signal_check(rec, seconds: float = 20.0) -> dict:
    """Is there anything spike-like in this recording at all?

    Found the hard way. `Nigel_Anterior_2023-01-24` has a 96-channel 30 kHz
    `.ns5` whose largest negative excursion over 30 s is **4.7x** the noise MAD
    -- pure noise, no action potentials -- while its `.nev` carries 66,795
    threshold crossings. A known-good session from the same animal gives 8.8x
    and a median excursion of -124 uV against this file's -22 uV. It also has
    only one segment where every good session has the documented 2.4 s
    false-start plus the real recording.

    **Owner-confirmed 2026-08-16: that session is a global connection failure**
    -- every channel at once, not an array or an electrode. Which is why its
    noise floor is *below* the cohort's rather than above it: a disconnected
    input is quieter than tissue.

    Without this check a sorter returns zero units, which is indistinguishable
    in a results table from an array that has genuinely died -- and worse,
    SpykingCircus2 returns 54 *units* on this session rather than zero, so a
    table without the diagnostic would show a healthy-looking sort of nothing.

    Returns the diagnostic numbers and `has_signal`; the caller decides.
    """
    sr = rec.get_sampling_frequency()
    n = rec.get_num_samples()
    start = int(min(5 * sr, max(0, n - seconds * sr)))
    end = int(min(start + seconds * sr, n))
    tr = rec.get_traces(start_frame=start, end_frame=end, return_scaled=True)
    mad = np.median(np.abs(tr - np.median(tr, axis=0)), axis=0) * 1.4826
    mad[mad == 0] = np.nan
    ratio = float(np.nanmedian(tr.min(axis=0) / -mad))
    return dict(noise_mad_uv=float(np.nanmedian(mad)),
                min_excursion_uv=float(np.median(tr.min(axis=0))),
                peak_to_noise=ratio,
                has_signal=bool(ratio >= MIN_PEAK_TO_NOISE))


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
def wants_docker(name: str, mode: str) -> bool:
    """Whether this sorter runs in its container.

    ``mode`` is "auto" (the default), "always" or "never". Auto containerises
    everything except the SI-internal sorters, whose version is the SI version
    already pinned, and mountainsort5, which has no conflicting dependencies.
    """
    if name in REQUIRES_DOCKER:
        return True
    if mode == "always":
        return True
    if mode == "never":
        return False
    return name not in PREFER_NATIVE


def sorter_kwargs(name: str, use_docker: bool) -> dict:
    """Params for one sorter, plus the container settings if it needs one."""
    kw = dict(SORTER_PARAMS.get(name, {}))
    if use_docker:
        kw["docker_image"] = True
        # The sorter images ship the sorter, not SpikeInterface, so SI installs
        # itself into the container at runtime. `auto` resolves to "github" for
        # a non-editable install, which failed here with `ModuleNotFoundError:
        # No module named 'spikeinterface'`. `pypi` installs the released
        # version, which is the one pinned in pyproject.toml -- so the container
        # runs the same SI as the host rather than main.
        kw["installation_mode"] = "pypi"
    return kw


def _sorter_child(ns5: str, cmp_path: str, name: str, use_docker: bool,
                  folder: str) -> None:
    """Child entry point: run one sorter and leave the result on disk.

    Deliberately rebuilds the recording from paths rather than receiving it
    pickled -- a lazy SI recording carries a preprocessing chain that is
    awkward to send across a spawn boundary, and re-reading a header is cheap.
    """
    from spikeinterface.preprocessing import highpass_filter
    from spikeinterface.sorters import run_sorter

    rec, _ = open_recording(Path(ns5), Path(cmp_path))
    rec_f = highpass_filter(rec, freq_min=FILTER_FREQ_HZ,
                            filter_order=FILTER_ORDER)
    run_sorter(sorter_name=name, recording=rec_f, folder=folder,
               remove_existing_folder=False, verbose=False,
               **sorter_kwargs(name, use_docker))


def run_sorter_guarded(job: dict, name: str, use_docker: bool, rec_f,
                       timeout_s: float):
    """Run one sorter in a killable child. Returns (sorting or None, error).

    Written after a run sat for **31 hours** on a single sorter. Tridesclous2
    hit `WinError 1455 -- the paging file is too small`, its worker pool
    deadlocked waiting on shared memory that never arrived, and nothing
    upstream noticed: the parent had no timeout, so the whole 67-session job
    was blocked by one call with no output and no error.

    A thread cannot be killed and `ProcessPoolExecutor` will not terminate a
    worker mid-task, so this uses a bare `multiprocessing.Process` and
    `terminate()`. `run_sorter` persists its output, so the parent reloads from
    the folder rather than needing a value back across the boundary.
    """
    import multiprocessing as mp

    from spikeinterface.sorters import read_sorter_folder

    folder = fresh_folder(OUT_DIR / "work" / f"{job['stem']}__{name}")
    ctx = mp.get_context("spawn")          # Windows has no fork
    p = ctx.Process(target=_sorter_child,
                    args=(job["ns5"], job["cmp"], name, use_docker,
                          str(folder)))
    p.start()
    p.join(timeout_s)
    if p.is_alive():
        p.terminate()
        p.join(15)
        if p.is_alive():
            p.kill()
        return None, f"TIMEOUT after {timeout_s:.0f}s (child killed)"
    if p.exitcode != 0:
        return None, f"child exited {p.exitcode}; see {folder.name}"
    try:
        return read_sorter_folder(folder), None
    except Exception as exc:  # noqa: BLE001
        return None, summarise_error(exc)


def run_session(job: dict, sorters: list[str], docker_mode: str = "auto",
                timeout_s: float = 3600.0) -> pd.DataFrame:
    """Every sorter on one recording, plus the NEV comparison."""
    from spikeinterface.preprocessing import highpass_filter

    rows: list[dict] = []
    base = {k: v for k, v in job.items() if k not in ("ns5", "nev", "cmp")}
    try:
        rec, info = open_recording(Path(job["ns5"]), Path(job["cmp"]))
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame([{**base, "sorter": "load",
                              "error": summarise_error(exc)}])
    base.update(info)
    rec_f = highpass_filter(rec, freq_min=FILTER_FREQ_HZ,
                            filter_order=FILTER_ORDER)

    # Pre-flight, recorded on every row rather than used to skip. Screening all
    # 67 sessions showed the flag catches two different things that must not be
    # merged: `Nigel_Anterior_2023-01-24` has an abnormally quiet 4.6 uV floor
    # against a cohort median of 8.6-9.1, which is a file that is not a neural
    # recording; the three late-2024 Nigel Posterior sessions have an entirely
    # normal 8.5-11.9 uV floor and simply no spikes, which is an array that has
    # stopped yielding. A sorter returning zero units is the right answer for
    # the second and a meaningless one for the first, so both run and the
    # diagnostic travels with the result.
    base.update(signal_check(rec_f))

    nev_times = {}
    if job.get("nev") and Path(job["nev"]).exists():
        try:
            nev_times = nev_event_times(Path(job["nev"]))
        except Exception:  # noqa: BLE001
            nev_times = {}
    nev_total = sum(len(v) for v in nev_times.values())
    base["nev_events"] = nev_total

    for name in sorters:
        t0 = time.perf_counter()
        use_docker = wants_docker(name, docker_mode)
        sorting, err = run_sorter_guarded(job, name, use_docker, rec_f, timeout_s)
        if sorting is None:
            rows.append({**base, "sorter": name, "docker": use_docker,
                         "error": err,
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
            **base, "sorter": name, "docker": use_docker, "error": None,
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


class SingleRun:
    """Refuse to start while another run of this script is alive.

    Two overlapping runs is what exhausted the Windows commit charge and
    produced `WinError 1455 -- the paging file is too small`, which then
    deadlocked a worker pool for 31 hours. Sorters are memory-hungry enough
    that one at a time is the only safe policy on this machine.
    """

    def __init__(self, path: Path):
        self.path = path

    def __enter__(self):
        if self.path.exists():
            try:
                pid = int(self.path.read_text())
            except (OSError, ValueError):
                pid = None
            if pid is not None and _pid_alive(pid):
                raise SystemExit(
                    f"another run is active (pid {pid}); refusing to start a "
                    f"second one. Remove {self.path} if that is wrong.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(str(os.getpid()))
        return self

    def __exit__(self, *exc):
        self.path.unlink(missing_ok=True)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=4,
                    help="sessions to run (0 = all)")
    ap.add_argument("--sorters", default=None,
                    help="comma-separated; default depends on --docker")
    ap.add_argument("--timeout", type=float, default=3600.0,
                    help="seconds before a single sorter is killed")
    ap.add_argument("--docker", choices=("auto", "always", "never"),
                    default="auto",
                    help="containerise: auto (default) uses images except for "
                         "SI-internal sorters and mountainsort5")
    args = ap.parse_args()

    from spikeinterface.sorters import installed_sorters

    # Without a container the pool is whatever imports; with one it is whatever
    # has an image. Kilosort4 only ever appears in the second case here.
    wanted = ([s.strip() for s in args.sorters.split(",") if s.strip()]
              if args.sorters else list(SORTER_PARAMS))
    have = set(installed_sorters())
    # A sorter is runnable if it imports natively OR will be containerised.
    sorters = [s for s in wanted
               if s in have or wants_docker(s, args.docker)]
    missing = [s for s in wanted if s not in sorters]

    lock = SingleRun(OUT_DIR / ".running.pid")
    lock.__enter__()

    inv = pd.read_parquet(INV)
    jobs = stratified(build_worklist(inv), args.limit)

    banner("S11 -- re-detection from continuous data")
    print(f"  per-sorter timeout: {args.timeout:.0f}s")
    print(f"  sessions with .ns5 and a registered mapfile: "
          f"{len(build_worklist(inv))}")
    print(f"  running: {len(jobs)}")
    print(f"  sorters: {sorters}")
    print(f"  docker mode: {args.docker}")
    for s_ in sorters:
        how = "docker" if wants_docker(s_, args.docker) else "native"
        print(f"      {s_:16s} {how}")
    if missing:
        print(f"  UNAVAILABLE, absent from this comparison: {missing}")
    print()
    for j in jobs:
        print(f"    {j['subject']:6s} {j['array']:10s} {j['date']}  {j['stem'][:44]}")

    SHARD_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    for i, j in enumerate(jobs, 1):
        shard = SHARD_DIR / f"{j['subject']}_{j['stem']}.parquet"
        if shard.exists():
            prev = pd.read_parquet(shard)
            # Only a shard that actually produced a sorting counts as done.
            # Caching a failure makes the next run report the same error
            # forever without retrying it -- which is what happened when the
            # `docker` package was missing.
            done = set(prev[prev.error.isna()].sorter) if "error" in prev \
                else set(prev.sorter)
            if set(sorters) <= done:
                frames.append(prev)
                print(f"  [{i}/{len(jobs)}] cached  {j['stem'][:50]}")
                continue
            retry = sorted(set(sorters) - done)
            print(f"  [{i}/{len(jobs)}] retrying {retry}  {j['stem'][:40]}")
        print(f"  [{i}/{len(jobs)}] {j['stem'][:50]} ...", flush=True)
        try:
            df = run_session(j, sorters, docker_mode=args.docker,
                             timeout_s=args.timeout)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            continue
        df.to_parquet(shard, engine="pyarrow", index=False)
        frames.append(df)
        for r in df.itertuples():
            err = getattr(r, "error", None)
            if isinstance(err, str) and err:
                print(f"        {r.sorter:16s} {err[:74]}")
            else:
                # Mixed frames make these floats; format defensively.
                print(f"        {r.sorter:16s} {r.n_units:6.0f} units  "
                      f"{r.n_spikes:9.0f} spikes  {r.seconds:6.1f}s  "
                      f"nev_recovered={r.frac_nev_recovered:.2f}  "
                      f"peak/noise={r.peak_to_noise:.1f}")

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

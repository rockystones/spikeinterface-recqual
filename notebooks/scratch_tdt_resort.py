"""Re-sort TDT broadband with the modern pool and compare against the legacy sort.

The legacy sorts in this corpus -- Luigi's `baySort`, Oops's OpenSorter runs,
Picasso's `kmsort` -- all label an event list the TDT rig had already detected
online. The modern pool re-detects from the continuous trace. **The two are
therefore not a fixed-event comparison**, exactly as with `.ns5` re-sorting in
S11, and the honest quantities to compare are yield and per-unit quality, not
spike-by-spike agreement.

Two constraints shape what this can cover.

**Only some blocks have both.** A legacy sort plus a readable broadband stream
co-occur on 5 Oops blocks, 1 Picasso block, and Luigi's 2013 tanks, whose
`Raw2` is carried inline in the tev rather than in `.sev` files.

**Luigi's 2013 broadband is int16 ADC counts**, and the counts-per-microvolt
factor is a PZ amplifier setting that the tank does not record
(`docs/notes/tdt_corpus.md`). Sorting is scale-invariant -- every sorter sets
its detection threshold in units of the trace's own MAD -- and so is SNR. So
every comparison here is expressed in **SNR and unit counts, never in
microvolts**, which keeps Luigi in the table instead of dropping him.

Geometry is a placeholder and says so. Which store is which anatomy is not yet
known, so a canonical 10x10 grid at the Utah pitch is attached rather than the
array's own mapfile. That is defensible *for sorting specifically*: at 400 um
every sorter's neighbourhood radius covers one electrode -- MountainSort5's own
log prints the adjacency as `[[0], [1], ... [95]]` -- so the channel-to-position
permutation cannot change the result. It would change any spatial output, and
none is produced here.

Run from repo root:

    uv run python notebooks/scratch_tdt_resort.py [--jobs 1] [--slice 180]
                                                  [--subject Oops]

Writes `data/derived/tdt/resort/<block>__<array>.parquet` shards and
`data/derived/tdt/tdt_resort.parquet`.

See:
- docs/notes/tdt_legacy_sorts.md
- docs/notes/ns5_plan.md
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_ns5_resort import (  # noqa: E402
    FILTER_FREQ_HZ,
    FILTER_ORDER,
    PITCH_UM,
    SORTER_PARAMS,
    fresh_folder,
    sorter_kwargs,
    summarise_error,
    wants_docker,
)
from scratch_tdt_io import open_tank  # noqa: E402

INV = REPO / "data" / "derived" / "tdt_inventory.parquet"
LEGACY = REPO / "data" / "derived" / "tdt" / "offline_sort_units.parquet"
STATUS = REPO / "data" / "derived" / "tdt" / "offline_sort_status.parquet"
OUT_DIR = REPO / "data" / "derived" / "tdt"
SHARD_DIR = OUT_DIR / "resort"
SUMMARY_OUT = OUT_DIR / "tdt_resort.parquet"

# Seconds of broadband to sort. Luigi's blocks run 13-18 minutes and Oops's
# 3 minutes; a common window keeps yield comparable across subjects, and
# CLAUDE.md's own rule is to iterate on 1-5 minute slices.
SLICE_S = 180.0
# The project's SNR gate. Reported both ways here because section 5 of
# `scratch_tdt_sorted.py` shows it does not transfer across acquisition
# systems unchanged.
SNR_GATE = 4.0
DEFAULT_SORTERS = ("mountainsort5", "tridesclous2", "spykingcircus2")


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === Recording construction ===
def placeholder_probe(n_channels: int, pitch_um: float = PITCH_UM):
    """A canonical Utah grid, used because the real mapping is not yet known.

    Row-major over a square grid large enough to hold the channels. See the
    module docstring for why this is safe for sorting and unsafe for anything
    spatial.
    """
    from probeinterface import Probe

    side = int(np.ceil(np.sqrt(n_channels)))
    pos = np.array([[(i % side) * pitch_um, (i // side) * pitch_um]
                    for i in range(n_channels)], dtype=float)
    probe = Probe(ndim=2, si_units="um")
    probe.set_contacts(positions=pos, shapes="circle",
                       shape_params={"radius": 20.0})
    probe.set_device_channel_indices(np.arange(n_channels))
    probe.annotate(name=f"placeholder-{n_channels}", manufacturer="blackrock")
    return probe


def open_tdt_recording(tev: str, array: int, slice_s: float):
    """Filtered broadband for one array, sliced, with a probe attached."""
    import spikeinterface.extractors as se
    from spikeinterface.preprocessing import highpass_filter

    rec = se.read_tdt(folder_path=str(tev), stream_name=f"Raw{array}")
    fs = rec.get_sampling_frequency()
    n = min(rec.get_num_frames(), int(slice_s * fs))
    rec = rec.frame_slice(0, n)
    rec = rec.set_probe(placeholder_probe(rec.get_num_channels()),
                        group_mode="by_probe")
    return highpass_filter(rec, freq_min=FILTER_FREQ_HZ,
                           filter_order=FILTER_ORDER), dict(
        sr=float(fs), n_channels=int(rec.get_num_channels()),
        slice_s=float(n / fs))


def _sorter_child(tev: str, array: int, slice_s: float, name: str,
                  use_docker: bool, folder: str) -> None:
    """Child entry point: run one sorter and leave the result on disk."""
    from spikeinterface.sorters import run_sorter

    rec_f, _ = open_tdt_recording(tev, array, slice_s)
    run_sorter(sorter_name=name, recording=rec_f, folder=folder,
               remove_existing_folder=False, verbose=False,
               **sorter_kwargs(name, use_docker))


def run_sorter_guarded(job: dict, name: str, use_docker: bool,
                       timeout_s: float):
    """Run one sorter in a killable child. Returns (sorting or None, error).

    Same construction as S11's, and for the same reason: a sorter that
    deadlocks on a paging-file failure has no timeout of its own, and one such
    call once blocked a 67-session run for 31 hours.
    """
    import multiprocessing as mp

    from spikeinterface.sorters import read_sorter_folder

    tag = f"{job['block']}_a{job['array']}__{name}"
    folder = fresh_folder(SHARD_DIR / "work" / tag)
    ctx = mp.get_context("spawn")          # Windows has no fork
    p = ctx.Process(target=_sorter_child,
                    args=(job["tev"], job["array"], job["slice_s"], name,
                          use_docker, str(folder)))
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
        return read_sorter_folder(folder), folder
    except Exception as exc:  # noqa: BLE001
        return None, summarise_error(exc)


# %%
# === Per-unit quality, in units that survive an unknown gain ===
def unit_quality(sorting, rec_f) -> pd.DataFrame:
    """Per-unit SNR, amplitude and rate from a SortingAnalyzer.

    SNR is the quantity that matters here: it is dimensionless, so it is
    comparable between Oops's float32 microvolts and Luigi's int16 counts, and
    it is the quantity the project's gate is expressed in.
    """
    from spikeinterface.core import create_sorting_analyzer

    sa = create_sorting_analyzer(sorting=sorting, recording=rec_f,
                                 sparse=False)
    sa.compute(["random_spikes", "waveforms", "templates", "noise_levels"])
    from spikeinterface.qualitymetrics import compute_quality_metrics

    qm = compute_quality_metrics(
        sa, metric_names=["snr", "firing_rate", "isi_violation",
                          "presence_ratio"])
    ext = sa.get_extension("templates").get_data()
    ids = list(sa.unit_ids)
    peak = [float(np.abs(ext[i]).max()) for i in range(len(ids))]
    out = qm.copy()
    out.insert(0, "unit_id", ids)
    out["peak_abs"] = peak
    return out.reset_index(drop=True)


def run_block(job: dict, sorters: tuple[str, ...], docker_mode: str,
              timeout_s: float) -> pd.DataFrame:
    """Every sorter on one (block, array)."""
    base = {k: v for k, v in job.items() if k != "tev"}
    rows: list[dict] = []
    try:
        rec_f, info = open_tdt_recording(job["tev"], job["array"],
                                         job["slice_s"])
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame([{**base, "sorter": "load",
                              "error": summarise_error(exc)}])
    base.update(info)

    for name in sorters:
        use_docker = wants_docker(name, docker_mode)
        sorting, folder_or_err = run_sorter_guarded(job, name, use_docker,
                                                    timeout_s)
        if sorting is None:
            rows.append({**base, "sorter": name, "used_docker": use_docker,
                         "error": str(folder_or_err)})
            continue
        try:
            q = unit_quality(sorting, rec_f)
        except Exception as exc:  # noqa: BLE001
            rows.append({**base, "sorter": name, "used_docker": use_docker,
                         "n_units": int(len(sorting.unit_ids)),
                         "error": f"metrics: {summarise_error(exc)}"})
            continue
        snr = q["snr"].to_numpy(dtype=float)
        rows.append({
            **base, "sorter": name, "used_docker": use_docker,
            "n_units": int(len(sorting.unit_ids)),
            "n_spikes": int(sum(len(sorting.get_unit_spike_train(u))
                                for u in sorting.unit_ids)),
            "snr_med": float(np.nanmedian(snr)) if snr.size else np.nan,
            "snr_p25": float(np.nanpercentile(snr, 25)) if snr.size else np.nan,
            "snr_p75": float(np.nanpercentile(snr, 75)) if snr.size else np.nan,
            "n_pass_gate": int(np.nansum(snr >= SNR_GATE)),
            "frac_pass_gate": float(np.nanmean(snr >= SNR_GATE))
            if snr.size else np.nan,
            "rate_med": float(q["firing_rate"].median()),
        })
    return pd.DataFrame(rows)


# %%
# === Worklist ===
def build_worklist(inv: pd.DataFrame, slice_s: float,
                   sample: int = 0) -> list[dict]:
    """(block, array) pairs that carry a legacy sort covering *that* array.

    A `.SortResult` names the store it covers and zeroes the rest, so only that
    store's array has a legacy counterpart. Re-sorting the other array of the
    same block would produce a modern number with nothing to compare it to.
    The pairing comes from `offline_sort_status.parquet`, which records the
    covered store per sort, rather than from the block-level `n_sorts > 0`.
    """
    if not STATUS.exists():
        raise FileNotFoundError(
            f"{STATUS} not found -- run scratch_tdt_sorted.py first")
    st = pd.read_parquet(STATUS)
    st = st[st.status == "ok"].copy()
    st["array"] = st.store.map(lambda s: int(str(s)[-1]))

    live = inv[inv.live & inv.excluded.isna()].copy()
    key = ["subject", "block", "array"]
    j = st[key + ["sort"]].merge(live[key + ["path", "stem", "date"]],
                                 on=key, how="inner")
    jobs: list[dict] = []
    for _, r in j.drop_duplicates(key).iterrows():
        jobs.append(dict(
            tev=str(Path(r["path"]) / f"{r['stem']}.tev"),
            path=r["path"], subject=r["subject"], block=r["block"],
            date=r["date"], array=int(r["array"]), slice_s=slice_s,
            sort_name=r["sort"],
        ))
    if sample:
        jobs = _spread(jobs, sample)
    return jobs


def _spread(jobs: list[dict], n: int) -> list[dict]:
    """Keep n jobs per subject, spread evenly by date.

    Luigi contributes 144 candidates and each costs ~10 minutes of header
    parse before a sorter even starts, so the full set is not affordable.
    Spreading by date keeps the 2013 range represented rather than its first
    few weeks.
    """
    out: list[dict] = []
    by_subject: dict[str, list[dict]] = {}
    for job in jobs:
        by_subject.setdefault(job["subject"], []).append(job)
    for group in by_subject.values():
        group = sorted(group, key=lambda j: (j["date"] or "", j["block"]))
        if len(group) <= n:
            out.extend(group)
            continue
        idx = np.unique(np.linspace(0, len(group) - 1, n).round().astype(int))
        out.extend(group[i] for i in idx)
    return out


def report(d: pd.DataFrame, legacy: pd.DataFrame | None) -> None:
    ok = d[d.get("error").isna()] if "error" in d else d
    banner("1. Runs")
    print(f"  rows: {len(d)}   failed: {len(d) - len(ok)}")
    if len(d) > len(ok):
        print(d[d.error.notna()][["subject", "block", "array", "sorter",
                                  "error"]].to_string(index=False))
    if not len(ok):
        return
    print()
    print(ok.groupby(["subject", "sorter"]).agg(
        blocks=("block", "nunique"), units=("n_units", "median"),
        spikes=("n_spikes", "median"), snr=("snr_med", "median"),
        pass_frac=("frac_pass_gate", "median")).round(2).to_string())

    banner("2. Spread between modern sorters on the same block")
    piv = ok.pivot_table(index=["subject", "block", "array"],
                         columns="sorter", values="n_units")
    piv = piv.dropna(how="any")
    if len(piv):
        spread = piv.max(axis=1) / piv.min(axis=1).replace(0, np.nan)
        print(f"  blocks where all sorters ran: {len(piv)}")
        print(f"  unit-count spread: median {spread.median():.2f}x  "
              f"p90 {spread.quantile(0.9):.2f}x  max {spread.max():.2f}x")
        print("  Blackrock S11 reference: median 1.44x, p90 2.09x")

    if legacy is None or not len(legacy):
        return
    banner("3. Legacy sort vs modern pool, same blocks")
    print("  Unit counts and SNR. The legacy sorter labels events the rig")
    print("  detected online; the modern pool re-detects from the trace, so")
    print("  this is a yield comparison, not an agreement one.\n")
    leg = legacy.groupby(["subject", "block", "array"]).agg(
        legacy_units=("unit", "size"),
        legacy_snr=("snr", "median"),
        legacy_pass=("passes_gate", "mean")).reset_index()
    mod = ok.groupby(["subject", "block", "array"]).agg(
        modern_units=("n_units", "median"),
        modern_snr=("snr_med", "median"),
        modern_pass=("frac_pass_gate", "median")).reset_index()
    j = leg.merge(mod, on=["subject", "block", "array"], how="inner")
    if not len(j):
        print("  no block has both a legacy sort and a completed re-sort yet")
        return
    j["unit_ratio"] = j.modern_units / j.legacy_units.replace(0, np.nan)
    print(j.round(3).to_string(index=False))
    print(f"\n  modern / legacy unit count: median "
          f"{j.unit_ratio.median():.2f}x  (n = {len(j)})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--slice", type=float, default=SLICE_S)
    ap.add_argument("--subject", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=2400.0)
    ap.add_argument("--docker", default="auto",
                    choices=("auto", "always", "never"))
    ap.add_argument("--sorters", default=",".join(DEFAULT_SORTERS))
    ap.add_argument("--sample", type=int, default=0,
                    help="keep N blocks per subject, spread evenly by date")
    args = ap.parse_args()

    sorters = tuple(s for s in args.sorters.split(",") if s in SORTER_PARAMS)
    inv = pd.read_parquet(INV)
    jobs = build_worklist(inv, args.slice, args.sample)
    if args.subject:
        jobs = [j for j in jobs if j["subject"] == args.subject]
    if args.limit:
        jobs = jobs[:args.limit]

    banner("TDT re-sort -- legacy versus the modern pool")
    print(f"  (block, array) pairs: {len(jobs)}   sorters: {sorters}")
    print(f"  slice: {args.slice:.0f}s   timeout: {args.timeout:.0f}s/sorter")
    SHARD_DIR.mkdir(parents=True, exist_ok=True)

    frames: list[pd.DataFrame] = []
    for i, job in enumerate(jobs, 1):
        shard = SHARD_DIR / f"{job['block']}_a{job['array']}.parquet"
        if shard.exists():
            frames.append(pd.read_parquet(shard))
            print(f"  [{i}/{len(jobs)}] {job['block']} a{job['array']}: cached")
            continue
        print(f"  [{i}/{len(jobs)}] {job['block']} a{job['array']} "
              f"({job['subject']}) ...", flush=True)
        d = run_block(job, sorters, args.docker, args.timeout)
        d.to_parquet(shard, engine="pyarrow", index=False)
        frames.append(d)

    d = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if len(d):
        d.to_parquet(SUMMARY_OUT, engine="pyarrow", index=False)
    legacy = pd.read_parquet(LEGACY) if LEGACY.exists() else None
    report(d, legacy)
    print(f"\n  wrote {SUMMARY_OUT}  ({len(d)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

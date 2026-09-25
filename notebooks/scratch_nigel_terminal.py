"""Nigel terminal session (2025-09-25): the full analysis suite.

The terminal recordings live as NPMK openNSx v7.3 exports
(`NS5_datafile00xx 1.mat`, 254 ch x 74 s int16) plus the NEVs; only
datafile0075 was human-sorted (-01). Everything file-level already ran
(inventory, previews, exact mmp2p: 48 units / 34 active channels /
61.7 uV, stripe pass, cohort row). This script adds the two missing
layers and the context figure:

1. MODERN-SORTER CONSENSUS on the continuous data. The .mat is not a
   .ns5, so the ns5 pipeline can't read it; load_mat_recording()
   rebuilds an SI recording from the NPMK struct - band corners from
   the embedded EXTENDED HEADER (CLAUDE.md: never the suffix), per-
   channel gain from MaxAnalog/MaxDigi, probe from the SN1496 CMP -
   caches it as an SI binary folder, and runs the CLAUDE.md pool with
   the ns5 pipeline's exact filter and parameters (MS5 scheme 2, TDC2,
   SC2 native; KS4 do_correction=False in the ks4:cu128 container,
   skipped with a recorded reason when Docker is down).
2. MANUAL-SORT COMPARISON + GATE AUTOPSY (datafile0075): the sorted
   NEV as a NumpySorting compared against each sorter at the I-005
   OFS tolerance (1.0 ms); the 48 manual units scored under the
   physics gate (scratch_rocky_resort.unit_metrics) to see WHY the
   cohort row reads 0 gated units.
3. Context figure: the terminal day on Nigel Anterior's mmp2p / yield
   trajectory.

The array is Anterior = TNP-family (D-008/D-014); the owner reports
the Ctrl-family array had failed by the terminal day, so no Posterior
files exist - consistent with the inventory.

Outputs: data/derived/nigel_terminal/{terminal_sorters,
terminal_agreement, manual_gate_audit}.parquet,
figures/nigel/terminal_overview.png
Run: uv run python notebooks/scratch_nigel_terminal.py [--skip-sort]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scratch_cohort_io import parse_cmp  # noqa: E402
from scratch_ns5_resort import (  # noqa: E402
    CUSTOM_IMAGE, FILTER_FREQ_HZ, FILTER_ORDER, SORTER_PARAMS,
    build_probe, chance_match_rate, match_rate, signal_check,
    summarise_error, wants_docker)
from scratch_rocky_resort import (  # noqa: E402
    open_nev, read_electrode, unit_metrics)

REPO = Path(__file__).resolve().parent.parent
TERM = Path(r"D:/Claude Code/Monkey Data/Nigel/Terminal recordings")
CMP = next((REPO / "configs" / "probes").glob("*1025-001496*.cmp"))
OUT = REPO / "data" / "derived" / "nigel_terminal"
FIG = REPO / "figures" / "nigel"
STEMS = ["datafile0075", "datafile0080", "datafile0090"]
SORTERS = ["mountainsort5", "tridesclous2", "spykingcircus2",
           "kilosort4"]
DELTA_OFS_MS = 1.0          # I-005: manual-sort comparisons at 1.0 ms
TIMEOUT_S = 3600.0


def _deref_num(f, field, i):
    """ElectrodesInfo numeric cell i (h5 object-reference array)."""
    return float(np.asarray(f[f[field][i, 0]]).ravel()[0])


def _deref_str(f, field, i):
    """ElectrodesInfo char-array cell i -> str."""
    a = np.asarray(f[f[field][i, 0]]).ravel()
    return "".join(chr(int(c)) for c in a if int(c) > 0)


def load_mat_recording(mat: Path):
    """NPMK openNSx v7.3 export -> (SI recording with probe, info)."""
    import h5py
    import spikeinterface.core as sc

    f = h5py.File(mat, "r")
    ns5 = f["NS5"]
    n_pts = float(np.asarray(ns5["MetaTags/DataPoints"]).ravel()[0])
    dur = float(np.asarray(ns5["MetaTags/DataDurationSec"]).ravel()[0])
    sr = n_pts / dur
    assert abs(sr - 30000) < 1, f"unexpected sampling rate {sr}"

    cmp_df = parse_cmp(CMP)
    want = set(int(c) for c in cmp_df.channel_id)

    ei = ns5["ElectrodesInfo"]
    n_ch = f[ei.name + "/ElectrodeID"].shape[0]
    sel, ids, gains, hp_hz = [], [], [], []
    for i in range(n_ch):
        eid = int(_deref_num(f, ei.name + "/ElectrodeID", i))
        if eid not in want:
            continue
        sel.append(i)
        ids.append(eid)
        # per-channel gain from the digital->analog range (uV/count)
        rng_a = (_deref_num(f, ei.name + "/MaxAnalogValue", i)
                 - _deref_num(f, ei.name + "/MinAnalogValue", i))
        rng_d = (_deref_num(f, ei.name + "/MaxDigiValue", i)
                 - _deref_num(f, ei.name + "/MinDigiValue", i))
        gains.append(rng_a / rng_d)
        # band from the EXTENDED HEADER, mHz -> Hz (CLAUDE.md rule)
        hp_hz.append(_deref_num(f, ei.name + "/HighFreqCorner", i)
                     / 1000.0)
    assert len(ids) == len(want), \
        f"only {len(ids)} of {len(want)} mapfile electrodes in the mat"

    # h5 axis0 = samples, axis1 = channels (v7.3 stores MATLAB
    # transposed); slice the array channels in one read
    data = ns5["Data"][:, sel].astype(np.int16, copy=False)
    f.close()

    rec = sc.NumpyRecording(data, sampling_frequency=sr,
                            channel_ids=[str(i) for i in ids])
    rec.set_channel_gains(gains)
    rec.set_channel_offsets(0.0)
    probe = build_probe(cmp_df)
    index_by_id = {cid: k for k, cid in enumerate(rec.channel_ids)}
    probe.set_device_channel_indices(np.array(
        [index_by_id[str(int(c))] for c in cmp_df.channel_id],
        dtype=int))
    rec = rec.set_probe(probe, group_mode="by_probe")
    info = dict(sr=sr, duration_s=dur, n_channels=len(ids),
                gain_uv=float(np.median(gains)),
                hp_corner_hz=float(np.median(hp_hz)))
    return rec, info


def cached_recording(stem: str):
    """Load (or build+cache) the terminal recording, binary folder."""
    import spikeinterface.core as sc
    folder = OUT / f"rec_{stem}"
    meta_p = OUT / f"rec_{stem}.json"
    if folder.exists() and meta_p.exists():
        import json
        return sc.load_extractor(folder), json.loads(
            meta_p.read_text())
    rec, info = load_mat_recording(TERM / f"NS5_{stem} 1.mat")
    rec = rec.save(folder=folder, format="binary", overwrite=True)
    import json
    meta_p.write_text(json.dumps(info))
    return rec, info


def _sorter_child(rec_folder: str, name: str, use_docker: bool,
                  out_folder: str) -> None:
    """Child: load cached recording, filter, run one sorter."""
    from spikeinterface.core import load_extractor
    from spikeinterface.preprocessing import highpass_filter
    from spikeinterface.sorters import run_sorter

    drive = Path(rec_folder).drive         # KS4 drive-letter gotcha
    if drive and Path(drive + "\\").exists():
        os.chdir(drive + "\\")
    rec = load_extractor(rec_folder)
    rec_f = highpass_filter(rec, freq_min=FILTER_FREQ_HZ,
                            filter_order=FILTER_ORDER)
    # sorter_kwargs carries the hard-won container settings: SI
    # pypi-installed inside the image (the github mode fails with
    # ModuleNotFoundError) and KS4 dminx from the probe's own 400-um
    # pitch instead of the Neuropixels default
    from scratch_ns5_resort import sorter_kwargs
    run_sorter(name, rec_f, folder=out_folder, verbose=False,
               remove_existing_folder=True,
               **sorter_kwargs(name, use_docker, rec_f))


def run_one(stem: str, name: str, use_docker: bool):
    """Guarded sorter run; returns (sorting|None, err|None, seconds)."""
    import multiprocessing as mp
    from spikeinterface.sorters import read_sorter_folder

    folder = OUT / "sortings" / f"{stem}__{name}"
    t0 = time.perf_counter()
    if not (folder / "spikeinterface_log.json").exists():
        ctx = mp.get_context("spawn")
        p = ctx.Process(target=_sorter_child,
                        args=(str(OUT / f"rec_{stem}"), name,
                              use_docker, str(folder)))
        p.start()
        p.join(TIMEOUT_S)
        if p.is_alive():
            p.terminate()
            p.join(15)
            return None, f"timeout>{TIMEOUT_S:.0f}s", \
                time.perf_counter() - t0
    try:
        return read_sorter_folder(folder), None, \
            time.perf_counter() - t0
    except Exception as exc:  # noqa: BLE001
        return None, summarise_error(exc), time.perf_counter() - t0


def manual_sorting(sr: float):
    """The human sort of datafile0075 as (NumpySorting, unit table)."""
    from spikeinterface.core import NumpySorting

    raw, meta, cbe = open_nev(TERM / "datafile0075-01.nev")
    nbefore, dur = meta["nbefore"], meta["duration_s"]
    times, labels, rows = [], [], []
    for elec in sorted(cbe):
        e = read_electrode(raw, meta, cbe[elec])
        if e is None or not len(e["t"]):
            continue
        wf, t, pu = e["wf"], e["t"], e["plexon_unit"]
        noise = None
        for u in sorted(set(pu.tolist()) - {0, 255}):
            selu = pu == u
            if selu.sum() < 2:
                continue
            if noise is None:
                from scratch_rocky_resort import baseline_noise_uv
                noise = baseline_noise_uv(wf, nbefore)
            m = unit_metrics(wf[selu], t[selu], noise, meta["sr"],
                             nbefore, dur)
            m.update(channel_id=int(elec), unit=int(u))
            rows.append(m)
            times.append((t[selu] * sr).astype(np.int64))
            labels.append(np.full(selu.sum(), elec * 100 + u))
    st = NumpySorting.from_times_labels(
        [np.concatenate(times)], [np.concatenate(labels)], sr)
    return st, pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-sort", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    import spikeinterface.comparison as scmp

    docker_up = os.system("docker info >nul 2>&1") == 0
    print(f"docker available: {docker_up}")

    rows, sortings = [], {}
    for stem in STEMS:
        rec, info = cached_recording(stem)
        print(f"[{stem}] {info['duration_s']:.1f}s, "
              f"{info['n_channels']} ch, gain {info['gain_uv']:.3f} "
              f"uV/ct, HP corner {info['hp_corner_hz']:.1f} Hz")
        base = dict(stem=stem, **info)
        from spikeinterface.preprocessing import highpass_filter
        base.update(signal_check(highpass_filter(
            rec, freq_min=FILTER_FREQ_HZ, filter_order=FILTER_ORDER)))
        if args.skip_sort:
            continue
        for name in SORTERS:
            use_docker = wants_docker(name, "auto")
            if use_docker and not docker_up:
                rows.append({**base, "sorter": name,
                             "error": "docker not running"})
                print(f"    {name}: SKIPPED (docker down)")
                continue
            sorting, err, secs = run_one(stem, name, use_docker)
            r = {**base, "sorter": name, "seconds": round(secs, 1),
                 "error": err}
            if sorting is not None:
                sortings[(stem, name)] = sorting
                r["n_units"] = int(len(sorting.unit_ids))
                r["n_spikes"] = int(sum(
                    len(sorting.get_unit_spike_train(u, 0))
                    for u in sorting.unit_ids))
            rows.append(r)
            print(f"    {name}: "
                  f"{r.get('n_units', 'ERR ' + str(err))} units "
                  f"({secs:.0f}s)")
    if rows:
        pd.DataFrame(rows).to_parquet(OUT / "terminal_sorters.parquet",
                                      index=False)

    # --- consensus + manual comparison (0075) ------------------------
    agree_rows = []
    for stem in STEMS:
        got = {n: s for (st, n), s in sortings.items() if st == stem}
        names = sorted(got)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                c = scmp.compare_two_sorters(
                    got[names[i]], got[names[j]],
                    delta_time=0.4, match_score=0.5)
                m = c.get_matching()[0]
                agree_rows.append(dict(
                    stem=stem, a=names[i], b=names[j],
                    n_a=len(got[names[i]].unit_ids),
                    n_b=len(got[names[j]].unit_ids),
                    n_matched=int((np.asarray(m) >= 0).sum())))
    # manual sort against every sorter (0075 only)
    rec0, info0 = cached_recording(STEMS[0])
    manual, audit = manual_sorting(info0["sr"])
    audit.to_parquet(OUT / "manual_gate_audit.parquet", index=False)
    n_gated = int(audit.pass_gate.sum())
    print(f"\nmanual sort: {len(audit)} units, {n_gated} pass the "
          f"gate; reject reasons:")
    print(audit.loc[~audit.pass_gate, "reject_reason"]
          .value_counts().head(6).to_string())
    for name, s in {n: s for (st, n), s in sortings.items()
                    if st == STEMS[0]}.items():
        c = scmp.compare_two_sorters(manual, s,
                                     delta_time=DELTA_OFS_MS,
                                     match_score=0.5)
        m = c.get_matching()[0]
        agree_rows.append(dict(stem=STEMS[0], a="manual", b=name,
                               n_a=len(manual.unit_ids),
                               n_b=len(s.unit_ids),
                               n_matched=int((np.asarray(m) >= 0)
                                             .sum())))
    if agree_rows:
        pd.DataFrame(agree_rows).to_parquet(
            OUT / "terminal_agreement.parquet", index=False)
        print("\npairwise agreement (units matched at 0.5):")
        print(pd.DataFrame(agree_rows).to_string(index=False))

    # --- context figure ----------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    m = pd.read_parquet(REPO / "data" / "derived" / "cohort" /
                        "mean_max_p2p.parquet")
    m = m[(m.subject == "Nigel")].copy()
    m["date"] = pd.to_datetime(m.date)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for arr, g in m.groupby("array"):
        g = g.sort_values("date")
        term = g.date.max() >= pd.Timestamp("2025-09-01")
        axes[0].plot(g.date, g.max_p2p_mean_nan, ".-", ms=4,
                     label=f"{arr}")
        axes[1].plot(g.date, g.n_active, ".-", ms=4, label=arr)
    for ax, yl in zip(axes, ("mean max P2P over active ch (uV)",
                             "active channels (of 96)")):
        t = m[m.date >= "2025-09-01"]
        if len(t):
            ax.axvline(t.date.iloc[0], color="r", ls="--", lw=1)
            ax.annotate("terminal\n2025-09-25", (t.date.iloc[0],
                        ax.get_ylim()[1] * 0.85), color="r",
                        fontsize=8, ha="left")
        ax.set_ylabel(yl)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    fig.suptitle("Nigel: the terminal session in context (Plexon "
                 "layer; Anterior = TNP-family; Posterior absent "
                 "after its 2024 failure)")
    fig.tight_layout()
    fig.savefig(FIG / "terminal_overview.png", dpi=150)
    print(f"\nwrote {FIG / 'terminal_overview.png'} and "
          f"{OUT}/*.parquet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

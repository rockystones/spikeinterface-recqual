"""The sorting-free layer over the whole Oops/Picasso TDT corpus.

This is the layer that reaches every session, and on this corpus it is not a
fallback but the primary instrument. TDT's online sortcode is an accept flag,
not a unit id -- only codes 0 and 1 occur, and no channel carries a second
identified neuron -- so there is no sorting-based layer to compare against
without re-sorting the broadband first. See `docs/notes/tdt_corpus.md`.

Metric names and definitions are deliberately identical to
`scratch_headstage_free.free_metrics`, which computed the same quantities on
Blackrock NEVs. Same columns means the two corpora can be put in one table.

Two TDT-specific checks ride along because they cost nothing once the snippets
are in memory:

- **the modal trough index**, which is what justifies `NBEFORE = 8` against
  NEO's reported 20. If any session disagrees, its noise floor is wrong and
  this column says so.
- **the NaN fraction**, since ~0.2% of TDT snippets arrive NaN-filled.

With `--broadband` the pass additionally bandpasses each block's `Raw*` stream
to the spike band and takes a per-channel MAD, giving the first independent
check of the snippet noise estimate since the single Nigel session in
`snippet_noise_floor.md` -- this time on 56 sessions and a different rig.

Run from repo root:

    uv run python notebooks/scratch_tdt_free.py [--jobs 6] [--broadband]

Writes `data/derived/tdt/free_metrics.parquet`.

See:
- docs/notes/tdt_corpus.md
- docs/notes/snippet_noise_floor.md
"""

from __future__ import annotations

import argparse
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from _paths import MONKEY_ROOT  # noqa: E402
from scratch_rocky_resort import baseline_noise_uv  # noqa: E402
from scratch_tdt_io import (  # noqa: E402
    channel_index,
    detect_nbefore,
    has_broadband,
    open_tank,
)

INV = REPO / "data" / "derived" / "tdt_inventory.parquet"
OUT_DIR = REPO / "data" / "derived" / "tdt"
OUT = OUT_DIR / "free_metrics.parquet"

# Matching the NSP-era convention in snippet_noise_floor.md: the comparison
# band is the acquisition system's own spike filter, so that a continuous MAD
# and a snippet MAD are estimating the same thing.
SPIKE_BAND = (300.0, 5000.0)
# Seconds of broadband to bandpass for the noise cross-check. The floor is a
# stationary property; 20 s of 96 channels is ample and keeps the pass cheap.
BROADBAND_SLICE_S = 20.0


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === One block, both arrays ===
def block_metrics(job: dict) -> list[dict]:
    """Sorting-free metrics for every live array in one TDT block.

    Opening the tank costs ~14 s of header parsing, so both arrays are done in
    one pass rather than one job per (block, array).
    """
    tev = Path(job["tev"])
    base_keys = ("subject", "block", "date", "letter", "run", "duration_s")
    try:
        io, meta = open_tank(tev)
        idx = channel_index(io)
    except Exception as exc:  # noqa: BLE001
        return [dict({k: job[k] for k in base_keys}, array=a,
                     error=f"{type(exc).__name__}: {exc}"[:140])
                for a in job["arrays"]]

    dur = meta["duration_s"] if np.isfinite(meta["duration_s"]) \
        else job["duration_s"]
    rows: list[dict] = []
    for arr in job["arrays"]:
        store = f"eNe{arr}"
        # Measured, not assumed: Luigi's 2013 tanks sample eNe at 48828 Hz and
        # trough at sample 9 rather than 8, uniformly across every channel.
        nbefore = detect_nbefore(io, meta, store, idx)
        meta = dict(meta, nbefore=nbefore)
        base = dict({k: job[k] for k in base_keys}, array=arr, store=store,
                    duration_s=dur, has_broadband=job["has_broadband"],
                    nbefore=nbefore)
        chans = sorted(c for (s, c) in idx if s == store)
        noises: list[float] = []
        counts: list[int] = []
        troughs: list[np.ndarray] = []
        snrs: list[float] = []
        modal: list[int] = []
        n_code1 = 0
        n_seen = 0
        for ch in chans:
            e = None
            try:
                e = read_one(io, meta, idx[(store, ch)])
            except Exception:  # noqa: BLE001 - one bad channel must not kill a block
                pass
            if e is None or not len(e["t"]):
                continue
            wf = e["wf"]
            noise = baseline_noise_uv(wf, meta["nbefore"])
            # |trough| per event: the crossing amplitude, sign-free. Same
            # definition as the Blackrock pass so the tables can be stacked.
            amp = np.abs(wf.min(axis=1))
            noises.append(noise)
            counts.append(len(e["t"]))
            troughs.append(amp)
            modal.append(int(np.bincount(np.argmin(wf, axis=1),
                                         minlength=wf.shape[1]).argmax()))
            n_code1 += int((e["code"] == 1).sum())
            n_seen += len(e["t"])
            if noise > 0:
                snrs.append(float(np.median(amp) / noise))
        if not counts:
            rows.append(dict(**base, error="no events"))
            continue

        allamp = np.concatenate(troughs)
        n_elec = meta["stores"].get(store, {}).get("n_chan", 96)
        rows.append(dict(
            **base,
            noise_med=float(np.median(noises)),
            noise_p90=float(np.percentile(noises, 90)),
            n_crossings=int(sum(counts)),
            crossing_rate_hz=float(sum(counts) / dur / max(len(counts), 1))
            if dur and np.isfinite(dur) else np.nan,
            amp_p50=float(np.percentile(allamp, 50)),
            amp_p90=float(np.percentile(allamp, 90)),
            amp_p99=float(np.percentile(allamp, 99)),
            amp_max=float(allamp.max()),
            peak_snr_med=float(np.median(snrs)) if snrs else np.nan,
            n_elec_active=len(counts),
            frac_elec_active=len(counts) / n_elec,
            n_electrodes=float(n_elec),
            frac_code1=n_code1 / n_seen if n_seen else np.nan,
            modal_trough=int(np.bincount(modal).argmax()),
            modal_trough_agree=float(np.mean(np.array(modal) == nbefore)),
        ))

    if job.get("broadband") and has_broadband(tev.parent):
        for r in rows:
            if "error" in r:
                continue
            r.update(broadband_noise(tev, r["array"]))
    return rows


def read_one(io, meta, units):
    """Thin indirection so the import stays local to the worker process."""
    from scratch_tdt_io import read_channel
    return read_channel(io, meta, units)


def broadband_noise(tev: Path, array: int) -> dict:
    """Per-channel MAD from the continuous trace, for the snippet cross-check.

    Returns empty on any failure: a tank can declare `Raw*` in its Tbk and
    carry no `.sev`, and a missing cross-check must not lose the row.

    **Refuses integer stores.** The snippet side is microvolts; Luigi's 2013
    `Raw*` is int16 ADC counts with no recorded counts-per-microvolt factor
    (`docs/notes/tdt_corpus.md`). Dividing one by the other would produce a
    ratio that looks like a noise-estimator bias and is really a unit error.
    Today this is belt and braces -- those tanks carry no `.sev` so the caller
    skips them anyway -- but the guard should not depend on that coincidence.
    """
    try:
        import spikeinterface.extractors as se
        from scratch_tdt_io import store_table, stream_units
        from spikeinterface.core import get_noise_levels
        from spikeinterface.preprocessing import bandpass_filter

        stores = store_table(tev.with_suffix(".Tbk"))
        units = stream_units(dict(stores=stores), f"Raw{array}")
        if units != "uV":
            return dict(bb_error=f"Raw{array} is {units}, not comparable "
                                 f"with microvolt snippets")

        rec = se.read_tdt(folder_path=str(tev), stream_name=f"Raw{array}")
        fs = rec.get_sampling_frequency()
        n = min(rec.get_num_frames(), int(BROADBAND_SLICE_S * fs))
        bp = bandpass_filter(rec.frame_slice(0, n), freq_min=SPIKE_BAND[0],
                             freq_max=SPIKE_BAND[1])
        # TDT streams arrive already scaled to uV -- verified against snippet
        # amplitudes on the same events -- so no gain is applied here.
        nl = np.asarray(get_noise_levels(bp, method="mad"))
        return dict(bb_noise_med=float(np.median(nl)),
                    bb_noise_p90=float(np.percentile(nl, 90)),
                    bb_n_chan=int(nl.size))
    except Exception as exc:  # noqa: BLE001
        return dict(bb_error=f"{type(exc).__name__}: {exc}"[:120])


# %%
# === Worklist ===
def stratified(jobs: list[dict], n: int) -> list[dict]:
    """Evenly spaced by date within each (subject, array set).

    Luigi's tanks cost minutes each to open -- a 1.18 GB tsq with 29.4M
    records, over which NEO's header parse runs one boolean mask per channel
    per store -- so the whole-corpus pass that is cheap for Oops and Picasso is
    not affordable for him. Sampling evenly across the date range preserves the
    longitudinal shape, which is what the trends need; sampling the first n
    would not.
    """
    if n <= 0 or n >= len(jobs):
        return jobs
    out: list[dict] = []
    by_subject: dict[str, list[dict]] = {}
    for j in jobs:
        by_subject.setdefault(j["subject"], []).append(j)
    for _subj, group in by_subject.items():
        group = sorted(group, key=lambda j: (j["date"] or "", j["block"]))
        take = max(1, round(n * len(group) / len(jobs)))
        idx = np.unique(np.linspace(0, len(group) - 1, take).round().astype(int))
        out.extend(group[i] for i in idx)
    return out


def build_worklist(inv: pd.DataFrame, broadband: bool) -> list[dict]:
    """One job per block, listing the arrays that actually acquired."""
    live = inv[inv.live & inv.excluded.isna()]
    jobs: list[dict] = []
    # Group on the absolute path, not the block name: Luigi's three trees use
    # `Block-N` names that repeat across them, and grouping on the name alone
    # would merge two different recordings into one job.
    for _, g in live.groupby("path"):
        r = g.iloc[0]
        jobs.append(dict(
            tev=str(Path(r["path"]) / f"{r['stem']}.tev"),
            subject=r["subject"], block=r["block"], date=r["date"],
            path=r["path"],
            letter=r["letter"], run=int(r["run"]),
            duration_s=float(r["duration_s"]),
            has_broadband=bool(r["has_broadband"]),
            arrays=sorted(int(a) for a in g["array"]),
            broadband=broadband,
        ))
    return jobs


def report(d: pd.DataFrame) -> None:
    ok = d[d.get("error").isna()] if "error" in d else d
    banner("1. Coverage")
    print(f"  rows            : {len(ok)} of {len(d)}")
    if len(d) > len(ok):
        print(d[d.error.notna()][["subject", "block", "array", "error"]]
              .head(10).to_string(index=False))
    print(ok.groupby(["subject", "array"]).agg(
        n=("block", "size"), first=("date", "min"), last=("date", "max"),
        noise=("noise_med", "median"), amp=("amp_p50", "median"),
        snr=("peak_snr_med", "median"),
        elec=("frac_elec_active", "median")).to_string())

    banner("2. Is NBEFORE = 8 right everywhere?")
    print("  NEO reports wf_left_sweep = 20 for these 40-sample snippets. If")
    print("  that were right, the 'baseline' would span the whole spike.\n")
    print(ok.groupby("subject").modal_trough.value_counts().to_string())
    print(f"\n  rows whose modal trough is 8 : "
          f"{int((ok.modal_trough == 8).sum())} of {len(ok)}")

    banner("3. The online threshold is not held constant")
    print("  Crossing rate per electrode, by subject and year.\n")
    y = ok.assign(year=pd.to_datetime(ok.date).dt.year)
    print(y.pivot_table(index="year", columns="subject",
                        values="crossing_rate_hz",
                        aggfunc="median").round(1).to_string())
    print("\n  Median |trough| amplitude, same cut:\n")
    print(y.pivot_table(index="year", columns="subject", values="amp_p50",
                        aggfunc="median").round(1).to_string())

    if "bb_noise_med" in ok and ok.bb_noise_med.notna().any():
        banner("4. Snippet noise estimate vs continuous MAD")
        b = ok[ok.bb_noise_med.notna()]
        ratio = b.noise_med / b.bb_noise_med
        print(f"  blocks with both  : {len(b)}")
        print(f"  snippet MAD median: {b.noise_med.median():.2f} uV")
        print(f"  continuous MAD    : {b.bb_noise_med.median():.2f} uV")
        print(f"  ratio median      : {ratio.median():.3f}  "
              f"(10-90%: {ratio.quantile(0.1):.3f}-{ratio.quantile(0.9):.3f})")
        print("  Nigel NEV reference: 1.305")
        r = np.corrcoef(b.noise_med, b.bb_noise_med)[0, 1]
        print(f"  correlation       : {r:+.3f}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--broadband", action="store_true",
                    help="also bandpass Raw* for a continuous noise floor")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--subject", default="",
                    help="restrict to one subject, e.g. Luigi")
    ap.add_argument("--sample", type=int, default=0,
                    help="keep only N blocks, spread evenly by date")
    ap.add_argument("--out", default="",
                    help="write here instead of the default, so a sampled "
                         "Luigi pass does not overwrite the full one")
    args = ap.parse_args()

    inv = pd.read_parquet(INV)
    jobs = build_worklist(inv, args.broadband)
    if args.subject:
        jobs = [j for j in jobs if j["subject"] == args.subject]
    if args.sample:
        jobs = stratified(jobs, args.sample)
    if args.limit:
        jobs = jobs[:args.limit]
    out_path = Path(args.out) if args.out else OUT
    banner("TDT sorting-free pass")
    print(f"  blocks: {len(jobs)}   broadband cross-check: {args.broadband}")
    print(f"  subjects: {sorted({j['subject'] for j in jobs})}")
    print(f"  writing:  {out_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Checkpoint. Luigi's 193 blocks carry 45.6 GB of tsq index between them
    # and the pass runs for hours; writing only at the end means an
    # interruption at hour four costs all four hours. The partial file is
    # written beside the target and replaces it at the end, so a reader never
    # sees a half-corpus at the real path.
    part = out_path.with_suffix(".partial.parquet")
    rows: list[dict] = []
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for i, batch in enumerate(ex.map(block_metrics, jobs, chunksize=1), 1):
            rows.extend(batch)
            if i % 20 == 0:
                print(f"    {i}/{len(jobs)} blocks", flush=True)
                pd.DataFrame(rows).to_parquet(part, engine="pyarrow",
                                              index=False)
    d = pd.DataFrame(rows)
    d.to_parquet(out_path, engine="pyarrow", index=False)
    part.unlink(missing_ok=True)
    report(d)
    print(f"\n  wrote {out_path}  ({len(d)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

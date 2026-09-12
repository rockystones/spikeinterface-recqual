"""The giant-event pass, for the subjects Rocky's pipeline never covered.

`scratch_rocky_events.py` builds two things from the NEV alone: CLAUDE.md's
first metrics layer (crossing rate, noise floor, amplitude, peak SNR, no sorter
involved) and a forensic classification of large-amplitude events by how many
*neighbouring* electrodes fire at the same instant. Both were only ever run on
Rocky.

The algorithm is subject-agnostic; only its I/O was Rocky-shaped. Rather than
rework a validated pipeline, this drives `event_stats_session` unchanged over
the other Blackrock subjects and writes the same shard layout, so the existing
figures read it without modification.

**Scope is Nigel and Fisk.** The classification rests on physical adjacency
between electrodes, so it needs a verified channel map. Oops, Picasso and Luigi
are TDT and their channel map is still unverified ([[tdt_channel_map]]), which
would make every adjacency claim about them unfounded.

Run from repo root:

    uv run python notebooks/scratch_giants_cohort.py --subject Nigel
    uv run python notebooks/scratch_giants_cohort.py --subject Fisk --n-jobs 4

See:
- docs/notes/giant_events.md
- docs/notes/snippet_noise_floor.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))

from scratch_rocky_events import event_stats_session  # noqa: E402
from scratch_rocky_spatial import parse_cmp  # noqa: E402

INV = REPO / "data" / "derived" / "inventory_all.parquet"
PROBE_DIR = REPO / "configs" / "probes"
SUBJECT_DIR = REPO / "configs" / "subjects"

# The Plexon automatic-output NEV. It carries the same event set as the
# unsorted original (verified on Rocky), so one read serves both layers.
CHAIN = "-01"


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def out_dirs(subject: str) -> dict[str, Path]:
    """Same shard layout Rocky uses, under the subject's own folder."""
    root = REPO / "data" / "derived" / subject.lower()
    return dict(
        root=root,
        elec_shards=root / "event_shards",
        giant_shards=root / "giant_shards",
        wf_shards=root / "giant_wf_shards",
        elec_out=root / "events_electrode.parquet",
        giant_out=root / "giant_events.parquet",
    )


def array_serials(subject: str, implant: str = "I1") -> dict[str, str]:
    """``array name -> serial`` from the subject registry, for ONE implant.

    Rocky's two implants reuse the Anterior/Posterior labels, so collapsing
    across implants lets a later implant overwrite an earlier one silently
    (see docs/notes/serial_resolution.md). Callers name the implant; the
    single-implant animals all live under "I1".
    """
    cfg = SUBJECT_DIR / f"{subject.lower()}.json"
    reg = json.loads(cfg.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for im in reg.get("implants", []):
        if im.get("implant") != implant:
            continue
        for arr, sn in (im.get("arrays") or {}).items():
            if sn:
                out[arr] = sn
    return out


def load_geometry(subject: str, arrays_seen: set[str]) -> dict[str, dict]:
    """``array -> {channel_id: (col, row)}``, resolved by serial.

    The inventory names Fisk's arrays by serial (`SN1498`) and Nigel's by
    anatomy (`Anterior`); the registry only knows the anatomical names. Both
    are matched against the serial, which is the one identifier the CMP
    filename actually carries.
    """
    serials = array_serials(subject)
    out: dict[str, dict] = {}
    for arr in sorted(arrays_seen):
        sn = serials.get(arr)
        if sn is None:
            # inventory used the serial as the array name, e.g. "SN1498"
            hit = [s for s in serials.values() if s.endswith(arr[-4:])]
            sn = hit[0] if hit else None
        if sn is None:
            print(f"  ! no serial for array {arr}")
            continue
        cmps = sorted(PROBE_DIR.glob(f"*{sn}*.cmp"))
        if not cmps:
            print(f"  ! no .cmp for {arr} (serial {sn})")
            continue
        cmp_df = parse_cmp(cmps[0])
        out[arr] = {int(r["channel_id"]): (int(r["col"]), int(r["row"]))
                    for _, r in cmp_df.iterrows()}
        print(f"  {arr:12s} serial {sn}  {cmps[0].name}  "
              f"{len(out[arr])} electrodes")
    return out


def build_worklist(subject: str) -> pd.DataFrame:
    """One row per session: the `-01` NEV, its array and its date."""
    inv = pd.read_parquet(INV)
    s = inv[(inv.subject == subject) & (inv.role == "snippets")
            & (inv.chain == CHAIN)].copy()
    s = s[s.array.notna() & s.date.notna()]
    # One file per (date, array): duplicates across volumes are the same
    # recording, and the census already established which copies are identical.
    s = s.sort_values("path").drop_duplicates(subset=["date", "array"])
    return s


def meta_of(row) -> dict:
    """Session identity carried onto every output row."""
    return dict(date=str(pd.Timestamp(row.date).date()), array=str(row.array),
                serial=None, headstage=getattr(row, "headstage", None),
                stem=str(row.stem))


def run_one(nev_path: str, meta: dict, geom: dict, dirs: dict[str, Path]) -> str:
    stem = f"{meta['date']}_{meta['array']}"
    pe = dirs["elec_shards"] / f"{stem}.parquet"
    pg = dirs["giant_shards"] / f"{stem}.parquet"
    pw = dirs["wf_shards"] / f"{stem}.npz"
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


def collect(dirs: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rebuild the aggregates from every shard on disk, never from this run.

    A scoped re-run that wrote its own results over the corpus summary has cost
    this project real data three times (docs/notes/sorter_operations.md §1).
    """
    def _cat(d: Path) -> pd.DataFrame:
        f = sorted(d.glob("*.parquet"))
        return (pd.concat([pd.read_parquet(p) for p in f], ignore_index=True)
                if f else pd.DataFrame())
    return _cat(dirs["elec_shards"]), _cat(dirs["giant_shards"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--n-jobs", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    subject = args.subject
    dirs = out_dirs(subject)
    dirs["root"].mkdir(parents=True, exist_ok=True)

    banner(f"Giant-event pass: {subject}")
    work = build_worklist(subject)
    if args.limit:
        work = work.head(args.limit)
    print(f"  sessions: {len(work)}")
    if not len(work):
        print("  nothing to do")
        return 1
    print(work.groupby("array").agg(n=("path", "size"), first=("date", "min"),
                                    last=("date", "max")).to_string())

    print("\n  geometry:")
    geom_by_array = load_geometry(subject, set(work.array.unique()))
    missing = set(work.array.unique()) - set(geom_by_array)
    if missing:
        print(f"  ! dropping arrays with no geometry: {sorted(missing)}")
        work = work[work.array.isin(geom_by_array)]

    from joblib import Parallel, delayed

    t0 = time.perf_counter()
    stats = Parallel(n_jobs=args.n_jobs, verbose=5)(
        delayed(run_one)(r.path, meta_of(r), geom_by_array[r.array], dirs)
        for r in work.itertuples()
    )
    errs = [s for s in stats if s.startswith("err")]
    print(f"\n  ok {sum(s.startswith('ok') for s in stats)}   "
          f"skip {sum(s == 'skip' for s in stats)}   err {len(errs)}")
    for s in pd.Series(errs).value_counts().head(5).items() if errs else []:
        print(f"    {s[1]:4d}  {s[0][:80]}")

    ed, gd = collect(dirs)
    if len(ed):
        ed.to_parquet(dirs["elec_out"], engine="pyarrow", index=False)
    if len(gd):
        gd.to_parquet(dirs["giant_out"], engine="pyarrow", index=False)

    banner("Done")
    print(f"  runtime {(time.perf_counter() - t0) / 60:.1f} min")
    print(f"  electrode rows {len(ed):,}  -> {dirs['elec_out'].name}")
    print(f"  giant rows     {len(gd):,}  -> {dirs['giant_out'].name}")
    if len(gd):
        print("\n  giant classes:")
        for k, c in gd["klass"].value_counts().items():
            print(f"    {c:8,}  {k}")
    if len(ed):
        print("\n  sorting-free layer, per array:")
        print(ed.groupby("array").agg(
            sessions=("date", "nunique"),
            crossing_hz=("crossing_rate_hz", "median"),
            noise_uv=("noise_uv", "median"),
            peak_snr=("peak_snr", "median"),
            frac_artifact=("frac_artifact", "median")).round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Bring Chase and the TDT subjects into the cohort table, on the cohort's gate.

`cohort_sessions.parquet` holds Fisk, Nigel and Rocky -- every subject whose
recordings are Blackrock NEVs with a Plexon `-01` automatic sort. Chase
(Plexon `.plx`) and the TDT subjects (Oops, Picasso) were analysed by their own
scripts with their own metric definitions and never entered it, so
`scratch_cohort_figures.py` -- which is already subject-generic -- has never
drawn them.

**The gate is the whole problem.** `chase_units.parquet` and
`tdt/offline_sort_units.parquet` carry a `passes_gate` column, but it means
`snr >= 4` and nothing else. The cohort's gate is four criteria: `snr >= 4`,
`n_spikes >= 50`, physiological peak-to-trough duration, and trough alignment.
Dropping the Chase and TDT rows in as they stand would give those subjects a
looser gate than Rocky's and inflate their yield and pass fraction against it.
So this re-reads the waveforms and calls the *same* `unit_metrics()` the
Blackrock path calls. It costs a pass over 20 `.plx` files and 10 TDT
block-arrays and it makes the comparison mean something.

Three things a reader should know before trusting the panels this feeds:

**The TDT sorting-based series is tiny.** Only 6 Oops blocks and 4 Picasso
blocks were ever offline-sorted (`.SortResult`); the online sortcode is an
accept flag, not a unit id ([[tdt_corpus]]). Every other TDT block contributes
a noise-floor row and nothing else, so C3 and the noise panel of C2 are real
while the yield panels are 5 and 4 points. That is the data, not a bug, and
the trend guard (n >= 8) correctly refuses to fit them.

**TDT noise is an electrode median, not a unit-weighted one.** The Blackrock
path takes `noise_uv.median()` over units, which weights an electrode by how
many units it carries. TDT blocks without a sort have no units at all, so
their noise can only be the median over electrodes. Rather than mix two
definitions inside one subject, every TDT row uses the electrode median. The
acquisition screen is relative to that array's own median, so a consistent
definition within the array is what matters.

**Array numbers are not anatomy.** Oops and Picasso have registered serials,
but which TDT store is anterior and which is posterior is a rig-wiring fact
that is not in the tank and has not been confirmed ([[tdt_channel_map]]).
Arrays are therefore named `Array1`/`Array2` and geometry resolves to the
96-electrode default rather than to a serial's mapfile -- `geometry_source`
reports `default` so nothing downstream mistakes it for a verified map.

Run from repo root:

    uv run python notebooks/scratch_cohort_extend.py [--part all] [--jobs 4]

Writes `data/derived/cohort/cohort_sessions_extra.parquet` and, unless
`--no-merge`, folds it into `cohort_sessions.parquet` and recomputes
`cohort_trends.parquet` over the union.

See:
- docs/notes/cohort_extension.md
- docs/notes/cohort_longitudinal.md
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
from scratch_cohort_io import array_geometry  # noqa: E402
from scratch_cohort_longitudinal import (  # noqa: E402
    SESSIONS_OUT,
    TRENDS_OUT,
    add_axes,
    trends,
)
from scratch_rocky_resort import (  # noqa: E402
    PLEXON_DROP_UNITS,
    align_on_trough,
    baseline_noise_uv,
    unit_metrics,
)

CHASE_ROOT = Path(r"C:\MyData\Monkeydata\Chase\chase.waveforms")
TDT_INV = REPO / "data" / "derived" / "tdt_inventory.parquet"
TDT_STATUS = REPO / "data" / "derived" / "tdt" / "offline_sort_status.parquet"
TDT_FREE = REPO / "data" / "derived" / "tdt" / "free_metrics_all.parquet"
OUT_DIR = REPO / "data" / "derived" / "cohort"
EXTRA_SESSIONS = OUT_DIR / "cohort_sessions_extra.parquet"
EXTRA_UNITS = OUT_DIR / "cohort_units_extra.parquet"

# Subjects this script owns. A merge replaces all of their rows, so a re-run
# never leaves half an old pass behind.
EXTEND_SUBJECTS = ("Chase", "Oops", "Picasso")

MV_TO_UV = 1000.0           # Plexon wf_gain is mV/count (docs/notes/chase_corpus.md)
TDT_OUTLIER_CODE = 31       # OpenSorter's reject bin, not a unit
IMPLANT = "I1"              # none of the three has a second implant


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === The cohort row, built exactly as the Blackrock path builds it ===
def session_row(units: pd.DataFrame, base: dict, subject: str, array: str,
                noise_override: float | None = None) -> dict:
    """Collapse one session's per-unit table into a `cohort_sessions` row.

    Mirrors `scratch_cohort_longitudinal.one_session` field for field. The only
    departure is `noise_override`, used for TDT where the noise floor has to be
    an electrode median for consistency with the unsorted blocks.

    Parameters
    ----------
    units : pandas.DataFrame
        One row per unit, from :func:`scratch_rocky_resort.unit_metrics`.
    base : dict
        Session identity carried onto the row.
    subject, array
        Used to look up electrode count.
    noise_override : float, optional
        Replaces the unit-weighted noise median when given.

    Returns
    -------
    dict
        A single `cohort_sessions` row.
    """
    geo = array_geometry(subject, array, IMPLANT)
    n_elec = geo["n_electrodes"]
    out = dict(base)
    out.update(
        n_candidates=float(len(units)),
        pass_fraction=float(units.pass_gate.mean()) if len(units) else np.nan,
        noise_med=(float(noise_override) if noise_override is not None
                   else float(units.noise_uv.median()) if len(units)
                   else np.nan),
        n_electrodes=float(n_elec),
        geometry_source=geo["source"],
    )
    gated = units[units.pass_gate] if len(units) else units
    if len(gated):
        out.update(
            n_units=float(len(gated)),
            n_elec_with_units=float(gated.channel_id.nunique()),
            units_per_electrode=len(gated) / n_elec,
            elec_coverage=gated.channel_id.nunique() / n_elec,
            amp_med=float(gated.amplitude_uv.median()),
            amp_p99=float(gated.amplitude_uv.quantile(0.99)),
            snr_med=float(gated.snr.median()),
            rate_med=float(gated.firing_rate_hz.median()),
        )
    elif len(units):
        # A session that sorted but passed nothing is a zero, not a gap.
        out.update(n_units=0.0, n_elec_with_units=0.0,
                   units_per_electrode=0.0, elec_coverage=0.0,
                   amp_med=np.nan, amp_p99=np.nan, snr_med=np.nan,
                   rate_med=np.nan)
    return out


# %%
# === Chase: Plexon .plx ===
def chase_one(job: dict) -> tuple[dict, list[dict]]:
    """Cohort row plus per-unit rows for one Chase `.plx`."""
    from neo.rawio import PlexonRawIO

    sys.path.insert(0, str(REPO / "notebooks"))
    from scratch_chase import plx_header

    path = Path(job["path"])
    base = dict(subject="Chase", implant=IMPLANT, array="Array1",
                stem=path.stem, headstage="plexon", run=None)
    try:
        hdr = plx_header(path)
        io = PlexonRawIO(filename=str(path))
        io.parse_header()
        sc = io.header["spike_channels"]
        dur = float(io.segment_t_stop(0, 0) - io.segment_t_start(0, 0))
        nbefore, sr = hdr["nbefore"], hdr["sr"]

        # Pass 1: pool every waveform on an electrode, sorted or not, so the
        # noise floor is a property of the electrode rather than of one unit.
        pooled: dict[int, list[np.ndarray]] = {}
        found: list[tuple[int, int, np.ndarray, np.ndarray]] = []
        for ui in range(len(sc)):
            ident = sc["id"][ui]
            ident = ident.decode() if isinstance(ident, bytes) else str(ident)
            ch_s, _, unit_s = ident.partition("#")
            ch, code = int(ch_s.replace("ch", "")), int(unit_s)
            w = io.get_spike_raw_waveforms(0, 0, ui)
            if w is None:
                continue
            w = np.asarray(w)
            if w.shape[0] == 0:
                continue
            w = w.reshape(w.shape[0], -1).astype(np.float32)
            w = w * float(sc["wf_gain"][ui]) * MV_TO_UV
            t = np.asarray(io.rescale_spike_timestamp(
                io.get_spike_timestamps(0, 0, ui), dtype="float64"))
            pooled.setdefault(ch, []).append(w)
            found.append((ch, code, w, t))
        if not found:
            return dict(**base, date=pd.NaT, error="no events"), []

        noise = {ch: baseline_noise_uv(np.concatenate(ws), nbefore)
                 for ch, ws in pooled.items()}

        rows: list[dict] = []
        for ch, code, w, t in found:
            if code in PLEXON_DROP_UNITS:
                continue
            n = min(w.shape[0], t.shape[0])
            if n == 0:
                continue
            m = unit_metrics(align_on_trough(w[:n], nbefore), t[:n],
                             noise[ch], sr, nbefore, dur)
            m.update(channel_id=int(ch), unit_id=int(code))
            rows.append(m)
        if not rows:
            return dict(**base, date=pd.NaT, error="no sorted units"), []

        u = pd.DataFrame(rows)
        base["date"] = pd.Timestamp(hdr["header_date"])
        row = session_row(u, base, "Chase", "Array1")
        for r in rows:
            r.update(subject="Chase", array="Array1", stem=path.stem,
                     date=base["date"])
        return row, rows
    except Exception as exc:  # noqa: BLE001
        return dict(**base, date=pd.NaT,
                    error=f"{type(exc).__name__}: {exc}"[:140]), []


def chase_jobs() -> list[dict]:
    if not CHASE_ROOT.exists():
        return []
    return [dict(path=str(p)) for p in sorted(CHASE_ROOT.glob("*.plx"))]


# %%
# === TDT: OpenSorter .SortResult ===
def tdt_one(job: dict) -> tuple[dict, list[dict]]:
    """Cohort row plus per-unit rows for one offline-sorted TDT block-array."""
    from scratch_tdt_io import channel_index, open_tank, read_channel

    store, arr = job["store"], job["array"]
    base = dict(subject=job["subject"], implant=IMPLANT, array=f"Array{arr}",
                stem=job["block"], headstage="tdt", run=None,
                date=pd.Timestamp(job["date"]))
    try:
        tev = next(Path(job["path"]).glob("*.tev"))
        io, meta = open_tank(tev, sortname=job["sort"])
        idx = channel_index(io)
        nbefore, dur = meta["nbefore"], meta["duration_s"]
        sr = float(meta.get("sr_by_store", {}).get(store) or meta["sr"])

        rows: list[dict] = []
        for (st, ch), units in sorted(idx.items()):
            if st != store:
                continue
            try:
                e = read_channel(io, meta, units)
            except Exception:  # noqa: BLE001 - one bad electrode is not fatal
                continue
            if e is None or not len(e["t"]):
                continue
            noise = baseline_noise_uv(e["wf"], nbefore)
            aligned = align_on_trough(e["wf"], nbefore)
            for code in np.unique(e["code"]):
                if code in (0, TDT_OUTLIER_CODE):
                    continue
                sel = e["code"] == code
                if not sel.any():
                    continue
                m = unit_metrics(aligned[sel], e["t"][sel], noise, sr,
                                 nbefore, dur)
                m.update(channel_id=int(ch), unit_id=int(code))
                rows.append(m)
        if not rows:
            return dict(**base, error="no sorted units"), []
        u = pd.DataFrame(rows)
        row = session_row(u, base, job["subject"], f"Array{arr}",
                          noise_override=job.get("noise_med"))
        for r in rows:
            r.update(subject=job["subject"], array=f"Array{arr}",
                     stem=job["block"], date=base["date"])
        return row, rows
    except Exception as exc:  # noqa: BLE001
        return dict(**base, error=f"{type(exc).__name__}: {exc}"[:140]), []


def _free_noise() -> pd.DataFrame:
    """Per block-array noise floor from the sorting-free layer."""
    if not TDT_FREE.exists():
        return pd.DataFrame()
    f = pd.read_parquet(TDT_FREE)
    if "error" in f.columns:
        f = f[f.error.isna()]
    keep = ["subject", "block", "date", "array", "noise_med", "duration_s"]
    return f[[c for c in keep if c in f.columns]].copy()


def tdt_jobs() -> list[dict]:
    """One job per offline-sorted TDT block-array, with its free-layer noise."""
    if not (TDT_STATUS.exists() and TDT_INV.exists()):
        return []
    st = pd.read_parquet(TDT_STATUS)
    st = st[(st.status == "ok") & st.subject.isin(EXTEND_SUBJECTS)]
    inv = pd.read_parquet(TDT_INV)
    path_of = (inv.groupby(["subject", "block"]).path.first().to_dict())
    noise = _free_noise()
    nmap = {}
    if len(noise):
        nmap = {(r.subject, r.block, int(r.array)): r.noise_med
                for r in noise.itertuples() if pd.notna(r.array)}

    jobs: list[dict] = []
    for r in st.itertuples():
        # array_of("eNe2") -> 2. A store with no array number is not an array.
        arr = int(str(r.store)[-1]) if str(r.store)[-1].isdigit() else None
        p = path_of.get((r.subject, r.block))
        if arr is None or p is None:
            continue
        jobs.append(dict(subject=r.subject, block=r.block, date=r.date,
                         sort=r.sort, store=r.store, array=arr, path=p,
                         noise_med=nmap.get((r.subject, r.block, arr))))
    return jobs


def tdt_free_only_rows(sorted_keys: set[tuple[str, str, int]]) -> list[dict]:
    """Noise-floor-only rows for TDT blocks that were never offline-sorted.

    These carry no unit metrics, so they contribute to the acquisition screen
    and the noise panel and to nothing else. Without them the TDT noise series
    would be six sessions instead of 251.
    """
    noise = _free_noise()
    if not len(noise):
        return []
    rows: list[dict] = []
    for r in noise.itertuples():
        if pd.isna(r.array):
            continue
        arr = int(r.array)
        if (r.subject, r.block, arr) in sorted_keys:
            continue
        geo = array_geometry(r.subject, f"Array{arr}", IMPLANT)
        rows.append(dict(
            subject=r.subject, implant=IMPLANT, array=f"Array{arr}",
            stem=r.block, headstage="tdt", run=None,
            date=pd.Timestamp(r.date), noise_med=float(r.noise_med),
            n_electrodes=float(geo["n_electrodes"]),
            geometry_source=geo["source"],
        ))
    return rows


# %%
# === Merge ===
def merge(extra: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fold the extra rows into `cohort_sessions` and refit every trend.

    The axes and the acquisition screen are recomputed over the union rather
    than carried across, so `noise_baseline`, `high_noise` and
    `days_since_first` mean the same thing for every subject in the file.
    """
    base = pd.read_parquet(SESSIONS_OUT)
    # Drop any previous pass of these subjects so a re-run is idempotent.
    base = base[~base.subject.isin(EXTEND_SUBJECTS)]
    missing = [c for c in base.columns if c not in extra.columns]
    for c in missing:
        extra[c] = np.nan
    union = pd.concat([base, extra[list(base.columns)]], ignore_index=True)
    union["date"] = pd.to_datetime(union["date"])
    # add_axes rebuilds implant_age_days / days_since_first / high_noise, so
    # the stale copies coming in from `base` are overwritten, not merged.
    for c in ("implant_age_days", "days_since_first", "age_axis",
              "noise_baseline", "high_noise"):
        if c in union.columns:
            union = union.drop(columns=[c])
    union = add_axes(union)
    ok = union[union.error.isna()] if "error" in union else union
    return union, trends(ok)


def report(extra: pd.DataFrame, units: pd.DataFrame) -> None:
    banner("1. Rows added, by subject and array")
    ok = extra[extra.get("error").isna()] if "error" in extra else extra
    t = ok.groupby(["subject", "array"]).agg(
        n=("date", "size"), first=("date", "min"), last=("date", "max"),
        sorted_n=("n_units", "count"),
        geometry=("geometry_source", "first"))
    print(t.to_string())
    if "error" in extra and extra.error.notna().any():
        e = extra[extra.error.notna()]
        print(f"\n  failed: {len(e)}")
        print(e.error.astype(str).str.slice(0, 70).value_counts()
              .head(5).to_string())

    banner("2. What the cohort gate rejects, and why")
    print("  The Chase/TDT tables gated on SNR alone. This is the four-part")
    print("  cohort gate, so the extra rejections are the price of parity.\n")
    if len(units):
        for sub, g in units.groupby("subject"):
            reasons = (g[~g.pass_gate].reject_reason
                       .str.split(";").explode().value_counts())
            print(f"  {sub}: {len(g)} units, {int(g.pass_gate.sum())} pass "
                  f"({g.pass_gate.mean():.1%})")
            for k, v in reasons.head(4).items():
                print(f"      {k:28s} {v:6d}")

    banner("3. Sorting-based coverage")
    print("  A yield panel needs sorted sessions; a noise panel does not.\n")
    for (sub, arr), g in ok.groupby(["subject", "array"]):
        n_sorted = int(g.n_units.notna().sum()) if "n_units" in g else 0
        flag = "" if n_sorted >= 8 else "   <- below the n>=8 trend threshold"
        print(f"  {sub:8s} {arr:8s} noise rows {len(g):4d}   "
              f"sorted rows {n_sorted:3d}{flag}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="all",
                    choices=("all", "chase", "tdt"))
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--no-merge", action="store_true")
    ap.add_argument("--merge-only", action="store_true",
                    help="re-merge the saved extra table without re-reading "
                         "any raw file")
    args = ap.parse_args()

    if args.merge_only:
        extra = pd.read_parquet(EXTRA_SESSIONS)
        union, tr = merge(extra)
        union.to_parquet(SESSIONS_OUT, engine="pyarrow", index=False)
        tr.to_parquet(TRENDS_OUT, engine="pyarrow", index=False)
        banner("Re-merged from the saved extra table")
        print(union.groupby(["subject", "implant", "array"]).size().to_string())
        print(f"\n  wrote {SESSIONS_OUT.relative_to(REPO)}  ({len(union)} rows)")
        print(f"  wrote {TRENDS_OUT.relative_to(REPO)}  ({len(tr)} rows)")
        return 0

    rows: list[dict] = []
    unit_rows: list[dict] = []

    if args.part in ("all", "chase"):
        jobs = chase_jobs()
        banner(f"Chase -- {len(jobs)} .plx on the cohort gate")
        if args.jobs > 1 and jobs:
            with ProcessPoolExecutor(max_workers=args.jobs) as ex:
                for r, us in ex.map(chase_one, jobs, chunksize=1):
                    rows.append(r)
                    unit_rows.extend(us)
        else:
            for i, j in enumerate(jobs, 1):
                r, us = chase_one(j)
                rows.append(r)
                unit_rows.extend(us)
                print(f"    [{i}/{len(jobs)}] {Path(j['path']).stem}"
                      f"{'  ERROR ' + r['error'] if 'error' in r else ''}",
                      flush=True)

    if args.part in ("all", "tdt"):
        jobs = tdt_jobs()
        banner(f"TDT -- {len(jobs)} offline-sorted block-arrays")
        for i, j in enumerate(jobs, 1):
            r, us = tdt_one(j)
            rows.append(r)
            unit_rows.extend(us)
            print(f"    [{i}/{len(jobs)}] {j['subject']} {j['block']} "
                  f"{j['store']}"
                  f"{'  ERROR ' + r['error'] if 'error' in r else ''}",
                  flush=True)
        keys = {(j["subject"], j["block"], j["array"]) for j in jobs}
        free = tdt_free_only_rows(keys)
        print(f"  + {len(free)} noise-only rows from unsorted blocks")
        rows.extend(free)

    extra = pd.DataFrame(rows)
    if not len(extra):
        print("  nothing to add")
        return 1
    extra["date"] = pd.to_datetime(extra["date"])
    units = pd.DataFrame(unit_rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    extra.to_parquet(EXTRA_SESSIONS, engine="pyarrow", index=False)
    if len(units):
        units.to_parquet(EXTRA_UNITS, engine="pyarrow", index=False)
    report(extra, units)

    if not args.no_merge:
        union, tr = merge(extra)
        union.to_parquet(SESSIONS_OUT, engine="pyarrow", index=False)
        tr.to_parquet(TRENDS_OUT, engine="pyarrow", index=False)
        banner("4. Merged cohort table")
        print(union.groupby(["subject", "implant", "array"]).size()
              .to_string())
        print(f"\n  wrote {SESSIONS_OUT.relative_to(REPO)}  "
              f"({len(union)} rows)")
        print(f"  wrote {TRENDS_OUT.relative_to(REPO)}  ({len(tr)} rows)")
    print(f"  wrote {EXTRA_SESSIONS.relative_to(REPO)}  ({len(extra)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

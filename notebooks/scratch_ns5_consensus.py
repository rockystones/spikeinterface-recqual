"""The consensus layer: re-run the pool with outputs kept, agree, then purge.

The ns5 resort ran 238 stems x 4 sorters but kept only summary rows -- the
spike trains were scratch, so CLAUDE.md's metrics layer 3 (the agreement
*structure*, longitudinally) was never computable. This driver closes that:

- an **era-spanning subset** per (subject, implant, array), chosen from stems
  the resort already completed on all four sorters, so every re-run is known
  feasible;
- `run_session` from `scratch_ns5_resort` does the sorting exactly as before
  (same filter, same params, same docker routing for Kilosort4);
- immediately per stem: each sorting is saved compactly as `numpy_folder`
  (MATLAB-safe, CLAUDE.md), `compare_multiple_sorters` produces the pairwise
  matches and the consensus ladder, a per-stem shard is written, and the
  heavy sorter scratch is purged. An interrupted run resumes from shards.

Deliberately **bypasses the resort's shard cache** -- that cache exists to
skip completed stems, which are exactly the ones being re-run here -- and
writes nothing into the resort's shard directory.

Run from repo root (sequential; hours -- run in the background):

    uv run python notebooks/scratch_ns5_consensus.py --per-array 6

See docs/notes/multisorter_agreement.md.
"""

from __future__ import annotations

import argparse
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))

from scratch_cohort_io import banner  # noqa: E402
from scratch_ns5_resort import (  # noqa: E402
    INV,
    build_worklist,
    purge_work,
    run_session,
    work_root,
)

SORTERS = ["mountainsort5", "kilosort4", "spykingcircus2", "tridesclous2"]
OUT = REPO / "data" / "derived" / "ns5" / "consensus"
SHARDS = OUT / "shards"
SORTINGS = OUT / "sortings"
SUMMARY = REPO / "data" / "derived" / "ns5" / "ns5_sorters.parquet"


# %%
def pick_stems(per_array: int) -> pd.DataFrame:
    """An even date-spread per (subject, implant, array) of proven stems."""
    d = pd.read_parquet(SUMMARY)
    ok = d[d.error.isna()]
    full = (ok.groupby(["subject", "implant", "array", "stem", "date"],
                       observed=True).sorter.nunique().reset_index())
    full = full[full.sorter == len(SORTERS)]
    rows = []
    for _, g in full.groupby(["subject", "implant", "array"], observed=True):
        g = g.sort_values("date").reset_index(drop=True)
        take = np.linspace(0, len(g) - 1,
                           min(per_array, len(g))).round().astype(int)
        rows.append(g.iloc[sorted(set(take))])
    return pd.concat(rows, ignore_index=True)


def load_sorting(job: dict, sorter: str):
    """Read one sorter's persisted output, resolving paths on its own drive."""
    from spikeinterface.sorters import read_sorter_folder

    folder = work_root(job["ns5"]) / f"{job['stem']}__{sorter}"
    if not folder.exists():
        return None
    drive = Path(job["ns5"]).drive
    prev = os.getcwd()
    try:
        if drive and Path(drive + "\\").exists():
            os.chdir(drive + "\\")
        return read_sorter_folder(folder, register_recording=False)
    except Exception as exc:  # noqa: BLE001
        print(f"    ! load {sorter}: {type(exc).__name__}: {exc}")
        return None
    finally:
        os.chdir(prev)


def agree_one(job: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pairwise agreement and consensus ladder from the kept work folders."""
    from spikeinterface.comparison import compare_multiple_sorters

    sortings, names = [], []
    for s in SORTERS:
        so = load_sorting(job, s)
        if so is None:
            continue
        dest = SORTINGS / job["stem"] / s
        if not dest.exists():
            try:
                so.save(folder=dest, format="numpy_folder")
            except Exception as exc:  # noqa: BLE001
                print(f"    ! save {s}: {type(exc).__name__}: {exc}")
        sortings.append(so)
        names.append(s)
    if len(sortings) < 2:
        return pd.DataFrame(), pd.DataFrame()

    comp = compare_multiple_sorters(sortings, name_list=names,
                                    delta_time=0.4, match_score=0.5,
                                    verbose=False)
    meta = {k: job[k] for k in ("subject", "implant", "array", "date", "stem")}
    pairs = []
    for (a, b), c in comp.comparisons.items():
        m12, m21 = c.hungarian_match_12, c.hungarian_match_21
        pairs.append(dict(**meta, a=str(a), b=str(b),
                          n_a=len(m12), n_b=len(m21),
                          frac_a_matched=float((m12 != -1).mean())
                          if len(m12) else np.nan,
                          frac_b_matched=float((m21 != -1).mean())
                          if len(m21) else np.nan))
    ladder = [dict(**meta, min_agreement=1,
                   n_units=int(sum(len(s.unit_ids) for s in sortings)),
                   n_sorters=len(names))]
    for k in range(2, len(names) + 1):
        agr = comp.get_agreement_sorting(minimum_agreement_count=k)
        ladder.append(dict(**meta, min_agreement=k,
                           n_units=int(len(agr.unit_ids)),
                           n_sorters=len(names)))
    return pd.DataFrame(pairs), pd.DataFrame(ladder)


# %%
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-array", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0,
                    help="stop after N stems (0 = all selected)")
    ap.add_argument("--timeout", type=float, default=2400.0)
    args = ap.parse_args()

    SHARDS.mkdir(parents=True, exist_ok=True)
    SORTINGS.mkdir(parents=True, exist_ok=True)

    banner("Consensus re-run: selection")
    sel = pick_stems(args.per_array)
    print(sel.groupby(["subject", "implant", "array"], observed=True)
             .agg(n=("stem", "size"), d0=("date", "min"), d1=("date", "max"))
             .to_string())

    inv = pd.read_parquet(INV)
    jobs = {j["stem"]: j for j in build_worklist(inv)}
    todo = []
    for stem in sel.stem:
        j = jobs.get(stem)
        if j is None:
            print(f"  ! {stem}: not in worklist, skipped")
            continue
        if not Path(j["ns5"]).exists():
            print(f"  ! {stem}: recording offline "
                  f"({Path(j['ns5']).drive}), skipped")
            continue
        todo.append(j)
    print(f"\n  runnable: {len(todo)} stems x {len(SORTERS)} sorters")

    if args.limit:
        todo = todo[: args.limit]

    for i, job in enumerate(todo, 1):
        shard = SHARDS / f"{job['stem']}.parquet"
        if shard.exists():
            print(f"  [{i}/{len(todo)}] done    {job['stem'][:52]}")
            continue
        print(f"  [{i}/{len(todo)}] sorting {job['stem'][:52]}", flush=True)
        try:
            runs = run_session(job, SORTERS, docker_mode="auto",
                               timeout_s=args.timeout)
            pairs, ladder = agree_one(job)
        except Exception as exc:  # noqa: BLE001
            print(f"    ! {type(exc).__name__}: {exc}")
            continue
        finally:
            purge_work(job)
        n_ok = int(runs.error.isna().sum()) if "error" in runs else 0
        print(f"      sorters ok {n_ok}/{len(SORTERS)}; "
              f"pairs {len(pairs)}, ladder {list(ladder.n_units) if len(ladder) else []}")
        runs["kind"] = "run"
        pairs["kind"] = "pair"
        ladder["kind"] = "ladder"
        pd.concat([runs, pairs, ladder], ignore_index=True).to_parquet(
            shard, index=False)

    banner("Aggregate")
    frames = [pd.read_parquet(p) for p in sorted(SHARDS.glob("*.parquet"))]
    if not frames:
        print("  nothing to aggregate")
        return 0
    alld = pd.concat(frames, ignore_index=True)
    pairs = alld[alld.kind == "pair"].dropna(axis=1, how="all")
    ladder = alld[alld.kind == "ladder"].dropna(axis=1, how="all")
    pairs.to_parquet(OUT / "consensus_pairs.parquet", index=False)
    ladder.to_parquet(OUT / "consensus_ladder.parquet", index=False)
    print(f"  stems with agreement: {pairs.stem.nunique()}")

    # symmetric mean agreement per stem, then the longitudinal question
    sym = pd.concat([
        pairs.rename(columns={"frac_a_matched": "frac"})[
            ["subject", "implant", "array", "date", "stem", "frac"]],
        pairs.rename(columns={"frac_b_matched": "frac"})[
            ["subject", "implant", "array", "date", "stem", "frac"]]])
    per = (sym.groupby(["subject", "implant", "array", "date", "stem"],
                       observed=True).frac.mean()
              .reset_index(name="mean_agreement"))
    per.to_parquet(OUT / "consensus_per_stem.parquet", index=False)
    print(per.groupby(["subject", "implant", "array"], observed=True)
             .mean_agreement.agg(["count", "median"]).round(3).to_string())

    from scipy.stats import spearmanr
    print("\n  agreement vs date:")
    for (sub, imp, arr), g in per.groupby(["subject", "implant", "array"],
                                          observed=True):
        if len(g) < 5:
            continue
        age = pd.to_datetime(g.date).map(pd.Timestamp.toordinal)
        rho, p = spearmanr(age, g.mean_agreement)
        print(f"    {sub:6s} {imp} {arr:10s} rho={rho:+.3f} p={p:.3g} "
              f"(n={len(g)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

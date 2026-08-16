"""Repair one mis-dated session across every derived table.

`Rocky_Anterior_2023-08-011_...` was read by the original parser as
**2023-08-01**. It is **2023-08-11**, on three independent grounds:

1. The NEV basic header's TimeOrigin reads 2023-08-11 16:22, a Friday.
2. 08-11 fills the only gap in an otherwise weekly series (07-27, 08-04, --,
   08-17, 08-24); the 1st would put three sessions in eight days.
3. **The Posterior array's file for the same session is correctly named
   `2023-08-11`.** Anterior and Posterior are recorded on the same day.

Point 3 also means the error had a cost beyond the label: the two arrays of one
session sat on different dates, so that session was never paired. Fixing the
date restores the pair.

Every affected row is Anterior, and every existing 2023-08-11 row is Posterior,
so the relabel cannot collide with real data. Verified before writing.

Dry run by default; pass ``--apply`` to write. Originals are copied to
``data/derived/_backup_datefix/`` rather than to ``.bak``, which already holds
the pre-channel-id-rename state and must not be clobbered.

    uv run python notebooks/scratch_fix_session_date.py
    uv run python notebooks/scratch_fix_session_date.py --apply

See:
- docs/notes/monkey_corpus.md
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
DERIVED = REPO / "data" / "derived"
BACKUP = DERIVED / "_backup_datefix"

WRONG = pd.Timestamp("2023-08-01")
RIGHT = pd.Timestamp("2023-08-11")
ONLY_ARRAY = "Anterior"          # the guard: nothing else may be touched

# Tables cheap enough to rebuild from their source. Migrating them instead would
# leave the generating script still emitting the wrong date, so the error would
# come back on the next run. `monkey_inventory` rebuilds in about a minute from
# `scratch_monkey_inventory.py`, which now carries the correction itself.
REGENERATE = {"monkey_inventory.parquet"}


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def date_columns(df: pd.DataFrame) -> list[str]:
    """Columns holding this session's date, whatever they are named."""
    return [c for c in df.columns
            if str(c).lower() in ("date", "date_dt", "date_file")]


def identity_columns(df: pd.DataFrame) -> list[str]:
    """Columns that, with the date, identify a recording.

    `subject` matters: `cohort_index` spans six animals, and Nigel also has an
    Anterior array with a real 2023-08-11 session. Keying a collision test on
    the array alone reads that as a clash with Rocky's.
    """
    want = ("subject", "array", "region")
    return [str(c) for c in df.columns if str(c).lower() in want]


# %%
# === The check that makes the relabel safe ===
def inspect(path: Path) -> dict | None:
    """Rows to change in one table, and whether changing them is safe.

    Unsafe means either the rows are not all `ONLY_ARRAY`, or a row for the
    corrected date already exists on the same array -- which would mean the
    relabel merges two distinct sessions.
    """
    try:
        df = pd.read_parquet(path)
    except (OSError, ValueError):
        return None
    flat = df.reset_index()
    cols = date_columns(flat)
    if not cols:
        return None
    hit = pd.Series(False, index=flat.index)
    for c in cols:
        hit |= pd.to_datetime(flat[c], errors="coerce").dt.normalize() == WRONG
    if not hit.any():
        return None

    ident = identity_columns(flat)
    keys = (set(map(tuple, flat.loc[hit, ident].astype(str).to_numpy()))
            if ident else set())
    arrays = {k[-1] for k in keys} if ident else set()

    already = pd.Series(False, index=flat.index)
    for c in cols:
        already |= (pd.to_datetime(flat[c], errors="coerce").dt.normalize()
                    == RIGHT)
    other = (set(map(tuple, flat.loc[already, ident].astype(str).to_numpy()))
             if ident else set())
    collide = bool(keys & other)
    return dict(path=path, n=int(hit.sum()), cols=cols, arrays=arrays,
                keys=keys, safe=(not collide)
                and (not arrays or arrays == {ONLY_ARRAY}), collide=collide)


def apply_to(path: Path, cols: list[str]) -> int:
    """Rewrite one table with the date corrected. Index is preserved."""
    df = pd.read_parquet(path)
    named = df.index.names not in ([None], [])
    flat = df.reset_index() if named else df.copy()
    n = 0
    for c in cols:
        if c not in flat.columns:
            continue
        col = pd.to_datetime(flat[c], errors="coerce")
        mask = col.dt.normalize() == WRONG
        if not mask.any():
            continue
        n += int(mask.sum())
        # Preserve any time-of-day and the column's original dtype. Test the
        # dtype rather than compare to `object`: several of these columns are
        # arrow-backed strings, which are neither `object` nor datetime, and
        # assigning a Timestamp into one raises.
        shifted = col + (RIGHT - WRONG)
        if pd.api.types.is_datetime64_any_dtype(flat[c]):
            flat.loc[mask, c] = shifted[mask]
        else:
            flat.loc[mask, c] = shifted[mask].dt.strftime("%Y-%m-%d")
    if named:
        flat = flat.set_index(list(df.index.names))
    flat.to_parquet(path, engine="pyarrow")
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the changes")
    args = ap.parse_args()

    banner(f"Relabel {WRONG.date()} -> {RIGHT.date()} ({ONLY_ARRAY} only)")
    jobs = [j for j in (inspect(p) for p in sorted(DERIVED.rglob("*.parquet"))
                        if ".bak" not in p.name
                        and p.name not in REGENERATE
                        and BACKUP not in p.parents) if j]
    if REGENERATE:
        print(f"  regenerated rather than migrated: {sorted(REGENERATE)}\n")
    shards = sorted(DERIVED.rglob(f"{WRONG.date()}_*.parquet"))

    for j in jobs:
        flag = "ok " if j["safe"] else "!! "
        why = "" if j["safe"] else (
            "  <- would MERGE with an existing row" if j["collide"]
            else f"  <- touches {j['arrays']}, not just {ONLY_ARRAY}")
        print(f"  {flag}{str(j['path'].relative_to(DERIVED)):52s} "
              f"{j['n']:6d} rows  {j['cols']}{why}")
    print(f"\n  shard files to rename : {len(shards)}")
    for s in shards:
        print(f"      {s.relative_to(DERIVED)}  ->  "
              f"{s.name.replace(str(WRONG.date()), str(RIGHT.date()))}")

    unsafe = [j for j in jobs if not j["safe"]]
    if unsafe:
        print(f"\n  ABORT: {len(unsafe)} table(s) failed the safety check.")
        return 1
    if not args.apply:
        print("\n  dry run -- pass --apply to write")
        return 0

    BACKUP.mkdir(parents=True, exist_ok=True)
    total = 0
    for j in jobs:
        rel = j["path"].relative_to(DERIVED)
        dest = BACKUP / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(j["path"], dest)
        total += apply_to(j["path"], j["cols"])
    for s in shards:
        s.rename(s.with_name(s.name.replace(str(WRONG.date()),
                                            str(RIGHT.date()))))
    print(f"\n  rewrote {len(jobs)} tables, {total} rows")
    print(f"  renamed {len(shards)} shard files")
    print(f"  originals copied to {BACKUP.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

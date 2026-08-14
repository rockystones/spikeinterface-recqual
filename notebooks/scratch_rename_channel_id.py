"""One-shot migration to the settled channel/electrode vocabulary.

Decided 2026-08-14: **channel id** indexes recording files, **electrode id**
indexes physical shanks. That is Blackrock's own usage (LB-0023 Rev 8), and it
makes the project's existing `electrode_id` column actively wrong -- it holds
`(bank - 'A') * 32 + pin`, which is a channel id.

| before | after | meaning |
|---|---|---|
| `electrode_id` | `channel_id` | index in the recording file, 1..96 |
| `electrode_num` (channel_map only) | `electrode_id` | physical shank, the CMP `elecNN` label |
| `channel_id` (threshold_crossings only) | `si_channel_id` | SpikeInterface's channel-id string |
| `channel_index` | unchanged | 0-based position in a recording's channel list |

Values do not change, only names, so the derived tables are migrated by
renaming columns rather than recomputed -- seconds instead of an hour, and
bit-identical data. Run once:

    uv run python notebooks/scratch_rename_channel_id.py [--apply]

Without ``--apply`` it reports what would change and touches nothing.

See:
- docs/notes/channel_mapping.md
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
DERIVED = REPO / "data" / "derived"

# Order matters: free the target name before renaming onto it.
RENAMES = [("channel_id", "si_channel_id"),
           ("electrode_id", "channel_id"),
           ("electrode_num", "electrode_id")]


def banner(t: str) -> None:
    print()
    print("=" * 74)
    print(t)
    print("=" * 74)


def plan_for(df: pd.DataFrame) -> dict[str, str]:
    """Which renames apply to one table, respecting the ordering.

    The ``channel_id -> si_channel_id`` step fires only when the existing
    column is a string: SpikeInterface's channel ids are strings, whereas a
    table that already carries an integer ``channel_id`` is already using the
    settled name and must be left alone.
    """
    out, current = {}, list(df.columns)
    for old, new in RENAMES:
        if old not in current or new in current:
            continue
        if old == "channel_id" and pd.api.types.is_integer_dtype(df[old]):
            continue
        out[old] = new
        current[current.index(old)] = new
    return out


def migrate_frame(path: Path, apply: bool) -> str:
    df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
    mapping = plan_for(df)
    if not mapping:
        return ""
    if apply:
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        df = df.rename(columns=mapping)
        if path.suffix == ".parquet":
            df.to_parquet(path, engine="pyarrow", index=False)
        else:
            df.to_csv(path, index=False)
    return ", ".join(f"{k} -> {v}" for k, v in mapping.items())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    # channel_map is excluded deliberately: it is cheap to regenerate from
    # scratch_channel_map.py, which also drops the deprecated electrode_id
    # alias -- something a column rename cannot express.
    targets = [p for p in sorted(DERIVED.rglob("*.parquet"))
               if "shard" not in str(p) and p.name != "channel_map.parquet"]

    banner(f"{'Applying' if args.apply else 'Dry run:'} column migration "
           f"over {len(targets)} tables")
    n = 0
    for p in targets:
        msg = migrate_frame(p, args.apply)
        if msg:
            n += 1
            print(f"  {str(p.relative_to(REPO)):58s} {msg}")
    print(f"\n  {n} tables {'migrated' if args.apply else 'would change'}; "
          f"{len(targets) - n} untouched")
    if args.apply:
        print("  originals kept alongside as .bak")

    banner("Verification")
    for p in targets[:200]:
        df = pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p)
        bad = [c for c in df.columns if c == "electrode_num"]
        if bad:
            print(f"  LEFTOVER {p.name}: {bad}")
    ch = [p for p in targets if "channel_id" in
          (pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p)).columns]
    print(f"  tables now carrying channel_id: {len(ch)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

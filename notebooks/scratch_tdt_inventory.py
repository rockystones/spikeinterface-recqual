"""Inventory the Oops and Picasso TDT corpus, one row per (block, array).

The Blackrock inventory (`scratch_monkey_inventory.py`) had to *discover* its
variant vocabulary because the filename suffix chains were undeclared. TDT has
no such problem -- a block is a directory and its stores are declared in the
Tbk -- but it brings two of its own:

**The date is in three places and they disagree.** The folder name, the file
stem inside it, and the tank's own clock. `Picasso_2016_01_14-1` holds files
stamped `Picasso_2015_01_14`, and the estate census flagged the pair without
being able to say which was right. The tsq start mark is a Unix timestamp
written at record time, so it settles it: 2016. The folder is right and the
stem is a New Year typo -- nine blocks carry that class of error.

**The tank clock is UTC, not local time**, which is why it is corroboration and
not the session date. Two blocks would otherwise be re-dated to the following
day from a 00:03 and a 00:04 start. Read as UTC against a US Eastern lab those
are 19:03 and 19:04 the previous evening, which is the modal recording hour of
the whole corpus (40 of 177 blocks), and both folder dates become correct. Read
as local time they are the only two past-midnight sessions in two years, and
the corpus would contain no session before 13:00. The same ruling was already
made for the Blackrock NSP clock: prefer a clock offset over past-midnight
recording. So `date` is the folder date and `utc_date` is kept beside it.

**"Array" is a store-name suffix, not a directory.** Each block carries eNe1
and eNe2 -- two 96-channel arrays recorded simultaneously into one tank. That
is the same two-array shape as Nigel and Rocky, but it lives inside the file
instead of beside it, so the row granularity here is (block, array).

Everything is read from the Tbk and tsq directly. Neither needs the tev
memory-mapped, which is what makes a 177-block pass take seconds instead of
the ~40 minutes a full `parse_header` sweep would cost.

Run from repo root:

    uv run python notebooks/scratch_tdt_inventory.py

Writes `data/derived/tdt_inventory.parquet`.

See:
- docs/notes/tdt_corpus.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from neo.rawio.tdtrawio import EVTYPE_SNIP, tsq_dtype

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_tdt_io import (  # noqa: E402
    MIN_DURATION_S,
    TDT_ROOTS,
    array_of,
    broadband_store,
    find_blocks,
    lfp_stores,
    sort_names,
    store_table,
    subject_of,
    tank_clock,
)

OUT = REPO / "data" / "derived" / "tdt_inventory.parquet"

# The tank clock is UTC; this converts it to the lab's wall clock. It is only
# load-bearing for Luigi, whose `Block-N` directories carry no date at all --
# Oops and Picasso take their date from the folder name and use the clock only
# as corroboration. DST is handled by the zone, not by a fixed offset.
LAB_TZ = ZoneInfo("America/New_York")

# A folder or stem date, tolerating the zero-padded-to-three typo that appears
# in `Oops_2015_07_010-1` and the run suffix that follows it.
DATE_RE = re.compile(r"(\d{4})[_-](\d{1,3})[_-](\d{1,3})")
# Trailing `-N` on the folder is the within-day record number; a bare `A`/`B`
# before it (with or without a separator) is the within-day session letter.
RUN_RE = re.compile(r"-(\d+)$")
LETTER_RE = re.compile(r"_?([AB])(?:-\d+)?$")


def parse_date(text: str) -> str | None:
    """Best-effort YYYY-MM-DD from a folder or file stem, or None."""
    m = DATE_RE.search(text)
    if not m:
        return None
    y, mo, d = (int(g) for g in m.groups())
    # `07_010` means the 10th: a stray leading zero, not day 10 of month 70.
    if d > 31 and d % 10 <= 31:
        d = d % 100
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}"


def block_labels(block: str) -> dict:
    """Session letter and run number carried by the block directory name."""
    lm = LETTER_RE.search(block)
    rm = RUN_RE.search(block)
    return dict(
        letter=lm.group(1) if lm else "",
        run=int(rm.group(1)) if rm else 1,
    )


# %%
# === One block ===
def scan_block(tev_str: str) -> list[dict]:
    """Rows for one block, one per snippet store (i.e. per array).

    Counts events straight out of the tsq index. The tsq holds one record per
    event with its store name, channel and sortcode, so the whole per-array
    event census is a few boolean masks over a single `fromfile`.
    """
    tev = Path(tev_str)
    block = tev.parent
    subject = subject_of(tev) or "?"
    root = TDT_ROOTS.get(subject)
    base = dict(
        subject=subject,
        block=block.name,
        stem=tev.stem,
        # Absolute, because the three subjects no longer share a root: Luigi
        # lives on C: and the others on D:.
        path=str(block),
        rel=str(block.relative_to(root)) if root else str(block),
        **block_labels(block.name),
    )
    try:
        stores = store_table(tev.with_suffix(".Tbk"))
        start, dur = tank_clock(tev.with_suffix(".tsq"))
        tsq = np.fromfile(tev.with_suffix(".tsq"), dtype=tsq_dtype)
    except Exception as exc:  # noqa: BLE001
        return [dict(**base, error=f"{type(exc).__name__}: {exc}"[:120])]

    folder_date = parse_date(block.name)
    stem_date = parse_date(tev.stem)
    clock_date = start.strftime("%Y-%m-%d") if start else None
    # Luigi's `Block-N` directories carry no date at all, so the clock is the
    # only source -- and since it is UTC, an evening session would be filed a
    # day late. Convert to the lab's wall clock before using it as the date.
    local_date = None
    if start is not None:
        local = start.replace(tzinfo=dt.timezone.utc).astimezone(LAB_TZ)
        local_date = local.strftime("%Y-%m-%d")
    n_sev = len(list(block.glob("*_Raw*_ch*.sev")))
    sorts = sort_names(block)

    snip = tsq["evtype"] == EVTYPE_SNIP
    rows: list[dict] = []
    for store, info in sorted(stores.items()):
        if info["ev_type"] != EVTYPE_SNIP:
            continue
        sel = snip & (tsq["evname"] == store.encode())
        chans = tsq["channel"][sel]
        codes = tsq["sortcode"][sel]
        n = int(sel.sum())
        arr = array_of(store)
        rows.append(dict(
            **base,
            array=arr,
            store=store,
            # Folder date is the session date where one exists; otherwise the
            # UTC clock converted to the lab's wall clock.
            date=folder_date or local_date,
            date_source="folder" if folder_date else
            ("clock_local" if local_date else "none"),
            folder_date=folder_date,
            stem_date=stem_date,
            utc_date=clock_date,
            local_date=local_date,
            date_conflict=bool(
                folder_date and stem_date and folder_date != stem_date
            ),
            utc_offset_day=bool(
                folder_date and clock_date and folder_date != clock_date
            ),
            # A gap of more than a day is not the timezone. Flag it so trends
            # can drop the block rather than place it on a wrong date.
            date_gap_days=(
                (dt.date.fromisoformat(clock_date)
                 - dt.date.fromisoformat(folder_date)).days
                if folder_date and clock_date else 0
            ),
            start_time_utc=start.strftime("%H:%M:%S") if start else None,
            duration_s=dur,
            sr=info["fs"],
            n_samples=info["n_points"],
            n_chan_declared=info["n_chan"],
            n_chan_with_events=int(np.unique(chans).size),
            n_events=n,
            n_code0=int((codes == 0).sum()),
            n_code1=int((codes == 1).sum()),
            n_code_other=int((codes > 1).sum()),
            n_sortcodes=int(np.unique(codes).size),
            event_rate_hz=(n / dur / max(np.unique(chans).size, 1))
            if dur and np.isfinite(dur) else np.nan,
            has_broadband=n_sev > 0,
            n_sev=n_sev,
            # Store naming is not uniform: two Picasso task tanks record
            # LFP{n} + pNe{n} and no broadband at all.
            broadband_store=broadband_store(stores, arr),
            lfp_stores=";".join(lfp_stores(stores, arr)),
            has_lfp=bool(lfp_stores(stores, arr)),
            sort_names=";".join(sorts),
            n_sorts=len(sorts),
            # A store can be declared in the Tbk and acquire nothing. Picasso
            # runs eNe1 through 2016 and switches to eNe2 in 2017, so "which
            # array is live" is a property of the block, not of the subject.
            live=n > 0,
            excluded=("short block" if (np.isfinite(dur) and dur < MIN_DURATION_S)
                      else "no events" if n == 0 else None),
        ))
    if not rows:
        rows = [dict(**base, error="no snippet store declared")]
    return rows


# %%
# === Report ===
def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def report(d: pd.DataFrame) -> None:
    ok = d[d.get("error").isna()] if "error" in d else d
    banner("1. What is there")
    print(f"  blocks scanned      : {d.block.nunique()}")
    print(f"  rows (block x array): {len(d)}   errors: {len(d) - len(ok)}")
    if len(d) - len(ok):
        print(d[d.error.notna()][["subject", "block", "error"]].to_string())
    g = ok.groupby(["subject", "array"]).agg(
        blocks=("block", "nunique"),
        first=("date", "min"), last=("date", "max"),
        median_dur_s=("duration_s", "median"),
        median_events=("n_events", "median"),
        with_sev=("has_broadband", "sum"),
        with_sort=("n_sorts", lambda s: int((s > 0).sum())),
    )
    print(g.to_string())

    banner("2. Which of the three dates to believe")
    c = ok.drop_duplicates("block")
    print(f"  blocks with no parseable folder date : "
          f"{int(c.folder_date.isna().sum())}")
    print(f"  blocks where the STEM disagrees      : "
          f"{int(c.date_conflict.sum())}  (stem typo, folder kept)")
    if c.date_conflict.any():
        print(c[c.date_conflict][
            ["subject", "block", "stem", "date", "stem_date"]
        ].head(12).to_string(index=False))
    off = c[c.utc_offset_day].copy()
    print(f"\n  blocks where folder date != UTC clock date: {len(off)}")
    if len(off):
        off["gap_days"] = (pd.to_datetime(off.utc_date)
                           - pd.to_datetime(off.folder_date)).dt.days
        print(off[["subject", "block", "date", "utc_date", "start_time_utc",
                   "gap_days"]].to_string(index=False))
        print("\n  A one-day gap on a late-evening start is the UTC offset and")
        print("  nothing more: 00:0x UTC is ~19:0x US Eastern the previous")
        print("  evening, the corpus's modal recording hour. Folder date kept.")
        wide = off[off.gap_days.abs() > 1]
        if len(wide):
            print(f"\n  {len(wide)} block(s) disagree by more than a day, which")
            print("  the timezone cannot explain. Treat their dates as")
            print("  unresolved -- most likely a re-record filed into an")
            print("  earlier session's folder:")
            print(wide[["subject", "block", "folder_date", "utc_date",
                        "gap_days"]].to_string(index=False))

    banner("2b. Which array is live")
    print("  A declared store is not an acquiring store.\n")
    live = ok.groupby(["subject", "array"]).agg(
        blocks=("block", "size"), live=("live", "sum"),
        first_live=("date", lambda s: s[ok.loc[s.index, "live"]].min()),
        last_live=("date", lambda s: s[ok.loc[s.index, "live"]].max()),
    )
    print(live.to_string())

    lv = ok[ok.live]
    banner("3. Online sortcodes carry no unit structure")
    print("  If TDT's online sorter identified neurons, sortcodes would run")
    print("  1..N per channel. They do not.\n")
    print(f"  {'subject':10s} {'rows':>5s} {'max distinct codes':>19s} "
          f"{'frac events code 1':>19s} {'frac code 0':>12s}")
    for subj, g2 in lv.groupby("subject"):
        tot = g2.n_events.sum()
        print(f"  {subj:10s} {len(g2):5d} {int(g2.n_sortcodes.max()):19d} "
              f"{g2.n_code1.sum() / tot:19.3f} {g2.n_code0.sum() / tot:12.3f}")
    print(f"\n  events with a code above 1, whole corpus: "
          f"{int(lv.n_code_other.sum())}")

    banner("4. What each analysis layer can reach")
    n_block = lv.block.nunique()
    n_sev = lv[lv.has_broadband].block.nunique()
    n_sorted = lv[lv.n_sorts > 0].block.nunique()
    print(f"  live (block, array) pairs   : {len(lv)} of {len(ok)}")
    print(f"  sorting-free (snippets)     : {n_block} blocks  (all with events)")
    print(f"  sorting-free (broadband)    : {n_sev} blocks")
    print(f"  LFP (pNe, 763 Hz)           : {lv[lv.has_lfp].block.nunique()} blocks")
    print(f"  offline-sort comparison     : {n_sorted} blocks")
    print(f"  re-sort from raw            : {n_sev} blocks")
    if n_sorted:
        s = lv[lv.n_sorts > 0].drop_duplicates("block")
        print("\n  offline sorts present:")
        print(s[["subject", "block", "date", "sort_names"]].to_string(index=False))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=8)
    args = ap.parse_args()

    blocks: list[str] = []
    banner("TDT inventory -- Oops, Picasso and Luigi")
    for name, root in TDT_ROOTS.items():
        found = find_blocks(root) if root.exists() else []
        print(f"  {name:8s} {len(found):4d} blocks   {root}")
        blocks.extend(str(p) for p in found)
    print(f"  total: {len(blocks)}")

    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        rows = [r for batch in ex.map(scan_block, blocks, chunksize=2)
                for r in batch]
    d = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, engine="pyarrow", index=False)
    report(d)
    print(f"\n  wrote {OUT.relative_to(REPO)}  ({len(d)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

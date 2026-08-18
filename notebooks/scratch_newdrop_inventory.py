"""Inventory the second data drop: Rocky's broadband and manual sorts, and Chase.

Three things arrived that the existing `monkey_inventory.parquet` cannot hold:

1. **Rocky's `.ns5`.** 431 broadband files on `C:` whose `.nev` siblings were
   already inventoried on `D:` -- every one of the 457 new NEV stems is
   already known. So this is not new sessions, it is **broadband for sessions
   that previously had only snippets**, which is what turns Rocky's 2017-2020
   series from a snippet-only corpus into a re-sortable one.
2. **Manual sorts by operator DS**, five dates under `Rocky_Manual_Sorts/`,
   as per-channel `.mat` (timestamp, unit, PC1-4, waveform samples) beside the
   original `.nev`/`.plx`. A second operator's labels on known recordings.
3. **Chase**, 20 Plexon `.plx` from 2009-2010 with a README giving implant,
   repair-surgery and quality-decline dates -- the only corpus in the project
   with dated events to test a longitudinal claim against.

The existing inventory stores paths relative to one root. Two roots now exist,
so every row here carries an absolute `path` and the merged table is written
separately rather than overwriting a table other scripts already depend on.

Run from repo root:

    uv run python notebooks/scratch_newdrop_inventory.py

Writes `data/derived/newdrop_inventory.parquet` and the merged
`data/derived/inventory_all.parquet`.

See:
- docs/notes/monkey_corpus.md
"""

from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from _paths import MONKEY_ROOT  # noqa: E402

NEW_ROOT = Path(r"C:\MyData\Monkeydata")
ROCKY_NEW = NEW_ROOT / "Rocky"
CHASE = NEW_ROOT / "Chase"

OLD_INV = REPO / "data" / "derived" / "monkey_inventory.parquet"
OUT = REPO / "data" / "derived" / "newdrop_inventory.parquet"
MERGED = REPO / "data" / "derived" / "inventory_all.parquet"

# Two date orders are in use and both must parse. Up to 2020 the convention is
# `Rocky_Anterior_01-03-2019_Baseline_AnalogHeadstage`; from 2022 it flips to
# `Rocky_Anterior_2022-06-01_Baseline_DigitalHeadstage`. Silently dropping the
# second cost 77 of 431 broadband files, and they are the most recent ones.
# The day field allows three digits to absorb `06-013-2019`, the same
# zero-padding typo the TDT tree carries in `Oops_2015_07_010-1`.
ROCKY_RE = re.compile(
    r"^Rocky_(?P<array>Anterior|Posterior)_"
    r"(?:(?P<mm>\d{1,2})-(?P<dd>\d{1,3})-(?P<yyyy>\d{4})"
    r"|(?P<yyyy2>\d{4})-(?P<mm2>\d{1,2})-(?P<dd2>\d{1,3}))_"
    r"(?P<condition>[^_.]+)"
    r"(?:_(?P<headstage>[A-Za-z]+))?"
    r"(?P<chain>-\d+|-DS|-MA)?$"
)
# `Chase_031709.plx`, `Chase.011410.w.plx`, `Chase_040309.3.plx`
CHASE_RE = re.compile(r"^Chase[._](?P<mmddyy>\d{6})")

ROLE_BY_EXT = {
    ".ns5": "broadband", ".ns6": "broadband", ".ns3": "lfp",
    ".nev": "snippets", ".ccf": "config", ".plx": "plexon",
    ".mat": "export_mat", ".txt": "text", ".png": "figure",
    ".tev": "tdt_tank", ".tsq": "tdt_index", ".sev": "tdt_stream",
}


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def parse_rocky(stem: str) -> dict:
    """Grammar fields from a Rocky filename stem, or an empty dict."""
    m = ROCKY_RE.match(stem)
    if not m:
        return {}
    g = m.groupdict()
    yyyy = int(g["yyyy"] or g["yyyy2"])
    mm = int(g["mm"] or g["mm2"])
    dd = int(g["dd"] or g["dd2"])
    # `06-013-2019` means the 13th: a stray leading zero, not day 13 of a
    # month that does not exist.
    if dd > 31:
        dd = dd % 100
    if not (1 <= mm <= 12 and 1 <= dd <= 31):
        return {}
    return dict(
        array=g["array"],
        date=f"{yyyy:04d}-{mm:02d}-{dd:02d}",
        condition=g["condition"],
        headstage=(g["headstage"] or "").replace("Headstage", "") or None,
        chain=g["chain"] or "",
    )


def parse_chase(stem: str) -> dict:
    """Chase encodes MMDDYY. Two-digit years are all 2009-2010 here."""
    m = CHASE_RE.match(stem)
    if not m:
        return {}
    s = m.group("mmddyy")
    mm, dd, yy = int(s[:2]), int(s[2:4]), int(s[4:])
    if not (1 <= mm <= 12 and 1 <= dd <= 31):
        return {}
    return dict(date=f"{2000 + yy:04d}-{mm:02d}-{dd:02d}", array="single",
                condition="waveforms", headstage=None, chain="")


# %%
# === Walkers ===
def walk_rocky() -> list[dict]:
    """Every file under the new Rocky tree, typed and dated where possible."""
    rows: list[dict] = []
    for p in ROCKY_NEW.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROCKY_NEW)
        # `Blackrock/Sorted` holds the -01 automatic output; the manual sorts
        # live in their own dated folders. Both matter and neither is the
        # unsorted original, so the source folder is kept as `tree`.
        tree = rel.parts[0] if len(rel.parts) > 1 else "."
        row = dict(
            subject="Rocky", implant="I1", tree=tree, path=str(p),
            rel=str(rel), folder=str(rel.parent), name=p.name, stem=p.stem,
            ext=p.suffix.lower(),
            role=ROLE_BY_EXT.get(p.suffix.lower(), "other"),
            size=p.stat().st_size, drop="newdrop",
        )
        row.update(parse_rocky(p.stem))
        if p.suffix.lower() == ".mat" and "Manual_Sorts" in str(rel):
            # `<stem>_<channel>[a|b].mat`, one file per sorted channel.
            row["role"] = "manual_sort_mat"
            row["chain"] = "-DS-manual"
            base = re.sub(r"_\d+[a-z]?$", "", p.stem)
            row.update(parse_rocky(base))
            row["stem"] = base
        rows.append(row)
    return rows


def walk_chase() -> list[dict]:
    rows: list[dict] = []
    for p in CHASE.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(CHASE)
        row = dict(
            subject="Chase", implant="I1", tree="Chase", path=str(p),
            rel=str(rel), folder=str(rel.parent), name=p.name, stem=p.stem,
            ext=p.suffix.lower(),
            role=ROLE_BY_EXT.get(p.suffix.lower(), "other"),
            size=p.stat().st_size, drop="newdrop",
        )
        row.update(parse_chase(p.stem))
        rows.append(row)
    return rows


def report(d: pd.DataFrame) -> None:
    banner("1. What arrived")
    print(d.groupby(["subject", "tree", "role"]).agg(
        files=("name", "size"),
        gib=("size", lambda s: round(s.sum() / 2**30, 1))).to_string())

    banner("2. Rocky: broadband now exists for sessions that had only snippets")
    r = d[(d.subject == "Rocky") & d.date.notna()]
    ns5 = r[r.role == "broadband"]
    nev = r[r.role == "snippets"]
    print(f"  .ns5 files            : {len(ns5)}")
    print(f"  .nev files            : {len(nev)}")
    print(f"  stems with both       : "
          f"{len(set(ns5.stem) & set(nev.stem))}")
    print(f"  date range            : {r.date.min()} .. {r.date.max()}")
    print()
    print("  by array and headstage (broadband only):")
    print(ns5.groupby(["array", "headstage"], dropna=False).size()
          .rename("sessions").to_string())

    banner("3. The equipment question: what overlaps")
    print("  Same-day analog/digital pairs with broadband on both sides:\n")
    piv = ns5.pivot_table(index=["array", "date"], columns="headstage",
                          values="name", aggfunc="size")
    if {"Analog", "Digital"} <= set(piv.columns):
        both = piv.dropna(subset=["Analog", "Digital"])
        print(f"  pairs: {len(both)}")
        print(f"  dates: {both.index.get_level_values('date').min()} .. "
              f"{both.index.get_level_values('date').max()}")
        print(both.groupby(level="array").size().rename("pairs").to_string())

    banner("4. Manual sorts by operator DS")
    ms = d[d.role == "manual_sort_mat"]
    if len(ms):
        print(ms.groupby(["date", "array"]).agg(
            channels=("name", "size")).to_string())
        print(f"\n  originals beside them: "
              f"{len(d[(d.tree == 'Rocky_Manual_Sorts') & d.ext.isin(['.nev', '.plx'])])}")

    banner("5. Chase")
    c = d[d.subject == "Chase"]
    plx = c[c.role == "plexon"]
    print(f"  .plx files : {len(plx)}   "
          f"{plx['size'].sum() / 2**30:.1f} GiB")
    if len(plx):
        print(f"  dates      : {plx.date.min()} .. {plx.date.max()}")
        print("\n  README documents: implant 2009-02-26, first brain-control")
        print("  2009-03-17, repair surgery 2009-08-24, and a noted 'sharp")
        print("  decline' in unit quality 2009-08-27. Dated events to test a")
        print("  longitudinal claim against -- the only corpus here with them.")
        print()
        print(plx[["stem", "date"]].sort_values("date").to_string(index=False))


def main() -> int:
    rows = walk_rocky() + walk_chase()
    d = pd.DataFrame(rows)
    for col in ("array", "date", "condition", "headstage", "chain"):
        if col not in d.columns:
            d[col] = None
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, engine="pyarrow", index=False)

    banner("Second drop inventory -- Rocky broadband, manual sorts, Chase")
    print(f"  files walked: {len(d)}")
    report(d)

    if OLD_INV.exists():
        old = pd.read_parquet(OLD_INV)
        old = old.copy()
        # The first drop stores `date` as datetime64 and this one as an
        # ISO string; concatenating without aligning gives an object column
        # that pyarrow refuses to write.
        old["date"] = pd.to_datetime(old["date"], errors="coerce")
        old["path"] = [str(MONKEY_ROOT / r) for r in old.rel]
        old["drop"] = "first"
        merged = pd.concat([old, d], ignore_index=True)
        merged.to_parquet(MERGED, engine="pyarrow", index=False)
        print(f"\n  merged with the first drop -> {MERGED.name} "
              f"({len(merged)} rows)")
    print(f"  wrote {OUT.relative_to(REPO)}  ({len(d)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

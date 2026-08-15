"""Cross-validate every array in the manufacturer CD collection.

The CD files carry, per array, up to three descriptions: the `.cmp` mapfile,
the factory workbook (`.xlsm`, or `.xls` for older lots), and the automated
impedance `.txt`. This walks all of them, checks each against the others, and
reports the geometries actually present rather than assuming Utah-96.

What it establishes:

- **Geometry is not one thing.** 96-channel 10x10 arrays on banks A-C and
  16-channel 4x4 arrays on bank A pins 1-16 both appear. Any code that
  hardcodes 96 or a 10x10 grid is wrong for a third of this collection.
- **`col`/`row` are display coordinates, not physical ones.** Three 16-channel
  maps place the identical 4x4 block on rows 1-4 instead of 0-3.
- **The channel-id rule is geometry-independent**: `(bank - 'A') * 32 + pin`
  holds for every array here, whatever its size.

Run from repo root:

    uv run python notebooks/scratch_array_catalog.py [--root <dir>]

See:
- docs/notes/channel_mapping.md
- docs/notes/array_catalog.md
"""

from __future__ import annotations

import argparse
import re
import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_cohort_io import (  # noqa: E402
    describe_cmp,
    open_workbook,
    parse_cmp,
    vacant_cells,
    validate_cmp,
)

CD_ROOT = Path(r"D:\Claude Code\Blackrock files\Blackrock Utah array"
               r"\Utah array manufacture CD files")
OUT = REPO / "data" / "derived" / "array_catalog.parquet"
PAD_SHEET = "Array Map with Automated Tester"
SERIAL_RE = re.compile(r"(\d{4}-\d{6})")


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === Pairing files by serial ===
def serial_of(p: Path) -> str | None:
    m = SERIAL_RE.search(p.name)
    return m.group(1) if m else None


def collect(root: Path) -> dict[str, dict]:
    """Group every CD file by array serial."""
    out: dict[str, dict] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        s = serial_of(p)
        if not s:
            continue
        ext = p.suffix.lower()
        rec = out.setdefault(s, dict(serial=s, folder=p.parent.name))
        if ext == ".cmp":
            rec.setdefault("cmp", p)
        elif ext in (".xlsm", ".xls"):
            rec.setdefault("book", p)
        elif ext == ".txt":
            rec.setdefault("txt", p)
    return out


# %%
# === Pad-side grid, found rather than assumed ===
def find_pad_block(book: Path, want: set[int], n_cols: int,
                   n_rows: int) -> dict[tuple[int, int], str] | None:
    """Locate the pad-side label grid anywhere in the workbook.

    The 96-channel template prints it at AR15:BA24, but that address is a
    property of one template, not of the format. Instead scan for the smallest
    rectangular block of integer cells whose values are exactly this array's
    electrode numbers -- which both finds the block and proves it is the right
    one.
    """
    wb, _ = open_workbook(book)
    if wb is None or PAD_SHEET not in wb.sheetnames:
        return None
    ws = wb[PAD_SHEET]
    grid: dict[tuple[int, int], int] = {}
    for row in ws.iter_rows(values_only=False):
        for c in row:
            if isinstance(c.value, (int, float)) and float(c.value).is_integer():
                grid[(c.column, c.row)] = int(c.value)
    wb.close()
    if not grid:
        return None

    # Scan windows rather than collecting every cell whose value happens to
    # land in 1..96: the impedance table on the same sheet is full of such
    # values and pollutes any global collection. The right block is the one
    # whose contents are *exactly* this array's electrode numbers.
    cmax = max(c for c, _ in grid)
    rmax = max(r for _, r in grid)
    for r0 in range(1, rmax + 1):
        for c0 in range(1, cmax + 1):
            win = {(c - c0, r - r0): v for (c, r), v in grid.items()
                   if c0 <= c < c0 + n_cols and r0 <= r < r0 + n_rows}
            if set(win.values()) == want:
                # Printed rows run top-down; cmp rows count from the bottom.
                return {(c, n_rows - 1 - r): f"elec{v}" for (c, r), v in win.items()}
    return None


# %%
# === Per-array checks ===
def check(rec: dict) -> dict:
    out = dict(serial=rec["serial"], folder=rec["folder"],
               has_cmp="cmp" in rec, has_book="book" in rec, has_txt="txt" in rec,
               book_kind=rec["book"].suffix.lower() if "book" in rec else "")
    if "cmp" not in rec:
        out["status"] = "no cmp"
        return out
    d = parse_cmp(rec["cmp"])
    if not len(d):
        out["status"] = "cmp unparseable"
        return out
    out |= describe_cmp(d)
    issues = validate_cmp(d)
    out["cmp_issues"] = "; ".join(issues)
    out["vacant"] = str(vacant_cells(d))
    out["formula_ok"] = bool(
        (d.channel_id == (d.bank.map(lambda b: ord(b) - 65) * 32 + d.elec)).all())

    if "book" in rec and rec["book"].suffix.lower() == ".xlsm":
        want = set(d.label.str.extract(r"(\d+)", expand=False).astype(int))
        pad = find_pad_block(rec["book"], want, out["n_cols"], out["n_rows"])
        if pad is None:
            out["pad"] = "no grid found"
        else:
            cmp_pos = {(int(r.col) - out["col0"], int(r.row) - out["row0"]): r.label
                       for r in d.itertuples()}
            bad = sum(1 for k in set(pad) & set(cmp_pos) if pad[k] != cmp_pos[k])
            miss = len(set(cmp_pos) - set(pad))
            out["pad"] = ("exact" if bad == 0 and miss == 0
                          else f"{bad} mismatched, {miss} missing")
    elif "book" in rec:
        out["pad"] = "legacy .xls, not read"
    else:
        out["pad"] = "no workbook"

    if "txt" in rec:
        rows = []
        for ln in rec["txt"].read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"\s*elec(\d+)\s+(<=\s*)?(\d+)", ln)
            if m:
                rows.append((int(m.group(1)), int(m.group(3))))
        out["txt_rows"] = len(rows)
        n = out["n"]
        # Rows 1..n should be this array's channels; the rest are unused pins
        # on a larger front end and read in the kilohm range.
        sig = [z for k, z in rows if k <= n]
        out["txt_signal_rows"] = len(sig)
        out["txt_median_ohm"] = int(pd.Series(sig).median()) if sig else -1
    out["status"] = "ok" if not issues else "ISSUES"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=str, default=str(CD_ROOT))
    args = ap.parse_args()

    files = collect(Path(args.root))
    banner(f"Cross-validating {len(files)} arrays from the manufacturer CD files")
    rows = [check(r) for r in files.values()]
    df = pd.DataFrame(rows)

    cols = ["serial", "folder", "n", "n_cols", "n_rows", "row0", "banks",
            "pin_max", "channel_max", "formula_ok", "pad", "book_kind", "status"]
    have = [c for c in cols if c in df.columns]
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        print(df[have].to_string(index=False))

    banner("Geometries present")
    g = (df.groupby(["n", "n_cols", "n_rows", "banks", "pin_max", "channel_max"])
           .size().rename("arrays").reset_index())
    print(g.to_string(index=False))

    banner("Checks")
    print(f"  channel_id == (bank-'A')*32 + pin : "
          f"{int(df.formula_ok.sum())}/{len(df)} arrays")
    print(f"  cmp self-consistent               : "
          f"{int((df.cmp_issues == '').sum())}/{len(df)} arrays")
    if (df.cmp_issues != "").any():
        for _, r in df[df.cmp_issues != ""].iterrows():
            print(f"      {r.serial}: {r.cmp_issues}")
    pad = df[df.pad.notna()]
    print(f"  pad-side grid agrees with the cmp : "
          f"{int((pad.pad == 'exact').sum())}/{int((pad.book_kind == '.xlsm').sum())} "
          f"workbooks in modern format")
    for v, c in df.pad.value_counts().items():
        print(f"      {c:3d}  {v}")

    banner("Display-coordinate origin is not guaranteed")
    off = df[df.row0 != 0]
    if len(off):
        print(f"  {len(off)} arrays place their grid above row 0:")
        print(off[["serial", "n", "n_cols", "n_rows", "row0"]].to_string(index=False))
        print("\n  Same electrode-to-pin mapping as their siblings; only the")
        print("  display origin differs. Compare geometry relatively, never by")
        print("  absolute (col, row) across arrays.")
    else:
        print("  every array starts at row 0")

    banner("Unconnected positions, per geometry")
    for n, g2 in df.groupby("n"):
        vac = g2.vacant.value_counts()
        print(f"\n  {n}-channel arrays ({len(g2)}):")
        for v, c in vac.items():
            print(f"    {c:3d}  {v}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, engine="pyarrow", index=False)
    banner("Written")
    print(f"  {OUT.relative_to(REPO)}  ({len(df)} arrays)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

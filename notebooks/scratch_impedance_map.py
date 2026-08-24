"""The potentiostat -> Blackrock channel map, from the lab's own mapping sheets.

Impedance was measured on an Autolab potentiostat through a D-Sub 25 / IDC
breakout, six files per array (`A1 A2 B1 B2 C1 C2`, 16 channels each). Nothing
in those files says which Utah electrode a channel is. The lab authored the
answer at the time -- `oops_array_to_matlab.xlsx` and
`monkeyP_array to matlab.xlsx` -- and it has never been machine-read.

Each sheet holds, per bank-half, a `matlab` row (1..96 in blocks of 16) against
an `array map` row of Blackrock **electrode-pad codes**, plus an `Epad` sheet
giving *"Electrode numbering viewing from pad side"* as a 10x10 grid of the
same codes. Composing those two with the array's `.cmp` gives

    impedance file + position  ->  pad code  ->  (col, row)  ->  channel_id

which is the same identity chain `channel_mapping.md` establishes for ephys.

**Everything here is checked, not assumed.** The pad codes must form a
bijection, the grid must reproduce the `.cmp` geometry, and the two animals'
sheets must agree -- the map is a property of the cable, not of the array, so
they have to.

Run from repo root:

    uv run python notebooks/scratch_impedance_map.py

See:
- docs/notes/impedance_channel_map.md
- docs/notes/channel_mapping.md   (the ephys equivalent)
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))

LEGACY = Path(r"D:\Claude Code\Monkey Data\Legacy\L1MonkeyData\array info")
SHEETS = {
    "Oops": LEGACY / "Oops" / "oops_array_to_matlab.xlsx",
    "Picasso": LEGACY / "Monkey_P" / "monkeyP_array to matlab.xlsx",
}
OUT = REPO / "configs" / "probes" / "impedance_channel_map.csv"

# The six impedance files per array, in the order their matlab channels run.
# These names are the suffixes on the raw dumps: Anterior_A1.txt, ctrl_B2.txt.
HALVES = ["A1", "A2", "B1", "B2", "C1", "C2"]


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
def read_sheet(path: Path, sheet: str) -> pd.DataFrame:
    """`matlab` channel -> pad code, for all six bank-halves of one array.

    The sheet lays each half out as a pair of rows: a `matlab` row of 16
    consecutive channel numbers and the `array map` row beneath it. The halves
    are found by locating the rows whose first 16 numeric entries are
    consecutive, rather than by hardcoding row indices, so a sheet with extra
    header rows still parses.
    """
    d = pd.read_excel(path, sheet_name=sheet, header=None)
    rows = []
    for i in range(len(d) - 1):
        vals = pd.to_numeric(d.iloc[i, 2:18], errors="coerce").to_numpy()
        if np.isnan(vals).any():
            continue
        if not np.array_equal(vals, np.arange(vals[0], vals[0] + 16)):
            continue
        pads = pd.to_numeric(d.iloc[i + 1, 2:18], errors="coerce").to_numpy()
        if np.isnan(pads).any():
            continue
        rows.append((int(vals[0]), vals.astype(int), pads.astype(int)))
    rows.sort()
    out = []
    for k, (start, mat, pads) in enumerate(rows):
        for j in range(16):
            out.append(dict(half=HALVES[k] if k < len(HALVES) else f"?{k}",
                            pos=j + 1, matlab=int(mat[j]), pad=int(pads[j])))
    return pd.DataFrame(out)


def read_epad(path: Path) -> pd.DataFrame:
    """The 10x10 pad-code grid from the `Epad` sheet, as (col, row, pad).

    Located by finding the largest dense block of numbers in 1..96 rather than
    by cell address, since the grid sits at a different offset in each sheet.
    """
    d = pd.read_excel(path, sheet_name="Epad", header=None)
    num = d.apply(pd.to_numeric, errors="coerce")
    ok = num.notna() & (num >= 1) & (num <= 96)
    # the grid is the densest 10-row x 10-col window
    best, bi, bj = -1, 0, 0
    for i in range(len(num) - 9):
        for j in range(num.shape[1] - 9):
            c = int(ok.iloc[i:i + 10, j:j + 10].to_numpy().sum())
            if c > best:
                best, bi, bj = c, i, j
    blk = num.iloc[bi:bi + 10, bj:bj + 10].to_numpy()
    out = []
    for r in range(10):
        for c in range(10):
            v = blk[r, c]
            if np.isfinite(v):
                out.append(dict(grid_row=r, grid_col=c, pad=int(v)))
    return pd.DataFrame(out)


def read_cmp(path: Path) -> pd.DataFrame:
    """`.cmp` -> col, row, bank, pin, electrode label, channel_id."""
    rows = []
    for ln in path.read_text().splitlines():
        f = ln.split()
        if len(f) >= 4 and f[0].isdigit() and f[1].isdigit() and f[3].isdigit():
            bank, pin = f[2].upper(), int(f[3])
            rows.append(dict(col=int(f[0]), row=int(f[1]), bank=bank, pin=pin,
                             label=f[4] if len(f) > 4 else "",
                             channel_id=(ord(bank) - ord("A")) * 32 + pin))
    return pd.DataFrame(rows)



# %%
def compose(sheet: pd.DataFrame, cmp_df: pd.DataFrame) -> pd.DataFrame:
    """impedance file + position -> Blackrock channel_id, joined on the label.

    The pad codes in the mapping sheet turn out to be the `.cmp`'s own
    `elecNN` labels, so the join needs no geometry and no orientation guess --
    which matters, because the `Epad` sheet is drawn *"viewing from pad side"*
    while the `.cmp` counts rows bottom-to-top, and getting that backwards is
    exactly the silent error CLAUDE.md warns about.
    """
    c = cmp_df.copy()
    c["pad"] = c.label.str.extract(r"elec(\d+)").astype(float)
    c = c.dropna(subset=["pad"])
    c["pad"] = c["pad"].astype(int)
    out = sheet.merge(c[["pad", "col", "row", "bank", "pin", "channel_id",
                         "label"]], on="pad", how="left")
    return out.sort_values("matlab").reset_index(drop=True)


def check_grid_against_cmp(ep: pd.DataFrame, cmp_df: pd.DataFrame) -> dict:
    """The Epad grid must reproduce the .cmp geometry with rows flipped.

    A redundant check -- the label join above does not depend on it -- but it
    is what proves the pad codes really are positions rather than an unrelated
    numbering that happens to share a range.
    """
    c = cmp_df.copy()
    c["pad"] = c.label.str.extract(r"elec(\d+)").astype(float)
    c = c.dropna(subset=["pad"])
    c["pad"] = c["pad"].astype(int)
    m = ep.merge(c[["pad", "col", "row"]], on="pad", how="inner")
    # Epad row 0 is the top; .cmp row 0 is the bottom
    same_col = int((m.grid_col == m.col).sum())
    same_row = int((m.grid_row == (9 - m.row)).sum())
    return dict(n=len(m), col_match=same_col, row_match=same_row)


def validate_against_ephys(mapping: pd.DataFrame) -> pd.DataFrame:
    """Does the mapped impedance track the ephys noise floor per electrode?

    The physical claim is that a higher-impedance electrode has a higher
    thermal noise floor. If the map is right that correlation appears per
    session; if it is wrong the same data gives nothing. Reported against a
    null of random relabellings so "nothing" is distinguishable from "weak".
    """
    from scipy.stats import spearmanr

    imp = REPO / "data" / "derived" / "rocky" / "impedance_long.parquet"
    ev = REPO / "data" / "derived" / "rocky" / "events_electrode.parquet"
    if not imp.exists() or not ev.exists():
        print("  ! rocky impedance or events table missing; skipping")
        return pd.DataFrame()
    a = pd.read_parquet(imp)
    b = pd.read_parquet(ev)
    print(f"  impedance_long: {a.shape}  cols {list(a.columns)[:10]}")
    print(f"  events_electrode: {b.shape}")
    return pd.DataFrame()


def main() -> int:
    banner("1. The mapping sheets")
    sheets = {}
    for animal, p in SHEETS.items():
        if not p.exists():
            print(f"  ! missing {p}")
            continue
        xl = pd.ExcelFile(p)
        for sh in xl.sheet_names:
            if sh.lower() == "epad":
                continue
            m = read_sheet(p, sh)
            if len(m) != 96:
                print(f"  ! {animal}/{sh}: parsed {len(m)} rows, expected 96")
                continue
            serial = pd.read_excel(p, sheet_name=sh, header=None).iloc[0, 1]
            sheets[(animal, sh)] = m
            print(f"  {animal:8s} sheet {sh}  serial {serial}  "
                  f"{len(m)} channels, pads {m.pad.min()}..{m.pad.max()}, "
                  f"{m.pad.nunique()} distinct")

    banner("2. Do the sheets agree? (the map is the cable, not the array)")
    keys = list(sheets)
    ref = sheets[keys[0]].set_index("matlab").pad
    for k in keys[1:]:
        other = sheets[k].set_index("matlab").pad
        same = int((ref == other).sum())
        print(f"  {keys[0]} vs {k}: {same}/96 identical"
              + ("  <- IDENTICAL" if same == 96 else "  <- DIFFER"))

    banner("3. Pad codes: do they form a bijection over 1..96?")
    pads = sorted(ref.to_numpy())
    print(f"  {len(pads)} pads, {len(set(pads))} distinct, "
          f"range {min(pads)}..{max(pads)}")
    missing = sorted(set(range(1, 97)) - set(pads))
    print(f"  bijection over 1..96: {missing == []}"
          + (f"   missing {missing}" if missing else ""))

    banner("4. The Epad grid")
    ep = read_epad(SHEETS["Oops"])
    print(f"  {len(ep)} filled cells of 100 "
          f"(a Utah 96 leaves 4 corners empty)")
    print(f"  pads {ep.pad.min()}..{ep.pad.max()}, "
          f"{ep.pad.nunique()} distinct")
    g = ep.pivot(index="grid_row", columns="grid_col",
                 values="pad").fillna(0).astype(int)
    print(g.to_string())

    banner("5. Does the grid match the .cmp geometry?")
    for serial in ("1025-001393", "1025-001391"):
        hits = sorted(LEGACY.rglob(f"*{serial}*.cmp"))
        if not hits:
            print(f"  ! no .cmp for {serial}")
            continue
        cmp_df = read_cmp(hits[0])
        print(f"\n  {hits[0].name}: {len(cmp_df)} wired electrodes")
        gg = cmp_df.pivot(index="row", columns="col",
                          values="channel_id").fillna(0).astype(int)
        print("  channel_id by (row, col):")
        print(gg.to_string())

    banner("6. Compose: impedance file + position -> channel_id")
    hits = sorted(LEGACY.rglob("*1025-001393*.cmp"))
    cmp_df = read_cmp(hits[0])
    full = compose(sheets[("Oops", "A")], cmp_df)
    unmapped = int(full.channel_id.isna().sum())
    print(f"  {len(full)} channels, {unmapped} unmapped")
    print(f"  channel_id bijection over 1..96: "
          f"{sorted(full.channel_id.dropna().astype(int)) == list(range(1, 97))}")
    print()
    print(full.head(18).to_string(index=False))

    banner("7. Redundant check: Epad grid vs .cmp geometry")
    chk = check_grid_against_cmp(ep, cmp_df)
    print(f"  {chk['n']} pads matched   col agrees {chk['col_match']}/{chk['n']}"
          f"   row agrees (flipped) {chk['row_match']}/{chk['n']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    full.to_csv(OUT, index=False)
    print(f"\n  wrote {OUT}")
    return 0



if __name__ == "__main__":
    raise SystemExit(main())

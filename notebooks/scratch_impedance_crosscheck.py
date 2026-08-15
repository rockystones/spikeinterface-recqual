"""Prove what the factory impedance file is indexed by, from the workbook itself.

The automated impedance dump heads its rows ``elec1..elec128``, which reads as
electrode numbers and is not. An earlier argument established that indirectly,
by showing rows 1-32 carry exactly the CMP's bank-A labels. The factory
workbook allows a direct proof, because it prints the same array twice on the
same sheet:

- *Electrode numbering viewing from pad side* — a grid of electrode numbers.
- *Electrode Impedance viewing from pad side* — the same grid of impedances.

So for every grid position the electrode number and its impedance are both
known, independently of any indexing assumption. Walk the positions, look each
electrode up in the `.cmp` to get its channel id, and check which row of the
impedance table carries that impedance:

    pad position -> electrode number -> (cmp) -> bank/pin -> channel id
    pad position -> impedance
    impedance table row N -> impedance

If row N matches the channel id, the file is indexed by channel. If it matches
the electrode number, it is indexed by electrode.

Run from repo root:

    uv run python notebooks/scratch_impedance_crosscheck.py

See:
- docs/notes/channel_mapping.md
- docs/notes/array_catalog.md
"""

from __future__ import annotations

import re
import sys
import warnings
from collections import Counter
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_array_catalog import CD_ROOT, collect, find_pad_block  # noqa: E402
from scratch_cohort_io import open_workbook, parse_cmp  # noqa: E402

PAD_SHEET = "Array Map with Automated Tester"
Z_SHEET = "Impedance Values from Automated"
OUT = REPO / "data" / "derived" / "impedance_crosscheck.parquet"


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === Readers ===
def read_z_table(book: Path) -> dict[int, int]:
    """``elecN`` row number -> impedance, from the automated-values sheet."""
    wb, _ = open_workbook(book)
    if wb is None or Z_SHEET not in wb.sheetnames:
        return {}
    ws = wb[Z_SHEET]
    out = {}
    for r in ws.iter_rows(min_row=1, max_col=3, values_only=True):
        lab = str(r[1]).strip() if r[1] is not None else ""
        if re.fullmatch(r"elec\d+", lab) and isinstance(r[2], (int, float)):
            out[int(lab[4:])] = int(r[2])
    wb.close()
    return out


def find_z_grid(book: Path, want: Counter, n_cols: int,
                n_rows: int) -> dict[tuple[int, int], int] | None:
    """The pad-side *impedance* grid: the window whose values are that multiset.

    Found rather than addressed, for the same reason as the electrode grid --
    the sheet holds several numeric blocks and only one of them is this.
    """
    wb, _ = open_workbook(book)
    if wb is None or PAD_SHEET not in wb.sheetnames:
        return None
    ws = wb[PAD_SHEET]
    grid = {}
    for row in ws.iter_rows(values_only=False):
        for c in row:
            if isinstance(c.value, (int, float)) and float(c.value).is_integer():
                grid[(c.column, c.row)] = int(c.value)
    wb.close()
    if not grid:
        return None
    cmax = max(c for c, _ in grid)
    rmax = max(r for _, r in grid)
    for r0 in range(1, rmax + 1):
        for c0 in range(1, cmax + 1):
            win = {(c - c0, r - r0): v for (c, r), v in grid.items()
                   if c0 <= c < c0 + n_cols and r0 <= r < r0 + n_rows}
            if Counter(win.values()) == want:
                return {(c, n_rows - 1 - r): v for (c, r), v in win.items()}
    return None


# %%
# === The check ===
def crosscheck(serial: str, rec: dict) -> dict | None:
    if "cmp" not in rec or "book" not in rec:
        return None
    if rec["book"].suffix.lower() != ".xlsm":
        return None
    d = parse_cmp(rec["cmp"])
    if not len(d):
        return None
    n = len(d)
    ztab = read_z_table(rec["book"])
    if not ztab:
        return None

    d["elec_num"] = d.label.str.extract(r"(\d+)", expand=False).astype(int)
    n_cols = int(d.col.max()) - int(d.col.min()) + 1
    n_rows = int(d.row.max()) - int(d.row.min()) + 1

    pad = find_pad_block(rec["book"], set(d.elec_num), n_cols, n_rows)
    if pad is None:
        return dict(serial=serial, status="no electrode grid")

    # The impedances that belong to this array are rows 1..n of the table.
    want = Counter(z for k, z in ztab.items() if k <= n)
    zgrid = find_z_grid(rec["book"], want, n_cols, n_rows)
    if zgrid is None:
        return dict(serial=serial, status="no impedance grid")

    by_elec = {int(r.elec_num): int(r.channel_id) for r in d.itertuples()}
    hit_chan = hit_elec = tested = 0
    for pos, lab in pad.items():
        e = int(lab[4:])
        if pos not in zgrid or e not in by_elec:
            continue
        z = zgrid[pos]
        tested += 1
        if ztab.get(by_elec[e]) == z:
            hit_chan += 1
        if ztab.get(e) == z:
            hit_elec += 1
    return dict(serial=serial, n=n, tested=tested,
                by_channel=hit_chan, by_electrode=hit_elec,
                status="ok")


def main() -> int:
    files = collect(CD_ROOT)
    banner("Is the factory impedance file indexed by channel or by electrode?")
    print("  For each pad-grid position: electrode number and impedance are both")
    print("  printed. Look the electrode up in the .cmp for its channel id, then")
    print("  see which row of the impedance table carries that impedance.\n")

    rows = [r for r in (crosscheck(s, rec) for s, rec in sorted(files.items()))
            if r is not None]
    df = pd.DataFrame(rows)
    ok = df[df.status == "ok"].copy()
    if len(ok):
        ok["chan_pct"] = (ok.by_channel / ok.tested * 100).round(1)
        ok["elec_pct"] = (ok.by_electrode / ok.tested * 100).round(1)
        print(ok[["serial", "n", "tested", "by_channel", "chan_pct",
                  "by_electrode", "elec_pct"]].to_string(index=False))
        banner("Verdict")
        t, c, e = ok.tested.sum(), ok.by_channel.sum(), ok.by_electrode.sum()
        print(f"  positions tested across {len(ok)} arrays : {t:,}")
        print(f"  impedance found at row = channel id      : {c:,}  ({c / t * 100:.2f}%)")
        print(f"  impedance found at row = electrode number: {e:,}  ({e / t * 100:.2f}%)")
        print()
        if c > e:
            print("  The file is indexed by CHANNEL (pin), not by electrode.")
            print("  Its 'elecN' row headers are a misnomer. Join impedance to")
            print("  recordings on channel_id.")
        print()
        print("  The electrode-number figure is not zero because impedance values")
        print("  repeat within an array, so some rows coincide by chance.")
    bad = df[df.status != "ok"]
    if len(bad):
        print(f"\n  {len(bad)} arrays not testable: "
              f"{dict(bad.status.value_counts())}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, engine="pyarrow", index=False)
    print(f"\n  wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

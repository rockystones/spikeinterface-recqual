"""Cross-validate each Rocky array across its .cmp, .xlsm and .txt files.

Blackrock ships three descriptions of the same array and they are not
redundant copies of one another:

- **`.cmp`** — the mapfile Central and every analysis tool reads. `col`, `row`,
  `bank`, `elec`, `label`.
- **`.xlsm`** — the factory workbook. Carries its own copy of the Cerebus
  mapping, the per-electrode impedance at final assembly, and an array map
  showing those impedances laid out on the physical board.
- **`.txt`** — the automated impedance dump, `label -> ohms`, 128 entries of
  which 97..128 are reference and ground pins rather than electrodes.

The workbook also prints a **pad-side location grid** — Blackrock's own record
of where each electrode physically sits — and that, not any canonical layout,
is the authority for geometry. It matters because which four cells of the 10x10
are empty is a property of the individual array: when shanks break during
manufacture, surviving shanks elsewhere are rewired to reach 96 channels and
the vacant cells move. `SN 1025-004377` is such an array, and checking it
against a sibling instead of against its own record reports the rewiring as
damage.

Run from repo root:

    uv run python notebooks/scratch_cmp_crossvalidate.py

See:
- docs/notes/cmp_validation.md
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
from scratch_cohort_io import (  # noqa: E402
    open_workbook,
    parse_cmp,
    read_pad_map,
    vacant_cells,
    validate_cmp,
    verify_against_padmap,
)

PROBE_DIR = REPO / "configs" / "probes"
ROCKY_PRE = Path(r"D:\Claude Code\Rocky\preimplant")
DOWNLOADS = Path(r"C:\Users\shide\Downloads")

# One entry per array: serial, implant, and the three files that describe it.
ARRAYS = [
    dict(serial="1025-001501", implant="I1", array="Anterior",
         cmp=ROCKY_PRE / "SN 1025-001501.cmp",
         xlsm=ROCKY_PRE / "13966-20 SN 1025-001501.xlsm",
         txt=ROCKY_PRE / "13966-20 SN 1025-001501.txt"),
    dict(serial="1025-001497", implant="I1", array="Posterior",
         cmp=ROCKY_PRE / "SN 1025-001497.cmp",
         xlsm=ROCKY_PRE / "13966-8 SN 1025-001497.xlsm",
         txt=ROCKY_PRE / "13966-8 SN 1025-001497.txt"),
    dict(serial="1025-004377", implant="I2", array="Anterior",
         cmp=PROBE_DIR / "SN 1025-004377.cmp",
         xlsm=DOWNLOADS / "1138-32 SN 1025-004377.xlsm",
         txt=PROBE_DIR / "1138-32 SN 1025-004377.txt"),
    dict(serial="1025-004419", implant="I2", array="Posterior",
         cmp=PROBE_DIR / "SN 1025-004419.cmp",
         xlsm=DOWNLOADS / "1138-34 SN 1025-004419.xlsm",
         txt=PROBE_DIR / "1138-34 SN 1025-004419.txt"),
]

N_ELECTRODES = 96
SHEET_CEREBUS = "Cerebus mapping"
SHEET_IMPEDANCE = "Impedance Values from Automated"
SHEET_MAP = "Array Map with Automated Tester"


def banner(t: str) -> None:
    print()
    print("=" * 76)
    print(t)
    print("=" * 76)


# %%
# === Readers ===
def read_xlsm_cerebus(path: Path) -> pd.DataFrame | None:
    """The workbook's own copy of the Cerebus mapping.

    Same five columns as the `.cmp`, plus a text column repeating the position
    as ``col,-row`` which acts as a second witness inside the same file.
    """
    wb, note = open_workbook(path)
    if wb is None or SHEET_CEREBUS not in wb.sheetnames:
        return None
    if note:
        print(f"        {note}")
    ws = wb[SHEET_CEREBUS]
    rows = []
    for r in ws.iter_rows(min_row=1, max_col=11, values_only=True):
        if r[0] is None or not str(r[0]).strip().lstrip("-").isdigit():
            continue
        try:
            col, row, bank, elec = int(r[0]), int(r[1]), str(r[2]).upper(), int(r[3])
        except (TypeError, ValueError):
            continue
        rows.append(dict(
            col=col, row=row, bank=bank, elec=elec, label=str(r[4]),
            channel_id=(ord(bank) - ord("A")) * 32 + elec,
            pos_text=str(r[9]) if len(r) > 9 and r[9] is not None else None,
        ))
    wb.close()
    return pd.DataFrame(rows)


def read_xlsm_impedance(path: Path) -> pd.DataFrame | None:
    """Per-label impedance from the factory workbook (column B label, C ohms)."""
    wb, _ = open_workbook(path)
    if wb is None or SHEET_IMPEDANCE not in wb.sheetnames:
        return None
    ws = wb[SHEET_IMPEDANCE]
    rows = []
    for r in ws.iter_rows(min_row=1, max_col=3, values_only=True):
        lab = str(r[1]).strip() if r[1] is not None else ""
        if not re.fullmatch(r"elec\d+", lab):
            continue
        rows.append(dict(label=lab, n=int(lab[4:]), z_xlsm=r[2]))
    wb.close()
    return pd.DataFrame(rows)


def read_txt_impedance(path: Path) -> pd.DataFrame:
    """Per-label impedance from the automated dump.

    Entries above ``elec96`` are reference and ground pins -- they read in the
    kilohm range against ~100-1000 ohms for an electrode -- and are excluded.
    """
    rows = []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\s*(elec\d+)\s+(<=\s*)?(\d+)", ln)
        if m:
            rows.append(dict(label=m.group(1), n=int(m.group(1)[4:]),
                             z_txt=int(m.group(3))))
    return pd.DataFrame(rows)


def read_xlsm_arraymap(path: Path) -> list[float]:
    """Numeric impedance values from the physical board map, in sheet order."""
    wb, _ = open_workbook(path)
    if wb is None or SHEET_MAP not in wb.sheetnames:
        return []
    ws = wb[SHEET_MAP]
    vals = [c for row in ws.iter_rows(min_row=6, max_row=30, min_col=1,
                                      max_col=20, values_only=True)
            for c in row if isinstance(c, (int, float))]
    wb.close()
    return vals


# %%
# === Comparisons ===
def compare_mapping(cmp_df: pd.DataFrame, xl_df: pd.DataFrame) -> pd.DataFrame:
    """Row-by-row diff of the two mappings, joined on the manufacturer label."""
    m = cmp_df.merge(xl_df, on="label", suffixes=("_cmp", "_xlsm"))
    return m[(m.col_cmp != m.col_xlsm) | (m.row_cmp != m.row_xlsm)
             | (m.electrode_id_cmp != m.electrode_id_xlsm)]


def check_pos_text(xl_df: pd.DataFrame) -> pd.DataFrame:
    """Rows where the workbook's own `col,-row` text disagrees with its numbers.

    A within-file consistency check: the text column is written by a different
    part of the template, so it catches a corrupted numeric cell.
    """
    bad = []
    for _, r in xl_df.iterrows():
        if not r.pos_text:
            continue
        m = re.fullmatch(r"\s*(-?\d+)\s*,\s*(-?\d+)\s*", str(r.pos_text))
        if not m:
            continue
        c, neg_r = int(m.group(1)), int(m.group(2))
        if c != r.col or -neg_r != r.row:
            bad.append(dict(label=r.label, numeric=(r.col, r.row),
                            text=r.pos_text, implies=(c, -neg_r)))
    return pd.DataFrame(bad)


def main() -> int:
    summary = []
    for a in ARRAYS:
        banner(f"{a['serial']}  ({a['implant']} {a['array']})")
        missing = [k for k in ("cmp", "xlsm", "txt") if not a[k].exists()]
        if missing:
            print(f"  MISSING: {missing}")
            continue

        cmp_raw = parse_cmp(a["cmp"])
        cmp_issues = validate_cmp(cmp_raw)
        vac = vacant_cells(cmp_raw)
        print(f"  cmp   {len(cmp_raw):3d} electrodes   "
              f"{'DEFECT: ' + '; '.join(cmp_issues) if cmp_issues else 'self-consistent'}")
        print(f"        vacant cells {vac}")

        pad = read_pad_map(a["xlsm"])
        if pad is None:
            print("  pad   no location grid in the workbook")
        else:
            geo = verify_against_padmap(cmp_raw, pad)
            print(f"  pad   {len(pad)} positions   "
                  f"{'MISMATCH: ' + '; '.join(geo) if geo else 'cmp agrees at every position'}")

        xl = read_xlsm_cerebus(a["xlsm"])
        if xl is None:
            print(f"  xlsm  no {SHEET_CEREBUS!r} sheet")
        else:
            xl_issues = validate_cmp(xl)
            print(f"  xlsm  {len(xl):3d} electrodes   "
                  f"{'DEFECT: ' + '; '.join(xl_issues) if xl_issues else 'clean'}")

            # The decisive comparison: raw cmp against the workbook.
            diff_raw = compare_mapping(cmp_raw, xl)
            print(f"\n  cmp(as shipped) vs xlsm : {len(diff_raw)} of "
                  f"{len(cmp_raw)} rows differ")
            for _, r in diff_raw.iterrows():
                print(f"      {r['label']:8s} cmp=({r.col_cmp},{r.row_cmp}) "
                      f"xlsm=({r.col_xlsm},{r.row_xlsm})  "
                      f"id {r.electrode_id_cmp} vs {r.electrode_id_xlsm}")

            bad_text = check_pos_text(xl)
            print(f"  xlsm internal col,-row text : "
                  f"{len(bad_text)} inconsistent rows")
            for _, r in bad_text.iterrows():
                print(f"      {r['label']:8s} numeric={r['numeric']} "
                      f"text={r['text']!r} implies={r['implies']}")

        imp_x = read_xlsm_impedance(a["xlsm"])
        imp_t = read_txt_impedance(a["txt"])
        elec_t = imp_t[imp_t.n <= N_ELECTRODES]
        print(f"\n  impedance: txt {len(imp_t)} entries "
              f"({len(elec_t)} electrodes + {len(imp_t) - len(elec_t)} ref/gnd pins)")
        if imp_x is not None:
            j = elec_t.merge(imp_x[imp_x.n <= N_ELECTRODES], on=["label", "n"])
            mismatch = j[j.z_txt != j.z_xlsm]
            print(f"  txt vs xlsm impedance : {len(j)} labels joined, "
                  f"{len(mismatch)} disagree")
            for _, r in mismatch.head(5).iterrows():
                print(f"      {r['label']:8s} txt={r.z_txt} xlsm={r.z_xlsm}")

        amap = read_xlsm_arraymap(a["xlsm"])
        if amap:
            from collections import Counter
            want = Counter(int(z) for z in elec_t.z_txt)
            got = Counter(int(v) for v in amap if 0 < v < 100_000)
            only_map = got - want
            only_txt = want - got
            print(f"  array map: {len(amap)} numeric cells; "
                  f"{sum((got & want).values())} values match the txt multiset, "
                  f"{sum(only_map.values())} extra, {sum(only_txt.values())} absent")
            if only_txt:
                print(f"      absent from map: {dict(list(only_txt.items())[:6])}")
            if only_map:
                print(f"      extra in map  : {dict(list(only_map.items())[:6])}")

        summary.append(dict(serial=a["serial"], implant=a["implant"],
                            array=a["array"],
                            cmp_defects=len(cmp_issues),
                            vacant=str(vac),
                            rewired=set(vac) != {(0, 0), (0, 9), (9, 0), (9, 9)},
                            pad_mismatches=(len(geo) if pad is not None else None),
                            xlsm_vs_cmp=len(diff_raw) if xl is not None else None))

    banner("Summary")
    print(pd.DataFrame(summary).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

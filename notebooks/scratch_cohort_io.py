"""Subject-agnostic loading for the six-subject cohort (session S07).

The session 4/5 code is Rocky-shaped: two arrays named Anterior and Posterior,
one CMP pair, `.ns5` for broadband, one implant. None of that survives contact
with the cohort — Fisk's broadband is `.ns6` and its LFP `.ns3`, Rocky has two
implants that reuse the same two array labels, and Picasso has no Blackrock at
all. This module moves every one of those facts into `configs/subjects/*.json`
and reads them at run time.

It also validates probe geometry rather than trusting it. CLAUDE.md's standing
warning is that channel-order mismatch is silent and ruinous; the same is true
of *position* mismatch, which is subtler because the channel order can be
perfectly correct while the electrode sits in the wrong place on the grid. A
Utah-96 map has a known shape — 10x10 minus four corners, 96 unique positions,
96 unique labels — and any deviation is a defect in the file.

Run from repo root:

    uv run python notebooks/scratch_cohort_io.py --validate
    uv run python notebooks/scratch_cohort_io.py --regress

See:
- docs/cohort_plan.md
- docs/notes/utah_channel_mapping.md
"""

from __future__ import annotations

import argparse
import json
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO / "configs" / "subjects"
PROBE_DIR = REPO / "configs" / "probes"
ROCKY_PREIMPLANT = Path(r"D:\Claude Code\Rocky\preimplant")

# A Utah-96 sits on a 10x10 grid with the four corners unpopulated.
GRID = 10
MISSING_CORNERS = {(0, 0), (0, GRID - 1), (GRID - 1, 0), (GRID - 1, GRID - 1)}
N_ELECTRODES = 96


def banner(t: str) -> None:
    print()
    print("=" * 74)
    print(t)
    print("=" * 74)


# %%
# === Subject configuration ===
def load_subject(name: str) -> dict:
    """Read one subject's registry entry written by `scratch_cohort_registry.py`."""
    p = CONFIG_DIR / f"{name.lower()}.json"
    if not p.exists():
        raise FileNotFoundError(f"no registry for {name!r}; run scratch_cohort_registry.py")
    return json.loads(p.read_text(encoding="utf-8"))


def stream_ext(subject: str, role: str = "broadband") -> str | None:
    """Which file extension carries a given signal for this subject.

    ``broadband`` is ``.ns5`` for five subjects and ``.ns6`` for Fisk, so this
    must never be hardcoded. Returns None when the subject has no such stream.
    """
    return load_subject(subject)["streams"].get(role)


def implant_for(subject: str, date: str) -> dict | None:
    """The implant in place on a given date, by surgery order."""
    imps = load_subject(subject)["implants"]
    chosen = imps[0]
    for imp in imps:
        s = imp.get("surgery_date")
        if isinstance(s, str) and date >= s:
            chosen = imp
    return chosen


def implant_age_days(subject: str, date: str) -> float | None:
    """Days since this implant's own surgery, which is the longitudinal axis.

    Calendar date is the wrong axis for cross-subject comparison and actively
    misleading within Rocky, whose second implant starts at age zero in 2025.
    """
    imp = implant_for(subject, date)
    s = imp.get("surgery_date") if imp else None
    if not isinstance(s, str):
        return None
    return (pd.Timestamp(date) - pd.Timestamp(s)).days


# %%
# === Probe geometry ===
def parse_cmp(path: Path) -> pd.DataFrame:
    """Parse a Blackrock CMP into electrode_id -> (col, row, bank, elec, label).

    Parameters
    ----------
    path : Path
        The `.cmp` mapfile shipped with the array.

    Returns
    -------
    pandas.DataFrame
        One row per electrode. ``electrode_id = (bank - 'A') * 32 + elec`` is
        the NEV channel id; ``label`` is the manufacturer's ``elecN`` and is
        deliberately a different number (see utah_channel_mapping.md).
    """
    rows = []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        p = ln.split()
        if len(p) >= 4 and p[0].isdigit() and p[1].isdigit() and p[3].isdigit():
            col, row, bank, elec = int(p[0]), int(p[1]), p[2].upper(), int(p[3])
            rows.append(dict(
                col=col, row=row, bank=bank, elec=elec,
                label=p[4] if len(p) >= 5 else "",
                electrode_id=(ord(bank) - ord("A")) * 32 + elec,
            ))
    return pd.DataFrame(rows)


def validate_cmp(cmp_df: pd.DataFrame) -> list[str]:
    """Every way a Utah-96 mapfile can be wrong, checked explicitly.

    Returns a list of human-readable problems; empty means the file is sound.
    Position errors are the dangerous kind: bank and elec can be perfectly
    correct -- so the sort is fine -- while the electrode sits in the wrong
    grid square, which silently corrupts spatial maps and any adjacency test.
    """
    issues: list[str] = []
    n = len(cmp_df)
    if n != N_ELECTRODES:
        issues.append(f"{n} electrodes, expected {N_ELECTRODES}")

    pos = list(zip(cmp_df.col, cmp_df.row, strict=True))
    dupes = {p for p in pos if pos.count(p) > 1}
    if dupes:
        issues.append(f"duplicate grid positions: {sorted(dupes)}")

    occupied = set(pos)
    on_corner = occupied & MISSING_CORNERS
    if on_corner:
        issues.append(f"electrodes on unpopulated corners: {sorted(on_corner)}")

    expected = {(c, r) for c in range(GRID) for r in range(GRID)} - MISSING_CORNERS
    missing = expected - occupied
    if missing:
        issues.append(f"grid positions with no electrode: {sorted(missing)}")

    out_of_range = cmp_df[(cmp_df.col >= GRID) | (cmp_df.row >= GRID)]
    if len(out_of_range):
        issues.append(f"{len(out_of_range)} positions outside the {GRID}x{GRID} grid")

    if cmp_df.electrode_id.duplicated().any():
        d = cmp_df.electrode_id[cmp_df.electrode_id.duplicated()].tolist()
        issues.append(f"duplicate electrode_id: {sorted(set(d))}")
    if cmp_df.label.duplicated().any():
        d = cmp_df.label[cmp_df.label.duplicated()].tolist()
        issues.append(f"duplicate label: {sorted(set(d))}")
    bad_bank = set(cmp_df.bank) - set("ABCD")
    if bad_bank:
        issues.append(f"unexpected bank values: {sorted(bad_bank)}")
    bad_elec = cmp_df[(cmp_df.elec < 1) | (cmp_df.elec > 32)]
    if len(bad_elec):
        issues.append(f"{len(bad_elec)} elec values outside 1..32")
    return issues


def repair_cmp(cmp_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Repair single-digit position typos, matching on the intact coordinate.

    A dropped digit puts an electrode on an unpopulated corner and leaves a
    real grid square empty. The repair is unambiguous when each corner shares
    exactly one coordinate with exactly one vacancy: `(0, 9)` with a vacant
    `(8, 9)` can only be a col 8 -> 0 slip, since the row is intact.

    Never applied silently -- the returned list is logged by the caller and
    written into the session record.
    """
    df = cmp_df.copy()
    fixes: list[str] = []
    occupied = set(zip(df.col, df.row, strict=True))
    expected = {(c, r) for c in range(GRID) for r in range(GRID)} - MISSING_CORNERS
    vacancies = sorted(expected - occupied)
    on_corner = sorted(occupied & MISSING_CORNERS)

    for c, r in on_corner:
        cands = [v for v in vacancies if v[0] == c or v[1] == r]
        if len(cands) != 1:
            fixes.append(f"AMBIGUOUS: ({c},{r}) matches {cands}; left as-is")
            continue
        nc, nr = cands[0]
        mask = (df.col == c) & (df.row == r)
        lbl = df.loc[mask, "label"].iloc[0]
        df.loc[mask, ["col", "row"]] = [nc, nr]
        vacancies.remove((nc, nr))
        fixes.append(f"{lbl}: ({c},{r}) -> ({nc},{nr})")
    return df, fixes


def load_probe_map(path: Path, repair: bool = True) -> tuple[pd.DataFrame, list[str]]:
    """Parse, validate and optionally repair one CMP. Returns (df, notes)."""
    df = parse_cmp(path)
    issues = validate_cmp(df)
    notes = [f"ISSUE: {i}" for i in issues]
    if issues and repair:
        df, fixes = repair_cmp(df)
        notes += [f"REPAIR: {f}" for f in fixes]
        remaining = validate_cmp(df)
        notes += [f"UNRESOLVED: {i}" for i in remaining]
    return df, notes


def find_cmp_files() -> list[Path]:
    """Every CMP available to the project, repo copies first."""
    out = sorted(PROBE_DIR.glob("*.cmp"))
    if ROCKY_PREIMPLANT.exists():
        out += sorted(ROCKY_PREIMPLANT.glob("*.cmp"))
    return out


# %%
# === Validation report ===
def run_validation() -> int:
    """Validate every CMP the project can see, and diff siblings."""
    files = find_cmp_files()
    banner(f"Validating {len(files)} CMP files")
    maps: dict[str, pd.DataFrame] = {}
    n_bad = 0
    for p in files:
        df, notes = load_probe_map(p, repair=True)
        serial = re.search(r"(\d{4}-\d{6})", p.name)
        key = serial.group(1) if serial else p.stem
        maps[key] = df
        status = "OK" if not notes else "DEFECT"
        print(f"\n  {p.name:34s} {len(df):3d} electrodes   {status}")
        for n in notes:
            print(f"      {n}")
        if notes:
            n_bad += 1

    banner("Are the arrays geometrically identical?")
    # Blackrock auto-generates these from one template, so a genuine difference
    # between two arrays is itself worth knowing about.
    keys = sorted(maps)
    base = maps[keys[0]]
    for k in keys[1:]:
        m = base.merge(maps[k], on="label", suffixes=("_a", "_b"))
        diff = m[(m.col_a != m.col_b) | (m.row_a != m.row_b)
                 | (m.electrode_id_a != m.electrode_id_b)]
        print(f"  {keys[0]} vs {k:14s} {len(m):3d} labels matched, "
              f"{len(diff):2d} differ")
        for _, r in diff.head(6).iterrows():
            print(f"      {r['label']:8s} ({r.col_a},{r.row_a}) id={r.electrode_id_a}"
                  f"   vs ({r.col_b},{r.row_b}) id={r.electrode_id_b}")

    banner("Summary")
    print(f"  {len(files) - n_bad} of {len(files)} CMP files sound")
    return 0


# %%
# === Regression against the session 4/5 pipeline ===
def run_regression() -> int:
    """Confirm the config-driven path reproduces the Rocky-specific one."""
    import sys

    sys.path.insert(0, str(REPO / "notebooks"))
    from scratch_rocky_resort import baseline_noise_uv, open_nev, read_electrode
    from scratch_rocky_spatial import CMP_BY_ARRAY
    from scratch_rocky_spatial import parse_cmp as old_parse_cmp

    banner("CMP parity: new parser vs the session 4/5 one")
    for arr, p in CMP_BY_ARRAY.items():
        if not Path(p).exists():
            print(f"  {arr:10s} SKIP (not staged): {p}")
            continue
        old = old_parse_cmp(Path(p)).sort_values("electrode_id").reset_index(drop=True)
        new = parse_cmp(Path(p)).sort_values("electrode_id").reset_index(drop=True)
        cols = ["col", "row", "bank", "elec", "label", "electrode_id"]
        same = old[cols].equals(new[cols])
        print(f"  {arr:10s} {len(old)} electrodes   identical={same}")
        if not same:
            print(old[cols].compare(new[cols]).head(10).to_string())

    banner("Stream resolution from config")
    for s in ["Rocky", "Nigel", "Fisk", "Picasso"]:
        cfg = load_subject(s)
        print(f"  {s:9s} broadband={cfg['streams']['broadband']}  "
              f"lfp={cfg['streams']['lfp']}  snippets={cfg['streams']['snippets']}")

    banner("Implant assignment and age")
    for s, d in [("Rocky", "2018-04-26"), ("Rocky", "2024-03-29"),
                 ("Rocky", "2025-04-04"), ("Rocky", "2025-06-05"),
                 ("Nigel", "2023-03-17"), ("Fisk", "2024-06-19")]:
        imp = implant_for(s, d)
        age = implant_age_days(s, d)
        print(f"  {s:7s} {d}  -> {imp['implant']}  "
              f"arrays={list(imp['arrays'])}  "
              f"age={'unknown' if age is None else f'{age} d'}")

    banner("Loading one Rocky session through the config-driven path")
    idx_p = REPO / "data" / "derived" / "rocky" / "session_index.parquet"
    if not idx_p.exists():
        print("  SKIP: Rocky session index not present")
        return 0
    idx = pd.read_parquet(idx_p)
    row = idx[(idx.date == "2018-04-26") & (idx.array == "Anterior")
              & (idx.kind == "OFS")]
    if not len(row):
        print("  SKIP: reference session not in index")
        return 0
    p = Path(row.iloc[0]["path"])
    raw, meta, cbe = open_nev(p)
    noises = []
    for elec in sorted(cbe):
        e = read_electrode(raw, meta, cbe[elec])
        if e is not None and len(e["t"]) >= 50:
            noises.append(baseline_noise_uv(e["wf"], meta["nbefore"]))
    print(f"  {p.name}")
    print(f"    electrodes {len(noises)}   median noise {np.median(noises):.2f} uV")
    print("    session 5 reported: 96 electrodes, median noise 9.82 uV")
    ok = len(noises) == 96 and abs(np.median(noises) - 9.82) < 0.01
    print(f"    REGRESSION {'PASS' if ok else 'FAIL'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--regress", action="store_true")
    args = ap.parse_args()
    if args.validate:
        run_validation()
    if args.regress:
        run_regression()
    if not (args.validate or args.regress):
        run_validation()
        run_regression()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

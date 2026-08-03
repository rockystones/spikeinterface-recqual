"""Build the session index for the Rocky snippet cohort.

The Rocky dataset is snippet-only: 886 in-scope `.nev` files spanning
2017-09-21 to 2023-10-06, with no continuous broadband anywhere. This script
does no sorting -- it produces the index every later step joins against.

Three date conventions coexist and must all be parsed:
  MM-DD-YYYY   .nev, 2017-2020   e.g. Rocky_Anterior_01-03-2019_Baseline_AnalogHeadstage
  YYYY-MM-DD   .nev, 2022-2023   e.g. Rocky_Anterior_2022-07-06_Baseline_DigitalHeadstage
  YYYYMMDD     impedance folders e.g. 20190228

Run from repo root:

    uv run python notebooks/scratch_rocky_inventory.py [--probe-n N] [--no-probe]

  --probe-n N   parse NEV headers for at most N files (default: all originals)
  --no-probe    skip header parsing entirely (filename-only index)

See:
- docs/session_plans/session04_rocky_resort.md
- docs/notes/snippet_sorting.md
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import warnings
from collections import Counter
from pathlib import Path

import pandas as pd
from neo.rawio import BlackrockRawIO

warnings.filterwarnings(
    "ignore", message="Detected .* undocumented segments within nev data"
)

REPO = Path(__file__).resolve().parent.parent
ROCKY = Path(r"D:\Claude Code\Rocky")
OUT_DIR = REPO / "data" / "derived" / "rocky"
INDEX_OUT = OUT_DIR / "session_index.parquet"

# Serial -> array, per user confirmation. Both maps are geometrically
# identical; this assignment is provenance only, but the impedance join
# depends on it being right.
SERIAL_BY_ARRAY = {"Anterior": "SN 1025-001501", "Posterior": "SN 1025-001497"}

EXCLUDE_YEARS = {"2025"}  # user scoped this session to 2017-2023

DATE_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
DATE_US = re.compile(r"(\d{2})-(\d{2})-(\d{4})")
DATE_COMPACT = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
SPIKE_CHANNEL_NAME_RE = re.compile(r"^ch(?P<elec>\d+)#(?P<unit>\d+)$")


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# === Date parsing: three conventions across the cohort ===
def parse_date(text: str) -> str | None:
    """Extract an ISO date from a filename or folder name.

    Handles all three conventions in the cohort. ISO is tried first because
    ``2022-07-06`` would otherwise be mis-read by the US pattern.

    Parameters
    ----------
    text : str
        Filename stem or folder name.

    Returns
    -------
    str or None
        ``YYYY-MM-DD``, or None if no date is present.
    """
    m = DATE_ISO.search(text)
    if m:
        return "{}-{}-{}".format(*m.groups())
    m = DATE_US.search(text)
    if m:
        mo, d, y = m.groups()
        return f"{y}-{mo}-{d}"
    m = DATE_COMPACT.match(text.strip())
    if m:
        return "{}-{}-{}".format(*m.groups())
    return None


def classify_nev(stem: str) -> dict:
    """Parse one NEV filename into its metadata fields.

    Parameters
    ----------
    stem : str
        Filename without extension.

    Returns
    -------
    dict
        Keys ``array``, ``date``, ``year``, ``headstage``, ``kind``.
        ``kind`` is ``ORIG`` (unsorted original), ``OFS`` (Plexon
        Offline Sorter output, ``-01`` suffix), or ``MA``.
    """
    array = (
        "Anterior" if "Anterior" in stem
        else "Posterior" if "Posterior" in stem
        else "unknown"
    )
    date = parse_date(stem)
    headstage = (
        "Analog" if "AnalogHeadstage" in stem
        else "Digital" if "DigitalHeadstage" in stem
        else "none"
    )
    kind = "OFS" if stem.endswith("-01") else ("MA" if "-MA" in stem else "ORIG")
    return dict(
        array=array,
        date=date,
        year=date[:4] if date else None,
        headstage=headstage,
        kind=kind,
    )


# === NEV header probe ===
def probe_nev_header(path: Path) -> dict:
    """Read a NEV header and summarise its spike channels.

    Unit ids live in the NEO ``spike_channels`` names (``chE#U``), so the
    header alone reveals whether a file is genuinely unsorted -- no need to
    read the waveform payload.

    Parameters
    ----------
    path : Path
        Path to the .nev file.

    Returns
    -------
    dict
        ``n_spike_channels``, ``n_electrodes``, ``unit_ids`` (sorted unique),
        ``duration_s``, ``wf_gain``, ``wf_left_sweep``, ``probe_error``.
    """
    try:
        raw = BlackrockRawIO(filename=str(path.with_suffix("")))
        raw.parse_header()
        chans = raw.header["spike_channels"]
        elecs, units = set(), set()
        for ch in chans:
            m = SPIKE_CHANNEL_NAME_RE.match(str(ch["name"]))
            if m:
                elecs.add(int(m["elec"]))
                units.add(int(m["unit"]))
        nseg = raw.segment_count(block_index=0)
        dur = sum(
            raw.segment_t_stop(0, s) - raw.segment_t_start(0, s) for s in range(nseg)
        )
        first = chans[0] if len(chans) else None
        return dict(
            n_spike_channels=len(chans),
            n_electrodes=len(elecs),
            unit_ids=",".join(str(u) for u in sorted(units)),
            n_segments=nseg,
            duration_s=round(float(dur), 2),
            wf_gain=float(first["wf_gain"]) if first is not None else None,
            wf_left_sweep=int(first["wf_left_sweep"]) if first is not None else None,
            probe_error="",
        )
    except Exception as e:  # noqa: BLE001 - want the message, not a crash
        return dict(
            n_spike_channels=None, n_electrodes=None, unit_ids=None,
            n_segments=None, duration_s=None, wf_gain=None,
            wf_left_sweep=None, probe_error=f"{type(e).__name__}: {e}",
        )


# === Impedance folder index ===
def index_impedance(root: Path) -> dict[tuple[str, str], list[str]]:
    """Map (date, array) -> impedance .txt paths.

    Impedance lives in per-date folders whose names use a third date
    convention (``YYYYMMDD``) alongside ``MM-DD-YYYY``. Files are named
    ``{Anterior,Posterior}_{A,B,C}{1,2}.txt`` -- 6 per array, 16 electrodes
    each, 96 total.

    Parameters
    ----------
    root : Path
        Rocky dataset root.

    Returns
    -------
    dict
        ``(date, array)`` -> sorted list of absolute paths.
    """
    out: dict[tuple[str, str], list[str]] = {}
    for txt in root.rglob("*.txt"):
        folder_date = parse_date(txt.parent.name)
        if folder_date is None:
            continue
        name = txt.stem
        if name.startswith("Anterior"):
            array = "Anterior"
        elif name.startswith("Posterior"):
            array = "Posterior"
        else:
            continue  # e.g. "CORRECT BOX CONNECTION.txt"
        out.setdefault((folder_date, array), []).append(str(txt))
    for k in out:
        out[k].sort()
    return out


# === Main ===
def main() -> int:
    """Build and write the Rocky session index."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-n", type=int, default=None,
                    help="Parse headers for at most N files (default: all originals).")
    ap.add_argument("--no-probe", action="store_true",
                    help="Skip NEV header parsing entirely.")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    banner("Step 1  scan filenames")
    t0 = time.perf_counter()
    records: list[dict] = []
    for p in ROCKY.rglob("*.nev"):
        rec = classify_nev(p.stem)
        rec["path"] = str(p)
        rec["stem"] = p.stem
        rec["size_mb"] = round(p.stat().st_size / 1024 / 1024, 2)
        rec["serial"] = SERIAL_BY_ARRAY.get(rec["array"], "")
        records.append(rec)
    df = pd.DataFrame(records)
    print(f"  found {len(df)} .nev in {time.perf_counter() - t0:.1f} s")

    n_nodate = int(df["date"].isna().sum())
    print(f"  unparsed dates: {n_nodate}")
    if n_nodate:
        for s in df.loc[df["date"].isna(), "stem"].head(5):
            print(f"    {s}")

    # Scope filter: user excluded 2025
    df["in_scope"] = df["year"].notna() & ~df["year"].isin(EXCLUDE_YEARS)
    scoped = df[df["in_scope"]].copy()
    print(f"  in scope (2017-2023): {len(scoped)}")
    print(f"  kinds: {dict(Counter(scoped['kind']))}")

    banner("Step 2  duplicate detection")
    dup = scoped.groupby("stem").size()
    dup = dup[dup > 1]
    print(f"  stems appearing more than once: {len(dup)}")
    if len(dup):
        for stem, n in dup.head(5).items():
            print(f"    {stem}  x{n}")
        print("  (duplicates kept; 'path' disambiguates)")

    banner("Step 3  pairing (ORIG + OFS per date-array)")
    combos = scoped.groupby(["date", "array"])["kind"].agg(set)
    paired = combos[combos.apply(lambda s: "ORIG" in s and "OFS" in s)]
    orig_only = combos[combos.apply(lambda s: "ORIG" in s and "OFS" not in s)]
    ofs_only = combos[combos.apply(lambda s: "OFS" in s and "ORIG" not in s)]
    print(f"  date-array combos : {len(combos)}")
    print(f"    paired ORIG+OFS : {len(paired)}")
    print(f"    ORIG only       : {len(orig_only)}")
    print(f"    OFS only        : {len(ofs_only)}")
    for arr in ("Anterior", "Posterior"):
        d = sorted(scoped.loc[scoped["array"] == arr, "date"].dropna().unique())
        print(f"  {arr}: {len(d)} dates  {d[0]} .. {d[-1]}")
    print()
    print("  paired per year:", dict(sorted(
        Counter(d[:4] for d, _ in paired.index).items()
    )))

    banner("Step 4  impedance folders")
    imp = index_impedance(ROCKY)
    print(f"  (date, array) keys with impedance: {len(imp)}")
    n_six = sum(1 for v in imp.values() if len(v) == 6)
    print(f"    with exactly 6 files: {n_six}")
    counts = Counter(len(v) for v in imp.values())
    print(f"    files-per-key distribution: {dict(sorted(counts.items()))}")
    scoped["impedance_files"] = [
        "|".join(imp.get((d, a), []))
        for d, a in zip(scoped["date"], scoped["array"], strict=True)
    ]
    scoped["has_impedance"] = scoped["impedance_files"].str.len() > 0
    matched = scoped.groupby(["date", "array"])["has_impedance"].first()
    print(f"  date-array combos with impedance: {int(matched.sum())} / {len(matched)}")

    banner("Step 5  NEV header probe")
    if args.no_probe:
        print("  skipped (--no-probe)")
        probe_df = pd.DataFrame()
    else:
        targets = scoped[scoped["kind"] == "ORIG"]
        if args.probe_n:
            targets = targets.head(args.probe_n)
        print(f"  parsing headers for {len(targets)} original files ...")
        t0 = time.perf_counter()
        rows = []
        for i, (idx, row) in enumerate(targets.iterrows(), 1):
            info = probe_nev_header(Path(row["path"]))
            info["_idx"] = idx
            rows.append(info)
            if i % 50 == 0 or i == len(targets):
                el = time.perf_counter() - t0
                print(f"    {i}/{len(targets)}  {el:.0f} s elapsed  "
                      f"({el / i * 1000:.0f} ms/file)")
        probe_df = pd.DataFrame(rows).set_index("_idx")
        for c in probe_df.columns:
            scoped.loc[probe_df.index, c] = probe_df[c]

        errs = probe_df["probe_error"].astype(str).str.len() > 0
        print(f"  header parse errors: {int(errs.sum())}")
        for m in probe_df.loc[errs, "probe_error"].head(3):
            print(f"    {m}")

        banner("Step 5b  are the ORIGINAL files truly unsorted?")
        uid = probe_df.loc[~errs, "unit_ids"].astype(str)
        print("  distinct unit-id signatures across originals:")
        for sig, n in Counter(uid).most_common(8):
            label = "unsorted only" if sig == "0" else "CARRIES SORT LABELS"
            print(f"    {sig[:44]:46s} x{n:4d}   <- {label}")

    banner("Step 6  write index")
    out = scoped.drop(columns=["in_scope"])
    out.to_parquet(INDEX_OUT, engine="pyarrow", index=False)
    print(f"  wrote {INDEX_OUT}  ({INDEX_OUT.stat().st_size / 1024:.1f} KB)  "
          f"rows={len(out)}  cols={len(out.columns)}")

    banner("Assertions")
    ok = True
    for label, got, want in (
        ("in-scope NEV", len(scoped), 886),
        ("paired date-array combos", len(paired), 332),
    ):
        status = "OK " if got == want else "FAIL"
        if got != want:
            ok = False
        print(f"  [{status}] {label}: {got} (expected {want})")
    print()
    print("INVENTORY OK" if ok else "INVENTORY MISMATCH - investigate before scaling")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Turn the multi-volume file census into an analysis registry (session S06).

The census (`_monkey-ephys.csv`, 979,044 rows over 25 volumes) is a storage
inventory. This turns it into the thing every later session indexes against:
one row per acquisition file the analysis will actually read, keyed by
`(subject, implant, array, date)` rather than by path.

Three things make that non-trivial, and each is a silent-error source:

1. **Rocky has two implants whose filenames are identical.** Both write
   `Rocky_Anterior_<date>_Baseline_DigitalHeadstage.nev`, but the 2025 files
   come from `SN 1025-004377`/`004419` implanted 2025-03-26, not from the
   2017 pair. Keying on filename alone merges two physical arrays into one
   series and reads a fresh implant as a recovery of the old one.
2. **Every subject dates its files differently**, and two of them do not date
   them at all -- Luigi and Oops Blackrock files are `datafileNNN.nev`, so
   their dates live in the NEV header and cannot be recovered from the census.
3. **Stream ids are not constant.** Fisk's broadband is `.ns6` and its LFP
   `.ns3`; the other five use `.ns5`. CLAUDE.md's "ns5 = broadband" rule holds
   for four subjects and not for Fisk.

Outputs:

    configs/subjects/<subject>.json   per-subject registry, hand-editable
    data/derived/cohort_index.parquet one row per distinct acquisition file
    data/derived/staging_manifest.csv what to copy, from where, in what order

Run from repo root:

    uv run python notebooks/scratch_cohort_registry.py [--census <path>]

See:
- docs/cohort_plan.md
"""

from __future__ import annotations

import argparse
import json
import re
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
CENSUS = Path(r"C:\Users\shide\Downloads\VirtualMachineTransientShare\_monkey-ephys.csv")
CONFIG_DIR = REPO / "configs" / "subjects"
OUT_DIR = REPO / "data" / "derived"
INDEX_OUT = OUT_DIR / "cohort_index.parquet"
MANIFEST_OUT = OUT_DIR / "staging_manifest.csv"

SUBJECTS = ["Rocky", "Oops", "Luigi", "Picasso", "Nigel", "Fisk"]

# Extensions that carry signal. Everything else in the estate -- .mda exports,
# sort intermediates, .mat, firings -- is regenerable from these and is
# deliberately out of scope, which is what turns 11.5 TiB into ~2 TiB.
ACQ_EXT = {
    "ns1": "lfp", "ns2": "lfp", "ns3": "lfp", "ns4": "broadband",
    "ns5": "broadband", "ns6": "broadband",
    "nev": "snippets", "ccf": "config",
    "sev": "tdt_stream", "tev": "tdt_stream", "tsq": "tdt_index",
    "tbk": "tdt_index", "tdx": "tdt_index",
    "plx": "sorted_ref", "pl2": "sorted_ref",
}

# What is known about each subject. Serial-to-array assignments come from the
# CMP filenames and the surgery folders; anything not established is left null
# rather than guessed, and reported as an open item at the end.
REGISTRY: dict[str, dict] = {
    "Rocky": dict(
        acquisition=["blackrock", "tdt"],
        streams=dict(broadband="ns5", lfp=None, snippets="nev"),
        implants=[
            dict(implant="I1", surgery_date=None, hemisphere=None,
                 arrays={"Anterior": "1025-001501", "Posterior": "1025-001497"},
                 date_range=["2017-09-01", "2024-03-29"]),
            # Implant 2 reuses the Anterior/Posterior labels, so the serials
            # cannot be inferred from the filenames. Which of 004377 / 004419
            # is Anterior is an open item; recorded as null rather than guessed.
            dict(implant="I2", surgery_date="2025-03-26", hemisphere="Right",
                 arrays={"Anterior": None, "Posterior": None},
                 serials_unassigned=["1025-004377", "1025-004419"],
                 date_range=["2025-04-04", "2025-06-05"]),
        ],
        date_from="filename",
    ),
    "Nigel": dict(
        acquisition=["blackrock"],
        streams=dict(broadband="ns5", lfp=None, snippets="nev"),
        implants=[dict(implant="I1", surgery_date=None, hemisphere=None,
                       arrays={"Anterior": None, "Posterior": None},
                       date_range=["2023-01-24", "2024-12-16"])],
        date_from="filename",
    ),
    "Fisk": dict(
        acquisition=["blackrock"],
        streams=dict(broadband="ns6", lfp="ns3", snippets="nev"),
        implants=[dict(implant="I1", surgery_date=None, hemisphere="Right",
                       arrays={"Lateral": "1025-001498", "Medial": "1025-001504"},
                       date_range=["2023-06-05", "2025-05-07"])],
        date_from="filename",
    ),
    "Oops": dict(
        acquisition=["tdt", "blackrock"],
        streams=dict(broadband="ns5", lfp=None, snippets="nev"),
        implants=[dict(implant="I1", surgery_date=None, hemisphere=None,
                       arrays={"Anterior": None, "Posterior": None},
                       date_range=["2015-04-08", "2017-01-18"])],
        date_from="tank_folder",
    ),
    "Picasso": dict(
        acquisition=["tdt"],
        streams=dict(broadband=None, lfp=None, snippets=None),
        implants=[dict(implant="I1", surgery_date=None, hemisphere=None,
                       arrays={"Anterior": None, "Posterior": None},
                       date_range=["2016-04-15", "2017-12-05"])],
        date_from="tank_folder",
    ),
    "Luigi": dict(
        acquisition=["tdt", "blackrock"],
        streams=dict(broadband="ns5", lfp=None, snippets="nev"),
        implants=[dict(implant="I1", surgery_date=None, hemisphere=None,
                       arrays={}, date_range=["2015-05-05", "2016-01-14"])],
        # Tanks are Block-NN and Blackrock files are datafileNNN: neither
        # carries a date. Both must be read from headers in a later session.
        date_from="header",
    ),
}


def banner(t: str) -> None:
    print()
    print("=" * 74)
    print(t)
    print("=" * 74)


# %%
# === Date extraction ===
# One pattern set per filing convention actually observed in this estate.
RX_YMD = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")                # 2023-07-27
RX_MDY = re.compile(r"(?<!\d)(\d{2})-(\d{2})-(20\d{2})(?!\d)")   # 04-26-2018
RX_COMPACT = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})-\d{6}")  # 20250123-100251
RX_TANK = re.compile(r"(20\d{2})_0?(\d{1,2})_(\d{2})")            # 2016_07_29, 2017_010_02


def parse_date(path: str) -> tuple[str | None, str | None]:
    """Best date for one file, and which convention produced it.

    Returns ``(iso_date, convention)``; ``(None, None)`` when the filename
    carries no date, which is itself information -- Luigi's tanks and the
    ``datafileNNN`` Blackrock files land here and need header reads.
    """
    for rx, name, order in (
        (RX_COMPACT, "compact_time", "ymd"),
        (RX_YMD, "iso", "ymd"),
        (RX_MDY, "us", "mdy"),
        (RX_TANK, "tank", "ymd"),
    ):
        m = rx.search(path)
        if not m:
            continue
        g = m.groups()
        y, mo, dy = (g[0], g[1], g[2]) if order == "ymd" else (g[2], g[0], g[1])
        try:
            y, mo, dy = int(y), int(mo), int(dy)
        except ValueError:
            continue
        if 2000 <= y <= 2030 and 1 <= mo <= 12 and 1 <= dy <= 31:
            return f"{y:04d}-{mo:02d}-{dy:02d}", name
    return None, None


def known_arrays(subject: str) -> set[str]:
    """Every array label this subject's registry declares, across implants."""
    return {a for imp in REGISTRY[subject]["implants"] for a in imp["arrays"]}


def parse_array(subject: str, path: str, fname: str) -> str | None:
    """Array label, from the filename for Blackrock or the folder for Fisk.

    Matched against the labels the registry declares rather than accepting any
    word in the slot: Rocky's TDT tanks are named `Rocky_baseline_...`, and a
    permissive regex reads `baseline` as an array. TDT files carry no array in
    the name at all -- both arrays share a tank -- so None is correct there.
    """
    m = re.match(rf"{subject}_([A-Za-z]+)_", fname)
    if m and m.group(1) in known_arrays(subject):
        return m.group(1)
    m = re.search(r"1025-1(\d{3}) \(Fisk [^)]*?(\w+)\)", path)
    if m and m.group(2) in known_arrays(subject):
        return m.group(2)
    return None


def parse_variant(fname: str) -> str:
    """Recording / processing variant encoded as a filename suffix.

    ``-MA`` appears on both arrays and on every 2025 Rocky date alongside the
    plain recording, so it is a second acquisition per session rather than an
    array. ``-NN`` is Plexon writing sorted output back beside the original.
    """
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", fname)
    ma = "-MA" in stem.upper()
    m = re.search(r"-(\d{2})$", stem)
    sortsuffix = m.group(1) if m else None
    if ma and sortsuffix:
        return f"MA-{sortsuffix}"
    if ma:
        return "MA"
    return sortsuffix or "base"


def assign_implant(subject: str, date: str | None) -> str | None:
    """Which implant a session belongs to, from its date.

    This is the step that keeps Rocky's two implants apart. Without it the
    2025 recordings append to the 2017 series and a new array reads as the old
    one recovering.
    """
    # pandas turns the undated None into NaN on assignment, so guard on type
    # rather than on None -- a float here would compare against a str and raise.
    if not isinstance(date, str):
        return None
    # Assign by surgery order, not by the observed date range: a range built
    # from the Blackrock era alone stranded 1,213 of Rocky's TDT files, which
    # start 2017-09-01. Everything before the next surgery belongs to the
    # implant in place at the time.
    imps = REGISTRY[subject]["implants"]
    chosen = imps[0]["implant"]
    for imp in imps:
        s = imp.get("surgery_date")
        if isinstance(s, str) and date >= s:
            chosen = imp["implant"]
    return chosen


# %%
# === Index construction ===
def build_index(census: Path) -> pd.DataFrame:
    """One row per distinct acquisition file, keyed for analysis."""
    df = pd.read_csv(census, low_memory=False)
    df["ext"] = df.path.str.extract(r"\.([A-Za-z0-9]{1,7})$", expand=False).str.lower()
    df["fname"] = df.path.str.rsplit("\\", n=1).str[-1]
    d = df[df.subject.isin(SUBJECTS) & df.ext.isin(ACQ_EXT)].copy()

    d["role"] = d.ext.map(ACQ_EXT)
    parsed = d.path.map(parse_date)
    d["date"] = [p[0] for p in parsed]
    d["date_convention"] = [p[1] for p in parsed]
    d["array"] = [parse_array(s, p, f)
                  for s, p, f in zip(d.subject, d.path, d.fname, strict=True)]
    d["implant"] = [assign_implant(s, dt)
                    for s, dt in zip(d.subject, d.date, strict=True)]
    d["variant"] = d.fname.map(parse_variant)
    # Plexon writes sorted output back into a -NN.nev beside the original.
    d["is_sorted_nev"] = d.fname.str.contains(r"-\d{2}\.nev$", case=False, regex=True)
    d["sig"] = d.fname + "|" + d.size_bytes.astype(str)
    d["gib"] = d.size_bytes / 2**30
    return d


def pick_source(d: pd.DataFrame) -> pd.DataFrame:
    """Collapse copies to one preferred source path per distinct file.

    Preference is the volume holding the most of that subject, so a session
    stages from as few drives as possible.
    """
    best = (d.groupby(["subject", "volume"])["sig"].nunique()
            .rename("vol_rank").reset_index())
    d = d.merge(best, on=["subject", "volume"], how="left")
    d = d.sort_values(["sig", "vol_rank"], ascending=[True, False])
    return d.drop_duplicates("sig", keep="first")


# %%
# === Outputs ===
def write_configs(idx: pd.DataFrame) -> None:
    """One JSON per subject: what it is, not where its bytes happen to sit."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    for s in SUBJECTS:
        g = idx[idx.subject == s]
        reg = REGISTRY[s]
        counts = g.groupby("role")["sig"].nunique().to_dict()
        vols = (g.groupby("volume")["sig"].nunique()
                .sort_values(ascending=False).head(3).to_dict())
        cfg = dict(
            subject=s,
            acquisition=reg["acquisition"],
            streams=reg["streams"],
            date_from=reg["date_from"],
            implants=reg["implants"],
            files_by_role={k: int(v) for k, v in counts.items()},
            distinct_files=int(g.sig.nunique()),
            distinct_gib=round(float(g.drop_duplicates("sig").gib.sum()), 1),
            dated_fraction=round(float(g.date.notna().mean()), 3),
            source_volumes={k: int(v) for k, v in vols.items()},
        )
        (CONFIG_DIR / f"{s.lower()}.json").write_text(
            json.dumps(cfg, indent=2), encoding="utf-8")


def staging_manifest(idx: pd.DataFrame) -> pd.DataFrame:
    """What to copy, in the order the session plan needs it.

    Priority follows docs/cohort_plan.md: the small Blackrock-only subjects
    first (whole subjects, ~1400 files), then Rocky's continuous data, then
    the TDT era.
    """
    order = {"Nigel": 1, "Fisk": 2, "Rocky": 3, "Picasso": 4, "Oops": 5, "Luigi": 6}
    m = idx.copy()
    m["session_priority"] = m.subject.map(order)
    m = m[["session_priority", "subject", "implant", "array", "date", "role",
           "variant", "ext", "gib", "volume", "path", "copies_in_corpus",
           "is_sorted_nev"]]
    return m.sort_values(["session_priority", "subject", "date", "role"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", type=str, default=str(CENSUS))
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    banner("Building cohort index")
    d = build_index(Path(args.census))
    print(f"  acquisition rows (all copies) {len(d):,}")
    idx = pick_source(d)
    print(f"  distinct files                {len(idx):,}")
    print(f"  total to stage                {idx.gib.sum():,.0f} GiB")

    banner("Per subject")
    hdr = f"{'subject':9s} {'files':>7s} {'GiB':>8s} {'dated':>6s} {'implants':>9s}  roles"
    print(hdr)
    print("-" * 96)
    for s in SUBJECTS:
        g = idx[idx.subject == s]
        roles = ", ".join(f"{k}:{v}" for k, v in
                          sorted(g.role.value_counts().items()))
        print(f"{s:9s} {len(g):7,} {g.gib.sum():8,.0f} "
              f"{g.date.notna().mean() * 100:5.0f}% "
              f"{g.implant.nunique():9d}  {roles}")

    banner("Date parsing: what the filenames do NOT tell us")
    und = idx[idx.date.isna()]
    print(f"  {len(und):,} of {len(idx):,} files carry no date in the path "
          f"({len(und) / len(idx) * 100:.0f}%)")
    print(und.groupby(["subject", "role"]).size().rename("files")
          .reset_index().to_string(index=False))
    print("\n  These need header reads, not better regexes. Luigi's tanks are")
    print("  Block-NN and its Blackrock files are datafileNNN; Oops shares the")
    print("  latter convention.")

    banner("Rocky: the two implants held apart")
    r = idx[(idx.subject == "Rocky") & idx.date.notna()]
    print(r.pivot_table(index="implant", columns="role", values="sig",
                        aggfunc="count", fill_value=0).to_string())
    print()
    for imp in REGISTRY["Rocky"]["implants"]:
        g = r[r.implant == imp["implant"]]
        if not len(g):
            continue
        print(f"  {imp['implant']}: {g.date.min()} .. {g.date.max()}  "
              f"{g.date.nunique()} dates  arrays={sorted(set(g.array.dropna()))}  "
              f"serials={list(imp['arrays'].values())}")
    orphan = idx[(idx.subject == "Rocky") & idx.date.notna() & idx.implant.isna()]
    if len(orphan):
        print(f"\n  {len(orphan)} dated Rocky files fall outside both implant "
              f"windows: {sorted(set(orphan.date))[:6]}")

    banner("Staging: fewest drives per subject")
    for s in SUBJECTS:
        g = idx[idx.subject == s]
        v = g.groupby("volume").agg(files=("sig", "count"), gib=("gib", "sum"))
        v = v.sort_values("files", ascending=False)
        top = ", ".join(f"{i} ({r.files:,} / {r.gib:,.0f} GiB)"
                        for i, r in v.head(2).iterrows())
        print(f"  {s:9s} {len(v)} volume(s) -> {top}")

    write_configs(idx)
    man = staging_manifest(idx)
    idx.to_parquet(INDEX_OUT, engine="pyarrow", index=False)
    man.to_csv(MANIFEST_OUT, index=False)

    banner("Written")
    print(f"  {INDEX_OUT.relative_to(REPO)}  ({len(idx):,} rows)")
    print(f"  {MANIFEST_OUT.relative_to(REPO)}  ({len(man):,} rows)")
    for p in sorted(CONFIG_DIR.glob("*.json")):
        print(f"  {p.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

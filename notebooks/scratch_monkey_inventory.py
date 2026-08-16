"""Inventory the staged Monkey Data drop, and test the stated naming convention.

The owner describes the convention as: original NEV, ``-01`` when sorted by
Plexon Offline Sorter, ``-02``/``DS`` for operator DS's manual curation, ``MA``
for operator Sidd's. Three subjects, four trees, and -- as it turns out -- three
mutually incompatible filename grammars.

This script does not assume the convention holds. It *discovers* every suffix
chain actually present, then reports which sessions carry which variants, so the
comparison work list is built from the files rather than from the description.

Run from repo root:

    uv run python notebooks/scratch_monkey_inventory.py

See:
- docs/notes/monkey_corpus.md
"""

from __future__ import annotations

import re
import struct
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(r"D:\Claude Code\Monkey Data")
REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "derived" / "monkey_inventory.parquet"
OUT_SESS = REPO / "data" / "derived" / "monkey_sessions_local.parquet"

# Trees as staged, mapped to (subject, implant). Rocky's two implants are
# separate trees, which is the only reason implant is knowable from the path.
TREES: dict[str, tuple[str, str | None]] = {
    "Nigel": ("Nigel", "I1"),
    "Fisk": ("Fisk", "I1"),
    "Rocky": ("Rocky", "I1"),
    "Rocky New": ("Rocky", "I2"),
}

# Roles keyed off the extension, after the variant chain is stripped.
ROLE_BY_EXT: dict[str, str] = {
    ".nev": "snippets",
    ".ns5": "broadband",
    ".ns3": "lfp",
    ".ccf": "config",
    ".scan": "ofs_scan",
    ".mat": "export_mat",
    ".ofb": "ofs_batch",
    ".log": "ofs_log",
    ".txt": "text",
    ".cmp": "mapfile",
    ".xlsm": "workbook",
    ".xlsx": "workbook",
    ".png": "figure",
    ".fig": "figure",
    ".jpg": "figure",
    ".pzfx": "prism",
    ".prism": "prism",
}


# Curation authorship, owner-ruled 2026-08-15. `-MADS` is Sidd's sort with DS's
# edits on top: one file, two operators in sequence, so it is evidence about
# neither operator alone and is excluded from the independent comparison.
DS_CHAINS = ("-02", "-DS")
MA_CHAINS = ("-MA", "-MA-01", "-MA-02", "-MA-RE")
SEQ_CHAINS = ("-MADS",)

# Names that parse to a valid but wrong date, so no rule can catch them. The
# NEV of this session is misspelt `2023-08-011` and is repaired by `parse_date`;
# its MATLAB export was named `2023-08-01`, which is a perfectly good date and
# therefore invisible. Both are the same recording, on 2023-08-11 -- confirmed
# by the NEV header clock, by the weekly series, and by the Posterior array's
# correctly-named file for the same day.
STEM_DATE_FIXES: dict[str, str] = {
    "Rocky_Anterior_2023-08-01_Baseline_DigitalHeadstage": "2023-08-11",
}


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === The authoritative date ===
def nev_time_origin(path: Path) -> pd.Timestamp | None:
    """Acquisition datetime from the NEV basic header. 44 bytes, no NEO.

    The header's ``TimeOrigin`` is a Windows SYSTEMTIME -- eight uint16 at byte
    offset 28 (year, month, day-of-week, day, hour, minute, second, ms). It is
    written by the NSP at acquisition, so it outranks the filename: filenames in
    this corpus use three date conventions, contain at least two typos, and for
    Nigel's terminal recordings carry no date at all.

    Returns None if the file is not a NEV or the field is not a valid date.
    """
    try:
        with path.open("rb") as fh:
            head = fh.read(44)
        if len(head) < 44 or not head.startswith(b"NEURALEV"):
            return None
        y, mo, _dow, d, hh, mi, ss, ms = struct.unpack("<8H", head[28:44])
        return pd.Timestamp(year=y, month=mo, day=d, hour=hh, minute=mi,
                            second=ss, microsecond=ms * 1000)
    except (OSError, ValueError, struct.error):
        return None


# %%
# === Filename grammar ===
# Three conventions coexist. Each returns (stem_key, date, fields) or None.

# Subject_Region_DATE[run]_[Condition]_[Headstage]. Everything after the date is
# optional -- the 2017-2018 Rocky files often stop at the date, and the tail slot
# sometimes holds an operator name rather than a headstage.
RE_LONG = re.compile(
    r"^(?P<subject>[A-Za-z]+)_(?P<region>Anterior|Posterior)_"
    r"(?P<date>\d{2}-\d{2,3}-\d{4}|\d{4}-\d{2}-\d{2,3})"
    r"(?P<run>[ab]?)"
    r"(?:_(?P<cond>[^_]+))?(?:_(?P<tail>.+))?$"
)
# Blackrock/Ripple default: YYYYMMDD-HHMMSS-NNN  (Fisk)
RE_STAMP = re.compile(r"^(?P<date>\d{8})-(?P<time>\d{6})-(?P<idx>\d{3})$")
# NSP default: datafileNNNN  (Nigel terminal recordings)
RE_DATAFILE = re.compile(r"^(?:NS5_)?datafile(?P<idx>\d+)\s*\d*$")

# The variant chain is whatever trailing -TOKEN groups sit before the extension.
# MADS must precede MA so the alternation does not consume only the first half.
RE_VARIANT = re.compile(
    r"^(?P<base>.*?)(?P<chain>(?:-(?:MADS|MA|DS|RE|\d{2}))+)$")


def split_variant(stem: str) -> tuple[str, str]:
    """Strip trailing sort/curation tokens. Returns (base_stem, chain).

    ``...DigitalHeadstage-MA-01`` -> (``...DigitalHeadstage``, ``-MA-01``).
    Fisk's ``20230605-132052-001`` must NOT lose its ``-001``, which is an
    acquisition index and not a variant -- the stamp grammar is checked first.
    """
    if RE_STAMP.match(stem):
        return stem, ""
    m = RE_VARIANT.match(stem)
    if not m or not m.group("base"):
        return stem, ""
    return m.group("base"), m.group("chain")


def parse_date(s: str) -> pd.Timestamp | None:
    """Parse the three date conventions in this corpus to one axis.

    One file pair is keyed ``2023-08-011``. Dropping the stray zero gives the
    11th, which fills the only gap in an otherwise weekly series (07-27, 08-04,
    --, 08-17, 08-24); reading it as the 1st would instead put three sessions in
    eight days. Repaired here rather than dropped, and flagged by `report_gaps`
    so the inference stays visible.
    """
    # Two files carry a 3-digit day with a stray leading zero, one in each date
    # convention: `2023-08-011` and `06-013-2019`. Drop the zero.
    if re.fullmatch(r"\d{4}-\d{2}-0\d{2}", s):
        s = s[:8] + s[9:]
    elif re.fullmatch(r"\d{2}-0\d{2}-\d{4}", s):
        s = s[:3] + s[4:]
    for fmt in ("%m-%d-%Y", "%Y-%m-%d", "%Y%m%d"):
        try:
            return pd.Timestamp(pd.to_datetime(s, format=fmt))
        except (ValueError, TypeError):
            continue
    return None


def parse_stem(stem: str) -> dict:
    """Pull session identity out of a base stem, whichever grammar it uses."""
    m = RE_LONG.match(stem)
    if m:
        tail = m.group("tail")
        if stem in STEM_DATE_FIXES:
            return dict(
                grammar="long", region=m.group("region"),
                date=pd.Timestamp(STEM_DATE_FIXES[stem]),
                run=m.group("run") or "a", condition=m.group("cond"),
                headstage=tail,
            )
        # tail is the headstage for Rocky/Nigel, but 2018 Rocky uses an
        # operator name ("Cui") in the same slot -- keep it verbatim.
        return dict(
            grammar="long",
            region=m.group("region"),
            date=parse_date(m.group("date")),
            run=m.group("run") or "a",
            condition=m.group("cond"),
            headstage=tail,
        )
    m = RE_STAMP.match(stem)
    if m:
        # The clock time distinguishes runs within a day; Fisk has several.
        return dict(
            grammar="stamp",
            region=None,
            date=parse_date(m.group("date")),
            run=m.group("time"),
            condition=None,
            headstage=None,
        )
    m = RE_DATAFILE.match(stem)
    if m:
        return dict(
            grammar="datafile",
            region=None,
            date=None,
            run=m.group("idx"),
            condition=None,
            headstage=None,
        )
    return dict(grammar="other", region=None, date=None, run="a",
                condition=None, headstage=None)


# %%
# === Walk ===
def walk() -> pd.DataFrame:
    rows: list[dict] = []
    for tree, (subject, implant) in TREES.items():
        base = ROOT / tree
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            name = p.name
            # .wfexp.mat and .ofb.log carry two suffixes; take the compound.
            low = name.lower()
            if low.endswith(".wfexp.mat"):
                stem, ext = name[: -len(".wfexp.mat")], ".mat"
                role = "export_wfexp"
            elif low.endswith(".ofb.log"):
                stem, ext, role = name[: -len(".ofb.log")], ".log", "ofs_log"
            elif low.endswith(".scan"):
                # <nevname>.nev_chanNN.scan -- strip back to the nev stem.
                stem = re.sub(r"\.nev_chan\d+\.scan$", "", name)
                ext, role = ".scan", "ofs_scan"
            else:
                stem, ext = p.stem, p.suffix.lower()
                role = ROLE_BY_EXT.get(ext, "other")
            base_stem, chain = split_variant(stem)
            info = parse_stem(base_stem)
            folder = str(p.parent.relative_to(base)) or "."
            rows.append(
                dict(
                    tree=tree, subject=subject, implant=implant,
                    rel=str(p.relative_to(ROOT)), folder=folder,
                    name=name, stem=base_stem, chain=chain, ext=ext, role=role,
                    array=array_label(info["region"], folder),
                    size=p.stat().st_size,
                    nev_time=nev_time_origin(p) if ext == ".nev" else None,
                    **info,
                )
            )
    df = pd.DataFrame(rows)
    # Session key = the filename date, corroborated by the header rather than
    # replaced by it. The header is the true acquisition clock, but it has two
    # demonstrated failure modes in this corpus (see `report_dates`), and one of
    # them would put two distinct Nigel sessions on the same day. The header is
    # used only where the filename carries no date at all.
    df["date_file"] = df["date"]
    df["date"] = df["date_file"].fillna(df["nev_time"].dt.normalize())
    return df


def array_label(region: str | None, folder: str) -> str | None:
    """Which array a file belongs to, however the corpus happens to say it.

    Rocky and Nigel put the implant site in the filename (`Anterior`/
    `Posterior`); Fisk names files by timestamp only and carries the array
    serial in the directory (`SN1498`/`SN1504`). Fisk's two arrays are recorded
    *sequentially on the same day* -- 43 shared dates, zero shared timestamps --
    so without this the two collapse into one session and the day looks like it
    was recorded twice.

    Nigel's terminal recordings say neither: owner-confirmed 2026-08-15 as
    Anterior, 2025-09-25. Posterior recorded no units that day.
    """
    if region:
        return region
    if folder.startswith("Terminal recordings"):
        return "Anterior"
    m = re.search(r"SN\d{4}", folder)
    return m.group(0) if m else None


# %%
# === Reports ===
def report_variants(df: pd.DataFrame) -> None:
    banner("1. Variant suffix chains actually present (NEV only)")
    print("  The owner's stated convention: base / -01 sorted / -02|DS curated")
    print("  by one operator / MA by the other. Discovered, not assumed:\n")
    nev = df[df.role == "snippets"]
    tab = pd.crosstab(nev.chain, nev.subject).sort_index()
    tab["TOTAL"] = tab.sum(axis=1)
    # Owner-ruled 2026-08-15, except where marked.
    lab = {"": "original, unsorted", "-01": "OFS automatic sort",
           "-02": "manual curation (DS)", "-DS": "manual curation (DS)",
           "-MA": "manual curation (Sidd)",
           "-MA-01": "Sidd, redone  [inferred from -MA-02, not ruled]",
           "-MA-02": "Sidd, redone",
           "-MA-RE": "Sidd, redone",
           "-MADS": "Sidd sorted THEN DS curated -- sequential, not independent",
           "-00": "partial OFS pass, superseded by -01  [read from packets]",
           "-01-01": "OFS sort re-saved by OFS"}
    out = tab.copy()
    out.insert(0, "meaning", [lab.get(c, "UNDECLARED") for c in out.index])
    print(out.to_string())
    missing = [c for c in tab.index if c not in lab]
    if missing:
        print("\n  Chains with no ruling -- do not use as a label:")
        for c in missing:
            n = int(tab.loc[c, "TOTAL"])
            who = ", ".join(s for s in tab.columns[:-1] if tab.loc[c, s])
            print(f"    {c:8s} {n:4d} file(s)  [{who}]")
    print("\n  Grouping that follows from the rulings:")
    print(f"    DS, independent   : {DS_CHAINS}")
    print(f"    Sidd, independent : {MA_CHAINS}")
    print(f"    sequential (excl.): {SEQ_CHAINS}  -- DS on top of Sidd's output,"
          " so not a second opinion")


def report_roles(df: pd.DataFrame) -> None:
    banner("2. Files by role and tree")
    tab = pd.crosstab(df.role, df.tree)
    tab["TOTAL"] = tab.sum(axis=1)
    print(tab.sort_values("TOTAL", ascending=False).to_string())
    banner("2b. Mass by role (GiB)")
    g = (df.groupby("role")["size"].sum() / 2**30).round(2).sort_values(
        ascending=False)
    print(g.to_string())


def build_sessions(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (subject, implant, region, date, headstage) recording."""
    nev = df[df.role == "snippets"].copy()
    # `run` separates same-day recordings: Rocky's trailing `b`, Fisk's clock
    # time. Without it two distinct recordings collapse into one row.
    keys = ["subject", "implant", "array", "date", "run", "headstage"]
    rows = []
    for key, g in nev.groupby([k for k in keys], dropna=False):
        chains = set(g.chain)
        rows.append(dict(
            zip(keys, key, strict=True),
            n_nev=len(g),
            has_original="" in chains,
            has_auto="-01" in chains,
            has_ds=bool(set(DS_CHAINS) & chains),
            has_ma=bool(set(MA_CHAINS) & chains),
            has_seq=bool(set(SEQ_CHAINS) & chains),
            chains=",".join(sorted(chains)),
        ))
    sess = pd.DataFrame(rows)
    # Attach raw availability on the same session key.
    raw = (df[df.role.isin(["broadband", "config"])]
           .groupby(keys, dropna=False)["role"].agg(set))

    def look(r, role: str) -> bool:
        k = tuple(getattr(r, c) for c in keys)
        return role in raw.get(k, set())

    sess["has_ns5"] = [look(r, "broadband") for r in sess.itertuples()]
    sess["has_ccf"] = [look(r, "config") for r in sess.itertuples()]
    return sess.sort_values(["subject", "implant", "array", "date", "run"])


def report_sessions(sess: pd.DataFrame) -> None:
    banner("3. Sessions by subject/implant, and which variants exist")
    g = sess.groupby(["subject", "implant"]).agg(
        sessions=("n_nev", "size"),
        original=("has_original", "sum"),
        auto_01=("has_auto", "sum"),
        curated_DS=("has_ds", "sum"),
        curated_MA=("has_ma", "sum"),
        raw_ns5=("has_ns5", "sum"),
        ccf=("has_ccf", "sum"),
    )
    print(g.to_string())
    banner("4. Where the two operators overlap -- the comparison set")
    both = sess[sess.has_ds & sess.has_ma]
    print(f"  sessions curated by BOTH operators: {len(both)}")
    if len(both):
        # dropna=False: Fisk carries no region in its filenames and would
        # otherwise vanish from this table entirely.
        print(both.groupby(["subject", "implant", "array"],
                           dropna=False).size().to_string())
        print("\n  dates:")
        for (s, i), g2 in both.groupby(["subject", "implant"]):
            ds = sorted(str(d.date()) for d in g2.date.dropna())
            print(f"    {s} {i}: {len(ds)}  {ds[:6]}{' ...' if len(ds) > 6 else ''}")
    tri = sess[sess.has_auto & sess.has_ds & sess.has_ma]
    print(f"\n  sessions with auto + BOTH operators (3-way): {len(tri)}")


def report_headstage_pairs(sess: pd.DataFrame) -> None:
    banner("5. Rocky analog/digital same-day pairs")
    r = sess[(sess.subject == "Rocky") & sess.headstage.notna()].copy()
    r["hs"] = r.headstage.str.lower()
    pivot = defaultdict(set)
    for row in r.itertuples():
        if row.date is not None and pd.notna(row.date):
            pivot[(row.implant, row.array, row.date)].add(row.hs)
    pairs = {k: v for k, v in pivot.items()
             if any("analog" in x for x in v) and any("digital" in x for x in v)}
    print(f"  date x region slots with BOTH headstages: {len(pairs)}")
    by = Counter((k[0], k[1]) for k in pairs)
    for k, n in sorted(by.items()):
        print(f"    {k[0]} {k[1]}: {n}")
    other = Counter(x for v in pivot.values() for x in v)
    print(f"\n  headstage/operator tokens seen: {dict(other)}")


def report_gaps(df: pd.DataFrame, sess: pd.DataFrame) -> None:
    banner("6. Things that will bite if not handled")
    unp = df[(df.role == "snippets") & (df.date.isna())]
    print(f"  NEV with no parseable date : {len(unp)}"
          f"  ({sorted(set(unp.tree))})")
    if len(unp):
        for n in sorted(set(unp.name))[:5]:
            print(f"      {n}")
    orphan = sess[~sess.has_original & (sess.has_auto | sess.has_ds | sess.has_ma)]
    print(f"\n  sorted/curated with NO original staged : {len(orphan)}")
    if len(orphan):
        print(orphan.groupby(["subject", "implant"]).size().to_string())
    grammars = df[df.role == "snippets"].grammar.value_counts()
    print(f"\n  filename grammars among NEV:\n{grammars.to_string()}")


def report_dates(df: pd.DataFrame) -> None:
    """Filename date against the NSP's own clock, and what the gaps mean."""
    banner("7. Filename date vs NEV header clock")
    nev = df[df.role == "snippets"]
    have = nev[nev.nev_time.notna()]
    print(f"  NEV files : {len(nev):,}")
    print(f"  readable header TimeOrigin : {len(have):,} "
          f"({len(have) / len(nev):.1%})  -- every one of them")

    c = have[have.date_file.notna()].copy()
    c["delta"] = (c.nev_time.dt.normalize() - c.date_file).dt.days
    c["hour"] = c.nev_time.dt.hour
    agree = int((c.delta == 0).sum())
    print(f"  agree exactly : {agree:,} / {len(c):,}  ({agree / len(c):.1%})\n")

    # Owner-ruled 2026-08-15: the NSP clock was off, the sessions did not run
    # past midnight. So every disagreement is a bad header, and the filename is
    # the date of record throughout -- not just the tie-breaker.
    late = c[(c.delta == 1) & (c.hour <= 4)]
    print(f"  [clock error] +1 day, header clock 00:00-04:00 : {len(late)}")
    print("      Owner ruling: the NSP clock was wrong, not the schedule.")
    print(f"      years affected: {sorted(set(late.date_file.dt.year))}")
    print("      Filename is the date of record. The header CLOCK is still")
    print("      usable for ordering within a session -- an analog/digital")
    print("      pair sits ~10 min apart and that spacing is unaffected.")

    # Class 2: disagreements that are not the +1-day clock error.
    bad = c[(c.delta != 0) & ~((c.delta == 1) & (c.hour <= 4))]
    uniq = bad.drop_duplicates("stem")
    print(f"\n  [other clock errors] : {len(bad)} files, {len(uniq)} recordings")
    for r in uniq.sort_values(["subject", "date_file"]).itertuples():
        note = ""
        if r.delta == 31:
            note = "  <- 2024-02-16 is ALREADY a separate session"
        elif r.delta == 3:
            note = "  <- both arrays shift +3 together: clock reset"
        elif abs(r.delta) > 100:
            note = "  <- month/day transposed in the header"
        print(f"      {r.subject:6s} {r.stem[:52]:52s} "
              f"{str(r.date_file.date())} -> {r.nev_time:%Y-%m-%d %H:%M}"
              f" ({r.delta:+d}d){note}")

    nodate = nev[nev.date_file.isna() & nev.nev_time.notna()]
    if len(nodate):
        print(f"\n  [!] dated ONLY by the header : {len(nodate)} files")
        for r in nodate.drop_duplicates("stem").sort_values("name").itertuples():
            print(f"      {r.name}  -> {r.nev_time:%Y-%m-%d %H:%M}")
        print("      Nigel's terminal recordings carry no date in the filename.")
        print("      Owner-confirmed 2026-08-15: Anterior array, 2025-09-25 --")
        print("      so here the header date is right despite falling in the")
        print("      window the clock is wrong in elsewhere. Posterior recorded")
        print("      no units that day.")


def main() -> int:
    df = walk()
    banner("Staged Monkey Data inventory")
    print(f"  root  : {ROOT}")
    print(f"  files : {len(df):,}")
    print(f"  mass  : {df['size'].sum() / 2**30:,.1f} GiB")

    report_roles(df)
    report_variants(df)
    sess = build_sessions(df)
    report_sessions(sess)
    report_headstage_pairs(sess)
    report_gaps(df, sess)
    report_dates(df)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, engine="pyarrow", index=False)
    sess.to_parquet(OUT_SESS, engine="pyarrow", index=False)
    print(f"\n  wrote {OUT.relative_to(REPO)}  ({len(df):,} rows)")
    print(f"  wrote {OUT_SESS.relative_to(REPO)}  ({len(sess):,} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

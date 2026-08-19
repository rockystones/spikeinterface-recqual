"""The Fisk drop: recordings, and impedance measured beside them.

This is the first corpus in the project where **impedance is recorded on the
same days as the ephys**, which is what CLAUDE.md's multimodal thread has been
waiting for. 41 `*-MotorImpedance.txt` files per array sit in the same folder
as 73 session directories, each session carrying `.nev`, `.ns3` (LFP) and
`.ns6` (broadband).

**The format is not Rocky's.** Rocky's impedance is potentiostat EIS -- 19
frequencies per electrode across six files per array
([[impedance_parsing]]). Fisk's is **Blackrock AutoImpedance**: one
single-frequency reading per channel, one file per date, written by Central at
the rig. Nothing in the existing parser applies, and the two must not be
pooled: a 1 kHz EIS magnitude and an AutoImpedance estimate are not the same
measurement.

The file's own header says so explicitly -- "Impedance values are estimates and
may be affected by noise" -- and carries the calibration it used
(`m`, `expected`, `b`). Those are kept per file so a change in calibration
between dates is visible rather than silently absorbed into a trend.

Array anatomy is finally unambiguous here: the folder names give
`1025-1498 = Right M1 Lateral` and `1025-1504 = Right M1 Medial`, matching the
serials already in the subject registry.

Run from repo root:

    uv run python notebooks/scratch_fisk_impedance.py

Writes `data/derived/fisk/impedance.parquet` and
`data/derived/fisk/fisk_sessions.parquet`.

See:
- docs/notes/fisk_impedance.md
- docs/notes/impedance_parsing.md
"""

from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from _paths import FISK  # noqa: E402

OUT_DIR = REPO / "data" / "derived" / "fisk"
IMP_OUT = OUT_DIR / "impedance.parquet"
SESS_OUT = OUT_DIR / "fisk_sessions.parquet"

# Folder name -> (serial, anatomy). Taken from the drop's own directory names,
# which are the first unambiguous statement of Fisk's array anatomy in the
# project.
ARRAY_DIRS = {
    "1025-1498 (Fisk Right M1 Lateral)": ("1025-001498", "Lateral"),
    "1025-1504 (Fisk Right M1 Medial)": ("1025-001504", "Medial"),
}

# `             chan1\t 602 kOhm`
CHAN_RE = re.compile(r"^\s*chan(\d+)\s+(\d+)\s*kOhm", re.IGNORECASE)
# `*  5 June 2023 13:29:15`
HDR_DATE_RE = re.compile(r"^\*\s+(\d{1,2}\s+\w+\s+\d{4})")
HDR_KV_RE = re.compile(r"^\*\s*(m|expected|b)\s*=\s*([-\d.]+)")
# `20230605-Lateral-MotorImpedance.txt`
FNAME_DATE_RE = re.compile(r"^(\d{8})-")
# `20230605-132052-Lateral`
SESSION_RE = re.compile(r"^(\d{8})-(\d{6})-(\w+)$")

# 1 MOhm is the conventional line above which a Utah electrode is called bad.
# It is used here only as a reporting cut, NOT as a classification: section 4b
# shows a channel crosses it a median of 7 times over 41 dates, so a single
# reading does not place an electrode on either side of it.
HIGH_Z_KOHM = 1000.0


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === Parsing ===
def parse_autoimpedance(path: Path) -> tuple[pd.DataFrame, dict]:
    """One AutoImpedance file to (per-channel frame, header dict).

    Returns the channel readings and the calibration the rig used, kept
    separately so a recalibration between dates is visible in the table
    rather than folded into the values.
    """
    meta: dict = {}
    rows: list[dict] = []
    for line in path.read_text(errors="replace").splitlines():
        m = CHAN_RE.match(line)
        if m:
            rows.append(dict(channel=int(m.group(1)),
                             kohm=float(m.group(2))))
            continue
        d = HDR_DATE_RE.match(line)
        if d:
            try:
                meta["measured"] = pd.to_datetime(d.group(1))
            except Exception:  # noqa: BLE001
                pass
            continue
        kv = HDR_KV_RE.match(line)
        if kv:
            meta[f"cal_{kv.group(1)}"] = float(kv.group(2))
    return pd.DataFrame(rows), meta


def build_impedance(root: Path = FISK) -> pd.DataFrame:
    """Every AutoImpedance reading in the drop, one row per (date, channel)."""
    out: list[pd.DataFrame] = []
    for folder, (serial, anatomy) in ARRAY_DIRS.items():
        rec = root / folder / "Recordings"
        if not rec.is_dir():
            continue
        for f in sorted(rec.glob("*MotorImpedance*.txt")):
            d, meta = parse_autoimpedance(f)
            if not len(d):
                continue
            fm = FNAME_DATE_RE.match(f.name)
            file_date = (pd.to_datetime(fm.group(1), format="%Y%m%d")
                         if fm else pd.NaT)
            d["subject"] = "Fisk"
            d["serial"] = serial
            d["array"] = anatomy
            d["date"] = file_date
            d["measured"] = meta.get("measured", pd.NaT)
            for k in ("cal_m", "cal_expected", "cal_b"):
                d[k] = meta.get(k, np.nan)
            d["file"] = f.name
            d["high_z"] = d.kohm >= HIGH_Z_KOHM
            out.append(d)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def build_sessions(root: Path = FISK) -> pd.DataFrame:
    """Every recording session folder, with the streams it carries."""
    rows: list[dict] = []
    for folder, (serial, anatomy) in ARRAY_DIRS.items():
        rec = root / folder / "Recordings"
        if not rec.is_dir():
            continue
        for d in sorted(p for p in rec.iterdir() if p.is_dir()):
            m = SESSION_RE.match(d.name)
            if not m:
                continue
            exts = {p.suffix.lower() for p in d.iterdir() if p.is_file()}
            rows.append(dict(
                subject="Fisk", serial=serial, array=anatomy,
                session=d.name, path=str(d),
                date=pd.to_datetime(m.group(1), format="%Y%m%d"),
                time=m.group(2),
                has_nev=".nev" in exts, has_lfp=".ns3" in exts,
                has_broadband=".ns6" in exts, has_config=".ccf" in exts,
                n_files=sum(1 for _ in d.iterdir()),
                bytes=sum(p.stat().st_size for p in d.iterdir()
                          if p.is_file()),
            ))
    return pd.DataFrame(rows)


# %%
# === Report ===
def report(imp: pd.DataFrame, sess: pd.DataFrame) -> None:
    banner("1. Recording sessions")
    print(sess.groupby(["array", "serial"]).agg(
        sessions=("session", "size"), first=("date", "min"),
        last=("date", "max"), nev=("has_nev", "sum"),
        lfp=("has_lfp", "sum"), broadband=("has_broadband", "sum"),
        gib=("bytes", lambda s: round(s.sum() / 2**30, 1))).to_string())

    banner("2. Impedance measurements")
    print(imp.groupby(["array", "serial"]).agg(
        files=("file", "nunique"), dates=("date", "nunique"),
        channels=("channel", "nunique"),
        first=("date", "min"), last=("date", "max")).to_string())
    print("\n  per-date channel counts:")
    print(imp.groupby(["array", "date"]).size().groupby(level=0)
          .describe()[["min", "50%", "max"]].to_string())

    banner("3. Is the calibration constant across dates?")
    print("  The rig writes the calibration it used into each file. If it")
    print("  changes, readings from different dates are not on one scale.\n")
    cal = imp.drop_duplicates(["array", "date"])[
        ["array", "date", "cal_m", "cal_expected", "cal_b"]]
    for arr, g in cal.groupby("array"):
        uniq = g[["cal_m", "cal_expected", "cal_b"]].drop_duplicates()
        print(f"  {arr}: {len(uniq)} distinct calibration(s) over "
              f"{len(g)} dates")
        if len(uniq) <= 4:
            print(uniq.to_string(index=False))

    banner("4. The impedance distribution")
    print(f"  readings: {len(imp)}   at/above {HIGH_Z_KOHM:.0f} kOhm: "
          f"{int(imp.high_z.sum())} ({imp.high_z.mean():.1%})")
    print()
    print(imp.groupby("array").kohm.describe()[
        ["count", "25%", "50%", "75%", "max"]].round(1).to_string())

    banner("4b. A single reading cannot classify an electrode")
    print("  If a high reading meant degradation, a channel that crossed")
    print("  1 MOhm would stay across. Counting how often each channel")
    print("  crosses the line over the series:")
    print()
    for arr, g in imp.groupby("array"):
        f = g.pivot_table(index="channel", columns="date", values="kohm")
        flips = ((f >= HIGH_Z_KOHM).astype(int)
                 .diff(axis=1).abs() == 1).sum(axis=1)
        print(f"  {arr:8s} {len(f)} channels over {f.shape[1]} dates:  "
              f"never cross {int((flips == 0).sum()):3d}   "
              f"median crossings {flips.median():.0f}   "
              f"max {int(flips.max())}")
    print()
    print("  The file header says it plainly: 'Impedance values are estimates")
    print("  and may be affected by noise.' Use a per-channel median across")
    print("  dates, never one reading, and treat 1 MOhm as a reporting")
    print("  convention rather than a diagnosis.")
    print()
    print("  per-date counts above the line, for reference:")
    oc = imp.groupby(["array", "date"]).high_z.sum().unstack(0)
    print(oc.tail(8).to_string())

    banner("5. Do impedance dates line up with recording dates?")
    for arr in sorted(set(imp.array) & set(sess.array)):
        idates = set(imp[imp.array == arr].date.dt.date)
        sdates = set(sess[sess.array == arr].date.dt.date)
        both = idates & sdates
        print(f"  {arr:10s} impedance {len(idates):3d} dates   "
              f"sessions {len(sdates):3d} dates   same day: {len(both):3d}")
    print("\n  Same-day pairs are what a quality-versus-impedance join needs;")
    print("  a nearest-date join across a gap assumes impedance is stable")
    print("  over that gap, which is the thing being measured.")


def main() -> int:
    imp = build_impedance()
    sess = build_sessions()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if len(imp):
        imp.to_parquet(IMP_OUT, engine="pyarrow", index=False)
    if len(sess):
        sess.to_parquet(SESS_OUT, engine="pyarrow", index=False)
    banner("Fisk -- recordings and Blackrock AutoImpedance")
    print(f"  impedance readings: {len(imp)}   sessions: {len(sess)}")
    if len(imp) and len(sess):
        report(imp, sess)
    print(f"\n  wrote {IMP_OUT}  ({len(imp)} rows)")
    print(f"  wrote {SESS_OUT}  ({len(sess)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

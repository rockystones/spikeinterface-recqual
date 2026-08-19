"""The operator floor on Fisk: DS against Sidd, seven dates, two arrays.

S09 measured how much of a longitudinal answer is the operator rather than the
tissue, using 30 DS/Sidd pairs on Fisk and Rocky implant 2. The new Fisk drop
adds a **matched** design that S09 did not have: the same seven session dates
curated by both operators on **both** arrays, 2023-12-13 to 2024-04-03.

Matched matters. S09's pairs were whatever happened to exist, so an operator
difference and a session difference were partly confounded. Here every date
contributes one DS file and one Sidd file per array, so the pairing is exact
and the comparison is within-session by construction.

The comparison itself is unchanged and deliberately so -- `label_file` and
`compare` are imported from S09 rather than reimplemented, so the numbers land
on the same scale as the floor already published in [[measurement_floor]].
Because sorting never re-detects on a NEV, both files hold the same event list
in the same order and agreement is exact rather than matched.

Run from repo root:

    uv run python notebooks/scratch_fisk_operators.py

Writes `data/derived/fisk/operator_pairs.parquet`.

See:
- docs/notes/fisk_impedance.md
- docs/notes/measurement_floor.md
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
from scratch_measurement_floor import compare, label_file  # noqa: E402

PAIR_ROOT = FISK / "DS vs Sidd"
OUT_DIR = REPO / "data" / "derived" / "fisk"
OUT = OUT_DIR / "operator_pairs.parquet"

# Folder serial -> anatomy, matching the Recordings tree.
ARRAYS = {"SN1498": "Lateral", "SN1504": "Medial"}
# `20231213-115922-001-DS.nev` -> stem `20231213-115922-001`, operator `DS`.
NAME_RE = re.compile(r"^(?P<stem>\d{8}-\d{6}-\d+)-(?P<op>DS|MA)$")
OPERATOR = {"DS": "DS", "MA": "Sidd"}


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def build_pairs() -> list[dict]:
    """Sessions curated by both operators, one row per (array, session)."""
    pairs: list[dict] = []
    for serial, anatomy in ARRAYS.items():
        base = PAIR_ROOT / serial
        if not base.is_dir():
            continue
        by_stem: dict[str, dict[str, Path]] = {}
        for nev in base.rglob("*.nev"):
            m = NAME_RE.match(nev.stem)
            if not m:
                continue
            by_stem.setdefault(m.group("stem"), {})[
                OPERATOR[m.group("op")]] = nev
        for stem, files in sorted(by_stem.items()):
            if {"DS", "Sidd"} <= set(files):
                pairs.append(dict(
                    subject="Fisk", serial=serial, array=anatomy, stem=stem,
                    date=pd.to_datetime(stem[:8], format="%Y%m%d"),
                    ds=str(files["DS"]), sidd=str(files["Sidd"]),
                ))
    return pairs


def score(pair: dict) -> dict:
    """Agreement between the two operators on one session."""
    base = {k: v for k, v in pair.items() if k not in ("ds", "sidd")}
    a = label_file(Path(pair["ds"]))
    b = label_file(Path(pair["sidd"]))
    if a is None or b is None:
        return dict(**base, error="unreadable")
    cmp = compare(a, b)
    if not cmp.get("comparable", True):
        return dict(**base, error="not element-wise comparable")
    # `compare` already reports n_spikes, units_a/units_b and the noise
    # counts; taking its version rather than duplicating them keeps one
    # definition per quantity.
    drop = {"comparable", "units_a", "units_b"}
    return dict(
        **base,
        ds_units=a["n_units"], sidd_units=b["n_units"],
        ds_keep=a["keep_frac"], sidd_keep=b["keep_frac"],
        ds_elec=a["n_elec_with_units"], sidd_elec=b["n_elec_with_units"],
        # Relative difference on the same definition S09 used, so the two
        # tables can be read on one scale.
        rel_units=abs(a["n_units"] - b["n_units"])
        / max((a["n_units"] + b["n_units"]) / 2, 1),
        ratio_units=b["n_units"] / a["n_units"] if a["n_units"] else np.nan,
        **{k: v for k, v in cmp.items() if k not in drop},
    )


def report(d: pd.DataFrame) -> None:
    ok = d[d.get("error").isna()] if "error" in d else d
    banner("1. The matched design")
    print(f"  pairs: {len(ok)} of {len(d)}")
    print(ok.groupby("array").agg(
        pairs=("stem", "size"), first=("date", "min"), last=("date", "max"),
        spikes=("n_spikes", "median")).to_string())
    print("\n  Every date contributes one DS and one Sidd file per array, so")
    print("  operator and session are not confounded -- which S09's")
    print("  opportunistic pairs could not guarantee.")

    banner("2. How far apart are the two operators?")
    print(f"  {'quantity':30s} {'median':>9s} {'IQR':>18s}")
    for col, lab in (("rel_units", "relative unit-count diff"),
                     ("ratio_units", "Sidd / DS unit count"),
                     ("keep_agree", "spikes treated the same"),
                     ("ari_kept", "ARI on spikes both keep"),
                     ("jaccard_kept", "overlap of the kept sets")):
        if col not in ok:
            continue
        s = ok[col].dropna()
        if not len(s):
            continue
        print(f"  {lab:30s} {s.median():9.3f} "
              f"{s.quantile(0.25):8.3f}-{s.quantile(0.75):.3f}")

    banner("3. Against the floor S09 published")
    print("  S09, 30 opportunistic DS/Sidd pairs:")
    print("    relative unit-count diff  0.25")
    print("    ARI on kept spikes        0.995")
    print("    keep agreement            0.935")
    print("    Sidd/DS unit ratio        0.79  (IQR 0.72-0.97)")
    if "rel_units" in ok and len(ok):
        print(f"\n  Fisk matched pairs, n = {len(ok)}:")
        print(f"    relative unit-count diff  {ok.rel_units.median():.3f}")
        if "ari_kept" in ok:
            print(f"    ARI on kept spikes        "
                  f"{ok.ari_kept.median():.3f}")
        if "keep_agree" in ok:
            print(f"    keep agreement            "
                  f"{ok.keep_agree.median():.3f}")
        print(f"    Sidd/DS unit ratio        "
              f"{ok.ratio_units.median():.3f}  "
              f"(IQR {ok.ratio_units.quantile(0.25):.2f}-"
              f"{ok.ratio_units.quantile(0.75):.2f})")

    banner("4. Is the difference systematic?")
    if "ratio_units" in ok and len(ok) >= 4:
        same = (ok.ratio_units < 1).mean()
        print(f"  Sidd keeps fewer units than DS in "
              f"{same:.0%} of pairs ({int((ok.ratio_units < 1).sum())} of "
              f"{len(ok)})")
        print("  A consistent offset cancels out of a trend computed within")
        print("  one operator and only breaks comparisons that cross them.")
        print()
        print(ok[["array", "date", "ds_units", "sidd_units", "ratio_units",
                  "keep_agree"]].round(3).to_string(index=False))


def main() -> int:
    pairs = build_pairs()
    banner("Fisk operator floor -- DS against Sidd")
    print(f"  matched pairs found: {len(pairs)}")
    if not pairs:
        print("  none; check the DS vs Sidd tree")
        return 1
    rows = [score(p) for p in pairs]
    d = pd.DataFrame(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, engine="pyarrow", index=False)
    report(d)
    print(f"\n  wrote {OUT}  ({len(d)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

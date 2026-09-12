"""Per-electrode events for Rocky implant 2 -- the fresh-implant ring test.

Implant 2 (surgery 2025-03-26, arrays 1025-004377 anterior / 1025-004419
posterior) has 20 baseline sessions spanning 2025-04-04 .. 2025-06-05 whose
`-01` NEVs turn out to live on a mounted copy (`Monkey Data\\Rocky New`).
That makes the deferred per-electrode build possible: the same
`event_stats_session` machinery that produced `rocky/events_electrode.parquet`
for implant 1, driven over the I2 sessions with the I2 CMPs.

The point is the ring test at a **known young implant age**. `ring_geometry.md`
established that the impedance edge effect is acquired over months in tissue
and that the ephys edge contrast is animal-specific. Arrays one to two months
in should show, if the acquisition story is right, a border contrast near the
bench-like baseline -- and any large contrast already present would have to be
explained another way.

Run from repo root:

    uv run python notebooks/scratch_rocky_i2_events.py

Results recorded in docs/notes/ring_geometry.md.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))

from scratch_cohort_io import banner  # noqa: E402
from scratch_ns5_resort import INV, build_worklist  # noqa: E402
from scratch_ring_geometry import (  # noqa: E402
    attach_bank,
    border_signs,
    to_grid,
    toroidal_null,
    within_bank_contrast,
)
from scratch_rocky_events import event_stats_session  # noqa: E402
from scratch_rocky_spatial import parse_cmp  # noqa: E402

OUT = REPO / "data" / "derived" / "rocky_i2"
PROBE_DIR = REPO / "configs" / "probes"
SERIALS = {"Anterior": "1025-004377", "Posterior": "1025-004419"}
METRICS = ["noise_uv", "amp_p50", "peak_snr", "crossing_rate_hz"]


def geometry(serial: str) -> dict[int, tuple[int, int]]:
    """channel_id -> (col, row) from the array's CMP."""
    hits = sorted(PROBE_DIR.glob(f"*{serial}*.cmp"))
    g = parse_cmp(hits[0])
    return {int(r.channel_id): (int(r.col), int(r.row))
            for r in g.itertuples()}


def build() -> pd.DataFrame:
    """Run the event machinery over every reachable I2 session."""
    inv = pd.read_parquet(INV)
    jobs = [j for j in build_worklist(inv)
            if j["subject"] == "Rocky" and j.get("implant") == "I2"
            and j.get("nev") and Path(j["nev"]).exists()]
    print(f"  {len(jobs)} I2 sessions with a reachable -01 NEV")
    geoms = {arr: geometry(sn) for arr, sn in SERIALS.items()}

    OUT.mkdir(parents=True, exist_ok=True)
    shard_dir = OUT / "event_shards"
    shard_dir.mkdir(exist_ok=True)
    frames = []
    for i, j in enumerate(sorted(jobs, key=lambda x: x["stem"]), 1):
        shard = shard_dir / f"{j['stem']}.parquet"
        if shard.exists():
            frames.append(pd.read_parquet(shard))
            continue
        meta = dict(date=j["date"], array=j["array"],
                    serial=SERIALS[j["array"]], implant="I2",
                    headstage=j.get("headstage", ""), stem=j["stem"])
        try:
            elec, _giants, _wf, _ids = event_stats_session(
                j["nev"], meta, geoms[j["array"]])
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {j['stem']}: {type(exc).__name__}: {exc}")
            continue
        elec.to_parquet(shard, index=False)
        frames.append(elec)
        print(f"  [{i}/{len(jobs)}] {j['stem'][:56]}  "
              f"{elec.channel_id.nunique()} electrodes")
    d = pd.concat(frames, ignore_index=True)
    d.to_parquet(OUT / "events_electrode.parquet", index=False)
    return d


def ring_tests(d: pd.DataFrame) -> None:
    """Border contrast, toroidal null, isotropy and within-bank on I2."""
    d = d.copy()
    d["date"] = pd.to_datetime(d["date"])
    print(f"  {len(d):,} electrode-sessions, {d.stem.nunique()} sessions, "
          f"{d.date.min().date()} .. {d.date.max().date()}")

    rows = []
    for met in METRICS:
        surf = (d.dropna(subset=[met])
                  .groupby(["array", "serial", "channel_id", "col", "row"],
                           observed=True)[met]
                  .median().reset_index(name="value"))
        for (arr, serial), g in surf.groupby(["array", "serial"],
                                             observed=True):
            grid = to_grid(g)
            obs, p = toroidal_null(grid)
            agree, _dev = border_signs(grid)
            rows.append(dict(array=arr, serial=serial, metric=met,
                             contrast_pct=obs, p_shift=p,
                             borders_agree=agree))
        # within-bank arm
        g2 = surf.rename(columns={"value": "v"}).copy()
        g2["subject"] = "RockyI2"
        g2["is_border"] = (np.minimum.reduce(
            [g2.col, 9 - g2.col, g2.row, 9 - g2.row]) == 0)
        wb = within_bank_contrast(attach_bank(g2), "v",
                                  ["subject", "array", "bank"])
        base = g2.groupby("array", observed=True).v.mean().rename("base")
        wb = wb.merge(base, on="array")
        wb["delta_pct"] = 100.0 * wb.delta / wb.base
        print(f"\n  {met}: within-bank border - interior (% of array mean)")
        print(wb.pivot_table(index="array", columns="bank",
                             values="delta_pct").round(1).to_string())
    res = pd.DataFrame(rows)
    print("\n  array-level, toroidal-shift null:")
    print(res.round(3).to_string(index=False))
    res.to_parquet(OUT / "ring_stats.parquet", index=False)

    print("\n  Implant-1 long-term values for the same statistics are in "
          "data/derived/ring/ -- the comparison is drawn in "
          "docs/notes/ring_geometry.md.")


def main() -> int:
    banner("1. Building I2 per-electrode events")
    d = build()
    banner("2. The fresh-implant ring test")
    ring_tests(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

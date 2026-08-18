"""Infer the TDT channel map from Rocky's same-day Blackrock recordings.

The TDT tanks do not record how a headstage channel wires onto an array
electrode, which is why the TDT previews are drawn in channel-index order.
Rocky supplies a way to recover it: on 22 days in 2018-2019 he was recorded on
**both** systems, and an electrode's own properties -- its impedance, and which
neurons sit near it -- do not change between two sessions on one day.

So each channel gets a signature that survives the change of amplifier, and
the map is the assignment of TDT channels to Blackrock electrodes that
minimises total signature distance (Hungarian algorithm, exact).

**Both sides are measured the same way on purpose.** The Blackrock side uses
its `.nev` snippets rather than the `.ns5`, so both corpora go through
`baseline_noise_uv` and the same trough statistic. Comparing a
continuous-derived noise floor against a snippet-derived one would inject the
1.1-1.3x estimator bias from [[snippet_noise_floor]] straight into the cost
matrix.

**The result is only worth having if it replicates.** A single day always
yields *an* assignment -- Hungarian returns one whatever the data. The test is
whether independently inferred maps from different days agree with each other,
scored against the ~1% agreement a random permutation would give. This script
reports that first and the map second, and it will say so plainly if the
answer is that the signature is not discriminative enough.

Rocky's TDT blocks carry a single store (`eNe2`) and come in `_A` and `_B`
variants on the same date, so which of Anterior/Posterior each letter denotes
is unknown too. Both pairings are scored; the correct one should fit better.

Run from repo root:

    uv run python notebooks/scratch_tdt_map_infer.py [--headstage Digital]

Writes `data/derived/tdt_map/day_signatures.parquet`,
`data/derived/tdt_map/pairings.parquet` and, if it replicates,
`configs/probes/tdt_channel_map_rocky.csv`.

See:
- docs/notes/tdt_channel_map.md
"""

from __future__ import annotations

import argparse
import itertools
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_rocky_resort import (  # noqa: E402
    baseline_noise_uv,
    open_nev,
    read_electrode,
)
from scratch_tdt_io import (  # noqa: E402
    channel_index,
    detect_nbefore,
    find_blocks,
    open_tank,
    read_channel,
    tank_clock,
)

ROCKY_TDT = Path(r"C:\MyData\Monkeydata\Rocky\Rocky_TDT")
INV = REPO / "data" / "derived" / "newdrop_inventory.parquet"
OUT_DIR = REPO / "data" / "derived" / "tdt_map"
MAP_OUT = REPO / "configs" / "probes" / "tdt_channel_map_rocky.csv"

# Per-channel features. All are physical properties of the electrode and the
# tissue around it, not of the amplifier: impedance sets the noise floor, the
# nearby neurons set the rate and the amplitude. Each is z-scored within a
# recording, so a global gain or threshold difference between the two systems
# cancels and only the *pattern across channels* is compared.
FEATURES = ("log_noise", "log_rate", "log_amp50", "log_amp90")
# A map is only believable if independent days agree. Chance agreement for a
# 96-way permutation is 1/96 ~ 1.04%.
CHANCE = 1.0 / 96.0


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def _z(x: np.ndarray) -> np.ndarray:
    """Z-score, tolerating a constant column."""
    s = np.nanstd(x)
    return (x - np.nanmean(x)) / s if s > 0 else np.zeros_like(x)


# %%
# === Signatures ===
def tdt_signature(tev: Path, store: str = "eNe2") -> pd.DataFrame:
    """Per-channel features from one TDT block's snippets."""
    io, meta = open_tank(tev)
    idx = channel_index(io)
    nbefore = detect_nbefore(io, meta, store, idx)
    dur = meta["duration_s"]
    rows = []
    for (st, ch), units in sorted(idx.items()):
        if st != store:
            continue
        e = read_channel(io, meta, units)
        if e is None or not len(e["t"]):
            rows.append(dict(channel=int(ch), noise=np.nan, rate=0.0,
                             amp50=0.0, amp90=0.0,
                             shape=np.zeros_like(SHAPE_GRID)))
            continue
        amp = np.abs(e["wf"].min(axis=1))
        rows.append(dict(
            channel=int(ch),
            noise=baseline_noise_uv(e["wf"], nbefore),
            rate=len(amp) / dur if dur and np.isfinite(dur) else np.nan,
            amp50=float(np.median(amp)),
            amp90=float(np.percentile(amp, 90)),
            shape=resample_shape(e["wf"].mean(axis=0),
                                 meta["sr_by_store"].get(store, meta["sr"]),
                                 nbefore),
        ))
    return pd.DataFrame(rows)


def nev_signature(nev: Path) -> pd.DataFrame:
    """Per-electrode features from one Blackrock NEV, computed identically."""
    raw, meta, chan_by_elec = open_nev(nev)
    nbefore, dur = meta["nbefore"], meta["duration_s"]
    rows = []
    for elec in sorted(chan_by_elec):
        e = read_electrode(raw, meta, chan_by_elec[elec])
        if e is None or not len(e["t"]):
            rows.append(dict(channel=int(elec), noise=np.nan, rate=0.0,
                             amp50=0.0, amp90=0.0,
                             shape=np.zeros_like(SHAPE_GRID)))
            continue
        amp = np.abs(e["wf"].min(axis=1))
        rows.append(dict(
            channel=int(elec),
            noise=baseline_noise_uv(e["wf"], nbefore),
            rate=len(amp) / dur if dur else np.nan,
            amp50=float(np.median(amp)),
            amp90=float(np.percentile(amp, 90)),
            shape=resample_shape(e["wf"].mean(axis=0), meta["sr"], nbefore),
        ))
    return pd.DataFrame(rows)


def featurise(d: pd.DataFrame) -> pd.DataFrame:
    """Add the z-scored log features the cost matrix is built from."""
    d = d.copy()
    d["log_noise"] = _z(np.log1p(d.noise.fillna(d.noise.median())))
    d["log_rate"] = _z(np.log1p(d.rate.fillna(0)))
    d["log_amp50"] = _z(np.log1p(d.amp50.fillna(0)))
    d["log_amp90"] = _z(np.log1p(d.amp90.fillna(0)))
    return d


# %%
# === Waveform shape, the feature with structure ===
# A common time base for two systems that sample at 24414 and 30000 Hz. Spans
# the trough and the repolarisation, which is where the shape information is.
SHAPE_T0_MS, SHAPE_T1_MS, SHAPE_STEP_MS = -0.25, 0.90, 0.02
SHAPE_GRID = np.arange(SHAPE_T0_MS, SHAPE_T1_MS, SHAPE_STEP_MS)


def resample_shape(mean_wf: np.ndarray, sr: float, nbefore: int) -> np.ndarray:
    """One mean waveform on the common grid, unit-normalised.

    Time is measured from the trough, not from the start of the snippet, so
    the two systems' different pre-trigger lengths do not shift the shapes
    relative to one another. Unit-normalising removes the gain difference,
    leaving only shape.
    """
    if mean_wf is None or not len(mean_wf):
        return np.zeros_like(SHAPE_GRID)
    t = (np.arange(len(mean_wf)) - nbefore) / sr * 1000.0
    y = np.interp(SHAPE_GRID, t, mean_wf, left=0.0, right=0.0)
    n = np.linalg.norm(y)
    return y / n if n > 0 else y


# %%
# === Assignment ===
def infer_map(tdt: pd.DataFrame, nev: pd.DataFrame,
              shape_weight: float = 1.0) -> tuple[dict, float]:
    """Best TDT-channel -> Blackrock-electrode assignment, and its mean cost.

    Hungarian on the Euclidean distance between feature vectors. Exact, so the
    only question is whether the features carry the information -- which is
    what the cross-day agreement test answers, not this function.
    """
    a = featurise(tdt).sort_values("channel").reset_index(drop=True)
    b = featurise(nev).sort_values("channel").reset_index(drop=True)
    n = min(len(a), len(b))
    a, b = a.iloc[:n], b.iloc[:n]
    A = a[list(FEATURES)].to_numpy(float)
    B = b[list(FEATURES)].to_numpy(float)
    cost = np.linalg.norm(A[:, None, :] - B[None, :, :], axis=2)
    if shape_weight and "shape" in a and "shape" in b:
        # Shape carries far more structure than four scalars: a ~57-point
        # unit-normalised waveform. Distance is 1 - correlation, so a channel
        # whose dominant unit looks the same on both systems is cheap to
        # match regardless of gain.
        SA = np.stack(a["shape"].to_numpy())
        SB = np.stack(b["shape"].to_numpy())
        SA = SA - SA.mean(axis=1, keepdims=True)
        SB = SB - SB.mean(axis=1, keepdims=True)
        na = np.linalg.norm(SA, axis=1, keepdims=True)
        nb = np.linalg.norm(SB, axis=1, keepdims=True)
        SA = SA / np.where(na == 0, 1, na)
        SB = SB / np.where(nb == 0, 1, nb)
        cost = cost + shape_weight * (1.0 - SA @ SB.T)
    ri, ci = linear_sum_assignment(cost)
    mapping = {int(a.channel.iloc[i]): int(b.channel.iloc[j])
               for i, j in zip(ri, ci, strict=True)}
    return mapping, float(cost[ri, ci].mean())


def agreement(m1: dict, m2: dict) -> float:
    """Fraction of TDT channels the two maps send to the same electrode."""
    keys = set(m1) & set(m2)
    if not keys:
        return np.nan
    return sum(m1[k] == m2[k] for k in keys) / len(keys)


# %%
# === Worklist ===
def build_days(headstage: str) -> pd.DataFrame:
    """Days carrying both a TDT block and a Blackrock NEV, per array pairing."""
    rows = []
    for tev in find_blocks(ROCKY_TDT):
        start, dur = tank_clock(tev.with_suffix(".tsq"))
        if start is None:
            continue
        name = tev.parent.name
        letter = "A" if "_A" in name else ("B" if "_B" in name else "")
        rows.append(dict(block=name, tev=str(tev), letter=letter,
                         date=str(start.date()), duration_s=dur))
    t = pd.DataFrame(rows)
    t = t[(t.letter != "") & (t.duration_s > 60)]

    inv = pd.read_parquet(INV)
    nev = inv[(inv.role == "snippets") & inv.date.notna()
              & (inv.tree == "Blackrock")].copy()
    nev["d"] = nev.date.dt.strftime("%Y-%m-%d")
    nev = nev[nev.headstage == headstage]
    # Only the unsorted original: a sorted sibling holds the same events, and
    # the features here do not use labels, but taking one file per (day,
    # array) keeps the pairing unambiguous.
    nev = nev[nev.chain == ""].drop_duplicates(["d", "array"])

    out = []
    for r in t.itertuples():
        for arr in ("Anterior", "Posterior"):
            hit = nev[(nev.d == r.date) & (nev.array == arr)]
            if not len(hit):
                continue
            out.append(dict(date=r.date, letter=r.letter, block=r.block,
                            tev=r.tev, array=arr,
                            nev=hit.iloc[0]["path"],
                            nev_stem=hit.iloc[0]["stem"]))
    return pd.DataFrame(out)


def report(days: pd.DataFrame, res: pd.DataFrame, maps: dict) -> None:
    banner("1. Days available")
    print(f"  TDT block x Blackrock array pairings: {len(days)}")
    print(days.groupby(["letter", "array"]).size().rename("days").to_string())

    banner("2. Which letter is which array")
    print("  Mean assignment cost, lower is a better fit. If `_A` really is")
    print("  one array, its cost against that array should be the lower of")
    print("  the two -- consistently, not on average.\n")
    piv = res.pivot_table(index="letter", columns="array", values="cost",
                          aggfunc="median")
    print(piv.round(4).to_string())
    wins = (res.sort_values("cost").groupby(["date", "letter"]).head(1)
            .groupby(["letter", "array"]).size().rename("days won"))
    print("\n  days on which each pairing had the lower cost:")
    print(wins.to_string())

    banner("3. Does the inferred map replicate across days?")
    print(f"  Chance agreement for a 96-way permutation is {CHANCE:.1%}.")
    print("  Anything near that means the signature does not identify a")
    print("  channel and the map is not recoverable this way.\n")
    for (letter, arr), g in res.groupby(["letter", "array"]):
        keys = [(r.date, letter, arr) for r in g.itertuples()]
        pairs = [agreement(maps[a], maps[b])
                 for a, b in itertools.combinations(keys, 2)
                 if a in maps and b in maps]
        if not pairs:
            continue
        pairs = np.array(pairs)
        print(f"  {letter} vs {arr:10s} n_days={len(keys):3d}  "
              f"pairwise agreement median {np.median(pairs):.3f}  "
              f"max {pairs.max():.3f}  "
              f"(chance {CHANCE:.3f})")

    banner("4. Verdict")
    best = []
    for (letter, arr), g in res.groupby(["letter", "array"]):
        keys = [(r.date, letter, arr) for r in g.itertuples()]
        pairs = [agreement(maps[a], maps[b])
                 for a, b in itertools.combinations(keys, 2)
                 if a in maps and b in maps]
        if pairs:
            best.append((float(np.median(pairs)), letter, arr, len(keys)))
    if not best:
        print("  no pairing had enough days to test")
        return
    best.sort(reverse=True)
    top = best[0]
    print(f"  best replicating pairing: {top[1]} <-> {top[2]}  "
          f"median cross-day agreement {top[0]:.3f} over {top[3]} days")
    if top[0] < 5 * CHANCE:
        print("\n  **The map does not replicate.** Cross-day agreement is")
        print("  within a small multiple of chance, so these four features do")
        print("  not identify a channel across the two systems. The inferred")
        print("  map is NOT written, and the previews stay in channel-index")
        print("  order. What would help: a feature with more structure than a")
        print("  per-channel scalar -- the mean waveform shape, resampled to a")
        print("  common rate -- or a day when both systems recorded")
        print("  simultaneously, which would allow spike-train matching.")
    else:
        print("\n  Agreement is well above chance, so the assignment is")
        print("  carrying real information. Writing the consensus map.")


def control(limit: int = 12) -> None:
    """Positive control: recover a map that is already known to be identity.

    Rocky was recorded on both headstages on the same day, through the same
    NSP onto the same array, so electrode 7 is electrode 7 in both files. If
    these features cannot recover *that* identity map, they certainly cannot
    recover an unknown one across two different acquisition systems, and the
    negative TDT result below is a statement about the method rather than
    about the data.

    This is the experiment that decides whether to keep going.
    """
    inv = pd.read_parquet(INV)
    nev = inv[(inv.role == "snippets") & inv.date.notna()
              & (inv.tree == "Blackrock") & (inv.chain == "")].copy()
    nev["d"] = nev.date.dt.strftime("%Y-%m-%d")
    pairs = []
    for (d, arr), g in nev.groupby(["d", "array"]):
        a = g[g.headstage == "Analog"]
        b = g[g.headstage == "Digital"]
        if len(a) and len(b):
            pairs.append((d, arr, a.iloc[0]["path"], b.iloc[0]["path"]))
    banner("0. Positive control -- can the features recover a KNOWN map?")
    print(f"  same-day analog/digital NEV pairs available: {len(pairs)}")
    print("  truth is the identity map: same array, same NSP, same electrode "
          "ids.\n")
    print(f"  {'date':12s} {'array':10s} {'scalars only':>13s} "
          f"{'+ shape':>9s} {'shape only':>11s}")
    got = []
    for d, arr, pa, pb in pairs[:limit]:
        try:
            sa, sb = nev_signature(Path(pa)), nev_signature(Path(pb))
        except Exception as exc:  # noqa: BLE001
            print(f"  {d} {arr}: {type(exc).__name__}: {exc}"[:110])
            continue
        truth = {int(c): int(c) for c in sa.channel}
        m0, _ = infer_map(sa, sb, shape_weight=0.0)
        m1, _ = infer_map(sa, sb, shape_weight=1.0)
        m2, _ = infer_map(sa.assign(**{f: 0.0 for f in FEATURES}),
                          sb.assign(**{f: 0.0 for f in FEATURES}),
                          shape_weight=1.0)
        r = (agreement(m0, truth), agreement(m1, truth), agreement(m2, truth))
        got.append(r)
        print(f"  {d:12s} {arr:10s} {r[0]:13.3f} {r[1]:9.3f} {r[2]:11.3f}")
    if got:
        g = np.array(got)
        print(f"\n  median   scalars {np.median(g[:, 0]):.3f}   "
              f"+shape {np.median(g[:, 1]):.3f}   "
              f"shape only {np.median(g[:, 2]):.3f}   "
              f"(chance {CHANCE:.3f})")


def control_crossday(limit: int = 8) -> None:
    """Is the signature a property of the electrode, or of the day?

    The same-day control recovers a known identity map at ~0.45. The TDT
    inference across systems sits at chance. Two very different things could
    explain that gap:

    - the signature is **electrode-specific and stable**, and TDT and
      Blackrock are simply not seeing the same electrodes in a comparable way;
    - the signature is **day-specific** -- driven by whichever neurons happened
      to be firing -- in which case even the same-day control only works
      because the two files are minutes apart, and nothing would ever transfer.

    Matching Blackrock against Blackrock *across different days* separates
    them. The truth is still the identity map, the amplifier is identical, and
    only the elapsed time changes.
    """
    inv = pd.read_parquet(INV)
    nev = inv[(inv.role == "snippets") & inv.date.notna()
              & (inv.tree == "Blackrock") & (inv.chain == "")
              & (inv.headstage == "Digital")].copy()
    nev["d"] = nev.date.dt.strftime("%Y-%m-%d")
    banner("0b. Is the signature stable over days, or only within one?")
    for arr in ("Anterior", "Posterior"):
        g = nev[nev.array == arr].sort_values("d").drop_duplicates("d")
        g = g.head(limit)
        if len(g) < 3:
            continue
        sigs, dates = [], []
        for r in g.itertuples():
            try:
                sigs.append(nev_signature(Path(r.path)))
                dates.append(r.d)
            except Exception:  # noqa: BLE001
                continue
        print(f"\n  {arr}: {len(sigs)} sessions, "
              f"{dates[0] if dates else '-'} .. {dates[-1] if dates else '-'}")
        print(f"    {'gap (days)':>11s} {'agreement':>10s}")
        rows = []
        for i, j in itertools.combinations(range(len(sigs)), 2):
            m, _ = infer_map(sigs[i], sigs[j], shape_weight=1.0)
            truth = {int(c): int(c) for c in sigs[i].channel}
            gap = (pd.Timestamp(dates[j]) - pd.Timestamp(dates[i])).days
            rows.append((gap, agreement(m, truth)))
        rows.sort()
        for gap, a in rows[:4]:
            print(f"    {gap:11d} {a:10.3f}")
        if len(rows) > 4:
            print(f"    ... {len(rows)} pairs total")
        arr_rows = np.array(rows)
        near = arr_rows[arr_rows[:, 0] <= 14]
        far = arr_rows[arr_rows[:, 0] > 30]
        if len(near):
            print(f"    <=14 days apart : median {np.median(near[:, 1]):.3f} "
                  f"(n={len(near)})")
        if len(far):
            print(f"    >30 days apart  : median {np.median(far[:, 1]):.3f} "
                  f"(n={len(far)})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--headstage", default="Digital",
                    choices=("Digital", "Analog"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--control", action="store_true",
                    help="run only the known-map positive control")
    ap.add_argument("--control-crossday", action="store_true",
                    help="test whether the signature is stable across days")
    ap.add_argument("--shape-weight", type=float, default=1.0)
    args = ap.parse_args()

    if args.control:
        control(limit=args.limit or 12)
        return 0
    if args.control_crossday:
        control_crossday(limit=args.limit or 8)
        return 0

    days = build_days(args.headstage)
    banner("TDT channel-map inference from same-day Blackrock")
    print(f"  headstage: {args.headstage}")
    if args.limit:
        days = days.head(args.limit)
    if not len(days):
        print("  no same-day pairings found")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    maps: dict = {}
    rows = []
    sig_cache: dict[str, pd.DataFrame] = {}
    for i, r in enumerate(days.itertuples(), 1):
        try:
            if r.tev not in sig_cache:
                sig_cache[r.tev] = tdt_signature(Path(r.tev))
            t = sig_cache[r.tev]
            n = nev_signature(Path(r.nev))
            m, cost = infer_map(t, n)
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i}/{len(days)}] {r.date} {r.letter}/{r.array}: "
                  f"{type(exc).__name__}: {exc}"[:150])
            continue
        maps[(r.date, r.letter, r.array)] = m
        rows.append(dict(date=r.date, letter=r.letter, array=r.array,
                         block=r.block, cost=cost, n_matched=len(m)))
        print(f"  [{i}/{len(days)}] {r.date} {r.letter}/{r.array:9s} "
              f"cost {cost:.4f}  n={len(m)}", flush=True)

    res = pd.DataFrame(rows)
    res.to_parquet(OUT_DIR / "pairings.parquet", engine="pyarrow", index=False)
    report(days, res, maps)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

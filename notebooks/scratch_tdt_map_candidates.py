"""Test named candidate channel maps against Rocky's TDT/Blackrock overlap.

`scratch_tdt_map_infer.py` tried to *infer* the map with Hungarian assignment
and failed: the signature it relies on is largely transient, so picking one
assignment out of 96! is hopeless. This asks a much weaker question.

TDT's `ZCA-CK96A` adapter datasheet ("ZIF-Clip Headstage to CyberKinetics
CerePort") publishes which headstage channel sits at each socket of the three
36-pin headers that mate with the CerePort. That does not hand over a map --
the socket-to-CerePort-pin correspondence is still unknown -- but it collapses
the search space from 96! to a few dozen **named candidates**. Testing a short
list is a far weaker demand on the data than inferring one.

**The candidate family rests on an assumption that cannot be verified from the
datasheet**: that each header mates with one CerePort bank, and that socket
order within a header follows one of a few natural raster conventions. If the
true map is outside that family, every candidate fails and the test cannot say
whether the family or the signature was at fault. That is why the controls run
first and are reported whatever the outcome.

Phases, in order, because each is a precondition for the next:

    A  power       Blackrock vs Blackrock, same day, truth = identity.
                   Does the statistic separate the truth from random maps?
    B  stability   TDT vs TDT, same array, different days, truth = identity.
                   Do TDT signatures reproduce on their own rig at all?
    C  candidates  TDT vs Blackrock under each candidate map.
    D  binding     TDT _A vs _B, same day. Is the signature bound to the
                   electrode or to the amplifier channel?

Run from repo root:

    uv run python notebooks/scratch_tdt_map_candidates.py --phase A
    uv run python notebooks/scratch_tdt_map_candidates.py --phase all

See:
- docs/notes/tdt_channel_map.md
"""

from __future__ import annotations

import argparse
import sys
import warnings
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))

from scratch_tdt_map_infer import (  # noqa: E402
    ROCKY_TDT,
    build_days,
    featurise,
    nev_signature,
    tdt_signature,
)

OUT_DIR = REPO / "data" / "derived" / "tdt_map"
CACHE = OUT_DIR / "sig_cache"
FIG = REPO / "figures" / "tdt_map"

# Features tested independently. Noise floor is the most electrode-intrinsic
# of them -- it is impedance-driven and should be the most transferable across
# amplifiers -- so it is reported separately rather than pooled into a cost.
FEATURES = ("log_noise", "log_rate", "log_amp50", "log_amp90")
N_NULL = 500          # random permutations forming the null distribution
RNG = np.random.default_rng(0)


# ---------------------------------------------------------------------------
# The published pinout
# ---------------------------------------------------------------------------
# Transcribed from TDT's ZCA-CK96A datasheet, rev 2020-05-12. Each header is a
# 2x18 socket block; labels alternate below/above along each row. Encoded here
# left-to-right, top row then bottom row, exactly as printed.
#
# VERIFY BEFORE TRUSTING: the datasheet is eleven years newer than the era
# this corpus was recorded in, and the part number carries a revision letter.
ZCA_CK96A = {
    "H1": [  # top block in the datasheet figure, carries R1
        ["NA", "G", 88, 84, 80, 76, 72, 68, 64, 60, 56, 52, 71, 67, 63, 59, 55, 51],
        ["G", "R1", 86, 82, 78, 74, 70, 66, 62, 58, 54, 50, 69, 65, 61, 57, 53, 49],
    ],
    "H2": [  # middle block
        ["NA", "G", 8, 4, 23, 19, 15, 11, 7, 3, 95, 91, 87, 83, 79, 75, 96, 92],
        ["G", "G", 6, 2, 21, 17, 13, 9, 5, 1, 93, 89, 85, 81, 77, 73, 94, 90],
    ],
    "H3": [  # bottom block, carries R2
        ["NA", "G", 47, 43, 39, 35, 31, 27, 48, 44, 40, 36, 32, 28, 24, 20, 16, 12],
        ["G", "R2", 45, 41, 37, 33, 29, 25, 46, 42, 38, 34, 30, 26, 22, 18, 14, 10],
    ],
}


def header_channels(h: str) -> list[int]:
    """Signal channels of one header, in printed socket order."""
    flat = [v for row in ZCA_CK96A[h] for v in row]
    return [int(v) for v in flat if not isinstance(v, str)]


def check_pinout() -> None:
    """The 96 numbers must partition 1..96 exactly. A transcription guard."""
    allc = sorted(c for h in ZCA_CK96A for c in header_channels(h))
    assert allc == list(range(1, 97)), (
        f"pinout is not a bijection over 1..96: {len(allc)} entries, "
        f"{len(set(allc))} distinct")
    for h in ZCA_CK96A:
        assert len(header_channels(h)) == 32, f"{h} does not carry 32 channels"


# Socket-order conventions tried within a header. The datasheet fixes which
# channels a header carries but not which CerePort pin each socket is, so this
# is the assumption the candidate family rests on.
ORDERS = {
    "printed": lambda v: v,
    "reversed": lambda v: v[::-1],
    "rowswap": lambda v: v[16:] + v[:16],
    "rowswap_rev": lambda v: (v[16:] + v[:16])[::-1],
}


def candidate_maps() -> dict[str, np.ndarray]:
    """`name -> array[96]` giving the TDT channel for Blackrock channel_id 1..96.

    Blackrock's `channel_id = (bank - 'A') * 32 + pin`, so channel_ids 1-32 are
    bank A, 33-64 bank B, 65-96 bank C. A candidate assigns each bank to one
    adapter header and one socket order within it.
    """
    out: dict[str, np.ndarray] = {}
    for banks in permutations(("H1", "H2", "H3")):
        for oname, ofn in ORDERS.items():
            m = np.zeros(97, dtype=int)
            for bi, h in enumerate(banks):
                chans = ofn(header_channels(h))
                for pin in range(1, 33):
                    m[bi * 32 + pin] = chans[pin - 1]
            name = f"{'-'.join(banks)}/{oname}"
            out[name] = m
    return out


# ---------------------------------------------------------------------------
# Statistic
# ---------------------------------------------------------------------------
def score(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman correlation between two 96-vectors, NaN-safe.

    Correlation rather than Hungarian agreement on purpose. Assignment accuracy
    demands the signature identify each electrode uniquely; correlation only
    demands it rank them consistently, which is a far lower bar and is what
    makes testing a fixed candidate feasible where inference was not.
    """
    from scipy.stats import spearmanr

    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 10:
        return np.nan
    r = spearmanr(a[m], b[m]).statistic
    return float(r) if np.isfinite(r) else np.nan


def null_scores(a: np.ndarray, b: np.ndarray, n: int = N_NULL) -> np.ndarray:
    """Same statistic under random relabelling, the reference distribution."""
    out = np.empty(n)
    for i in range(n):
        out[i] = score(a, b[RNG.permutation(len(b))])
    return out


def z_against_null(obs: float, null: np.ndarray) -> tuple[float, float]:
    """Z and one-sided empirical p of an observed score against its null."""
    null = null[np.isfinite(null)]
    if not len(null) or not np.isfinite(obs):
        return np.nan, np.nan
    z = (obs - null.mean()) / (null.std() or np.nan)
    p = (1 + (null >= obs).sum()) / (1 + len(null))
    return float(z), float(p)


# ---------------------------------------------------------------------------
# Cached signatures
# ---------------------------------------------------------------------------
def cached(key: str, fn) -> pd.DataFrame | None:
    """Signatures are minutes of IO each; compute once per key."""
    CACHE.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "_-." else "_" for c in key)
    p = CACHE / f"{safe}.parquet"
    if p.exists():
        return pd.read_parquet(p)
    try:
        d = fn()
    except Exception as exc:  # noqa: BLE001
        print(f"    ! {key}: {type(exc).__name__}: {str(exc)[:70]}")
        return None
    if d is None or not len(d):
        return None
    d = featurise(d)
    d.drop(columns=[c for c in ("shape",) if c in d]).to_parquet(p, index=False)
    return pd.read_parquet(p)


def vec(sig: pd.DataFrame, feature: str, order: np.ndarray | None = None,
        n: int = 96) -> np.ndarray:
    """Feature as a length-96 vector indexed by channel, optionally remapped."""
    v = np.full(n + 1, np.nan)
    for r in sig.itertuples():
        c = int(r.channel)
        if 1 <= c <= n:
            v[c] = getattr(r, feature)
    if order is None:
        return v[1:]
    return np.array([v[order[i]] if 1 <= order[i] <= n else np.nan
                     for i in range(1, n + 1)])


# ---------------------------------------------------------------------------
# Phases
# ---------------------------------------------------------------------------
def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def blackrock_pairs() -> list[tuple[str, str, str, str]]:
    """Same-day analog/digital NEV pairs. Truth is the identity map."""
    from scratch_tdt_map_infer import INV

    inv = pd.read_parquet(INV)
    nev = inv[(inv.role == "snippets") & inv.date.notna()
              & (inv.tree == "Blackrock") & (inv.chain == "")].copy()
    nev["d"] = nev.date.dt.strftime("%Y-%m-%d")
    out = []
    for (d, arr), g in nev.groupby(["d", "array"]):
        a, b = g[g.headstage == "Analog"], g[g.headstage == "Digital"]
        if len(a) and len(b):
            out.append((d, arr, a.iloc[0]["path"], b.iloc[0]["path"]))
    return out


def phase_a(limit: int) -> pd.DataFrame:
    """Does the statistic separate a known-true map from random ones?

    Same array, same NSP, minutes apart, truth = identity. If the correlation
    under the identity is not far out in the tail of the random-permutation
    null, nothing downstream can work and the candidate test is not worth
    running.
    """
    pairs = blackrock_pairs()[:limit]
    banner(f"PHASE A -- power check on {len(pairs)} same-day Blackrock pairs")
    print("  truth is the identity map. reporting r(identity) against a null")
    print(f"  of {N_NULL} random relabellings.")
    rows = []
    for d, arr, pa, pb in pairs:
        sa = cached("nev_" + Path(pa).stem, lambda p=pa: nev_signature(Path(p)))
        sb = cached("nev_" + Path(pb).stem, lambda p=pb: nev_signature(Path(p)))
        if sa is None or sb is None:
            continue
        for f in FEATURES:
            a, b = vec(sa, f), vec(sb, f)
            obs = score(a, b)
            z, p = z_against_null(obs, null_scores(a, b))
            rows.append(dict(date=d, array=arr, feature=f, r=obs, z=z, p=p))
    r = pd.DataFrame(rows)
    if len(r):
        print()
        print(r.groupby("feature").agg(
            n=("r", "size"), median_r=("r", "median"),
            median_z=("z", "median"),
            frac_p_lt_01=("p", lambda s: float((s < 0.01).mean()))
        ).round(3).to_string())
    return r


def tdt_blocks_by_letter() -> dict[str, list[Path]]:
    """TDT blocks grouped by the A/B letter, longest first."""
    from scratch_tdt_map_infer import find_blocks, tank_clock

    out: dict[str, list[tuple[float, Path]]] = {}
    for tev in find_blocks(ROCKY_TDT):
        start, dur = tank_clock(tev.with_suffix(".tsq"))
        if start is None or not dur or dur < 60:
            continue
        name = tev.parent.name
        letter = "A" if "_A" in name else ("B" if "_B" in name else "")
        if not letter:
            continue
        out.setdefault(letter, []).append((dur, tev))
    return {k: [t for _, t in sorted(v, key=lambda x: -x[0])]
            for k, v in out.items()}


def phase_b(limit: int) -> pd.DataFrame:
    """Do TDT signatures reproduce on their own rig, across days?

    Same tank letter, two different days, no adapter or amplifier change --
    truth is the identity. This isolates whether the signature survives a
    change of day at all, separately from whether it survives a change of
    system. A null result here means no cross-rig test can succeed and the
    candidate phase cannot be interpreted.
    """
    by_letter = tdt_blocks_by_letter()
    banner("PHASE B -- do TDT signatures reproduce across days on one rig?")
    rows = []
    for letter, blocks in sorted(by_letter.items()):
        use = blocks[:limit]
        print(f"  letter {letter}: {len(blocks)} blocks, using {len(use)}")
        sigs = []
        for tev in use:
            s = cached("tdt_" + tev.parent.name, lambda t=tev: tdt_signature(t))
            if s is not None:
                sigs.append((tev.parent.name, s))
        for i in range(len(sigs)):
            for j in range(i + 1, len(sigs)):
                for f in FEATURES:
                    a, b = vec(sigs[i][1], f), vec(sigs[j][1], f)
                    obs = score(a, b)
                    z, p = z_against_null(obs, null_scores(a, b))
                    rows.append(dict(letter=letter, a=sigs[i][0], b=sigs[j][0],
                                     feature=f, r=obs, z=z, p=p))
    r = pd.DataFrame(rows)
    if len(r):
        print()
        print(r.groupby(["letter", "feature"]).agg(
            n=("r", "size"), median_r=("r", "median"),
            median_z=("z", "median"),
            frac_p_lt_01=("p", lambda s: float((s < 0.01).mean()))
        ).round(3).to_string())
    return r


def phase_c(limit: int) -> pd.DataFrame:
    """Score every candidate map on the TDT/Blackrock same-day overlap.

    The correct candidate, if it is in the family, should stand out from the
    other 47 and from the random null. Anything less is not an answer.
    """
    days = build_days("Digital")
    if not len(days):
        days = build_days("Analog")
    days = days.drop_duplicates(["date", "letter", "array"]).head(limit)
    cands = candidate_maps()
    banner(f"PHASE C -- {len(cands)} candidate maps on {len(days)} pairings")
    rows = []
    for r in days.itertuples():
        st = cached("tdt_" + Path(r.tev).parent.name,
                    lambda t=r.tev: tdt_signature(Path(t)))
        sn = cached("nev_" + Path(r.nev).stem,
                    lambda p=r.nev: nev_signature(Path(p)))
        if st is None or sn is None:
            continue
        for f in FEATURES:
            bl = vec(sn, f)                    # indexed by channel_id 1..96
            null = null_scores(bl, vec(st, f))
            for name, m in cands.items():
                obs = score(bl, vec(st, f, order=m))
                z, p = z_against_null(obs, null)
                rows.append(dict(date=r.date, letter=r.letter, array=r.array,
                                 feature=f, candidate=name, r=obs, z=z, p=p))
    return pd.DataFrame(rows)


def phase_d(limit: int) -> pd.DataFrame:
    """Is the TDT signature a property of the ELECTRODE or of the AMPLIFIER?

    Rocky's TDT tanks come in `_A` and `_B` blocks, nominally the two arrays.
    Correlating an `_A` block against the same day's `_B` block **under the
    identity channel order** separates two hypotheses that look identical from
    inside a single block:

    - if the signature tracks the electrode, two different arrays share
      nothing and this reads ~0;
    - if it tracks the amplifier channel, the two blocks share the rig's state
      on that day and this reads high.

    The answer decides whether any channel map is findable from these features
    at all, which is why it belongs beside the candidate test rather than
    after it.
    """
    from scratch_tdt_map_infer import find_blocks, tank_clock

    blocks: dict[str, dict[str, Path]] = {}
    for tev in find_blocks(ROCKY_TDT):
        st, dur = tank_clock(tev.with_suffix(".tsq"))
        if st is None or not dur or dur < 60:
            continue
        n = tev.parent.name
        letter = "A" if "_A" in n else ("B" if "_B" in n else "")
        if letter:
            blocks.setdefault(str(st.date()), {}).setdefault(letter, tev)

    days = sorted(d for d, v in blocks.items() if len(v) == 2)
    banner("PHASE D -- is the TDT signature electrode-bound or amplifier-bound?")
    print(f"  days carrying both an _A and a _B block: {len(days)}, "
          f"using {min(limit, len(days))}")
    rows = []
    for d in days[:limit]:
        sa = cached("tdt_" + blocks[d]["A"].parent.name,
                    lambda t=blocks[d]["A"]: tdt_signature(t))
        sb = cached("tdt_" + blocks[d]["B"].parent.name,
                    lambda t=blocks[d]["B"]: tdt_signature(t))
        if sa is None or sb is None:
            continue
        for f in FEATURES:
            a, b = vec(sa, f), vec(sb, f)
            obs = score(a, b)
            z, p = z_against_null(obs, null_scores(a, b))
            rows.append(dict(date=d, feature=f, r=obs, z=z, p=p))
    r = pd.DataFrame(rows)
    if len(r):
        print()
        print(r.groupby("feature").agg(
            n=("r", "size"), median_r=("r", "median"),
            median_z=("z", "median"),
            frac_p_lt_01=("p", lambda s: float((s < 0.01).mean()))
        ).round(3).to_string())
        print("\n  Read against phase B (same letter, different days). A feature")
        print("  that scores HIGH here and LOW there is tracking the rig, not")
        print("  the electrode, and cannot identify a channel map.")
    return r


def report_c(c: pd.DataFrame) -> None:
    if not len(c):
        print("  no candidate scores")
        return
    print("\n  candidates ranked by median |r| across pairings, per feature:")
    for f, g in c.groupby("feature"):
        agg = (g.groupby("candidate").r.median().abs()
               .sort_values(ascending=False))
        zz = g.groupby("candidate").z.median()
        print(f"\n  --- {f} ---")
        for name in list(agg.index)[:5]:
            print(f"    {name:24s} median |r| {agg[name]:.4f}   "
                  f"median z {zz[name]:+.2f}")
        worst = agg.index[-1]
        print(f"    {'... worst of ' + str(len(agg)):24s} median |r| "
              f"{agg.iloc[-1]:.4f}   median z {zz[worst]:+.2f}")
    print("\n  A correct map should sit far above every other candidate AND")
    print("  far outside the null. A flat ranking means the family is wrong,")
    print("  the signature does not transfer, or both -- and this test cannot")
    print("  separate those two.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="A", choices=["A", "B", "C", "D", "all"])
    ap.add_argument("--limit", type=int, default=12)
    args = ap.parse_args()

    check_pinout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cands = candidate_maps()
    print("  pinout verified: 3 headers x 32 channels, bijection over 1..96")
    print(f"  candidate maps: {len(cands)} "
          f"(3! bank assignments x {len(ORDERS)} socket orders)")

    if args.phase in ("A", "all"):
        a = phase_a(args.limit)
        if len(a):
            a.to_parquet(OUT_DIR / "cand_phaseA.parquet", index=False)
    if args.phase in ("B", "all"):
        b = phase_b(min(args.limit, 6))
        if len(b):
            b.to_parquet(OUT_DIR / "cand_phaseB.parquet", index=False)
    if args.phase in ("D", "all"):
        d = phase_d(args.limit)
        if len(d):
            d.to_parquet(OUT_DIR / "cand_phaseD.parquet", index=False)
    if args.phase in ("C", "all"):
        c = phase_c(args.limit)
        if len(c):
            c.to_parquet(OUT_DIR / "cand_phaseC.parquet", index=False)
            report_c(c)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

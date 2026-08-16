"""What each NEV variant actually contains, read from the spike packets.

The suffix chain says who touched a file; it does not say what changed. This
reads the unit-class byte of every spike packet and compares variants of the
same recording, which answers three questions the filenames cannot:

- what is the undeclared ``-00``?
- does a curation pass change spike times, or only labels?
- where an operator has two passes over one recording (``-MA`` and
  ``-MA-RE``), how much do they agree with themselves?

That last one is the denominator the inter-operator comparison needs. Two
operators disagreeing by more than one operator disagrees with themselves is a
standards difference; less than that is noise.

NEV 2.x spike packet: uint32 timestamp, uint16 packet id (0 = digital input,
1..512 = electrode), uint8 unit class, uint8 reserved, then the waveform.
Unit class is 0 unsorted, 1..16 sorted units, 255 noise.

Run from repo root:

    uv run python notebooks/scratch_monkey_variants.py

See:
- docs/notes/monkey_corpus.md
"""

from __future__ import annotations

import hashlib
import struct
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
INV = REPO / "data" / "derived" / "monkey_inventory.parquet"
ROOT = Path(r"D:\Claude Code\Monkey Data")
OUT = REPO / "data" / "derived" / "monkey_variant_compare.parquet"

DIGITAL_PACKET_ID = 0        # serial/digital input, not a spike
NOISE_CLASS = 255


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === Reading spike packets ===
def read_packets(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (timestamps, electrode ids, unit classes) for every spike packet.

    Digital-input packets (id 0) are dropped -- they are events, not spikes.
    """
    raw = path.read_bytes()
    spec_major = raw[8]
    hdr_bytes, pkt_bytes = struct.unpack("<II", raw[12:20])
    if spec_major >= 3:
        raise NotImplementedError(f"{path.name}: NEV spec {spec_major}.x")
    body = raw[hdr_bytes:]
    n = len(body) // pkt_bytes
    body = body[: n * pkt_bytes]
    arr = np.frombuffer(body, dtype=np.uint8).reshape(n, pkt_bytes)
    ts = arr[:, 0:4].copy().view(np.uint32).ravel()
    eid = arr[:, 4:6].copy().view(np.uint16).ravel()
    cls = arr[:, 6]
    keep = eid != DIGITAL_PACKET_ID
    return ts[keep], eid[keep], cls[keep]


def summarise(path: Path) -> dict:
    """Spike count, unit-class histogram and a content hash for one NEV."""
    ts, eid, cls = read_packets(path)
    hist = Counter(cls.tolist())
    sorted_units = {c for c in hist if 0 < c < NOISE_CLASS}
    return dict(
        n_spikes=len(ts),
        n_electrodes=len(np.unique(eid)),
        n_unsorted=hist.get(0, 0),
        n_noise=hist.get(NOISE_CLASS, 0),
        n_assigned=sum(v for c, v in hist.items() if 0 < c < NOISE_CLASS),
        max_unit=max(sorted_units) if sorted_units else 0,
        # Units are per electrode, so the total is counted per (elec, class).
        n_units=len({(e, c) for e, c in zip(eid, cls, strict=True)
                     if 0 < c < NOISE_CLASS}),
        ts_hash=hashlib.md5(ts.tobytes()).hexdigest()[:12],
        size=path.stat().st_size,
    )


# %%
# === Comparisons ===
def compare_group(files: dict[str, Path]) -> pd.DataFrame:
    """Summarise every variant of one recording, keyed by suffix chain."""
    rows = []
    for chain, p in sorted(files.items()):
        try:
            rows.append(dict(chain=chain or "(orig)", name=p.name,
                             **summarise(p)))
        except (NotImplementedError, ValueError, OSError) as exc:
            rows.append(dict(chain=chain or "(orig)", name=p.name,
                             error=str(exc)[:60]))
    return pd.DataFrame(rows)


def show(title: str, files: dict[str, Path], note: str = "") -> pd.DataFrame:
    banner(title)
    if note:
        print(f"  {note}\n")
    df = compare_group(files)
    cols = [c for c in ["chain", "n_spikes", "n_electrodes", "n_unsorted",
                        "n_assigned", "n_noise", "n_units", "max_unit",
                        "ts_hash", "size"] if c in df]
    print(df[cols].to_string(index=False))
    if "ts_hash" in df and len(set(df.ts_hash)) == 1:
        print("\n  -> identical spike times across all variants: the sort and"
              "\n     curation change LABELS only, never detection.")
    elif "ts_hash" in df:
        same = df.groupby("ts_hash").chain.apply(list).to_dict()
        print(f"\n  -> spike times differ between variants: {same}")
    return df


def main() -> int:
    inv = pd.read_parquet(INV)
    nev = inv[inv.role == "snippets"].copy()

    # --- 1. What is -00? Compare against the original of the same recording.
    z = nev[nev.chain == "-00"]
    for stem in sorted(set(z.stem)):
        g = nev[(nev.stem == stem) & nev.chain.isin(["", "-00", "-01"])]
        files = {r.chain: ROOT / r.rel for r in g.itertuples()}
        show(f"1. The undeclared -00  --  {stem}", files,
             "Read as spike packets rather than trusted from the name.")

    # --- 2. Does curation change detection, or only labels?
    tri = (nev[nev.subject == "Rocky"]
           .groupby("stem").chain.apply(set))
    pick = [s for s, c in tri.items() if {"", "-01", "-02"} <= c]
    if pick:
        g = nev[(nev.stem == pick[0]) & nev.chain.isin(["", "-01", "-02"])]
        show(f"2. Sort and curation on one recording  --  {pick[0]}",
             {r.chain: ROOT / r.rel for r in g.itertuples()},
             "original -> OFS automatic -> operator DS.")

    # --- 3. Sidd's repeat passes: within-operator agreement.
    rep = nev.groupby("stem").chain.apply(set)
    repeats = [s for s, c in rep.items()
               if "-MA" in c and ({"-MA-RE", "-MA-02"} & c)]
    banner("3. Within-operator repeats (Sidd sorted the same file twice)")
    print(f"  recordings with both -MA and a redo: {len(repeats)}")
    rows = []
    for stem in repeats:
        g = nev[(nev.stem == stem)
                & nev.chain.isin(["-MA", "-MA-RE", "-MA-02"])]
        files = {r.chain: ROOT / r.rel for r in g.itertuples()}
        try:
            s = {c: summarise(p) for c, p in files.items()}
        except (NotImplementedError, ValueError, OSError):
            continue
        first, redo = s.get("-MA"), s.get("-MA-RE") or s.get("-MA-02")
        if not first or not redo:
            continue
        rows.append(dict(
            stem=stem[:34],
            units_first=first["n_units"], units_redo=redo["n_units"],
            d_units=redo["n_units"] - first["n_units"],
            noise_first=first["n_noise"], noise_redo=redo["n_noise"],
            same_times=first["ts_hash"] == redo["ts_hash"],
        ))
    if rows:
        rep_df = pd.DataFrame(rows)
        print(rep_df.to_string(index=False))
        up = int((rep_df.d_units > 0).sum())
        print(f"\n  median change in unit count: {rep_df.d_units.median():+.0f}"
              f"   ({up} of {len(rep_df)} passes increased it)")
        same_noise = int((rep_df.noise_first == rep_df.noise_redo).sum())
        print(f"  noise assignment unchanged in {same_noise} of {len(rep_df)}")
        print("\n  Read this as a REVISION, not a test-retest. The redo moves in"
              "\n  one direction -- more units, identical noise -- so it bounds"
              "\n  how far one operator's output shifts on reconsideration, but"
              "\n  it is not a symmetric noise floor for the between-operator"
              "\n  comparison. Splitting, not relabelling.")
        rep_df.to_parquet(OUT, engine="pyarrow", index=False)
        print(f"\n  wrote {OUT.relative_to(REPO)}")

    # --- 3b. Does the "labels only" result hold corpus-wide, or only on the
    # handful of recordings inspected above? Checked on every recording that
    # has more than one variant staged.
    banner("3b. Do any variants change the spike times? (all recordings)")
    multi = [s for s, c in nev.groupby("stem").chain.apply(set).items()
             if len(c) > 1]
    print(f"  recordings with >1 variant : {len(multi)}")
    same = diff = err = 0
    offenders: list[str] = []
    for stem in multi:
        g = nev[nev.stem == stem]
        try:
            hashes = {summarise(ROOT / r.rel)["ts_hash"] for r in g.itertuples()}
        except (NotImplementedError, ValueError, OSError):
            err += 1
            continue
        if len(hashes) == 1:
            same += 1
        else:
            diff += 1
            offenders.append(stem)
    print(f"  identical spike times across variants : {same}")
    print(f"  DIFFERENT spike times                 : {diff}")
    print(f"  unreadable                            : {err}")
    if offenders:
        print("\n  recordings whose variants disagree on detection:")
        for s in offenders[:15]:
            print(f"      {s}")
    else:
        print("\n  -> Corpus-wide: sorting and curation never re-detect. Every"
              "\n     variant of a recording carries the SAME event set, so"
              "\n     comparing two sorts is a labelling comparison on a fixed"
              "\n     set -- no spike matching, no tolerance window.")

    # --- 4. -MADS is sequential, not independent.
    banner("4. -MADS: Sidd sorted, DS curated on top -- NOT independent")
    m = nev[nev.chain == "-MADS"]
    for stem in sorted(set(m.stem)):
        g = nev[(nev.stem == stem) & nev.chain.isin(["-MA", "-MADS", "-DS"])]
        files = {r.chain: ROOT / r.rel for r in g.itertuples()}
        if len(files) > 1:
            show(f"   {stem}", files, "DS's edits sit on top of Sidd's output.")
        else:
            print(f"  {stem}: only {list(files)} staged -- nothing to compare")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Canonical ORIG/OFS pairing for the Rocky snippet corpus (nav D-015).

One combo per (date, array). The combo's LINEAGE is the ORIG whose
stem + "-01" matches the chosen OFS file's stem, so the resort layer
and the Plexon layer describe the SAME recording, and the stem written
into every derived row names the file that was actually read.

Why this exists (nav I-007): the previous pairing took iloc[0] of
ORIG and OFS independently within each (date, array). On the 2018
dual-headstage days those are different recordings, so 80 of 332
combos carried Digital -01 data under an Analog stem, and two of
those Digital -01 files are truncated Plexon exports (1 event), which
poisoned the Analog-stem rows downstream.

Rule, in order:
1. Take the (date, array) groups where both ORIG and OFS exist.
2. Choose the OFS file (iloc[0] of the OFS side, as before).
3. Choose the ORIG whose stem equals that OFS stem minus "-01" -
   the same recording. All 332 combos resolve this way on the current
   index (measured 2026-09-21: 252 already matched + 80 re-paired,
   0 fallbacks).
4. If no stem-matched ORIG existed, fall back to iloc[0] and let the
   caller's truncation guard compare event counts.

Every caller stamps `source_nev` (the file actually read) onto its
output rows; a reader that finds the OFS file empty or truncated
(fewer events than electrodes) reads the ORIG instead and flags
`ofs_truncated`.
"""

from __future__ import annotations

import pandas as pd


def paired_combos(idx: pd.DataFrame) -> list[tuple[pd.Series, pd.Series]]:
    """[(orig_row, ofs_row)] per (date, array), stem-matched lineage."""
    combos = idx.groupby(["date", "array"])["kind"].agg(set)
    paired = combos[combos.apply(
        lambda s: "ORIG" in s and "OFS" in s)].index
    out = []
    for date, array in paired:
        sub = idx[(idx["date"] == date) & (idx["array"] == array)]
        o = sub[sub["kind"] == "ORIG"]
        f = sub[sub["kind"] == "OFS"]
        if not (len(o) and len(f)):
            continue
        frow = f.iloc[0]
        stem = frow["stem"]
        base = stem[:-3] if stem.endswith("-01") else stem
        match = o[o["stem"] == base]
        orow = match.iloc[0] if len(match) else o.iloc[0]
        out.append((orow, frow))
    return out

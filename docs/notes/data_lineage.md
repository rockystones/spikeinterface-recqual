# Data lineage: which derived row comes from which file

Written after the I-007 pairing bug (2026-09-21) so the answer to
"what file produced this number?" is always checkable, not assumed.

## The bug, plainly

The Rocky snippet corpus is processed as one combo per **(date,
array)**. On most days one recording exists per array, so "the
original file" and "the sorted file" are unambiguous. But through
2018 each array was recorded **twice per day** — once through the
Analog headstage, once through the Digital — and only the Digital
file was human-sorted.

The pipelines (`scratch_rocky_resort.py`, `scratch_rocky_events.py`)
selected, within each (date, array) group, the first ORIG row and the
first OFS row **independently** (`iloc[0]` on each side). Sorted
alphabetically, "Analog" precedes "Digital", so the ORIG pick was the
Analog file while the OFS pick was the Digital `-01`. Both pipelines
then read **only the `-01` file** (a legitimate optimization — a
sorted NEV carries the same events as its original, verified — but
only when the two files are the same recording) and stamped every
output row with the **ORIG's stem**. Result: 80 of 332 combos carried
Digital data under an Analog name. The failure was invisible because
both files are real recordings of the same array minutes apart; it
only surfaced when two Digital `-01` files turned out to be truncated
exports (one event), producing absurd rows under Analog stems.

Lesson encoded in the fix: **never join two file pickers; derive one
file from the other's name.**

## The rule now (nav D-015)

- `notebooks/_pairing.py` is the single pairing authority: a combo's
  lineage is the ORIG whose stem + `-01` equals the OFS file's stem.
  One recording, two labelings, one stem.
- **Truncation guard**: a `-01` under half its original's size is an
  aborted export; the pipeline reads the original instead, skips the
  ofs layer, and sets `ofs_truncated=True`. (Defensive only - no
  current file trips it; the Dec-2018 one-event files are faithful
  copies of pathological recordings and are excluded as outliers.)
- **Provenance column**: every rebuilt shard row carries
  `source_nev` — the filename actually read. A NaN `source_nev`
  means the shard predates the rebuild; all such shards were verified
  stem-matched (the 252 untouched combos).

## Who reads what, cohort by cohort

| derived store | reader | file it reads | stem it writes |
|---|---|---|---|
| `rocky/shards` → `units_long` | scratch_rocky_resort | the `-01` (original if truncated) | the matching ORIG stem |
| `rocky/event_shards` → `events_electrode`, giants | scratch_rocky_events | same rule | same |
| `cohort/mmp2p_shards` → `mean_max_p2p` | scratch_mean_max_p2p_pass | canonical **sorted** NEV (I-004 preference) | the sorted file's stem minus chain |
| `ns5/consensus` shards | scratch_ns5_consensus | continuous `.ns5` | ns5 stem |
| provenance stores | scratch_provenance_dump | canonical sorted NEV | sorted stem |
| `surface/electrode_metrics` | scratch_surface_conditions | Nigel/Fisk sorted NEVs | per-recording stem |

After the rebuild the 332-corpus stems on dual-headstage days are the
**Digital** ones, which is also what the mmp2p / provenance layers
use — stem-level joins across cohorts are now consistent. The Analog
recordings of those days are simply not part of any derived corpus
(they were never sorted); they remain on disk, listed in
`monkey_inventory.parquet`.

## How to audit a number

1. Find its stem and table; take `source_nev` if present.
2. `session_index.parquet` (Rocky) or `monkey_inventory.parquet`
   (cohort) maps stem → absolute path, size, kind.
3. The inspection kit (`scratch_outlier_inspect.py`,
   `matlab/rocky_outlier_inspect.m`) rebuilds any session's units and
   metrics from the named file directly.

## Related

[[segment_handling]], [[snippet_sorting]], [[longitudinal_metrics]];
nav I-007, D-015.

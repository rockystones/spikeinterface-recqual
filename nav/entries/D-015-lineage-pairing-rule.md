---
id: D-015
type: decision
status: accepted
title: Combos pair by stem-matched lineage; every derived row stamps source_nev; truncated -01 exports fall back to the original
created: 2026-09-21
actor: agent
basis: recorded
parent: P-03
resolves: [I-007]
informs: [REF-003]
source: [notebooks/_pairing.py, notebooks/scratch_rocky_resort.py, notebooks/scratch_rocky_events.py]
---
Repair design for I-007, run 2026-09-21 on owner instruction ("I need
absolute clarity of which derived data comes from which files").

Context: the resort and events pipelines paired ORIG and OFS by
(date, array) with independent iloc[0] picks, then read only the -01
file; 80 dual-headstage combos mixed lineages, and two truncated -01
exports poisoned their stems' rows.

Choice (shared helper notebooks/_pairing.py):
1. A combo's lineage is the ORIG whose stem + "-01" equals the chosen
   OFS file's stem - both methods and the stem now name ONE
   recording. On the 80 re-paired combos the stems flip
   Analog -> Digital, which also aligns them with the 405-session
   NEV-cohort tables (mmp2p) that always used the sorted files.
2. TRUNCATION GUARD: a -01 smaller than half its original is an
   aborted export - the pipeline then reads the ORIGINAL, skips the
   unscoreable ofs layer, and flags ofs_truncated. (CORRECTION,
   same day: the two Dec-2018 one-event files are NOT truncated
   exports - each -01 mirrors its original exactly. The Digital
   Posterior RECORDINGS of 12-06/12-13 are themselves pathological:
   9 and 6 segments spanning ~40 hours holding one spike event. The
   guard therefore never fires on them; they are handled as owner
   outlier exclusions instead. The guard stays as protection against
   genuine aborted exports.)
3. PROVENANCE: every rebuilt shard row carries source_nev (the file
   actually read). Older, untouched shards predate the column and
   read NaN - a NaN source_nev means "pre-D-015 shard, lineage
   already verified stem-matched".

Alternatives considered: keeping the Analog lineage on dual-headstage
days (rejected - the human sort exists only for the Digital file, so
the ofs layer would vanish from 80 combos and the mmp2p join would
stay broken); processing every stem instead of one per (date, array)
(rejected for now - it changes the corpus definition that all
downstream pairing assumes; can be revisited).

Consequence: 320 shard files (80 combos x 4 shard dirs) deleted and
rebuilt; all aggregates and downstream tables regenerated. Outcome
entry: R-025.

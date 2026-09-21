---
id: R-025
type: result
status: current
title: Lineage rebuild - 80 combos re-stamped, values unchanged, every published trend stable
created: 2026-09-21
actor: agent
basis: recorded
parent: P-03
depends_on: [D-015, D-016]
informs: [Q-006, REF-003]
source: [data/derived/rocky/units_long.parquet, data/derived/rocky/events_electrode.parquet, results/01_resampling.md]
---
Outcome of the I-007 repair (owner-ordered 2026-09-21).

WHAT CHANGED: labels and provenance, not data. The old shards had
already computed the Digital -01 recordings' content - only the stem
said Analog. After the rebuild the 80 combos carry their true Digital
stems plus source_nev on every row (24,193 unit rows, 7,490 electrode
rows stamped); row counts match the old tables almost exactly because
the underlying files are the same. Stem-level joins with the
405-session NEV cohort (mmp2p, provenance stores) are now consistent.

VERIFIED STABLE after rebuild + the D-016 restorations:
- longitudinal trends: Posterior yield rho -0.644 (note says -0.64);
- coating ratios: consensus-by-2 1.489 / by-3 1.758 (R-017 exact);
- variance: rho 0.236 vs 0.235, all sham SDs within CI noise
  (results/01-06 regenerated);
- headstage-pair analyses (S12) never touched the combo corpus - they
  read the per-file cohort pass - so the Analog-vs-Digital verdicts
  were NEVER contaminated. The bug's practical damage was confined to
  the two pathological Dec-2018 stems' bookkeeping and to stem-join
  consistency.

NEW FACT surfaced by the repair: the Dec-2018 Posterior DIGITAL
recordings are pathological captures - 28.5/29.9 MB, 9/6 segments
spanning ~40 HOURS, one spike event each (the -01 mirrors them
exactly; nothing was truncated). Their Analog same-day counterparts
are normal 182-184 s recordings but were never sorted, so they sit
outside every sorted corpus. 12-06 Digital was already owner-excluded
(2026-09-19); 12-13 Digital added provisionally as the same class -
owner confirmation requested.

Exclusion set after D-016: 23 stems (six restored, one added).

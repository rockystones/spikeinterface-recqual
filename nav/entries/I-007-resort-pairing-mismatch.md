---
id: I-007
type: problem
status: open
title: Resort corpus paired ORIG and OFS by (date, array) ignoring headstage - 80 of 332 combos read the Digital -01 file under the Analog stem
created: 2026-09-19
actor: agent
basis: recorded
parent: P-03
informs: [REF-003, R-021]
source: [notebooks/scratch_rocky_resort.py, data/derived/rocky/session_index.parquet]
---
Found while adding the owner's Digital 12-06-2018 exclusion (chat
2026-09-19). scratch_rocky_resort's --all path groups session_index
by (date, array) and takes iloc[0] of ORIG and OFS separately; on
dual-headstage days these are DIFFERENT recordings. It then reads
ONLY the -01 file ("it carries the same events as the original") and
stamps the output with the ORIG's stem. Measured scope: 80 of 332
paired combos are headstage-mismatched (Analog stem, Digital -01
data), essentially the whole dual-headstage 2018 block; 123 combos
have multiple ORIG or OFS files at all.

Consequences, concrete cases verified:
- Rocky_Posterior_12-06/12-13-2018 AnalogHeadstage rows in
  events_electrode / units_long are 1-event stubs: the Digital -01
  files on those dates are TRUNCATED Plexon exports (12-06 carries
  exactly one event - electrode 40, unit code 77, 3.9 mV - the
  mean_max_p2p NaN-fill peak). The Analog ORIGINAL NEVs are healthy
  184-s recordings (241,808 snippets, 96 electrodes). My earlier
  statement that these sessions are "near-dead recordings" was WRONG
  - the recordings are fine, the derived rows describe a different,
  truncated file.
- The z-flag "amplitude blowup" outliers on the Analog Dec-2018
  stems flagged this artifact, not the tissue. Their exclusion (and
  the owner's Digital 12-06 ruling) still stands for the CURRENT
  tables, but both should be re-evaluated after repair.
- Any stem-level join between the 332-corpus tables and the
  405-session NEV cohort mixes headstages on the 80 combos; the
  Analog-vs-Digital headstage comparisons built from these tables
  compared Digital against itself on those days.

Repair direction (not yet run): pair OFS to ORIG by exact stem
(+"-01"), fall back to resorting the ORIG where no matching -01
exists; rebuild the 80 mismatched shards + the 2 truncated-stub
combos; regenerate events_electrode / units_long / giants /
two_array_metrics and re-check every downstream trend that consumed
them (longitudinal_metrics note, S-sweeps, crossing-rate variance
metric). Owner sign-off wanted before the rebuild since published
figures shift.

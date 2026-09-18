---
id: R-023
type: result
status: current
title: Legacy TDT cohort replicates the variance structure - between-subject SD 0.239 vs modern 0.227
created: 2026-09-17
actor: agent
basis: recorded
parent: P-03
informs: [Q-006]
depends_on: [R-020, R-014]
source: [notebooks/scratch_variance_legacy.py, results/05_legacy_resampling.md]
---
W-020 step 5: Analysis 1 repeated on the compiled TDT per-channel
amplitude sets (unitsum.sig, definition tdt_sig): Chase, Oops A/B,
Picasso A/B - 215 sessions, 72 array-month cells, months 0-20.
Resampling only (sig carries no cross-session channel identity, so
cells pool sessions and the MoM route is not constructible; the
pooled within-SD includes vE, making the ratios conservative).
Luigi excluded (session means only).

REPLICATION: within-array SD 0.0706 (modern 0.0585), between-subject
0.2386 (modern 0.2268) - the two design levels agree across cohorts
recorded on different systems a decade apart. Efficiency x11.4
realistic / x4.4 matched, against the modern x15.0 / x8.6.

Between-array reads 0.2301 - as large as between-subject - but BOTH
legacy pairs are coated-vs-uncoated, so this level contains the full
treatment effect (R-017's coating ratios of 1.3-1.9x are 0.11-0.28 in
log10, the right size to produce exactly this inflation). It is the
contamination warning from R-020 demonstrated at full strength: with
whole-array treatment assignment, the device level is indistinguishable
from the treatment.

No clean pair exists in the legacy cohort; month anchors for
Oops/Picasso are first-session (no implant date in the compile).

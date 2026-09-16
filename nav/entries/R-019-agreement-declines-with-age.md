---
id: R-019
type: result
status: current
title: Sorter agreement declines with implant age on dying arrays and only there
created: 2026-09-16
actor: agent
basis: recorded
parent: P-04
resolves: [W-019]
informs: [Q-008, R-001, R-016]
source: [notebooks/scratch_ns5_consensus.py, "data/derived/ns5/consensus/consensus_pairs.parquet", "expand.log aggregate 2026-09-16"]
---
W-019 complete: 206/206 selected stems sorted 4/4 (214 stems with kept
trains overall; all 26 Rocky I1 same-day pairs included). The
full-coverage agreement-vs-date trends:

  Nigel Anterior   rho -0.74  p 1.3e-4  (n=21)
  Nigel Posterior  rho -0.63  p 4.3e-3  (n=19)
  Rocky I1 Post    rho -0.56  p 1.3e-4  (n=41)
  Rocky I1 Ant     rho +0.005 p 0.98    (n=41)   healthy: flat
  Fisk both        rho +0.07/-0.20, n.s. (n=36)  healthy: flat
  Rocky I2 both    n.s. (n=10)

Median pairwise agreement stays in a narrow band everywhere (0.285-
0.355), so the LEVEL is uninformative - the TREND is the signal: the
pool disagrees progressively more as an array dies, and does not on
arrays that stay healthy. Q-008's prediction (credence 0.75) is
supported on the trend axis; the remaining falsifier test - is the
trend more predictive than single-sorter counts of independent markers
like impedance - is still open, so Q-008 stays open with this as
evidence rather than the answer.

Supersedes the dispersion-proxy reading in multisorter_agreement.md
("disagreement does not grow with implant age"), which rested on the
chance-saturated recovery fractions (I-005) and 6-stem-per-array
coverage.

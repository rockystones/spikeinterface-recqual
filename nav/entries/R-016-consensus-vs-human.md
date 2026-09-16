---
id: R-016
type: result
status: current
title: Consensus replaces the human sort as a yield tracker, not as a unit inventory
created: 2026-09-14
actor: agent
basis: recorded
parent: P-03
resolves: [Q-009]
informs: [Q-008, R-001]
evidence: [I-005]
source: [notebooks/scratch_consensus_vs_ofs.py, docs/notes/consensus_vs_human.md]
---
45 stems (Rocky/Nigel/Fisk), every sorter and consensus rung vs the
canonical Plexon sort, lag-corrected (I-005):

- Unit-for-unit: 0-7% of human units find a >=0.5-agreement counterpart
  in ANY candidate; flat from 1 to 3 ms windows - structural, not
  timing. The human and automatic partitions are different objects.
- Spike level: the top decile of human units is recalled >=0.99 by KS4
  and consensus-2; the median human unit only 0.13-0.65 - the tail of
  small human-accepted units has no automatic counterpart. Consensus-3
  keeps ~60 and consensus-4 ~20 units vs the human's 100-200.
- Longitudinal: FINAL, full W-019 coverage (196 stems with usable
  Plexon layers): consensus-2/3 track human counts at Spearman rho
  +0.60/+0.61 (p ~ 1e-20; Nigel +0.86/+0.88, Rocky +0.61/+0.63, Fisk
  +0.41/+0.39), ahead of every single sorter (+0.44 SC2 to +0.59 MS5).
  The ordering - consensus above each single sorter - replicated at
  45, 87 and 196 stems while the point estimate settled from +0.74 to
  +0.60 as denser, narrower-range sessions entered.

Answer to Q-009: not a replacement for the unit inventory; a better-
than-any-single-sorter replacement for tracking yield over an array's
life. Coverage extends automatically as W-019 completes (script resumes
from shards).

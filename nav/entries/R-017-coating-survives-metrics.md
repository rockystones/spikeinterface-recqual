---
id: R-017
type: result
status: current
title: The Rocky I1 coated/uncoated contrast survives every measurement chain
created: 2026-09-14
actor: agent
basis: recorded
parent: P-03
resolves: [Q-010]
informs: [Q-006, R-016]
depends_on: [W-019]
source: [notebooks/scratch_coating_metrics.py, "data/derived/cohort/coating_by_metric.parquet", figures/treatment/W6_coating_by_metric.png]
---
Within-session paired ratios, Anterior(L1-coated)/Posterior(uncoated),
Rocky I1, Wilcoxon on log-ratios - all 13 chains point the same way and
all reject the null:

- ofs: units/electrode 1.08 (n=151), median amplitude 1.33
- resort gated: 1.96 (n=135)
- legacy exact mean-max-P2P: 1.26 (n=153)
- sorting-free: crossing rate 1.88, amp_p50 1.32, noise 1.07 (n=153)
- modern sorters on continuous ns5 (the W-019 pairs, n=25-27):
  KS4 1.27, MS5 1.55, SC2 1.51, TDC2 1.18
- consensus units: agreed-by-2 1.49 (n=26), agreed-by-3 1.76 (n=23,
  firmed from 1.44 when the full W-019 pair set completed)

Answer to Q-010: yes - the contrast is metric-robust, human and
automatic, sorted and sorting-free. Standing caveat unchanged: within
one animal the coated/uncoated axis IS the anterior/posterior axis;
W5 (treatment_effect.md) showed the coating direction reverses across
animals while the pedestal direction does not. This result says the
measurement chain is not the explanation for the within-animal
contrast; it does not un-confound treatment from position.

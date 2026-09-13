---
id: R-004
type: result
status: current
title: UnitRefine is discriminative on recording-backed analyzers (54-68% neural)
created: 2026-09-12
actor: human
basis: recorded
reviewed: 2026-09-12
verdict: works
parent: P-05
source: [docs/notes/unitrefine_analyzer.md, notebooks/scratch_unitrefine_pilot.py]
---
What ran: full-feature analyzers (35/37 real) on two retained Fisk stems; both
classifiers driven with the sklearn-1.4 imputer patch.
Outcome: 88/129 and 147/272 neural with plausible SNR ordering, against 0.02%
on snippets.
Interpretation: the snippet failure was the input representation, as
hypothesised; the continuous arm can use UnitRefine (W-012 validates it).

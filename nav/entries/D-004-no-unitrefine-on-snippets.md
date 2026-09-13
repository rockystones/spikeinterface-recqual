---
id: D-004
type: decision
status: accepted
title: Do not use UnitRefine on snippet data; the physics gate is the curation layer
created: 2026-08-18
actor: agent
basis: recorded
decided_by: agent
pinned: true
summary: Seven required features need continuous traces; imputing them saturates the classifier at noise
evidence: [docs/notes/snippet_sorting.md, docs/notes/robustness.md]
source: [docs/notes/robustness.md]
---
Context: UnitRefine labels 99.98% of 65,051 snippet units noise; seven of its
features need continuous traces.
Options: threshold-shift the classifier; impute features; ban it on snippets.
Choice: ban on snippets; explicit SNR/count/shape gate instead. Scope-narrowed
by R-004: on recording-backed analyzers the models are usable.
Consequences: contradicts CLAUDE.md's stated default curation policy for the
snippet arm; ur_* columns in curation_labels are not to be used.

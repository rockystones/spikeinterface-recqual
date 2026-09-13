---
id: D-003
type: decision
status: accepted
title: Snippet-only cohorts are sorted per-electrode (ISO-SPLIT), as the correct method
created: 2026-08-03
actor: agent
basis: recorded
decided_by: agent
pinned: true
summary: At 400 um pitch a neuron appears on one electrode; per-electrode clustering is the correct method
evidence: [docs/notes/snippet_sorting.md]
source: [README.md, docs/session_plans/session04_rocky_resort.md]
---
Context: the standard pool needs continuous traces; much of the estate is
snippet-only NEV.
Options: skip snippet eras; pretend snippets feed sorters; per-electrode
clustering with an explicit physics gate.
Choice: per-electrode ISO-SPLIT on PCA features - at 400 um pitch a neuron
appears on one electrode, so this is the correct method there, not a fallback.
Consequences: two-regime pipeline; snippet results carry their own methods
suffixes and gate.

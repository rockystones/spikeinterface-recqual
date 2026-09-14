---
id: D-013
type: decision
status: accepted
title: Mean max peak-to-peak amplitude is a default sorted metric for every monkey
created: 2026-09-13
actor: agent
basis: recorded
decided_by: human
summary: "Legacy MATLAB metric: per active channel take the largest-P2P unit, average across channels; owner ruled it a cohort default"
resolves: []
informs: [A-001]
source: ["chat 2026-09-13 (owner instruction)", "matlab/ (legacy post-processing)"]
---
Context: the owner's legacy MATLAB layer reports 'mean max peak-to-peak
amplitude' - for each active channel the unit with the largest P2P
amplitude, averaged across channels (inactive channels as NaN or zero);
the modern figures never carried it.
Options: leave it legacy-only; add as a default metric.
Choice: owner ruled it a default for all monkeys, Rocky first (W-017).
Consequences: needs per-unit amplitudes per channel; exact definition
taken from the legacy MATLAB source, both NaN- and zero-fill variants
reported.

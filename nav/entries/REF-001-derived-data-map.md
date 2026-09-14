---
id: REF-001
type: ref
status: current
title: Map of the preserved sorting results and how to inspect them
created: 2026-09-13
actor: agent
basis: recorded
kind: data-map
path: docs/notes/data_inspection.md
summary: Layer-by-layer inventory (sorting-free, per-unit, spike trains, consensus, joins) with loaders and the figure-to-script-to-table trace
informs: [Q-008]
source: [docs/notes/data_inspection.md]
---
Written when the owner asked to dive into Rocky's data. Key grain facts: the
snippet-era methods keep per-unit metrics (spike membership re-derives from
NEVs); the 48-stem consensus subset keeps full spike trains as SI
numpy_folder; giant-event waveforms persist as npz shards. C1's previously
uncommitted figure code is now notebooks/scratch_consensus_figures.py.

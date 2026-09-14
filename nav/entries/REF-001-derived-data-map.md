---
id: REF-001
type: ref
status: current
title: Map of the preserved sorting results and how to inspect them
created: 2026-09-13
actor: agent
basis: recorded
updated: 2026-09-13
kind: data-map
path: docs/notes/data_inspection.md
summary: Layer-by-layer inventory (sorting-free, per-unit, spike trains, consensus, joins) with loaders and the figure-to-script-to-table trace
informs: [Q-008]
source: [docs/notes/data_inspection.md, matlab/rocky_reproduce_figures.m]
---
Written when the owner asked to dive into Rocky's data. Key grain facts: the
snippet-era methods keep per-unit metrics (spike membership re-derives from
NEVs); the 48-stem consensus subset keeps full spike trains as SI
numpy_folder; giant-event waveforms persist as npz shards. C1's previously
uncommitted figure code is now notebooks/scratch_consensus_figures.py.
MATLAB inspection layer added 2026-09-13: rocky_load_tables.m loads all
19 Rocky tables; rocky_reproduce_figures.m rebuilds the 27 derived-data
figures (verified against MATLAB R2025b); read_npy/read_npz_array read the
waveform shards, checked value-exact against NumPy.

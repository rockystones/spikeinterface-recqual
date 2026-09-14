---
id: REF-002
type: ref
status: current
title: Provenance store - full derivation chains for nine sessions across three subjects
created: 2026-09-13
actor: agent
basis: recorded
kind: data-store
path: data/derived/provenance
count: 9
summary: Per-spike assignments for all methods, waveforms, features, per-unit tables and modern-pool trains; MATLAB re-derivation matches at max-diff 0 for all nine
informs: [REF-001, Q-008]
source: [notebooks/scratch_provenance_dump.py, matlab/rocky_provenance.m, docs/notes/data_inspection.md]
---
Built at the owner's request to inspect and validate the path from raw
sorting results to the figure tables. Nine sessions kept for inspection:
five era-spanning Rocky (early/methods-subset/giants/end-of-life/I2),
two Nigel (healthy Anterior 2023-03-24, dying Posterior 2024-10-01) and
two Fisk (2023 Lateral SN1498, 2025 Medial3Min SN1504). Seeded
regeneration is deterministic and matches stored methods_long exactly on
the in-subset session (343/192/159/206/120 units per method);
matlab/rocky_provenance.m re-derives all metrics from the raw arrays with
max|diff| = 0 and 100% gate agreement for all nine (R-012 Rocky, R-013
Nigel/Fisk), and matches the stored free layer once the
|trough|-vs-max(|vmin|,vmax) amplitude split is respected (documented in
data_inspection.md). Also surfaced and resolved I-003 (the Rocky NEV
estate move).

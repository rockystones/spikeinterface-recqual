---
id: REF-002
type: ref
status: current
title: Provenance store - full derivation chains for five representative Rocky sessions
created: 2026-09-13
actor: agent
basis: recorded
kind: data-store
path: data/derived/provenance
count: 5
summary: Per-spike assignments for all methods, waveforms, features, per-unit tables and modern-pool trains; MATLAB re-derivation matches at max-diff 0
informs: [REF-001, Q-008]
source: [notebooks/scratch_provenance_dump.py, matlab/rocky_provenance.m, docs/notes/data_inspection.md]
---
Built at the owner's request to inspect and validate the path from raw
sorting results to the figure tables. Five era-spanning sessions (~359 MB,
kept for inspection): early/methods-subset/giants/end-of-life/I2. Seeded
regeneration is deterministic and matches stored methods_long exactly on
the in-subset session (343/192/159/206/120 units per method);
matlab/rocky_provenance.m re-derives all metrics from the raw arrays with
max|diff| = 0 and 100% gate agreement, and matches the stored free layer
once the |trough|-vs-max(|vmin|,vmax) amplitude split is respected (now
documented in data_inspection.md). Also surfaced and resolved I-003 (the
Rocky NEV estate move).

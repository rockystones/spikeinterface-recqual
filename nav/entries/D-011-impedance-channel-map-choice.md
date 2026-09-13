---
id: D-011
type: decision
status: proposed
title: Adopt the authored potentiostat channel map over the naive sweep-order map
created: 2026-08-24
owner: human
basis: recorded
evidence: [R-003, docs/notes/impedance_channel_map.md]
source: [docs/notes/impedance_channel_map.md, configs/probes/impedance_channel_map.csv]
---
Context: the two candidate maps agree on 0/96 channels; every per-electrode
impedance conclusion depends on the choice. Owner said "we will validate
together".
Options: authored (lab mapping sheets; four internal checks pass); naive
(sweep order; no provenance); either reversed.
Choice: pending the owner. Three empirical arbiters are null (R-003), so the
decision rests on documentary evidence alone - the authored map's provenance
against the naive map's nothing.
Consequences when accepted: unblocks W-004 (per-electrode joins) and firms the
Rocky edge-widening interpretation (R-007).

---
id: D-009
type: decision
status: accepted
title: Potentiostat open/short flags are measurement-chain diagnostics, not electrode states
created: 2026-09-12
actor: agent
basis: recorded
decided_by: agent
summary: Potentiostat opens sit at ephys percentile ~0.5 under every candidate map
evidence: [R-003]
source: [docs/notes/impedance_channel_map.md]
---
Context: impedance QC carries frac_open/frac_short; the map-validation plan
assumed an open electrode is a dead ephys channel.
Options: treat opens as electrode deaths; treat them as chain faults.
Choice: chain faults - opens sit at ephys percentile ~0.5 under every candidate
map (R-003), so they do not replicate through the recording chain.
Consequences: the open/short map-validation idea is retired; QC flags read as
rig health.

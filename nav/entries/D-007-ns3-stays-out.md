---
id: D-007
type: decision
status: accepted
title: "Fisk's .ns3 stays out of the pipeline"
created: 2026-09-12
actor: agent
basis: recorded
decided_by: agent
summary: A 300 Hz high-passed band-limited copy of the .ns6; one sampled file all-zero
evidence: [R-008]
source: [docs/notes/lfp_quality.md]
---
Context: 140 sessions of a second 2 kHz stream, suffix suggests LFP.
Options: ingest as LFP; ingest as a second spike-band stream; exclude.
Choice: exclude - it is a 300 Hz high-passed band-limited copy of the .ns6
(R-008), and one sampled file is all-zero.
Consequences: Fisk LFP derives from .ns6 alone; no ns3 code paths.

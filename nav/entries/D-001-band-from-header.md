---
id: D-001
type: decision
status: accepted
title: Read the band from the nsX extended header, never from the suffix
created: 2026-08-23
owner: agent
basis: recorded
evidence: [docs/notes/lfp_quality.md]
source: [CLAUDE.md]
---
Context: suffix conventions implied .ns5=broadband, .ns3=LFP.
Options: trust suffixes; read hi/lo_freq_corner (millihertz) per file.
Choice: header always; both suffix conventions were checked and both are wrong
on this corpus (498/626 continuous files are 250 Hz high-passed).
Consequences: LFP derivable only from Fisk .ns6; per-subject filter work
differs and must be checked before cross-animal comparisons.

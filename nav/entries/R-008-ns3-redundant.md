---
id: R-008
type: result
status: current
verdict: measured
title: Fisk .ns3 reproduces band-matched .ns6 noise at rho 0.94-0.996, x1.19 scale
created: 2026-09-12
owner: human
basis: recorded
parent: P-03
resolves: []
source: [docs/notes/lfp_quality.md, notebooks/scratch_fisk_ns3_check.py]
---
What ran: six sessions spanning 2023-2025; .ns6 band-passed to the .ns3's own
corners and decimated.
Outcome: rank agreement ~0.99, stable x1.19 filter-shape scale; one sampled
.ns3 all-zero while its .ns6 is fine.
Interpretation: the stream is a redundant copy; grounds D-007.

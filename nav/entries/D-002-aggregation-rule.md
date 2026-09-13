---
id: D-002
type: decision
status: accepted
title: Never pool numerator and denominator across sessions; pair within session
created: 2026-08-18
actor: agent
basis: recorded
decided_by: agent
pinned: true
summary: Pooled ratios mis-stated findings by 661x and 5.1x; one produced a confident wrong conclusion
evidence: [docs/notes/giant_events.md, docs/notes/sorter_operations.md]
source: [CLAUDE.md]
---
Context: session sizes span two orders of magnitude; pooled ratios are
statements about the largest sessions (measured 661x and 5.1x distortions, one
producing a confident wrong conclusion).
Options: pooled ratios; per-session ratio then median; mixed.
Choice: per-session then median; pair inside the session where a pair exists.
Consequences: every campaign since (treatment, rings, impedance) is built on
per-session medians and within-session pairing.

---
id: R-018
type: result
status: current
title: Gated ISO-SPLIT on snippets behaves like a member of the modern sorter pool
created: 2026-09-15
actor: agent
basis: recorded
parent: P-03
informs: [R-016, Q-008]
evidence: [I-005]
source: [notebooks/scratch_isosplit_vs_ms5.py, "data/derived/ns5/consensus/isosplit_vs_ms5.parquet"]
---
Direct unit-level comparison, lag-aligned, on the 7 provenance sessions
with kept MS5 trains. Gated ISO-SPLIT (the resort layer that feeds the
figures) vs MS5 on the same session's continuous ns5:

- Healthy sessions: 36-62% of gated iso units Hungarian-match an MS5
  unit at >=0.5 (Rocky 58-62%, Nigel Ant 58%, Fisk 36-39%); best-
  agreement p50 0.35-0.65; per-unit spike recall by the best MS5 unit
  p50 0.50-0.98, p90 0.97-1.00.
- Dead arrays agree on collapse from both sides (Nigel Post 2024-10:
  0 gated vs MS5 2; Rocky Post 2023-09: MS5 8, no correspondence).
- UNGATED iso drops to 20-34% matched (p50 agreement 0.08-0.32): the
  gate is what makes the snippet clusters sorter-like; the small
  sub-gate clusters have no MS5 counterpart.

Why it matters for Q-009/R-016: iso-gated matches MS5 at or ABOVE the
sorter-vs-sorter level (0.24-0.47 pairwise), while the human Plexon
sort matches every automatic method at <=7%. So the human-vs-automatic
gap is NOT caused by the snippet basis - a snippet-side automatic
method lands inside the modern family - it is the human partition
itself (its ~2-units-per-channel habit and acceptance of small units)
that stands apart. Fisk sits lower (36-39%) than Rocky/Nigel; its ns6
is true broadband where MS5's own filtering diverges most from the
NEV's spike band.

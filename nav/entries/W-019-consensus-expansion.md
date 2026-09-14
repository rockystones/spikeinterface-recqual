---
id: W-019
type: work
status: active
title: Expand the modern-sorter pool to Rocky same-day pairs and cohort breadth
created: 2026-09-14
actor: agent
basis: recorded
parent: P-03
hill: uphill
informs: [Q-009, Q-010]
source: [notebooks/scratch_ns5_consensus.py, "chat 2026-09-14 overnight"]
---
Owner request: the modern sorters ran on a small subset; broaden
coverage to answer (1) consensus vs human sorting and (2) coating
across metrics. The resort's stratification picked Anterior and
Posterior dates independently, leaving ONE same-day Rocky I1 pair in
the whole modern layer while 148 paired 2018+ dates sit online.

Running overnight 2026-09-14: scratch_ns5_consensus.py --paired-rocky
26 --per-array 32 - 52 Rocky I1 pair-stems first (26 dates evenly
spread), then Nigel/Fisk/Rocky-I2 breadth to 206 stems total, 4 sorters
each, agreement graph + numpy_folder trains kept per stem. Done looks
like: consensus tables spanning the pairs, ofs_match and
coating_by_metric rebuilt on the expanded coverage.

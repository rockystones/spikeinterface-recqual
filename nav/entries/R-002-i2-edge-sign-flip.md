---
id: R-002
type: result
status: current
verdict: measured
title: Rocky I2 (fresh) has border 26-38% below interior; I1 ran the opposite way
created: 2026-09-12
owner: human
basis: recorded
parent: P-03
source: [docs/notes/ring_geometry.md, notebooks/scratch_rocky_i2_events.py]
---
What ran: per-electrode events for 20 I2 sessions; ring/border/within-bank.
Outcome: all 16 within-bank cells negative, isotropy 4/4 on 6/8 array-metrics;
I1 in the same animal ran +16 to +55%.
Interpretation: the ephys edge sign is implant-level, not geometric and not
animal-level - the deconfound is now within-animal. Feeds Q-002.

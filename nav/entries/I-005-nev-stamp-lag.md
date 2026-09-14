---
id: I-005
type: issue
status: resolved
title: NEV stamps trail the continuous stream by a fixed lag; pooled recovery fractions are chance-saturated
created: 2026-09-14
actor: agent
basis: recorded
parent: P-03
informs: [Q-008, Q-009]
source: [notebooks/scratch_consensus_vs_ofs.py, docs/notes/multisorter_agreement.md]
---
Two related measurement facts surfaced while building the consensus-vs-
human comparison:

1. The NSP's online detector stamps NEV events a FIXED few ms after the
   same waveform appears in the continuous ns5 (measured +2.6 ms on
   Nigel_Anterior_2023-03-24 by re-thresholding one channel: 61.5% of
   crossings match NEV stamps at 0.4 ms once shifted, 3% unshifted).
   Any NEV-vs-continuous spike matching must estimate and remove this
   per-stem lag; scratch_consensus_vs_ofs.py does (top-unit pooled
   scan, lag recorded per shard).

2. ns5_sorters.parquet's frac_nev_recovered / frac_sorter_in_nev are
   POOLED 1 ms matches whose rates sit exactly at their own stored
   chance columns: median excess over chance is -0.004 across 920 runs,
   77% within 0.05. The columns were flagged at write time
   (match_is_pooled, chance_* alongside) but carry no per-unit
   information and must not be interpreted as recovery. The
   dispersion-proxy paragraph of multisorter_agreement.md that leans on
   their spread should be read with this in mind.

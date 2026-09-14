---
id: R-014
type: result
status: current
title: TDT maxsigM verified as the legacy mean-max-amplitude structure; maxsig field is a trap
created: 2026-09-14
actor: agent
basis: recorded
parent: P-03
informs: [W-017, D-013]
source: [notebooks/scratch_maxsig_tdt.py, "D:/Claude Code/Monkey Data/Legacy/L1MonkeyData/ephys/monkey_units_compiled.mat", "Oops tank 2015_06_12-1 probe 2026-09-14"]
---
The flagged "unverified candidate" is now decoded. In
monkey_units_compiled.mat, `unitsum.maxsigM` equals the mean over active
channels of the per-channel MAX over sorted units of the per-unit
amplitude `sig` (uV) - exact to 1e-12 for all 215 sessions that carry
`sig` (Chase.A 11, Oops.A 71, Oops.B 58, Picasso.A 40, Picasso.B 35;
Luigi.A stores only maxsigM). Structurally identical to D-013's NaN-fill
variant. Exported: cohort/mean_max_p2p_tdt.parquet, 241 sessions with
coating/arrayloc labels, definition="tdt_sig".

Two limits, both recorded in longitudinal_metrics.md:
- The FIELD `maxsig` is NOT max(sig) and NOT what maxsigM averages
  (Oops.A s0: mean(maxsig)=109.0 vs maxsigM=68.2), nor the tank's max
  single-snippet P2P. Never join eras through that field.
- The waveform-level definition of `sig` is locally unverifiable: the
  compiling sort_*.mat offline sorts (fnames like
  sort_Oops_baseline_Oops_2015_06_12-001.mat) exist on no local drive,
  and the in-tank sortcode {0,1} partition is a different sort - count
  anchoring against the Oops 2015-06-12 tank matched nothing. Chase/
  Luigi date handling: MMDDYY strings / days-post-implant only.

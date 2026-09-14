---
id: R-015
type: result
status: current
title: Exact mean-max-P2P computed for the whole cohort; both eras tabled as a default metric
created: 2026-09-14
actor: agent
basis: recorded
parent: P-03
resolves: [W-017]
informs: [D-013, R-014]
evidence: [I-004]
source: [notebooks/scratch_mean_max_p2p_pass.py, notebooks/scratch_mean_max_p2p_figs.py, notebooks/scratch_maxsig_tdt.py, docs/notes/longitudinal_metrics.md]
---
The legacy headline metric (D-013: per channel the max-P2P unit, plain
mean waveform, global range; per session the NaN-fill and zero-fill
means) is now a computed default for every monkey.

- **Blackrock, exact from the sorted NEVs**: 708 sessions
  (cohort/mean_max_p2p.parquet; per-channel audit grain in
  mmp2p_shards/). NaN-fill medians: Rocky I1 Ant 81.2 / Post 65.2, I2
  Ant 127.9 / Post 112.6; Nigel Ant 78.8 / Post 62.7; Fisk SN1498 92.3 /
  SN1504 109.3 uV. Cross-checked against all nine provenance stores at
  per-channel max|diff| = 0 (the one initial disagreement became I-004).
- **TDT era**: 241 sessions from monkey_units_compiled.mat via the
  verified maxsigM identity (R-014), definition="tdt_sig".
- Figures: cohort/mean_max_p2p.png (2x3, implant-resolved per the
  serial-resolution rule), rocky/16_mean_max_p2p.png (exact vs the
  disqualified approximation).

What the metric shows at a glance: the two fill variants disagree
exactly on collapsed arrays - the NaN-fill peak is 2018-12-06 Rocky
Posterior, ONE active channel holding a single 3.9 mV unit (NaN 3901 vs
zero 40.6 uV); Nigel Posterior's death plunge and Fisk's weak 2024
stretch (incl. a zero-unit 2024-05-31 session) are all visible.
Amplitude ordering across arrays is not survival ordering: dying arrays
can carry a HIGHER mean-max-P2P late (few surviving channels with big
units dominate the NaN-fill mean).

---
id: I-008
type: issue
status: resolved
title: Rebuilt resort shards renamed electrode_id to channel_id - units_long carried both columns with 76k NaNs for two days
created: 2026-09-23
actor: agent
basis: recorded
parent: P-03
depends_on: [D-015]
informs: [R-025]
source: [notebooks/scratch_rocky_resort.py, data/derived/rocky/units_long.parquet]
---
Found while auditing figures/matlab_repro/rocky on owner request. The
D-015 rebuild's process_combo writes the electrode column as
channel_id; the 252 untouched pre-rebuild shards call it
electrode_id. The plain concat in the resort aggregation produced a
units_long with BOTH columns - channel_id NaN on 76,418 old-shard
rows, electrode_id NaN on the 24,193 rebuilt rows.

Damage window 2026-09-21 -> 09-23: consumers that key on channel_id
silently dropped the 252 old combos' rows from channel-level
quantities. Concretely wrong in that window: two_array_metrics'
yield_pct and mean_max_amp for the ofs and resort_gated layers (and
the 17-19 figure sets built from them), the spatial/impedance-join
figures rerun on 09-23 morning (impedance-vs-yield read rho=-0.034
on a third of its electrode-sessions), and the first 09-23 MATLAB
repro pass. NOT affected: everything keyed by session or amplitude
only - variance results (mmp2p-based, rho 0.236 stands), coating
ratios (R-017 exact), longitudinal session trends (posterior yield
rho -0.644 stands), events/giants (own pipeline), headstage pairs.

Fix (same day): the resort aggregation now coalesces
electrode_id -> channel_id (fillna + drop); units_long rebuilt with 0
NaN ids; all consumers rerun (two_array_metrics, longitudinal,
curation, spatial, coating, outlier index, MATLAB repro).
Post-fix checks: posterior yield rho -0.644 (note: -0.64),
impedance-vs-yield back to rho +0.013 over the full 14,964
electrode-sessions, resort_gated yield medians a smooth 47.9 -> 6.2%
across 2017-2023.

Guard that caught it: scratch_rocky_spatial's
`assert missing == 0, "CMP join failed"` - the one consumer that
refuses to run with unjoined electrodes. The concat now normalizes,
and the assert stays.

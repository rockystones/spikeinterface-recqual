---
id: REF-003
type: ref
status: current
title: Waveform catalog - 13,321 unit shapes, 10 sorting chains, 6 monkeys
created: 2026-09-17
actor: agent
basis: recorded
kind: data-store
path: data/derived/rocky/waveform_catalog.parquet
count: 13321
summary: Shape-clustered unit means (k=16, ids frozen) with owner merge rulings as the archetype column; giants/extremes panels; TDT scaling verified
informs: [REF-002, R-013]
source: [notebooks/scratch_waveform_catalog.py, "figures/rocky/21,22,22b,23"]
---
Built across 2026-09-16/17 with the owner. One row per unit: subject,
store, method (ofs / isosplit_full / gmm_bic / kmeans_sil / hdbscan /
4 modern sorters / tdt_sortcode), cluster, archetype, snr, pass_gate,
edge_max, centroid_dist. Cluster ids are FROZEN (k-means fit on the
unchanged reference chains, seed 0; new layers assigned, never refit).

Owner rulings encoded: c0+c10 and c1+c13 merged (same archetype split
by snippet-vs-modern alignment), c10+c12 rejected for now. Validation
of the construction: 89% of the 1,840 TDT units land in exactly those
two merged archetypes from a different acquisition system and decade.

Findings that live here:
- The "pre-trough-max" class (edge-max clusters) is selection-shaped
  near-threshold residue, not units: no cross-channel co-firing
  (0-1.1% vs chance), unimodal threshold-hugging troughs, 0-4% gated;
  some real-neuron strays mixed in (ch2/ch69 have gated 56-66 uV
  isosplit twins). ~90% confidence not-isolated-neurons.
- Amplitude-definition verdict (figure 20): the owner's global-range
  P2P equals trough->post-peak within 1% on 85% of 618 Plexon units;
  worst divergence among real-sized (>40 uV) units is 1.12x. The
  divergent tail is the selection-noise class the gate rejects.
- TDT scaling verified, no gain misconfiguration: unit medians match
  the compiled maxsigM anchor; all 46 store-blocks have 16-63 uV
  floors; the mV "spike-like" extremes are per-event tails in 2016
  task blocks, Picasso's 15,998 uV ceiling = the amplifier rail.
- Flags for manual examination: Oops_2016_01_07/eNe2 floor p50 = 1 uV
  (array B near-flat; the early-2016 eNe1==eNe2 MDA-bug era); residual
  amplitude-outlier candidates Rocky_Anterior_10-31-2017 (568 uV
  resort), Rocky_Posterior_01-31-2020 (350), and the late-life
  2023-01-13 / 2023-08-11 Posterior subset-method excursions.
- Chase has no local tanks; its waveforms arrive with W-001.

---
id: R-013
type: result
status: current
title: Nigel and Fisk derivation chains validate to the Rocky standard
created: 2026-09-14
actor: agent
basis: recorded
parent: P-03
resolves: [W-018]
informs: [REF-002, R-012]
source: [notebooks/scratch_provenance_dump.py, matlab/rocky_provenance.m, "scratchpad prov_validate_3.log 2026-09-14"]
---
All four non-Rocky provenance stores now MATLAB-validated exactly, same
standard as R-012: every unit metric max|diff| = 0 (snr at float32
epsilon), 100% gate agreement, free layer identical to the official
events_electrode tables.

- Nigel_Anterior_2023-03-24 (healthy): 193 units, 95 gated.
- Nigel_Posterior_2024-10-01 (dying): 62,435 events still produce 97
  isosplit clusters, but **0 pass the gate** - the death signature is
  gated-out clusters, not silence; modern pool agrees (MS5 keeps 2
  units / 193 spikes).
- Fisk 20230605-132052-Lateral (SN1498): only 41/96 electrodes reach 50
  events in the 3-min baseline; 53 units, 39 gated.
- Fisk 20250507-095730-Medial3Min (SN1504): 256,890 events on 94
  electrodes; 165 units, 139 gated - the 2025 Medial array is far
  livelier than the 2023 Lateral one.

One cosmetic MATLAB warning (legend with zero gated units on the Nigel
Posterior P1 figure); figures written under
figures/matlab_repro/provenance/<stem>/.

Refined same day (I-004): the initial Nigel Anterior dump had used a
test-vintage sorted copy and the Fisk dumps the unsorted Recordings
NEVs. All three stores were redumped from the canonical sorted files
and revalidated - every number above is unchanged (the isosplit layer
is label-independent and the event sets are identical); the Fisk
stores additionally gained their true Plexon ofs layer (Lateral 55,
Medial3Min 174 ofs units in units_full).

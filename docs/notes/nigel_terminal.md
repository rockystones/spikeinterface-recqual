# Nigel terminal session (2025-09-25)

Three recordings from the last day of Nigel's implant, TNP-family
(Anterior, SN1496) array only — the Ctrl-family array had failed
(last recorded late-2024). `notebooks/scratch_nigel_terminal.py`;
outputs in `data/derived/nigel_terminal/`,
`figures/nigel/terminal_overview.png`; nav R-026.

## The data

`Monkey Data/Nigel/Terminal recordings/`: three NEVs
(datafile0075/0080/0090; only 0075 human-sorted, `-01`) and three
NPMK `openNSx` v7.3 `.mat` NS5 exports (74/57/82 s, 254 channels of
which 96 are the array, int16, gain 0.25 µV/count). **The terminal
export is broadband — extended-header high-pass corner 0.3 Hz —
unlike the regular Nigel `.ns5` corpus (250 Hz)**; the pipeline's
300 Hz filter normalizes this before sorting. `load_mat_recording()`
is the reader (h5py; band and gain from the embedded header per the
CLAUDE.md rule) and caches SI binary folders under
`nigel_terminal/rec_*`.

## What each layer says

- **Sorting-free**: noise floor 8.0 µV — normal for this animal.
  The array is quiet, not noisy.
- **Manual sort (Plexon)**: 48 units on 34 active channels,
  mean-max P2P 61.7 µV (exact mmp2p pass). Under the physics gate,
  **6 of 47 scoreable units pass**; 34 fail SNR ≥ 4, the rest spike
  count or shape (`manual_gate_audit.parquet`). The cohort-layer row
  reads 0 for the same file (its gate differs); the per-unit audit
  is the auditable number.
- **Modern sorters** (MS5 scheme 2, TDC2, SC2, KS4 dminx=400 in
  ks4:cu128): counts are pure method artifacts at this signal
  level — MS5 10–14, KS4 42–47, TDC2 91–141, SC2 143–218 per file,
  and **0–15 units match between any pair** (0.5 agreement,
  0.4 ms); manual-vs-KS4 matches 0 of 47-vs-47
  (`terminal_agreement.parquet`). Compare the healthy-era structure
  (R-016), where consensus counts tracked the human sort at
  ρ ≈ +0.6.

## The terminal verdict

The defensible statement: at explant the TNP array still carried
**~6 isolatable units** (and hand-sortable threshold activity on 34
of 96 channels) over a normal noise floor, while the Ctrl-family
array had already failed outright. Quote gated counts or
sorting-free metrics for this day — raw sorter unit counts from any
single method are meaningless here, and the near-zero cross-method
agreement is the evidence.

## Related

[[longitudinal_metrics]], [[consensus_vs_human]], [[data_lineage]],
[[surface_conditions]].

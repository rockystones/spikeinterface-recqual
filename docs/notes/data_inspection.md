# Inspecting the preserved sorting results (Rocky and the cohort)

What survives, at what grain, in what format, and how to open it. Everything
below `data/derived/` is Parquet, NPY/NPZ, or JSON — no pickle (CLAUDE.md
MATLAB rule). Load tables with `pd.read_parquet(path)`; from MATLAB use
`parquetread` and npy-matlab's `readNPY`.

## Layer 0 — raw inputs (not copied, re-derivable from)

Rocky NEVs/ns5 under `D:\Claude Code\Rocky`, `C:\MyData\Monkeydata\Rocky`,
`Monkey Data\Rocky New` (I2). `rocky/session_index.parquet` maps I1
sessions→files; `cohort_index.parquet` covers the estate. Every derived store
names its inputs in the generating script's header.

## Layer 1 — sorting-free (threshold crossings, no unit labels)

| store | grain | rows |
|---|---|---|
| `rocky/events_electrode.parquet` (+ `event_shards/` per session) | electrode × session, 52 cols: noise MAD, crossing rates, amplitude percentiles, artifact/impulse/rail counts, giant taxonomy, CMP col/row | 31,654 (I1 2017–2023) |
| `rocky_i2/events_electrode.parquet` | same, I2 2025 | 1,920 |
| `rocky/giant_events.parquet`, `giant_sites.parquet` | per giant event / per recurring site | — |
| `rocky/giant_wf_shards/*.npz` | **raw waveforms** of giant events (`wf` array + `gid` ids), per session | 332 files |
| `rocky_ns5/ns5_free.parquet` (+ `free/`) | session-level re-detection at fixed k from continuous .ns5 | 431 Rocky rows |

## Layer 2 — per-unit sorting results

**Snippet-era methods** (per-electrode clustering of NEV snippets):

- `rocky/units_long.parquet` — one row per unit, **`ofs`** (Plexon Offline
  Sorter reference, 44,211 units) and **`resort`** (our ISO-SPLIT, 56,400
  units): n_spikes, rate, SNR, trough/peak µV, widths, ISI violations,
  presence, `pass_gate` + `reject_reason`.
- `rocky/methods_long.parquet` (+ `method_shards/`) — the five-method
  comparison (isosplit, gmm_bic, kmeans_sil, hdbscan, ofs), 65,051 units ×
  58 cols.
- `rocky/curation_labels.parquet` — the same units with the full SI quality-
  metric set and the (unusable, kept for the record) `ur_*` labels.
- `rocky/method_agreement.parquet`, `method_jaccard.parquet` — cross-method
  matching.

**Grain caveat:** these tables are *per-unit metrics*, not per-spike
assignments. Spike-level membership for the snippet sorts was not persisted;
it re-derives deterministically from the NEVs via
`scratch_rocky_methods.py` / `scratch_rocky_resort.py`.

**Modern pool** (MS5, KS4, SC2, TDC2 on continuous data):

- `ns5/ns5_sorters.parquet` — 238 stems × 4 sorters: unit counts, runtimes,
  NEV-recovery fractions (summaries only; scratch purged).
- `ns5/consensus/sortings/<stem>/<sorter>/` — **full spike trains** for the
  48-stem era-spanning subset (12 Rocky I1, 12 I2), SI `numpy_folder`:
  `spikes.npy` is a structured array `(sample_index, unit_index,
  segment_index)` at 30 kHz. Load:

  ```python
  import spikeinterface.core as sc
  s = sc.load("data/derived/ns5/consensus/sortings/<stem>/<sorter>")
  s.get_unit_spike_train(unit_id)          # sample indices
  ```

  (MATLAB: `spikes.npy` is structured — npy-matlab cannot read it directly;
  use the Parquet tables, or ask for a split-into-plain-npy export.)

## Layer 3 — consensus and joins

`ns5/consensus/consensus_pairs / consensus_ladder / consensus_per_stem
.parquet` (pairwise Hungarian match fractions; units at ≥k sorters; per-stem
means) with per-stem `shards/`. Impedance: `rocky/impedance_long_full.parquet`
(52 dates, per sweep, both candidate channel maps as columns),
`impedance_bench.parquet`, QC and arbiter tables. Geometry campaigns:
`data/derived/ring/*`, `data/derived/cohort/*`, `data/derived/surface/*`.

## Figure → script → table

Every figure in `figures/` is produced by a committed `notebooks/scratch_*.py`
that reads only these stores (or the raw estate) — the script header names
its inputs and outputs. The Rocky-relevant map:

| figures | script | main tables |
|---|---|---|
| `ring/G1–G7` | `scratch_ring_geometry.py` | rocky/fisk events_electrode, factory CD dumps, `ring/*` |
| `consensus/C1` | `scratch_consensus_figures.py` | `ns5/consensus/*` |
| `treatment/W1–W5` | `scratch_treatment_longitudinal.py` | `cohort/*`, legacy sorts |
| `deepdive/*` | `scratch_rocky_deepdive.py` | events_electrode, methods_long |
| giants `X*` | `scratch_giants_compare.py` | giant_events, giant_wf_shards |
| ring stats (I2) | `scratch_rocky_i2_events.py` | rocky_i2/* |

`figure_coverage.md` tracks the wider figure inventory. To trace any number
in a note: the note names its script; the script's banner output shows the
intermediate tables; the tables are openable directly.

## Related

[[multisorter_agreement]], [[snippet_sorting]], [[giant_events]],
[[impedance_sources]]; nav `REF-001` points here.

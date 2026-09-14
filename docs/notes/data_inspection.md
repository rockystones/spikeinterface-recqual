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

## The provenance store: full chains for five representative sessions

`data/derived/provenance/<stem>/` (see `scratch_provenance_dump.py`)
materializes every intermediate step for five era-spanning Rocky sessions —
2018-02-22 Anterior (early, consensus), 2018-03-22 Anterior (in the
60-session methods subset), 2018-04-12 Posterior (giants), 2023-09-29
Posterior (end-of-life, consensus), 2025-05-02 Anterior (I2, consensus):
raw snippets (`waveforms.npy` + row-aligned `events.parquet` with the
full-data ISO-SPLIT label and the Plexon unit), the seeded subsample each
of the five methods clustered (`subsample.parquet`: PCA features + one
label column per method), per-unit tables rebuilt with the same functions,
the re-derived free layer, the official rows copied alongside, and — for
consensus stems — the modern pool's spike trains as plain int64 arrays
plus templates and peak-channel sample waveforms from the ns5.

**Validation status.** Regeneration is deterministic (identical counts on
re-run) and, on the methods-subset session, matches the stored
`methods_long` exactly (343/192/159/206/120 units per method).
`matlab/rocky_provenance.m` re-derives every metric in MATLAB from the raw
arrays and compares: unit metrics max|Δ| = 0 (SNR at float32 epsilon),
gate decisions 100%, free layer = stored `events_electrode` to 1e-05.

**One definitional split it surfaced:** the free-layer `amp_*` percentiles
use **|trough| (= |vmin|)** — "comparable with the sorted tables" — while
`max(|vmin|, vmax)` is the giant/artifact amplitude. Both are columns in
`events.parquet`; conflating them shifts amp_p50 by up to ~8 µV.

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
| MATLAB reproductions of all of the above | `matlab/rocky_reproduce_figures.m` (+ `rocky_load_tables.m`, `read_npy.m`, `read_npz_array.m`) | same Parquet/NPZ stores; writes `figures/matlab_repro/rocky/` (untracked) |

`figure_coverage.md` tracks the wider figure inventory. To trace any number
in a note: the note names its script; the script's banner output shows the
intermediate tables; the tables are openable directly.

## Related

[[multisorter_agreement]], [[snippet_sorting]], [[giant_events]],
[[impedance_sources]]; nav `REF-001` points here.

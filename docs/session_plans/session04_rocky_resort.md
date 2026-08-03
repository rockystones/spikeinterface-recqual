# Session 04  Rocky snippet re-sort, anterior vs posterior longitudinal

## Plan

Two jobs. First, fold in the archived project from the retired Enterprise/Pro accounts. Second, re-sort a large snippet-only Utah cohort and compare anterior against posterior array quality across the implant lifetime.

**Archive merge.** `CLAUDE.md` is byte-identical to the repo; `pyproject.toml` in the archive is the pre-fix state that `4b0783b` already corrected. Nothing to merge back on either. Seven genuinely new files move into place: `docs/roadmap.md`, `docs/project_instructions.md`, four literature reports into `docs/reports/`, and four legacy MATLAB files into `matlab/`.

**Re-sort.** `D:\Claude Code\Rocky` holds 886 in-scope `.nev` (2017-09-21 → 2023-10-06) and **zero `.ns5`**. Every sorter in CLAUDE.md's pool needs continuous traces and is unusable. At 400 µm Utah pitch each electrode is independent, so per-electrode snippet clustering is the correct method rather than a fallback. Approach: pre-trigger baseline MAD for the noise floor, trough re-alignment, PCA, ISO-SPLIT (`isosplit6`), then an explicit noise-rejection gate (SNR ≥ 4, ≥ 50 spikes, physiological peak-to-trough, trough on alignment). Plexon OFS labels are scored under the identical gate for a head-to-head. Scope per user: 2017–2023 only, ignore 2025; SN 1025-001501 = Anterior.

Deliverables: `notebooks/scratch_rocky_{inventory,resort,impedance,longitudinal}.py`; `data/derived/rocky/{session_index,units_long,impedance_long,session_summary}.parquet`; `figures/rocky/05..09`; notes `snippet_sorting.md`, `impedance_parsing.md`.

## Outcome

_Filled in at session end._

## SI / PI functions introduced

- `neo.rawio.BlackrockRawIO.get_spike_raw_waveforms` / `get_spike_timestamps` / `rescale_spike_timestamp` — snippet access; see [snippet_sorting.md](../notes/snippet_sorting.md)
- `isosplit6.isosplit6` — MountainSort5's ISO-SPLIT clustering, used standalone on PCA features since no SI sorter accepts snippets
- `sklearn.decomposition.PCA`, `scipy.stats.spearmanr`, `pandas.merge_asof` — not SI, no note required

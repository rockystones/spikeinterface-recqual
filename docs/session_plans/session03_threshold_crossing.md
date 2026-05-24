# Session 03  Threshold-crossing baseline (Layer 1 metric)

## Plan

First sorter-free metric on the pipeline. Per-channel noise floor (MAD + SD), threshold-crossing rate via local-minimum peak detection at `k ∈ {3, 4, 5}` × MAD with a 1.0 ms refractory, per-peak amplitude summary, and peak SNR. Cross-validated against session 2's curated per-electrode unit counts via Pearson r + Spearman rho (Spearman is the honest pass/fail — the relation is monotonic but probably non-linear).

Pipeline applied to seg[1] (180.01 s) of the Nigel 2023-03-17 baseline. seg[0] (2.36 s) dropped per [segment_handling.md](../notes/segment_handling.md). 300 Hz Butterworth order-3 highpass; **no CMR** at Layer 1 — characterize raw noise floor first so any future CMR can be measured as a separate Δ-MAD (see [spike_band_filter.md](../notes/spike_band_filter.md)). Scratch-first; no promotion to `src/`, no Tier 1 tests this session per [testing_policy.md](../notes/testing_policy.md).

Deliverables:
- `notebooks/scratch_threshold_crossing_nigel_2023-03-17.py`
- `data/derived/nigel_2023-03-17/threshold_crossings.parquet` (long, 288 rows)
- `figures/validation/04_xc_rate_vs_curated_units.png` (3-panel scatter, one per k)
- `docs/notes/threshold_crossing.md`, `docs/notes/spike_band_filter.md`

Reuse: session 1's loader + probe-attach pattern; session 2's cached SortingAnalyzer at `data/derived/nigel_2023-03-17/sorting_analyzer_curated.zarr` and `get_template_extremum_channel` for the curated peak-electrode assignment.

## Outcome

End-to-end run cleanly on seg[1] in **52.8 s**. Three `detect_peaks` passes dominate (~46 s combined); all other steps under 3 s.

Noise floor across the 96-channel array:
- `mad_uv`  median 12.8 (IQR [12.0, 13.6])   range [10.4, 15.6]
- `sd_uv`   median 13.8 (IQR [12.7, 15.3])   range [11.2, 27.8]
- `sd_over_mad` median 1.07, max 1.84   **no channel above the 2.5 heavy-tail flag**

Peak rates per k:
- k=3   51.6 / 76.1 / 167.1 Hz   (min / median / max)
- k=4   14.7 / 31.3 / 118.0 Hz
- k=5    3.7 / 13.1 /  84.5 Hz

**Tier 2 invariant**: 96 / 96 channels satisfy `n_peaks(k=3) ≥ n_peaks(k=4) ≥ n_peaks(k=5)`.

**Cross-validation vs session-2 curated** (across 96 electrodes, n=288 rows in parquet):
- k=3   Pearson r = +0.484   Spearman ρ = +0.423
- k=4   Pearson r = +0.509   Spearman ρ = +0.372
- k=5   Pearson r = +0.521   Spearman ρ = +0.377

All ρ positive and non-zero → the sorter-free metric tracks per-electrode unit density at a moderate but useful level. Magnitudes are bounded above by the fact that high-rate single units produce many crossings on their home electrode but contribute only `+1` to the unit-count axis (rate-vs-count is monotonic but compressive).

Per-step wall-clock anchor for longitudinal budgeting: **~0.55 s / channel / 180 s segment** end-to-end on the existing `.venv` (sequential, no parallelism). detect_peaks scales linearly in n-channels at fixed segment length; the noise-levels call subsamples 20 chunks regardless of channel count.

Gotcha caught at execution time: **`pyarrow` was not in the bootstrap-time `.venv`** (it is listed in the still-uncommitted pyproject expansion but `uv sync` is broken — see the spawned-task chip). Resolved with a one-shot `uv pip install --python .venv\Scripts\python.exe pyarrow`. Logged here so the spawned pyproject-fix task can confirm pyarrow ends up in the committed dependency set.

SI / PI functions introduced this session (per CLAUDE.md SI literacy practice):

- `spikeinterface.preprocessing.highpass_filter` — see [spike_band_filter.md](../notes/spike_band_filter.md)
- `spikeinterface.core.get_noise_levels` — see [threshold_crossing.md](../notes/threshold_crossing.md)
- `spikeinterface.sortingcomponents.peak_detection.detect_peaks` — see [threshold_crossing.md](../notes/threshold_crossing.md)
- `scipy.stats.pearsonr`, `scipy.stats.spearmanr` — used for the cross-validation; not SI, no note needed.

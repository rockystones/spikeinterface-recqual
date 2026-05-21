# SortingAnalyzer

Replaces the deprecated `WaveformExtractor`. Pairs one `BaseRecording` with one `BaseSorting` and hangs computed quantities (random spikes, waveforms, templates, quality metrics, …) off the pair as named "extensions". The persisted form is a folder (binary or zarr) that can be reloaded with all extensions intact.

## Create / load

```python
from spikeinterface.core import create_sorting_analyzer, load_sorting_analyzer

sa = create_sorting_analyzer(
    sorting, recording,
    format="zarr",                # or "binary_folder" or "memory"
    folder="data/derived/.../sorting_analyzer_curated.zarr",
    sparse=False,                 # dense across all channels; see "Sparsity" below
    return_scaled=True,           # all extensions see uV-scaled traces
    overwrite=False,
)

sa = load_sorting_analyzer("data/derived/.../sorting_analyzer_curated.zarr")
```

`return_scaled=True` is the global gain-scaling switch — set it once at construction so different extensions don't disagree (e.g. an SNR computed against scaled traces vs an amplitude against raw counts).

## Extensions

Computed as a dependency chain. Templates depend on `random_spikes` (or on `waveforms`, which itself depends on `random_spikes`).

```python
sa.compute("random_spikes", method="uniform", max_spikes_per_unit=500, seed=0)
sa.compute("templates", operators=["average"], ms_before=1.0, ms_after=2.0)
```

- Persisted to the analyzer folder on `save=True` (default). Reload via `load_sorting_analyzer` carries them automatically.
- Check with `sa.has_extension("templates")`; access data with `sa.get_extension("templates").get_data(operator="average")` → numpy array `(n_units, n_samples, n_channels)`.

## Sparsity

`sparse=True` (default) computes a per-unit channel mask from a quick template estimate, then propagates it: waveforms and templates only store channels near each unit's peak. **For this project we want `sparse=False`** when the spatial template across every electrode is the point — Figure 3 in session 2 needs all 96 channels per unit to overlay on the Utah grid.

## The "waveforms vs accumulator" gotcha

`sa.compute("templates")` has two code paths:

1. **If the `waveforms` extension is present**, templates are averaged from the cached waveform stack. Memory cost is full: `(n_random_spikes × n_samples × n_channels × dtype)` lives in a single shared buffer.
2. **If `waveforms` is absent**, templates fall through to `spikeinterface.core.template_tools.estimate_templates_with_accumulator`, which streams the recording once and accumulates running means per unit. Memory cost is `(n_units × n_samples × n_channels)` — orders of magnitude smaller.

On Windows, path 1 fails for our parameter range. 217 units × 500 spikes × 96 channels × 90 samples × float32 ≈ **3.75 GB** in a single `multiprocessing.shared_memory.SharedMemory` allocation, which trips `OSError [WinError 1450] Insufficient system resources`. Session 2 settled on path 2: **skip `sa.compute("waveforms", ...)` when only templates are needed**. 6.1 s for 217 units on a 180 s segment; cached zarr is 6.8 MB.

Path 1 is still required if downstream needs individual waveforms (PCA, amplitude scatter, per-spike features). When that day comes, switch to `format="binary_folder"` — the waveforms extension then writes via `numpy.memmap` instead of shared memory, sidestepping the Windows cap.

## Alternative considered

`WaveformExtractor` (older SI API). Excluded: deprecated, removed in 0.102.x. CLAUDE.md hard rule: "Use `SortingAnalyzer`, not `WaveformExtractor`. Any code referencing `WaveformExtractor` is outdated and must be ported."

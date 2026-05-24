# Threshold crossing (Layer 1 metric)

A sorter-free per-channel quality metric: **rate of local minima below −k·MAD within a 1.0 ms refractory window**, computed independently per channel. The two SI functions doing the work are `get_noise_levels` and `detect_peaks(method='by_channel')`.

## Metric contract

For each channel and each threshold factor `k`:
- Take the 300 Hz highpass-filtered seg[1] (see [spike_band_filter.md](spike_band_filter.md)).
- Estimate `mad` per channel using `get_noise_levels(rec, method='mad')`.
- Detect local minima in the negative trace satisfying `trace < -k * mad`, with no larger negative peak within `±1.0 ms` of the candidate (the "refractory" / `exclude_sweep_ms`).
- Report `n_peaks`, `rate_hz = n_peaks / dur_s`, `peak_amp_{median,p10,p90}_uv`, and `peak_snr = median(|amp|) / mad_uv`.

Refractory rationale: 1.0 ms aligns with the biological absolute refractory; suppresses noise jitter near threshold within one negative phase of an extracellular spike; covers rare two-negative-peak W-waveforms. Trade-off: very fast doublets with ISIs < 1 ms are undercounted (biologically rare). Reference: Gold et al. 2006 (J Neurophysiol 95:3113) for the canonical triphasic EAP shape that justifies the refractory tuning.

## `get_noise_levels(recording, return_scaled=True, method='mad'|'std', force_recompute=False, ...)`

Returns `np.ndarray (n_channels,)`. Samples ~20 random chunks of the recording and computes per-channel MAD (default) or STD across chunks. **The estimate is non-deterministic** — random-chunk selection has no fixed seed by default. For a stable baseline, results within a single run are reproducible because of the recording-property cache.

**Cache gotcha.** Results are cached as a property on the recording object across calls. Empirically (SI 0.102.3) the cache may not robustly key on `method` and `return_scaled` together. Pass `force_recompute=True` defensively on every call when you need MAD AND SD (or scaled AND raw) from the same recording, so the second call doesn't return the first's cached values. Cost is one extra noise scan (~1 s per call on a 180 s × 96 ch recording).

## `detect_peaks(recording, method='locally_exclusive', ...)`

Returns a numpy structured array; fields include `sample_index`, `channel_index`, `amplitude`, `segment_index`. **Default method is `locally_exclusive`** — must pass `method='by_channel'` explicitly for the per-channel independent detector this metric uses. The `by_channel` engine accepts `peak_sign`, `detect_threshold`, `exclude_sweep_ms`, `noise_levels`.

**Units gotcha.** Internally, `by_channel` compares the recording's RAW traces against `noise_levels * detect_threshold`. The `noise_levels` you hand it must therefore be in raw trace units (`return_scaled=False`). For reporting we want µV — compute MAD twice:

```python
mad_raw = get_noise_levels(rec, method='mad', return_scaled=False, force_recompute=True)  # for detect_peaks
mad_uv  = get_noise_levels(rec, method='mad', return_scaled=True,  force_recompute=True)  # for reporting
```

The returned per-peak `amplitude` is in raw trace units too; multiply by `gain_to_uV` (read from the recording, never hardcoded — CLAUDE.md rule) to convert.

## Alternative considered

Computing peak detection by hand on `rec.get_traces()` slices with `scipy.signal.find_peaks`. Equivalent algorithmically, but loses SI's chunked/streamed execution (the 180 s × 96 ch × 3 thresholds run finished in 46 s on the existing .venv) and forces us to manage threshold/refractory/segment plumbing manually. The SI helper also returns a uniform structured array that joins cleanly with the parquet output schema.

## Session-3 numbers

On Nigel 2023-03-17 baseline seg[1] (180.01 s, 96 ch), 300 Hz HP, no CMR:

- MAD: median 12.8 µV, IQR [12.0, 13.6], range [10.4, 15.6]
- `sd_over_mad`: median 1.07, max 1.84 — all channels well below the 2.5 heavy-tail flag
- Rate at k=4: median 31.3 Hz, max 118.0 Hz
- Spearman ρ vs curated unit count (positive control): 0.42 / 0.37 / 0.38 for k=3/4/5 — confirms the metric tracks unit density at the per-electrode level

# Spike-band filter

Layer 1 of the pipeline applies a 300 Hz highpass Butterworth filter (order 3) before any noise estimation or peak detection. Common-average / common-median referencing (CMR) is **deliberately not** applied at Layer 1.

## The call

```python
from spikeinterface.preprocessing import highpass_filter
rec_filt = highpass_filter(rec_seg, freq_min=300.0, filter_order=3)
```

Lazy: returns a `BaseRecording` whose `get_traces` filters on demand. The cost shows up at the next read, not at construction.

## Why 300 Hz HP, order 3

- 300 Hz is the conventional spike-band lower edge (below it: LFP, slow drift, motion artifact; above it: spike waveforms with most energy 300–3000 Hz).
- Butterworth: monotonically flat passband, no ripple. SI's default `ftype='butter'`.
- Order 3 is conservative — modest roll-off (~18 dB/octave), low filter-induced ringing, preserves spike shape. SI's default `filter_order=5` is more aggressive than this project needs.
- `filter_mode='sos'` (SI default): cascaded second-order sections, numerically stable.
- `direction='forward-backward'` (SI default): zero-phase filtering via `sosfiltfilt`. **Doubles the effective filter order** (3 → 6) but preserves temporal alignment, which matters for spike sorting and template estimation downstream.

No upper edge (no bandpass) at Layer 1 — `highpass_filter` rather than `bandpass_filter`. Downstream metric layers may add an upper edge if specific narrowband artifacts emerge.

## Why no CMR at Layer 1

Layer 1's job is to characterize the **raw noise floor** as the array sees it. CMR removes a per-sample shared signal across channels — useful for sorters that assume independent channel noise, but it changes the noise floor itself. Folding CMR into the baseline means we can never measure "what did CMR buy us?".

The plan is to revisit CMR at Layer 2 once sorter input requirements are characterized, and to report it as a **Δ-MAD effect**: MAD per channel before vs after CMR, plus the resulting Δ in threshold-crossing rate. That decomposition only works if Layer 1 measures the un-CMR'd noise floor.

If a recording has obvious mains contamination (50/60 Hz) that drives MAD into double digits where it shouldn't be, the per-channel MAD distribution at Layer 1 will catch it (uniformly inflated MAD across the array, often with one channel an extreme outlier). If found, flag in the session_plan Outcome rather than retrofitting CMR into Layer 1.

## Alternative considered

`bandpass_filter(freq_min=300, freq_max=6000)` instead of HP. Adds an upper edge typical of "spike-band" definitions. Excluded because nothing in the current pipeline needs the upper rolloff and the cost of a second filter stage is non-zero. If a future metric (e.g., gamma-band coupling) needs a low-pass before some computation, it gets its own filter object, not a piggyback on the spike-band preprocessor.

## Session-3 numbers

On Nigel 2023-03-17 baseline seg[1] after this filter:
- MAD median 12.8 µV, max 15.6 µV — tight noise floor across the 96-channel array
- `sd_over_mad` median 1.07, max 1.84 — no channel above the 2.5 heavy-tail flag → no mains-contamination evidence on this session

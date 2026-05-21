# Segment handling

## Policy

Drop any segment shorter than 5 seconds at the IO layer with a logged warning. Process kept segments independently; do not concatenate. `segment_index` is an explicit argument throughout the pipeline.

## Why this matters

Blackrock and Ripple NSP firmware commonly produce a brief (sub-5-second) first segment from operator record-verification before the real recording starts. A pause-resume during recording can also produce a short segment. These segments are artifacts, not data, but the pipeline cannot distinguish them from real epochs without a duration rule.

The cost of not having the policy is that every downstream function must handle arbitrarily short segments correctly. Most produce silently bad outputs rather than crashes:

**Spike sorting.** Sorters need hundreds of spikes per unit to estimate templates stably. At realistic firing rates (~5 Hz), a 2.36-second segment yields ~12 spikes per unit, well below the threshold for any modern sorter. MountainSort5 and Tridesclous2 run but produce unreliable templates. Kilosort4 may fail or produce nonsense. Failure modes vary across sorters and not all of them throw clean errors. Failures here can be silent: a unit "exists" in the output but its template is noise.

**Per-segment quality metrics.** Presence ratio, ISI violations, amplitude cutoff, and SNR all assume enough spikes to estimate a distribution. For very short segments these are statistically meaningless. They will still compute a number, which is the problem.

**Threshold-crossing rates.** The rate value itself is well-defined (normalized per second), but the variance is enormous. A true 0.1 Hz crossing rate over 2.36 s yields 0 or 1 actual crossings; the rate estimate is unstable. Pooling unstable estimates into longitudinal trends produces noisy time courses for no benefit.

**Aggregation and longitudinal joins.** Cross-session statistics require either per-segment aggregation weighted by duration or a "longest segment" rule. Both require carrying `segment_index` and duration through every join. The cleanest place for this decision to live is "drop segments below a duration where the question stops mattering."

## Why 5 seconds

5 seconds is a safety floor, calibrated to catch operator-verification artifacts (typically 1 to 3 s) without affecting any legitimate analysis epoch. Real baseline recordings are minutes long; real task epochs are typically tens of seconds at minimum. There is no plausible scientific use case for a 4-second segment in this project.

Downstream operations may impose stricter minimums at their own layer. Spike sorting in particular often requires segments of 60 s or more to estimate templates reliably. These per-stage minimums are separate from the IO-layer policy and are documented in their respective modules.

## Cost of the policy

One filter at the IO layer, approximately 10 lines of code, plus one log entry per dropped segment. The policy lives in `src/recqual/io/` and is applied during recording load, so every downstream consumer sees only kept segments.

## What to log

For each dropped segment, log: source file, segment index in the raw file, duration in seconds, reason ("below 5 s threshold"). Keep the log per-session so the segment-handling decisions are auditable.

## Reference

- Discovered: session 1 on `data/raw/nigel_2023-03-17.ns5` (2.36 s segment 0, 180.01 s segment 1).
- Policy decided: between session 1 and session 2.

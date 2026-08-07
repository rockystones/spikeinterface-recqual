# Session 05 — Longitudinal metric comparison, giant-event forensics, noise validation

## Goal

Deliver the project's stated end goal — longitudinal comparison of the major metrics across arrays — plus four things the experimenter raised:

1. Do not discard large-amplitude events on threshold alone; separate cross-channel artifacts from rare localised giants and from atypical positive-led (axon-like) waveforms, and record where they are.
2. Answer explicitly how the noise floor is obtained from snippet data.
3. Record that raw `.ns5` exists and what it unlocks.
4. Show how each analysis choice, including gating, moves the longitudinal trend.

Plus an interactive artifact reconstructing the project's reasoning flow.

## Built

- `notebooks/scratch_rocky_events.py` — event-level sorting-free pass over all 332 paired sessions (10.6 min, 8 workers). Per-electrode crossing rate, noise floor, amplitude percentiles, peak SNR, and a seven-class taxonomy of every event ≥250 µV. Outputs `events_electrode.parquet` (31,654 rows), `giant_events.parquet`, waveform shards.
- `notebooks/scratch_rocky_longitudinal_metrics.py` — the comparison. Sorting-based and sorting-free layers side by side, five figures, Spearman trend table.
- `notebooks/scratch_rocky_sensitivity.py` — four sweeps (9 gates × 5 methods × 4 cohort restrictions × artifact removal) re-deriving every trend.
- `notebooks/scratch_rocky_giants.py` — forensics and case studies, five figures.
- `notebooks/scratch_nigel_noise_validation.py` — snippet noise estimate against the paired `.ns5`.
- Notes: `snippet_noise_floor.md`, `giant_events.md`, `longitudinal_metrics.md`, `ns5_plan.md`.
- Artifact: interactive collapsible reasoning flow.

## Outcome

**The posterior array failed; the anterior did not.** Posterior yield ends at 3 % of its start, and the decline survives all 18 gate/method/cohort variants (rho −0.78 to −0.31, always significant). It is visible in the sorting-free layer too — crossing rate fell 3.8× — so it is not a sorting artefact. Median unit SNR is flat on both arrays: loss of units, not degradation of survivors.

**Anterior yield decline is not robust.** rho spans −0.72 to +0.05 and the sign flips across clustering methods. Anterior *amplitude* decline is robust (−0.81 to −0.39).

**Three things diverged from expectation.**

1. *The noise estimate is worse than assumed.* Validated against the Nigel `.ns5` for the first time: biased 1.305× high and **anti-correlated** with true noise (r = −0.445), because the pre-trigger window sits inside the excursion that triggered it. 21 alternative estimators were tested; none is better. Direction is safe for the posterior conclusion, unsafe for claiming a decline was mild.
2. *2017 is a different protocol*, not just an earlier date — 4916 s sessions vs 180 s, and 2.3× the noise and amplitude of 2018 with identical digitisation. It is the largest single lever on the anterior trend.
3. *The extreme amplitude tail is not neural at all.* Two pathologies no amplitude or coincidence test catches: single-sample digital impulses (43,931, pinned near 3.82 mV on specific electrodes for months) and int16 rail hits at exactly 8192 µV (4,667). Both needed a waveform-width test.

**Two corrections to my own method during the session.** Chance coincidence is ~2 electrodes per 1 ms window, so the first "local cluster" count was entirely explicable by randomness; fixed by requiring the partner to show a ≥100 µV deflection within ±0.3 ms, which drops chance to 0.076 and leaves an 11.6× excess. And selecting large-trough snippets to get a clean noise baseline makes the estimate *worse*, not better — refuting the obvious hypothesis.

**The side note the experimenter asked for.** 172 electrode sites carry real giants, 51 recurring in ≥5 sessions. Anterior electrode 61 carries 250 µV+ spikes in 30 sessions spanning 2017-10-31 to 2023-08-01 at up to 2509 µV on an 11.5 µV noise floor. Anterior 90 and 93, 800 µm apart, share 227 of 279 large events at a median lag of 0 µs with a positive-led waveform — consistent with an axonal source. 288 axon-like sites cohort-wide.

## Deferred

- Applying artifact/impulse/rail exclusion inside the sorter's gate. The event-level flags exist; folding them into `scratch_rocky_resort.py` needs a full re-run and changes every downstream number. Cohort-wide effect is small (median session max 622 → 566 µV).
- The noise-bias correction. Measured on one session only; not safe to apply cohort-wide.
- Still awaiting: manually sorted subset, impedance electrode ordering.

## SpikeInterface functions used

- `spikeinterface.preprocessing.bandpass_filter` — **new this session.** Applies a lazy zero-phase Butterworth bandpass, returning a `BaseRecording` view with no data copied. Chosen over the project's usual `highpass_filter` because the comparison target is the NSP's own hardware spike filter, which is band-limited at both ends; a highpass-only chain leaves high-frequency content the NEV snippets never saw and inflates the continuous noise estimate (14.68 µV vs 13.33 µV here, an 11 % difference in the wrong direction for the comparison).
- `spikeinterface.core.get_noise_levels` — `method="mad"` and `"std"`, `return_scaled=True` for µV.
- `spikeinterface.extractors.read_blackrock` — `stream_id="5"` for the ns5.
- `spikeinterface.preprocessing.highpass_filter` — retained for the 300 Hz comparison arm.
- `neo.rawio.BlackrockRawIO` — `get_spike_raw_waveforms`, `get_spike_timestamps`, `rescale_spike_timestamp` (via the project's `open_nev` / `read_electrode`).

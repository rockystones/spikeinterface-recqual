# Large-amplitude events: seven classes, not one

An earlier pass concluded that units above 800 µV are cross-channel artifacts and should be removed. That was right about the population and wrong as a rule. Removing large events by amplitude also deletes two phenomena that are real, rare, and interesting: very large waveforms confined to a few *neighbouring* electrodes with an atypical positive-led shape, and genuinely huge, normally-shaped spikes.

Amplitude cannot separate them. Three other quantities can, and all three are computable from snippet data alone.

`notebooks/scratch_rocky_events.py` (census) and `scratch_rocky_giants.py` (forensics). Figures in `figures/rocky/giants/`.

## The three discriminators

1. **How many electrodes carry a large deflection at the same instant.** A synchronous artifact appears everywhere; a neuron appears on one electrode, or at 400 µm pitch occasionally two.
2. **Whether those electrodes are physically adjacent**, via the CMP grid. A shared physical source is local; chance coincidence is not.
3. **The width of the dominant phase at half amplitude.** A spike at 30 kHz occupies 10–30 samples. One sample is a digital glitch, and no amplitude or coincidence test will catch it.

## Chance coincidence is the trap

The first attempt counted *any* coincident event within ±1 ms and called 1–4 coincidences "local". In a 361 k-event session the pooled rate gives **~2 electrodes per 1 ms window by chance**, so 14 % of all events have ≥4 coincident partners for no reason at all — and the number of apparently spatially-clustered giants it produced (126) was exactly what randomness predicts (~120).

Two changes fix it, and both matter:

- A coincident event only counts if it is itself **≥ 100 µV**. Chance drops from 2.0 to 0.31 partners per window.
- The shared-waveform test uses a **±0.3 ms** window, not ±1 ms, because a real shared event is time-locked far tighter than the artifact criterion needs to be. Chance drops again to **0.076**.

The artifact test keeps the ±1 ms window and a cut of ≥15 electrodes, matching Plexon's own pre-sort pass on this cohort (`width 60 ticks, channel percentage 15`). Where the pooled rate makes 15 meaningless the cut rises to the Poisson 1e-9 quantile, so it adapts to sessions spanning 14 Hz to >1 kHz.

Every session records its own `chance_coincidence`, `chance_coincidence_big` and `artifact_cut`, so any classification can be re-checked against what chance would have produced.

## The census

268,071,001 events across 332 paired sessions. **15,605,413 (5.82 %) exceed 250 µV**, which is why "giant" needs a taxonomy rather than a threshold.

| class | count | share | what it is |
|---|---|---|---|
| isolated | 7,362,310 | 47.2 % | one electrode, no large partner |
| local_cluster | 3,341,432 | 21.4 % | shared with 1–4 electrodes within 2 grid steps |
| scattered_few | 3,258,838 | 20.9 % | shared, but partners not adjacent |
| artifact | 1,418,803 | 9.1 % | synchronous across the array |
| multi_channel | 175,432 | 1.1 % | 5–7 large partners |
| impulse | 43,931 | 0.3 % | single-sample digital glitch |
| railed | 4,667 | 0.03 % | int16 saturation at exactly 8192 µV |

**local_cluster is a 11.6× excess over chance** (21.4 % observed against 1.85 % expected). Spatially local multi-electrode giants are real.

## The two non-neural pathologies

Both were invisible to the original gate and to any amplitude threshold.

**Railed.** 32768 counts × 0.25 µV = 8192 µV, the int16 ceiling, hit exactly. The recorded amplitude is not a measurement; the true value is unknown and larger.

**Impulse.** A single sample at several mV with no rising phase, followed by a smooth decay. Observed pinned near 3.82 mV on specific electrodes across whole months — posterior 6 and 8 through mid-2022, anterior 23 and 90. These produced the largest `amp_z` values in the entire cohort (up to 793× the electrode's noise) and would have topped any "biggest spike" ranking.

## What is real — the side note

After filtering to 400–4000 µV (clear of the rail), electrode noise < 30 µV, `amp_z ≥ 20` and a dominant phase ≥ 3 samples: **36,116 events across 172 electrode sites, 51 of which recur in five or more sessions.**

**A huge, isolated, normally-shaped spike that lasted years.** Anterior electrode 61 (col 8, row 2, manufacturer label `elec11`) carries 250 µV+ events in 30 sessions from 2017-10-31 to 2023-08-01 — the whole implant lifetime — at a median 521 µV and up to 2509 µV against an 11.5 µV noise floor, `amp_z` median 45. Anterior 77 does the same across 35 sessions. Anterior 78, 79, 80, 76, 87, 73, 65 and posterior 22, 71 are the same phenomenon. These are single neurons sitting unusually close to an electrode tip, and they are the events worth going back to in the raw data.

**The neighbouring-electrode axonal case.** Anterior 2018-04-19, electrodes 90 (col 5, row 0) and 93 (col 7, row 0), **800 µm apart**: of 279 events ≥400 µV on electrode 90, **227 (81 %) have a large coincident event on electrode 93, at a median lag of 0 µs**. Both mean waveforms are the same shape — a shallow trough at 0.1 ms followed by a sharp positive peak at 0.32 ms, positive-dominant with `pos_ratio` ~3. Chance would produce a handful, not 227. Electrode 90 is axon-like in 42 % of its filtered giants across 11 sessions spanning 2018-02 to 2020-07.

A positive-led biphasic waveform reaching two electrodes 800 µm apart with no measurable delay is not a somatic spike. It is consistent with an axonal or fibre-of-passage source, which is what the experimenter independently reported observing. `figures/rocky/giants/G3_neighbour_pair.png`.

Cohort-wide there are **288 axon-like sites** (positive peak dominant, below rail, normal noise, width ≥ 3 samples), split 1033 events posterior / 743 anterior.

## Where they live

Giants are a property of a few electrodes, not of the array: **the top 10 electrode-sessions hold 17 % of all giants, the top 100 hold 66 %**, and only 9,062 of 31,654 electrode-sessions have any at all. Any per-array average over "max amplitude" is really reporting on two or three electrodes.

## Practical rule

Do not gate on amplitude. Gate on `klass in {artifact, impulse, railed}` and keep the rest with their class attached. Cohort-wide the removal is small — 1.74 % artifact, 0.42 % impulse, 0.002 % railed, moving median session-max amplitude 622 → 566 µV and median electrode p99 69.6 → 65.2 µV — but it is the difference between a real 2.5 mV neuron and an ADC rail.

## Related

[[snippet_sorting]] for the per-electrode gate this supplements, [[snippet_noise_floor]] for the `amp_z` denominator, [[longitudinal_metrics]] for what removal does to the trends, [[utah_channel_mapping]] for the CMP grid used by the adjacency test.

# Longitudinal metrics, and how much they depend on the analysis

The project's goal is longitudinal comparison across arrays. This note records what the comparison says and — equally important — which parts of it survive changing the analysis and which do not.

Two scripts: `scratch_rocky_longitudinal_metrics.py` (the comparison, `figures/rocky/longitudinal/`) and `scratch_rocky_sensitivity.py` (the sweeps, `figures/rocky/sensitivity/`). 332 paired sessions, 2017-09-21 to 2023-10-06.

## Two independent layers

Every headline metric is computed twice, from sources that share only the raw file:

- **Sorting-based** (CLAUDE.md layer 2), from `units_long.parquet`: unit count, yield per electrode, electrode coverage, amplitude percentiles, unit SNR.
- **Sorting-free** (layer 1), from `events_electrode.parquet`: crossing rate, noise floor, crossing-amplitude percentiles, peak SNR. No clustering, therefore no gate, therefore nothing to argue about.

On snippet data layer 1 is unusually direct: the NEV *is* the threshold-crossing record, so the crossing rate is measured rather than reconstructed. If the layers disagree about a trend, the trend belongs to the sorter.

## What the arrays did

| metric | Anterior rho | Posterior rho | Anterior first5 → last5 | Posterior first5 → last5 |
|---|---|---|---|---|
| yield (units/electrode) | −0.09 n.s. | **−0.64*** | 1.58 → 0.26 | 1.66 → 0.05 |
| electrode coverage | −0.16* | **−0.64*** | 0.93 → 0.18 | 0.90 → 0.05 |
| median unit amplitude | **−0.74*** | **−0.50*** | 104 → 82 µV | 95 → 40 µV |
| median unit SNR | +0.09 n.s. | −0.10 n.s. | 6.97 → 6.54 | 6.50 → 5.95 |
| crossing rate (free) | −0.14 n.s. | **−0.54*** | 4.2 → 4.5 Hz | 18.5 → 4.8 Hz |
| noise floor (free) | **−0.74*** | **−0.66*** | 14.6 → 13.0 µV | 13.7 → 7.4 µV |
| electrodes with peak SNR ≥ 4 | +0.12 n.s. | −0.18* | 1.00 → 0.93 | 0.99 → 0.83 |

The posterior array failed and the anterior array did not. Posterior yield ends at 3 % of where it started, with the loss visible in the sorting-free layer too — the crossing rate itself fell 3.8×, so it is not a sorting artefact.

**Median unit SNR is flat on both arrays.** Combined with amplitude falling, this says the surviving units are as well isolated as they ever were; what changed is how many there are. Loss of units, not degradation of survivors.

## The confound that moves everything: 2017

The 2017 block was recorded on a different protocol — **4916 s sessions against 180 s from 2018 onward**, no headstage token in the filename, and a visibly different NSP threshold. It sits ~2.3× above 2018 in *both* noise floor and crossing amplitude:

| year | headstage | noise µV | crossing p50 µV | peak SNR |
|---|---|---|---|---|
| 2017 | none | 24.83 | 80.0 | 3.88 |
| 2018 | Analog | 10.75 | 37.0 | 7.58 |
| 2019 | Digital | 10.01 | 32.1 | 7.06 |
| 2022 | Digital | 8.15 | 23.0 | 6.14 |
| 2023 | Digital | 9.27 | 25.5 | 5.40 |

Digitisation is identical throughout — `gain 0.25 µV/count`, `wf_left_sweep 10`, 30 kHz on every file checked across all six years — so this is the acquisition chain, not a units bug. Including 2017 turns a mild anterior decline into a steep one: anterior yield rho ranges **−0.72 to −0.09** depending only on which sessions are admitted.

Note also that the 2017 estimate is exactly where [[snippet_noise_floor]]'s bias is largest, since those sessions have the fewest crossings per second.

## Sensitivity: what survives

Four sweeps re-derive every trend under a different analysis choice. `figures/rocky/sensitivity/S2`, `S4`, `S7` are the summary heatmaps.

- **Gate** — 9 variants (SNR 0/3/4/5/6, shape on/off, ≥20/50/200 spikes, +ISI), same ISO-SPLIT clusters throughout. Possible because `units_long.parquet` stores rejected clusters with their metrics, so re-gating is arithmetic.
- **Method** — 5 clusterers (ISO-SPLIT, GMM+BIC, HDBSCAN, k-means+silhouette, Plexon OFS) on the 60-session subset, identical gate and identical spikes.
- **Cohort** — all / exclude 2017 / Digital only / 180 s only.
- **Artifact removal** — cross-channel, impulse and railed events.

| conclusion | verdict |
|---|---|
| Posterior yield declines | **robust** — negative and significant in all 18 gate/method/cohort variants, rho −0.78 to −0.31 |
| Posterior electrode coverage declines | **robust** under method and cohort; splits under the gate |
| Anterior median unit amplitude declines | **robust** — rho −0.81 to −0.39, significant everywhere |
| Anterior yield declines | **not robust** — rho −0.72 to +0.05; sign flips across clustering methods |
| Median unit SNR trends | **not robust** — splits under every sweep |
| Electrode coverage in absolute terms | **not robust** — rho −0.23 to +0.29 under the gate alone |

Unit *counts* are strongly method-dependent in absolute level — GMM+BIC yields 6,360 units where Plexon yields 1,686 on the same 60 sessions, a 3.8× spread — but the posterior *trend* is the same in all five. Level is a property of the method; direction is a property of the array.

## Artifact removal barely touches the trends

1.74 % of events are cross-channel artifacts, 0.42 % single-sample impulses, 0.002 % railed. Median session-max crossing amplitude falls 622 → 566 µV and median electrode p99 falls 69.6 → 65.2 µV. Crossing rate and every central-tendency metric are unmoved. The correction matters for the amplitude *tail* and for anything reporting per-electrode maxima, not for yield.

## How to read a number from this project

Quote the sweep range, not the point estimate, for anything except the posterior decline. When a metric is reported for the anterior array, say which cohort restriction produced it.

## Related

[[snippet_sorting]], [[snippet_noise_floor]], [[giant_events]], [[impedance_parsing]], [[segment_selection]].

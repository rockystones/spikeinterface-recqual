# Snippet sorting (NEV-only cohorts)

How to sort a cohort that has spike snippets but no continuous broadband, and why none of the project's usual sorters can be used on one.

## The constraint

The Rocky cohort is 886 `.nev` files with **no `.ns5` anywhere**. Blackrock NEV stores pre-detected threshold crossings: a timestamp plus a short waveform clip per event. In this cohort each clip is `(n_spikes, 1, 30)` int16 — 30 samples at 30 kHz, `wf_left_sweep = 10` (10 pre-trigger, 20 post), `wf_gain = 0.25` µV/count.

Every sorter in CLAUDE.md's pool — MountainSort5, Kilosort4, Tridesclous2, SpykingCircus2 — detects spikes *from continuous traces* and extracts its own waveforms. Handed snippets, they have nothing to run on. `spikeinterface.sorters.available_sorters()` lists `waveclus_snippets` as the one snippet-native option, but it requires MATLAB and is not installed here.

This is not a degraded situation. Utah arrays have 400 µm pitch, so a neuron appears on exactly one electrode; there is no spatial oversampling for a multi-channel sorter to exploit. Per-electrode clustering is the correct method for this geometry, not a fallback. It is also what Plexon Offline Sorter itself does.

## Method

Per electrode, on the pooled snippets (all Plexon unit ids merged back together):

1. **Noise floor from the pre-trigger baseline.** No continuous trace means no MAD-from-traces. But samples `0 .. nbefore-2` of every snippet precede the threshold crossing by construction, so their MAD across all snippets estimates the electrode noise. The last two pre-trigger samples are excluded — on a fast-rising spike they already contain part of the depolarisation and bias the estimate upward. This single trick is what makes SNR, and therefore the noise gate, computable at all.
2. **Re-align on the trough** within ±2 samples. The NSP triggers on threshold crossing, which leaves 1–2 samples of jitter; removing it tightens clusters materially.
3. **PCA**, 5 components.
4. **ISO-SPLIT** (`isosplit6`) for clustering — MountainSort5's algorithm, available standalone as a 1-package install. Non-parametric unimodality test, determines cluster count automatically, assumes no cluster shape. Chosen over GMM+BIC (assumes Gaussian clusters, and extracellular clusters are not) and over reproducing Plexon's T-Dist E-M (the thing being improved on). Above 20 000 spikes it fits on a random subsample and assigns the remainder to the nearest centroid.
5. **Noise-cluster rejection gate** — see below.

## The gate

A cluster becomes a unit only if it passes all of:

| Criterion | Threshold |
|---|---|
| SNR = `\|trough\| / baseline_MAD` | ≥ 4.0 |
| Spike count | ≥ 50 |
| Peak-to-trough duration | 0.15–1.20 ms |
| Trough position vs alignment point | within ±0.20 ms |

ISI refractory violations (< 1.5 ms) are computed and *flagged* rather than used to delete — contamination is informative, and deleting on it would hide bursty units.

Rejected clusters are kept in the output with a `reject_reason`, so the cut is auditable rather than asserted. `figures/rocky/09_gate_audit_*.png` renders every cluster template against the ±1σ noise band; rejected clusters are visibly not spikes — most sit entirely inside the band with the same stereotyped shape, which is the signature of a threshold crossing on noise rather than a neuron.

## Why the gate matters

Plexon OFS output on this cohort, scored under the identical gate:

| Era | OFS units passing |
|---|---|
| 2017 (early) | 82–94 % |
| 2018 | 23 % |
| 2023 | 21 % |

OFS is genuinely good on early recordings and degrades badly as the array ages and the noise floor rises relative to signal. Its failing units are overwhelmingly `snr < 4` — median OFS unit SNR is 2.7 in 2018 and 1.8 in 2023, against a noise floor near 10 µV. Those rejected noise clusters routinely carry 500–750 spikes each, which is why they look like plausible units until amplitude is checked.

## Gotcha: NEV electrode ids exceed the array

NSP auxiliary channels appear in `spike_channels` as `ch110#227`, `ch112#68` and similar — electrode numbers above 96, with arbitrary unit ids. They are not array electrodes. Filter to `1 <= electrode_id <= 96`. Sixteen of 512 original files carry such entries; the other 496 are cleanly `chN#0`.

## Gotcha: the `-01` file holds the same events as the original

Verified on two sessions spanning the cohort: the Plexon `-01.nev` and its unsorted original contain identical event counts (2 457 967 and 153 763 respectively, matching exactly). Plexon relabels events; it never adds or removes them. So both the re-sort and the OFS scoring can be derived from a single read of the `-01` file. This halves I/O on a cohort whose largest files reach 513 MB, and makes the two methods score literally the same events — the comparison becomes exact rather than approximate.

## Gotcha: memory, not CPU, is the scaling limit

A single 2017 session holds 2.4 M snippets ≈ 290 MB as float32, doubled by the aligned copy. Running 24 parallel workers exhausted 19 GB of RAM and drove the machine to 0.3 GB free. Use ~8 workers, pop each electrode from the dict as it is consumed, and free the raw waveforms after alignment. Output is written as per-combo parquet shards so an interrupted run resumes instead of restarting.

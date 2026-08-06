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

## UnitRefine does not transfer to snippet data

The pretrained UnitRefine classifiers are ordinary sklearn Pipelines, so they can be driven from a metric table without a `SortingAnalyzer` — which matters here, since a `SortingAnalyzer` needs continuous traces this cohort does not have. They were tested properly and the result is negative.

**30 of 37 features were supplied.** The 8 that were initially missing are all computable and were added: `nn_hit_rate`, `nn_miss_rate` (SI's `nearest_neighbors_metrics` on raw arrays), `sync_spike_2/4/8` (SI's `_get_synchrony_counts`, requiring a second pass over every unit in the file), `rp_contamination` (Llobet & Wyngaard closed form), `amplitude_cv_range`, and `sliding_rp_violation`. The remaining **7 are intrinsically impossible** on single-channel snippets — `drift_ptp/std/mad`, `spread`, `velocity_above/below`, `exp_decay` — as each describes motion or decay across channels or across a continuous recording.

**Result: the models label 65 040 of 65 051 units (99.98 %) as noise.** They keep 11. This is not conservatism — the 1 686 Plexon units and 2 910 ISO-SPLIT units they discard have median SNR 6.5–6.8 and median amplitude ~81 µV against a ~11 µV noise floor, with physiological waveform shape. Those are unambiguously real units.

The saturation is complete, not a threshold artefact: `P(neural)` has median 0.224 and **maximum 0.604**, with only 0.02 % of units above 0.5. Lowering the decision threshold cannot recover the data because the probability mass never gets there.

The likely mechanism is the 7 unavailable features. On Neuropixels they are precisely what separates a real unit — spatially localised, low drift, characteristic amplitude decay across channels — from noise, which spreads everywhere. Imputing them with training-set medians strips out the evidence the classifier leans on hardest.

**Practical consequence.** For snippet-only cohorts, use an explicit physics-based gate (SNR, spike count, waveform shape, trough alignment). Do not use UnitRefine, and do not interpret its labels here as weak evidence — they are anti-correlated with unit quality on this data.

### Gotcha: the label mapping is inverted relative to intuition

`load_model` returns `(model, info)`, and `info["label_conversion"]` is `{'0': 'neural', '1': 'noise'}` — **class 1 is noise**. The models also emit integer classes, not strings, so a string comparison against `"noise"` silently matches nothing and marks every unit neural. That single mistake inverts the entire conclusion, turning "rejects everything" into "accepts everything". Always read `label_conversion` from the model card rather than assuming the sign. The SUA model is `{'0': 'mua', '1': 'sua'}`.

## Gotcha: `spike_count()` disagrees with the arrays it describes

`BlackrockRawIO.spike_count()` is **not reliable** on this cohort. Observed on `Rocky_Anterior_09-13-2018`: `spike_count` reports 296 events on a channel where `get_spike_raw_waveforms` returns 285, and 22 where only 11 waveforms exist. Reshaping by the reported count raises `ValueError: cannot reshape array of size 8550 into shape (296,newaxis)` and killed 150 of 332 combos on the first full run — all of 2019 and 2022 among them.

`get_spike_raw_waveforms` and `get_spike_timestamps` **do** agree with each other in every case checked. Take the length from the returned arrays, never from `spike_count`, and defensively truncate to `min(len(wf), len(ts))`.

## Gotcha: NEO's segment splitting is broken here, and it corrupts every rate

NEO emits `UserWarning: Detected N undocumented segments within nev data` on many files, and the segments it produces are not trustworthy. `Rocky_Anterior_01-03-2019` is reported as **10 segments**, one of them spanning **143 119 s (40 hours)** — for a 180-second baseline recording. Several segments contain timestamps but zero waveforms.

Summing segment durations to get session length therefore inflates it catastrophically and silently corrupts `firing_rate_hz`, `presence_ratio`, and anything else normalised by time.

The fix is to select **one primary segment** rather than pooling: the longest whose duration is physically plausible (≥ 5 s per the project's segment policy, ≤ 3600 s to reject NEO's artefacts). On the 2019 file this correctly picks segment 9 (183.5 s); on a 2018 file it picks segment 1 (180.0 s) over a 3.1 s false start.

Verify the bound against the cohort before reusing it elsewhere: 2017 Rocky sessions are genuinely ~50 min single-segment recordings while 2018 onward are 180 s, so a tighter upper bound would have silently discarded the entire 2017 era. That protocol change is real and must not be mistaken for an artefact.

## Gotcha: memory, not CPU, is the scaling limit

A single 2017 session holds 2.4 M snippets ≈ 290 MB as float32, doubled by the aligned copy. Running 24 parallel workers exhausted 19 GB of RAM and drove the machine to 0.3 GB free. Use ~8 workers, pop each electrode from the dict as it is consumed, and free the raw waveforms after alignment. Output is written as per-combo parquet shards so an interrupted run resumes instead of restarting.

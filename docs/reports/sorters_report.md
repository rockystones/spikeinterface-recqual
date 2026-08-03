# Comparative Review of Spike Sorting Algorithms Supported by SpikeInterface and Benchmarked by SpikeForest

## TL;DR
- **Kilosort4 (Pachitariu, Sridhar, Pennington & Stringer, Nat Methods 2024, 21:914–921) is the current default first choice for any high-density linear probe with potential drift (Neuropixels 1.0/2.0, dense linear or planar arrays).** Across the authors' simulation suite — drawn from IBL Neuropixels data with 600 ground-truth + 600 multi-units per ~45-min recording — Kilosort4 "consistently performed better" than KS2.5/KS3 in all drift conditions and recovered 80–90% of units where IronClust recovered ~50%; Kilosort2/2.5/3/4 all outperformed every non-Kilosort algorithm tested.
- **For low-channel-count, sparse, or non-drifting recordings (tetrodes, Utah arrays, micro-wire bundles, single channels) the field's empirical conclusion (Magland et al., eLife 2020, e55167; Buccino et al., eLife 2020, e61834) is that no single sorter dominates.** MountainSort4/5 (Chung et al., Neuron 2017, 95:1381–1394) excels on monotrodes/tetrodes, IronClust (Jun et al., bioRxiv 2017, doi:10.1101/101030) is competitive across nearly every study set, Wave_clus (Chaure, Rey & Quian Quiroga, J Neurophysiol 2018, 120:1859–1871) remains the standard for human/micro-wire single-channel data, and Combinato (Niediek et al., PLOS ONE 2016, 11:e0166598) is the strongest choice for multi-hour clinical recordings.
- **Several formerly important sorters are deprecated, legacy, or unmaintained as of May 2026** — YASS, Klusta, the original Tridesclous (v1) and SpyKING CIRCUS (v1) have been moved to SpikeInterface's "legacy" list; HDSort and the MATLAB Kilosort 1/2/2.5/3 lines no longer receive in-depth developer support ("we are no longer providing in-depth support for Kilosort 1-3", MouseLand/Kilosort README). The SpikeInterface team's actively developed internal alternatives are SpykingCircus2, Tridesclous2, the newer "Lupin" (Garcia, Halcrow, Windolf, McKenzie, Adkisson-Floro, Mayorquin, Dichter, Buccino & Yger, eLife Reviewed Preprint v1, doi:10.7554/eLife.110588.1, April 2026) and "Simple" sorters, all built on the modular `spikeinterface.sortingcomponents` API.

---

## Key Findings

1. **The field has split into three durable families.** (i) The Kilosort family (template-learning + matching pursuit, GPU) dominates for dense linear silicon probes with drift. (ii) The density/graph-based family (MountainSort, IronClust, HerdingSpikes2) dominates for low-channel-count or planar/CMOS-MEA recordings without strong rigid drift. (iii) The classical wavelet/SPC family (Wave_clus, Combinato) dominates for monotrodes and human micro-wire recordings, especially over multi-hour timescales.

2. **Drift handling is now the single most important axis of differentiation.** Only Kilosort 2.5/3/4, IronClust, and (recently) the SpikeInterface motion-correction front-end (DREDge, MEDiCINe, Kilosort-datashift) implement explicit drift correction. Pachitariu et al. (2024) showed that under the simulation conditions tested in the Kilosort4 paper, SpyKING CIRCUS and MountainSort4 matched IronClust at low/medium drift but their performance "deteriorated drastically with higher drift", whereas Kilosort 2.5/3/4 maintained accuracy.

3. **Maintenance status has shifted dramatically since 2023.** The original SpyKING CIRCUS v1, Tridesclous v1, and YASS are unmaintained; their authors (Yger, Garcia) have moved development into SpikeInterface's internal SpykingCircus2/Tridesclous2 sorters. The Pachitariu lab now formally declines to support Kilosort 1/2/2.5/3 ("we are no longer providing in-depth support for Kilosort 1-3", MouseLand/Kilosort README). pyKilosort exists but is wrapped in SpikeInterface mainly for IBL legacy use. Klusta is in SpikeInterface's "legacy" bucket. HDSort has had no substantive activity since v1.0.1.

4. **There are real, published differences in unit yield that should change interpretation.** On the Buccino et al. (2020) Allen Institute Neuropixels mouse cortex recording (15 min, 246 active channels), six sorters produced wildly different unit counts: Tridesclous 187, HerdingSpikes2 210, IronClust 233, HDSort 317, Kilosort2 446, SpyKING CIRCUS 628. Of 2,031 total units, **all six sorters agreed on only 33**, and "two or more sorters agree on just 263 of the total units." Consensus (k ≥ 2 sorter) curation matches expert manual curation at the ~85–90% level, while non-consensus Kilosort2 units match curated units at only ~19–24%. This argues strongly for **multi-sorter ensemble curation** as standard practice for high-density data.

5. **Several sorter-specific failure modes are now well-documented.** Kilosort family is known for **oversplitting** (mitigated in KS4 by graph clustering and cross-correlogram merge logic) and for fewer-spikes-at-batch-boundaries bugs in KS2/2.5/3 (issue #594, fixed in patch1 releases — but unpatched containers still circulate). SpyKING CIRCUS v1 tends toward **overestimation of unit count**. HerdingSpikes2 explicitly fails on probes with channel pitch > 60 μm. KS4's SpikeInterface wrapper has undergone breaking API changes ("Kilosort4 seems to change very quickly and I seem unable to find a combination of spikeinterface/kilosort4 versions with which I do not encounter problems" — SI issue #3901).

---

## Details

### A. Inventory of SpikeInterface-Wrapped Sorters (as of SpikeInterface 0.104.3 / May 2026)

External wrappers (`run_sorter(sorter_name=...)` accepts):
`herdingspikes`, `ironclust`, `kilosort`, `kilosort2`, `kilosort2_5`, `kilosort3`, `kilosort4`, `pykilosort`, `mountainsort4`, `mountainsort5`, `rtsort`, `spykingcircus`, `tridesclous`, `waveclus`, `combinato`, `hdsort`.

Internal (sortingcomponents-based) sorters: `lupin`, `spykingcircus2`, `tridesclous2`, `simple`.

Legacy / no longer supported in current release: `klusta`, `yass`.

Two new wrappers in the past year referenced in the SpikeInterface release notes are **RT-Sort** (van der Molen T, Lim M, Bartram J, Cheng Z, Robbins A, Parks DF et al., PLOS ONE 2024, 19(12):e0312438; "a spike sorting algorithm that enables the sorted detection of action potentials within 7.5 ms ± 1.5 ms (mean ± STD) after the waveform trough while the recording remains ongoing") and **Bombcell** (Fabre JMJ, van Beest EH, Peters AJ, Carandini M & Harris KD, 2023, Zenodo doi:10.5281/zenodo.8172821 — "Bombcell: automated curation and cell classification of spike-sorted electrophysiology data"). MEDiCINe (Watters et al., eNeuro 2025, 12:ENEURO.0529-24.2025) is integrated as a motion-correction front-end, not a sorter.

### B. Algorithmic mechanism, design intent, and probe fit — by sorter

#### Kilosort family (Pachitariu lab, HHMI Janelia / Flatiron Institute)

All Kilosort versions share a common backbone: GPU-based whitening and bandpass preprocessing → **template learning** (joint detection + clustering by scaled K-means in KS1; "drift tracking" in KS2; modified template-learning + datashift in KS2.5; new clustering in KS3; graph-based modularity-optimisation clustering with merging tree in KS4) → **matching-pursuit template deconvolution** to recover collision spikes → post-processing merges/splits. Kilosort is "the only major current spike-sorting platform" that performs this template-subtraction step, allowing it "to resolve spike collisions better than all" others (Pachitariu et al., Nat Methods 2024).

**Design intent:** awake head-fixed mouse, Neuropixels 1.0, dense linear probes with vertical pitch ≤ 40 μm. KS2.5+ expects probes with site geometry that supports sub-pixel registration; performance is best on probes ≥ 32 channels with dense spacing. CUDA NVIDIA GPU required (≥ 8 GB VRAM minimum; 12 GB+ recommended for standard 384-channel Neuropixels <3 h recording, per the Kilosort4 hardware page).

| Version | First public release | Key change | Drift correction | Implementation |
|---|---|---|---|---|
| KS1 (Pachitariu et al., NeurIPS 2016, bioRxiv 061481) | 2016 | Scaled K-means template learning + matching pursuit | None | MATLAB + CUDA |
| KS2 (no peer-reviewed paper) | 2018 | "Drift tracking" — templates modified continuously as a function of inferred drift | Template-side | MATLAB + CUDA |
| KS2.5 (Steinmetz et al., Science 2021, 372:eabf4588 "Neuropixels 2.0") | 2020 | Standalone **datashift** drift correction directly modifying raw voltage data via sub-pixel registration | Data-side | MATLAB + CUDA |
| KS3 | 2021 | "Completely new and much more sophisticated clustering algorithm" (per repo README); inherits KS2.5 datashift | Data-side | MATLAB + CUDA |
| KS4 (Pachitariu et al., Nat Methods 2024, 21:914–921) | Feb 2024 | Pure-Python/PyTorch reimplementation; **graph-based clustering by modularity optimization** + merging tree using refractory-period violation and bimodality criteria; explicit convolutions replace Butterworth filtering; no intermediate processed binary required | Data-side (datashift inherited) | Python + PyTorch, NVIDIA GPU |
| pyKilosort | 2021 (IBL-maintained) | Direct Python translation of KS2/KS2.5 kernels; primary purpose is reproducibility for IBL data | Data-side | Python + CuPy |

**Known limitations / failure modes:** (a) **Batch-boundary bug** in KS2/2.5/3 producing ~7 ms gaps every 2.1866 s — fixed in patch1, but many published runs predate the fix; (b) tendency to **oversplit** (mitigated in KS4); (c) Buccino et al. (2020, eLife) reported that on simulated Neuropixels data Kilosort2 produced **147 false-positive units out of 415**, reduced to 93 with KS2's built-in contamination filter; (d) KS4's SpikeInterface wrapper has unstable API — open issue #3901 documents that KS4 returns a 4-element tuple where SI expects 2; (e) Kilosort4 paper notes some false-positive results in the SpikeInterface paper (their Extended Data Fig. 3) "are due to unrealistically long spike durations" in MEArec simulations — a methodological dispute that should affect how you interpret the SI 2020 comparison.

#### MountainSort family (Magland, Chung, Barnett — Flatiron Institute)

**Algorithm (MS4, Chung et al., Neuron 2017, 95:1381–1394):** event detection by absolute amplitude threshold per channel → PCA feature extraction on detected events sparsified to local neighborhoods (adjacency_radius) → **Isosplit** non-parametric density-based clustering (Magland & Barnett 2015) that performs binary splits based on a 1-D dip-statistic test, recursively, without requiring K. CPU-only; "no parameters to tune" is the design philosophy.

**MountainSort5 (flatironinstitute/mountainsort5, 2023):** complete rewrite using SpikeInterface I/O. Three sorting schemes — Scheme 1 single-pass; Scheme 2 catalog-then-classify (handles longer recordings); Scheme 3 chunked with time-segment annealing (handles drift). Uses isosplit6 (later isosplit clustering). "Runs faster than previous versions, especially for large channel counts; better handles time-overlapping events and drifting waveforms; runs fast on CPU" (repo README). The subdivision clustering recursively splits and re-extracts PCA features within each subdivision (mountainsort5/docs/scheme1.md).

**Probe fit:** SpikeForest qualitative result (Magland et al. 2020, eLife): "MountainSort4 is among the top performers for six of the study sets... does particularly well for the low-channel-count datasets (monotrodes and tetrodes)." Recovered the highest accuracy of any sorter on the PAIRED_MONOTRODE study, slightly above Wave_clus. Strong on PAIRED_BOYDEN and PAIRED_KAMPFF mouse cortex paired recordings.

**Limitations:** MS4 scales poorly to >64 channels (quadratic dependence of pairwise distance computations). No drift correction in MS4; only Scheme 3 of MS5 handles drift, and only at chunk-level annealing — not sub-pixel registration. MS5 is missing some MS4 features (curation tags, burst-merge logic). Active maintenance is moderate — the repo is current but receives less attention than Kilosort.

#### Tridesclous family (Garcia & Pouzat, CRNL Lyon)

**Tridesclous 1 (TDC1):** offline + online (with pyacq) sorter. Pipeline: detection → feature extraction (PCA, wavelets, or "peak" features per user choice) → user-selectable clustering (DBSCAN, OPTICS, GMM, K-means, or the in-house "sawchaincut") → template-matching fitting. Designed as a teaching toolkit — "the user eye and intuition is better a weapon than a pre parametrised algorithm" (TDC docs). Strong support for many file formats via Neo. OpenCL acceleration for GPU and multi-core CPU. **Repo README now states: "trisdesclous is not maintenaned anymore, please user spikeinterface and treidesclous2 instead."**

**Tridesclous 2 (TDC2):** rewritten natively in SpikeInterface using sortingcomponents. Replaces sawchaincut clustering with iterative-isosplit and uses the SI orthogonal-matching-pursuit template matcher. Still flagged "experimental" but the recommended replacement.

**Probe fit:** SpikeForest finding was that "Tridesclous is among the top performers for both MEAREC study sets and for PAIRED_MEA64C_YGER, but had a substantially lower accuracy for most of the other datasets" (Magland et al. 2020). It's conservative — Buccino et al. (2020) report it returns the **fewest** units of any tested sorter on Neuropixels data (187 of ~2,000 total).

#### SpyKING CIRCUS family (Yger, Marre — Institut de la Vision Paris)

**SpyKING CIRCUS 1 (Yger et al., eLife 2018, 7:e34518):** Python + MPI parallelization. Pipeline: bandpass + whitening → median absolute deviation threshold detection → smart-search subsampling for clustering (designed to handle highly imbalanced firing-rate scenarios) → density-based clustering (extended Rodriguez & Laio 2014) → **greedy template matching** ("fitting") that reconstructs traces as a linear sum of templates, solving the collision problem. Tested from 30-channel in vivo to 4,225-channel in vitro MEAs. GPU optional (CUDA) for fitting step.

**SpyKING CIRCUS 2 (SC2, internal sorter in SpikeInterface):** "upgraded version of SpykingCircus, natively written in SpikeInterface. The main differences are located in the clustering (now using on-the-fly features and less prone to finding noise clusters), and in the template-matching procedure, which is now a fully orthogonal matching pursuit, working not only at peak times but at all times, recovering more spikes close to noise thresholds" (SI install_sorters docs). The clustering change addresses SC1's notorious tendency to overestimate unit count (Buccino et al. 2020 found SC1 reported 628 units on a recording where consensus suggested far fewer).

**Probe fit:** SpikeForest found "SpyKING CIRCUS is among the best sorters for ten study sets. However, it ranks a lot lower in the unit count table" — i.e., when restricted to units above accuracy 0.8, SC1's lead disappears, consistent with the false-positive critique.

#### IronClust (Jun et al., Flatiron Institute; descended from JRCLUST)

**Algorithm:** MATLAB-based, drift-resistant. Detection by absolute threshold; feature extraction using waveforms + spike location estimates; **DPCLUS** density-peak clustering (extended Rodriguez & Laio). **Drift handling via "anatomical-snapshot" linking**: divides recording into ~20-s chunks, computes activity-amplitude histograms per chunk as "anatomical snapshots," links each chunk to its 15 nearest neighbors by snapshot similarity (constrained to ±64 steps ≈ ±1,280 s to handle rigid drift on faster timescales), then performs KNN-graph density clustering with neighborhoods restricted to linked chunks. This is "terabyte-scale, drift-resistant" (repo README). GPU optional but accelerates clustering substantially.

**Probe fit:** Designed for "high channel-count, high-density silicon probes" (Neuropixels). SpikeForest summary: "IronClust appears among the top average accuracies for eight of the study sets, and is especially strong for the simulated and drifting recordings." Pachitariu et al. (2024) found IronClust "generally found ~50% of all units" in their simulations, vs 80–90% for Kilosort4 — but importantly IronClust was the **nearest competing algorithm in performance** to Kilosort 2.5/3/4 under drift.

**Limitations:** MATLAB dependency (or pre-compiled MCR); active development has slowed (James Jun moved to BSEC, leadership transferred); no Python-native port. Containerized version available via SpikeInterface Docker Hub avoiding MATLAB license requirement.

#### HDSort (Diggelmann, Fiscella, Hierlemann, Franke — ETH Zurich; J Neurophysiol 2018, 120:3155–3171)

**Algorithm:** MATLAB-based. Designed specifically for high-density CMOS MEAs (MaxWell/3Brain), exploits subsets-of-electrodes ("local electrode groups") to avoid the curse of dimensionality. Pipeline: spike detection → local group ICA-based feature extraction → mixture-of-Gaussians clustering → template-matching final assignment. Not GPU-accelerated.

**Probe fit:** SpikeInterface paper (Buccino et al. 2020) found HDSort returned 317 units (real Neuropixels) and 458 units (simulated Neuropixels), the highest count of any tested sorter on the simulated dataset — suggesting an oversplitting tendency on linear probes. Designed for, and best on, planar high-density MEAs.

**Maintenance:** Effectively unmaintained since v1.0.1; SpikeInterface wrapper still functions but the upstream repo is not active.

#### HerdingSpikes2 (Hilgen et al., Cell Reports 2017, 18:2521–2532; mhhennig/HS2)

**Algorithm:** Python + Cython. Per-channel spike detection with multi-channel interpolation → **event source localization** (estimating barycentre from amplitudes on adjacent channels) → aggressive dimensionality reduction → mean-shift density-based clustering. No GPU required. Real-time on 4,096 channels at 7 kHz on a desktop PC.

**Design intent (explicit, from README):** "developed specifically for high density multielectrode arrays, for example the Neuropixels probe, the SinAPS probes, or high-density MEAs such as the BioCam or the MaxWell Biosystems HD-MEA." **Explicit contraindication: "performance is poor for recording systems with few recording channels and channels separated by more than 60 microns; for such recordings, use one of the many other sorters."**

**Probe fit:** Restricted by design to planar/dense arrays. SpikeForest: "applied only for recordings with a sufficiently planar electrode array structure (this excluded tetrodes and linear probes). For PAIRED_MEA64C_YGER its performance was similar to other top sorters, but in the other study sets, it was somewhat less accurate."

#### Wave_clus (Quian Quiroga lab; Chaure, Rey & Quian Quiroga, J Neurophysiol 2018, 120:1859–1871)

**Algorithm:** MATLAB. Detection by amplitude threshold → **wavelet decomposition** (4-level Haar) → Kolmogorov-Smirnov-based selection of most-discriminative wavelet coefficients → **superparamagnetic clustering** (SPC, Blatt, Wiseman & Domany, Phys Rev Lett 1996, 76:3251) with automatic temperature selection (variable number of features; Chaure 2018 update). Designed for monotrodes and tetrodes. Originally Quian Quiroga, Nadasdy & Ben-Shaul, Neural Comput 2004, 16:1661–1687.

**Probe fit:** SpikeForest restricted Wave_clus to monotrodes only, where MountainSort4 narrowly beat it. Remains the de facto standard for human single-unit work and small-channel-count rodent recordings.

**Limitations:** Single-channel design — does not exploit cross-channel waveform information; not appropriate for high-density probes. MATLAB required; SPC clustering executable (cluster.exe) is a closed binary on some platforms.

#### Klusta (Rossant et al., Nat Neurosci 2016, 19:634–641)

**Algorithm:** SpikeDetekt (flood-fill detection in the adjacency graph defined by the probe geometry, per-channel double-threshold) → masked PCA features → **Masked KlustaKwik** (Kadir, Goodman & Harris, Neural Comput 2014, 26:11), a masked EM algorithm fitting a variable-K mixture of Gaussians using BIC penalty for K selection.

**Status:** **Legacy** — moved to SpikeInterface's unsupported list. Originally designed for ≤64-channel probes. KlustaKwik2 is a separate repo. The successor architecture is essentially the phy ecosystem; many users now run Kilosort + phy curation instead.

#### Combinato (Niediek, Boström, Elger & Mormann, PLOS ONE 2016, 11:e0166598)

**Algorithm:** Python. Channel selection → spike extraction → **artifact removal** → block-wise iterative superparamagnetic clustering (SPC) → template-matching reassignment for remaining spikes → non-neural cluster removal → cross-block cluster recombination. Designed for **multi-hour clinical recordings** (tested on 100-channel × 15-h ≈ 300 GB datasets) where waveforms drift over hours and where artifact rejection is critical. Multi-process scaling.

**Probe fit:** human depth electrodes, Behnke-Fried micro-wire bundles, single channels / few channels per shank. Not appropriate for high-density probes.

#### YASS — Yet Another Spike Sorter (Lee et al., NeurIPS 2017; primate-retina extension Lee, Mitelut et al., bioRxiv 2020.03.18.997924)

**Algorithm:** Triage-then-cluster-then-pursuit. **Neural-network spike detection** (CNN trained on spike templates) → outlier triage to remove collisions and noise → nonparametric Bayesian (Dirichlet Process Mixture) clustering with coreset data reduction → matching-pursuit deconvolution to recover triaged collision spikes. Python + CUDA (CuPy) + TensorFlow for the NN detector. Designed for and validated on primate retina with ≥500-electrode dense MEAs.

**Status:** **Legacy** in SpikeInterface. The original repo (paninski-lab/yass) has not had significant releases since 2020. Installation has historically been the most painful of any major sorter (TF-GPU + CUDA + custom CuPy kernels).

#### RT-Sort (recently added)

**Algorithm:** Action-potential propagation–based real-time spike detection and sorting. From van der Molen et al. (PLOS ONE 2024, 19(12):e0312438): "a spike sorting algorithm that enables the sorted detection of action potentials within 7.5 ms ± 1.5 ms (mean ± STD) after the waveform trough while the recording remains ongoing." Wrapped in SpikeInterface in the past year.

#### SpikeInterface-internal sorters (sortingcomponents-based)

- **SpykingCircus2** and **Tridesclous2**: see above.
- **Lupin**: newer SI-internal sorter described in Garcia, Halcrow, Windolf, McKenzie, Adkisson-Floro, Mayorquin, Dichter, Buccino & Yger ("Opening the black box: a modular approach to spike sorting", eLife Reviewed Preprint v1, doi:10.7554/eLife.110588.1, April 1 2026): "Lupin is a new spike sorting algorithm...created to demonstrate the power of such modularity."
- **Simple**: minimalist reference implementation.

### C. SpikeForest benchmark results (Magland et al., eLife 2020)

SpikeForest (https://spikeforest.flatironinstitute.org) is the canonical web-facing benchmark, currently containing ~650 recordings (1.3 TB), ~35,000 ground-truth units, contributed by 11 laboratories. Ten "popular" sorters are run via SpikeInterface wrappers in a nightly batch on the Flatiron compute cluster. Results are displayed as heatmaps (Fig. 2) — average accuracy with SNR threshold = 8 and unit count with accuracy threshold = 0.8.

**Important methodological caveat:** the published paper presents the numerical accuracy results only as a heatmap figure; the per-cell numbers must be read from the live website or the heatmap image. The textual conclusions from Magland et al. are reproduced below:

> "No single spike sorter emerged as the top performer in all study sets, with IronClust, KiloSort2, MountainSort4, and SpyKING CIRCUS each appearing among the most accurate in at least six of the study sets."

> "IronClust appears among the top average accuracies for eight of the study sets, and is especially strong for the simulated and drifting recordings."

> "MountainSort4 is among the top performers for six of the study sets (based on the average accuracy table) and does particularly well for the low-channel-count datasets (monotrodes and tetrodes)."

> "SpyKING CIRCUS is among the best sorters for ten study sets. However, it ranks a lot lower in the unit count table on the right of Figure 2."

> "Klusta is substantially less accurate than other sorters in most of the study sets, apart from MANUAL_FRANKLAB where, surprisingly, it found the most units above accuracy 0.8 of any sorter."

> "KiloSort and KiloSort2 had higher numbers of crashes than any of the other sorters, including crashing on every one of the SYNTH_VISAPY recordings."

Study sets and characteristics (from Magland et al. 2020 Table 2):

| Study set | Recordings | Channels | Duration | Source |
|---|---|---|---|---|
| PAIRED_BOYDEN | 19 | 32 | 6–10 min | Boyden lab, mouse cortex paired |
| PAIRED_CRCNS_HC1 | 93 | 4–6 | 6–12 min | Buzsaki lab, rat hippocampus tetrodes |
| PAIRED_ENGLISH | 29 | 4–32 | 1–36 min | English lab, hybrid juxta+Si |
| PAIRED_KAMPFF | 15 | 32 | 9–20 min | Kampff lab, mouse cortex paired |
| PAIRED_MEA64C_YGER | 18 | 64 | 5 min | Marre lab, mouse retina |
| SYNTH_BIONET | 36 | 60 | 15 min | Allen Institute (drift simulation) |
| SYNTH_JANELIA | 60 | 4–64 | 5–20 min | Pachitariu (the bioRxiv preprint called this HYBRID_JANELIA) |
| SYNTH_MAGLAND | 80 | 8 | 10 min | Flatiron |
| SYNTH_MEAREC_NEURONEXUS | 60 | 32 | 10 min | Buccino (MEArec simulation) |
| SYNTH_MEAREC_TETRODE | 40 | 4 | 10 min | Buccino |
| SYNTH_VISAPY | 6 | 30 | 5 min | Einevoll (LFPy simulation) |
| MANUAL_FRANKLAB | 21 | 4 | 10–40 min | Frank lab tetrodes |

### D. The SpikeInterface multi-sorter comparison (Buccino et al., eLife 2020)

On the Allen Institute Neuropixels 1.0 mouse cortex recording (V1 + CA1 + DG + LP, 246 active channels, 30 kHz, 15 min, Allen dataset ID 766640955), Buccino et al. ran six sorters at default parameters:

| Sorter | Units found (real NPX) | Units found (simulated NPX, 250 GT) |
|---|---|---|
| Tridesclous 1.6.0 | **187** | 189 |
| HerdingSpikes2 0.3.7 | 210 | 233 |
| IronClust 5.9.8 | 233 | 283 |
| HDSort 1.0.1 | 317 | 458 |
| Kilosort2 (commit 48bf2b81d8ad) | 446 | 415 |
| SpyKING CIRCUS 0.9.7 | **628** | 343 |

**Consensus statistics on the real recording:**
- Of 2,031 total detected units, **all six sorters agreed on only 33 units (1.6%)**.
- **Two or more sorters agreed on just 263 units (12.9%)**.
- "For most sorters, over 50% of the units that they find do not match with any other sorter (with the exceptions of Ironclust and Tridesclous)."

**On the MEArec-simulated Neuropixels recording (250 GT neurons, 10 μV noise, 10 min):**
- Only 139 of 1,921 total units (7.24%) agreed across all six sorters.
- Kilosort2: 245 well-detected + 147 false positive + 21 redundant. With KS2's automated >20% contamination filter: 241 well-detected + 93 FP + 18 redundant.
- "For two sorters, the most reliable identification of true positives for this dataset was achieved by combining Kilosort2 and Ironclust (96% and 95% false positive and true positive detection rate, respectively)."

**Consensus vs expert curation (Buccino et al. Fig. 4):**
- IronClust ∩ Curator 1 = 59.83%; IronClust ∩ Curator 2 = 61.1%
- Kilosort2 ∩ C1 = 50.67%; Kilosort2 ∩ C2 = 56.25%
- **Consensus-curated** (k ≥ 2 sorter agreement) match to curated: KS2_c ∩ C1 = 84.55%, KS2_c ∩ C2 = 89.55%; IC_c ∩ C1 = 82.63%, IC_c ∩ C2 = 83.83%.
- Non-consensus Kilosort2 units match curated at only 18–24%.

The take-home: **automated consensus curation across multiple sorters performs nearly as well as expert manual curation, while requiring no manual labor.**

### E. The Kilosort4 benchmark (Pachitariu et al., Nat Methods 2024)

The Kilosort4 paper introduces a new hybrid-simulation framework using densely-sampled real electrical fields from IBL Neuropixels data to generate non-stationary spike waveforms and realistic noise. Six simulation conditions (no drift, medium drift, high drift, fast drift, step drift, step drift with aligned/NP2-style sites) of ~45 min each, 600 GT neurons + 600 multi-units each. All non-KS algorithms were run via SpikeInterface wrappers (December 2022 versions).

**Algorithms tested:** Kilosort 1, 2, 2.5, 3, 4, pyKilosort, IronClust, SpyKING CIRCUS, MountainSort4, HerdingSpikes2, Tridesclous, HDSort.

**Key textual numerical claims:**
- "All Kilosort versions except Kilosort1 outperformed all other algorithms, with Kilosort4 performing the best" (no-drift hybrid simulations).
- "Kilosort 2, 2.5, 3 and 4 outperformed all other algorithms in all cases" (drift simulations).
- "IronClust generally found ~50% of all units, compared to the 80–90% found by Kilosort4."
- "Some of these (SpyKING CIRCUS and MountainSort4) matched the IronClust performance at no drift, medium and fast drift, but their performance deteriorated drastically with higher drift."
- "Among all algorithms with explicit drift correction (Kilosort2.5, 3 and 4), Kilosort4 consistently performed better due to its improved clustering algorithm and in some cases performed much better (on the step drift conditions)."
- "Across simulations Kilosort4 had similar numbers of false positive units compared to the other algorithms, which were generally in the range of 50–100 units."

**Ablation findings:** drift correction, template deconvolution, and CCG-based merges/splits had the strongest individual effects on accuracy; nonrigid motion correction had the least impact.

**Methodological dispute worth noting:** Pachitariu et al. (2024) Extended Data Fig. 3 contends that some Kilosort false-positive results in the SpikeInterface paper "are due to unrealistically long spike durations" in MEArec simulations. This is a real methodological caveat — MEArec biophysical simulations may favor density-based sorters over template-matching sorters.

### F. Independent comparisons

- **Brainstem recordings (rostroventromedial medulla, ~32-channel custom probes, Reddy et al., J Neurophysiol 2024, PMC11601346):** Compared MS5, IC, KS3, TDC, SC on 1,241 total units. KS3 (good-only) and TDC produced the fewest units; SC the most; MS5 and IC intermediate. The paper explicitly recommends consensus curation.
- **Allen Institute pipeline retrospective (Siegle et al., bioRxiv 2025.11.12.687966):** "The results of the benchmarking pipeline Application #1 motivated our decision to replace Kilosort2.5 with Kilosort4 as the default spike sorter in our spike sorting pipeline. We found that Kilosort4 could more accurately identify ground truth spikes... which corroborated the results of the original paper... We extended this result to data with the same noise characteristics and spiking statistics as what we were actively collecting, as well as to data from Neuropixels 2.0."
- **MEDiCINe motion correction (Watters et al., eNeuro 2025):** comparison across 384 simulated NP datasets shows MEDiCINe and DREDge slightly outperform Kilosort-datashift on relative spike-sorting inaccuracy, especially under irregular non-rigid motion patterns.

### G. Maintenance and installation status (May 2026 snapshot)

| Sorter | Repo status | Container | Compute | GPU required | License | Recent activity |
|---|---|---|---|---|---|---|
| Kilosort4 | Active (MouseLand) | Yes (spikeinterface/kilosort4-base) | Python/PyTorch | **Yes — NVIDIA, ≥12 GB VRAM recommended** | GPL-3 | Continuous releases |
| Kilosort3 | "No longer providing in-depth support" | Yes | MATLAB + CUDA | Yes | GPL-3 | Patch1 bug fix only |
| Kilosort2.5 | "No longer providing in-depth support" | Yes | MATLAB + CUDA | Yes | GPL-3 | Patch1 bug fix only |
| Kilosort2 | "No longer providing in-depth support" | Yes | MATLAB + CUDA | Yes | GPL-3 | Patch1 bug fix only |
| Kilosort1 | Archival | Yes | MATLAB + CUDA | Yes | GPL-3 | None |
| pyKilosort | Active (IBL) | Yes (spikeinterface/pykilosort-base) | Python + CuPy | Yes | Apache | Bug fixes |
| MountainSort5 | Active (Flatiron) | Yes | Python (CPU) | No | Apache | Steady |
| MountainSort4 | Maintenance-only | Yes | Python (CPU) | No | Apache | Stable |
| IronClust | Slow but maintained | Yes (no MATLAB license needed) | MATLAB + optional GPU | Optional | Apache | Occasional |
| SpyKING CIRCUS 1 | Frozen (1.x line) — author redirects to SC2 | Yes | Python + MPI | Optional (CUDA) | CeCILL | Minor only |
| SpykingCircus2 | Active (SpikeInterface internal) | N/A (no install needed) | Python | No | Apache | Active |
| Tridesclous 1 | **Repo banner: "not maintaned anymore"** | Yes | Python + OpenCL | Optional | MIT | Frozen |
| Tridesclous2 | Active (SI internal) | N/A | Python | No | Apache | Active |
| HerdingSpikes2 | Active (Hennig lab) | Yes | Python + Cython | No | GPL-3 | Steady |
| HDSort | Unmaintained since ~2019 | Yes | MATLAB | No | GPL-3 | None |
| Wave_clus | Active (Quian Quiroga lab) | Yes | MATLAB | No | Custom non-commercial | Occasional |
| Klusta | **Legacy in SI** | No (current) | Python | No | BSD-3 | Abandoned |
| YASS | **Legacy in SI** | No (current) | Python + CUDA + TF | Yes | Apache | Abandoned |
| Combinato | Active | Yes | Python | No | MIT | Occasional |
| RT-Sort | New (Dec 2024) | Yes | Python | Likely yes | TBD | Active |
| Lupin / Simple | New SI internals (2026) | N/A | Python | No | Apache | Active |

### H. Containerization

SpikeInterface maintains Docker images on Docker Hub (https://hub.docker.com/u/spikeinterface) for nearly every sorter, including all MATLAB-based ones (Kilosort 1–3, IronClust, HDSort, Wave_clus). The MATLAB containers ship with the MATLAB Compiler Runtime and **do not require a MATLAB license** at runtime. To use GPU-accelerated containers, the host must have NVIDIA drivers, CUDA, and `nvidia-container-toolkit`. Singularity is also supported and is the appropriate option for HPC environments where Docker is not allowed.

---

## Decision Table — Sorter → Use case

Read this as: **for a given probe/dataset, which sorter(s) should you prioritize?** I take positions; alternatives in parentheses.

| Probe / dataset | Primary sorter | Secondary (for consensus) | Notes / contraindications |
|---|---|---|---|
| Neuropixels 1.0 / 2.0, acute (<3 h), expected drift | **Kilosort4** | IronClust, MountainSort5 (Scheme 3) | Use the official kilosort PyPI release; lock SI ↔ KS4 versions explicitly to avoid wrapper breakage (see SI issue #3901). Apply SI motion correction (MEDiCINe or DREDge) as preprocessing if drift > ~30 μm. |
| Neuropixels chronic, multi-day | **Kilosort4** with motion correction; or **IronClust** for terabyte-scale | MountainSort5 Scheme 3 | KS4 limited by GPU memory and ~3 h batch design — split chronic recordings into daily sessions or use IronClust for whole-implant analyses. |
| Dense planar/CMOS MEAs (3Brain BioCam, MaxWell, ETH MEA1K) | **HerdingSpikes2** | SpykingCircus2, Kilosort4 | HS2 is the only sorter designed for this geometry; KS4 works on dense planar arrays but template-matching scales worse than HS2's localization-then-cluster. |
| NeuroNexus low-density linear (32–64 ch, pitch > 50 μm) | **Kilosort4** (with caution) | IronClust, MountainSort5, Tridesclous2 | HerdingSpikes2 **contraindicated** (pitch > 60 μm cutoff). KS4 default parameters assume denser probes — increase channel grouping radius. |
| NeuroNexus multi-shank | **Kilosort4** per shank or **MountainSort5** | IronClust, Tridesclous2 | Shank-by-shank sorting avoids cross-shank artifacts; SI's `split_recording` makes this trivial. |
| Utah array (Blackrock, 96 ch, ~400 μm pitch) | **MountainSort5** (Scheme 2) | IronClust, Tridesclous2, Wave_clus per-channel | Most sorters are sub-optimal here because the array is too sparse for spatial template matching. Treat each electrode as a near-monotrode. KS family will work but loses its main advantage (spatial template). |
| Tetrodes (4-channel, e.g. Frank lab, Buzsaki lab) | **MountainSort4 or MountainSort5 (Scheme 1)** | Wave_clus, Tridesclous2, Klusta (legacy reproducibility only) | SpikeForest result: MS4 strongest on PAIRED_CRCNS_HC1 and MANUAL_FRANKLAB. Kilosort family is overkill and sometimes worse on tetrodes (KS expects dense linear geometry). |
| Single channel / monotrode (rodent) | **Wave_clus** | MountainSort4, Combinato | MS4 was narrowly best on SpikeForest PAIRED_MONOTRODE, Wave_clus second. |
| Human micro-wires (Behnke-Fried, multi-hour clinical) | **Combinato** | Wave_clus | Combinato is the only sorter designed for >12-h clinical recordings with artifact bursts. |
| Primate retina ex vivo (≥500-ch dense MEA, high firing rates) | **YASS** (if you can install it) or **Kilosort4** | SpyKING CIRCUS, MountainSort5 | YASS was specifically validated on primate retina; in SI, it's now legacy — prefer KS4 in containers for new analyses. |
| Drift simulation / strong drift validation | **Kilosort4** | IronClust | Pachitariu et al. (2024) is the relevant benchmark; KS4 explicitly dominates here. |
| Reproducibility-locked archive (publishing pipelines) | **Containerized SI run of 2+ sorters + consensus** | — | Use Docker/Singularity for version pinning; Buccino et al. (2020) demonstrated that consensus of any 2 sorters approaches expert curation. |
| Real-time / closed-loop | **RT-Sort** | Tridesclous 1 (with pyacq) | RT-Sort (van der Molen et al. 2024) reports 7.5 ms ± 1.5 ms detection latency. |
| Multi-hour recording, frequent waveform drift | **Combinato** (human) or **MountainSort5 Scheme 3** (rodent) or **IronClust** | Kilosort4 + motion correction | Annealing-style chunking handles slow waveform drift better than continuous datashift in some cases. |
| You don't know yet / pilot dataset | **Run Kilosort4 + IronClust + MountainSort5 via SpikeInterface, take consensus** | Tridesclous2 | This is the empirically validated multi-sorter strategy (Buccino et al. 2020). |

---

## Recommendations

### Staged strategy for a longitudinal recording quality pipeline

**Stage 1 — Establish baseline and reproducibility (week 1):**
1. Install SpikeInterface ≥ 0.104.3 in a pinned conda environment. Pin one SpikeInterface version per pipeline release.
2. Use containerized sorters (Docker or Singularity) exclusively, not local installs. This eliminates the entire class of MATLAB/CUDA/version-drift bugs that has historically dominated user issues.
3. For a Neuropixels-class probe, run **Kilosort4** as the primary sorter with default parameters and SI's MEDiCINe motion-correction preprocessor.
4. **Always also run a second sorter** (IronClust for drift, MountainSort5 for sparse arrays) — the marginal compute cost is small compared to the validation benefit.

**Stage 2 — Validate against ground truth or consensus (weeks 2–4):**
1. If you have any paired juxta+extra recordings, build a SpikeForest-style internal benchmark — even 2–3 recordings will reveal sorter-specific failure modes for your geometry.
2. If not, use the Buccino et al. (2020) approach: define "consensus units" as units detected by ≥ 2 sorters with > 50% spike-train agreement. Treat consensus units as your high-quality set.
3. Apply automated quality metrics (SpikeInterface `qualitymetrics`: ISI violation, presence ratio, amplitude cutoff, drift metric, sliding RP violation) and **Bombcell** (Fabre et al. 2023, Zenodo 8172821) for cell-type-aware quality control.

**Stage 3 — Lock and version (week 4 onward):**
1. Pin sorter version, SI version, container hash, and motion-correction method in a config file checked into source control.
2. Re-benchmark whenever any of these change. Pachitariu et al. (2024) and Siegle et al. (2025) both document that newer Kilosort releases substantially change unit yield, so blind upgrades will break longitudinal comparability.
3. Re-run the whole archive when (a) Kilosort releases a major version bump (KS4 → KS5), (b) the SpikeForest leaderboard shows a sorter beating your current default by ≥ 5% accuracy, or (c) a probe change introduces new geometry.

### Thresholds that should change your sorter choice

- **Channel pitch > 60 μm:** rule out HerdingSpikes2.
- **Channel count < 16:** rule out Kilosort family in favor of MountainSort or Wave_clus.
- **Drift > 20 μm peak-to-peak:** require a sorter with explicit drift correction (KS2.5/3/4 or IronClust); add motion-correction preprocessing for any other sorter.
- **Recording > 6 hours continuous:** prefer Combinato (human) / IronClust or MS5 Scheme 3 (rodent), or split the recording.
- **No NVIDIA GPU available:** rule out Kilosort family and YASS; use MountainSort5, HerdingSpikes2, Tridesclous2, SpykingCircus2.
- **No MATLAB license and no Docker:** rule out IronClust, HDSort, Wave_clus, Kilosort 1–3.
- **Final unit yield > 2× any other sorter:** treat with skepticism — most likely oversplitting (Kilosort family) or noise-cluster inflation (SpyKING CIRCUS 1). Apply consensus filtering or upgrade to the v2 reformulation.

---

## Caveats

1. **SpikeForest's per-cell accuracy numbers are not in the paper text.** They live only in the Figure 2 heatmap and on the live website. Numerical claims in this document attributed to SpikeForest are the *qualitative* rankings explicitly stated by Magland et al. (2020); per-cell numbers must be queried at https://spikeforest.flatironinstitute.org.

2. **The Kilosort4 simulation framework favors Kilosort.** Pachitariu et al. (2024) constructed their hybrid simulations using IBL data templates and their own drift models, and their critique of MEArec simulations (Extended Data Fig. 3) suggests the SpikeInterface paper's KS false positives may be partly simulation artifacts. The reverse is also true: MEArec biophysical simulations are arguably more realistic for waveform shape but less so for drift. **Treat all single-benchmark claims with caution; the field's consensus is that consensus-of-sorters is more reliable than any single sorter.**

3. **Default parameters were used in nearly all published comparisons.** Buccino et al. (2020) explicitly say: "we fix their parameters to default values to allow for straightforward comparison." Real-world performance with tuned parameters can differ substantially — especially for SpyKING CIRCUS (whose smart-search threshold strongly affects unit count) and Kilosort (whose `Th` detection threshold trades sensitivity for FP rate).

4. **The Pachitariu lab does not support SpikeInterface wrappers for Kilosort.** From the MouseLand/Kilosort README: "We do not provide support for SpikeInterface, and are not involved in their development (or vise-versa). If you encounter problems running Kilosort4 through SpikeInterface, please try running Kilosort4 directly instead." For maximally reproducible runs, consider invoking Kilosort4 directly (its `run_kilosort` API can read a SpikeInterface RecordingExtractor via the `RecordingExtractorAsArray` wrapper) rather than through `run_sorter`.

5. **Bugs and breaking changes.** The KS2/2.5/3 batch-boundary bug (~7 ms gaps every 2.18 s) was fixed in late 2023 patch1 releases, but uncountably many published results predate the fix. The KS4 ↔ SI wrapper has had repeated API breaks (issue #3901). Pin versions deliberately.

6. **Maintenance status is a moving target.** This document reflects the state of repos as of May 2026; reassess every 6–12 months. The trajectory is clearly toward (a) Python-native, (b) GPU-optional or modular, (c) integrated with SpikeInterface, (d) using ensemble or graph-based clustering. Sorters that do not move in this direction (HDSort, YASS, Klusta) are effectively dead-ends despite their historical importance.

7. **Probe-class coverage in SpikeForest is uneven.** Utah arrays in particular are under-represented in SpikeForest study sets; my recommendation of MountainSort5 for Utah arrays is based on the SpikeForest tetrode/monotrode result (because each Utah electrode is functionally an isolated monotrode at 400 μm pitch) and the algorithm's lack of dependence on dense geometry, rather than direct ground-truth benchmarking. This is an informed inference, not a sourced claim.

8. **Method-of-comparison matters.** Most cited papers use "agreement score" = matched spikes within ±0.4 ms / max(GT, sorted) spikes. This penalizes oversplit units more than overmerged ones, biasing rankings against Kilosort-family sorters and toward conservative sorters like Tridesclous. Reading the original paper's matching definition before quoting numbers is essential.
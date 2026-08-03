# Part 4 — Integrated Extracellular Recording Quality Pipelines, Organized by Probe Physical Category

## Framing

This document is the synthesis layer of a four-part reference series. Parts 1–3 are treated as authoritative inputs and are not re-derived. Part 1 reviewed spike sorters available in SpikeInterface and benchmarked in SpikeForest; Part 2 reviewed post-sorting curation; Part 3 reviewed sorting-free quality metrics for longitudinal tracking. Part 4 inverts the axis from method-family to probe-category: for each physical class of penetrating extracellular probe, **which integrated pipeline (sorter + curator + sorting-free metric stack + motion-correction policy) is defensible in 2026, what fails, and where the field is still inferring rather than validating**.

The categorization rules are applied first-match-wins, in this order: (1) 3D penetrating bed-of-nails arrays → Category 1; (2) otherwise, pitch ≤ 100 µm → Category 2; (3) otherwise, channel count > 16 → Category 3; (4) otherwise (pitch > 100 µm AND channels ≤ 16) → Category 4. The 3D-dense cell remains empty as of 2026 — no widely-deployed probe combines bed-of-nails geometry with within-shank pitch ≤ 100 µm. ECoG and other non-penetrating surface arrays are out of scope.

Three integration conflicts between Parts 1–3 must be made visible up front, because they shape the per-category recommendations below:

1. **Sorter–curator drift-correction conflict (Category 1).** Part 1 recommends Kilosort4 as the modern default for dense linear probes with drift. Part 2's primary rule-based curator (Bombcell) is "specifically tailored for units recorded with Neuropixel probes (3A, 1.0, and 2.0) using SpikeGLX or OpenEphys and spike-sorted with Kilosort" (Fabre et al. 2023 Zenodo 10.5281/zenodo.8172821 README). Part 3's chronic-Utah-array AEY convention (BrainGate; Hahn et al. 2025 medRxiv) skips spike sorting entirely. Composing all three on a Utah array produces an inconsistent stack: Kilosort4's drift module is contraindicated on 400 µm pitch (Pachitariu et al. 2024 Nat Methods 21:914), Bombcell is out-of-scope, and AEY does not need a sorter at all. The integrated recommendation must reconcile these.

2. **PC-feature curator–modern sorter conflict (all sorter-based categories).** Part 2 flagged that PC-based isolation metrics (L-ratio, isolation distance, nn_*) are tetrode-era classics that "fail on Kilosort outputs". Yet several legacy Category 4 pipelines (and Allen ecephys_spike_sorting defaults) still ship them. Part 4 must say explicitly when to drop them.

3. **HerdingSpikes2 pitch–benchmark conflict (Category 3 boundary).** Part 1 stated HerdingSpikes2 explicitly fails on probes with pitch > 60 µm. Category 3 (sparse planar) typically has 100–200+ µm pitch. Therefore HerdingSpikes2 is contraindicated across Category 3 even though SpikeInterface still wraps it.

---

## 1 — Executive Integrated Decision Table

| Category | Defining rule | Representative probes | Primary sorter | Secondary sorter(s) | Contraindicated sorters | Primary curator | Mandatory sorting-free metrics | Motion correction | Key caveat |
|---|---|---|---|---|---|---|---|---|---|
| **1. 3D sparse penetrating arrays** | Bed-of-nails geometry, electrodes project into tissue volume; ~400 µm pitch on the cortical surface, each shank is a single electrode | Blackrock Utah array (16/96/256 ch, 400 µm pitch); Utah Slant Array (USEA); Utah Optrode | **None for BCI decoding (threshold crossings, –4.5 × robust σ)**. For SUA: **Kilosort4 with `nblocks=0` / `do_correction=False`** | MountainSort5 (channel-local), Kilosort2 (no required drift module), Wave_clus (per-electrode) | Kilosort4 with drift on; HerdingSpikes2; SpyKING CIRCUS with shared-channel templates; any sorter assuming dense spatial templates | UnitRefine (with caveat: n=80 cluster validation on Utah V1/V4, Jain 2025 reports 96.0% balanced accuracy); Bombcell **not validated**, use only ISI/amplitude/refractory components manually | **AEY (–4.5 × robust σ, 250–5000 Hz, ≥ 2 Hz, BrainGate)**; V_RMS; top-2% V_pp (Hughes 2021); 1 kHz impedance (Williams 2009/Ludwig 2008) | **Disabled** — array geometry makes z-axis drift correction ill-defined (Pachitariu 2024) | Each shank is electrically a single-channel monotrode at ~400 µm pitch; "single-unit yield" measured by SUA count is a strong function of operator policy, not a probe property |
| **2. Dense planar arrays** | Pitch ≤ 100 µm; linear single-shank, dense multi-shank, or planar 2D | Neuropixels 1.0 (20 µm), Neuropixels 2.0 (15 µm), 3Brain BioCam, MaxWell HD-MEA, ETH MEA1K, NeuroNexus 64-ch @ 20–50 µm pitch | **Kilosort4** (Pachitariu 2024 Nat Methods 21:914) | Kilosort 2.5 (legacy reference, drift-corrected; current IBL pipeline sorter per figshare 19705522); SpyKING CIRCUS 2; MountainSort5 for in vitro / retina; HerdingSpikes2 *only* for pitch ≤ 60 µm and large in-vitro arrays | HerdingSpikes2 on pitch > 60 µm (e.g., NeuroNexus 50 µm linear); Wave_clus (single-channel); Combinato (human-microwire-tuned); HDSort outside CMOS-MEAs | **Bombcell + UnitRefine layered** (Part 2 recommendation; Power Pixels pipeline, Meijer & Battaglia 2025 bioRxiv 2025.06.27.661890); Allen ecephys defaults for cross-validation | V_RMS; AEY; drift trace from DREDge or MEDiCINe; for chronic: spike-band power (Nason 2020), top-2% V_pp | **Enabled by default** — Kilosort4 piecewise rigid + DREDge (Windolf et al. 2025 Nat Methods s41592-025-02614-5) for cross-session chronic | KS4's piecewise-rigid drift correction assumes ≤ 40 µm vertical pitch and z-only motion; oblique insertions or shear violate this |
| **3. Sparse planar arrays, mid-to-high channel count** | Pitch > 100 µm AND channels > 16; planar linear/multi-shank arrangement | NeuroNexus 64-ch linear @ 200 µm; NeuroNexus 32-ch multi-shank (8 sh × 4 ch); Cambridge NeuroTech sparse multi-shank | **Kilosort4 with `nblocks=0`** OR **MountainSort5** (operator's choice, run both for consensus) | The other of {KS4, MS5}; Tridesclous2; per-shank Wave_clus on isolated shanks | HerdingSpikes2 (pitch >> 60 µm); Kilosort4 default drift settings (will hallucinate motion on sparse channels); KS3 (oversplit prone) | **UnitRefine** as primary (validated on wire bundles, NHP arrays); manual ISI/amplitude refractory thresholds; PC-based metrics **excluded** | V_RMS; AEY (where threshold-crossing decoding is a target); MUA firing rate; impedance | **Disabled or sub-shank only** | Most under-benchmarked category; Liu 2025 JHU MS thesis on 64-ch NeuroNexus rhesus monkey recordings reports MountainSort 5 outperforms Kilosort 2.5 and KS4 |
| **4. Low-N sparse probes** | Pitch > 100 µm AND channels ≤ 16 | Tetrodes (4 ch); micro-wire bundles (1–16 ch, 9-channel Neuralynx probes); single-channel monotrodes; carbon-fiber arrays (16 ch, ~150–500 µm pitch) | **MountainSort 4 or 5** (tetrodes; Chung et al. 2017 Neuron 95:1381) OR **Wave_clus 3** / **Combinato** (single-wire human MTL); Kilosort4 with `nblocks=0` acceptable but not preferred | The other; Tridesclous; Klusta (legacy) | Kilosort4 with drift correction on; HerdingSpikes2; SpyKING CIRCUS 2 dense-template mode | Manual + per-cluster ISI / refractory / SNR thresholds; **UnitRefine retrained** if used (wire-bundle generalization untested in Jain 2025); rely on PC-based isolation metrics here (this is where they are still defensible) | V_RMS; AEY (–3.5 to –4.5 × σ depending on lab); SUA firing rate; impedance | **Inapplicable** (tetrodes/microwires have no z-axis to register against) | Human single-wire literature still relies on operator-tuned Wave_clus/Combinato; the field has no equivalent of Pachitariu-grade hybrid benchmarks for this category |

---

## 2 — Per-Category Sections

### Category 1: 3D Sparse Penetrating Arrays

#### A. Category characteristics
Bed-of-nails 3D silicon arrays (the canonical Blackrock Utah array, in 16/96/256-channel configurations; also the Utah Slant Array USEA for peripheral nerve, and the Utah Optrode). Each shank is electrically a single-channel monotrode; shanks are spaced at 400 µm on a 4 × 4 mm square base. The "array" has 96 spatially separated single electrodes, not a spatially correlated population. Typical context: **chronic** implantation in human motor / somatosensory / language cortex (BrainGate, Pittsburgh, Battelle/Ohio State, Caltech/USC), in NHP (Hatsopoulos, Smith, Shenoy lineage), and in rodent cortex. Recordings span days to years (BrainGate up to 7.6 years; one Hatsopoulos NHP array — designated MkM1c in macaque M1 — sustained recordings for nearly nine years and was explanted only because of an infection near the connector, per Sponheim et al. 2021 J Neural Eng 18:066044). Expected drift profile: macroscopic insertion-day settling over 4–6 weeks (Sponheim 2021 Fig. 5b shows yield rising in first 40 days post-implantation), then slow yield decline (Hahn et al. 2025 medRxiv 2025.07.02.25330310: "On average, arrays successfully recorded neural spiking waveforms on 35.6% of electrodes, with only a 7% decline over the study enrollment period (up to 7.6 years, with a mean of 2.8 years)"). Expected SNR: low to moderate per electrode (5–15 µV peak for many channels, with a long tail of high-amplitude channels — hence the top-2% V_pp metric).

#### B. Primary sorter recommendation + rationale
**For BCI decoding: no sorter; use threshold crossings at −4.5 × robust σ in the 250–5000 Hz band**, after linear-regression re-referencing. This is the BrainGate convention used unchanged across all 14 BrainGate / BrainGate2 participants and 2,319 recording sessions. Verbatim from Hahn et al. 2025 medRxiv (Fig. 1C caption): "30 KHz recordings were decimated to 15 KHz, band pass filtered with a pass band of 250-5000 Hz, re-referenced with linear regression referencing (LRR) and thresholded at −4.5 times the robust standard deviation of the voltage signal for each channel." Trautmann et al. 2019 Neuron 103:292 showed that on Utah arrays in NHP M1/PMd, population dynamics recovered from threshold crossings are essentially indistinguishable from those recovered after spike sorting.

**For systems-neuroscience SUA analysis: Kilosort4 with `nblocks=0` (drift correction disabled).** Pachitariu et al. 2024 Nat Methods 21:914–921 explicitly state: "Some types of data do require special consideration. For example, some data cannot be drift-corrected effectively due to either lacking a well-defined geometry (tetrodes) or due to the vertical spacing between electrodes being too high (more than 40 μm). This consideration also applies to data from single electrodes such as in a Utah array." Operationally this means using KS4 on a per-shank basis (each shank treated as a 1-channel recording, then concatenated). The Allen Institute for Neural Dynamics SpikeInterface wrapper exposes a `--min-drift-channels` argument that defaults to 96, which has the effect of disabling drift correction for typical Utah arrays.

#### C. Secondary sorters for consensus
**MountainSort5** (Chung et al. 2017 Neuron 95:1381; modern reimplementation by Magland/Flatiron). Because it sorts each local channel neighborhood independently and does not assume a dense spatial template, it is mechanically compatible with Utah-array geometry. **Kilosort2** (no required drift module) and **Wave_clus 3** (Chaure, Rey & Quian Quiroga 2018 J Neurophysiol 120:1859, per-electrode) are also defensible for cross-validation. Buccino et al. 2020 eLife 9:e61834 documents that no single sorter dominates in consensus comparisons, so a KS4 + MS5 consensus on Utah arrays is the most defensible posture for SUA work.

#### D. Contraindicated sorters
- **Kilosort4 with drift correction on** (`nblocks > 0`): Pachitariu 2024 explicitly warns against this.
- **HerdingSpikes2**: requires pitch ≤ 60 µm (Part 1 finding; HerdingSpikes PyPI README explicitly excludes this regime).
- **SpyKING CIRCUS / Kilosort3 with shared-channel templates across electrodes**: the 400 µm pitch makes cross-electrode template sharing pathological.
- **HDSort**: tuned for CMOS-MEA geometries.

#### E. Primary curation method
**UnitRefine** is the only Part-2 curator with **any** published Utah-array validation. Jain et al. 2025 bioRxiv 2025.03.30.645770 verbatim: "Going beyond Neuropixels, we tested UnitRefine in Utah array recordings in the visual cortex (V1 and V4, n = 80 clusters) of non-human primates during resting-state conditions. Here, the model was trained on data from one Utah array and tested on another within the same brain region, achieving a very high balanced decoding accuracy of 96.0%." The underlying dataset is the 1024-channel macaque V1/V4 dataset from Chen et al. 2022 Scientific Data 9:77 (DOI: 10.1038/s41597-022-01180-1). This is a small validation set compared to UnitRefine's Neuropixels validations (Neuropixels 2.0 rat CA1: 87.4% on n=1,062; Neuropixels 2.0 mole-rat: 81.0% on n=506), the Utah arrays were anesthetized/resting-state visual cortex (not motor cortex BCI), and the upstream sorter was Kilosort (version unspecified). Bombcell is contraindicated because its README explicitly restricts scope to Kilosort outputs from Neuropixels 3A/1.0/2.0 (Fabre et al. 2023 Zenodo 10.5281/zenodo.8172821). For BCI work where no sorter is run, curation reduces to per-channel artifact rejection and per-channel AEY thresholding.

#### F. Sorting-free metric stack
Category 1 is the category where Part 3's eleven metric families were largely defined and validated. **Mandatory core**: (1) array-wide electrode yield (AEY) at −4.5 × robust σ, ≥ 2 Hz, 250–5000 Hz, the BrainGate convention; (2) V_RMS computed in event-free windows (Downey et al. 2018 J Neural Eng 15:046016); (3) top-2% peak-to-peak voltage (Hughes et al. 2021 J Neural Eng 18:045012; the 1500-day Pittsburgh cohort metric); (4) 1 kHz impedance (Barrese et al. 2013 failure-mode analysis remains the canonical longitudinal-failure framework). **Optional/advanced**: MUA firing rate; spiking-band power (Nason 2020 Nat Biomed Eng 4:973; Even-Chen 2020 Nat Biomed Eng 4:984); decoding-based metrics (Christie 2015; Trautmann 2019). **Inapplicable**: drift detection via DREDge/MEDiCINe (no z-axis to register), CSD (no laminar geometry), HerdingSpikes2-style local-density network metrics.

#### G. Integrated pipeline
1. Read .ns5/.ns6 via `spikeinterface.extractors.read_blackrock` (path to .ns6, not .nev).
2. Bandpass 250–5000 Hz; linear regression re-referencing (BrainGate convention) or common median re-referencing.
3. Compute V_RMS per channel in event-free windows (Downey 2018 convention).
4. Threshold at −4.5 × robust σ; compute AEY (≥ 2 Hz threshold).
5. If SUA needed: run Kilosort4 per shank with `nblocks=0`; alternatively MountainSort5 over a logical "tetrode" of nearest-neighbor channels.
6. Curation: UnitRefine + manual review of waveform/ISI/refractory in Phy or SortingView.
7. Reconcile: report AEY, top-2% V_pp, V_RMS, impedance; SUA counts as a derived secondary outcome.
8. For longitudinal series: track all four metrics per session per channel; apply the Sponheim slope (−0.00058 yield-fraction/day for NHP Utah arrays) as a sanity baseline.

#### H. Cross-validation logic when methods disagree
- **AEY rises but SUA count falls**: typical pattern in chronic decline. Trust AEY for BCI decoder retraining; SUA loss reflects waveform amplitude attenuation, not signal loss.
- **Bombcell would label many units "non-somatic"**: ignore — Bombcell's non-somatic logic is tuned for Neuropixels somatic templates; on Utah arrays many high-amplitude waveforms are legitimately axonal/dendritic at the single-channel recording-site geometry.
- **UnitRefine confidence < 0.7 on > 50% of clusters**: probably out-of-distribution motor cortex vs. V1/V4 training; fall back to manual curation.
- **V_RMS rises sharply with stable impedance**: external noise contamination, not implant failure; re-run with notch filtering before re-curation.

#### I. Evidence base and caveats
Strong evidence: BrainGate longitudinal (Hahn 2025 medRxiv; 14 participants, 7.6 years, preprint); Sponheim 2021 J Neural Eng (55 arrays, 19 subjects, nearly 9 years for one NHP array; slope −0.00058 fraction/day); Hughes 2021 J Neural Eng (1500-day Pittsburgh cohort). Weak evidence: Bombcell/UnitRefine on motor-cortex Utah arrays during behavior (no published benchmark). Open questions: whether modern automated curation can match the precision of a trained Phy operator on Utah-array SUA when units are sparse and waveforms are single-channel.

### Category 2: Dense Planar Arrays

#### A. Category characteristics
Probes with within-shank pitch ≤ 100 µm: Neuropixels 1.0 (20 µm vertical pitch, 384 active channels), Neuropixels 2.0 (15 µm vertical pitch on a denser linearized geometry, four-shank 5120-site variant; Steinmetz et al. 2021 Science 372:eabf4588 demonstrates stable chronic recordings over more than two months in 21 rats and mice across six laboratories), 3Brain BioCam, MaxWell Biosystems HD-MEA, ETH MEA1K, NeuroNexus 64-channel linear @ 20–50 µm pitch. Drift profile: micrometer-scale within-session drift (corrected by Kilosort4 piecewise-rigid registration) and tens-of-micrometers between-session drift in chronic implantations (corrected by DREDge or MEDiCINe across sessions; Windolf et al. 2025 Nat Methods s41592-025-02614-5 demonstrates DREDge on chronic Neuropixels 1.0 cohorts of 31 and 57 sessions and chronic four-shank Neuropixels 2.0 cohorts of 11 and 13 sessions). Typical context: acute and chronic, rodent (most common), NHP (Pesaran, Moore labs), and intraoperative human. SNR moderate-to-high; recording duration minutes to months.

#### B. Primary sorter recommendation + rationale
**Kilosort4** (Pachitariu et al. 2024 Nat Methods 21:914). Kilosort4 was designed on Neuropixels data and benchmarked specifically on Neuropixels and Neuropixels-like hybrid recordings. Verbatim from Pachitariu 2024: "IronClust generally found ~50% of all units, compared to the 80–90% found by Kilosort4 (Fig. 4j). Many of the algorithms tested did not have explicit drift correction. Some of these (SpyKING CIRCUS and MountainSort4…) matched the IronClust performance at no drift, medium and fast drift, but their performance deteriorated drastically with higher drift." The graph-based clustering avoids the over-split pathology of Kilosort3.

#### C. Secondary sorters
- **Kilosort 2.5**: the IBL pipeline reference sorter (figshare 19705522, ibl-sorter; used at scale in the IBL Brain-Wide Map). Useful as a versioned reference baseline.
- **SpyKING CIRCUS 2** (Yger 2018): template-matching with explicit overlapping-spike modeling; useful when high firing rates produce template collisions.
- **MountainSort 5**: defensible for in-vitro CMOS-MEAs and retinal arrays.
- **HerdingSpikes2**: only on dense planar 2D arrays with pitch ≤ 60 µm (e.g., MaxWell HD-MEA, BioCam) — not on linear silicon with 50 µm spacing.

#### D. Contraindicated sorters
- HerdingSpikes2 on linear probes with pitch > 60 µm (Part 1; HerdingSpikes PyPI README).
- Wave_clus, Combinato (single-electrode methods).
- HDSort outside CMOS-MEAs (it was designed specifically for HD-MEA geometries).
- Klusta (legacy, no drift, no modern curation hooks).

#### E. Primary curation method
**Layered Bombcell + UnitRefine** is the Part 2 recommendation, and the Power Pixels pipeline (Meijer & Battaglia, 2025 bioRxiv 2025.06.27.661890; abstract verbatim: "The Power Pixels pipeline combines processing steps from SpikeInterface, elements from the [IBL pipeline], Bombcell, and UnitRefine") instantiates exactly this layering on Neuropixels recordings. Bombcell provides rule-based four-class labels (single somatic / MUA / non-somatic / noise) with 17 quality metrics; UnitRefine provides a random-forest classifier with ~83% balanced accuracy on Neuropixels training data. Allen ecephys_spike_sorting thresholds (ISI<0.5, amplitude_cutoff<0.1, presence_ratio>0.95; Siegle et al. 2021 Nature 592:86) and the IBL pipeline (slidingRP + noise_cutoff + amplitude_median ≥ 50 µV) are reasonable cross-validation references.

#### F. Sorting-free metric stack
**Mandatory**: V_RMS, AEY (often used as a within-shank yield check), drift trace from DREDge or MEDiCINe. **Optional**: top-2% V_pp (less commonly reported for Neuropixels than for Utah arrays); spike-band power (Nason 2020) for BCI-style applications; LFP power and CSD (Senzai/Buzsaki 2019 Neuron 101:500) for laminar context; network synchrony metrics for in-vitro CMOS-MEAs. **Inapplicable**: impedance at 1 kHz on Neuropixels is a probe-internal CMOS measurement and is not directly comparable to the Utah-array 1 kHz convention; treat as an internal diagnostic, not a longitudinal QC scalar.

#### G. Integrated pipeline
1. Read SpikeGLX (Neuropixels), Open Ephys, or MaxWell HDF5 via SpikeInterface.
2. CatGT-style or SpikeInterface `common_reference` preprocessing; bandpass; bad-channel detection.
3. Motion estimation: DREDge (Windolf 2025) or MEDiCINe (Watters et al. 2025 eNeuro 12: ENEURO.0529-24.2025); apply within-session piecewise-rigid correction.
4. Kilosort4 with default `nblocks` (≥ 5 for Neuropixels 1.0).
5. Bombcell on Kilosort output (the Bombcell-Kilosort interface is the natively supported one).
6. UnitRefine random-forest classification of remaining ambiguous units.
7. Compute SpikeInterface qualitymetrics module on the final SortingAnalyzer.
8. SortingView interactive view (Magland & Soules 2025 Figurl/sortingview as integrated in eLife reviewed-preprint 110170, bioRxiv 2025.11.12.687966) for manual spot-check.
9. For chronic series: cross-session DREDge alignment, then sliding-window AEY and SUA-count tracking.

#### H. Cross-validation logic when methods disagree
- **Kilosort4 reports many units, UnitRefine confidence low**: usually oversplitting in regions of high local firing density; merge candidates via SLAy or manual merge in Phy.
- **Bombcell labels many units "non-somatic"**: trust on Neuropixels; this is what Bombcell is calibrated for (Fabre 2023 README).
- **DREDge and Kilosort4 drift estimates disagree**: DREDge is more robust to nonstationary firing patterns (Windolf 2025); prefer DREDge for chronic across-session registration.
- **HerdingSpikes2 produces wildly different unit count vs Kilosort4** on a 2D HD-MEA: this is expected and is documented as the canonical use case for ensemble sorting (SpikeInterface "Ensemble sorting of a 3Brain Biocam recording from a retina" tutorial).

#### I. Evidence base and caveats
Strong: Pachitariu 2024 Nat Methods (hybrid ground-truth on real Neuropixels recordings, 80–90% true unit recovery at high drift); Steinmetz 2021 Science (chronic Neuropixels 2.0, 21 rats/mice across 6 labs, > 2 months stable recording); Windolf 2025 Nat Methods (DREDge chronic across-session validation); Magland & Soules 2025 eLife reviewed preprint 110170 (efficient and reproducible pipelines, Allen Institute for Neural Dynamics). Weak: chronic CMOS-MEA in vitro literature is sparse on integrated curation pipelines. Caveat: Kilosort4 drift correction assumes piecewise-rigid z-axis motion at pitch ≤ 40 µm; oblique insertions, multi-shank Neuropixels 2.0 angled insertions, or large shear all violate this assumption (KIASORT preprint 2025, bioRxiv 2025.07.10.664175).

### Category 3: Sparse Planar Arrays, Mid-to-High Channel Count

#### A. Category characteristics
Pitch > 100 µm AND channel count > 16. Includes NeuroNexus 64-channel linear probes at 200 µm pitch, NeuroNexus 32-channel sparse multi-shank (e.g., 8 shanks × 4 channels with intra-shank pitch > 100 µm), Cambridge NeuroTech sparse multi-shank variants, and modular custom Si arrays used in NHP basal-ganglia and deep-cortex work. Context: acute and chronic, primarily rodent and NHP; head-fixed; chronic implants for behavioral neuroscience. Drift profile: in chronic implants, drift is real but not well-corrected by piecewise-rigid motion algorithms because the sparse channel count provides too few constraints. SNR moderate; recording duration weeks to months.

#### B. Primary sorter recommendation
**Kilosort4 with `nblocks=0`** OR **MountainSort5** — depending on the operator's prior. The Kilosort4 documentation explicitly states: "For probes with fewer channels (around 64 or less) or with sparser spacing (around 50um or more between contacts), drift estimates are not likely to be accurate, so drift correction should be skipped by setting nblocks = 0." On 64-channel NeuroNexus rhesus monkey recordings, Liu (2025, JHU MS thesis, "Optimizing and benchmarking spike sorting pipelines for high-density neural recordings") found that "Mountainsort 5 outperforms both versions of Kilosort on real and hybrid data" — a notable category-specific finding because it inverts the Part 1 dense-probe default.

#### C. Secondary sorters
The other of {Kilosort4-no-drift, MountainSort5}; Tridesclous 2; per-shank Wave_clus on isolated shanks (treating each shank as a single channel set).

#### D. Contraindicated
- HerdingSpikes2 (pitch >> 60 µm).
- Kilosort4 with default drift settings (will hallucinate large fictitious motion).
- Kilosort3 (oversplit-prone; Pachitariu 2024 acknowledges this).

#### E. Primary curation method
**UnitRefine** is the strongest Part-2 option because Jain et al. 2025 explicitly validated on "wire bundles" and "Utah arrays" beyond Neuropixels — the closest published validation to Category 3 probes. Bombcell can be run but its non-somatic rules are calibrated on Neuropixels somatic waveforms and may mislabel sparse-probe waveforms with unusual spatial structure. Allen ecephys defaults are acceptable. PC-based isolation metrics (L-ratio, isolation distance, nn_*) — Part 2 explicitly warned that these "fail on Kilosort outputs" — should be excluded.

#### F. Sorting-free metric stack
**Mandatory**: V_RMS, AEY where threshold-crossing decoding is a downstream target, MUA firing rate per channel, impedance at 1 kHz. **Optional**: top-2% V_pp; spike-band power; LFP coherence across channels. **Inapplicable**: DREDge/MEDiCINe (too few channels to converge); CSD (depends on linear shank geometry — applicable on a single 64-ch linear shank at 200 µm pitch, inapplicable on multi-shank-sparse).

#### G. Integrated pipeline
Same backbone as Category 2, with three modifications: (1) preprocess on a per-shank basis where multi-shank; (2) disable drift correction in the sorter; (3) prefer manual merge / split over automated, because sorter ensembles disagree more strongly in this regime.

#### H. Cross-validation logic
- **Kilosort4-no-drift and MountainSort5 cluster counts differ by > 30%**: run consensus matching in SpikeInterface comparisons module; accept only clusters present in both within 10-ms tolerance.
- **UnitRefine confidence low across the board**: out-of-distribution probe; fall back to Bombcell with non-somatic flag disabled, plus manual Phy review.

#### I. Evidence base and caveats
This is the most under-benchmarked category. SpikeForest (Magland 2020) and Kilosort4 hybrid benchmarks (Pachitariu 2024) both focus on dense linear / high-channel-count probes. The Liu 2025 JHU thesis benchmarks (MountainSort 5 > Kilosort 2.5 / KS4 on 64-ch NeuroNexus rhesus monkey real and hybrid data) is the strongest pointer specific to this category but is a single thesis, not a peer-reviewed multi-site validation. **Pipeline recommendations in this category are informed inferences more than benchmarked best practice.**

### Category 4: Low-N Sparse Probes

#### A. Category characteristics
Tetrodes (4 channels) in microdrives (Buzsáki, Frank labs in rodent hippocampus and PFC); micro-wire bundles (1–16 channels, e.g., Behnke-Fried 8-microwire depth electrodes in human MTL, Neuralynx 9-microwire probes used in Quian Quiroga 2008 ff., Mormann lab arrays); single-channel monotrodes; carbon-fiber arrays of 16 channels at ~150–500 µm pitch (Patel et al., Chestek lab). Context: freely-moving rodents (tetrodes), human epilepsy patients (microwires), birds (HVC carbon-fiber arrays in zebra finches). Drift profile: tetrodes drift visibly within session, corrected historically by manual cluster-drift modeling (MoDT, Shan/Kadir 2017 bioRxiv 109850) rather than spatial registration. Microwires in human MTL drift across days due to patient movement, brain pulsation, and tissue settling. SNR can be very high per-channel because the operator advances tetrodes to the cell layer. Recording duration: hours (acute), weeks (chronic rodent), days (epilepsy admission for human microwires), months (carbon-fiber arrays).

#### B. Primary sorter recommendation
- **Tetrodes**: **MountainSort 4 or 5** (Chung et al. 2017 Neuron 95:1381). MS returns >99% accuracy on the Harris hippocampal juxtacellular ground-truth tetrode data; Kilosort split the same unit into two pieces with >99% accuracy but has no native bursting-pair report; SpyKING CIRCUS split it incorrectly. Strohl et al. 2021 Bioelectronic Medicine 7:21 (DOI 10.1186/s42234-021-00079-3, "Framework for automated sorting of neural spikes from Neuralynx-acquired tetrode recordings in freely-moving mice") documents the MountainSort + Neuralynx tetrode integration pattern. Wave_clus 3 (Chaure, Rey & Quian Quiroga 2018 J Neurophysiol 120:1859) reports significantly fewer errors than Klusta, MountainSort, Kilosort, and SpyKING CIRCUS on tetrode simulations — though MS is the de facto standard in the Frank lab pipeline.
- **Human single-wire MTL**: **Wave_clus 3** (Chaure et al. 2018) or **Combinato** (Niediek/Mormann); the MCWs (MiCroWire sorter) preprint (bioRxiv 2025.07.09.663285) is an emerging alternative tailored for human microwire arrays. The HSUPipeline standardizes SpikeInterface + NWB for human single-unit work.
- **Carbon-fiber arrays**: published 64-channel CFEA spike sorting (Guitchounts & Cox 2020 Sci Rep 10:3830) — specific sorter not directly verified from available sources, treat as informed inference; published CFEA work elsewhere has used MountainSort and semi-automated PCA + k-means / Gaussian mixture pipelines (Welle et al. 2024 J Neural Eng on PEDOT-coated carbon fibers).

#### C. Secondary sorters
The other of {MS, Wave_clus}; Tridesclous; for tetrode-style geometry Kilosort4 with `nblocks=0` (Pachitariu 2024 demonstrated KS4 on a 128-channel tetrode array as a sanity check, identifying 127 single units; verbatim Extended Data Fig. 2: "Eight single units out of 127 identified in a publicly available tetrode dataset").

#### D. Contraindicated
- Kilosort4 with drift correction enabled (Pachitariu 2024 explicitly excludes tetrodes from drift correction).
- HerdingSpikes2 (pitch and channel count violate its assumptions).
- SpyKING CIRCUS 2 dense-template configurations.

#### E. Primary curation method
- **Manual + per-cluster ISI, refractory period violation, and SNR thresholds** remain the gold standard for tetrodes and microwires.
- **UnitRefine retrained** if a lab wants automation — Jain et al. 2025 included wire bundles in their validation set but the training data is dominated by Neuropixels, so a per-probe retraining is advisable.
- **PC-based isolation metrics** (L-ratio, isolation distance, nearest-neighbor metrics) are still defensible here — this is the regime they were designed for (Schmitzer-Torbert et al. 2005; Hill et al. 2011) and where Part 2's warning about Kilosort outputs does not bite as hard, because MountainSort/Wave_clus produce PC-compatible features.
- **Bombcell**: not validated, contraindicated on a per-unit basis (non-somatic rules misfire on bursting hippocampal pyramidal cells).

#### F. Sorting-free metric stack
**Mandatory**: V_RMS, AEY (with thresholds typically tuned to −3.5 to −4.5 × σ), SUA firing rate, impedance at 1 kHz. **Optional**: top-2% V_pp; LFP power and CSD if shank geometry permits. **Inapplicable**: DREDge/MEDiCINe (no z-axis to register against), drift detection via spatial registration generally.

#### G. Integrated pipeline
1. Read Neuralynx, Plexon, Intan, or Open Ephys via SpikeInterface.
2. Bandpass, common-median reference within the tetrode/bundle.
3. Compute V_RMS, threshold-crossing AEY.
4. MountainSort (tetrodes) or Wave_clus / Combinato (microwires).
5. Manual curation in Phy / SortingView with per-cluster ISI, refractory, and SNR review.
6. PC-based isolation metrics where the sorter produces compatible features.
7. For longitudinal: tetrode-drift modeling (MoDT) within session; manual cross-session unit re-identification.

#### H. Cross-validation logic
- **MountainSort and Wave_clus disagree on cluster count by > 50%**: trust the higher-amplitude clusters from MountainSort, and use Wave_clus as a sanity check on low-amplitude units.
- **PC-based isolation metric flags unit but ISI clean**: investigate cross-talk between adjacent tetrode wires or between adjacent microwires in the bundle.

#### I. Evidence base and caveats
MountainSort is well-validated on tetrodes (Chung 2017 with juxtacellular ground truth on Harris hippocampal dataset). Wave_clus 3 is well-validated on single-channel ground-truth simulations and on human MTL microwires (Chaure 2018). Human microwire literature is currently in flux: MCWs preprint (bioRxiv 2025.07.09.663285) explicitly criticizes Wave_clus 3 ("its current approach, based on non-Gaussian wavelet coefficient distributions, is suboptimal for effective clustering"), Combinato ("frequently requires manual intervention to resolve a tendency toward over-clustering"), and OSort ("reliance on significant manual parameter tuning"). Caveat: UnitRefine has not been benchmarked specifically on tetrodes; users should treat its tetrode predictions as advisory.

---

## 3 — Cross-Category Synthesis

### Principles that generalize across all four categories
1. **Preprocessing is universal**: bandpass 250–5000 Hz (or 300–6000 Hz for tetrodes), bad-channel detection, and re-referencing apply to every category.
2. **The four-metric reporting standard from Part 3** — V_RMS, AEY, top-2% V_pp, 1 kHz impedance — is reportable on every category (with the impedance caveat for CMOS Neuropixels).
3. **Run two sorters and accept consensus units only**: Buccino et al. 2020 eLife 9:e61834 established this as the defensible posture for SUA work; it applies regardless of category.
4. **Manual review of refractory period violations and ISI distributions never goes away** for any single-unit analysis.

### Principles that are category-specific (do not generalize)
1. **Kilosort4's drift module**: works in Category 2, must be disabled in Categories 1, 3, 4. This is not a parameter tuning detail — it is a categorical contraindication.
2. **HerdingSpikes2's pitch ≤ 60 µm constraint**: cuts across Category 2 (where it works only on the dense end) and excludes Categories 1, 3, 4 entirely.
3. **Bombcell's Neuropixels-only scope**: cleanly applicable in Category 2; not portable to Categories 1, 3, 4 without retraining of thresholds.
4. **PC-based isolation metrics**: defensible in Category 4 where they were designed; misleading in Category 2 on Kilosort outputs (Part 2 finding).
5. **DREDge / MEDiCINe motion correction**: useful in Category 2, ill-defined in Categories 1, 3, 4.
6. **Whether to sort at all**: in Category 1 BCI work, the default is to not sort; in all other categories, sorting is the default.

### Common cross-category failure modes
- **Sorter–curator mismatch**: e.g., running Bombcell on a HerdingSpikes2 output (Bombcell's metric definitions assume Kilosort template structure).
- **Drift correction hallucinating motion** on sparse-channel probes (Pachitariu 2024 explicitly warns; Kilosort GitHub issue #619).
- **PC-based metrics misapplied** on Kilosort outputs in dense probes.
- **Cross-session unit tracking** treated as equivalent to within-session sorting (it is not; cross-session requires explicit cross-session registration, e.g., UnitMatch or DREDge cross-session).
- **Treating threshold-crossing AEY as a sorter substitute**: AEY is a quality metric and a decoding feature, not a sorted-unit count.

---

## 4 — Integration Patterns

### Patterns that work universally
- **Sequential**: preprocess → sort → curate → metrics → reconcile. Works for every category.
- **Parallel computation per shank / per recording block**: works for every category; required at scale (Magland & Soules 2025 eLife reviewed preprint 110170 / bioRxiv 2025.11.12.687966 demonstrates >20× speedup on six-Neuropixels-Quad-Base recordings via Nextflow + SpikeInterface + Code Ocean).
- **Triage on V_RMS first**: drop channels with V_RMS > 3× cohort median *before* sorting; applies in every category.

### Patterns that are category-specific
- **Consensus sorting** (running two sorters and intersecting) is most defensible in Categories 1 and 3 (under-benchmarked) and Category 2 dense MEAs in vitro; less informative in Category 4 where MS or Wave_clus is the de facto gold standard.
- **Layered Bombcell + UnitRefine**: only validated as a stack in Category 2 (Power Pixels pipeline, Meijer & Battaglia 2025).
- **DREDge cross-session registration before merging across days**: Category 2 only.

### Evidence applicability
- Pachitariu 2024 hybrid benchmarks: Category 2 directly; Categories 1, 3, 4 by extension only.
- Buccino 2020 ensemble finding: applies categorically across all categories.
- Magland 2020 SpikeForest: tetrode and Neuropixels-like; Categories 2, 4.
- Jain 2025 UnitRefine: Categories 2 strong; 1, 3 by limited validation; 4 by inference.
- Fabre 2023 Bombcell: Category 2 only.

---

## 5 — Longitudinal-Pipeline-Specific Guidance

### Category 1 (chronic BCI, Utah arrays)
The most defensible chronic combination is:
- **Sorter**: none for BCI decoding; Kilosort4-no-drift for SUA where required.
- **Curator**: none for BCI; UnitRefine with caveats for SUA.
- **Metric stack**: AEY (BrainGate −4.5 × robust σ convention), V_RMS, top-2% V_pp, 1 kHz impedance — all four reported per session per channel.
- **Longitudinal baseline**: Sponheim 2021 slope −0.00058 yield-fraction/day; BrainGate Hahn 2025 7% decline over 7.6 years; one NHP array (MkM1c) recorded nearly nine years.
- **Cross-session unit tracking**: not done at scale on Utah arrays; the chronic BCI literature relies on decoder retraining rather than unit-level tracking.

### Category 2 (chronic Neuropixels)
- **Sorter**: Kilosort4 with default drift correction.
- **Curator**: Bombcell + UnitRefine layered.
- **Metric stack**: V_RMS, AEY, DREDge drift trace.
- **Cross-session tracking**: DREDge cross-session registration (Windolf 2025; demonstrated on 31 + 57 NP1.0 sessions and 11 + 13 four-shank NP2.0 sessions); or UnitMatch.
- **Reference**: Steinmetz 2021 (chronic NP2.0 demonstrated over more than two months in 21 rats and mice across six laboratories).

### Category 3 (chronic NeuroNexus / Cambridge NeuroTech)
- **Sorter**: Kilosort4-no-drift OR MountainSort5; consensus.
- **Curator**: UnitRefine + manual.
- **Metric stack**: V_RMS, AEY, MUA firing rate.
- Cross-session tracking: largely manual (operator re-identification).

### Category 4 (chronic tetrodes / microwires / carbon-fiber)
- **Sorter**: MountainSort (tetrodes / carbon-fiber); Wave_clus 3 or Combinato (microwires).
- **Curator**: manual + PC-based metrics.
- **Metric stack**: V_RMS, AEY, SUA count, impedance.
- **Cross-session tracking**: MoDT (Shan/Kadir 2017 bioRxiv 109850) within session; manual across.

---

## 6 — Probes That Do Not Fit Cleanly

### Carbon-fiber arrays
Patel/Chestek 16- and 64-channel carbon-fiber arrays operate at pitches in the 150–500 µm range with channel counts spanning Categories 3 and 4 boundaries. They typically resemble Category 4 (low-N sparse) in 16-channel form and Category 3 in 64-channel form. Recommendation: **categorize by channel count and pitch as in the rules**; the integrated-pipeline literature uses MountainSort (e.g., Patel et al. 2020 Sci Rep PMC10771280 for chronic 16-ch CFEA with semi-automated PCA + MoG sorting; Guitchounts & Cox 2020 Sci Rep 10:3830 for the 64-ch CFEA), consistent with the Category 4 default.

### Ultra-flexible mesh electronics, polyimide flexible probes
These can range from low-N to high-density. Categorize by their probe-array geometry; methods recommendations follow whichever category they map to. The ultra-flexible MERF in NHP V1 (PMC10667845) functions as a Category 2 dense probe and should be processed with Kilosort4. No additional category needed.

### Intravascular Stentrode (Synchron) and other endovascular arrays
Out of scope for spike-resolution Part 4 — these record LFP, not resolvable spikes.

### Neuropixels NHP variants with mm-scale insertion (e.g., basal ganglia at 20+ mm depth, Windolf 2025)
Still Category 2 by pitch (≤ 100 µm), but motion correction is mission-critical and Kilosort's template-based drift tracking can fail (Windolf 2025 demonstrates this on macaque GPi recordings: "KS' template-based drift tracking failed in this case"); use DREDge as the motion estimator.

**No new category is proposed.** All probes encountered in this synthesis map to one of the four existing categories.

---

## 7 — Recommendations for User's Specific Hardware

### Acquisition: Blackrock / Ripple Neuro
Both write the .ns5/.ns6 / .nev family; SpikeInterface's `read_blackrock(file_path, stream_id=..., block_index=...)` extractor reads both (Neo-backed). Ripple Trellis-acquired files can also be read via Blackrock-compatible extractors. Probe metadata (geometry, channel mapping) must be set via a `ProbeInterface` object — Blackrock files do not always carry probe geometry natively.

### Utah arrays, 16 ch and 96 ch → Category 1
**Priority-ordered recommendation**:
1. **Threshold-crossing AEY at −4.5 × robust σ in 250–5000 Hz** as the primary daily quality metric and the default BCI feature.
2. **V_RMS per channel** computed in event-free windows.
3. **Top-2% V_pp** per session (Hughes 2021 convention).
4. **1 kHz impedance** per session.
5. **If single units required**: Kilosort4 with `nblocks=0` (or `do_correction=False`) per-shank; consensus with MountainSort5; UnitRefine for automated curation (with caveat: small validation set on V1/V4 NHP only, n=80 clusters, 96.0% balanced accuracy per Jain 2025).
6. **Do not run**: Bombcell, HerdingSpikes2, Kilosort4 with drift correction, SpyKING CIRCUS with shared-channel templates.
7. **Longitudinal reporting**: track all four mandatory metrics across sessions; apply Sponheim 2021 slope as a sanity baseline (−0.00058 fraction/day expected for NHP).

### NeuroNexus probes, 16 ch → Category 4
**Priority-ordered recommendation**:
1. **MountainSort 5** as the primary sorter.
2. **Wave_clus 3** as the secondary sorter (single-channel feature extraction per channel, then merge).
3. **Manual curation in Phy** with per-cluster ISI, refractory, and SNR review; PC-based isolation metrics defensible here.
4. **Metric stack**: V_RMS, AEY, SUA count, impedance at 1 kHz per session.
5. **Do not run**: Kilosort4 with drift correction; HerdingSpikes2; UnitRefine without retraining (training set is Neuropixels-dominant).
6. **For chronic recordings**: MoDT-style cluster-drift modeling within session; manual cross-session re-identification.

### NeuroNexus probes, 64 ch — depends on configuration
**Configuration A: linear 64-ch shank at 20 µm or 50 µm pitch → Category 2**.
- Primary sorter: Kilosort4.
- Curator: Bombcell + UnitRefine layered.
- Metric stack: V_RMS, AEY, DREDge drift trace.

**Configuration B: linear 64-ch shank at 200 µm pitch, or sparse multi-shank → Category 3**.
- Primary sorter: Kilosort4 with `nblocks=0` OR MountainSort5; consensus.
- Curator: UnitRefine + manual.
- Metric stack: V_RMS, AEY, MUA firing rate.

**The user should specify pitch and shank layout** for the 64-ch NeuroNexus probe. The configuration matters more than the channel count: a 64-ch linear at 50 µm pitch lives squarely in Category 2 and the Kilosort4/Bombcell/UnitRefine pipeline applies; a 64-ch linear at 200 µm pitch lives in Category 3 and inverts to MountainSort5 as a preferred sorter per the Liu 2025 JHU thesis benchmark on rhesus monkey recordings.

### Multi-category pipeline design notes
- Use a single SpikeInterface project with category-conditional branches: read_blackrock → categorize → branch on category → category-specific sort/curate → unified SortingAnalyzer for downstream metrics.
- Maintain a single sorting-free metric report (V_RMS, AEY, top-2% V_pp, impedance) reported identically across categories for cross-array comparability.
- For chronic data, version SortingAnalyzer outputs per session and store unit IDs separately per category — do not attempt cross-category unit tracking.
- Bombcell's MATLAB and new Python versions both expose threshold parameters; if Bombcell is run on Category 3/4 data, disable the non-somatic flag and inspect waveforms manually.

---

## 8 — Distinguishing Directly Supported, Derived, and Inferred Recommendations

- **Directly supported by Parts 1–3**: Kilosort4 as Category 2 default; MountainSort for tetrodes; AEY at −4.5 × robust σ as the BrainGate convention; Bombcell tuned for Neuropixels; HerdingSpikes2 fails at pitch > 60 µm.
- **Derived from integrating Parts 1–3**: composing Kilosort4-no-drift + UnitRefine + AEY for Category 1 single-unit pipelines (no single Part says this; it integrates Part 1's drift caveat, Part 2's UnitRefine validation footprint, and Part 3's AEY convention); using MS5 as a Category 3 default (Liu 2025 thesis evidence integrated with Part 1's "no single sorter dominates" finding).
- **Informed inferences (not validated)**: UnitRefine on chronic motor-cortex Utah arrays (only V1/V4 NHP validation exists, n=80); Bombcell on Kilosort4 outputs from chronic Neuropixels 2.0 across months (Bombcell was developed on within-session Neuropixels recordings, not cross-session chronic); MountainSort5 default for 64-ch NeuroNexus at 200 µm pitch (single-thesis evidence); MountainSort 4 as default carbon-fiber sorter (not directly verified from Guitchounts & Cox 2020 text).

---

## 9 — Caveats

1. The Hahn et al. 2025 BrainGate paper and the Jain et al. 2025 UnitRefine paper are both preprints as of May 2026 (medRxiv 2025.07.02.25330310 and bioRxiv 2025.03.30.645770 respectively); the peer-reviewed versions may revise numerical thresholds.
2. The Pachitariu 2024 Nat Methods Utah-array statement is a single sentence in the Discussion, not a benchmarked recommendation; KS4 has not been hybrid-benchmarked on Utah-array data.
3. Bombcell remains pre-publication ("manuscript under preparation" on the Zenodo entry); the threshold conventions may change.
4. SpikeForest has not been updated since 2020 and does not benchmark Kilosort4 or MountainSort5 (Magland & Soules 2025 eLife reviewed preprint 110170 explicitly notes this).
5. Cross-session unit tracking (UnitMatch, DREDge-chronic, OnACID) is rapidly evolving in 2024–2026 and the recommendations above will need revisiting.
6. Several integration patterns recommended here have been demonstrated by single labs or single theses (Liu 2025 JHU; Power Pixels 2025) and have not been replicated independently.

---

## TL;DR

- **The correct pipeline depends categorically on probe geometry**: for Utah arrays (Category 1) the defensible 2026 stack is no sorter (threshold crossings at −4.5 × robust σ in 250–5000 Hz, BrainGate convention) for BCI decoding plus Kilosort4-with-`nblocks=0` for SUA; for Neuropixels-class probes (Category 2) it is Kilosort4 with default drift correction + Bombcell + UnitRefine layered; for sparse linear / multi-shank arrays > 16 ch (Category 3) it is Kilosort4-with-`nblocks=0` or MountainSort5 (run as a consensus) + UnitRefine; for tetrodes and microwires (Category 4) it is MountainSort or Wave_clus 3 / Combinato + manual + PC-based isolation metrics.
- **The four-metric reporting standard from Part 3 — V_RMS, AEY at −4.5 × σ, top-2% V_pp, 1 kHz impedance — is the only quality scaffold that ports across all four categories** and should be reported per session per channel regardless of which sorter and curator are used; Kilosort4's drift module, Bombcell's full ruleset, HerdingSpikes2, DREDge cross-session motion correction, and PC-based isolation metrics are each defensible in only one or two of the four categories.
- **For the user's specific hardware on Blackrock/Ripple acquisition**: 16- and 96-ch Utah arrays → Category 1 (the BCI threshold-crossing stack; Kilosort4-no-drift only if SUA is required); 16-ch NeuroNexus → Category 4 (MountainSort 5 + Wave_clus consensus + manual Phy); 64-ch NeuroNexus → ambiguous between Categories 2 and 3 — the user should report pitch and shank layout; if pitch ≤ 50 µm it is Category 2 (Kilosort4 + Bombcell + UnitRefine), if pitch ~ 200 µm or sparse multi-shank it is Category 3 (Kilosort4-no-drift or MountainSort5 + UnitRefine).
# Post-Sorting Curation for Extracellular Spike Sorting: A Comparative Reference

*Companion to the sorting-algorithms reference. Scope: rule-based curators, ML classifiers, quality-metric frameworks, manual GUIs, and cell-type classifiers — with formulas, thresholds, failure modes, and probe-specific guidance.*

---

## TL;DR

- **For SpikeInterface-based longitudinal Neuropixels pipelines**: layer (1) Bombcell or Allen-style threshold curation to kill noise/non-somatic units, (2) UnitRefine (random-forest, two-stage noise-vs-neural then SUA-vs-MUA) for SUA/MUA refinement, and (3) the SpikeInterface `qualitymetrics` module to attach per-unit scores for downstream filtering — keep manual review (Phy or SortingView) only for ambiguous/scientifically-critical units. UnitRefine reaches ~83% balanced accuracy vs human curators (Jain et al., bioRxiv 2025.03.30.645770) and Bombcell exposes interpretable thresholds you can lock across sessions for longitudinal consistency.
- **Metrics that matter most for longitudinal yield stability**: amplitude_median (µV), presence_ratio, drift_ptp/std/mad, sliding-RP contamination (Llobet 2022 / IBL), and per-channel SNR. Avoid PC-based metrics (isolation_distance, L-ratio, nn_*) as primary filters on Kilosort outputs — they depend on the sorter's PC features and are biased by template-matching artifacts; use them as secondary signals only.
- **Probe-type matters**: thresholds tuned on Neuropixels (e.g., Bombcell defaults amplitude_median ≥ 30 µV, snr ≥ 5, presence_ratio ≥ 0.7, rp_contamination ≤ 0.1) systematically over-reject low-density data; for **Utah arrays / NeuroNexus / tetrodes**, drop the amplitude floor, relax non-somatic shape rules (designed against Neuropixels somatic templates), and prefer UnitRefine with a probe-matched pretrained model or retrained classifier rather than threshold-based Bombcell defaults.

---

## Key Findings

1. **Two paradigms have converged**. Threshold-based (Bombcell, IBL, Allen ecephys, SpikeInterface defaults) and ML-classifier (UnitRefine) approaches both consume the same SpikeInterface `qualitymetrics`/`template_metrics` feature set. As of SpikeInterface 0.104, both Bombcell labels and UnitRefine labels are first-class functions in `spikeinterface.curation`, returning per-unit labels in a pandas DataFrame ("Automatic labeling units after spike sorting" tutorial, SpikeInterface 0.104 docs).
2. **Bombcell is the most mature interpretable curator**: 17 metrics, four-class output (good / MUA / noise / non-somatic), MATLAB + Python ports, validated on Neuropixels 1.0/2.0 + Kilosort; published as Fabre, van Beest, Peters, Carandini & Harris (Zenodo DOI 10.5281/zenodo.8172821, v1.7.0 Nov 2024; manuscript still in preparation as of GitHub README, May 2026).
3. **UnitRefine is the most general ML curator**. Authors: Anoushka Jain, Robyn Greene, Chris Halcrow, Jake A. Swann, Alexander Kleinjohann, Federico Spurio, Severin Graff, Alejandro Pan-Vazquez, Björn Kampa, Juergen Gall, Sonja Grün, Olivier Winter, Alessio Buccino, Matthias H. Hennig, Simon Musall (bioRxiv 2025.03.30.645770, Mar 2025). Random-forest classifiers trained on multi-curator labels generalize across Neuropixels, Utah arrays, wire bundles, mice/rats/mole-rats/macaques/humans. On a brain-wide dataset, "UnitRefine doubled single unit yield and improved behavioral decoding performance" (abstract verbatim).
4. **Allen Institute defaults (Siegle et al. 2021, *Nature* 592:86) remain the de-facto baseline**: per the original paper, filtering based on `ISI violations < 0.5`, `amplitude cutoff < 0.1`, and `presence ratio > 0.95`. These were tuned on Kilosort2 + Neuropixels 1.0 in passive visual cortex; Siegle 2021 yielded over 40,000 units passing quality control across more than 14 brain regions and 4 mouse lines (the often-quoted "~100,000" figure refers to pre-QC recorded neurons). They are well-documented to over-include MUA in higher-firing-rate regions and to depend on whether template-scaling or raw amplitudes are used.
5. **IBL pipeline** (figshare 19705522 v4 white paper) uses three orthogonal "bitwise" criteria: `slidingRP_viol == 1`, `noise_cutoff` Z-score test pass, and `amplitude_median ≥ 50 µV`. A unit is "good" iff all three pass; this is the criterion behind `clusters.metrics.label == 1`.
6. **Cell-type classification (C4, Beau et al. *Cell* 2025; Bombcell ephys-properties module) is a separate downstream step**, not curation. C4 reports >95% accuracy in cerebellum across labs/probes/species using a semi-supervised deep classifier on waveform + ACG statistics; it does not curate noise.

---

## Details

### 1. Rule-Based Automated Curators

#### 1.1 Bombcell (Fabre et al.)

- **What it does**: Inputs a Kilosort/SpikeInterface sorting + raw binary; computes 17 metrics per unit; outputs labels in {good, MUA, noise, non-somatic}. MATLAB live-script and Python (`pip install bombcell`, repo `Julie-Fabre/bombcell`) ports exist; the Python port is integrated into SpikeInterface as `spikeinterface.curation.bombcell_label_units(...)`.
- **Algorithmic mechanism**: Multi-step cascading thresholds.
  1. **Noise detection from waveform shape**: thresholds on `num_negative_peaks` (≤ 1), `num_positive_peaks` (≤ 2), `peak_to_trough_duration` (0.1–1.15 ms), `waveform_baseline_flatness` (≤ 0.5), `exp_decay` of spatial spread (0.01–0.1 µm⁻¹).
  2. **Non-somatic detection**: `main_peak_to_trough_ratio` < 0.8 and `peak_before_to_peak_after_ratio` < 3 and `peak_before_to_trough_ratio` thresholds — flags axonal/dendritic waveforms (positive-going first peak).
  3. **MUA vs SUA on remaining somatic units**: `num_spikes` > 300, `presence_ratio` > 0.7, `amplitude_median` ≥ 30 µV (|abs|), `snr` ≥ 5, `rp_contamination` ≤ 0.1, `amplitude_cutoff` ≤ 0.2, `drift_ptp` ≤ 100 µm.
- **Design intent**: Neuropixels 3A / 1.0 / 2.0, Kilosort outputs, SpikeGLX or OpenEphys. Striatum/cortex-tested. Optional `ep_helpers` module classifies striatal (MSN / FSI / TAN / UIN) or cortical (pyramidal / interneuron) cell types from waveform + ACG features (using FMAToolbox CCG via `mex -O CCGHeart.c`).
- **Failure modes**:
  - Non-somatic classifier flags valid axonal/dendrite-recorded units → for hippocampal/cerebellar work, set `param.hillOrLlobetMethod = 0` and consider disabling the non-somatic class.
  - Thresholds tuned for Neuropixels probe geometry; `exp_decay` spatial-decay metric is meaningless on tetrodes/Utah arrays (no continuous spatial axis) — defaults will reject many valid units.
  - `amplitude_median ≥ 30 µV` floor is too high for low-density arrays.
- **Validation**: No peer-reviewed validation study as of May 2026; validation is via reproducibility against expert manual curation in the Carandini/Harris/Bombcell tutorials and concordance with Allen Institute metrics. SpikeInterface 0.104 includes an `upset` plot widget that shows which metric combinations cause each failure label.
- **Integration**: SpikeInterface ≥ 0.104 ships `spikeinterface.curation.bombcell_label_units` and `bombcell_get_default_thresholds`. Works with any sorter SpikeInterface supports; default thresholds are Neuropixels-tuned.
- **Maintenance**: Active; v1.7.0+ on Zenodo; Python release announced June 2025 (Fabre @basal_gang on X/Bluesky, June 13 2025). Handles Kilosort4 output natively.

#### 1.2 Allen Institute `ecephys_spike_sorting` + AllenSDK defaults

- **Pipeline architecture**: post-Kilosort2 modules computing `firing_rate`, `presence_ratio`, `amplitude_cutoff`, `isi_violations` (Hill 2011), `isolation_distance`, `L-ratio`, `d'`, `nn_hit_rate`/`nn_miss_rate`, `silhouette_score`, `max_drift`, `cumulative_drift`, plus newer `isi_violations_corrected` (Llobet 2022).
- **Default thresholds** (Siegle et al., *Nature* 592:86, 2021): `isi_violations < 0.5`, `amplitude_cutoff < 0.1`, `presence_ratio > 0.95`. The downstream AllenSDK Visual Coding Neuropixels documentation describes the same three filters with default `presence_ratio > 0.95`.
- **Failure modes**:
  - **Amplitude-cutoff inflation**: when Kilosort `amplitudes.npy` (template-scaling factors) is used instead of raw waveform amplitudes, the cutoff is systematically much higher (AllenSDK docs explicitly warn: "Amplitude cutoffs computed from the template scaling factors … tend to be much higher than when using actual spike amplitudes extracted from the raw data. SpikeInterface uses amplitudes calculated from the raw data, but several large-scale electrophysiology surveys (such as those from the Allen Institute) use the template scaling factors").
  - PC-based metrics (isolation_distance, L-ratio, d', nn_hit/miss) are computed pairwise and reported as worst-case; Allen docs note these "tend to under- or over-estimate the degree of contamination when there are large firing rate differences between pairs of units".
  - Drift metrics (`max_drift`, `cumulative_drift`) require waveform-based depth estimation; can fail in low-channel-count probes.
- **Maintenance**: ecephys_spike_sorting (AllenInstitute/ecephys_spike_sorting) is feature-frozen in favor of the newer Allen Institute for Neural Dynamics pipeline (Siegle group), which uses SpikeInterface + Kilosort + UnitRefine (Magland & Soules 2025, *eLife* reviewed-preprint 110170, "Efficient and reproducible pipelines for spike sorting large-scale electrophysiology data").

#### 1.3 IBL spike sorting pipeline curation

- **Pipeline**: `int-brain-lab/ibl-sorter` (Kilosort2.5 backbone) + `ibllib.brainbox.metrics.single_units`. Defined in figshare 10.6084/m9.figshare.19705522 v4 white paper.
- **Per-unit decision** (`label = 1` ⇔ all three pass):
  1. `slidingRP_viol == 1` (sliding refractory period method, Llobet/IBL implementation; passes if ≥ 90% confident contamination < 10% at any tested RP in {1.25, 1.5, …, 10} ms).
  2. `noise_cutoff` passes: Z-score of low-amplitude bin (second-nonzero bin of amplitude histogram) against mean/std of upper-quantile bins; FAILS if `(cutoff > 5) AND (first_low_quantile > 0.1 · peak_bin_height)`.
  3. `amplitude_median ≥ 50 µV`.
- **Algorithm details** (from `ibllib/brainbox/metrics/single_units.py`):
  - `noise_cutoff`: 100-bin amplitude histogram, peak at `idx_peak`; high-quantile statistics from upper 50% of top half; `cutoff = (first_low_quantile − μ_high) / σ_high`.
  - `slidingRP_viol`: tests RPs at 0.25-ms-resolution bins; uses `poisson.ppf(0.1, λ = 0.1 · 2 · FR · RP · recDur)` as max allowed violations; passes if observed ≤ max at any tested RP.
- **Design intent**: Brain-wide Neuropixels 1.0 reproducibility across 30+ labs. Conservative: optimized for false-positive elimination across heterogeneous brain regions (including thalamus and macaque with short refractory periods).
- **Failure modes**: 50-µV amplitude floor is conservative and Neuropixels-specific; thalamic/midbrain neurons with brief RPs may need sliding-RP (already adopted).
- **Maintenance**: Active; ibl-sorter v1.7.0 used in 2024_Q2_IBL_et_al_BWM brain-wide map release.

#### 1.4 Siegle-lab / Allen Neural Dynamics pipeline (Magland & Soules 2025, *eLife* reviewed-preprint 110170)

Combines the Allen Siegle 2021 thresholds (default_qc tag) with UnitRefine (random-forest) labels, runs on Nextflow + Code Ocean + SpikeInterface. Quality-metric thresholds: `isi_violation_ratio < 0.5`, `amplitude_cutoff < 0.1`, `presence_ratio > 0.8`. Visualizations via Figurl/SortingView for remote curation.

### 2. Machine-Learning Curators

#### 2.1 UnitRefine (Jain et al., bioRxiv 2025.03.30.645770)

- **Architecture**: Cascading two-stage classifier — Stage 1 noise vs neural; Stage 2 SUA vs MUA on the neural units. Random forest is the recommended default after hyperparameter search across multiple model families. Feature set is the full SpikeInterface `qualitymetrics` + `template_metrics` extension (~50 features).
- **Features used** (per the preprint + SpikeInterface docs): amplitude_cutoff, amplitude_cv_median/range, amplitude_median, d_prime, drift_mad/ptp/std, firing_range, firing_rate, isi_violations_count/ratio, isolation_distance, l_ratio, nn_hit_rate, nn_miss_rate, noise_cutoff, noise_ratio, num_spikes, presence_ratio, rp_contamination, rp_violations, sd_ratio, silhouette, sliding_rp_violation, snr, sync_spike_2/4/8 + template metrics (exp_decay, half_width, peak ratios, recovery/repolarization slopes, spread, velocity, waveform_baseline_flatness).
- **Validation accuracy** (UnitRefine preprint):
  - Up to ~83% balanced 3-way (noise/MUA/SUA) accuracy on unseen Neuropixels recordings (mouse).
  - 87.4% balanced accuracy on rat hippocampus CA1 (Neuropixels 2.0 4-shank, n = 1062 clusters).
  - 81.0% on mole-rat Neuropixels 2.0 (n = 506 clusters).
  - Tested cross-modality on NHP V1/V4 Utah arrays (n = 80 clusters) and human intracranial epilepsy recordings.
  - Brain-wide application: doubled SUA yield and improved task-variable decoding.
- **Failure modes**:
  - As a supervised model, it inherits curator biases in training data; running an out-of-distribution model on, e.g., human epilepsy data when trained only on mouse Neuropixels can fail silently. Mitigation: SHAP-based interpretability notebook (provided in the repo) + GUI showing low-confidence clusters for active-learning relabeling.
  - PC-based features (isolation_distance, L-ratio, nn_*) require Kilosort-style PC outputs; on sorters without PCs (HerdingSpikes, Mountainsort5), some features fall back to NaN.
- **Maintenance**: Active (Buccino/Hennig/Musall labs, Hugging Face Hub model sharing). GUI shipped with the repo (`anoushkajain/UnitRefine`).
- **Integration**: `spikeinterface.curation.train_model` and `apply_sorting_curation` plus a Hugging-Face-hosted pretrained model. Single function call drops it into any SpikeInterface pipeline.

#### 2.2 Other ML curators

- **A-FLOATer, sua_classifier, noise_neural classifier**: predecessors / inspirations for UnitRefine; sua_classifier and noise_neural were standalone scikit-learn classifiers used by individual labs (Musall, Buccino) before being unified under UnitRefine. They are effectively deprecated for new work; UnitRefine is the consolidated successor.
- **Phy auto-curation**: Phy 2.0 GUI itself has no built-in auto-curation classifier; it consumes external `cluster_group.tsv` labels (good/mua/noise) and lets users edit them. Some auto-merge heuristics exist as Phy plugins but are community-maintained.

#### 2.3 C4 — Cell Class Classifier (Beau, Herzfeld, Naveros, Hemelt et al., *Cell* 2025; bioRxiv 2024.01.30.577845)

- **Not a curation tool**; a downstream cell-type identifier. Semi-supervised deep classifier (variational-autoencoder-based) trained on optogenetically + pharmacologically identified cerebellar cells (Purkinje, MLI, Golgi, mossy fiber).
- Reports >95% accuracy with cross-lab, cross-probe, cross-species generalization (mouse Neuropixels → macaque flocculus). Confidence threshold typically 2 (log-likelihood units) to exclude ambiguous units.
- Database: UCL figshare `Cerebellum_cell_type_collaboration_database` (DOI 23702850, posted 2025-01-28).
- **Caveat**: Only validated for cerebellar cell types; do not apply outside cerebellum. Use *after* curation (it expects clean SUA inputs).

### 3. Quality Metrics — Deep Dive

#### 3.1 Contamination / Type-I (false-positive) metrics

**ISI violations (Hill et al., *J Neurosci* 31:8699, 2011)**
- Definition: count of inter-spike intervals < refractory period `t_r`.
- SpikeInterface `isi_violations_ratio`: `(N_v · T) / (2 · N_s² · (t_r − t_min))`, an estimate of contaminating spike rate relative to true rate (assumes contaminating spikes are Poisson and independent of unit).
- IBL `contamination` formula (Hill 2011):
  ```
  F_p = N_v · (T_max − T_min) / (2 · N_s² · (t_r − t_min))
  ```
- **Failure modes**:
  - Breaks for highly contaminated units (F_p > 1 or complex; see Llobet 2022 Section 4.1).
  - Sensitive to choice of `t_r` (default 1.5 ms is too long for thalamus/macaque; Llobet 2022 documents shorter RPs).
  - Anti-correlated contamination (e.g., from gap-junction-coupled cells) under-estimates.
- **Allen default threshold**: < 0.5. **IBL**: replaced by slidingRP_viol.

**Sliding refractory period (Llobet, Wyngaard & Barbour, bioRxiv 2022.02.08.479192; IBL implementation)**
- Tests multiple candidate refractory periods (1.25–10 ms) and finds the minimum contamination level for which we have ≥ 90% confidence the unit is *less* contaminated than that level. Returns the worst-case contamination (continuous metric) or binary pass/fail.
- SpikeInterface `compute_sliding_rp_violations` returns the minimum contamination at 90% confidence.
- **Strength**: no need to pre-specify `t_r`; robust across brain regions and species (Steinmetz lab `slidingRefractory` repo).
- **Failure mode**: low-firing-rate units lack statistical power → defaults to NaN/fail.

**Llobet `rp_contamination`** — closed-form alternative to Hill, more accurate at low contamination but undefined at high contamination. SpikeInterface implements both; Bombcell defaults to Hill but offers Llobet via `param.hillOrLlobetMethod = 0`.

**Isolation distance (Harris et al. *Neuron* 32:141, 2001; Schmitzer-Torbert et al. *Neuroscience* 131:1, 2005)**
- For cluster C of size n_C, compute squared Mahalanobis distance D²_{i,C} of all non-cluster spikes from the cluster center in PC space. Isolation distance = n_C-th smallest D² (i.e., distance at which as many out-cluster as in-cluster spikes are included).
- Higher = better isolated. Common threshold (tetrode literature): ≥ 15 (Yoshida et al., Schmitzer-Torbert 2005).
- **Failure mode**: undefined when n_C > total non-cluster spikes (rare); scale depends on PC dimensions and sorter; very sensitive to cluster size imbalance.

**L-ratio (Schmitzer-Torbert et al. 2005)**
- `L(C) = Σ_{i ∉ C} [1 − CDF_{χ²,df}(D²_{i,C})]`; `L-ratio = L(C) / n_C`.
- Lower = better isolated. Tetrode threshold often < 0.05 (Schmitzer-Torbert 2005; Nakamura et al. striatum studies).
- Schmitzer-Torbert et al. found "Lratio outperformed Isolation Distance. Isolation Distance was not sensitive to the presence of the noise unless this small noise mode contained at least as many points as the cluster" (Neuroscience 131:1, 2005).

**d-prime** (Hill 2011): linear discriminant between cluster and surrounding spikes in PC space. Higher = better isolated. Less used than L-ratio because it assumes Gaussianity.

**Nearest-neighbor isolation & noise overlap (Chung et al. *Neuron* 95:1381, 2017; Siegle adaptation)**
- `nn_isolation`: for cluster C, draw equal-size sample A from C and B from outside C in PC space; for each spike in A∪B, find its k nearest neighbors; isolation = fraction of A's neighbors that are in A (and B's in B). Higher = better.
- `nn_noise_overlap`: noise cluster constructed from random non-spike segments at the same channels; same procedure to measure how confusable the unit is with noise. Lower = better.
- Threshold (Chung 2017): nn_isolation > 0.9 and nn_noise_overlap < 0.1 suggested for SUA.
- **Failure mode**: requires `radius_um` set appropriately for probe (SpikeInterface default 100 µm — wrong for tetrodes); slow on large datasets.

**SNR**
- `SNR = |peak_amplitude_template| / (median absolute deviation of noise on peak channel)`. SpikeInterface default uses MAD-based noise on the channel of the template's extremum.
- Bombcell default ≥ 5; some pipelines use ≥ 3.
- **Failure mode**: noise estimation includes spikes (inflating noise) unless explicitly excluded; SD-ratio metric was added to address this.

**SD-ratio**: SD of unit's spike amplitudes / SD of background voltage at the same channel. Correctly identifies merged units (high SD) and drifting units.

**Synchrony metrics** (`sync_spike_2`, `_4`, `_8`): fraction of spikes that coincide with ≥ N other units within ±0.5 ms. High values flag artifacts/cross-talk.

#### 3.2 Completeness / Type-II (false-negative) metrics

**Presence ratio**
- Divide recording into 100 bins; fraction of bins containing ≥ 1 spike (or above mean-FR threshold).
- Allen Siegle 2021 default > 0.95 (Nature 592:86); Bombcell > 0.7; IBL no explicit threshold.
- **Failure mode**: punishes truly state-dependent neurons (e.g., place cells active only during running) — Allen docs explicitly warn against using presence_ratio when "highly selective spiking patterns" are expected.

**Amplitude cutoff (Allen)**
- Fit Gaussian to spike-amplitude histogram and estimate fraction of distribution truncated below detection threshold. Returns ∈ [0, 0.5] (0.5 = peak at lowest bin → cannot estimate).
- Allen default < 0.1; Bombcell < 0.2 for MUA.
- **Critical caveat**: AllenSDK docs note "Amplitude cutoffs computed from the template scaling factors (amplitudes.npy in the Kilosort output) tend to be much higher than when using actual spike amplitudes extracted from the raw data." Always document which amplitude source you use across sessions for longitudinal consistency.

**Noise cutoff (IBL)** — see §1.3.

**nn_miss_rate** (Chung-style): fraction of cluster spikes that are isolated as nearest neighbors of noise samples. Higher = more spikes missed.

#### 3.3 Drift metrics (SpikeInterface; Siegle origin)

- `drift_ptp`: peak-to-peak of median unit depth across time bins.
- `drift_std`: SD of median depth across time bins (recording-duration-invariant).
- `drift_mad`: MAD of median depth (recording-duration-invariant, outlier-robust).
- Requires `spike_locations` extension (SpikeInterface) → needs probe geometry; not meaningful on tetrodes or single-shank low-density probes.
- Bombcell default: drift_ptp ≤ 100 µm (Neuropixels-scale).
- SpikeInterface docs: "`max_drift` is calculated with the peak-to-peak, so it's been renamed `drift_ptp`" and explicitly note that `cumulative_drift` is "very sensitive to the number of bins (and hence the recording duration)" while drift_std/mad are not — for **longitudinal pipelines, prefer drift_std and drift_mad to avoid duration-dependent biases**.

#### 3.4 Waveform-shape metrics (template_metrics extension)

- **num_negative_peaks / num_positive_peaks**: noise-classification primary signal in Bombcell (real somatic spikes have one trough and ≤ 2 peaks).
- **peak_to_trough_duration**: 0.1 – 1.15 ms for real spikes (Bombcell default range); narrow waveforms < 0.4 ms typical for fast-spiking interneurons.
- **half_width**: full width at half-minimum of trough.
- **peak_after_to_trough_ratio**, **peak_before_to_peak_after_ratio**, **main_peak_to_trough_ratio**: non-somatic vs somatic separation (Bombcell uses thresholds 0.8 and 3.0).
- **waveform_baseline_flatness**: SD of the pre-spike baseline relative to spike amplitude; high values → noise.
- **exp_decay**: exponential spatial-decay constant of amplitude across channels. Requires multi-channel data; meaningless on tetrodes.
- **spread**: number of channels with > 0.5 × peak amplitude.
- **recovery_slope, repolarization_slope, velocity_above/below**: shape descriptors used by C4 and UnitRefine; have biophysical interpretations (axonal propagation velocity from `velocity_above/below`).

### 4. Manual Curation Tools

| Tool | Strengths | Weaknesses | Best paired with |
|---|---|---|---|
| **Phy 2.0** (Rossant et al.) | Full Kilosort feature set, fast GPU rendering, scriptable plugins, merge/split | Local desktop-only, dataset-bound, no cloud collaboration | Kilosort/Kilosort2/2.5/3/4 outputs |
| **SortingView/Figurl** (Magland & Soules, Flatiron) | Web-based, shareable links via kachery cloud, JSON curation format | Slower than Phy on local raw data, requires kachery-cloud auth | SpikeInterface, AIND pipelines |
| **spikeinterface-gui** | Native SpikeInterface, multi-backend (Qt + sortingview), reads `SortingAnalyzer` | Newer, fewer expert curators trained on it | SpikeInterface 0.100+ workflows |
| **Neuroscope** (Buzsáki lab legacy) | Lightweight, good for tetrodes | No template-based views; legacy | Tetrode / linear-probe pipelines |

**Integration pattern (recommended)**: Run automated curation (Bombcell + UnitRefine) → export to Phy or SortingView for *targeted* manual inspection of disagreement units → write back JSON curation that SpikeInterface ingests with `apply_sorting_curation`. SpikeInterface's JSON curation format (`merges + deletions + manual tags`) keeps the sorting output immutable and the curation reproducible.

### 5. Cell-Type Classification

| Tool | Method | Target | Reported accuracy |
|---|---|---|---|
| **C4 (Beau et al. 2025)** | Semi-supervised VAE + classifier on waveform + ACG | Cerebellar PC/MLI/Golgi/MF | >95% with confidence threshold 2 |
| **Bombcell `+bc.ep`** | Threshold rules on waveform + ACG | Striatal (MSN/FSI/TAN/UIN), cortical (pyr/IN) | Not formally benchmarked |
| **Phy templateGUI** | Manual labeling of cluster_group | Any | Curator-defined |

**Cell-type classification ≠ curation**. Use only after noise/non-somatic units removed and SUA identified.

---

## Decision Table — Curation Method by Use Case

| Method | Sorter pairings | Probe types | Validation strength | Compute | Maintenance | Key caveats |
|---|---|---|---|---|---|---|
| **Bombcell (rule-based)** | Kilosort 2/2.5/3/4, SpikeInterface sorters | Neuropixels 1.0/2.0/3A (designed); Utah/NeuroNexus only with retuned thresholds | Moderate: tutorials + community use, no peer-reviewed accuracy study (manuscript in prep) | Fast (CPU, minutes per session) | Active (v1.7.0 Nov 2024, Python June 2025) | Tuned for somatic Neuropixels; `exp_decay` meaningless on tetrodes; non-somatic class can be overzealous |
| **UnitRefine (ML)** | Any SpikeInterface-supported sorter | Any (Neuropixels, Utah, wire bundles, tetrodes; pretrained models per probe) | Strong: bioRxiv 2025, ~83% balanced acc 3-way, validated across 5 species and 3 probe types | Moderate (random-forest CPU; training ~minutes) | Very active (Buccino/Musall, Hugging Face) | Inherits curator bias; needs probe-matched pretrained model or retraining for OOD data |
| **Allen ecephys (rule-based)** | Kilosort2 (designed) | Neuropixels 1.0 (designed) | Strong for original use: Siegle 2021 yielded >40,000 QC-passing units across 14+ regions and 4 mouse lines | Fast | Frozen — superseded by AIND/SpikeInterface pipeline | template-amp vs raw-amp ambiguity in `amplitude_cutoff`; PC metrics worst-case-paired |
| **IBL (rule-based)** | iblsorter (KS2.5) | Neuropixels 1.0 (designed) | Strong: brain-wide map, slidingRP from Llobet 2022 | Fast | Active (BWM 2024_Q2 release uses ibl-sorter 1.7.0) | 50-µV amp floor strict; designed for FP-elimination across labs |
| **SpikeInterface `qualitymetrics`** | Any | Any | Library of metrics; not itself a curator | Fast–moderate (PC metrics slow) | Very active (0.104, 2025) | User chooses thresholds; PC metrics need PCs |
| **Phy (manual)** | Kilosort family, SpyKING Circus | Neuropixels primary; works on others | Gold standard for expert curation, but Buccino et al. (*eLife* 9:e61834, 2020) report two curators agreed on 400/525 = 76% of Kilosort2 clusters (UnitRefine preprint citation) | Slow (hours per session) | Maintained (Rossant) | Slow, subjective, GPU+SSD required |
| **SortingView** | Any | Any | View/curate only | Cloud-dependent | Active (Magland 2025) | Requires kachery-cloud auth; slower for very large datasets |
| **C4 (cell type)** | Any | Neuropixels validated; cerebellum only | >95% acc within cerebellum (Beau et al. 2025, *Cell*) | Moderate (deep model inference) | Active (UCL Hausser/Medina labs) | Not curation; cerebellum-only |

---

## Integration Guidance

### Recommended layered pipeline (SpikeInterface 0.104+ baseline)

```
RAW → preprocess → motion correction → sort (Kilosort4 / etc.) → SortingAnalyzer
  → compute_quality_metrics (full set: contamination, completeness, drift, waveform)
  → Bombcell labels (interpretable thresholds, locked across sessions)
  → UnitRefine labels (ML, pretrained or retrained for your probe/species)
  → reconcile: keep units where BOTH agree "good/SUA"
  → flag disagreements for manual review in SortingView (or Phy export)
  → write back JSON curation (merges + deletions + tags)
  → final filtered SortingAnalyzer for downstream analysis
```

### How to layer when methods disagree

- **Bombcell good + UnitRefine SUA** → high-confidence single unit. Use without manual review.
- **Bombcell good + UnitRefine MUA** (or vice versa) → tag for manual inspection. Common cause: UnitRefine sees subtle ISI/amplitude features that the discrete Bombcell thresholds miss.
- **Bombcell noise/non-somatic + UnitRefine SUA** → almost always a non-somatic or low-amplitude unit. For hippocampus/cerebellum where dendritic/axonal recordings are common, prefer UnitRefine's call. For striatum/cortex, prefer Bombcell.
- **Both reject** → drop.

### When manual review is still mandatory

1. **Putative optotagged units** for cell-type studies (do not delegate to automated curation).
2. **Boundary units in critical analyses** (e.g., decoder weight outliers).
3. **First N sessions of a new probe / lab / animal model**, to calibrate threshold/model choice.
4. **Drift events** flagged by drift_ptp > probe-pitch threshold (e.g., > 30 µm on Neuropixels 1.0).

### Longitudinal / cross-session yield consistency

- **Lock thresholds across sessions** — do not re-fit Bombcell defaults per session. Re-run UnitRefine with the *same* pretrained model across sessions; only retrain when probe/species changes.
- **Track unit-yield metadata per session**: total units, % good, % MUA, % noise, mean amplitude_median, mean drift_std. Drift across sessions in these summaries flags rig/probe issues.
- **For chronic recordings**, prefer drift_std/drift_mad over drift_ptp (recording-duration invariant).
- **Amplitude source consistency**: always use raw waveform amplitudes (SpikeInterface default) and document this — switching between template-scaling and raw amplitudes mid-study breaks amplitude_cutoff comparability (AllenSDK warning, above).
- **Refractory-period method consistency**: pick Hill or Llobet/slidingRP and keep it for the whole study.

### Probe-specific tuning

| Probe | Recommended curation stack | Threshold/parameter notes |
|---|---|---|
| **Neuropixels 1.0/2.0** | Bombcell + UnitRefine (mouse pretrained) | Default Bombcell thresholds work; drift metrics meaningful |
| **NeuroNexus linear / multi-shank** | UnitRefine (retrained on probe-matched data) + manual Allen-style thresholds | Bombcell `exp_decay`/`spread` may need disabling on short-span shanks; lower amplitude_median floor to ~20 µV |
| **Utah arrays** | UnitRefine (Utah-pretrained available) + ISI/SNR/amplitude_cutoff | Disable Bombcell spatial-decay & multi-channel waveform shape metrics; UnitRefine validated by Jain 2025 on Utah arrays |
| **Tetrodes (Buzsáki-style)** | L-ratio / isolation_distance (Schmitzer-Torbert thresholds: ID > 15, L-ratio < 0.05) + ISI < 0.5% | Disable Bombcell; PC-space metrics are the historical standard here; UnitRefine can work but needs retraining on tetrode-labeled data |
| **MEAs (in vitro)** | SpikeInterface qualitymetrics + manual; ISI + SNR + presence_ratio | Drift metrics rarely needed; high-channel-count MEAs (3Brain etc.) benefit from UnitRefine |

---

## Recommendations

1. **Default pipeline** (production, longitudinal Neuropixels): SpikeInterface 0.104+ → Kilosort4 → `compute_quality_metrics(metric_names=all)` → Bombcell labels with locked thresholds → UnitRefine (mouse-pretrained random forest) → reconcile → SortingView for disagreements. Document thresholds and UnitRefine model hash in repo per session.
2. **For Utah arrays**: skip Bombcell; use UnitRefine with the Utah-trained model (or train your own from a small expert-labeled batch using `spikeinterface.curation.train_model`).
3. **For tetrodes**: use SpikeInterface qualitymetrics with PC-based metrics (L-ratio < 0.05, isolation_distance > 15, ISI < 0.5%) plus manual curation in Phy/Neuroscope. UnitRefine is not yet validated for tetrodes.
4. **Re-evaluation triggers**: if cross-session unit yield drops > 25% week-over-week, or if % "noise" labels increases > 10% between sessions, recompute drift metrics and review preprocessing — the curation rules are probably correct; the data quality changed.
5. **Always store**: full per-unit quality-metrics table (SpikeInterface CSV/Parquet) regardless of which curator label is used. This makes it trivial to revisit decisions later or apply alternative thresholds without re-sorting.
6. **Pair the curation step with a manual sanity check** on a small held-out fraction of units per session (e.g., 5%); track curator-vs-automated agreement over time to detect model drift.

---

## Caveats

- **Bombcell has no peer-reviewed publication as of May 2026**; cite the Zenodo DOI (10.5281/zenodo.8172821) and the GitHub repo. Performance characterizations come from talks (UCL Neuropixels Course 2023/2024), the lab's open-neuroscience blog post, and community use.
- **UnitRefine accuracy ~83%** is balanced 3-way accuracy on the held-out brain-wide Neuropixels test set; per-recording numbers vary 75–87%. It is *not* better than the best human curator on individual hard units; it matches median curator accuracy at vastly greater throughput.
- **Inter-rater human agreement is itself limited**: Buccino et al. (*eLife* 9:e61834, 2020) report that two expert curators agreed on 400/525 = 76% of Kilosort2 clusters (cited in the UnitRefine preprint as the empirical ceiling for automated-curation benchmarks).
- **PC-based metrics** (isolation_distance, L-ratio, nn_*) depend on the sorter's PC features and are pairwise "worst-case" in Allen pipelines — Allen docs explicitly note these "tend to under- or over-estimate the degree of contamination when there are large firing rate differences between pairs of units". Use as secondary, not primary, filters on template-matching sorter outputs.
- **Sliding refractory period** outperforms fixed-t_r ISI metrics for cross-region work, but for low-firing-rate units it returns NaN/fail — pair with a firing-rate floor.
- **Cell-type classifiers (C4, Bombcell ephys-properties) are domain-specific**: C4 is cerebellum, Bombcell `+bc.ep` is striatum/cortex. Do not export across regions.
- **All threshold defaults reported here are from currently-shipping software versions** (Bombcell v1.7+, SpikeInterface 0.104, AllenSDK 2.0, iblsorter 1.7.0); thresholds change between releases — pin software versions in your pipeline and document in the analysis README.
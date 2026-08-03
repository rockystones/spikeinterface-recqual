# Sorting-Free Metrics for Offline Longitudinal Tracking of Extracellular Recording Quality (Part 3 of 3)

## TL;DR

- **For chronic implants, the most reproducible longitudinal recording-quality scaffold is a four-metric core computed *before* spike sorting:** (i) noise floor V_RMS estimated from pre-event samples or MAD; (ii) Active Electrode Yield (AEY) = fraction of electrodes with threshold-crossing rate ≥ 2 Hz at −4.5 × robust σ (the BrainGate convention); (iii) per-electrode unsorted peak-to-peak voltage on the top 2 % of snippets (Hughes 2021 convention); and (iv) 1 kHz electrode impedance.
- **Sorting-free metrics complement, not replace, sorter-based QC:** they detect dead/degrading channels and noise-floor drift that sorters silently absorb, while Bombcell/UnitRefine (Part 2) catch failures of single-unit identity that sorting-free metrics are blind to.
- **For BCI-class longitudinal cohorts the evidence is now strong enough to set quantitative reporting standards:** Sponheim et al. 2021 (55 arrays, 9 years, 6,132 sessions; linear slope −0.00058 yield-fraction/day ≈ −2 %/30 d), Hahn et al. 2025 BrainGate medRxiv (20 arrays, 14 participants, 2,319 sessions; 35.6 % mean active-electrode fraction, 7 % decline over 2.8 years mean enrollment, max 7.6 years), and Hughes et al. 2021 (1,500-day single-subject, top-2 % V_pp convention) define the de facto field standards.

---

## Key Findings

1. **The TC-rate yield metric has converged on a specific definition.** BrainGate (Hahn et al. 2025 medRxiv 2025.07.02.25330310): ≥ 2 Hz at −4.5 × robust σ, bandpass 250–5000 Hz, linear regression referencing. Hughes 2021 (Pittsburgh): −4.5 × V_RMS, ≥ 1.67 Hz, ≥ 30 µV V_pp inclusion floor, 48-sample (1.6 ms) snippets starting 11 samples before crossing. Sponheim 2021: −5.25 × V_RMS (moved to −4.5 from day 565 for one participant), ≥ 14 events, SNR > 1.5. Christie et al. 2015 (J Neural Eng 12:016009) showed that thresholds in the −3 to −5 × V_RMS range produce decoding within ~5 % classification accuracy of each other (Naïve Bayes accuracy change ~5 %, correlation Δ = 0.015), so threshold choice is not critical for population decoding but is critical for cross-study yield comparability.

2. **V_RMS estimation varies by lab.** Downey et al. 2018 (J Neural Eng 15:046016) use the 5–10 samples immediately pre-crossing to avoid spike contamination. SpikeInterface `get_noise_levels` uses MAD-based estimator on random chunks (σ̂ = MAD / 0.6745). Both are valid; reports must specify which. The chunk-length sensitivity is non-trivial: SpikeInterface issue #4367 documents that "the noise levels vector varies, but in the longer file values are sometimes as much as 20 % higher than the shorter file," which then changes peak-detection thresholds and downstream motion estimation.

3. **Unsorted V_pp is more longitudinally stable than sorted-unit count.** Chestek 2011, Downey 2018, Hughes 2021, Sponheim 2021, and BrainGate 2025 all report TC yield declining far more slowly than well-isolated single units. Trautmann et al. 2019 (Neuron 103:1064) demonstrated via random projections that population dynamics from unsorted TC are nearly indistinguishable from those from sorted units, and Christie 2015 quantified the equivalence (Naïve Bayes Δ ≈ 5 % accuracy, Δ correlation = 0.015).

4. **Impedance is gold-standard hardware health but non-monotonic with yield.** Hughes 2021: Pt-tipped motor arrays median 447.5 kΩ pre-implant → 1,396 kΩ at day 7 (post-implant interface formation), then declining over years; SIROF-tipped sensory arrays 74.5 kΩ pre-implant. Lewis et al. 2024 (Adv Healthcare Mater 13:2303401) showed that extremely low Z can flag insulation failure rather than improved tissue coupling on PEDOT-coated flexible probes.

5. **LFP metrics are the most underused longitudinal stability signal.** Senzai, Fernandez-Ruiz & Buzsáki 2019 (Neuron 101:500) used 500–2000 Hz LFP power and CSD for laminar identification. DREDge (Windolf et al. 2025 Nat Methods, doi:10.1038/s41592-025-02614-5) and MEDiCINe (Watters, Buccino & Jazayeri 2025 eNeuro 12:ENEURO.0529-24.2025) make LFP / AP-band motion estimation routine without sorting.

6. **Network-level sorting-free metrics** (pairwise MUA correlation, population envelope, correlation-matrix similarity across sessions) are emerging but lack formal longitudinal validation. Trautmann 2019 provides the theoretical basis via random projections.

7. **Discovered eleventh family — Spiking-Band Power (SBP).** Even-Chen et al. 2020 (Nat Biomed Eng 4:984) and Nason et al. 2020 (Nat Biomed Eng 4:973) showed band-limited (300–1000 Hz) envelope power can predict movement similarly to TCR at 30 ksps. Meets all three discovery criteria (distinct physical quantity, ≥ 2 independent studies, different computational pipeline) and is elevated to Family 11.

---

## Details — Sorting-Free Metric Families

### Family 1 — Threshold-Crossing-Based Metrics

**A.** Whether functional MUA is detectable above the local noise floor at each electrode — the most direct sorter-free proxy for "is this electrode still alive."

**B.** Threshold $T_i = \alpha\hat\sigma_i$, α ∈ {−3, −3.5, −4.5, −5.25}. Rate $r_i = N_i / T_{\text{rec}}$. Yield $\mathrm{AEY} = N_{\text{ch}}^{-1}\sum_i \mathbf{1}(r_i > r_{\min})$, with $r_{\min} = 2$ Hz (BrainGate) or 1.67 Hz (Pittsburgh).

**C.** Chestek, Gilja, Nuyujukian et al., J Neural Eng 8:045005 (2011), 382 days post-implant in three rhesus macaques with Utah arrays in motor cortex. Validated by Christie et al. 2015, Hughes et al. 2021, Sponheim et al. 2021, Hahn et al. 2025.

**D.** Excellent on Utah, Neuropixels, NeuroNexus, tetrodes. Weak on ECoG (signal is largely LFP).

**E.** Large baseline shifts (movement, chewing) produce false stability; amplifier saturation produces false stability (rate caps at the high end); 60 Hz line noise inflates rates if not notched; CAR with too few channels generates correlated artifacts that mimic spikes.

**F.** Highly sensitive to α and to filter band. The Pittsburgh group changed from a 4th-order 250 Hz HP to a 1st-order 750 Hz HP at day 200 of the Hughes 2021 dataset and observed a discontinuity in noise/SNR metrics.

**G.** Real-time feasible on any FPGA / DSP. Storage = timestamps only (kB/min). Standard real-time output of Blackrock NSP, Ripple Grapevine, Intan/Open Ephys.

**H.** `spikeinterface.sortingcomponents.peak_detection.detect_peaks(method='by_channel'|'locally_exclusive', detect_threshold=5, peak_sign='neg')`; noise floor by `si.get_noise_levels` (MAD-based).

**I.** Hahn et al. 2025 (BrainGate, 14 participants, 20 arrays, 2,319 sessions): 35.6 % mean active-electrode fraction at the −4.5 × robust σ / ≥ 2 Hz definition; ~7 % decline over 2.8 yr mean enrollment (max 7.6 yr); substantial inter-array variability — some declined sharply within year 1 (S2, S3, T2), some increased (T7, T8), most stable or gradual (T5, T6, T10, T11). Sponheim et al. 2021 (55 arrays in 17 NHPs + 2 humans, 6,132 sessions over ~9 years): ~70 % of arrays had ≥ 40 % yield in first 3 mo, ~50 % at 12 mo, ~10 % at 36 mo; linear regression slope = −0.00058 yield-fraction/day ≈ −2 %/30 d; average lifespan in dataset = 622 days (range 44 d to > 3000 d); 16/55 arrays maximum yield > 90 %.

**J.** AEY consistently exceeds sorted-unit count. The gap reflects multi-unit channels where the sorter cannot cleanly isolate individual neurons but task-relevant population information remains.

### Family 2 — Unsorted Amplitude Metrics

**A.** The largest waveforms an electrode is producing, without identity assignment. Drops indicate neuron loss, electrode-tissue distance increase from glial encapsulation, or electrode degradation.

**B.** Per-event V_pp = max − min over a snippet (48 samples / 1.6 ms in BrainGate / Pittsburgh). Top-2 % V_pp (Hughes 2021): mean V_pp of the 2 % of snippets per electrode per session with the largest amplitudes. Unsorted multi-unit SNR: $\mathrm{SNR}_{\mathrm{MU}} = V_{pp,\text{top2}} / V_{\mathrm{RMS}}$.

**C.** Suner et al. 2005 (IEEE TNSRE 13:524) for SNR tracking in macaque motor Utah arrays. Hughes, Flesher, Weiss et al. 2021 (J Neural Eng 18:045012) formalized the top-2 % convention: "The largest 2 % of the snippets for each electrode were averaged and the peak-to-peak voltage was calculated. If the firing rate of all the snippets on any electrode was less than 1.67 Hz or the peak-to-peak voltage of the averaged signal was less than 30 µV, the electrode was excluded from analysis."

**D.** Same as Family 1.

**E.** Amplifier clipping inflates max V_pp; reference noise (broken bone-screw etc.) inflates V_pp uniformly across channels — easy to flag because all channels move together; stim-artifact bleed-through can dominate the top 2 %.

**F.** Filter cut-on changes V_pp by 20–40 % (a 250 Hz HP preserves more spike foot than a 750 Hz HP). Always report filter band when reporting V_pp.

**G.** Low — one pass per snippet.

**H.** `extract_waveforms` + user-side V_pp percentile. Bombcell exposes per-unit V_pp but not per-channel unsorted V_pp.

**I.** Hughes 2021 (Fig. 1c) reports median and top-2 % V_pp trajectories over 1,500 days; SIROF-sensory electrodes preserved high V_pp longer than Pt-motor. Perge et al. 2013 (J Neural Eng 10:036004) tracked intra-day V_pp fluctuations predicting decoder degradation.

**J.** Top-2 % V_pp correlates strongly with best-isolated-unit V_pp; divergence (high top-2 % V_pp, no sorted unit) flags single-neuron waveform variability that sorters split into transient clusters — a classic over-splitting signature.

### Family 3 — Noise-Floor Metrics

**A.** Background voltage variability in the absence of spikes; sets every SNR denominator and determines every event-detection threshold.

**B.** $V_{\mathrm{RMS}} = \sqrt{N^{-1}\sum_k x_k^2}$ on zero-mean filtered signal. Pre-event V_RMS (Downey 2018): same formula on 5–10 pre-crossing samples. $\hat\sigma_{\mathrm{MAD}} = \mathrm{MAD}(x) / 0.6745$ (SpikeInterface, Kilosort, most modern sorters). Spectral noise floor: PSD above 0.8 × Nyquist > 0.02 µV² / Hz triggers the IBL "noisy" flag.

**C.** Downey, Schwed, Chase et al. 2018 (J Neural Eng 15:046016) for pre-event V_RMS in human BCI users. The IBL coherence + PSD bad-channel detector is folded into SpikeInterface as the `coherence+psd` method.

**D.** All probes. Particularly critical on Neuropixels where a single bad channel corrupts CMR if not detected first.

**E.** A broken reference inflates V_RMS uniformly across all channels — detectable by cross-channel covariance of V_RMS. CMR with > 5 % bad channels included in the average re-injects noise into "good" channels. MAD estimators are robust to spikes but inflated by line noise unless notched first.

**F.** Filter cut-on changes V_RMS by 30–50 %; reference scheme by 20–40 %; sampling rate by ~10 %. Always report all three.

**G.** Trivial single-pass.

**H.** Native: `si.get_noise_levels(return_scaled=True)` returns per-channel MAD-based σ in µV. `si.preprocessing.detect_bad_channels(method='coherence+psd', std_mad_threshold=5, psd_hf_threshold=0.02, dead_channel_threshold=-0.5, noisy_channel_threshold=1.0, n_neighbors=11)` returns {good, noise, dead, out}. Run BEFORE CMR.

**I.** Downey 2018 tracked pre-event V_RMS over 200+ sessions in human BCI. Luo et al. 2020 (eLife 9:e59716): "Explanted probes displayed a small increase in noise compared to unimplanted probes, but this was insufficient to impair future single-unit recordings"; noise across banks was correlated (R² = 0.84 for explanted vs R² = 0.94 for new probes), with the gap attributed to recording-site degradation after long-term implantation.

**J.** Noise-floor drift directly changes sorter detection threshold (a doubling of V_RMS halves the effective amplitude threshold). Pairing V_RMS with sorted-unit count exposes this confound.

### Family 4 — Multi-Unit Firing Rate Metrics

**A.** Aggregate spiking activity per electrode, including task-related modulation.

**B.** $r_{\mathrm{MU},i}(t) = \Delta t^{-1}\sum_k\mathbf{1}(t \le t_k^{(i)} < t + \Delta t)$, Δt ≈ 10–50 ms. Modulation index $M_i = (r_{\text{stim}} - r_{\text{base}})/(r_{\text{stim}} + r_{\text{base}})$.

**C.** Used since Hochberg et al. 2006 (Nature 442:164). Christie et al. 2015 and Trautmann et al. 2019 formalized MUA decoding as a sorter-bypass strategy.

**D.** All extracellular probes.

**E.** Noise-driven false rates. Correlate MUA rate with V_RMS to disambiguate; MUA modulation by behavior is more selective than raw rate because behavior selectively engages real spiking.

**F.** Inherits from Families 1 and 3.

**G.** Trivial.

**H.** Downstream of `detect_peaks`; no dedicated SI module.

**I.** Fraser et al. 2009 (J Neurophysiol 102:1296) and Gilja, Nuyujukian, Chestek et al. 2012 (Nat Neurosci 15:1752) used MUA rate per electrode as the primary BCI control feature. Hahn et al. 2025: 11/14 BrainGate arrays maintained decoder SNR (dSNR) > 1 throughout enrollment; 3 reached peak dSNR > 4.5 vs. 6.29 in able-bodied mouse control; dSNR scales logarithmically with electrode count.

**J.** MUA rate is an upper bound on the firing rate of all sortable units on a channel; divergence (high MUA rate, low sorted rates) flags sorter misses or merge errors.

### Family 5 — LFP-Based Metrics

**A.** Synaptic input integrated over ~250 µm; systematically more stable than spikes on weeks-to-years timescales.

**B.** Bandpower $P_b(c) = \int_{f_1}^{f_2} S_c(f)\,df$ in δ (1–4), θ (4–8), α (8–13), β (13–30), γ_low (30–80), γ_high (80–200), HF (300–1000 Hz, used as spiking-activity proxy). Coherence $C_{ij}(f) = |S_{ij}|^2 / (S_{ii} S_{jj})$. CSD $\approx -[\phi(z+\Delta,t) - 2\phi(z,t) + \phi(z-\Delta,t)]/\Delta^2$.

**C.** Senzai, Fernandez-Ruiz & Buzsáki 2019 (Neuron 101:500); Rasch, Logothetis & Kreiman 2009 (J Neurosci 29:10613). Chen et al. 2023 a-SiC MEA paper: 1–500 Hz bandpower stable for 16 weeks on amorphous silicon carbide MEAs while declining on conventional Si-MEAs.

**D.** All LFP-capable probes. Particularly powerful on linear/laminar probes (Neuropixels, NeuroNexus) where CSD anatomically fingerprints the probe. ECoG is essentially LFP-only.

**E.** 50/60 Hz line noise dominates β/γ_low bands; reference noise dominates δ; CSD requires equally spaced contacts and breaks at probe-channel gaps.

**F.** Highly sensitive to HP cut-on; LFP needs separate 0.5–300 Hz acquisition stream, not the AP-band stream.

**G.** PSD per channel: O(N log N). Coherence O(C² N log N) — expensive on 384-channel Neuropixels.

**H.** `si.preprocessing.bandpass_filter`. No native PSD/CSD — use scipy / elephant (`elephant.current_source_density.estimate_csd`).

**I.** DREDge demonstrated LFP-based motion estimation in human intraoperative and chronic NHP recordings, "tracking motion across centimeters of tissue and several brain regions while mapping single-unit electrophysiological features." Steinmetz et al. 2019 (Nature 576:266) used LFP correlation matrices as anatomical fingerprints on Neuropixels.

**J.** LFP-spike divergence (LFP stable, spikes declining) is the classic encapsulation signature.

### Family 6 — Impedance and Electrochemical Metrics

**A.** Electrode-tissue interface impedance dominated by double-layer capacitance and charge-transfer resistance; sensitive to encapsulation, insulation cracks, and metal degradation.

**B.** |Z|(1 kHz) in kΩ; phase angle θ(1 kHz); EIS sweep 10 Hz – 10 kHz for Randles equivalent circuit fit.

**C.** Williams, Hippensteel, Dilgen et al. 2009 (Brain Res 1282:183); Ludwig, Uram, Yang et al. 2008 (J Neurophysiol 100:1142).

**D.** All electrode types. Standard on Blackrock CerePort (via NSP), Plexon, Intan RHD/RHS headstages, Ripple Grapevine.

**E.** Saline-bath impedance is not in-vivo impedance; calibration drifts with cabling. Very low Z can flag insulation failure rather than improved coupling.

**F.** Requires controlled current injection — typically 1 kHz, 10 nA p-p sinusoid (Blackrock convention). Measure at session start, not after stimulation (post-stim impedance is transiently elevated).

**G.** Hardware measurement; trivial software.

**H.** No SI native measurement; import as side metadata.

**I.** Hughes 2021: Pt-tipped motor arrays at median 447.5 kΩ pre-implant, rising to 1,396 kΩ at day 7, then declining over years; SIROF-tipped sensory arrays at 74.5 kΩ pre-implant. Barrese et al. 2013 (J Neural Eng 10:066014; 78 MEAs in 27 monkeys) verbatim: "Most failures (56%) occurred within a year of implantation, with acute mechanical failures the most common class (48%), largely because of connector issues (83%). Among grossly observable biological failures (24%), a progressive meningeal reaction that separated the array from the parenchyma was most prevalent (14.5%)" — 9 arrays (14.5 % of 78 MEAs) failed from meningeal encapsulation with mean time to failure of 160 days (median = 163 d). Parylene-C cracking/delamination is the dominant material failure mode on Utah arrays.

**J.** Impedance is uncorrelated with sorted-unit count short-term but correlates over months. Impedance change without yield change is an early-warning signal.

### Family 7 — Waveform-Shape Metrics (Sorting-Free)

**A.** Typical spike-event shape per channel without identity assignment.

**B.** Median waveform $\bar w_i(\tau) = \mathrm{median}_k\{x_i(t_k + \tau)\}$, τ ∈ [−0.4, +1.2] ms. Half-width = FWHM of negative peak. PCA spread = ratio of top eigenvalues of snippet covariance, as coarse measure of how many distinct shapes are present.

**C.** Folklore; Quiroga 2004 (Neural Comp), Lewicki 1998 (Network).

**D.** All probes; particularly useful on dense probes where shape variation across nearby channels reveals drift.

**E.** Stim artifacts inflate median waveform; movement-correlated activity correlates across channels.

**F.** Filter band changes waveform width substantially.

**G.** Modest.

**H.** `extract_waveforms` + custom median. `si.compute_template_metrics` provides peak_to_valley_duration, half_width on templates.

**I.** Perge 2013 tracked waveform amplitude drift intra-day. Chestek 2011 reported slower-than-expected shape decline over months.

**J.** Per-channel median waveform = channel template; mismatch with sorter per-unit template flags misclustering.

### Family 8 — Information-Theoretic / Decoding-Based Metrics

**A.** Whether the recording carries decodable task-relevant information independent of spike assignment.

**B.** Classifier accuracy; mutual information $I(X;Y) = \sum p(x,y)\log[p(x,y)/(p(x)p(y))]$; dSNR (BrainGate 2025).

**C.** Christie et al. 2015 (J Neural Eng 12:016009) for head-to-head sorted-vs-unsorted comparison; Trautmann et al. 2019 (Neuron 103:1064) for the theoretical justification via random projections.

**D.** All BCI / decoder applications.

**E.** Decoder recalibration masks underlying signal degradation; report decoder vs. raw input separately.

**F.** Decoder accuracy is the outcome; sensitivity to acquisition parameters propagates from upstream families.

**G.** Decoder training cost varies.

**H.** Downstream of SpikeInterface.

**I.** Christie 2015: sorted-vs-unsorted Naïve Bayes accuracy Δ ≈ 5 %, correlation Δ = 0.015. Hahn 2025: 11/14 arrays dSNR > 1; 3 arrays peak dSNR > 4.5 (vs. 6.29 able-bodied mouse control); dSNR scales logarithmically with electrode count.

**J.** Persistent decoder accuracy with declining sorted-unit count is the strongest evidence that sorting-free metrics are sufficient.

### Family 9 — Drift Detection Without Sorting

**A.** Probe-vs-tissue movement inferred from apparent depth of spiking events without unit identity.

**B.** DREDge: pairwise cross-correlations of time-binned activity along probe axis + spatiotemporal smoothing prior → drift trace μ(t); operable on AP-band peaks or LFP. MEDiCINe: maximize sparsity of time-marginalized depth × amplitude distribution by inferring a generative motion function.

**C.** Decentralized framework: Varol et al. 2021 ICASSP. DREDge: Windolf et al. 2023 bioRxiv → Windolf et al. 2025 Nat Methods (doi:10.1038/s41592-025-02614-5). MEDiCINe: Watters, Buccino & Jazayeri 2025 eNeuro 12:ENEURO.0529-24.2025.

**D.** Linear / dense probes (Neuropixels, NeuroNexus linear, dense MEAs). Limited utility on Utah arrays (electrode spacing 400 µm is too sparse for spatial motion inference).

**E.** DREDge AP-band can be fooled by transient firing-rate changes that mimic motion; LFP-based DREDge is more robust. MEDiCINe assumes sparsity in depth × amplitude space, which fails for very dense layers.

**F.** SpikeInterface GitHub issue #4367 documents that different chunk-length MAD calculations cause meaningful variability in peak thresholds, with "the noise levels vector varies, but in the longer file values are sometimes as much as 20 % higher than the shorter file" — this propagates into motion-estimation variability.

**G.** Minutes per session on a single GPU.

**H.** `si.preprocessing.correct_motion(method='dredge_ap'|'dredge_lfp'|'medicine')`.

**I.** Steinmetz et al. 2021 (Science 372:eabf4588) Neuropixels 2.0 paper demonstrated computational motion correction enabling same-neuron tracking over 300+ days. DREDge demonstrated in chronic recordings with sessions separated by days/weeks.

**J.** Drift correction is a preprocessing step that improves sorter performance (Kilosort 2.5+ and Kilosort 4 have built-in motion correction; DREDge/MEDiCINe are alternatives or supplements). Sorting-free drift traces are themselves a longitudinal metric: large between-session drift is a mechanical-stability flag.

### Family 10 — Synchrony / Network-Level Metrics

**A.** Spatial pattern of coordinated activity across the array as functional fingerprint of the recording.

**B.** Pairwise MUA cross-correlation $C_{ij} = \mathrm{Pearson}(r_i(t), r_j(t))$ in small bins. Population envelope $E(t) = \sum_i r_i(t)$. Correlation-matrix similarity across sessions (e.g., Frobenius distance, matrix correlation).

**C.** Steinmetz et al. 2019 (Nature) — LFP correlation matrices as anatomical fingerprints; MUA cross-correlation is folklore now formalized in IBL data QC.

**D.** Best on multi-channel probes > 32 channels.

**E.** Common reference noise creates spurious cross-channel correlations; CMR mitigates but the CMR window choice matters.

**F.** Reference scheme is the dominant confound.

**G.** O(C²) per session.

**H.** User-side; no SI module.

**I.** Limited formal longitudinal validation; primarily used as an anatomical fingerprint for cross-session alignment.

**J.** Largely insensitive to sorter changes; preserved if the underlying population is stable.

### Family 11 (Newly Elevated) — Spiking-Band Power (SBP)

**A.** Continuous-time envelope power of the spike-band-filtered signal, without discrete event detection — a fundamentally different observable from threshold-crossing rate (F1) and from spike-band amplitude (F2).

**B.** Bandpass to 300–1000 Hz → absolute value (or square) → low-pass / decimate to 1–2 kHz output rate: $\mathrm{SBP}(t) = \mathrm{LP}_{\Delta t}|x_{[300\text{–}1000]}(t)|$.

**C.** Stark & Abeles 2007 (J Neurosci Methods) introduced "Entire Spiking Activity" (ESA) as a continuous spike proxy. Nason et al. 2020 (Nat Biomed Eng 4:973) verbatim: "the downsampled magnitude of the 300–1,000 Hz band of spiking activity can predict movement similarly to the threshold crossing rate (TCR) at 30 kilo-samples per second" and SBP "is dominated by local single-unit spikes with spatial specificity comparable to or better than that of the TCR." Even-Chen et al. 2020 (Nat Biomed Eng 4:984) used SBP for power-saving wireless BCI.

**D.** All spike-band-capable probes; particularly attractive for ultra-low-power wireless implants.

**E.** Sensitive to high-frequency line noise and EMG. SBP is not equivalent to spike rate if spike amplitudes vary substantially.

**F.** Filter band is the definition; output rate can be as low as 1 kHz (Even-Chen 2020 reports 2–3 orders of magnitude bandwidth reduction).

**G.** Trivial; suitable for on-implant computation. This is its main appeal.

**H.** Not natively exposed in SpikeInterface; assemble from `bandpass_filter` + `np.abs` + `decimate` in user code.

**I.** Nason 2020 demonstrated chronic NHP BCI control with SBP over months. Less longitudinal track record than TCR.

**J.** SBP correlates with sorted firing rates of low-SNR units better than TCR does (Nason 2020). Continuous sorter-free proxy for MUA that captures sub-threshold spiking power.

---

## Additional Metrics Encountered (Side Notes)

1. **dSNR (Hahn 2025 BrainGate)** — decoder-output SNR; folded into Family 8 because it is a downstream summary of decoding-based metrics, not a fundamentally distinct quantity.
2. **PCA per-channel variance** (some QC GUIs) — folded into Family 7 (waveform shape).
3. **IBL coherence + PSD bad-channel detector** — folded into Families 3 + 5; specifically `si.preprocessing.detect_bad_channels(method='coherence+psd', …)`.
4. **Neuropixels phase-shift correction** — preprocessing for multiplexed ADCs (NP 1.0: 32 ADCs × 12 ch; NP 2.0: 24 ADCs × 16 ch), not a metric; failure to apply inflates V_RMS through poorly corrected common-mode artifacts.
5. **Pre- vs post-stim impedance** — variant of Family 6; post-stim Z is transiently elevated, so use pre-session values.
6. **Stentrode endovascular signal metrics** (medRxiv 2025.09.19.25335897) — distinct probe class (intravascular ECoG-like) but overlaps Families 5 + 1.
7. **1–500 Hz bandpower on a-SiC MEAs** (Chen et al. 2023) — instantiation of Family 5; supports LFP bandpower as a probe-comparison stability metric.
8. **Barrese 2013 failure-mode taxonomy** (J Neural Eng 10:066014) — interpretation reference for what changes in F1, F2, F3, F6 mean physically (meningeal encapsulation, parylene-C cracking, wire bundle/connector failure).

---

## Mathematical Reference Section

Compiled formulas with parameter values and units.

**Threshold detection.**
- $T_i = \alpha\hat\sigma_i$; α ∈ {−3, −3.5, −4.5, −5.25}; units µV.
- Pittsburgh / BrainGate: α = −4.5; snippet 48 samples (1.6 ms at 30 kHz), starting 11 samples before crossing.
- Christie 2015 empirical: α = −3 for low-noise arrays, α = −4.5 for higher-noise arrays.

**Noise estimators.**
- $V_{\mathrm{RMS}} = \sqrt{N^{-1}\sum_{k=1}^N x_k^2}$ on zero-mean bandpassed trace; µV.
- Pre-event V_RMS (Downey 2018): same formula on 5–10 pre-crossing samples.
- $\hat\sigma_{\mathrm{MAD}} = \mathrm{MAD}(x) / 0.6745$; SpikeInterface default.

**SNR.**
- $\mathrm{SNR}_{\mathrm{MU}} = V_{pp,\text{top2}} / V_{\mathrm{RMS}}$ (Hughes 2021).
- $\mathrm{SNR}_{\mathrm{Sponheim}} = \text{peak-to-trough}/(2\cdot \mathrm{avg\,std}_{\text{46 samp}})$; "good" channel threshold > 1.5.

**Yield.**
- $\mathrm{AEY}_{\mathrm{BG}} = |\{i : r_i > 2\,\mathrm{Hz}\,@\,-4.5\hat\sigma_{\mathrm{robust}}\}| / N_{\mathrm{ch}}$.
- $\mathrm{AEY}_{\mathrm{Pitt}}$: include electrode if rate ≥ 1.67 Hz AND mean top-2 % V_pp ≥ 30 µV at −4.5 × V_RMS.
- $\mathrm{Yield}_{\mathrm{Sponheim}}$: fraction of channels with ≥ 14 events AND SNR > 1.5.

**Sponheim linear yield decline.**
- Slope = −0.00058 yield-fraction / day ≈ −2 % / 30 d. Average dataset lifespan = 622 d (range 44 d to > 3000 d).

**LFP / CSD.**
- $P_b(c) = \int_{f_1}^{f_2} S_c(f)\,df$.
- $C_{ij}(f) = |S_{ij}(f)|^2 / (S_{ii}(f) S_{jj}(f))$.
- $\mathrm{CSD}(z,t) \approx -[\phi(z+\Delta,t) - 2\phi(z,t) + \phi(z-\Delta,t)] / \Delta^2$.

**SBP.**
- $\mathrm{SBP}(t) = \mathrm{LP}_{\Delta t}|x_{[300\text{–}1000\,\mathrm{Hz}]}(t)|$.

**Impedance.**
- |Z|(1 kHz) measured by 10 nA p-p sinusoid (Blackrock convention); kΩ.

**Bad-channel detection (IBL / SpikeInterface defaults).**
- `std_mad_threshold=5`, `psd_hf_threshold=0.02 µV²/Hz` (above 80 % Nyquist), `dead_channel_threshold=-0.5`, `noisy_channel_threshold=1.0`, `n_neighbors=11`.

---

## Decision Table — Sorting-Free Metric Families × Use Case

| Family | Recommended probe types | Pair with (Parts 1–2) | Compute / storage cost | Sensitivity to acquisition | Validation in chronic/longitudinal literature | Key caveats |
|---|---|---|---|---|---|---|
| 1. TC yield | Utah, Neuropixels, NeuroNexus, tetrodes | Sorter unit count, ISI metrics | Low | High (threshold α, filter) | **Strong** (BrainGate 14-pt, Sponheim 55 arr) | Threshold choice dominates cross-study comparability |
| 2. Unsorted V_pp top-2 % | Same as F1 | Bombcell per-unit V_pp | Low | Medium (filter band) | **Strong** (Hughes 1500 d, Perge) | Filter cut-on shifts values 20–40 % |
| 3. Noise floor (V_RMS / MAD) | All | Sorter detection threshold | Trivial | High (reference, filter) | **Strong** (Downey, IBL) | Specify pre-event vs all-sample |
| 4. MUA firing rate | All | Sorted firing rate | Trivial | Medium | Strong | Inflated by noise; pair with V_RMS |
| 5. LFP band power / CSD | Linear probes, ECoG, NP, NN | Anatomical localization | Medium | Medium | Moderate (Senzai, a-SiC MEAs, DREDge) | Line noise contamination |
| 6. Impedance @ 1 kHz | All (hardware) | None direct | Trivial | Low | **Strong** (Williams, Ludwig, Barrese) | Non-monotonic with yield; flag direction |
| 7. Waveform shape | All | Sorter templates | Low | High (filter) | Moderate | Useful as sorter cross-validation |
| 8. Decoding-based (dSNR, MI) | BCI applications | Decoder accuracy | High (training) | Low (outcome) | **Strong** (Christie, Trautmann, Hahn 2025) | Recalibration masks degradation |
| 9. Drift (DREDge / MEDiCINe) | NP, NN linear, dense MEAs | Sorter drift correction | Medium (GPU) | Medium | Moderate (NP 2.0, Windolf) | AP-version fooled by FR changes |
| 10. Network synchrony | Multi-ch > 32 | Anatomical fingerprint | O(C²) per session | High (reference) | Weak | Reference noise creates spurious correlations |
| 11. SBP | All; especially low-power implants | None direct | Trivial | Medium (filter band) | Moderate (Even-Chen, Nason 2020) | Less longitudinal track record than TCR |

---

## Integration Guidance

### Minimum reporting standard

For any chronic implant study, report alongside sorter outputs:

1. Per-session V_RMS distribution (median, IQR across electrodes) — F3.
2. AEY at a stated threshold (recommend −4.5 × robust σ, ≥ 2 Hz, BrainGate convention) — F1.
3. Median V_pp of top 2 % of snippets (Pittsburgh convention) — F2.
4. 1 kHz impedance distribution — F6 (mandatory for clinical / NHP chronic implants).

Storage cost < 1 kB per session, computationally trivial, sorter-independent, directly comparable across BrainGate, Pittsburgh, and Sponheim datasets.

### Sorting-free metrics as triage (dead-channel identification before sorting)

Use `si.preprocessing.detect_bad_channels(method='coherence+psd')` BEFORE CMR and BEFORE spike sorting. Channels labeled "dead" or "out" must be excluded from the CMR reference (otherwise they corrupt all good channels). Channels labeled "noise" require manual review. This is part of the IBL destriping pipeline now widely adopted by SpikeInterface users.

### Cross-validating sorter outputs

- AEY ≫ sorted-unit count: either oversplitting (Bombcell catches via amplitude cutoff, ISI violations) OR legitimate multi-unit-dominant territory. Use per-channel median waveform (F7) as cross-validation: if it shows multiple peaks at distinct latencies, the sorter is correctly identifying multi-unit territory.
- Sorted-unit count > electrodes with detectable threshold crossings: sorter hallucinating, almost always motion-related cluster splitting. Apply DREDge/MEDiCINe (F9) to confirm.
- V_pp top-2 % stable but sorted-unit count declining: drift, not amplitude loss → motion correction.
- V_pp top-2 % declining AND impedance rising together: classic encapsulation; expect glial scar (Polikov, Tresco & Reichert 2005 J Neurosci Methods 148:1).
- V_RMS rising sharply: hardware fault. Check reference, cabling, headstage.

### Layering with Bombcell / UnitRefine (Part 2)

Compute sorting-free metrics on the *raw recording*; compute Bombcell / UnitRefine quality on the *sorter output*. Use the four-metric core as a channel mask (which channels are eligible for sorting), then let Bombcell/UnitRefine do per-unit curation. A channel that fails sorting-free triage (IBL "dead", V_RMS > 2× cohort median, AEY = 0) should never produce "good" units; if Bombcell marks units as good on such a channel, they are almost certainly sorter artifacts.

---

## Probe-Specific Recommendations

### Utah arrays (Blackrock, 96–256 channels, intracortical)
- Most informative: F1 (AEY), F2 (V_pp top 2 %), F3 (V_RMS), F6 (impedance), F8 (decoding).
- Less informative: F5 (4 × 4 mm grid limits CSD; cross-channel coherence is shallow), F9 (400 µm spacing too sparse for DREDge/MEDiCINe).
- Use the BrainGate convention: −4.5 × robust σ, ≥ 2 Hz, 250–5000 Hz bandpass.

### Neuropixels (1.0 / 2.0)
- All families informative. F5 and F9 particularly because dense linear geometry enables CSD and motion estimation.
- Recommended pipeline: `phase_shift` → `highpass_filter` → `detect_bad_channels` → CMR → DREDge or MEDiCINe → sort.
- F11 (SBP) under-explored on Neuropixels but theoretically attractive given dense site coverage.

### NeuroNexus linear / multi-shank silicon
- Similar to Neuropixels with sparser sampling. F1–F7 apply. F9 effective if site spacing ≤ 50 µm.
- Karumbaiah, Saxena, Carlson et al. 2013 (Biomaterials 34:8061) and Rennaker, Miller, Tang et al. 2007 (J Neural Eng 4:L1) provide chronic stability baseline.

### Tetrodes
- F1, F2, F3, F4 informative. F7 (waveform shape) particularly valuable because tetrode triangulation depends on per-channel waveforms.
- F5 limited by sparse sampling. Single-tetrode CMR ineffective due to high inter-channel correlation; use shared/global reference.

### MEAs (in vitro, planar)
- F1, F2, F3, F4, F5, F6, F10 (network synchrony particularly relevant given dense 2D coverage).

### ECoG / micro-ECoG
- F1, F2, F4 inapplicable (no resolvable spikes). F3, F5, F6, F10 highly informative. F8 routinely used in ECoG BCI.

---

## Recommendations (Decision-Ready Next Steps)

1. **Adopt the BrainGate AEY convention (−4.5 × robust σ, ≥ 2 Hz rate) as your primary longitudinal yield metric.** Cross-study comparability is the threshold for this choice. Trigger to change: if noise statistics differ markedly from BrainGate (e.g., very high firing rates in marmoset striatum), Christie 2015 supports α = −3 for low-noise arrays, but report both.

2. **Compute and persist the four-metric core (V_RMS distribution, AEY, top-2 % V_pp median, impedance) for every session.** < 1 kB per session. This generates the longitudinal table that survives sorter / curator turnover.

3. **Add `si.preprocessing.detect_bad_channels` as a mandatory triage step before sorting.** Action threshold: any "dead" or "out" channel excluded from CMR. Review threshold: "noise" channels reviewed before final sort.

4. **Adopt DREDge or MEDiCINe motion correction on linear / dense probes.** Trigger: linear or dense probe geometry (Neuropixels, NeuroNexus linear, dense MEAs). Skip on Utah (electrode spacing too coarse).

5. **Report top-2 % V_pp not median V_pp.** Top-2 % captures the high-quality units that drive sorter output and BCI performance; median V_pp is dominated by sub-threshold noise events. Hughes 2021 sets this convention.

6. **Pair sorting-free metrics with Bombcell / UnitRefine outputs from Part 2 as a routine cross-check.** Flag any session where (a) Bombcell-good unit count > AEY × N_channels (sorter hallucination) or (b) AEY > 0.5 but Bombcell-good unit count = 0 on the same channels (sorter under-sensitive or curator too aggressive).

7. **For new chronic implants, instrument LFP-band acquisition from day 1.** Even if your primary analysis is spike-based, LFP-based DREDge motion tracking and CSD anatomical fingerprinting (F5) provide a slower-changing baseline that catches probe motion before it shows up in spike loss.

8. **For BCI-class longitudinal cohorts (> 6 months), explicitly model V_pp top-2 % and AEY as log-linear functions of days-post-implant.** The Sponheim −0.00058/day yield-slope and the Hughes 1,500-day log-linear fits provide priors; deviation from these priors flags anomalous decline that warrants intervention.

---

## Caveats

- **Numerical conventions vary across labs.** BrainGate (−4.5 × robust σ, 2 Hz, 250–5000 Hz), Pittsburgh (−4.5 × V_RMS, 1.67 Hz, 30 µV V_pp floor), Sponheim (−5.25 → −4.5 × V_RMS, ≥ 14 events, SNR > 1.5). Sponheim does not report V_pp; Hughes does not directly report Family-1 AEY. Cross-study yield numbers must be re-computed under a common convention to be comparable.

- **Hughes 2021 numerical V_pp and V_RMS trajectories are reported as graphical regressions (Fig. 1 c–e); exact starting and ending µV values and per-day slopes are present in the figure panels and were not extracted as text in the source materials available to this review.** The directional claim ("decreased over time" for both V_pp and V_RMS, SIROF-sensory preserving high amplitudes longer than platinum-motor) is well-sourced; precise numbers require direct retrieval from the published figure.

- **The Bullard et al. 2020 citation in the original seed list (J Neural Eng 17:056035) could not be verified.** The Bullard / Hutchison / Lee / Chestek / Patil 2020 paper is in *Neuromodulation* 23(4):411–426 — a hardware-complications systematic review, not a primary longitudinal recording-quality dataset. The intended citation may be Colachis et al. 2021 (*J Neural Eng* 18:046051, the 5-year Battelle/Ohio State retrospective). Verify before citing.

- **The Lewis et al. 2024 finding that impedance and recording quality are non-monotonic is on flexible / PEDOT-coated probes specifically and may not generalize to platinum or SIROF Utah arrays.** Treat impedance as a directional change indicator, not an absolute yield predictor.

- **DREDge and MEDiCINe were both published in 2025 and are still being integrated into common pipelines.** Pre-2024 chronic studies did not have these tools; cross-study comparisons should account for whether motion correction was applied. Garcia et al. 2024 (eNeuro, doi:10.1523/ENEURO.0229-23.2023, "A modular implementation to handle and benchmark drift correction for high-density extracellular recordings") provides the benchmarking framework.

- **Family 10 (network synchrony) and Family 11 (SBP) have weaker longitudinal validation than F1–F6.** Treat as exploratory in chronic reporting.

- **For Neuropixels specifically, the multiplexed ADC architecture imposes a `phase_shift` preprocessing requirement that, if neglected, inflates V_RMS and corrupts CMR.** The SpikeInterface docs and the SpikeGLX `catGT -gbldmx` flag both address this. Always apply phase-shift correction before CMR on Neuropixels.

- **Threshold-crossing yield is sensitive to noise statistics that change with anesthesia state, behavioral state, and time of day** (Perge 2013 documented within-day fluctuations affecting decoder performance in BrainGate participants). Compare across sessions only after controlling for state, or use a robust longitudinal time-windowed median rather than per-session point estimates.

- **The Fiscella, Farrow, Jones et al. citation in the original seed list (J Neurosci Methods 193:41, 2010) could not be verified through this review's searches; PubMed indexing suggests the relevant in-vitro MEA stability work may be at a different volume/page.** Verify before citing.
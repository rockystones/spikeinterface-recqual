# Analysis brief: empirically demonstrating the within-array design benefit from NHP ephys data

**For:** the Claude Code session holding the processed NHP electrophysiology dataset.
**From:** a parallel session working on the manuscript that these analyses support.
**Status:** self-contained. You do not need the manuscript to execute this.

---

## 0. Why you are doing this

The paper claims that assigning two surface coatings to different shanks **within a single microelectrode array** ("within-array" design) is a better way to compare biomaterials than putting one coating on each of two arrays ("between-array") or on arrays in two different animals ("between-subject").

That claim is currently asserted in the Introduction and supported only by a citation to a rabbit-cartilage paper. It needs to be replaced with numbers measured from this dataset.

**The core insight that makes this tractable:** the benefit of the within-array design is entirely a statement about *variance structure*, and variance structure can be measured from control data without reference to any treatment effect. Decompose an observation as

```
y[animal, array, shank, channel, session]
  = mu + tau*Treatment + a[animal] + d[array] + s[shank] + e
```

with variances `vA, vD, vS, vE`. Then, with `n` units and `m` shanks per array:

| Design | treatment assigned at | variance of the treatment contrast |
|---|---|---|
| between-subject | animal | `2*(vA + vD + (vS+vE)/m) / n` |
| between-array | array within animal | `2*(vD + (vS+vE)/m) / n` |
| within-array | shank within array | `4*(vS+vE) / (m*n)` |

Define `rho = (vA+vD)/total`. The number of animals a between-subject study needs per animal a within-array study needs, at equal power, is

```
N_between / N_within  =  1 + m*rho/(1-rho)
```

Reference values (these are theory, not data — your job is to produce the empirical `rho`):

| rho | m=4 | m=16 | m=48 | m=96 |
|---|---|---|---|---|
| 0.10 | 1.4 | 2.8 | 6.3 | 11.7 |
| 0.20 | 2.0 | 5.0 | 13.0 | 25.0 |
| 0.30 | 2.7 | 7.9 | 21.6 | 42.1 |
| 0.40 | 3.7 | 11.7 | 33.0 | 65.0 |

**Deliver `rho_hat` with a confidence interval, and the design-efficiency factor that follows from it.** Everything else in this brief is secondary.

---

## 1. Step 0 — inventory gate (do this first, report back before proceeding)

Do not start modelling until you have confirmed what exists. Report a short inventory covering:

1. **Granularity.** Is there one row per channel per session, or only per-array summaries? Per-channel is required for everything below. If only summaries exist, stop and report that.
2. **Identifiers present.** animal ID, array ID, channel index, session date. Which of these exist as columns?
3. **Channel→shank→condition map.** Is there a mapping from channel index to (row, column) position on the 10×10 grid, and from position to coating condition? This is essential. If the map exists only as a figure or a lab notebook, say so.
4. **Geometry.** Can you compute, for each channel: distance to array edge, inner/outer classification (central 6×6 = inner), and distance/direction to the wire-bundle exit? The wire bundle exit edge must be known per array.
5. **Metrics available.** Per channel per session: number of units, active/inactive flag, max peak-to-peak amplitude, 1 kHz impedance. Which exist?
6. **Exclusions.** How are broken channels flagged? Is the impedance >3 MΩ rule applied upstream or downstream?
7. **Coverage.** Sessions per animal per month; the months where both animals contribute.
8. **Other cohorts.** Is the earlier 4-monkey / 8-array dataset (implants 2012–2017, sorted with MountainSort) also accessible in this environment? If yes, flag it — see §7.

Write the inventory to `results/00_inventory.md`. If items 1–3 are missing, that is the finding; report it and stop.

---

## 2. Analysis 1 — sham-contrast resampling (the headline result)

This is the most important analysis and the most persuasive, because it makes **no distributional or model assumptions**. It measures the efficiency difference directly by constructing fake experiments out of real data.

### Procedure

Work on one metric at a time (start with max peak-to-peak amplitude, then repeat for units-per-site and channel yield). Work within a single month bin at a time, then pool results across months.

**Preparation.** Because a real treatment effect would inflate the between-array variance artificially, first remove condition means: fit `y ~ C(condition)` across the whole dataset for that month and take residuals `r`. All resampling below operates on `r`.

**A. Within-array sham contrast.** For each array, repeat `B = 10000` times: randomly split that array's usable shanks into two equal halves, compute `mean(half1) - mean(half2)`. Collect all values across arrays into a null distribution; record `SD_within`.

**B. Between-array sham contrast.** Repeat `B` times: draw two distinct arrays, randomly label one A and one B, compute `mean(all channels of A) - mean(all channels of B)`. Record `SD_between`.

**C. Between-subject sham contrast.** Same as B but drawing two distinct *animals* and using each animal's pooled channels. With only two animals this is a single contrast per resample of session assignment — report it, but flag it as `n=2` and therefore indicative only.

### Report

```
efficiency_between_vs_within  = (SD_between / SD_within)^2
efficiency_bs_vs_within       = (SD_bs      / SD_within)^2
```

with bootstrap CIs (resample arrays/animals with replacement at the outer level).

Run **two variants** and report both, because they answer different questions:

- **Realistic** — within-array uses 48 vs 48 channels on one array; between-array uses 96 vs 96 across two arrays. This is what an investigator would actually do, and it is the number for the paper.
- **Matched-n** — both contrasts use 48 channels per side. This isolates the variance-structure effect from the averaging effect. It will be the smaller number. Report it so a reviewer cannot accuse you of conflating the two.

### Interpretation to hand back

One sentence of the form: *"Under random relabelling of real data, a between-array contrast had SD X µV and a within-array contrast had SD Y µV; the within-array design is Z-fold more efficient, equivalent to needing Z-fold fewer arrays for the same precision."*

---

## 3. Analysis 2 — variance components with confidence intervals

The parametric counterpart to Analysis 1. Should agree with it; if it does not, investigate before reporting either.

R is strongly preferred over Python here because `lme4` handles nested random effects and profile-likelihood intervals on variance components properly.

```r
library(lme4)
d$animal <- factor(d$animal); d$array <- factor(d$array); d$shank <- factor(d$shank)

m0 <- lmer(amplitude ~ condition * poly(month, 2)
           + (1 | animal/array/shank),
           data = d, REML = TRUE)
# (1|animal/array/shank) expands to (1|animal) + (1|animal:array) + (1|animal:array:shank)

print(VarCorr(m0), comp = "Variance")
confint(m0, method = "profile", oldNames = FALSE)
```

Python fallback if R is unavailable — `statsmodels` MixedLM with `vc_formula`, or `pymer4` which wraps lme4:

```python
import statsmodels.formula.api as smf
vcf = {"array": "0 + C(array)", "shank": "0 + C(shank)"}
md  = smf.mixedlm("amplitude ~ condition * month", d, groups=d["animal"],
                  vc_formula=vcf, re_formula="1")
mdf = md.fit(reml=True)
```

Report `vA, vD, vS, vE` with intervals, then `rho_A`, `rho_D`, `rho = rho_A + rho_D`, then the efficiency factor `1 + m*rho/(1-rho)` for `m = 48` and `m = 96`.

**Expect a poor `vA`.** Two animals gives essentially no information about between-animal variance. Report it with its (very wide) interval and do not lean on it. `vD` is the load-bearing quantity and you have four arrays for it — still few, but defensible. Say so explicitly rather than presenting a point estimate alone.

---

## 4. Analysis 3 — does the within-array advantage grow with implant age?

Prediction worth testing: as arrays chronically diverge — one becoming encapsulated while its neighbour does not — `vD` should grow over time while `vS+vE` stays roughly flat. If so, the within-array design is *most* valuable exactly in the chronic regime where chronic studies are hardest.

Fit the variance-components model separately in sliding windows (e.g. months 0–6, 4–10, 8–14, 12–18, 16–21) and plot `rho_D` against implant month with intervals. Equivalently, re-run Analysis 1's resampling per window and plot the efficiency factor over time.

If the trend is present it is a strong, quotable result. If it is flat, report that too — it is still informative.

---

## 5. Analysis 4 — minimum detectable effect, and equivalence tests for the nulls

The study's within-array comparisons (TNP vs TNP+L1; uncoated control vs EDC/NHS+L1) returned nulls. A null is only informative if the design had resolution. Quantify it.

### 4a. MDE achieved

For the within-array design at 80% power, α = 0.05 two-sided:

```
MDE / sigma_w = 5.60 / sqrt(m_total * n_arrays)      where sigma_w = sqrt(vS + vE)
```

| shanks/array | 1 array | 2 arrays | 4 arrays |
|---|---|---|---|
| 48 | 0.81 | 0.57 | 0.40 |
| 96 | 0.57 | 0.40 | 0.29 |

Convert to the natural units of each metric using `sigma_w_hat` from Analysis 2, so the paper can say "we could have detected a difference of N µV and did not."

### 4b. TOST equivalence tests

Run two one-sided tests (Lakens 2017, *Soc Psychol Personal Sci* 8:355–369) on each within-array null. The smallest effect size of interest should come from inside this dataset, not from the literature: **use a fraction of the observed TNP-versus-uncoated effect measured in the same animals.** Report at SESOI = 25% and 50% of that effect.

```r
library(TOSTER)
# bounds expressed in the same units as the outcome
TOSTtwo.raw(m1=, m2=, sd1=, sd2=, n1=, n2=, low_eqbound=-0.25*tnp_effect,
            high_eqbound=0.25*tnp_effect, alpha=0.05)
```

Important: `n1`/`n2` must be the **number of independent units**, not the number of channels. Use array-level or animal-level means, or derive the SE from the mixed model's contrast rather than from raw channel counts. Getting this wrong inflates the apparent precision enormously.

Report, for each null: the point estimate, its 90% CI (TOST convention), the SESOI, and the verdict — equivalent / not equivalent / inconclusive.

---

## 6. Analysis 5 — position confounds and treatment × position

The coating stripes on these arrays run in alternating **rows**, and the wire bundle exits one edge. Two things follow that must be checked, not assumed.

### 5a. Is condition confounded with tether distance?

For each array, compute the mean distance-to-wire-bundle-exit for each condition's shanks. If the two conditions differ systematically, the within-array contrast is confounded with the mechanical strain gradient. **Report the numbers even if the difference is small** — a reviewer will compute this themselves.

Same check for distance-to-array-edge and for inner/outer membership.

### 5b. Adjusted treatment effect and interaction

```r
m2 <- lmer(amplitude ~ condition * region + condition * dist_to_tether
           + poly(month,2) + (1 | animal/array/shank), data = d)
```

Report the condition effect adjusted for position, and the `condition:region` interaction as the formal test of the "shielding effect" claim (coating helps on mechanically sheltered interior shanks, not on the perimeter).

### 5c. Subgroup n

The captions currently state "N = 48 shanks per condition" without giving the inner/outer split. By construction with alternating rows and a central 6×6 inner region this should be roughly 18 inner and 30 outer per condition. **Compute the actual counts per array and report them** — this is a direct reviewer question and the manuscript cannot currently answer it.

---

## 7. Analysis 6 — spillover (attempt, expect to bound rather than estimate)

The within-array design's validity requires that a shank's outcome depends only on its own coating. If a coating's biological effect reaches beyond the inter-shank pitch (400 µm on this array), control shanks are contaminated and the measured effect is attenuated by a factor `(1 - phi)`, where `phi` is the spillover fraction. Critically, **spillover shrinks the estimate without inflating its variance** — a contaminated null looks like a confident null.

With an *alternating-row* pattern every interior shank has both neighbours of the opposite type, so the neighbour-exposure geometry is nearly constant and `phi` is close to unidentifiable from these data. Do the following anyway, and report honestly if it fails to identify:

1. For each shank compute an exposure index `E = sum over opposite-condition shanks of exp(-dist/lambda)` on a grid of `lambda` values (50–600 µm).
2. Fit `y ~ condition * E + (1|animal/array/shank)` at each `lambda`; profile the likelihood over `lambda`.
3. Report whether the `condition:E` term is identifiable and, if so, the implied `phi`.

**Expected outcome: poorly identified, wide interval.** That is a legitimate result and should be reported as a design limitation — it means the alternating pattern maximises spillover exposure while providing no internal way to measure it. A half-half partition would provide a boundary gradient from which `phi` *is* estimable. If any array or cohort in your data used a half-half or otherwise non-uniform partition, prioritise that one for this analysis.

---

## 8. Analysis 7 — fold in the earlier 4-monkey cohort if you have it

If the 2012–2017 dataset (4 monkeys, 8 arrays, one coated and one uncoated array per animal) is accessible, it materially strengthens two things:

- **`vD` estimated on 8 arrays instead of 4**, with a real `vA` on 4 animals instead of 2. This is the single biggest improvement available to the `rho_hat` estimate.
- **A test of the implant-location effect.** In the current cohort, coating condition is perfectly confounded with implant location (non-TNP lateral/anterior and TNP medial/posterior in both animals). The earlier cohort was partially counterbalanced across medial/lateral and anterior/posterior, so it can be used to ask whether location predicts outcome independently of coating. If it does not, that materially weakens the confound objection against the current cohort.

**Caution on pooling.** The two cohorts were spike-sorted with different pipelines (MountainSort4 vs Plexon Offline Sorter with different curation and blinding). Absolute amplitudes and unit counts are **not** comparable across cohorts. However, *variance ratios and ICCs are dimensionless* and can legitimately be compared or pooled. Estimate `rho` separately per cohort and compare; only pool if they agree.

---

## 9. Output contract

Produce, under `results/`:

| File | Contents |
|---|---|
| `00_inventory.md` | Step 0 findings; blockers |
| `01_resampling.md` + `.csv` | SD of sham contrasts by design, metric, month; efficiency factors with bootstrap CIs; both realistic and matched-n variants |
| `02_variance_components.csv` | `vA, vD, vS, vE` with profile CIs, per metric; `rho_A`, `rho_D`, efficiency factor |
| `03_rho_over_time.csv` + figure | `rho_D` and efficiency by implant-month window |
| `04_mde_and_tost.md` | MDE in natural units per metric; TOST results per null comparison with 90% CIs and verdicts |
| `05_position.md` | Condition-vs-geometry confound table; adjusted effects; `condition:region` interaction; inner/outer subgroup counts per array |
| `06_spillover.md` | Exposure-index profile; identifiability verdict; bound on `phi` if obtainable |
| `analysis/` | All scripts, runnable end to end, with a seed set |

For each numeric result, report the **estimate, an interval, and the n at the level of the inferential unit** (arrays or animals — not channels).

---

## 10. Pitfalls — please read before writing code

1. **Channels are not independent replicates.** Channels within a shank and shanks within an array share variance; treating them as independent inflates Type I error severely (Aarts et al. 2014, *Nat Neurosci* 17:491–496 report rates reaching 80% at a nominal 5%). Every inferential statement must use a model with the nesting, or aggregate to the array/animal level first. This applies to the TOST `n` in particular.

2. **Do not use coefficient of variation as the variability measure.** `%CV = SD/mean` conflates dispersion with location. If two groups differ in mean, a %CV comparison will report a variability difference that is partly or wholly a mean-scale artifact. Use variance components or SDs on a fixed scale.

3. **Removing the condition effect before resampling is mandatory** in Analysis 1. Skipping it lets the real treatment effect masquerade as between-array variance and inflates the apparent efficiency gain.

4. **Channel exclusion interacts with the variance estimate.** The impedance >3 MΩ exclusion truncates a tail. Run the key analyses with and without the exclusion and report whether conclusions change. Also report the number and fraction excluded per array per month — if exclusion rates differ by condition, the surviving-channel comparison is itself biased.

5. **Document the monthly binning.** Weekly sessions binned to months is implied everywhere but described nowhere. State the rule and whether both animals contribute to every bin.

6. **Set and record seeds** for all resampling.

7. **Report `n` at every level** in every figure caption you generate: animals, arrays, shanks per condition, channels.

---

## 11. What NOT to conclude

- Do **not** report that the within-array design "eliminates confounds" as an empirical finding. That it removes animal- and array-level terms from the contrast is true by construction, from the model definition. What these analyses establish is the *magnitude* of the variance removed and whether interference erodes it.
- Do **not** extend the efficiency claim to the TNP-versus-non-TNP comparison. That contrast is between two different arrays and gets **no benefit** from the within-array design; it is an `n = 2` between-array comparison with condition confounded with implant location. The efficiency tables apply only to contrasts that were assigned within a single array.
- Do **not** treat a precise within-array estimate as generalisable across arrays without estimating the treatment × array variance. With four arrays that term is barely identifiable, and the position analyses are likely to show the effect is context-dependent — which is direct evidence it will not transfer unchanged.
- If spillover turns out to be large or unidentifiable, the within-array nulls are **uninterpretable**, not confirmatory. Order matters: settle §7 before anyone writes a sentence claiming L1 adds nothing.

---

## 12. One-line summary of what success looks like

A sentence the manuscript can use, with every blank filled from this dataset:

> *"Assigning both surface conditions within a single array removed the animal- and device-level variance components from the treatment contrast; these accounted for rho = ___ (95% CI ___) of total variance in ___, so an equivalently powered between-subject study would have required ___-fold more animals. Within the resulting resolution (minimum detectable effect ___), the L1 protein layer conferred no benefit over the nanoparticle base layer (TOST equivalence at ___% of the TNP effect, p = ___)."*

# The longitudinal layer measured from continuous data

559 sessions with real broadband — Rocky 2017–2023 (431 `.ns5`) and Fisk
2023–2025 (128 `.ns6`) — re-detected identically at 4·MAD. Every previous
longitudinal number in this project came from NEV snippets, so this is the
first time the noise floor has been *measured* rather than inferred from
pre-trigger windows.

`notebooks/scratch_rocky_ns5_free.py` → `data/derived/rocky_ns5/ns5_free.parquet`.

## The analog headstage cannot carry a trend

Before any trend: **the analog headstage degrades over its own era.** Taking
the analog/digital noise ratio per same-day pair, with the digital recording of
the same array on the same day as a control:

| array | first 8 pairs | last 8 pairs | rho(date) | p |
|---|---|---|---|---|
| Anterior | 1.25 | **2.07** | +0.662 | 8.3e−09 |
| Posterior | 1.33 | **3.88** | +0.607 | 2.2e−07 |

Restricting both headstages to the same 2018-04 → 2019-07 window rules out era
as the explanation: analog noise rho **+0.658 / +0.695**, digital
**−0.084 / −0.071**, on the same days.

**So every trend below uses the digital headstage only.** An analog series
shows a rising noise floor that is entirely instrument.

## Rocky, digital, 2018–2023

| metric | Anterior (n=137) | Posterior (n=136) |
|---|---|---|
| noise floor | −0.438 (8.7e−08) | −0.375 (6.8e−06) |
| amplitude p50 | −0.400 (1.3e−06) | −0.389 (2.9e−06) |
| **peak SNR** | **−0.739** (6.1e−25) | **−0.719** (7.0e−23) |
| crossing rate | −0.537 (1.4e−11) | −0.745 (2.4e−25) |

### The SNR result needs its magnitude quoted, not its rho

rho = −0.739 at p = 6e−25 reads as a collapse. It is not. By year, Anterior:

| year | n | noise | amp | **peak SNR** | rate |
|---|---|---|---|---|---|
| 2018 | 35 | 7.87 | 49.60 | **4.85** | 32.26 |
| 2019 | 51 | 7.84 | 49.32 | **4.80** | 32.81 |
| 2020 | 13 | 7.69 | 49.41 | **4.69** | 31.53 |
| 2022 | 29 | 6.32 | 40.50 | **4.55** | 24.86 |
| 2023 | 9 | 8.73 | 50.73 | **4.25** | 11.47 |

**A 12% decline over five years.** The rho is enormous because the decline is
almost perfectly monotone, not because it is large. Spearman measures
monotonicity; it says nothing about size. Quote both or neither.

### The two estimators disagree in sign

| | continuous (this table) | snippet (published S10) |
|---|---|---|
| noise floor | −0.438 | −0.730 |
| amplitude | −0.400 | −0.432 |
| **SNR** | **−0.739** | **+0.105, n.s.** |

The published cross-subject conclusion is that **SNR is flat while yield
falls**, replicating across three animals and eight arrays. The continuous data
does not reproduce it on Rocky: SNR declines, consistently, by 12%.

Which is right is not settled here, and the honest reading is that a 12% effect
is well inside what the snippet estimator's known failure mode could
manufacture or erase. [[snippet_noise_floor]] shows that estimator is biased
1.1–1.3× high **and anti-correlated with the true floor**, and the snippet
noise trend (−0.730) is steeper than the continuous one (−0.438). An SNR built
on a noise floor that falls too fast will be held up artificially.

**What this does not license** is replacing one conclusion with the other. The
continuous layer covers Rocky and Fisk; the flat-SNR result spans three animals
and eight arrays, most of which have no broadband at all. What it does license
is dropping the word "robust" from the flat-SNR claim until the two layers are
reconciled on a subject where both exist.

### Reconciled on Fisk, and the estimator is implicated

Fisk's 140 session folders carry an unsorted `.nev` **and** an `.ns6` recorded
simultaneously, so both layers can be computed from the same recordings and
differ only in where the noise floor comes from.
`notebooks/scratch_fisk_layers.py`, **128** sessions with both.

The level difference is exactly the documented bias — snippet noise against
continuous at a ratio of **1.20**, inside the 1.1–1.3× range in
[[snippet_noise_floor]].

The trends:

| series | snippet SNR | continuous SNR |
|---|---|---|
| Rocky Anterior | +0.105 (n.s.) | **−0.739** |
| Rocky Posterior | +0.104 (n.s.) | **−0.719** |
| Fisk Medial | +0.224 (p = 0.077) | **−0.261** (p = 0.038) |
| Fisk Lateral | −0.047 (n.s.) | +0.026 (n.s.) |

**Correction, 2026-08-19.** The Fisk rows previously read 132 sessions and
+0.219 / −0.249 / −0.038 / +0.044. `scratch_fisk_layers.py` joined the two
layers on `(array, date)`, and two dates carry more than one session on the
same array — a many-to-many join that fanned four rows out to sixteen and
paired some snippet sessions against a *different* session's continuous
metrics. `scratch_fisk_figures.py` joins on the session stem, giving 128
sessions and the numbers above. The sign flip, its direction and its
significance are unchanged; only the fourth decimal moved.

**In every series where either layer finds a trend, the two flip sign, and the
snippet side is always the more positive.** Fisk Lateral is flat on both and
testifies to nothing — a sign flip between two null results is noise, not
evidence, and is excluded rather than counted.

Three of three, on two subjects, with a documented mechanism: the snippet noise
floor falls faster than the true one (Rocky −0.730 against −0.438; Fisk −0.151
against −0.509 on Medial), and a ratio whose denominator falls too fast is held
up artificially.

**So "flat SNR while yield falls" is most likely an artefact of the snippet
noise estimator.** The yield half stands — it is measured from labels, not from
the noise floor. The SNR half should not be quoted as evidence that signal
quality is preserved.

Plotted in `figures/fisk/layer/` by `notebooks/scratch_fisk_figures.py`:
`X1_level` puts the two noise floors on one axis against equality and shows the
gap is not constant; `X2_trend` puts the four rho values side by side and then
draws the two series per array, where the snippet trace is visibly the noisier
of the two.

The claim is bounded: two subjects, four array-series, and the underlying
effects are small (Rocky's continuous decline is 12% over five years). It is
enough to withdraw a conclusion, not enough to assert the opposite with
confidence.

### The metric definition matters here

`peak_snr_med` is the **median over channels of each channel's**
median(amplitude)/noise. That is not the ratio of the session medians, and on
this data they diverge: amp/noise from the yearly medians is 6.30, 6.29, 6.43,
6.41, 5.81 — essentially flat — while the median of per-channel ratios falls
4.85 → 4.25. The distribution across channels is changing shape even as the
aggregates track together. Any comparison of "SNR" between analyses must check
which of the two is meant.

## Fisk, 2023–2025

| metric | Lateral (n=65) | Medial (n=63) |
|---|---|---|
| noise floor | −0.405 (0.0008) | −0.504 (2.6e−05) |
| amplitude p50 | −0.294 (0.017) | −0.151 (0.24) |
| peak SNR | +0.026 (0.84) | −0.261 (0.039) |
| crossing rate | −0.036 (0.77) | −0.016 (0.90) |

A two-year-old implant, and the only consistent signal is a **falling noise
floor** on both arrays with no matching fall in yield. Fisk is early in its
life where Rocky's series is late.

## Electrode coverage does not survive the move to continuous data

`frac_elec_active` takes exactly **two distinct values across Rocky's 431
sessions** — 0.99 and 1.00. At 4·MAD every channel produces crossings in every
session, so the metric is saturated and carries no information.

This matters because [[robustness]] Q3 names electrode coverage **the most
reliable sorting-based longitudinal metric** — declining in all eight arrays,
significantly, with the lowest variance. That result is real and it is a
property of the **snippet** layer, where the NSP's own threshold was selective
enough to leave electrodes empty. Re-detecting from the trace at a fixed
multiple of each channel's own noise removes exactly the selectivity that made
the metric informative.

**Electrode coverage is a snippet-layer metric. Do not compute it from
continuous data and do not compare the two.**

## A bug worth recording

The µV gain was computed with `np.median` over `noise_uv / noise_raw`, a ratio
that carries a NaN wherever a channel has zero raw noise. `np.median`
propagates it, so **one dead channel made every amplitude in the session NaN** —
ten sessions reported 300,000–550,000 perfectly good crossings alongside a
missing amplitude. `np.nanmedian` fixes it. The tell was that the affected
sessions had healthy crossing counts, which is what a genuinely empty recording
would not.

## Related

[[equipment_comparison]] for the headstage contrast this extends,
[[snippet_noise_floor]] for the estimator the two layers disagree through,
[[robustness]] for the flat-SNR and electrode-coverage conclusions this
qualifies, [[threshold_crossing]] for the detection contract.

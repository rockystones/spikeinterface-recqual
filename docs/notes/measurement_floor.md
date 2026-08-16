# The measurement floor: how much the answer moves before biology does

S09. `notebooks/scratch_measurement_floor.py` → `data/derived/floor/`.
2,576 comparisons, **100% element-wise comparable**.

Because sorting never re-detects ([`monkey_corpus`](monkey_corpus.md)), every
variant of a recording labels the same list of spikes. Agreement is therefore a
confusion between two labellings, computed exactly — no spike matching, no
tolerance window.

## The four sources, measured

Relative difference in unit count, |b − a| / mean(a, b), median:

| source | n | rel. Δunits | ARI (kept spikes) | keep agreement |
|---|---|---|---|---|
| **operator vs self** (Sidd's redo) | 12 | **0.13** | 1.000 | 0.996 |
| **automatic vs DS** | 107 | 0.19 | 0.946 | 0.838 |
| **operator identity** (DS vs Sidd) | 30 | **0.25** | 0.995 | 0.935 |
| **automatic vs Sidd** | 243 | 0.28 | 0.995 | 0.876 |
| **algorithm choice** (8 OFS variants) | 2,184 | **0.36** | 0.889 | 0.873 |

On the 29-recording matched subset — the only place all four run on identical
input — the ordering is unchanged.

**Two operators disagree about 25%; an algorithm choice disagrees about 36%.**
Choosing a different clustering algorithm moves the unit count more than
swapping the human does.

## Operators disagree about inclusion, not about clustering

The decomposition matters more than the headline. Between DS and Sidd:

- **ARI on spikes both keep: 0.995.** They partition the kept spikes almost
  identically.
- **Keep agreement: 0.935.** 6.5% of spikes differ in whether they belong to a
  unit at all.
- **Noise assignment: unchanged**, median Δ = 0 across every comparison type.

So the operator difference is a **threshold-of-inclusion** difference, not a
clustering difference. Sidd keeps fewer units than DS by a ratio of 0.79
(IQR 0.72–0.97). Algorithms, by contrast, genuinely re-partition — ARI 0.889.

## Systematic or random — this decides whether the floor bites

A consistent offset cancels out of a trend computed within one operator, and
only breaks comparisons that cross operators. Random disagreement does not
cancel.

| source | same sign | ratio b/a (median, IQR) |
|---|---|---|
| operator vs self | **100%** | 1.14 (1.08–1.15) |
| automatic vs Sidd | 87% | 0.76 (0.67–0.87) |
| operator identity | 80% | 0.79 (0.72–0.97) |
| algorithm | 78% | 0.74 (0.57–0.96) |
| automatic vs DS | 65% | 1.12 (0.94–1.28) |

Sidd's redo is perfectly consistent — 12 of 12 in the same direction, ratio
tight at 1.14. It is a systematic revision, not noise.

The operator difference is largely but not wholly systematic (80%, ratio IQR
0.72–0.97). **A longitudinal series sorted throughout by one operator is
therefore mostly protected;** any series that changes operator part-way inherits
a ~21% step that looks like biology.

## The third source, which is larger than both

**Some sessions have a noise floor 4–5× the array's baseline.** The candidate
count is unchanged — the events are still detected — but the SNR ≥ 4 gate then
rejects nearly all of them.

| array | baseline | high-noise sessions | median units, normal | high-noise | ratio |
|---|---|---|---|---|---|
| Anterior | 11.1 µV | 10 / 169 (6%) | 76 | 4 | **0.06** |
| Posterior | 10.4 µV | 3 / 144 (2%) | 41 | 9 | 0.22 |

A relative effect up to **0.94** — 2.6× the algorithm floor, 3.7× the operator
floor, 7× the within-operator floor. Rocky 2017-09-29 is the clearest case: the
noise floor goes 14.6 → 58.9 µV between two sessions four days apart, candidates
stay at ~200, and the unit count falls from 176 to 11. It recovers to 80 a month
later.

**This is acquisition state, not electrode state**, and it is the largest single
source of variation in the series.

## What that does to the trend

Excluding high-noise sessions on the **acquisition criterion** — the session's
own noise floor, never its unit count, which would be circular:

| array | rho, all sessions | rho, excluding high-noise | dropped |
|---|---|---|---|
| Anterior | −0.092, p = 0.23 (n = 169) | **−0.273, p = 0.0005** (n = 159) | 10 |
| Posterior | −0.644, p = 2.9e−18 (n = 144) | **−0.706, p = 1.4e−22** (n = 141) | 3 |

**This is mostly not a new result, and saying so matters.** Nine of the ten
dropped Anterior sessions fall in September–October 2017, and
[`longitudinal_metrics.md`](longitudinal_metrics.md) already identified 2017 as
the confound that moves the anterior trend. Excluding 2017 wholesale gives
rho = −0.233, p = 0.004; adding the noise screen on top moves it to −0.236.
The two operations are nearly the same one.

What the noise criterion adds is **precision, not a new effect**:

- **2017 is not uniformly bad.** Its first four Anterior sessions (09-22 to
  09-28) sit at ~14 µV noise and ~150 units — entirely normal. An era exclusion
  discards them; the acquisition screen keeps them.
- **It catches sessions no era rule would**: 2019-05-30 Anterior (30.9 µV) and
  2019-05-23 Posterior (56.0 µV). Those two dates are independently flagged in
  [`impedance_parsing.md`](impedance_parsing.md) as single-array connection
  faults — two unrelated diagnostics converging on the same sessions.
- **It is defensible where "drop 2017" is not.** The criterion is the session's
  own noise floor, fixed before any outcome is looked at.

So: the anterior decline is real *given* acquisition screening, at
rho ≈ −0.24 to −0.27. It remains inside the −0.72 to +0.05 range the sensitivity
sweep reported, so the sweep's conclusion — that this trend is sensitive to
analysis choices — stands. What changed is that the largest single choice now
has a principled setting instead of an arbitrary one.

## The shape, which endpoints hide

Median units per session by year:

| year | Anterior | Posterior |
|---|---|---|
| 2017 | 11 (n=17) | 128 (n=12) |
| 2018 | 75 (n=49) | 52 (n=46) |
| 2019 | **85** (n=51) | 36 (n=50) |
| 2020 | 81 (n=13) | 33 (n=13) |
| 2022 | 60 (n=30) | 20 (n=23) |
| 2023 | 29 (n=9) | — |

**Anterior rises to 2019 and falls after.** Its first four sessions sit near 150
units and its 2017 median is 11, so any first-versus-last summary is meaningless
for it — an earlier draft of this analysis reported "152 → 25, exceeds the floor
by 5.7×", which is an artefact of picking endpoints from a non-monotone series.
Report the yearly shape, or a rank correlation on acquisition-screened sessions.

## The waveform pass: not every metric has the same floor

The table above is unit *count*. Running the project's own per-unit metrics over
1,226 of the same files (7 fail legitimately — no units after dropping classes
0 and 255) shows the floor is very far from uniform across metrics.

Median relative difference, **gated** — the scope the longitudinal metrics use:

| source | n | n_units | amp_med | amp_p99 | snr_med | rate_med |
|---|---|---|---|---|---|---|
| operator vs self | 12 | 0.045 | 0.011 | 0.005 | 0.017 | 0.137 |
| auto vs Sidd | 240 | 0.125 | 0.045 | 0.041 | 0.036 | 0.157 |
| **operator identity** | 30 | **0.161** | **0.017** | 0.030 | **0.015** | 0.164 |
| algorithm choice | 2,184 | 0.173 | 0.032 | 0.018 | 0.029 | 0.226 |
| auto vs DS | 104 | 0.267 | 0.041 | 0.070 | 0.042 | 0.363 |

**Amplitude and SNR are almost floor-free; counts are not.** Two operators
differ by 16% on how many units there are and by **1.7% on median amplitude**
and **1.5% on median SNR**. An algorithm change moves the count 17% and the
amplitude 3%.

The consequence is direct: a longitudinal claim about **amplitude or SNR is far
better supported than one about yield**, because the amplitude of a unit is a
property of the signal while the existence of a unit is a judgement call. The
flat-SNR result that holds across all three animals is therefore the most
robust thing in the cross-subject comparison, not the least.

Firing rate is the exception among waveform metrics (0.16 operator, 0.23
algorithm) — it depends on which spikes were assigned, so it inherits the count
problem.

### The gate mostly absorbs disagreement — except in one place

Ratio of gated spread to ungated spread; below 1 means the gate removes
disagreement:

| source | n_units | n_elec_with_units | amp_med | snr_med |
|---|---|---|---|---|
| operator vs self | 0.33 | 0.16 | 0.12 | 0.49 |
| auto vs Sidd | 0.45 | 0.28 | 0.30 | 0.31 |
| algorithm | 0.49 | — | 0.50 | 0.37 |
| operator identity | 0.64 | 0.80 | 0.52 | 0.83 |
| **auto vs DS** | **1.46** | **2.56** | 0.22 | 0.21 |

Gating helps everywhere except **automatic versus DS**, where it makes the
count disagreement *worse* — 1.46 on units and 2.56 on electrodes with units.

### The two operators have measurably different standards

Fraction of declared units that pass the project gate:

| variant | n files | pass fraction |
|---|---|---|
| OFS algorithms | 78 each | 0.18 – 0.33 |
| **DS** | 105 | **0.394** |
| automatic `-01` | 320 | 0.397 |
| **Sidd** | 241 | **0.659** |
| Sidd, redone | 12 | 0.671 |

**Sidd's units pass at 66%, DS's at 39%** — and DS sits exactly where the
automatic sort sits. Read with the label-pass result that Sidd keeps fewer
units (ratio 0.79) and that the two agree at ARI 0.995 on the spikes they both
keep: Sidd applies a stricter inclusion threshold and keeps cleaner units; DS
keeps more marginal ones, close to what OFS proposed. That is the "different
sorting standards" made quantitative, and it is a difference in *where the line
is drawn*, not in how the clustering is done.

## The trend against the per-metric floor

Rocky implant 1, acquisition-screened, best year to last year:

| array | metric | best → last | relative | operator floor | algorithm floor |
|---|---|---|---|---|---|
| Anterior | n_units | 117 → 29 | 1.21 | 0.16 | 0.17 |
| Anterior | amp_med | 104.2 → 76.6 | 0.31 | 0.02 | 0.03 |
| Anterior | snr_med | 7.2 → 6.5 | 0.09 | 0.02 | 0.03 |
| Posterior | n_units | 141 → 20 | 1.50 | 0.16 | 0.17 |
| Posterior | amp_med | 100.1 → 55.5 | 0.57 | 0.02 | 0.03 |
| Posterior | amp_p99 | 400.6 → 132.2 | 1.01 | 0.03 | 0.02 |
| Posterior | snr_med | 6.9 → 6.0 | 0.14 | 0.02 | 0.03 |

Every one exceeds both floors. The amplitude declines clear their floor by
10–20×, which is a wider margin than the count declines manage at 7–9×.

## Which OFS algorithms disagree most

Lowest agreement: `ScanKmean-J3` vs `TDIST-EM-3D-PSF` (ARI 0.733, Δ −230 units).
Highest: `TDIST-EM-3D-J3` vs `TDIST-EM-3D-PSF` (ARI 0.978, Δ −11).

`ScanKmean-J3` is the outlier — it appears in the four lowest-agreement pairs
and yields the most units of any variant. The `J3`/`PSF` axis matters less than
the clustering family, except within `TDIST-EM-3D` where it barely matters at
all.

## Limits

- The operator floor is measured on **Fisk and Rocky implant 2 (2023–2025)**;
  the algorithm floor on **Nigel**. The trend it sizes is **Rocky implant 1
  (2017–2023)**. That the spread transfers across that gap in protocol and
  hardware is an assumption.
- Every comparison here is conditional on the NSP's acquisition threshold, which
  is common-mode within a recording and invisible to all of it. Only `.ns5`
  re-detection can see it — see [`analysis_plan`](../analysis_plan.md) S11.
- This is the label-only pass. Amplitude and SNR spread need the waveform pass.

## Related

[[monkey_corpus]] for the variant vocabulary and the no-re-detection result,
[[longitudinal_metrics]] for the trends this sizes, [[snippet_noise_floor]] for
the noise estimator whose excursions drive section 6.

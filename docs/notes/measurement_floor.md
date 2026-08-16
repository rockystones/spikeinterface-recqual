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

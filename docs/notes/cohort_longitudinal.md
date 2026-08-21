# Cross-subject longitudinal metrics, and the headstage control

S10 and S12. `scratch_cohort_longitudinal.py` and `scratch_headstage_pairs.py`
→ `data/derived/cohort/`. **1143 recordings, 15 array-implants, 7 subjects,
2009-03 → 2025-09**, of which 871 carry a unit yield.

The original file was 693 recordings across the three Blackrock subjects.
`scratch_cohort_extend.py` added Chase, Oops, Picasso and Luigi — see
[`cohort_extension`](cohort_extension.md) for what each contributes and for
the two things the added rows do *not* support. Every claim below about eight
arrays still refers to the Blackrock eight unless it says otherwise.

Sized against the floors in [`measurement_floor`](measurement_floor.md).

## Method, and three choices that matter

**One sorting method throughout.** Every subject is scored on the Plexon `-01`
automatic sort, which exists for all of them. S09 put the algorithm floor at
0.17–0.36 relative difference in unit count, larger than the operator floor;
mixing methods across subjects would inject exactly that spread into a
comparison whose purpose is holding method constant.

**An acquisition screen before any trend.** Sessions whose own noise floor
exceeds 2× that array's median are excluded — never on unit count, which would
be circular. Screened out: Rocky I1 Anterior 13/184, Posterior 5/190, Nigel
Anterior 6/78, Posterior 3/79, Fisk SN1498 4/71, everything else 0.

**Days since first recording, not implant age.** Only Rocky implant 2 has a
surgery date on record, so a true age axis exists for **one of eight arrays**.
The rest align at their own first session, which assumes each series starts at a
comparable point post-implant. Surgery dates for Nigel, Fisk and Rocky implant 1
would materially sharpen every cross-subject statement here.

## Six of eight arrays decline

Units per electrode, acquisition-screened:

| array-implant | n | rho | p | first → last | span |
|---|---|---|---|---|---|
| Nigel Posterior | 76 | **−0.791** | 2e−17 | 1.17 → **0.00** | 643 d |
| Rocky I2 Posterior | 10 | −0.758 | 0.011 | 0.84 → 0.59 | 62 d |
| Rocky I1 Posterior | 185 | **−0.732** | 3e−32 | 1.81 → **0.00** | 2205 d |
| Nigel Anterior | 72 | **−0.642** | 1e−9 | 1.02 → 0.16 | 973 d |
| Chase Array1 | 19 | −0.519 | 0.023 | 0.67 → 0.32 | 343 d |
| Fisk SN1504 | 71 | −0.421 | 3e−4 | 1.30 → 1.08 | 702 d |
| Fisk SN1498 | 66 | −0.227 | 0.066 | 0.92 → 0.98 | 702 d |
| Rocky I1 Anterior | 171 | −0.183 | 0.017 | **2.37 → 0.19** | 2205 d |
| Rocky I2 Anterior | 10 | +0.018 | 0.96 | 0.89 → 0.81 | 62 d |

**Nigel's Posterior array reaches zero in 643 days** — faster than Rocky's took
in six years. Both Nigel arrays fall steeply. Rocky implant 2's Posterior is
already declining within its first 62 days, on 10 sessions.

**Two Rocky I1 endpoints in this table were wrong until 2026-08-19.** `trends()`
took `head(5)`/`tail(5)` of each group without sorting by date, and `groupby`
preserves row order, not date order. Fisk, Nigel and Rocky I2 happened to be
stored date-ordered and were unaffected; both Rocky I1 arrays were not.
Anterior read `0.19 → 0.19` and is really **2.37 → 0.19**; Posterior read
`0.27 → 0.00` and is really **1.81 → 0.00**. Every rho and p in the table was
always computed against the date and was never affected.

The correction changes one reading materially. Rocky I1 Anterior's weak rho
(−0.183) was previously paired with flat endpoints, which together said
"this array did not decline". The endpoints say it fell **12.6-fold**. Both are
true: the array drops hard and early, then scatters around a low plateau for
four more years, and a rank correlation over 171 sessions dilutes a step into a
weak monotone trend. **Read rho and the endpoints together; neither alone
describes this series.**

## The result that replicates everywhere

| metric | Fisk ×2 | Nigel ×2 | Rocky I1 ×2 |
|---|---|---|---|
| units per electrode | −0.23, −0.42 | −0.64, −0.79 | −0.18, −0.73 |
| electrode coverage | −0.27, −0.50 | −0.66, −0.77 | −0.21, −0.74 |
| **median unit SNR** | **+0.08, +0.23** | −0.30, −0.39 | **+0.10, +0.10** |

**Yield and coverage fall; median unit SNR does not.** Units are lost, survivors
are not degraded. An array does not fade — it sheds electrodes while the ones
still working keep working.

This was the Rocky finding and it now holds across three animals and eight
arrays. It is also the *best-supported* thing here rather than the weakest:
S09's waveform pass puts the operator floor on median SNR at **0.015** and on
unit count at **0.161**, so a flat-SNR claim rests on a metric an order of
magnitude less sensitive to who sorted it.

**Two of the five animals are exceptions, not one.** Nigel's SNR declines
(−0.30, −0.39) alongside the steepest yield loss in the cohort, and Chase —
added 2026-08-19 — lands next to it at −0.47 SNR against −0.52 yield. So the
flat-SNR result holds on Fisk and Rocky (four arrays, +0.08 to +0.23) and fails
on Nigel and Chase (three arrays, −0.30 to −0.47). What separates them is not
yet established; the exceptions are also the steepest yield declines, which
would be the first thing to test.

**Luigi Array2 is a third exception, with a caveat.** Its 150 sorted sessions
give SNR rho −0.318 against yield −0.624 — the same signature. But that series
carries an apparent gain step between January and February 2013, so its
whole-series rho mixes a step with a trend and should not be quoted beside the
others without reading [[cohort_extension]] first. Oops and Picasso still
cannot weigh in: 6 and 4 sorted blocks.

## An oddity: the noise floor falls over time

`noise_med` declines on six of eight arrays (−0.21 to −0.78). That is the
opposite direction from the usual encapsulation account, where impedance and
noise rise as tissue responds.

**Recorded, not explained.** Candidate explanations that have *not* been tested:
a changing NSP threshold admitting fewer marginal crossings; the noise estimate
being taken over candidates whose composition shifts; or a genuine drop in
background activity. The first is the one S11 can settle, since re-detection at
a fixed threshold removes it by construction.

## S12 — analog against digital headstage

121 date × array slots on Rocky implant 1 carry both headstages recording the
same session. The comparison is **not** fixed-event: two physical recordings
have different threshold crossings, so only session-level metrics are compared.

### Analog is noisier — and also larger, which changes the reading

Paired Wilcoxon, 35 screened pairs, analog ÷ digital:

| metric | analog | digital | ratio | p |
|---|---|---|---|---|
| noise floor | 12.23 µV | 10.01 µV | **1.22** | 5e−07 |
| median amplitude | 80.63 µV | 63.88 µV | **1.26** | 8e−10 |
| p99 amplitude | 241.75 µV | 201.69 µV | 1.20 | 1e−05 |
| **median SNR** | 6.45 | 5.98 | **1.08** | 0.011 |
| units per electrode | 0.38 | 0.27 | 1.38 | 0.90 |

The owner's expectation that analog is noisier is confirmed. But **signal and
noise scale together**, so SNR — the scale-invariant measure — is essentially
unchanged at 1.08.

The digitization factor is identical on both (`wf_gain = 0.25 µV/count`,
checked on three pairs), so the 1.2× is real microvolts, not a units artefact.
Something in the analog chain scales both signal and noise by about a fifth.

Two consequences:

- **A longitudinal series that mixes headstages inherits a ~1.2× amplitude and
  noise step** that looks like biology. Rocky implant 1 switched from analog to
  digital during 2018–2019, squarely inside the series.
- **The pair is a weaker graded benchmark than hoped.** `_MONKEY-PLAN.md` §2
  proposes it as a hard-case/easy-case pair for measuring how a sorter degrades.
  At equal SNR it mostly is not graded.

### S12b — redone sorting-free on all 121 pairs

`scratch_headstage_free.py`. Dropping the sorter removes the selection step:
every slot has an original NEV for both headstages, so all **121 pairs** enter
(107 after the acquisition screen, applied per array *and headstage* because
the two amplifiers sit at different floors).

Nothing here reads a unit label — only the NSP's threshold crossings and the
baseline they sit on.

| metric | analog | digital | ratio | p |
|---|---|---|---|---|
| noise floor | 12.23 µV | 9.82 µV | **1.25** | 6e−18 |
| noise p90 | 15.38 µV | 12.23 µV | 1.26 | 1e−15 |
| **crossings** | **283,985** | **354,653** | **0.80** | 9e−08 |
| crossing rate | 15.55 Hz | 20.48 Hz | 0.76 | 7e−08 |
| median amplitude | 60.0 µV | 45.0 µV | **1.33** | 3e−19 |
| p90 amplitude | 136.5 µV | 110.8 µV | 1.23 | 7e−17 |
| max amplitude | 972.8 µV | 492.0 µV | **1.98** | 6e−09 |
| **peak SNR** | 2.87 | 2.92 | **0.98** | 0.001 |

**This is a gain difference, not a quality difference.** Noise and amplitude
both scale by ~1.25, and peak SNR — their ratio, the scale-invariant measure —
is 0.98. The p-value is small only because n = 107; a 2% effect is nothing.

Two things fall out that the sorted pass could not see:

**Analog yields 20% *fewer* threshold crossings.** With a threshold fixed in
microvolts a noisier channel would cross *more* often, so this says the NSP
threshold was set as a multiple of RMS: a higher noise floor raises the absolute
bar and admits fewer events. That is a direct, if indirect, measurement of how
the online threshold behaves — and it is the mechanism S11 exists to remove.

**Analog's largest event is 2× digital's** (973 vs 492 µV), far beyond the 1.25
gain factor. Consistent with the analog chain picking up more large artifacts,
which is what [`giant_events.md`](giant_events.md) classifies.

### The amplifiers disagree about the trend

Spearman rho against date, within the 2018-04 → 2019-07 paired window:

| array | crossing rate | noise floor | median amplitude | peak SNR |
|---|---|---|---|---|
| Anterior | a **+0.39** / d +0.01 | a **+0.63** / d −0.10 | a **+0.53** / d −0.23 | a −0.40 / d +0.15 |
| Posterior | a **+0.32** / d −0.05 | a **+0.69** / d +0.06 | a **+0.66** / d −0.43 | a −0.50 / d −0.47 |

**The analog headstage's own noise floor rose over those 14 months (+0.63,
+0.69) while the digital one stayed flat.** Amplitude follows it up, and peak
SNR consequently falls on analog.

So the analog recordings carry **amplifier drift on top of any physiology**, and
the two arrays agree about that drift — which is what identifies it as the
amplifier rather than the tissue. Any longitudinal metric computed from analog
sessions inherits it. This is precisely the confound the paired design was built
to expose, and it is larger than the between-amplifier offset.

### Why the earlier sorted pass saw only 40 pairs

Only **40 of the 121** slots have an automatic sort for *both* members. All 121
have the original NEV; the gap is entirely on one side:

| headstage | originals | with `-01` |
|---|---|---|
| analog | 122 | **40** |
| digital | 275 | 275 |

**Four of five analog recordings were never sorted.** Testing whether the sorted
40 are representative: they carry a median 254,978 threshold crossings against
306,507 for the 82 unsorted ones (p = 0.023), over the same date range. The
cleaner analog sessions were the ones put through OFS.

That bias runs *against* the finding rather than inflating it, and the
sorting-free redo above confirms it: 1.25× on all 121 pairs against 1.22× on the
selected 40. The sorted pass was directionally right and is superseded.

### Does the headstage change the trend?

| array | units/electrode | median SNR | median amplitude |
|---|---|---|---|
| Anterior | analog **+0.15**, digital **−0.16** | −0.04, −0.31 | +0.47, +0.18 |
| Posterior | analog −0.68, digital −0.75 | +0.49, +0.32 | +0.67, +0.53 |

On Posterior — the array that actually failed — the two amplifiers agree
closely (−0.68 vs −0.75). On Anterior, where the effect is weak, they disagree
in sign. Large effects survive the amplifier; small ones do not, which is the
same lesson the measurement floor teaches.

## Related

[[measurement_floor]] for the per-metric floors these are sized against,
[[monkey_corpus]] for the corpus and variant vocabulary,
[[longitudinal_metrics]] for the Rocky-only predecessor.

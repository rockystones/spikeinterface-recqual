# Cross-subject longitudinal metrics, and the headstage control

S10 and S12. `scratch_cohort_longitudinal.py` and `scratch_headstage_pairs.py`
→ `data/derived/cohort/`. 693 recordings, 8 array-implants, 3 subjects,
2017-09 → 2025-09.

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
| Rocky I1 Posterior | 185 | **−0.732** | 3e−32 | 0.27 → **0.00** | 2205 d |
| Nigel Anterior | 72 | **−0.642** | 1e−9 | 1.02 → 0.16 | 973 d |
| Fisk SN1504 | 71 | −0.421 | 3e−4 | 1.30 → 1.08 | 702 d |
| Fisk SN1498 | 66 | −0.227 | 0.066 | 0.92 → 0.98 | 702 d |
| Rocky I1 Anterior | 171 | −0.183 | 0.017 | 0.19 → 0.19 | 2205 d |
| Rocky I2 Anterior | 10 | +0.018 | 0.96 | 0.89 → 0.81 | 62 d |

**Nigel's Posterior array reaches zero in 643 days** — faster than Rocky's took
in six years. Both Nigel arrays fall steeply. Rocky implant 2's Posterior is
already declining within its first 62 days, on 10 sessions.

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

Nigel is the partial exception — its SNR does decline (−0.30, −0.39) alongside
the steepest yield loss in the cohort.

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

### The 40 pairs are a selected subset, and the selection is not neutral

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

That bias runs *against* the finding, so 1.22× is a lower bound on the noise
difference rather than an inflation of it. It does not rescue the comparison:
the honest fix is to recompute the headstage contrast from **sorting-free
metrics on all 121 original NEVs**, which needs no `-01` and so has no selection
step. Not yet done.

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

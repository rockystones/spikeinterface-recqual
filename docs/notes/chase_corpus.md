# Chase: the corpus with an external record, and what it says

19 readable Plexon sessions, 2009-03-17 to 2010-02-23, from one Utah array
whose history an operator wrote down at the time.

`notebooks/scratch_chase.py` → `data/derived/chase/`.

| date | event, from the corpus README |
|---|---|
| 2009-02-26 | array implanted |
| 2009-03-17 | first day of brain control |
| 2009-08-24 | repair surgery (skin around the pedestal) |
| 2009-08-25 | notes: "many of the units from one and one-half weeks ago are still there" |
| 2009-08-27 | notes: **"sharp decline"** in unit quality |

Every other longitudinal conclusion in this project is data checked against
data. This is the one place a metric can be checked against an independent
record of what happened to the array.

## The headline: the documented event is not visible as an event

**There is a strong decline across the series**, and it is the most convincing
longitudinal signal in the project:

| metric | rho vs date | p |
|---|---|---|
| **crossing rate** | **−0.791** | 5.5e−05 |
| **unit amplitude (median)** | **−0.698** | 0.00088 |
| unit SNR (median) | −0.472 | 0.041 |
| unit count | −0.458 | 0.048 |
| peak SNR | −0.351 | 0.14 |
| sorting-free amplitude p50 | −0.244 | 0.31 |
| noise floor | +0.037 | 0.88 |

**But nothing steps at 2009-08-27.** Removing a linear date trend and asking
how far that session sits below it:

| metric | residual on 2009-08-27 |
|---|---|
| unit count | −1.45 SD |
| sorting-free amplitude p50 | −1.24 SD |
| unit amplitude | −0.61 SD |
| peak SNR | −0.50 SD |
| crossing rate | −0.41 SD |
| unit SNR | **+0.27 SD** |

With 19 sessions, a session at ±1.5 SD is unremarkable. The operator's "sharp
decline" does not appear as a discontinuity in any of these summaries.

**A first-half/second-half split looks like it validates the event, and does
not.** Splitting at 2009-08-27 gives 9 sessions before and 10 after, and
reports unit amplitude down 1.63× (p = 0.0009), crossing rate down 3.04×
(p = 0.002), unit SNR down 1.22× (p = 0.016). Every one of those is the
monotone trend above being cut near its middle. A declining series produces
exactly this whether or not anything happened on that date. **The split is not
a test and should not be quoted as one.**

## How to read that

Three explanations, and this data cannot separate them:

1. **The note is about particular units the operator was tracking**, not about
   the population summary. "Many of the units from one and one-half weeks ago
   are still there" is the language of someone following named units.
2. **The decline was real and gradual**, and 08-27 is when it became obvious
   rather than when it happened.
3. **The summaries genuinely miss it.**

What can be said is narrower and still useful: **a summary metric that would
have flagged 2009-08-27 as special does not exist among these.** Any claim in
this project that a longitudinal metric detects a discrete failure event now
has one external test it did not pass.

## Confounds this corpus carries

- **Recording length varies 1,423 to 9,286 s** and correlates with unit count
  (rho = +0.479, p = 0.038). Unit count is therefore partly a measure of how
  long the operator ran that day. It does not track date (rho = +0.218,
  p = 0.37), so it does not manufacture the trend, but it inflates the
  session-to-session scatter that the step test is measured against.
- **Crossing rate depends on the Plexon threshold setting.**
  [[equipment_comparison]] showed crossing rate is an instrument choice rather
  than a yield, and it is the strongest trend here (−0.791). Treat it as the
  least trustworthy of the declining metrics, not the most, despite its p.
- **The noise floor is flat** (rho = +0.037). Whatever declined, it was signal,
  not the amplifier.

## Format notes

Plexon declares what TDT hides, which makes this the easiest corpus to read
correctly:

| | value | note |
|---|---|---|
| `NumPointsPreThr` | 8 | pre-threshold samples, **declared** |
| `NumPointsWave` | 32 | snippet length |
| `ADFrequency` | 40000 | NEO's `wf_sampling_rate` reads **0**; use this |
| `Year/Month/Day` | — | recording date in the header |

The header date agrees with the filename in **19 of 19** files, which is worth
knowing given that the TDT tree needed a ruling to reconcile three date sources.

`NumPointsPreThr = 8` against a measured modal trough of **9** is not a
conflict: the crossing is detected at sample 8 and the minimum lands one sample
later. 8 is the correct baseline boundary.

**Units, checked and not assumed.** NEO derives Plexon `wf_gain` from
`SpikeMaxMagnitudeMV`, so `raw * wf_gain` is **millivolts** and microvolts need
a further ×1000. `wf_units` is left empty, so nothing warns. Anchored on the
physics: the noise floor is **12.5 µV** under that reading and 12,520 µV under
the volts reading, and extracellular noise is 5–20 µV. This is the third format
in the project where NEO's units needed independent verification — see
[[tdt_corpus]] for the other two.

**One file of 20 failed to parse** and is excluded; the other 19 read cleanly.

## Related

[[equipment_comparison]] for why crossing rate is the weakest of these trends,
[[measurement_floor]] for the per-metric floors these declines should be read
against, [[robustness]] for the longitudinal-reliability question this corpus
was brought in to test.

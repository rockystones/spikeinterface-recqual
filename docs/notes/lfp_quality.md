# The LFP layer, and why most of this corpus has no LFP

CLAUDE.md puts LFP in scope and says it must be handled alongside spikes rather
than as an afterthought. Building it turned up a corpus fact that contradicts
the project's own stated file conventions — **both** of them.

`notebooks/scratch_lfp_quality.py` → `data/derived/lfp/`.

## The rule: read the header, never the suffix

Blackrock records the filter the NSP applied in the nsX extended header, in
**millihertz**:

```python
raw = BlackrockRawIO(filename=stem, nsx_to_load=nsx_id, load_nev=False)
raw.parse_header()
h = raw._nsx_ext_header[nsx_id][0]
hp = h["hi_freq_corner"] / 1000.0     # high-pass, Hz
lp = h["lo_freq_corner"] / 1000.0     # low-pass, Hz
```

`nsx_filter()` reads those and refuses any stream cornered above 30 Hz. The
same guard serves both file types, which is the point — it is a statement about
the band, not about the suffix.

## What the corpus actually contains

Header corners, confirmed against the measured spectrum on 9 sessions spanning
each subject's full span:

| subject | stream | corners | power 1–80 Hz | power >250 Hz | LFP? |
|---|---|---|---|---|---|
| Fisk | `.ns6` | 0.3–7500 Hz | **0.33 – 0.79** | 0.02–0.09 | **yes** |
| Nigel | `.ns5` | **250**–7500 Hz | **0.0000** | 0.94–0.99 | no |
| Rocky | `.ns5` | **250**–7500 Hz | **0.0000** | 0.97–1.00 | no |
| Rocky (2017-10-30) | `.ns5` | **750**–7500 Hz | 0.0000 | 1.0000 | no |
| Fisk | `.ns3` | **300**–1000 Hz | 0.002 | 0.94 | no |

**498 of the corpus's 626 continuous files carry no LFP.** They are spike-band
streams that happen to be sampled at 30 kHz. The spectrum is not merely low
below 80 Hz — it rounds to **zero at four decimal places**, which is what a
250 Hz high-pass does and nothing else does.

So the LFP layer covers **Fisk only** on Blackrock. Nigel and Rocky have no
`.ns3` either (zero files, both subjects), so there is no Blackrock route to
LFP for them at any point in their recorded history. That is not a gap to be
filled by better code.

| corpus | stream | rate | genuine LFP? |
|---|---|---|---|
| Fisk `.ns6` | broadband | 30 kHz | **yes** — derived here |
| Fisk `.ns3` | 300–1000 Hz band-pass | 2 kHz | no |
| Nigel `.ns5` | 250 Hz high-pass | 30 kHz | no |
| Rocky `.ns5` | 250 Hz high-pass | 30 kHz | no |
| TDT `pNe*` | low-pass | 763 Hz (Luigi 2013: 1526) | **yes**, all 370 blocks |

The TDT `pNe` store is the only other genuine LFP, and it covers Oops, Picasso,
Luigi and Rocky's TDT era. It is **int16 ADC counts with no recorded scale**
([[tdt_corpus]]), so amplitudes from it are in counts; only ratios — line
fraction, band fractions, cross-channel correlation — compare with a
Blackrock-derived LFP.

## Deriving LFP from broadband

`broadband_to_lfp()` band-passes then decimates:

| step | SI call | why |
|---|---|---|
| band-pass | `bandpass_filter(rec, 0.5, 250, margin_ms=10000)` | 250 Hz **is** the anti-alias filter |
| decimate | `decimate(rec, 30)` | 30 kHz → 1 kHz, Nyquist 500 ≫ 250 |

Both are lazy wrappers — `BandpassFilterRecording` and `DecimateRecording` —
so nothing is read until `get_traces`, and the 60 s slice is pulled in 30 s
chunks to bound the parent read at ~350 MB rather than materialising 60 s of
30 kHz × 96 ch at once.

**`decimate` does no anti-aliasing.** Its own docstring says so and points at
`resample` as the safe choice. It is safe *here* only because the band-pass
above already removed everything over 250 Hz. `resample` was considered and
rejected: it is FFT-based, so it wants a whole segment in memory, and the
anti-alias filter it would need is one this layer applies anyway. Filtering
first makes the aliasing argument explicit instead of delegating it.

### `margin_ms` is the parameter that decides whether this is correct

SI's default is **5 ms**, sized for a 300 Hz spike-band corner. A 0.5 Hz
high-pass has a time constant of ~0.32 s, so 5 ms of context leaves a settling
transient at every chunk boundary. Measured on Nigel's `.ns5`, chunked and
one-shot reads differed by **18.5 µV against a 0.25 µV median signal** — 74×
the signal — and correlation against a scipy reference fell to 0.48 on some
channels.

The error decays cleanly with the margin. Measured on a pure 10 Hz tone,
chunked against one-shot, as a fraction of signal amplitude:

| `margin_ms` | error |
|---|---|
| 3000 | 6.7e-3 |
| 6000 | 3.4e-4 |
| **10000** | **5.8e-6** |
| 20000 | 1.7e-7 |

10 s is where it stops mattering, and the cost is a 50 s parent read per 30 s
of output. On real Fisk broadband the same comparison is bit-identical and
correlation against `sosfiltfilt` is 0.992–0.998.

Both invariants are pytest cases in `tests/test_lfp_quality.py`, along with a
control that runs `decimate` **without** the band-pass and requires the alias
to actually appear — a test that cannot fail is worse than no test.

The general form: **a chunked filter's margin must scale with its lowest
corner, not with the default.** Any SI filter chain reaching below ~10 Hz needs
this raised, and the failure is silent — the traces look plausible either way.

## What the layer measures

Three quantities chosen because the spike layer cannot see them:

- **60 Hz line power as a fraction of total.** Mains contamination is an
  acquisition fault, and a 250 or 300 Hz high-pass removes it completely — so a
  grounding problem is invisible to every other metric in this project. This is
  the strongest argument for the layer existing at all, and it is also why
  Nigel and Rocky can never be checked for it.
- **Band power** (delta → gamma), normalised, so a spectral shift separates
  from an amplitude change.
- **Median cross-channel correlation.** A shorted, bridged or common-referenced
  array approaches 1; volume conduction alone leaves it moderate. The closest
  thing in the corpus to a direct hardware-fault test, with no spike-layer
  equivalent.

Segment choice is explicit (`pick_segment`): the longest segment of at least
5 s, never `segment_index=0` by default, per [[segment_handling]].

## The guard has to fail closed

The first corpus pass reported **28 Rocky sessions with valid LFP metrics** --
delta fractions, cross-channel correlations, the lot. Every one was false.

```python
try:
    filt = nsx_filter(job["path"], int(job["stream"]))
    ...
except Exception:      # a missing header must not stop the read
    pass               # <- and now the guard does not run
```

NEO refuses to parse a Blackrock file whose `.nev` and `.nsX` disagree on
segment count (*"12 segments present in .nev file, but 4 in ns5"*), which is
true of exactly those 28 sessions. The exception was swallowed, `is_lfp` was
never set, and the layer went on to integrate LFP bands over a stream with
**0.0000** of its power below 250 Hz. The output looked like data: rms 1.7 uV,
corr_med 0.20, delta_frac 6e-5.

The tell was the 20x rms gap against Fisk, not anything in the numbers
themselves. Re-read with the fix, all 28 report 250 Hz (27) or 750 Hz (1) and
are correctly rejected. **Rocky has no LFP session at any point in its span.**

Two changes, both needed:

- **Fail closed.** An unreadable band is a reason to refuse the session, not a
  reason to proceed without checking. `error="band unknown: ..."`.
- **Read the header without the `.nev`.** `BlackrockRawIO(..., load_nev=False)`
  skips the consistency check entirely; the band lives in the nsX extended
  header and the `.nev` was never needed for it.

The general lesson is narrower than "handle exceptions": **a validity check
wrapped in try/except-and-continue is not a check.** It is a check on the happy
path only, and the sessions that fail to parse are exactly the ones most likely
to be irregular in other ways.

## What it found: a grounding fault that reads as array death

The layer was built to see acquisition faults the spike band structurally
cannot. It found one on its first corpus pass.

**Eight sessions, 2025-02-26 to 2025-03-26.** Before that date, 113 sessions
across two years never exceed **0.045** of total LFP power at 60 Hz. During it,
Fisk Lateral reaches **0.76** — three quarters of the entire LFP spectrum
sitting on mains.

It reached the spike layer hard. Joined to `cohort_sessions` (n=8 contaminated
against 123 clean):

| metric | contaminated | clean | p |
|---|---|---|---|
| noise floor | **20.8 µV** | 11.1 µV | 3e-06 |
| units per electrode | **0.33** | 0.98 | 9e-05 |
| unit yield | **32** | 94 | 9e-05 |
| pass fraction | **0.31** | 0.66 | 9e-04 |
| median amplitude | **112 µV** | 59 µV | 2e-05 |
| median SNR | **5.68** | 4.97 | 1e-03 |

**Note the last two rows.** Amplitude and SNR both go *up* on the broken
sessions — survivorship, because only the largest units clear the gate once the
floor triples. A quality screen reading SNR alone would rank these sessions
above the healthy ones. This is the concrete form of the caution the flat-SNR
result needs ([[cohort_longitudinal]]): SNR conditioned on surviving units is
not a measure of recording health.

### Two arguments that it is the rig, not the tissue

**Dose-response across arrays.** Same rig, same days:

| array | line fraction | units/electrode | noise |
|---|---|---|---|
| Lateral (SN1498) | 0.64–0.76 | 0.90 → **0.08** | 10.7 → **30.4 µV** |
| Medial (SN1504) | 0.11–0.16 | 1.14 → **0.60** | 11.5 → **15.6 µV** |

**Interleaving.** A single clean session on **2025-03-05** sits between two
contaminated ones and reads 0.84 units per electrode at 9.6 µV — baseline on
both arrays, as do the post-fault sessions from 2025-04-23 on. Nothing physical
recovers and re-fails on a weekly cadence.

Without this layer, Feb–Mar 2025 on Fisk Lateral is a 91% collapse in yield
with a tripled noise floor, in the last months of the record. That is exactly
the shape of end-of-life array failure, and it would have been scored as such.

**Consequence for the longitudinal analysis:** the eight contaminated sessions
must be excluded from, or flagged in, any degradation claim about Fisk. The
trends in `fig_longitudinal` are computed on clean sessions only.

### What the clean sessions show

Trends over 2023-06 to 2025-05, clean sessions only (n=61 Lateral, 59 Medial):

| metric | Lateral | Medial |
|---|---|---|
| cross-channel correlation | **+0.503** (p=4e-05) | **+0.290** (p=0.026) |
| delta fraction | **−0.334** (p=0.009) | **−0.538** (p=1e-05) |
| LFP rms | +0.061 (p=0.64) | −0.343 (p=0.008) |
| gamma fraction | −0.295 (p=0.021) | +0.022 (p=0.87) |

Rising cross-channel correlation on both arrays is the finding with **no
spike-layer equivalent** — it is what bridging, a degrading reference, or
increasing common-mode pickup looks like, and no unit metric would show it.
Falling delta on both is consistent with the same drift. Neither is proof of a
mechanism; both are visible only because the layer exists.

## The reason this was worth checking twice

The first run of this layer computed delta/theta/alpha/beta fractions of 0.000
from Fisk's `.ns3`. Those numbers were not a bug — they are what you get when
you integrate an LFP band over a signal that has none. **A metric computed from
the wrong stream looks exactly like a metric computed from the right one.**

The `.ns3` finding then made the `.ns5` assumption suspect by the same
argument, and it turned out to be wrong in the same way. Neither would have
surfaced from the data alone: the sorters ran fine on a 250 Hz high-passed
stream, because that is roughly what a spike-band filter produces anyway.

**One consequence reaches past LFP.** Nigel's and Rocky's continuous data
arrives already high-passed at 250 Hz while Fisk's does not, so the pipeline's
own spike-band filter is doing different amounts of work per subject. Any
cross-subject comparison of noise floor or waveform shape has to account for
that; within-subject longitudinal trends are unaffected, because the NSP
configuration is constant across each animal's span.

## Related

[[tdt_corpus]] for the `pNe` stores and their units, [[fisk_impedance]] for the
rest of the Fisk drop, [[threshold_crossing]] for the spike-band layer this
complements, [[segment_handling]] for the segment rule.

# Fisk: impedance measured beside the ephys, and how far to trust it

The first corpus in this project where **impedance is recorded on the same days
as the recordings**, which is what CLAUDE.md's multimodal thread was waiting
for. It is also the first where a single impedance reading turns out not to
mean much.

`notebooks/scratch_fisk_impedance.py` → `data/derived/fisk/`.

## What arrived

215 GiB. Two arrays, each with its own `Recordings/` folder holding session
directories and impedance files side by side.

| | Lateral (SN 1025-001498) | Medial (SN 1025-001504) |
|---|---|---|
| sessions | 71 | 69 |
| dates | 2023-06-05 → 2025-05-07 | 2023-06-05 → 2025-05-07 |
| with `.nev` | 71 | 69 |
| with `.ns3` LFP | 71 | 69 |
| with `.ns6` broadband | 65 | 63 |
| size | 88.1 GiB | 88.4 GiB |
| impedance files | 41 | 40 |
| impedance dates | 2023-06-05 → 2024-05-31 | 2023-06-05 → 2024-06-05 |

**Array anatomy is finally stated outright.** The folder names give
`1025-1498 (Fisk Right M1 Lateral)` and `1025-1504 (Fisk Right M1 Medial)`,
matching the serials already in `configs/subjects/fisk.json`. No inference
needed, unlike the TDT stores.

A `DS vs Sidd/` tree also arrived: 170 curated `.nev` per operator with
`.wfexp.mat` beside them, and **7–10 sessions per array carry both operators**
— an operator-floor pair set on a subject and era S09 did not cover.

## The format is not Rocky's, and they must not be pooled

| | Rocky | Fisk |
|---|---|---|
| instrument | potentiostat EIS | Blackrock AutoImpedance, written by Central |
| per electrode | 19 frequencies, 1 MHz → 1 Hz | **one** reading |
| layout | 6 files per array per date | 1 file per array per date |
| readout used | magnitude at 1 kHz | whatever the rig reports |

A 1 kHz EIS magnitude and an AutoImpedance estimate are different
measurements. Nothing in [[impedance_parsing]] applies here, and the two tables
should never be concatenated.

**The calibration is constant**, which is the one thing that had to be checked
before comparing dates: `m = 5.40, expected = 4460, b = 34.00` on all 81 files
across both arrays. Readings from different dates are on one scale.

## A single reading cannot classify an electrode

This is the finding that governs how the data can be used.

| array | channels | dates | never cross 1 MΩ | median crossings | max |
|---|---|---|---|---|---|
| Lateral | 96 | 41 | **22** | **7** | 17 |
| Medial | 96 | 40 | 19 | 6 | 23 |

If a high reading meant degradation, a channel that crossed 1 MΩ would stay
across. Instead the median channel crosses the line **seven times** over the
series, and only about a fifth never cross at all. The count above the line
fluctuates between adjacent weeks — Lateral runs 43, 37, 34, 31, 39, 34, 40
over six consecutive measurement dates — with no monotone trend.

The file header warns of exactly this: *"Impedance values are estimates and may
be affected by noise."*

**So: use a per-channel median across dates, never one reading**, and treat
1 MΩ as a reporting convention rather than a diagnosis. Any analysis that
labels an electrode dead from a single AutoImpedance file is labelling noise.

Distribution over all 7,774 readings, for orientation:

| array | 25% | 50% | 75% | max |
|---|---|---|---|---|
| Lateral | 532 kΩ | 830 kΩ | 1386 kΩ | 17,573 kΩ |
| Medial | 403 kΩ | 601 kΩ | 1001 kΩ | 20,479 kΩ |

## Same-day pairs, which is what the join needs

| array | impedance dates | session dates | **same day** |
|---|---|---|---|
| Lateral | 41 | 70 | **40** |
| Medial | 40 | 68 | **37** |

Nearly every impedance measurement has a recording from the same day. That
matters: a nearest-date join across a gap assumes impedance is stable over that
gap, and the crossing counts above show it is not stable even between adjacent
weeks. **Restrict any impedance-versus-quality analysis to same-day pairs.**

## Does impedance predict quality? Partly, and not consistently

70 same-day sessions, 6,720 electrode-days, per channel so date, amplifier and
threshold are held fixed by construction.
`notebooks/scratch_fisk_impedance_quality.py`.

**Within a session**, median Spearman across the 70:

| | median rho | sessions with \|rho\| > 0.3 |
|---|---|---|
| noise floor | **+0.341** | 59% |
| crossing rate | **−0.258** | 47% |
| SNR | **−0.269** | 44% |
| amplitude | +0.119 | 9% |

So a higher-impedance electrode is noisier, fires less, and has slightly worse
SNR — but the relationship is weak and it is present in only about half the
sessions.

**Pooled on each channel's median impedance**, which averages the measurement
noise down:

| | Lateral (n=96) | Medial (n=96) |
|---|---|---|
| noise | **+0.497** (2.6e−07) | +0.142 (0.17) |
| crossing rate | −0.086 (0.40) | **−0.342** (0.0006) |
| amplitude | +0.313 (0.0019) | +0.004 (0.97) |
| SNR | −0.161 (0.12) | **−0.347** (0.0005) |

**The two arrays do not agree.** Lateral carries the noise relationship and no
SNR effect; Medial carries the rate and SNR effects and no noise relationship.
The same electrode type, the same animal, the same rig, four months apart —
and impedance predicts different things on each.

Grouping on median impedance rather than one reading:

| group | n | noise | **rate** | amp | SNR |
|---|---|---|---|---|---|
| ≥ 1 MΩ | 61 | 9.53 | **7.02** | 44.1 | 4.45 |
| < 1 MΩ | 131 | 8.82 | **13.73** | 40.9 | 4.68 |

**The largest and clearest effect is on yield, not on noise**: high-impedance
electrodes cross threshold at *half* the rate. Noise is 8% higher, amplitude 8%
higher, SNR 5% lower.

### What to conclude, and what not to

**Do:** treat impedance as a weak, array-specific predictor of yield. A
per-channel median above 1 MΩ roughly halves the expected crossing rate, which
is worth knowing when interpreting a quiet electrode.

**Do not:** use it to classify electrodes as dead. 61 electrodes sit above
1 MΩ on median and record at SNR 4.45 against 4.68 for the rest — 95% of the
good group. On this array the 1 MΩ convention would condemn a third of the
electrodes that are working.

**And do not read this as "impedance sets the scale like the amplifier does."**
An earlier pass over four Lateral sessions showed noise +0.594 and SNR −0.074
and looked exactly like the gain relationship in [[equipment_comparison]]. The
full 70-session, two-array result does not support that: SNR moves on Medial
(−0.347, p = 0.0005) and the dominant effect is on rate. The four-session
reading was one array and too few sessions.

## Impedance against unit yield — the stronger version

`<SN>/Sorted/Exported/` holds 73 Plexon `-01` NEVs per array, so Fisk has a
sorting-based layer without re-sorting anything: 145 sessions, 12,747
electrode-rows. `notebooks/scratch_fisk_sorted.py`.

**Unit yield is the metric impedance predicts best.** Per session, across 77
same-day sessions:

| | median rho | IQR |
|---|---|---|
| **units per electrode** | **−0.277** | −0.327 to −0.175 |
| gated units | −0.146 | −0.267 to −0.051 |
| SNR | −0.117 | −0.205 to +0.026 |
| amplitude | +0.127 | −0.032 to +0.198 |

Pooled on each channel's median impedance:

| | Lateral (n=96) | Medial (n=96) |
|---|---|---|
| units | −0.197 (0.055) | **−0.440** (7.2e−06) |
| gated units | +0.110 (0.29) | **−0.284** (0.005) |
| SNR | +0.178 (0.083) | −0.189 (0.065) |
| amplitude | **+0.312** (0.002) | −0.008 (0.94) |

So a high-impedance electrode yields **fewer sortable units** — the clearest
impedance relationship in this corpus, and stronger than anything in the
sorting-free layer (crossing rate managed −0.258 per session and −0.342
pooled).

**The array-specificity persists.** Medial carries it strongly (−0.440),
Lateral marginally (−0.197, p = 0.055). Whatever links impedance to yield is
not a fixed property of the electrode type.

## Fisk's own longitudinal decline, from the sorted layer

| | Lateral (n=73) | Medial (n=72) |
|---|---|---|
| units | −0.258 (0.028) | −0.358 (0.002) |
| gated units | −0.334 (0.004) | −0.293 (0.013) |
| electrodes with units | −0.233 (0.048) | **−0.401** (0.0005) |
| amplitude | −0.209 (0.078) | −0.097 (0.42) |
| **SNR** | −0.137 (0.25) | **+0.235 (0.047)** |

**Yield falls on both arrays over two years while SNR does not** — Medial's SNR
even rises slightly. That is the pattern [[robustness]] reports across three
animals and eight arrays, and it is reproduced here on a fourth.

It also sharpens the disagreement in [[continuous_longitudinal]], where Rocky's
*continuous* SNR fell at rho −0.739. Fisk's *sorted* SNR does not fall. The
split may be layer (sorted versus continuous) rather than subject, which is a
testable claim: run the continuous layer's SNR on Fisk and see which way it
goes. Both are available.

## What is not done yet

- Fisk's continuous SNR trend, which would settle the paragraph above.
- The `.ns3` LFP stream, present for all 140 sessions and untouched.

## Related

[[impedance_parsing]] for Rocky's EIS format and why it does not transfer,
[[measurement_floor]] for the operator floor the DS/Sidd pairs extend,
[[equipment_comparison]] for the acquisition contrasts already measured.

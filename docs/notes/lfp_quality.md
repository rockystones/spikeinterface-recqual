# The LFP layer, and why Fisk has no LFP

CLAUDE.md puts LFP in scope and says it must be handled alongside spikes rather
than as an afterthought. Building it turned up a corpus fact that contradicts
the project's own stated file convention.

`notebooks/scratch_lfp_quality.py` → `data/derived/lfp/`.

## `.ns3` is not LFP on this corpus

CLAUDE.md's data conventions say:

> `.ns3` = LFP, typically 2 kHz. Use this directly for LFP; do not decimate ns5.

**For Fisk that is wrong.** The nsX extended header records the filter the NSP
applied, in millihertz:

| field | value | meaning |
|---|---|---|
| `hi_freq_corner` | 300000 | **300 Hz high-pass** |
| `lo_freq_corner` | 1000000 | 1000 Hz low-pass |

So Fisk's `.ns3` is a **300–1000 Hz band-pass stream sampled at 2 kHz** — a
second spike-band copy, not LFP. The spectrum agrees: across six sessions on
both arrays, **94% of the power sits above 250 Hz and 0.2% below 80 Hz**.

The first run of this layer computed delta/theta/alpha/beta fractions of 0.000
from it. Those numbers were not an error in the code — they are what you get
when you integrate an LFP band over a signal that has none. **A metric computed
from the wrong stream looks exactly like a metric computed from the right one.**

`nsx_filter()` now reads the corners and refuses any stream cornered above
30 Hz, so the failure is loud instead of silent.

## Where the LFP actually is

| corpus | stream | rate | genuine LFP? |
|---|---|---|---|
| Fisk `.ns3` | 300–1000 Hz band-pass | 2 kHz | **no** |
| Fisk `.ns6` | broadband | 30 kHz | yes, but needs decimating |
| TDT `pNe*` | low-pass | 763 Hz (Luigi 2013: 1526) | **yes** |
| Rocky `.ns5` | broadband | 30 kHz | yes, but needs decimating |

The only ready-made LFP in the whole corpus is the TDT `pNe` store, present for
all 370 blocks. It is **int16 ADC counts with no recorded scale**
([[tdt_corpus]]), so amplitudes from it are in counts; only ratios — line
fraction, band fractions, cross-channel correlation — are comparable with a
Blackrock-derived LFP.

CLAUDE.md's instruction not to decimate `.ns5` was written on the assumption
that `.ns3` carries LFP. Where it does not, decimating the broadband is the
only route, and that should be a deliberate exception rather than a silent
violation.

## What the layer measures, once pointed at real LFP

Three quantities chosen because the spike layer cannot see them:

- **60 Hz line power as a fraction of total.** Mains contamination is an
  acquisition fault, and a 300 Hz high-pass removes it completely — so a
  grounding problem is invisible to every other metric in this project.
- **Band power** (delta → gamma), normalised, so a spectral shift separates
  from an amplitude change.
- **Median cross-channel correlation.** A shorted, bridged or common-referenced
  array approaches 1; volume conduction alone leaves it moderate. This is the
  closest thing in the corpus to a direct hardware-fault test and it has no
  spike-layer equivalent.

## Status

Not yet run against a genuine LFP stream. The guard is in place and the
worklist builder currently covers Fisk's `.ns3` only, which it now correctly
rejects on all 140 sessions. Pointing it at the TDT `pNe` stores is the next
step and needs the TDT reader rather than the Blackrock one.

## Related

[[tdt_corpus]] for the `pNe` stores and their units, [[fisk_impedance]] for the
rest of the Fisk drop, [[threshold_crossing]] for the spike-band layer this
complements.

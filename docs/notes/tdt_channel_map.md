# Can the TDT channel map be inferred from same-day Blackrock?

**No.** The method is sound and demonstrably works when two recordings are
minutes apart, but the signature it relies on decays within days, and even its
best case is too inaccurate to use. The TDT previews stay in channel-index
order and no inferred map is written.

`notebooks/scratch_tdt_map_infer.py` → `data/derived/tdt_map/`.

## The idea

A TDT tank does not record how headstage channel 1–96 wires onto an array
electrode. Rocky was recorded on **both** systems on 22 days in 2018–2019, and
an electrode's impedance and the neurons near it should not change between two
sessions on one day. So: give every channel a signature that survives a change
of amplifier, and take the map to be the assignment of TDT channels to
Blackrock electrodes that minimises total signature distance — Hungarian, so
exact given the cost.

Signature: z-scored log noise floor, crossing rate, and amplitude at p50 and
p90, plus the mean waveform shape resampled onto a common time base measured
**from the trough** and unit-normalised, so neither the different sampling
rates (24414 vs 30000 Hz) nor the gain difference matters.

Both sides go through the same code. The Blackrock side uses its `.nev`, not
the `.ns5`, so a continuous-derived noise floor is never compared against a
snippet-derived one — that would inject the 1.1–1.3× estimator bias from
[[snippet_noise_floor]] straight into the cost matrix.

## The control chain, which is the point

Hungarian returns *an* assignment whatever the data, so the result means
nothing without knowing what the method scores when the answer is known.

**Positive control.** Rocky has 121 same-day analog/digital NEV pairs recorded
through the same NSP onto the same array, minutes apart. The true map is the
identity.

| features | agreement with truth |
|---|---|
| four scalars | 0.396 |
| **+ waveform shape** | **0.448** |
| shape alone | 0.448 |
| chance (96-way) | 0.010 |

So the features do identify electrodes — 43× chance — and shape carries nearly
all of it on its own.

**Stability control.** Same array, same headstage type, different days. Truth
is still the identity; only elapsed time changes.

| separation | agreement |
|---|---|
| same day, minutes apart | **0.448** |
| ≤ 14 days | 0.146 (Anterior) / 0.167 (Posterior) |
| > 30 days | 0.042 / 0.062 |
| chance | 0.010 |

**The signature is largely transient**, carried by which neurons happened to be
firing rather than by a fixed property of the electrode. This is expected, and
**nothing in the method asks the signature to transfer across days.** Every map
is inferred *within* one day, from two files minutes apart. Only the resulting
maps are compared across days, and they should agree because the true wiring
is fixed even when the activity is not.

**Calibration control — what a working method scores on the cross-day test.**
This is the one that makes 0.021 interpretable. Take the analog/digital pairs,
infer a map within each day exactly as the TDT inference does, then measure
agreement between those maps across days:

| | Anterior | Posterior |
|---|---|---|
| within-day recovery vs truth | 0.417 | 0.448 |
| **cross-day agreement of the maps** | **0.193** | **0.224** |
| chance | 0.010 | 0.010 |

**The ceiling is ~0.2, not 1.0** — two maps that are each ~45% correct agree
with each other about 20% of the time, which is what these numbers are. So the
criterion is fair, and the scale it should be read on is:

| | agreement |
|---|---|
| ceiling, method demonstrably working | **0.19–0.22** |
| TDT ↔ Blackrock, all four pairings | **0.021** |
| chance | 0.010 |

TDT sits at a tenth of the ceiling and twice chance.

## The result

Across TDT and Blackrock, over 22 days and both array pairings:

| pairing | days | median cross-day agreement | max |
|---|---|---|---|
| A ↔ Anterior | 21 | 0.021 | 0.085 |
| A ↔ Posterior | 21 | 0.021 | 0.095 |
| B ↔ Anterior | 19 | 0.021 | 0.087 |
| B ↔ Posterior | 19 | 0.021 | 0.085 |

Two times chance against a demonstrated ceiling of 0.19–0.22, on every
pairing. The stability control explains why: two sessions on the same calendar
day but on different rigs are, as far as this signature is concerned, further
apart than two Blackrock files recorded back-to-back — and the signature does
not survive that gap. Whether that is because the TDT and Blackrock sessions
are hours rather than minutes apart, because the two detectors select
different events, or because the TDT blocks are not recording the array the
Blackrock files are, this data cannot say.

**The `_A`/`_B` letters are not resolved either.** Both prefer Anterior on 16
of ~20 days, which is not what two different arrays would do; it says the cost
is dominated by something common to the Anterior files rather than by array
identity.

## Why this would not be usable even if it had replicated

The ceiling is the positive control: **0.448**. That is the score under ideal
conditions — same array, same NSP, minutes apart, truth known. It means more
than half the channels are assigned to the wrong electrode. A map at that
accuracy is worse than no map, because every downstream figure would look
plausible and be wrong in a way nothing else in the pipeline could catch. This
is exactly the silent, ruinous channel-order mismatch CLAUDE.md warns about.

## What would actually settle it

- **Simultaneous recording on both systems.** Spike-train matching on
  coincident events is a far stronger constraint than any summary statistic,
  and it is the only method here that would give a per-channel answer with
  usable confidence. No such session exists in this corpus.
- **Per-channel impedance measured on both rigs.** Impedance is a genuine
  fixed property of an electrode, and Rocky already has chronic potentiostat
  EIS ([[impedance_parsing]]). If a TDT-side impedance reading exists anywhere,
  that pairing is worth trying.
- **The headstage wiring documentation.** Cheapest by far if it can be found.

Until one of those, TDT results are reported by channel index and by array
number, and no figure claims a physical position.

## Related

[[tdt_corpus]] for what the tanks do and do not record, [[utah_channel_mapping]]
for how the Blackrock side maps bank/pin to a grid position,
[[snippet_noise_floor]] for why both sides are measured the same way.

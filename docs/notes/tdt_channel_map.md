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

---

# Testing named candidates from the TDT datasheet

The section above ends with "the headstage wiring documentation, cheapest by
far if it can be found." It was found. It does not settle the question, and
the way it fails identifies what is actually wrong.

`notebooks/scratch_tdt_map_candidates.py` → `data/derived/tdt_map/cand_phase*.parquet`.

## What the datasheet gives, and what it does not

TDT's **`ZCA-CK96A`** adapter — *"ZIF-Clip Headstage to CyberKinetics
CerePort"* — connects a 96-channel chronic CerePort to a ZC96/ZD96/ZCD96
headstage through three 36-pin micro socket headers. Its Fast Facts sheet
publishes which headstage channel sits at each socket. Transcribed and verified
as an exact bijection over 1–96, 32 channels per header:

| header | headstage channels carried |
|---|---|
| H1 (carries R1) | 49–72, plus even 74–88 |
| H2 | 1–9, odd 11–23, odd 73–87, 89–96 |
| H3 (carries R2) | even 10–24, plus 25–48 |

**That is emphatically not bank-preserving**, which is consistent with the map
being non-trivial. But it is not a map either: the socket-to-CerePort-pin
correspondence is not published, so the datasheet constrains rather than
determines. Assuming each header mates with one CerePort bank and that socket
order within a header follows one of four natural raster conventions gives
**24 named candidates** — down from 96!, and a short list is a far weaker
demand on the data than an inference.

**Three reasons not to trust the sheet, all live.** It is revision
**2020-05-12**, eleven years after the ZIF-Clip patent (US 7,540,752, granted
June 2009) and long after this corpus was recorded. The part number ends in a
revision letter. And TDT's own text hedges — "**most** TDT adapters and
headstages have one-to-one connections", with an explicit note that the ZD96
*digital* headstage has a different pinout than the ZC96 analog one. The point
of the test below is that none of that has to be resolved: the sheet supplies
candidates, and the data judges them.

## A statistic with enough power, which the old one lacked

The failed inference used Hungarian assignment agreement. That demands the
signature identify each electrode **uniquely**. Correlation only demands it
rank them **consistently**, which is a far lower bar:

| | Hungarian agreement | Spearman r |
|---|---|---|
| Blackrock ↔ Blackrock, same day, truth known | 0.448 | **0.938** |

Same data, same features. Every score below is Spearman r across the 96
channels, against a null of 500 random relabellings.

## Phase A — the statistic works

Same array, same NSP, minutes apart, **and a change of headstage** (analog vs
digital), truth = identity. 14 pairs:

| feature | median r | median z | pairs at p<0.01 |
|---|---|---|---|
| log_rate | **0.938** | +9.1 | 14/14 |
| log_amp90 | 0.884 | +8.8 | 14/14 |
| log_amp50 | 0.881 | +8.3 | 14/14 |
| log_noise | 0.799 | +7.9 | 14/14 |

Nine sigma, and it survives an amplifier change. The method is not the
limitation.

## Phase B — only one feature survives a change of day on TDT

Same tank letter, different days, no hardware change, truth = identity:

| letter | log_rate | log_noise | log_amp50 | log_amp90 |
|---|---|---|---|---|
| A | **0.427** (10/10) | 0.152 | 0.043 | 0.022 |
| B | **0.493** (10/10) | 0.080 | 0.021 | 0.076 |

**Crossing rate is a genuine per-electrode property on TDT. Noise and
amplitude are not.** That is the first hard constraint: the cross-rig test has
one usable feature, not four.

## Phase C — no candidate map works

24 candidates, 16 TDT/Blackrock same-day pairings, on `log_rate`:

| comparison | truth | median r | z | pairings p<0.01 |
|---|---|---|---|---|
| Phase A, Blackrock ↔ Blackrock | identity | 0.938 | +9.1 | 14/14 |
| Phase B, TDT ↔ TDT across days | identity | 0.459 | +4.5 | 20/20 |
| **Phase C, best of 24 candidates** | unknown | **0.125** | **+1.2** | **1/16** |

The best candidate reaches **27% of TDT's own day-to-day reproducibility** and
is not significant. Worse, no candidate is coherent across features — the
`log_rate` winner ranks 13th, 13th and 11th on the other three, and the best
"worst rank" over all four features is 7th of 24. A correct map ranks first on
all four.

## Phase D — why, and it is not the map

Rocky's TDT tanks come in `_A` and `_B` blocks, nominally the two arrays.
Correlating an `_A` block against the **same day's** `_B` block, under the
identity channel order:

| feature | r | z | days p<0.01 |
|---|---|---|---|
| log_noise | **0.818** | +7.9 | 8/8 |
| log_amp50 | **0.802** | +7.7 | 8/8 |
| log_amp90 | 0.779 | +7.7 | 8/8 |
| log_rate | 0.372 | +3.7 | 8/8 |

Two different Utah arrays in different cortex share no electrodes, so under a
correct reading this should be ~0. It is 0.82.

**Put Phase D beside Phase B and the pattern is diagnostic:**

| feature | across days, same letter (B) | across letters, same day (D) | what it is bound to |
|---|---|---|---|
| log_noise | 0.08 – 0.15 | **0.818** | **the rig** |
| log_amp50 | 0.02 – 0.04 | **0.802** | **the rig** |
| log_rate | **0.43 – 0.49** | 0.372 | the electrode |

A property of the *electrode* reproduces when the electrode is held fixed and
the day changes. A property of the *amplifier channel* reproduces when the rig
state is held fixed and the electrode changes. **TDT's noise and amplitude do
the second.** They are carrying the recording system's per-channel state on
that day, not anything about the tissue — which is why the candidate rankings
built on them were incoherent, and why the original Hungarian inference, whose
cost was dominated by exactly these features, could never have worked.

Crossing rate is the exception and behaves correctly: more stable across days
than across letters.

## What this establishes

1. **The 24 datasheet-derived candidates are excluded**, using a statistic with
   demonstrated 9σ power on a known-true map.
2. **Three of the four features are unusable on TDT** — they measure the
   amplifier, not the electrode. Any future attempt must drop them.
3. **`log_rate` is the only usable feature**, and on it the best candidate sits
   at 0.125 against a 0.459 same-rig reference.
4. The remaining possibilities are that the true map lies outside the candidate
   family, that the TDT and Blackrock files are not recording the same array on
   the same day, or both. **This test cannot separate them**, and no result
   here should be read as if it could.

## What would still settle it

Unchanged from above, minus the one now tried:

- **A surviving Synapse `Mapper` configuration or `.pmap` file.** TDT's own
  documentation names Mapper as the tool that composes electrode → adapter →
  headstage. If one was saved with the recordings it contains the answer
  outright. Worth grepping the tanks for before anything else.
- **The adapter's own part number, read off the PCB**, and the headstage model
  (ZC96 analog vs ZD96 digital — TDT states these differ). Either narrows or
  replaces the candidate family.
- **Per-channel impedance on both rigs.** Impedance is genuinely
  electrode-bound, unlike three of the four features tested here.
- **Simultaneous recording on both systems.** Still the only method that would
  give per-channel confidence, and still absent from this corpus.

Until then the position is unchanged and now better founded: TDT results are
reported by channel index and by array number, and no figure claims a physical
position.

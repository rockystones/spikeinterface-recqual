# Three questions: sorters, operators, and the longitudinal trend

What to run, in what order, and what each comparison can and cannot answer.
Written 2026-08-15, after the Monkey Data inventory ([`monkey_corpus.md`](notes/monkey_corpus.md)).
Extends the session list in [`cohort_plan.md`](cohort_plan.md) §5.

The three questions are not independent. Two of them are the **denominator** for
the third:

> A longitudinal change is only interpretable if it exceeds the amount the
> measurement moves when you change the sorter or the operator.

The sensitivity sweep already made this concrete on one side: Rocky's anterior
yield trend ranges from `rho = −0.72` to `+0.05` depending on gate and cohort
choices, so it is **not** a robust decline. The posterior collapse survived all
18 variants and is real. That was method sensitivity alone. Operator sensitivity
has never been measured, and it can be — exactly.

---

## 0. The fact that decides the whole design

**Sorting never re-detects on NEV data.** Every variant of a recording carries
byte-identical spike timestamps — verified on all 697 recordings with more than
one variant. OFS, both operators and every clusterer change the unit-class label
only.

This splits every comparison into two regimes with completely different
properties:

| | **Regime A — fixed events** | **Regime B — independent detection** |
|---|---|---|
| source | `.nev` snippets | `.ns5` broadband |
| what varies | clustering and curation | detection *and* clustering |
| comparison | **exact** — a confusion between two labellings of one spike list | requires spike matching within a tolerance |
| available | everything: 2,423 NEV | Nigel 47, Rocky I2 20 staged (more on `L:`) |
| blind to | **the NSP's online threshold**, which is common-mode | nothing |

The last row is the important one. **No Regime A comparison can see the
detection threshold**, because every file inherits the same one from
acquisition. That threshold changed between Rocky's recording eras and is the
single largest lever on his anterior trend. Only Regime B can remove it.

So "how do sorters differ" is really two questions, and they need different
sessions and different data.

---

## S09 — The measurement floor *(recommended first)*

**One axis, three sources of spread, no re-sorting required.**

| source of variation | data | n |
|---|---|---|
| **operator identity** — DS vs Sidd on the same recording | Fisk 19, Rocky I2 11 | **30** |
| **human vs automatic** — each operator vs `-01` | same 30, all three-way | 30 |
| **operator vs themselves** — Sidd's redo | Fisk `-MA` vs `-MA-RE` | 7 |
| **algorithm choice** — OFS clustering variants | Nigel sweep, 8 × 78 fully crossed | **624** |
| **clusterer choice** — isosplit / GMM / HDBSCAN / k-means / OFS | Rocky 60-session subset | done |

The OFS sweep is the asset that makes this session worth running now:
`Scan{EM,Kmean,Valley}` and `TDIST-EM-3D`, each × `{J3, PSF}`, over the **same
78 sessions** — a fully crossed algorithm × session design that is already
computed and has never been read.

**Metrics, per comparison:** unit count, noise-marked fraction, spike-level
label agreement, and — on a stratified subset, because these need waveform reads
— per-unit SNR and amplitude distributions.

**Deliverable:** for each longitudinal metric, an error bar attributable to who
sorted it and with what. Everything downstream then gets compared against it.

**Two limits to state up front.** The operator set is Fisk and Rocky implant 2,
both 2023–2025; Rocky implant 1 — the six-year series every current conclusion
rests on — has only **2 curated dates**. So the floor is measured on different
data than it will be applied to. And because detection is common-mode, the floor
is *conditional on* the NSP threshold of those sessions.

---

## S10 — Longitudinal metrics, cross-subject

Extend the existing pipeline to Nigel (160 sessions, 2023-01 → 2025-09) and
Rocky implant 2 (20, 2025); Fisk (143, 2023-06 → 2025-05) when its originals
land. Rocky implant 1 is done.

Align on **implant age**, not calendar date — that is the axis on which four
array-implants become comparable. Every trend now carries the S09 error bar, so
the reportable result is which metrics move *more than the measurement floor*,
and whether they move the same way in different animals.

Nigel's terminal session is a natural endpoint: **2025-09-25, Anterior only, and
the Posterior array recorded no units that day.** That is a terminal fact for a
survival analysis, not an acquisition failure.

---

## S11 — Regime B: re-detection on continuous data

The only session that answers "how do *sorters* differ" in the full sense, and
the only one that can remove the threshold confound.

67 sessions staged (Nigel 47, Rocky I2 20); Rocky implant 1 has ~431 more `.ns5`
on `L:`. Per CLAUDE.md's sorter policy: MountainSort5 (scheme 2), Tridesclous2,
Kilosort4 with `do_correction=False`, optionally SpykingCircus2. Compare against
the NEV threshold events with a stated match tolerance.

Two things it settles that nothing else can:

1. **How much of the longitudinal trend is NSP threshold drift.** Re-detect at a
   fixed `k × MAD` and the era effect disappears by construction.
2. **Whether the snippet noise floor bias generalises.** It is currently measured
   at 1.305× high on one session, one animal ([`snippet_noise_floor.md`](notes/snippet_noise_floor.md)).

---

## S12 — Analog versus digital headstage

121 date-slots on Rocky implant 1 carry both headstages recording the same
session, analog known to be noisier. No ground truth needed: agreement between
the pair is an accuracy proxy, and the noise asymmetry makes it a *graded*
benchmark — it measures not just whether a method works but how it degrades.

It is also the cleanest test of whether a sorting-free metric tracks physiology
or headstage noise. Any metric that differs between the pair is measuring the
amplifier.

---

## Ordering, and why

```
S09  measurement floor      cheap, exact, no re-sorting     <- start here
 |
 +--> S10  longitudinal      needs S09's error bar to be interpretable
 |
 +--> S12  analog/digital    independent; validates the metrics themselves
 |
S11  ns5 re-detection        largest job; the only view of the threshold
```

S09 first because it is the cheapest of the four, requires no sorter run, gives
an **exact** answer rather than an estimated one, and because without it S10
produces trends nobody can size. S11 is the deepest but the most expensive, and
its result is easier to interpret once the floor is known.

## Open, and not blocking

- **Fisk originals** — 53 sessions have curated output with no original staged.
- **Impedance sweep ordering** — still unresolved, now blocking per-electrode
  conclusions for five subjects ([`impedance_parsing.md`](notes/impedance_parsing.md)).
- **`-MADS`** — Sidd then DS, sequential. Excluded from the independent set; it
  is *usable* as a study of what a second operator changes about the first's
  work, on 2 recordings.

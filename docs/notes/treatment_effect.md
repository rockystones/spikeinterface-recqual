# Coated against uncoated — and why the contrast may not be the coating

The project exists to compare L1-coated Utah arrays against uncoated controls
implanted in the same animal. `cohort_definition.md` established which array is
which; this runs the comparison.

`notebooks/scratch_treatment_longitudinal.py` → `figures/treatment/W1–W5`.

**The headline: the treatment effect reverses between animals, while a
position effect does not.** On the evidence here, what looks like a coating
effect is at least as well explained by which pedestal the array sits under.

## The design, and what makes the test possible

Each generation-1 animal carries one coated and one uncoated array from the
same surgery, recorded in the same sessions through the same amplifier. Every
number below is **paired inside the session** — the aggregation rule from
CLAUDE.md — so the day, the animal and the rig are held fixed.

The three animals do not arrange treatment the same way, and that is the whole
point:

| animal | anterior pedestal | posterior pedestal |
|---|---|---|
| Oops | uncoated, lateral | **coated**, medial |
| Picasso | **coated**, medial | uncoated, lateral |
| Rocky I1 | **coated**, lateral | uncoated, medial |

Oops and Picasso put the coating under opposite pedestals, which separates
treatment from position. Rocky puts the coating on the opposite cortex from the
other two, which separates treatment from cortical site. Together the three
deconfound all three axes.

## The result

Paired within session, median ratio:

### units per session

| contrast | Oops | Picasso | Rocky I1 | consistent? |
|---|---|---|---|---|
| **anterior / posterior** | **1.227** | **1.614** | **1.143** | **yes — all > 1** |
| coated / uncoated | 0.815 | 1.614 | 1.143 | **no — reverses** |
| medial / lateral | 0.815 | 1.614 | 0.794 | **no — reverses** |

### electrode yield (% of electrodes carrying a unit)

| contrast | Oops | Picasso | Rocky I1 | consistent? |
|---|---|---|---|---|
| **anterior / posterior** | **1.080** | **1.158** | **1.167** | **yes — all > 1** |
| coated / uncoated | 0.926 | 1.158 | 1.167 | **no** |
| medial / lateral | 0.926 | 1.158 | 0.824 | **no** |

Taken one animal at a time, the coating result is significant and confident —
and points the wrong way half the time:

| animal | metric | n | coated/uncoated | p |
|---|---|---|---|---|
| Oops | units | 55 | **0.815** | 1.9e-05 |
| Oops | yield | 55 | **0.926** | 0.0016 |
| Picasso | units | 25 | **1.614** | 0.035 |
| Picasso | yield | 25 | **1.158** | 0.016 |
| Rocky I1 | units/electrode | 153 | **1.160** | < 1e-4 |

**Oops says the coating costs 18% of units at p = 2e-05. Picasso says it gains
61% at p = 0.03.** Both are real measurements of the same intervention. Either
one alone would read as a clear effect.

The only axis on which all three agree is the pedestal.

## Reading this honestly

**What it does not show.** It does not show the coating has no effect. Three
animals is a small design, and a position effect and a treatment effect could
both be present with the position term larger.

**What it does show.** Any claim of an L1 yield benefit that rests on one
animal, or on animals sharing a coating-to-pedestal arrangement, is not
separable from position. The published claim this project set out to re-examine
— *"L1 coating showed significantly improved single unit recording yield of a
Blackrock array in primate motor cortex over the course of 10 months"* (U01
aims) — is of that form.

**Why a pedestal effect is plausible rather than a fluke.** The pedestal is
where the percutaneous connector sits, where cable strain lands, and where the
Luigi notes record a physical failure mode directly: *"monkey is able to bang
the rear cereport chip and clip against the rails on the chair, further
screwing up the signal"* (2013-01-14). Posterior pedestals in this cohort also
failed earlier — Oops's posterior came out 2016-12 against the anterior's
2017-03, Picasso's posterior 2016-10 while the anterior survived, and Luigi's
posterior was disconnected in 2013 while the anterior ran to 2016.

**Three of four generation-1 animals lost the posterior array first.** That is
the same ordering as the yield contrast, from an entirely separate observable.

## Two measurement caveats that matter

**The sources differ.** Oops and Picasso come from the **legacy OpenSorter
sorts** in `monkey_units_compiled.mat`; Rocky comes from the **modern
pipeline**. The modern cohort table has almost no unit counts for Oops and
Picasso — 5 and 1 non-null rows out of 61 and 84 — because their legacy sorts
never carried yield forward. So the three animals are not measured by one
chain, and the *magnitudes* are not directly comparable across sources. The
*directions*, which is what the argument rests on, are.

**The legacy sorter is not neutral.** Its configuration put two units on 913 of
929 channels ([[cohort_extension]]), which is why the TDT animals' gate-pass
rates are low. That affects the level, not the within-session pairing, since
both arrays of a pair were sorted the same way on the same day.

## What would settle it

- **An animal with both arrays under the same pedestal**, or a coating swapped
  between pedestals within an animal. Neither exists in this cohort.
- **Rocky implant 2**, which is TNP vs TNP-L1 with the coating on the opposite
  pedestal from implant 1 — a fourth arrangement, though only 10 sessions per
  array so far.
- **Nigel and Fisk**, whose striped design puts both treatments on one array
  under one pedestal, which removes the position term entirely. That is the
  design that answers this question, and it is exactly why the stripe
  assignment being unverified ([[surface_conditions]]) is the most valuable
  open item in the project.

## Related

[[cohort_definition]] for which array is which and how it was established,
[[surface_conditions]] for the generation-2 within-array test,
[[cohort_longitudinal]] for the per-array trends this reframes,
[[legacy_archive]] for `monkey_units_compiled.mat`.

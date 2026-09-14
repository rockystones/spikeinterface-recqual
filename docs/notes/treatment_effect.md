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
- **Rocky implant 2** — now run (2026-09-12). TNP-only sits anterior and
  TNP-L1 posterior, so the extra L1 term is on the *opposite* pedestal from
  every prior L1 animal. Paired within session over the 10 I2 dates:
  anterior/posterior units **1.152** (p = 0.16 at this n). Alone that is not
  significant; its weight is the consistency — a **fourth distinct
  arrangement landing on the same side of the pedestal axis** (Oops 1.227,
  Picasso 1.614, Rocky I1 1.143, Rocky I2 1.152), while the more-coated array
  loses again (more-L1/less-L1 = 0.87). Caveat: TNP vs TNP-L1 is a different
  chemical contrast from L1 vs bare, so this is a fourth arm, not a
  replication.
- **Nigel and Fisk**, whose striped design puts both treatments on one array
  under one pedestal, which removes the position term entirely. That is the
  design that answers this question, and it has been run
  ([[surface_conditions]]): **0 of 168 array × method × metric combinations
  separate the treated stripes from the untreated ones** under a stripe
  permutation, across thirteen sorting methods including two human curators.
  Nigel's assignment is verified from the schematic's own electrode maps, which
  reproduce 1473 and 1496 including their per-array unconnected positions;
  Fisk's is still inferred from the surgical design rather than from a
  schematic of its own, and confirming it is what remains open.

  So the striped design does not rescue a coating effect — it bounds it. That
  design can rule out a yield effect of roughly 30% or more on three of the four
  arrays and cannot rule out a modest one.

## Related

[[cohort_definition]] for which array is which and how it was established,
[[surface_conditions]] for the generation-2 within-array test,
[[cohort_longitudinal]] for the per-array trends this reframes,
[[legacy_archive]] for `monkey_units_compiled.mat`.

## W6 (2026-09-14): the within-animal contrast is metric-robust

The orthogonal robustness check (Q-010 / R-017): Rocky I1's
coated/uncoated ratio, paired within session, under every measurement
chain the project has - human Plexon sort, gated resort, exact
mean-max-P2P, sorting-free crossings, each of the four modern sorters on
the continuous ns5, and consensus units agreed by 2 and by 3 (the W-019
same-day pairs). All 13 ratios sit above 1 (1.07-1.96), all p < 1e-3.
`figures/treatment/W6_coating_by_metric.png`,
`cohort/coating_by_metric.parquet`. This removes "it's an artifact of
the measurement chain" as an explanation for the within-animal
contrast; it says nothing new about treatment-vs-pedestal, which is
W5's result above and unchanged.

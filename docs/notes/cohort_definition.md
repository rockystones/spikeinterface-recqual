# The cohort, defined by surface treatment

The project's reason for existing is a comparison between **coated and uncoated
Utah arrays implanted in the same animal**. That design was scattered across
PowerPoints, folder names, a spreadsheet and a day-by-day recording log, and
nothing in the pipeline encoded it. This note establishes it.

**Method.** The owner's rule: *individual files contain mistakes; the
consistent definitions are the correct ones.* So every fact below carries a
count of **independent sources** that agree, and each source is named. Nothing
rests on one document being authoritative.

Sources searched: `D:\Claude Code\Monkey Data\Legacy`, plus the recording files
themselves — which turn out to be the strongest evidence of all, because an
array's disappearance from the data dates its explant.

## The convention, which two documents get backwards

From the owner, and it resolves several apparent contradictions:

- **anterior / posterior** = where the **pedestal** sits on the skull.
- **lateral / medial** = where the **array** sits on cortex.

These are different axes. Most documents give only one, and a few give one
while appearing to mean the other.

## The established cohort

| animal | implanted | pedestal | cortex | treatment | serial | array gone | src |
|---|---|---|---|---|---|---|---|
| Chase | ? | ? | ? | uncoated | ? | ? | 1 |
| Luigi | **2012-12-18** | Anterior | lateral | **L1 coated** | `1025-001082` | ? | 3 |
| Luigi | 2012-12-18 | Posterior | medial | uncoated | `1025-001085` | disconnected **2013-03-20** | 2 |
| Oops | **2014-12-16** | Anterior | ? | uncoated | `1025-001391` | **2017-03** | 4 |
| Oops | 2014-12-16 | Posterior | ? | **L1 coated** | `1025-001393` | **2016-12** | 4 |
| Picasso | **2015-11-03** | Anterior | medial | **L1 coated** | `1025-001499` | survivor | 4 |
| Picasso | 2015-11-03 | Posterior | lateral | uncoated | `1025-001503` | **2016-10-11** | 3 |
| Rocky | **2017-08-30** | Anterior | lateral | **L1 coated** | `1025-001501` | — | 3 |
| Rocky | 2017-08-30 | Posterior | medial | uncoated | `1025-001497` | — | 3 |

Every serial matches `configs/subjects/*.json` exactly. No registry correction
was needed — the registry was right, it just carried no treatment field.

**The design is consistent across all four early animals**: one L1-coated array
and one uncoated control per animal, so the comparison is always *within*
subject. Chase is the exception with a single uncoated array, which makes it a
control animal rather than a paired one.

### Where each fact comes from

**Coating**, four independent encodings that agree:

| source | what it says |
|---|---|
| `implanted_monkeys_status.pptx` | the master table: Monkey / Implanted / Arrays / Location / Treatment |
| folder names | `CTRL_11032015` → SN1503, `L1_11032015` → SN1499; `coat_1025-001501` vs `ctrl_1025-001497`; `pre_implant/coated` vs `pre_implant/ctrl` |
| `Monkey_Data_Compile.xlsx` | two sheets, **`L1`** and **`Ctrl`**. Picasso and Luigi appear only on `L1`; Oops only on `Ctrl`; **Rocky on both**, because it is the one animal where both arrays survived |
| `Monkey Impedance_update_20170509.pptx` | slide 3, in words: *"Oops-anterior: CTRL / Picasso-anterior: L1"* |

**Implant dates**: the status deck, plus `Recording Notes - Luigi.pdf`, whose
first entry reads *"12/20/2012 … recorded for the first time (2 days after
surgery!)"* — independently fixing Luigi's surgery at 2012-12-18. Picasso's
`11/3/2015` is also carried in the array-info folder names.

**Explant dates**, and this is where the recording files earn their place:

| animal | claim | what the data shows |
|---|---|---|
| Oops posterior | removed 12/2016 | impedance: last measured **2016-12-02**, absent after. TDT: `eNe2` present in every block to **2016-12-21**, then gone |
| Oops anterior | removed 3/2017 | impedance to **2017-02-17**; TDT `eNe1` alone to **2017-02-15** |
| Picasso posterior | removed 2016-10-11 | impedance: last **2016-09-14**, absent from **2016-10-20** on — the stated date falls exactly between |
| Luigi posterior | — | recording notes, **2013-03-20**: *"Sorted both arrays, but the posterior array was all noise, so disconnected it."* |

Four dates, four independent confirmations from data the documents never
touched. This is the strongest part of the reconstruction.

## The TDT store → array assignment, inferred not documented

A TDT tank records store names (`eNe1`, `eNe2`, `eNe3`), never which physical
array fed them. The assignment below is **inferred from which store disappears
when**, against explant dates established separately:

| animal | store composition per block | inference |
|---|---|---|
| Oops | `eNe1+eNe2` to 2016-12-21, then **`eNe1` alone** to 2017-02-15 | `eNe2` = Posterior (L1), `eNe1` = Anterior (ctrl) |
| Picasso | `eNe1+eNe2` to 2017-01-06, then **`eNe2` alone** to 2017-04-14 | `eNe1` = the array that stopped; `eNe2` = the survivor |
| Luigi | `eNe1+eNe2+eNe3` to 2013-05-17, then **`eNe1` alone** from 2015-03-05 | `eNe1` = Anterior (L1), the array the notes say survived |

Oops matches its explant dates to the week and is safe to use. **Luigi and
Picasso are inferences and should be labelled as such.**

## The one contradiction that did not resolve

Picasso's posterior pedestal came out **2016-10-11** — the status deck and the
impedance record agree, and the topography deck independently gives the
posterior impedance series as ending *"Sept 14 2016"*, the same last date.

But the recordings do not stop:

- `eNe1` continues to **2017-01-06**, three months past the explant, and looks
  **alive**: noise flat across the boundary (9.43 → 9.70 µV), all 96 electrodes
  active, crossing rate up 1.58× but p=0.21.
- The change it does show is shared by the *surviving* store — `eNe2`'s
  `amp_p90` rises 1.63× (p=0.0006) over the same split — so it is a rig or
  configuration change affecting both, not one array dying.
- It is **not** the known `eNe1==eNe2` export duplication: 0 of 14 blocks
  carrying both stores have matching values on any metric.
- Separately, the topography deck says *"Picasso Sacrificed March 2017"*, while
  Picasso-labelled TDT blocks run to **2017-04-14**.

So three readings survive: the block dates are wrong for some Picasso blocks,
the store→array assignment is not what the disappearance pattern suggests, or
recording continued on a disconnected input in a way that does not look
disconnected. **This note does not choose between them**, and no Picasso figure
should assume a per-array attribution after 2016-10-11 until it is settled.

## Gaps

Tracked in `docs/handoff_legacy_search.md` for the drive-census search.

1. **`TNP`, `TNP L1`, `EDCNHS`** — Nigel and Fisk use a *striped* design,
   alternating shank rows with different surface conditions:
   Nigel `1473` Posterior = EDCNHS vs ctrl, `1496` Anterior = TNP vs TNP L1,
   with Fisk the same pattern. **No legacy document mentioning these treatments
   was found.** Currently owner-stated only, which is why the surface-condition
   analysis calls its stripe assignment inferred.
2. **Chase** — no implant date, no serial, no `.cmp`. Oldest data in the corpus
   (2009-03 → 2010-02) and unreachable for any spatial analysis.
3. **Oops cortical locations** — the only animal whose lateral/medial
   assignment is unrecorded.
4. **Luigi's 21-month gap** — no blocks between 2013-05-17 and 2015-03-05, and
   three stores for two arrays in 2013.
5. **A later Picasso impedance drop** — the topography deck cites anterior
   impedance to *"Feb 27 2018"*; the folders here stop 2017-04-28.
6. **The Google Sheets "array log"** linked from `implanted_monkeys_status.pptx`
   is probably the authoritative record and needs the owner's credentials.

## Why this matters to the analysis

Every longitudinal result in this project has been reported per *array*, with
treatment nowhere in the pipeline. With the table above, the four early animals
become four **within-subject coated-vs-uncoated pairs** — the comparison the
cohort was built for, and one that holds tissue, surgery date and animal fixed.

Two cautions carry over from work already done. Yield differences between
arrays must be compared **within animal and within session**, never pooled
across sessions ([[giant_events]] §aggregation). And an array's apparent
collapse can be an acquisition fault rather than tissue — Fisk's Feb–Mar 2025
grounding fault cost 91% of yield and fully recovered ([[lfp_quality]]).

## Related

[[monkey_corpus]] for the file inventory, [[tdt_corpus]] for the tanks,
[[surface_conditions]] for the Nigel/Fisk stripe analysis this would ground,
[[impedance_sources]] for the impedance records used here as explant evidence.

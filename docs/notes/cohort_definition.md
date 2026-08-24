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

## Three design generations, not one

The cohort is not a single experiment. Treatments and the *unit of comparison*
both change across three generations, and conflating them is the main way to
get this wrong.

| gen | years | comparison | unit | animals |
|---|---|---|---|---|
| **1** | 2012–2017 | **L1 vs uncoated** | whole array, paired within animal | Luigi, Oops, Picasso, Rocky **I1** (+ Chase, single uncoated) |
| **2** | 2023–2025 | **striped** — alternating shank rows | *within* one array | Nigel, Fisk |
| **3** | 2025 | **TNP vs TNP-L1** | whole array, paired within animal | Rocky **I2** |

`TNP`, `TNP L1` and `EDCNHS` belong **only** to generations 2 and 3. No
generation-1 animal carries them, which is why no document in the
`L1MonkeyData` tree mentions them — that tree predates them entirely.

Generation 1 and 3 share a design (one treatment per array, two arrays per
animal) and differ only in the chemistry. Generation 2 is a different
experiment: the contrast lives inside a single array, so it controls for
pedestal, amplifier and hemisphere at the cost of having no uncoated array at
all.

## The established cohort

| animal | implanted | pedestal | cortex | treatment | serial | array gone | src |
|---|---|---|---|---|---|---|---|
| Chase | ? | ? | ? | uncoated | ? | ? | 2 |
| Luigi | **2012-12-18** | Anterior | lateral | **L1 coated** | `1025-001082` | ? | 3 |
| Luigi | 2012-12-18 | Posterior | medial | uncoated | `1025-001085` | disconnected **2013-03-20** | 2 |
| Oops | **2014-12-16** | Anterior | **lateral** | uncoated | `1025-001391` | **2017-03** | 6 |
| Oops | 2014-12-16 | Posterior | **medial** | **L1 coated** | `1025-001393` | **2016-12** | 6 |
| Picasso | **2015-11-03** | Anterior | medial | **L1 coated** | `1025-001499` | survivor | 4 |
| Picasso | 2015-11-03 | Posterior | lateral | uncoated | `1025-001503` | **2016-10-11** | 3 |
| Rocky | **2017-08-30** | Anterior | lateral | **L1 coated** | `1025-001501` | — | 3 |
| Rocky | 2017-08-30 | Posterior | medial | uncoated | `1025-001497` | — | 3 |
| Rocky **I2** | **2025-03-26** | Anterior | **medial** | **TNP** (all shanks) | `1025-004377` | — | 1 |
| Rocky **I2** | 2025-03-26 | Posterior | **lateral** | **TNP-L1** (all shanks) | `1025-004419` | — | 1 |
| Nigel | ? | Anterior | ? | **TNP vs TNP-L1** (striped) | `1025-001496` | — | 1 |
| Nigel | ? | Posterior | ? | **EDCNHS vs ctrl** (striped) | `1025-001473` | — | 1 |
| Fisk | ? | ? | lateral | striped, pattern as Nigel | `1025-001498` | — | 1 |
| Fisk | ? | ? | medial | striped, pattern as Nigel | `1025-001504` | — | 1 |

Every serial matches `configs/subjects/*.json` exactly. No registry correction
was needed — the registry was right, it just carried no treatment field.

**Euthanasia dates**, from Table 2 of the study write-up. These are later than
the pedestal removals and are a different event:

| animal | euthanized |
|---|---|
| Oops | 2017-04-10 |
| Picasso | **2018-03-02** |
| Luigi | 2018-05-24 |
| Rocky | 2025-06-11 |

Picasso's resolves a conflict flagged earlier: the topography deck says
*"Sacrificed March 2017"*, which is **a year early**. March 2018 is consistent
with Picasso's TDT blocks running to 2017-04-14 and with the same deck's own
claim that anterior impedance continues to *"Feb 27 2018"*. The deck is the
outlier; two other sources agree on 2018.

Luigi outlived its last recording (2016-08-30) by 21 months.

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
| `monkey_units_compiled.mat` | a `coating` field **per array**, machine-readable: Oops A=uncoated / B=coated, Picasso A=coated / B=uncoated, Luigi A=coated, Chase A=uncoated |
| Table 2 of the study write-up | the only source giving **both** axes for every array, plus euthanasia dates |

**A labelling collision to be aware of.** `monkey_units_compiled.mat` labels
Oops's arrays `A`=uncoated and `B`=coated, while the array-info folders are
named `A_1025-001393` and `B_1025-001391` — and 1393 is the *coated* posterior.
So the two A/B conventions are **opposite**. The `.mat` letters track the
pedestal (A=Anterior, 71 files against B's 58, matching the TDT block counts of
85 and 78); the folder letters do not. Neither is wrong, but they must never be
joined on the letter.

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

## Luigi's TDT tank clock is one month fast for its first 39 blocks

Luigi's 2013 blocks are named `Block-NN` with **no date in the name**, so their
dates come entirely from the tank's own clock (`date_source = clock_local` for
444 of 489 rows; the 2015–16 blocks are dated from folder names instead).
That clock is wrong.

The recording notes carry a **TDT Block #** column, which makes it checkable:

| blocks | tank vs notes |
|---|---|
| 12 – 39 | tank is **exactly +31 days** (19 blocks) |
| 40 – 54 | exact agreement (5 blocks) |

Three things confirm the offset rather than a mis-read of the notes:

1. **The raw series is not monotonic in block order.** Block-39 reads
   2013-04-13 and Block-40 reads 2013-03-14 — consecutive blocks going a month
   backwards. Subtracting 31 days from blocks below 40 makes the whole series
   monotonic.
2. **The corrected first block lands on 2012-12-20**, which is exactly the
   notes' first entry, *"recorded for the first time (2 days after surgery!)"*,
   against a surgery of 2012-12-18.
3. The changeover is clean: Block-39 corrects to 2013-03-13 and Block-40 is
   already 2013-03-14, one day apart as the notes have them.

So the clock was one month fast from the start and was corrected at
**Block-40, 2013-03-14**. **Luigi's true 2013 span is 2012-12-20 → 2013-05-17**,
not 2013-01-20 → 2013-05-17 as `tdt_inventory.parquet` currently records, and
**39 blocks are misdated by exactly 31 days**.

Nothing downstream has used Luigi's within-2013 dates for anything finer than
"the 2013 era", so no published result changes. It must be fixed before any
day-resolution Luigi analysis.

### And the compile spreadsheet never had Luigi's dates at all

`Monkey_Data_Compile.xlsx` shows Luigi running 2013-01-03 to 2015-02-03, which
looks like a continuous two-year series. It is not. In
`monkey_units_compiled.mat`, Luigi is the **only** animal whose struct carries
`dayvec` instead of `dates`:

```
dayvec = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365, ...]
```

26 values, exact monthly day-offsets, no calendar anywhere. Oops, Picasso and
Chase all carry real `dates` arrays. The spreadsheet's Luigi column was made by
anchoring day 0 at 2013-01-03, and the giveaway survives in the sheet: **13 of
25 consecutive rows share an identical max amplitude**, each real measurement
duplicated across two monthly bins, while Picasso and Rocky on the same sheet
have zero such duplicates.

**So the spreadsheet is not evidence that Luigi was recorded through 2015.**
Whether the 21-month hole between 2013-05-17 and 2015-03-05 is real or is
missing data remains open.

## Rocky reuses its array labels across two implants

**This is the most dangerous thing in the table**, because nothing in the
pipeline currently guards against it.

| label | implant | serial | cortex | treatment | sessions | span | units/electrode |
|---|---|---|---|---|---|---|---|
| Anterior | I1 | `1025-001501` | lateral | L1 | 184 | 2017-09 → 2023-10 | 0.276 |
| Anterior | **I2** | `1025-004377` | **medial** | **TNP** | 10 | 2025-04 → 2025-06 | **0.849** |
| Posterior | I1 | `1025-001497` | medial | uncoated | 190 | 2017-09 → 2023-10 | 0.250 |
| Posterior | **I2** | `1025-004419` | **lateral** | **TNP-L1** | 10 | 2025-04 → 2025-06 | **0.771** |

Same label, different array, different coating — and the anatomy **flips**:
I1's Anterior array sits on lateral cortex, I2's on medial. A longitudinal
series plotted as "Rocky Anterior, 2017 to 2025" splices two implants and
shows a 3× jump at the join that is a new array, not a recovery.

**It has already affected a published number.** Rocky's four-sorter set is 57
sessions, of which **20 are implant 2**:

| Rocky | n | span | spread | KS4 ÷ others |
|---|---|---|---|---|
| I1 | 37 | 2018-02 → 2023-10 | 2.54 | **2.162** |
| I2 | 20 | 2025-04 → 2025-06 | 2.39 | **1.798** |
| pooled — *as previously reported* | 57 | | 2.44 | 1.978 |

The two differ at **p = 4.2e-07**, so 1.978 is an average of two populations
rather than a property of the animal. Splitting them also sharpens the original
finding: Rocky I1 at 2.16 sits beside Nigel at 2.05, against Fisk at 1.33.

Anything grouping by `(subject, array)` must group by
`(subject, implant, array)` or by serial. See [[sorter_operations]].

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

1. **`TNP`, `TNP L1`, `EDCNHS` are owner-stated only.** All three belong to
   generations 2 and 3, so the `L1MonkeyData` tree correctly does not mention
   them — any documentation will be **2020 or later** and filed elsewhere.
   What is needed: a definition of each chemistry, and for Nigel and Fisk a
   schematic showing **which shank rows** carry which, since the striped design
   is a within-array contrast and the stripe assignment is currently inferred
   from the surgical design rather than verified.
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

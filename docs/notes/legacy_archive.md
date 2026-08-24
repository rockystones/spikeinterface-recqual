# The legacy archive: what is in it and what each file can settle

`D:\Claude Code\Monkey Data\Legacy` — **1,796 files** across three trees. This
maps what kind of question each part can answer, reconstructs the analysis that
was running in 2016–2017, and separates what is *confirmed* from what is
*asserted once*.

| tree | files | size | what it is |
|---|---|---|---|
| `L1MonkeyData` | 652 | 191 MB | the monkey study: array info, ephys sorts, impedance |
| `LEGACY STUFF FOUND` | 272 | 279 MB | slide decks, grant applications, recording notes |
| `Patrick` | 871 | 64 MB | mostly rat and bench work; a few monkey items |

By type: 1,458 `.txt` (nearly all impedance dumps), 183 `.nox` (potentiostat),
33 `.pdf`, 23 `.pptx`, 19 `.docx`, 18 `.fig`, 11 `.mat`, 8 `.cmp`, 7 `.m`.

## What each kind of file is good for

| you want to know | look at |
|---|---|
| **which array had which coating** | `impstructure_cell.mat` (states it per `anterior`/`posterior`), figure legends, `monkey_units_compiled.mat`, folder names |
| **implant and explant dates** | `implanted_monkeys_status.pptx`, Table 2 of the write-up, and — most reliably — **which arrays are absent from a dated impedance folder** |
| **what was actually recorded, when** | `monkey_units_compiled.mat` `fnames`, which are the per-session sort filenames |
| **what analysis was being run** | the `.fig` files and the `ephys_by_treatment_*.mat` variants; their names encode the decisions |
| **the science behind the coating** | the R01/U01 grant `RESEARCH STRATEGY` and `Specific Aims` documents |
| **per-electrode impedance** | `impstructure_cell.mat` (Oops, Picasso) and `imp_vars.mat` (Rocky) |
| **array geometry** | `.cmp` files under `array info/` |

**Folder and file names carry as much as contents.** `CTRL_11032015`,
`L1_11032015`, `coat_1025-001501`, `ctrl_1025-001497`, `pre_implant/coated`,
`noposteriorped`, `2.5sd_rem`, `sansoutlier` — every one of these encodes a
decision.

## The legacy analysis, reconstructed from file mtimes

A coherent pipeline, and its variants show what the analysts were worried about.

```
per-session sorting          J:\monkey_ephys\<Animal>\sortedmat\<A|B>\
   -> sort_<Animal>_<date>-001.mat
compile                      monkey_units_compiled.mat
   -> unitsort.<Animal>.<A|B>.{unitsum, fnames, dates, ucount, coating}
group by treatment           ephys_by_treatment_*.mat
   -> ephysXtreatment.{control, L1}.{ID, T, unitcount, maxsigM, binct, ...}
bin by month, plot           *.fig  ("Months After Implant")
```

The `J:\monkey_ephys\` path survives inside `maxamp_3array.fig` — **the
original sorted data lived on a `J:` drive**, which is a search target.

| when | what appeared | what it tells you |
|---|---|---|
| 2016-12-19 | `ucount_all`, `bin_ucount_wchase`, `maxsignal_w_chase`, and `_wo_chase` twins | first pass; Chase's inclusion was already contested |
| 2016-12-20 | `impstructure_cell.mat` | impedance compiled |
| 2017-02-10/11 | `chasesorts.mat`, `all_unitsort_newchase.mat` + figures | Chase **re-sorted** ("newchase") |
| 2017-02-16 | `..._noposterior.mat`, `ephys_by_treatment_newchase_wo_postpedestal.mat` | posterior-pedestal arrays dropped as a variant |
| 2017-04-25 | `monkey_units_compiled.mat`, "3 arrays" and "4 arrays" plot folders | the analysis settled into 3- and 4-array versions |
| 2017-05-03 | `ephys_x_treatment_3 arrays_without chase_fixbinav.mat` | binning revised ("fixbinav") |
| 2017-08-22 | `bin_ucount_wo_chase_2.5sd_rem`, `maxsignal_wo_chase` "SANS OUTLIERS" | 2.5 SD outlier removal |
| 2017-08-29 | Rocky `imp_vars.mat`, Rocky `.cmp` files | Rocky enters, implanted 2017-08-30 |

**Three sensitivity axes were being explored, all still live questions here:**
include Chase or not; include the posterior-pedestal arrays or not; remove
outliers at 2.5 SD or not. The y-axis on `maxamp_treatment_newchase.fig` runs
to 1200 µV and its `sansoutlier` twin to 450 — a single session was moving the
scale by 2.7×.

**Every treatment analysis used exactly one array per animal:**

| file | control group | L1 group |
|---|---|---|
| `ephys_by_treatment_newchase_wo_postpedestal` (Feb) | `Oops_A`, `Chase_A` | `Picasso_A`, `Luigi_A` |
| `ephys_by_treatment_4-arrays` (Apr) | `Oops_A`, `Chase_A` | `Picasso_A`, `Luigi_A` |
| `ephys_x_treatment_3 arrays...fixbinav` (May) | `Oops_A` | `Picasso_A`, `Luigi_A` |

So the published comparison rested on **four arrays, one per animal**, and by
May on three. The `_B` arrays — the posterior pedestals — were excluded, which
is exactly the attrition documented elsewhere.

## Eight sources for the cohort definition, and what each adds

| # | source | what only it gives |
|---|---|---|
| 1 | `implanted_monkeys_status.pptx` | implant dates and treatment in one table |
| 2 | folder names (`CTRL_11032015`, `coat_1025-001501`) | treatment tied to a **serial** |
| 3 | `Monkey_Data_Compile.xlsx` sheets `L1` / `Ctrl` | which animals were in which group |
| 4 | `Monkey Impedance_update_20170509.pptx` | "Oops-anterior: CTRL / Picasso-anterior: L1" in words |
| 5 | **Table 2** of the write-up | the only source with **both** axes for every array, plus euthanasia dates |
| 6 | `monkey_units_compiled.mat` | machine-readable `coating` per array, plus `fnames` |
| 7 | **figure legends** | `Oops.A.uncoated | Oops.B.coated | Picasso.A.coated | Picasso.B.uncoated | Luigi.A.coated | Chase.A.uncoated` |
| 8 | `impstructure_cell.mat` | `treatment` stated per `anterior`/`posterior` — **no A/B letter to misread** |

Sources 6, 7 and 8 were found only on a second, systematic pass. All three
agree with 1–5.

**The A/B letters are settled by source 7 in a way no other source manages.**
The figure `ucount_allmonkey_newchase_noposteriorped.fig` keeps `Oops.A`,
`Picasso.A`, `Luigi.A`, `Chase.A` and drops the `_B`s — and it is named *no
posterior pedestal*. So **A = anterior pedestal, B = posterior pedestal**, and
that composes with source 8 to give treatment without ambiguity.

**One source disagrees.** The array-info folders name Oops's arrays
`A_1025-001393` and `B_1025-001391`, but 1393 is the *posterior*, which every
other source calls B. The folder letters are the outlier — one source against
seven. Never join on the letter.

## Anchors: facts you can verify without trusting a document

These are the most valuable things in the archive, because they are
measurements rather than assertions.

**1. Coated arrays sit at roughly twice the impedance of uncoated ones.**
From `impstructure_cell.mat`, 1 kHz |Z| median across all electrodes and dates:

| animal | array | treatment | median |Z| |
|---|---|---|---|
| Oops | anterior | uncoated | 623 kΩ |
| Oops | posterior | **coated** | **1425 kΩ** (2.29×) |
| Picasso | anterior | **coated** | **1034 kΩ** (2.10×) |
| Picasso | posterior | uncoated | 493 kΩ |

Two animals, independently, same direction and nearly the same factor. **The
treatment label can be checked against the electrode measurement.** Any future
array whose coating is uncertain can be tested this way.

**2. An array's absence from a dated folder dates its explant.** The impedance
tree has one folder per session with `Anterior*.txt` / `Posterior*.txt` inside.
Oops posterior vanishes after 2016-12-02, Picasso posterior after 2016-09-14 —
matching the documented removals of 12/2016 and 2016-10-11 with nothing else
required.

**3. Sort filenames date every session.** `monkey_units_compiled.mat` `fnames`
carry `sort_Oops_baseline_Oops_2017_02_15-001.mat` and the like, giving a
per-array session list independent of any tank clock. Oops A ends 2017-02-15
and B ends 2016-12-21 — matching the TDT stores `eNe1` and `eNe2` exactly, and
confirming the store→array inference.

**4. `ucount` sums reproduce the spreadsheet.** `Luigi_A.ucounts` is a (4, 26)
array of unit-quality categories; 133+78+46+9 = **266**, 136+54+46+17 = **253**,
65+78+52+23 = **218** — the compile spreadsheet's first three Luigi values.
**The spreadsheet was generated from the `.mat`**, so the two are one source,
not two.

## Consistency audit

**Agrees across every source checked** — the coating assignment for Oops,
Picasso, Luigi and Rocky; implant dates; and Oops's two explant dates, which
match in the status deck, the impedance folders, the TDT stores and the legacy
sort filenames.

**Disagrees, and the minority is identifiable:**

| claim | majority | outlier |
|---|---|---|
| Picasso sacrifice | **2018-03-02** (Table 2; consistent with impedance to Feb 2018 and blocks to Apr 2017) | topography deck: *"Sacrificed March 2017"* — a year early |
| Oops A/B letters | A = anterior (7 sources) | array-info folder `A_1025-001393` |

**Unresolved.** Picasso's legacy sorts have `B` — the *uncoated posterior* —
continuing to **2017-03-24**, five months past its documented explant, while
`A` stops 2016-12-30. `B`'s max signal roughly doubles across that boundary
(64.4 → 127.1 µV, p=0.012), but it is also significantly different from `A`
(p=0.034), so it is not simply `A` relabelled. The same shape appears in the
TDT stores. **No source in the archive explains it.**

## The science, for context

The R01 (2013, 2014) and U01 (2016) applications state the rationale: **L1 is
L1CAM**, a neural cell adhesion molecule, coated on custom Blackrock arrays, on
the hypothesis that promoting neuronal growth at the probe surface improves
recording quality while reducing microglial activation. The U01 aims cite the
prior result directly — *"L1 coating showed significantly improved single unit
recording yield of a Blackrock array in primate motor cortex over the course of
10 months"* — which is the claim this project's longitudinal analysis is
positioned to re-examine on the full corpus.

Sorting was done in **UltraMegaSort2000** (manual present, 2013) on Plexon
files (`PL2 File System Overview`, `Matlab Offline Files SDK`), which is what
the `sort_*.mat` files are.

## What remains unexamined

- **`Patrick/`, 871 files** — mostly rat and bench work (`Patrick/rat`,
  `modelcelltests`, `aptamer`), but it contains `Batista_arrays` and
  `monkey_array/Rocky/postimplant` which are monkey-relevant.
- **183 `.nox`** potentiostat files, the raw form behind the impedance dumps.
- **1,458 `.txt`** impedance dumps — read in aggregate, not individually.
- The grant documents beyond the aims sections.
- `Oops_array_maps.rar` is **already extracted** alongside it as
  `Oops_array_maps/`; it holds only the `.cmp` and IFU files already known.

## Related

[[cohort_definition]] for the conclusions this archive supports,
[[impedance_sources]] for how the impedance data is used,
`docs/handoff_legacy_search.md` for the drive-wide search seeded from here.

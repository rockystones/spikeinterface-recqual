# Handoff: legacy-drive search for cohort-definition evidence

**To:** the Claude Code session with the hard-drive census / dedupe corpus
**From:** the `recqual` analysis session (`D:\Claude Code\SpikeInterface`)
**Date:** 2026-08-23

## What I need

I am pinning down, without ambiguity, the **surface-treatment definition of the
monkey cohort**: for each animal and each implanted Utah array — the serial, the
pedestal position, the cortical location, the coating, the implant date and the
explant/failure date.

Most of it is now established from `D:\Claude Code\Monkey Data\Legacy` (see
"Already established"). **Eight specific questions remain**, listed at the end.
I need you to search the census for files that answer them.

**Ground rule the owner set, and I have been applying it:** individual files
contain mistakes. A fact is accepted when **independent sources agree**, not
because one authoritative-looking document says it. So please report *every*
copy and variant you find, including ones that disagree — a disagreeing copy is
data, not noise. Do not silently pick a winner.

---

## What a useful file looks like

These are the seed files that actually resolved things. Look for siblings,
earlier/later revisions, and copies on other drives.

### Highest value — these carried the answers

| file | why it mattered |
|---|---|
| `LEGACY STUFF FOUND\implanted_monkeys_status.pptx` | **The master table.** Columns: Monkey / Implanted / Arrays / Location / Treatment / Notes. Gave implant dates and coating for 5 animals. |
| `Monkey_Data_Compile.xlsx` | Two sheets named **`L1`** and **`Ctrl`**, each listing animals + session dates + unit counts. Which sheet an animal is on *is* its coating. |
| `LEGACY STUFF FOUND\From Noah\Recording Notes - Luigi.pdf` | Day-by-day log, 2012-12-20 → 2013-09-05. Gave the surgery date ("2 days after surgery!") and the exact date the posterior array was disconnected. |
| `L1MonkeyData\impedance\rawdata\data\...` | Folder names encode treatment: `coat_1025-001501` vs `ctrl_1025-001497`, `pre_implant/coated` vs `pre_implant/ctrl`. Per-date subfolders with `Anterior*.txt` / `Posterior*.txt` — **an array's absence from a date is the explant evidence.** |
| `L1MonkeyData\array info\Monkey_P\CTRL_11032015\` and `L1_11032015\` | Folder name = treatment + implant date; contents = the array's `.cmp` and serial. |
| `LEGACY STUFF FOUND\effect of electrode topography on chronic array performance.pptx` | Slide 4 "Subjects & Data Available" — per-array date ranges and sacrifice dates. |
| `LEGACY STUFF FOUND\Monkey Impedance_update_20170509.pptx` | Slide 3 states plainly: "Oops-anterior: CTRL / Picasso-anterior: L1". |

### Search patterns

**By name** (case-insensitive, any extension):
```
implanted_monkeys  monkey_data_compile  array log  array info  array_to_matlab
recording notes    surgery              implant              explant
necropsy           sacrific             perfus               pedestal
topography         L1 coated            L1MonkeyData
```

**Animal names** — note the aliases: Picasso is also **"Monkey P"** and
**"Monkey_P"**; Oops arrays appear as **A_1025-001393** / **B_1025-001391**:
```
Chase  Luigi  Oops  Picasso  Monkey_P  MonkeyP  Rocky  Nigel  Fisk
```

**Serials** — these are the unambiguous keys. Any file containing one is worth
reporting:
```
1025-001082  1025-001085          (Luigi)
1025-001391  1025-001393          (Oops)
1025-001499  1025-001503          (Picasso)
1025-001497  1025-001501          (Rocky implant 1)
1025-004377  1025-004419          (Rocky implant 2)
1025-001473  1025-001496          (Nigel)
1025-001498  1025-001504          (Fisk)
```
Blackrock also uses a build prefix that appears in filenames:
`13167-25`, `13167-31`, `13966-8`, `13966-20`, `13966-25`, `13966-27`.
Any `13xxx-xx` + serial pair is an array datasheet — **please report the
prefix, it identifies the build lot.**

**Coating vocabulary.** Generation 1 (2012–2017) uses the first row; the newer
implants (2023 and 2025) use the second, and **no legacy document I have found
mentions the second row at all**:
```
L1  L1CAM  coated  coat  ctrl  control  uncoated  bare
TNP         TNP L1        EDCNHS
```
**Any document defining TNP, TNP L1 or EDCNHS, or assigning them to serials
1473 / 1496 / 1498 / 1504 / 4377 / 4419, is the single highest-value result you
could return.** See Q1.

**File types that have paid off:** `.pptx`, `.xlsx`/`.xls`, `.pdf`, `.cmp`,
`.txt` impedance dumps, `.rar`/`.zip` archives (one seed is
`Oops_array_maps.rar`, unopened). Also worth checking: lab-notebook scans,
`.docx` protocols, surgery photos with dated filenames, and any Google Sheets
export.

**Not a lead:** `implanted_monkeys_status.pptx` slide 2 links a Google Sheets
"array log". The owner confirms its content is already covered by what is
established below — **do not spend time hunting for a copy.**

---

## Already established — do not spend time re-confirming

Each row below is agreed by the number of independent sources shown. Report
contradicting copies if you find them, but these are not open questions.

| animal | implanted | pedestal | cortex | treatment | serial | removed | sources |
|---|---|---|---|---|---|---|---|
| Chase | ? | ? | ? | uncoated | ? | ? | 1 |
| Luigi | 2012-12-18 | Anterior | lateral | **L1 coated** | 1025-001082 | ? | 3 |
| Luigi | 2012-12-18 | Posterior | medial | uncoated | 1025-001085 | disconnected **2013-03-20** | 2 |
| Oops | 2014-12-16 | Anterior | ? | uncoated | 1025-001391 | **2017-03** | 4 |
| Oops | 2014-12-16 | Posterior | ? | **L1 coated** | 1025-001393 | **2016-12** | 4 |
| Picasso | 2015-11-03 | Anterior | medial | **L1 coated** | 1025-001499 | survivor | 4 |
| Picasso | 2015-11-03 | Posterior | lateral | uncoated | 1025-001503 | **2016-10-11** | 3 |
| Rocky | 2017-08-30 | Anterior | lateral | **L1 coated** | 1025-001501 | — | 3 |
| Rocky | 2017-08-30 | Posterior | medial | uncoated | 1025-001497 | — | 3 |
| Rocky **I2** | 2025-03-26 | Anterior | medial | **TNP** (all shanks) | 1025-004377 | — | 1 |
| Rocky **I2** | 2025-03-26 | Posterior | lateral | **TNP L1** (all shanks) | 1025-004419 | — | 1 |
| Nigel | ? | Anterior | ? | **TNP vs TNP L1** (striped) | 1025-001496 | — | 1 |
| Nigel | ? | Posterior | ? | **EDCNHS vs ctrl** (striped) | 1025-001473 | — | 1 |
| Fisk | ? | ? | lateral | striped, as Nigel | 1025-001498 | — | 1 |
| Fisk | ? | ? | medial | striped, as Nigel | 1025-001504 | — | 1 |

The last six rows are **one source only** — the owner. They are what Q1 is
about; everything above them is multiply confirmed.

Convention, from the owner: **anterior/posterior = pedestal position on the
skull; lateral/medial = array position on cortex.** They are not the same axis
and documents sometimes give only one.

---

## The eight open questions

Ordered by value to me.

### Q1 — What are `TNP`, `TNP L1` and `EDCNHS`, and which arrays got them?
These belong to the **two newer implant generations only** — Nigel, Fisk, and
Rocky's second implant (2025). No generation-1 animal has them, which is why
the `L1MonkeyData` tree correctly never mentions them: **that tree predates
them, so do not search it.** Anything relevant will be **2020 or later**.

Two different designs are involved, and both need documenting:

- **Striped, within-array** — Nigel and Fisk. Alternating rows of shanks carry
  different surface conditions on the *same* array. Nigel:
  `1473` Posterior = **EDCNHS vs ctrl**, `1496` Anterior = **TNP vs TNP L1**;
  Fisk the same pattern on `1498`/`1504`. **A schematic showing which shank
  rows carry which treatment is the single most valuable thing you could
  find** — the stripe assignment is currently inferred from surgical design,
  not verified, and it is the axis an entire analysis rests on.
- **Whole-array** — Rocky implant 2, 2025-03-26: `1025-004377` Anterior/medial
  = **TNP on all shanks**; `1025-004419` Posterior/lateral = **TNP L1 on all
  shanks**.

Also worth finding: a definition of each chemistry (what EDCNHS and TNP
actually are, and how TNP L1 differs from L1), and any coating/surgery record
for the 2023 and 2025 implants.

### Q2 — Chase: implant date, array serial, pedestal position, `.cmp` file
The status deck lists Chase with a single **uncoated** array and `?` for
everything else. Chase's recordings run **2009-03-17 → 2010-02-23** — the
oldest data in the corpus. No serial, no `.cmp`, so no spatial analysis is
possible. A single datasheet would unlock it. Also try `Chase` inside
`L1MonkeyData\ephys\chase_data`.

### Q3 — Picasso: three sources conflict about the end of its recordings
This is the one genuine contradiction I could not resolve.
- Status deck **and** impedance folders agree the **posterior** pedestal came
  out **2016-10-11** (last posterior impedance 2016-09-14; the array is absent
  from every folder from 2016-10-20 on).
- The topography deck says **"Picasso Sacrificed March 2017"**.
- But TDT blocks labelled Picasso run to **2017-04-14**, and the second store
  (`eNe2`) is alive and normal throughout.
- And `eNe1` continues to **2017-01-06** with healthy signal — three months
  *after* the posterior removal — with no death signature (noise flat at
  9.4→9.7 µV, all 96 electrodes active) and **not** a duplicate of `eNe2`
  (0 of 14 shared blocks have matching values).

**What would settle it:** a necropsy/sacrifice record with a date, a surgery
log for the 2016-10 explant, or any block-level recording log naming which
array each TDT store came from. Also: the topography deck claims Picasso
anterior impedance runs to **Feb 27 2018**, but the folders I have stop at
2017-04-28 — **a later impedance drop exists somewhere.**

### Q4 — Which TDT store is which array?
`eNe1` / `eNe2` / `eNe3` are store names; nothing in the tank records which
physical array each came from. I inferred it from which store disappears when
(Oops matches its explant dates exactly). **Any TDT/OpenEx/Synapse config,
`.pmap`, block notes, or experiment log that names the mapping would replace an
inference with a fact.**

Related and separately valuable: I am also trying to recover the **TDT→Utah
channel map**. A surviving **Synapse `Mapper` configuration or `.pmap` file**
would answer that outright. Search for `pmap`, `Mapper`, `SynapseAPI`,
`.rcx`, `.rpx`, `OpenEx`, `tankmap`, and for the adapter part number
`ZCA-CK96` / `ZCA-CK96A`.

### Q5 — Luigi's 21-month gap, and its array count
TDT blocks run 2013-01-20 → 2013-05-17, then **nothing until 2015-03-05**,
then 2015-03 → 2016-08-30. The recording notes stop 2013-09-05. Was the animal
rested, was there a second surgery, or is a drive of 2013–2015 data missing?
Also: 2013 blocks carry **three** stores (`eNe1/eNe2/eNe3`) for **two** arrays —
what was the third?

### Q6 — Oops cortical locations
The status deck gives Oops's pedestals (Anterior/Posterior) but **not** whether
each array sat on lateral or medial cortex — the only animal where that is
missing. Luigi, Picasso and Rocky all have it.

### Q7 — Explant/failure dates for Luigi and Rocky
Luigi: both arrays "removed?" — only the 2013-03-20 disconnection of the
posterior is documented, and that is a cable decision, not an explant.
Rocky: the owner gives an end date of **2025-06-11** but no per-array failure.

### Q8 — `Oops_array_maps.rar`
`L1MonkeyData\array info\Oops\Oops_array_maps.rar` (3.5 MB, dated 2016-02-08)
is unopened. If you find an extracted copy elsewhere, or can list its contents,
it may hold the Oops cortical locations for Q6.

---

## What to send back

For each hit: **full path, drive, size, mtime, and the relevant excerpt** — a
path alone is not usable. Where a document states a fact, quote the sentence or
give the table row.

Please explicitly flag:
- any file that **contradicts** the established table above;
- **duplicate copies with different mtimes or content** — the revision history
  is itself evidence of which version is right;
- anything mentioning **TNP** or **EDCNHS** (Q1), however trivial-looking.

I will treat multi-source agreement as the criterion, so volume of
corroboration matters more than any single authoritative-looking file.

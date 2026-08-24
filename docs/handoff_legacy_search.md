# Handoff: legacy-drive search for anything about the monkeys

**To:** the Claude Code session with the hard-drive census / dedupe corpus
**From:** the `recqual` analysis session (`D:\Claude Code\SpikeInterface`)
**Updated:** 2026-08-23

## The ask

**Find anything on the drives that is relevant to the monkey cohort.** Not a
narrow lookup — a sweep. I have reconstructed most of the cohort definition
from one folder (`D:\Claude Code\Monkey Data\Legacy`) and from the recording
files themselves, and that reconstruction produced both confirmations and two
real data bugs. There is almost certainly more of this material scattered
across the other drives.

This document gives you **search seeds taken from the files that actually
worked**, what is already settled so you do not spend effort re-deriving it,
and the specific holes worth aiming at.

**Ground rule the owner set, and I have been applying it:** individual files
contain mistakes. A fact is accepted when **independent sources agree**, not
because one authoritative-looking document says so. Report *every* copy and
variant you find, **including ones that disagree** — a disagreeing copy is
evidence, not noise. Do not silently pick a winner. Two of the biggest results
below came from noticing that a document and the raw data conflicted.

---

## Search seeds

### Names and aliases

```
Chase   Luigi   Oops   Picasso   Rocky   Nigel   Fisk
Monkey_P   MonkeyP   Monkey P            (all = Picasso)
```
TDT blocks appear as `Block-NN`, and as `<Animal>_<YYYY>_<MM>_<DD>_<A|B>-N`.
Beware: a block named `Picasso_2018_02_22_A-1` sits inside **Rocky's** tree —
animal names in paths are not reliable.

### Array serials — the unambiguous key

Any file containing one of these is worth reporting.

```
1025-001082  1025-001085     Luigi
1025-001391  1025-001393     Oops
1025-001499  1025-001503     Picasso
1025-001497  1025-001501     Rocky implant 1  (2017)
1025-004377  1025-004419     Rocky implant 2  (2025)
1025-001473  1025-001496     Nigel
1025-001498  1025-001504     Fisk
```
Serials often appear abbreviated as `SN1503`, `SN 1025-001503`, or just `1503`.
Blackrock build prefixes appear alongside them in datasheet filenames —
`13167-25`, `13167-31`, `13966-8`, `13966-20`, `13966-25`, `13966-27`,
`1138-32`, `1138-34`. **Report the prefix; it identifies the build lot.**

### Treatment vocabulary

Generation 1 (2012–2017) uses the first row. The newer implants (2023, 2025)
use the second, and **no document I have found mentions the second row at all**:

```
L1   L1CAM   coated   coat   ctrl   control   uncoated   bare
TNP        TNP L1        EDCNHS
```

### Filename and folder patterns that paid off

```
implanted_monkeys   monkey_data_compile   array info   array_to_matlab
recording notes     surgery   implant   explant   necropsy   sacrific   perfus
pedestal   topography   impedance   L1MonkeyData   unitsort   fixbinav
```
**Folder names carry the answers as often as file contents** — `CTRL_11032015`,
`L1_11032015`, `coat_1025-001501`, `ctrl_1025-001497`, `pre_implant/coated`,
`A_1025-001393`. Please report directory names, not just files.

### File types that paid off

`.pptx` (the master table was a PowerPoint), `.xlsx`/`.xls`, `.pdf` (a scanned
day-by-day log), `.mat` (a compiled struct with a per-array `coating` field),
`.cmp`, per-date `.txt` impedance dumps, and `.rar`/`.zip` archives. Also worth
checking: lab-notebook scans, `.docx` protocols, dated surgery photos, and
TDT/Synapse config files.

### The seven files that resolved the most

| file | what it gave |
|---|---|
| `LEGACY STUFF FOUND\implanted_monkeys_status.pptx` | master table: Monkey / Implanted / Arrays / Location / Treatment / Notes |
| `Monkey_Data_Compile.xlsx` | two sheets named **`L1`** and **`Ctrl`** — which sheet an animal is on *is* its coating |
| `L1MonkeyData\ephys\monkey_units_compiled.mat` | machine-readable `coating` per array, plus real session-date arrays |
| `LEGACY STUFF FOUND\From Noah\Recording Notes - Luigi.pdf` | day-by-day log with a **TDT Block #** column — caught a clock bug |
| `L1MonkeyData\impedance\rawdata\data\...` | per-date folders; **an array's absence from a date is explant evidence** |
| `L1MonkeyData\array info\Monkey_P\{CTRL,L1}_11032015\` | folder name = treatment + implant date |
| `...\effect of electrode topography on chronic array performance.pptx` | per-array date ranges; also contains a one-year error |

**Not leads:** the Google Sheets "array log" linked from
`implanted_monkeys_status.pptx` — the owner confirms its content is already
covered. And `Oops_array_maps.rar` — the owner confirms it holds only the
`.cmp` files already extracted.

---

## Already settled — do not re-derive

Confirmed by the number of independent sources shown.

| animal | implanted | pedestal | cortex | treatment | serial | array gone | euthanized | src |
|---|---|---|---|---|---|---|---|---|
| Chase | ? | ? | ? | uncoated | ? | ? | ? | 2 |
| Luigi | 2012-12-18 | Anterior | lateral | **L1** | 1025-001082 | ? | 2018-05-24 | 4 |
| Luigi | 2012-12-18 | Posterior | medial | uncoated | 1025-001085 | disconn. 2013-03-20 | 2018-05-24 | 3 |
| Oops | 2014-12-16 | Anterior | lateral | uncoated | 1025-001391 | 2017-03 | 2017-04-10 | 6 |
| Oops | 2014-12-16 | Posterior | medial | **L1** | 1025-001393 | 2016-12 | 2017-04-10 | 6 |
| Picasso | 2015-11-03 | Anterior | medial | **L1** | 1025-001499 | survivor | 2018-03-02 | 5 |
| Picasso | 2015-11-03 | Posterior | lateral | uncoated | 1025-001503 | 2016-10-11 | 2018-03-02 | 4 |
| Rocky | 2017-08-30 | Anterior | lateral | **L1** | 1025-001501 | — | 2025-06-11 | 4 |
| Rocky | 2017-08-30 | Posterior | medial | uncoated | 1025-001497 | — | 2025-06-11 | 4 |
| Rocky **I2** | 2025-03-26 | Anterior | medial | **TNP** all shanks | 1025-004377 | — | 2025-06-11 | 1 |
| Rocky **I2** | 2025-03-26 | Posterior | lateral | **TNP L1** all shanks | 1025-004419 | — | 2025-06-11 | 1 |
| Nigel | ? | Anterior | ? | **TNP vs TNP L1** striped | 1025-001496 | — | ? | 1 |
| Nigel | ? | Posterior | ? | **EDCNHS vs ctrl** striped | 1025-001473 | — | ? | 1 |
| Fisk | ? | ? | lateral | striped, as Nigel | 1025-001498 | — | ? | 1 |
| Fisk | ? | ? | medial | striped, as Nigel | 1025-001504 | — | ? | 1 |

The last six rows are **one source only** (the owner). Everything above them is
multiply confirmed.

**Convention:** *anterior/posterior* = pedestal position on the skull;
*lateral/medial* = array position on cortex. Different axes; most documents give
only one.

**Three design generations**, which is why the vocabulary changes:

| gen | years | comparison | unit | animals |
|---|---|---|---|---|
| 1 | 2012–2017 | L1 vs uncoated | whole array | Luigi, Oops, Picasso, Rocky I1, + Chase |
| 2 | 2023–2025 | striped shank rows | **within** one array | Nigel, Fisk |
| 3 | 2025 | TNP vs TNP L1 | whole array | Rocky I2 |

**One labelling trap.** `monkey_units_compiled.mat` labels Oops's arrays
`A`=uncoated and `B`=coated, while the array-info folders are named
`A_1025-001393` and `B_1025-001391` — and 1393 is the *coated* posterior. The
two A/B conventions are **opposite**. Never join on the letter.

---

## Where to aim

Roughly by value. Anything relevant is welcome even if it is not on this list.

### 1. The newer implants — 2020 and later
`TNP`, `TNP L1` and `EDCNHS` are **owner-stated only**. The `L1MonkeyData` tree
predates them, so **do not search it for these** — anything relevant is 2020+
and filed elsewhere. Wanted:

- **A schematic showing which shank rows carry which treatment** on Nigel and
  Fisk. Highest-value item on the list: the striped design is a within-array
  contrast, an entire analysis rests on the stripe assignment, and that
  assignment is currently inferred from surgical design rather than verified.
- What the chemistries are — what EDCNHS and TNP are, and how TNP L1 differs
  from plain L1.
- Surgery, coating or QA records for the 2023 (Nigel, Fisk) and 2025
  (Rocky I2) implants; implant dates for Nigel and Fisk; their pedestal and
  cortical locations.

### 2. Chase
Oldest data in the corpus (2009-03-17 → 2010-02-23) and least documented: no
implant date, no serial, no `.cmp`, so **no spatial analysis is possible**. A
single array datasheet would unlock it. The compiled `.mat` confirms
`Chase A = uncoated`, 11 sessions, 2009-03-17 → 2010-02-16. Try
`L1MonkeyData\ephys\chase_data` and anything from 2008–2010.

### 3. Luigi's 21-month hole
TDT blocks run 2012-12-20 → 2013-05-17, then **nothing until 2015-03-05**, then
to 2016-08-30. The notes stop 2013-09-05, and Luigi was not euthanized until
2018-05-24. **Is 2013-06 → 2015-02 missing data or a genuine pause?** Any Luigi
recordings, notes or logs in that window would settle it.

Do **not** treat the compile spreadsheet's apparent 2013→2015 Luigi series as
proof the data exists — it is an interpolated monthly axis (see §8).

Also: Luigi's 2013 blocks carry **three** stores (`eNe1/eNe2/eNe3`) for **two**
arrays. What was the third?

### 4. TDT store → array, and the TDT channel map
Nothing in a tank records which physical array fed `eNe1` vs `eNe2`. I inferred
it from which store disappears when, and it matches Oops's explant dates to the
week — but it is an inference. Any experiment log, block sheet or config naming
the mapping would replace it with a fact.

Separately and just as valuable: I am trying to recover the **TDT → Utah
channel map**, and a surviving **Synapse `Mapper` configuration or `.pmap`
file** would answer it outright. Search:
```
pmap   Mapper   SynapseAPI   OpenEx   tankmap   .rcx   .rpx
ZCA-CK96   ZCA-CK96A   ZC96   ZD96   RZ2   PZ2   ZIF-Clip
```

### 5. Picasso's unexplained recordings
Its posterior pedestal came out 2016-10-11 (three sources agree), yet the
`eNe1` store runs to 2017-01-06 looking healthy — noise flat at 9.43→9.70 µV,
all 96 electrodes active, and not a duplicate of `eNe2`. Any block-level
recording log for Picasso Oct 2016 – Apr 2017 would explain it. Also: the
topography deck cites Picasso anterior impedance to **Feb 27 2018**, but the
folders here stop 2017-04-28 — **a later impedance drop exists somewhere.**

### 6. Explant and failure dates
Luigi: only the 2013-03-20 *disconnection* of the posterior is documented, and
that is a cable decision, not an explant. Rocky: euthanized 2025-06-11, no
per-array failure recorded. Nigel and Fisk: nothing at all.

### 7. Impedance beyond what I have
I have Rocky, Oops and Picasso. **Nothing for Luigi, Chase, Nigel or Fisk.**
The dumps are per-date folders of `.txt` files named like `Anterior_A1.txt`,
`ctrl_B2.txt`, `full96ch.txt`. Any such tree for the missing animals is
valuable — impedance is genuinely electrode-bound and is one of the few things
that could independently validate a channel map.

### 8. Anything that dates a recording
Two date bugs have already surfaced, so provenance matters:

- **Luigi's TDT tank clock is one month fast for blocks 1–39**, corrected at
  Block-40 (2013-03-14). Caught only because the notes carry block numbers: the
  raw series runs *backwards* across that boundary, and the corrected first
  block lands exactly on the notes' "2 days after surgery".
- The topography deck says Picasso was *"Sacrificed March 2017"*; two other
  sources say **March 2018**.
- The compile spreadsheet's Luigi column is a monthly resampling, not session
  dates — in `monkey_units_compiled.mat` Luigi is the only animal carrying
  `dayvec` (day offsets) instead of `dates`, and 13 of 25 consecutive
  spreadsheet rows share an identical max amplitude.

So: recording logs, block sheets, session indices, calendar exports — anything
pairing a block or file name with a date.

---

## What to send back

For each hit: **full path, drive, size, mtime, and the relevant excerpt.** A
path alone is not usable — where a document states a fact, quote the sentence
or give the table row.

Please explicitly flag:
- anything that **contradicts** the settled table above;
- **duplicate copies with different mtimes or content** — the revision history
  is itself evidence;
- anything mentioning **TNP**, **TNP L1** or **EDCNHS**, however trivial;
- anything for **Chase**, **Nigel** or **Fisk**, the least documented animals.

Volume of corroboration matters more than any single authoritative-looking
file.

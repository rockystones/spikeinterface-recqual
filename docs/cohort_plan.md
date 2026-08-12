# Six-subject cohort: inventory and session plan

Derived from `_monkey-ephys.csv` (979,044 rows, 25 volumes) re-cut as an *analysis* census rather than a storage one. Storage view lives in `_MONKEY-EPHYS.md`; this file asks a different question — what can actually be run, on which subject, from where.

Written 2026-08-11.

## 1. What each subject is

Distinct files (name+size signature, copies collapsed).

| subject | acquisition | broadband | snippets | span | sorted reference | impedance |
|---|---|---|---|---|---|---|
| **Luigi** | TDT + Blackrock | 5,183 `.sev` + 178 `.ns5` | 178 `.nev` | 2015–2016 | 493 `.plx` | **none found** |
| **Oops** | TDT + a little Blackrock | 7,584 `.sev` + 13 `.ns5` | 13 `.nev` | 2015–2017 | 163 `.plx` | 2,589 `.txt` + 984 `.nox` |
| **Picasso** | TDT only | 6,623 `.sev` | **none** | 2016–2017 | 173 `.plx` | 1,974 `.txt` |
| **Rocky** | TDT + Blackrock | 12,875 `.sev` + **470 `.ns5`** | 966 `.nev` | 2017-09 → 2025-06 | 81 `.plx` | 1,275 `.txt` |
| **Nigel** | Blackrock only | 168 `.ns5` | 483 `.nev` | 2023-01 → 2024-12 | — | 350 `.txt` |
| **Fisk** | Blackrock only | 132 **`.ns6`** + 146 **`.ns3`** | 436 `.nev` | 2023-06 → 2025-05 | — | 282 `.txt` |

Three consequences the existing code does not handle:

**Rocky is not snippet-only.** 470 `.ns5` exist, 431 of them on `L:`. Everything in [`snippet_sorting.md`](notes/snippet_sorting.md) and [`snippet_noise_floor.md`](notes/snippet_noise_floor.md) was written under "this cohort has no continuous data", which was true of the *local staging folder* (`D: Data`: 857 `.nev`, 0 `.ns5`) and false of the estate. The biased noise estimate, the unmeasurable threshold drift, the unusable sorter pool — all of it is fixable for Rocky, not just for future subjects.

**Fisk uses different streams.** `.ns6` is the 30 kHz broadband and `.ns3` the LFP; there is no `.ns5`. `stream_id` must come from the subject registry, never be assumed. CLAUDE.md's "`.ns5` = broadband" rule holds for four subjects and not for Fisk.

**Picasso has no Blackrock at all.** TDT `.sev` and Plexon `.plx` only. Nothing in the current pipeline reads either.

## 2. Rocky has two implants, and the filenames do not say so

| | implant 1 | implant 2 |
|---|---|---|
| arrays | **Anterior** = `SN 1025-001501`, **Posterior** = `SN 1025-001497` | **Anterior** and **Posterior** again — serials `1025-004377` / `1025-004419`, assignment unknown |
| implanted | before 2017-09 | **2025-03-26**, right hemisphere |
| recordings | 2017-09-01 → 2024-03-29 (TDT from 2017-09-01, Blackrock from 2017-09-21) | 2025-04-04 → 2025-06-05, 10 weekly dates |
| CMP location | `Rocky\preimplant\` | `…\Chronic Impedance\Second batch\Rocky New\` and `…\Surgery photo\Rocky\Rocky Right Hemisphere Implant 2025-03-26\Utah array CD files\` |

**Both implants write `Rocky_{Anterior,Posterior}_<date>_Baseline_DigitalHeadstage.nev` — the same two labels for four different physical arrays.** Concatenating on filename merges them and reads a fresh implant as the old one recovering. Every key must be `(subject, implant, array)`, and implant age measured from that implant's own surgery date. `scratch_cohort_registry.py` assigns implant by surgery-date ordering, not by observed date range: a range built from the Blackrock era alone stranded 1,213 of Rocky's TDT files.

Because the labels repeat, **which serial is Anterior in implant 2 cannot be inferred from the data** and is recorded as null rather than guessed.

Two further corrections to session 4/5:

- **2024 exists and was never analysed.** Six dates, 2024-01-19 → 2024-03-29, Anterior, each with `.ns5`. The implant-1 series currently stops at 2023-10-06.
- **2025 was excluded on instruction** (`EXCLUDE_YEARS = {"2025"}` in `scratch_rocky_inventory.py`) when it looked like stray files. It is a second implant and is in scope.

**`-MA` is a recording variant, not an array.** Every 2025 date carries a plain recording and an `-MA` one *per array*, each with its own Plexon `-01`/`-02` output. Still open: what MA denotes. Carried as a `variant` column so it can never be silently pooled with the base recording.

## 3. Where to read from

Coverage = share of that subject's distinct acquisition files held by one volume.

| subject | best volume | coverage | second |
|---|---|---|---|
| Oops | `L: MonkeyEphys(Delin)` | **100 %** | `E: MED` 73 % |
| Luigi | `L: MonkeyEphys(Delin)` | **100 %** | `E: MED` 10 % |
| Rocky | `L: MonkeyEphys(Delin)` | **95 %** | `G: OneDrive` 44 % |
| Picasso | `L: MonkeyEphys(Delin)` | 75 % | `E: DATASSD` 58 % |
| Nigel | `E: Dani NTE` / `F: BackupHDD` | 67 % | `F: My Passport` 56 % |
| Fisk | `H: BackupHDD` / `G: OneDrive` | 59 % | `E: SSD128GB` 41 % |

`L:` alone stages four of six subjects. **Nigel and Fisk are not on `L:` at all** and each needs two volumes merged to reach full coverage — that merge is a prerequisite for their sessions, not a detail.

## 4. Impedance

| subject | format | notes |
|---|---|---|
| Oops, Picasso, Nigel, Rocky (first batch) | `{Array}_{Bank}{Half}.txt` under a dated folder | **Identical to the format already parsed** in `scratch_rocky_impedance.py` |
| Rocky (second batch) | `<lot> SN <serial>.txt` | Per-array manufacturer file, different layout |
| Fisk | `<date>-<array>-MotorImpedance.txt` | Plus `Mapping and Impedance\` folders holding 3-minute `.ns3`/`.nev` recordings |
| Oops (extra) | 984 `.nox` | Ripple/Trellis native; not yet read by anything here |
| Luigi | — | **None found in the census** |

The blocker is the same one for all of them: **which electrode each of the 16 sweeps inside a `{Bank}{Half}` file corresponds to**. Two attempts to establish it empirically failed ([`impedance_parsing.md`](notes/impedance_parsing.md)). It is one answer that unlocks five subjects at once, which changes its priority — it is no longer a Rocky detail.

Picasso and Nigel also carry variant filenames encoding acquisition conditions (`_newCable`, `_newplug`, `_no_autorange`, `_flip_GND_direction`, `_amplitude_correction`). Those are operator experiments on the measurement rig, not electrode properties, and must be kept out of the longitudinal series rather than averaged into it.

## 5. Session plan

Each session is one task, ends with a logbook entry, and leaves the repo runnable. Sessions 6–8 are prerequisites; 9–13 are independent of each other once 6–8 land.

### S06 — Cohort registry and staging manifest — **DONE**
`notebooks/scratch_cohort_registry.py` → `configs/subjects/*.json`, `data/derived/cohort_index.parquet` (39,851 distinct acquisition files), `data/derived/staging_manifest.csv`.

**Total working set: 1,979 GiB** — the acquisition tier only, against 11.5 TiB for the estate. 95 % of files carry a parseable date; the 5 % that do not are listed below and need header reads, not better regexes.

| subject | files | GiB | dated | volumes |
|---|---|---|---|---|
| Rocky | 15,562 | 813 | 100 % | 6 (L: holds 724 GiB) |
| Oops | 8,171 | 172 | 100 % | **1** (all on L:) |
| Luigi | 7,146 | 478 | **75 %** | 2 |
| Picasso | 7,297 | 145 | 100 % | 2 |
| Nigel | 819 | 177 | 100 % | 4 |
| Fisk | 856 | 194 | 100 % | 2 |

Undated: all 178 Luigi `.ns5`, 178 `.nev` and 493 `.plx` (`datafileNNN`), 592 Luigi tank indices (`Block-NN`), and 13 Oops Blackrock triples. Those dates live in file headers.

### S07 — Generalise the Blackrock path off Rocky-specific assumptions
The loaders hardcode Rocky's two arrays, its CMP pair and `.ns5`. Parameterise by registry entry; add `.ns6`/`.ns3`; make `stream_id` a config value. Verify channel order against each subject's own CMP, per CLAUDE.md's standing warning. Regression: Rocky implant 1 must reproduce session 4/5 numbers exactly.

### S08 — Nigel and Fisk, sorting-free layer first
Both are Blackrock-only and small (651 and 714 acquisition files). Run the layer-1 event pass — crossing rate, noise floor, amplitude percentiles, peak SNR, the seven-class large-event taxonomy — which needs no sorter and no gate. Fisk additionally has `.ns3` LFP, in scope per CLAUDE.md and untouched so far.

### S09 — Rocky continuous re-detection *(the highest-value analysis session)*
Re-detect the 431 `.ns5` at a fixed `k × MAD` threshold and compare against the snippet result. This is what [`ns5_plan.md`](notes/ns5_plan.md) identifies as the top priority, and the sensitivity sweep already showed why: cohort composition moves the anterior trend more than any sorter or gate choice does, and the reason is that the NSP's online threshold changed between eras. Continuous data is the only thing that removes it. Also validates the noise-floor bias on more than the single Nigel session it currently rests on.

### S10 — Rocky implant 2, and the 2024 extension
Index 2024 into implant 1; index 2025 as implant 2 with its own age-zero at 2025-03-26 and its own CMP pair. Resolve the `-MA` variant first. Produces the first within-subject comparison of two implants in the same animal.

### S11 — TDT ingestion, on Picasso
Picasso is the clean test: TDT-only, no Blackrock to fall back on, 6,623 `.sev` across 123 tanks. New IO path (`neo.rawio.TdtRawIO` / SI `read_tdt`), new date extraction — Picasso and Oops tanks carry `YYYY_MM_DD` in the folder name, **Luigi's do not** (`Block-NN` only, so dates must come from the `.tsq` header). Write the SI-literacy note for the reader.

### S12 — Oops and Luigi
Both TDT-era with a Blackrock tail. Luigi's tanks need the header-date path from S11. Luigi is also the narrowest-spread subject and a candidate to seal as closed.

### S13 — Impedance across the cohort
Generalise the existing parser to Oops, Picasso, Nigel and Rocky-first-batch (same format), then Fisk and Rocky-second-batch separately. Blocked on the sweep-ordering answer for per-electrode conclusions; the session-level QC — level shifts, dispersion, open/short fractions, cross-array agreement — is ordering-independent and can run immediately.

### S14 — Cross-subject synthesis
Align every subject on implant age rather than calendar date and compare degradation across seven array-implants (Rocky ×2 implants ×2 arrays, Nigel, Fisk, Oops, Picasso, Luigi). This is the question the whole project exists to answer, and it is the last session because it is the only one that needs all the others.

## 6. Open questions

1. **Can analysis read `L:` directly, or must data be staged to local disk first?** Sets whether S06 emits a copy manifest or just paths. Rocky implant 1 alone is ~500 GiB of `.ns5`.
2. **Rocky 2025 `-MA`** — second array, or second configuration?
3. **Luigi impedance** — genuinely absent, or filed outside the `Monkey\` trees the census walked?
4. **Impedance sweep ordering** — still outstanding, now blocking five subjects rather than one.
5. **Picasso's Plexon `.plx`** is the only sorted reference for a TDT-only subject. Is it trustworthy enough to use as the comparison baseline the way Rocky's OFS output was?

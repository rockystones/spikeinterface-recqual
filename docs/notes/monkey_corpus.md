# The staged Monkey Data drop — what is there and how it is keyed

`D:\Claude Code\Monkey Data`, three subjects, four trees, 126,930 files, 221.9 GiB.
Built by `notebooks/scratch_monkey_inventory.py` into `monkey_inventory.parquet`
(per file) and `monkey_sessions_local.parquet` (per recording).

This supersedes `D:\Claude Code\Rocky`, which was merged in and no longer exists.
Every script that held that path now imports `notebooks/_paths.py`.

## Trees and what distinguishes them

| tree | subject | implant | arrays | keyed by |
|---|---|---|---|---|
| `Nigel` | Nigel | I1 | Anterior, Posterior | filename |
| `Fisk` | Fisk | I1 | SN1498, SN1504 | **directory** |
| `Rocky` | Rocky | I1 | Anterior, Posterior | filename |
| `Rocky New` | Rocky | I2 | Anterior, Posterior | filename |

**Fisk is the exception that breaks naive keying.** Its files carry only
`YYYYMMDD-HHMMSS-NNN`, and its two arrays were recorded *sequentially on the same
day* — 43 shared dates, zero shared timestamps. The array is knowable only from
the directory (`SN1498`/`SN1504`). Key on the folder or the two arrays collapse
into one session and every Fisk date looks recorded twice.

## Three filename grammars

| grammar | shape | files | subjects |
|---|---|---|---|
| long | `Subject_Region_DATE[_Cond[_Headstage]]` | 2,011 | Rocky, Nigel |
| stamp | `YYYYMMDD-HHMMSS-NNN` | 408 | Fisk |
| datafile | `datafileNNNN` | 4 | Nigel terminal |

Within the long grammar everything after the date is optional — 2017–2018 Rocky
files often stop at the date, and the headstage slot sometimes holds an operator
name (`Cui`, `Schwartz`) instead. Dates appear as `MM-DD-YYYY`, `YYYY-MM-DD` and
`YYYYMMDD`, plus a trailing `a`/`b` for a second recording the same day.

Three files carry a 3-digit day with a stray leading zero, one in each
convention: `Rocky_Anterior_2023-08-011` and `Rocky_Anterior_06-013-2019`. Both
are repaired to the 11th and 13th; the NEV header confirms the first
independently.

## Variant suffixes — owner-ruled 2026-08-15

| chain | meaning | Fisk | Nigel | Rocky |
|---|---|---|---|---|
| *(none)* | original, unsorted | 93 | 160 | 477 |
| `-01` | Plexon OFS automatic sort | 145 | 782 | 394 |
| `-02` | manual curation, operator DS | 5 | 74 | 17 |
| `-DS` | manual curation, operator DS | 14 | · | · |
| `-MA` | manual curation, operator Sidd | 126 | 83 | 19 |
| `-MA-01` | Sidd, redone † | · | · | 6 |
| `-MA-02` | Sidd, redone | · | · | 1 |
| `-MA-RE` | Sidd, redone | 23 | · | · |
| `-MADS` | **Sidd sorted, then DS curated on top** | 2 | · | · |
| `-00` | partial OFS pass, superseded by `-01` ‡ | · | 2 | · |

† inferred by analogy with `-MA-02`, not explicitly ruled.
‡ read from the spike packets, not from the name — see below.

Grouping that follows:

```
DS, independent    -02, -DS
Sidd, independent  -MA, -MA-01, -MA-02, -MA-RE
sequential         -MADS   -- excluded: two operators in one file
```

**`-MADS` is not a second opinion.** DS's edits sit on top of Sidd's output, so
the file is evidence about neither operator alone. Both instances are Fisk
2025-02-26, outside the overlap window, so nothing is lost by excluding them.

**`-02` and `-DS` are the same operator in two notations**; any grouping must
accept both. `-01` outnumbers originals because OFS was run repeatedly with
different parameters.

### What `-00` is, read from the packets

Neither the name nor the folder says. Comparing unit-class bytes against the
same recording's other variants does:

| variant | unsorted | assigned | noise | units |
|---|---|---|---|---|
| original | 390,681 | 0 | 0 | 0 |
| `-00` | 363,603 | 26,788 | **290** | 44 |
| `-01` | 145,494 | 149,839 | **95,348** | 201 |

`-00` assigned a fraction of the units and marked essentially **nothing as
noise**. It is an early or aborted pass, superseded by `-01` on both recordings.
Exclude it, or treat it as a distinct parameter setting — not as a curation.

## Sorting never re-detects — 697 of 697 recordings

Every variant of a recording carries **byte-identical spike timestamps**.
Checked on all 697 recordings with more than one variant staged: zero
disagreements. OFS and both operators change the unit-class label only.

This is the single most useful structural fact in the corpus:

- **Comparing two sorts is a labelling comparison on a fixed event set.** No
  spike matching, no tolerance window, no agreement-matrix ambiguity. Operator
  agreement can be computed exactly.
- It does **not** extend to a sorter run on `.ns5`, which re-detects and
  produces its own event set. Those comparisons still need matching.

### Sidd's repeat passes are revisions, not test-retest

Seven Fisk recordings have both `-MA` and a redo. The redo increased the unit
count in **7 of 7** (+10 to +19, median +15) while leaving the noise assignment
**byte-identical in 7 of 7**. That is systematic splitting on reconsideration,
not random variation, so it does not give a symmetric noise floor for the
between-operator comparison — but it does bound how far one operator's output
moves when they look again.

## Sessions

| subject | implant | sessions | original | `-01` | DS | Sidd | ns5 | ccf |
|---|---|---|---|---|---|---|---|---|
| Fisk | I1 | 143 | 90 | 142 | 19 | 124 | 0 | 0 |
| Nigel | I1 | 160 | 160 | 158 | 73 | 83 | 47 | 47 |
| Rocky | I1 | 457 | 457 | 374 | **4** | 0 | 0 | 0 |
| Rocky | I2 | 20 | 20 | 20 | 12 | 19 | 20 | 20 |

A session here is (subject, implant, array, date, run, headstage) — Rocky's
analog and digital recordings of the same day are two sessions, which is what
makes them comparable.

**Rocky I1 has exactly two manually curated dates** — 2022-12-02 and 2023-10-06,
both arrays, operator DS. That is the entire hand-sorted anchor for the cohort
every existing longitudinal conclusion rests on. It supersedes the note in
[`session_state`](session_state.md) that implant 1 had none.

**53 Fisk sessions have `-01`/`-MA` output but no original NEV staged** — all
from 2024-06 onward. The experimenter is adding them (stated 2026-08-15); re-run
`scratch_monkey_inventory.py` once they land.

## One folder the experimenter already set aside

`Rocky New/Sidd Curated/Not applicable/` holds a second `-MA` of
`Rocky_Posterior_2025-05-30` that differs from the one in the parent folder --
same size, different md5. The folder name is the operator's own verdict.

**It reached two of S09's comparisons before this was noticed**, including one
of the 30 inter-operator pairs, because it merely shadowed the good file in a
name-keyed lookup. `scratch_monkey_inventory.py` now marks anything under an
`EXCLUDE_FOLDERS` name with an `excluded` column and every worklist filters on
it. Correcting it moved the operator floor from 0.252 to **0.241** and
`keep_agree` from 0.935 to **0.941** -- small, and now right.

**Three other recordings share a stem and variant with a different file**, all
Nigel and Rocky duplicates across folders:

| recording | folders | same file? |
|---|---|---|
| `Nigel_Posterior_2023-03-17…-02` | `Curated/DS Curated`, `Posterior/sorted` | **different md5** |
| `Nigel_Posterior_2023-01-26…-01` | `Posterior/sorted`, `Original` | identical |
| `Rocky_Posterior_2025-05-30…-02` | `Curated`, `Sidd Curated` | identical |

The first is a genuine ambiguity: two different DS curations of one recording,
neither marked as superseded. Session previews disambiguate by folder rather
than letting one overwrite the other; **which of the two is authoritative is an
open question for the experimenter.**

## Two ready-made comparison sets

**Inter-operator, 30 sessions.** Both operators independently curated the same
recording: Fisk SN1498 9, SN1504 10, Rocky I2 Anterior 6, Posterior 5. **All 30
also have the `-01` automatic sort**, giving a three-way automatic/DS/Sidd
comparison on one input. This is the only place in the corpus where operator
disagreement is measurable directly, and the operators are known to use
different standards. (The count was 29 before `-MA-RE` and `-MA-02` were ruled
as Sidd's own redos and folded into his group.)

Because every variant shares the same event set, agreement here is exact — a
confusion between two labellings of one list of spikes, not a matching problem.

**Analog/digital, 121 slots.** Rocky I1, 60 Anterior and 61 Posterior date-slots
carrying both headstages — the same session recorded twice, analog expected
noisier. No ground truth needed: agreement between the two is an accuracy proxy
and the noise asymmetry makes it graded. See `_MONKEY-PLAN.md` §2.

## The NEV header carries the acquisition clock

The basic header's `TimeOrigin` is a Windows `SYSTEMTIME` — eight `uint16` at
byte offset 28. Readable in **2,423 of 2,423** files without NEO.

It corroborates the filename in 93.8% of cases. **The filename is the date of
record** — owner-ruled 2026-08-15: where the two disagree, the NSP clock was
wrong, not the recording schedule.

- **129 files, `+1` day with the header clock at 00:00–04:00** (2017–2019, 2024).
  Clock error, not a session that ran past midnight.
- **8 recordings disagree some other way.** Nigel 2024-01-16 → header 2024-02-16
  (+31 d) is **provably wrong**: 2024-02-16 is already a separate session. Nigel
  2024-02-02 and 2024-02-09 both shift `+3 d` on both arrays — a clock reset.
  Rocky 2019-07-09 → 2019-02-07 (−152 d), month and day transposed. Rocky
  2020-01-02 → 2020-01-03 16:59.

**The header clock is still usable for ordering *within* a session.** An
analog/digital pair sits ~10 minutes apart, and that spacing is unaffected by a
wrong date — so it tells you which headstage was recorded first.

### The four terminal recordings, dated by the header alone

Nigel's `datafileNNNN` files carry no date in the filename, so the header is the
only source — and it reads **2025-09-25, 01:18–02:07**, inside the window the
clock is wrong in elsewhere. Owner-confirmed 2026-08-15: **Anterior array,
2025-09-25**, so here the header is right. **Nigel's Posterior array recorded no
units that day** — a terminal-session fact worth carrying into any survival
analysis, not an acquisition failure.

### One correction to existing derived data

`units_long.parquet` and everything downstream carry a session dated
**2023-08-01** that is actually **2023-08-11** — the old parser read the
`2023-08-011` typo as the 1st. The NEV header says 2023-08-11 16:22 Friday, and
the 11th fills the only gap in an otherwise weekly series. One of 180 dates,
shifted 10 days; it changes no conclusion but should be fixed on the next
re-run.

## Impedance — two instruments, owner-confirmed

- **Fisk**: `<date>-Lateral-MotorImpedance.txt`, 1 kHz from the Blackrock
  headstage. Same family as the factory automated dump, therefore **indexed by
  `channel_id`** — proved at 1,248/1,248 in [`impedance_sources`](impedance_sources.md).
- **Rocky**: `postimplant/<date>/{Anterior,Posterior}_{A,B,C}{1,2}.txt`,
  full-spectrum EIS from an external potentiostat. Sweep-to-electrode order
  still unverified — see [`impedance_parsing`](impedance_parsing.md).

`Rocky/preimplant/` additionally holds the **implant-1 array mapfiles and factory
workbooks** — `SN 1025-001497.cmp`, `SN 1025-001501.cmp` and their `.xlsm` — plus
pre-implant 1 kHz baselines from 2015-03-26 under `coat_1025-001501/` and
`ctrl_1025-001497/`. The `coat`/`ctrl` split is the coating experimental
variable.

## Plexon OFS algorithm sweep

`Nigel/OFS sorting test2023/` — the same sessions sorted eight ways:
`Scan{EM,Kmean,Valley}-{J3,PSF}` and `TDIST-EM-3D-{J3,PSF}`, with the driving
`.ofb` batch files under `OFS batch/`. 72,475 `.scan` files across the Nigel
tree. This is an existing single-tool parameter sweep to compare a multi-sorter
consensus against.

## Related

[`cohort_plan`](../cohort_plan.md) for the six-subject session plan,
[`analysis_plan`](../analysis_plan.md) for what to run next, [[session_state]] for what is
waiting on the experimenter, [[impedance_sources]] and [[impedance_parsing]] for
the two impedance families, [[channel_mapping]] for the channel/electrode
vocabulary.

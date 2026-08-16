# The staged Monkey Data drop — what is there and how it is keyed

`D:\Claude Code\Monkey Data`, three subjects, four trees, 126,930 files, 221.9 GiB.
Built by `notebooks/scratch_monkey_inventory.py` into `monkey_inventory.parquet`
(per file) and `monkey_sessions_local.parquet` (per recording).

This supersedes `D:\Claude Code\Rocky`, which was merged in and no longer exists.
**`scratch_rocky_inventory.py` still points at the old path and will fail.**

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

## Variant suffixes — the stated convention, and four it does not cover

| chain | meaning | Fisk | Nigel | Rocky |
|---|---|---|---|---|
| *(none)* | original, unsorted | 93 | 160 | 477 |
| `-01` | Plexon OFS automatic sort | 145 | 782 | 394 |
| `-02` | manual curation, operator DS | 5 | 74 | 17 |
| `-DS` | manual curation, operator DS | 14 | · | · |
| `-MA` | manual curation, operator Sidd | 126 | 83 | 19 |
| `-MA-01` | Sidd's curation re-saved by OFS | · | · | 6 |

**Four chains are undeclared and must not be treated as a known label until
ruled on:** `-00` (2, Nigel), `-MA-02` (1, Rocky), `-MA-RE` (23, Fisk),
`-MADS` (2, Fisk). `-MADS` matters most — if it is one operator's file curated
by the other, it is not an independent second opinion and cannot go in the
inter-operator agreement set.

**`-02` and `-DS` are the same operator in two notations**, so any grouping must
accept both. `-01` outnumbers originals because OFS was run repeatedly with
different parameters.

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
from 2024-06 onward. The originals exist on the source volumes.

## Two ready-made comparison sets

**Inter-operator, 29 sessions.** Both operators curated the same recording:
Fisk SN1498 9, SN1504 9, Rocky I2 Anterior 6, Posterior 5. 28 of the 29 also
have the `-01` automatic sort, giving a three-way automatic/DS/Sidd comparison
on one input. This is the only place in the corpus where operator disagreement
is measurable directly, and the operators are known to use different standards.

**Analog/digital, 121 slots.** Rocky I1, 60 Anterior and 61 Posterior date-slots
carrying both headstages — the same session recorded twice, analog expected
noisier. No ground truth needed: agreement between the two is an accuracy proxy
and the noise asymmetry makes it graded. See `_MONKEY-PLAN.md` §2.

## The NEV header carries the acquisition clock

The basic header's `TimeOrigin` is a Windows `SYSTEMTIME` — eight `uint16` at
byte offset 28. Readable in **2,423 of 2,423** files without NEO.

It corroborates the filename in 93.8% of cases, and **the filename is kept as the
session key**, because the header has two demonstrated failure modes:

- **129 files, `+1` day with the header clock at 00:00–04:00.** Sessions that
  started in the evening and crossed midnight (2017–2019, 2024). Benign — both
  headstages of a pair shift together, so pairing survives. The filename records
  the experimental day, which is the right longitudinal axis.
- **8 recordings where the header is otherwise wrong or unexplained.** Nigel
  2024-01-16 → header 2024-02-16 (+31 d) is **provably wrong**: 2024-02-16 is
  already a separate session. Nigel 2024-02-02 and 2024-02-09 both shift `+3 d`
  on both arrays, consistent with an NSP clock reset. Rocky 2019-07-09 → header
  2019-02-07 (−152 d). Rocky 2020-01-02 → header 2020-01-03 16:59, not a
  midnight crossing.

Use the header to **date the 4 Nigel terminal recordings**, which carry no date
in the filename at all: all four are 2025-09-25, 01:18–02:07.

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

[[cohort_plan]] for the six-subject session plan, [[session_state]] for what is
waiting on the experimenter, [[impedance_sources]] and [[impedance_parsing]] for
the two impedance families, [[channel_mapping]] for the channel/electrode
vocabulary.

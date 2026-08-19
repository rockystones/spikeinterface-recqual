# Figure coverage across subjects

Rocky has 50 analysis figures in seven families plus 914 session previews. No
other subject has more than five. This note records what each subject has been
analysed *for*, which Rocky figure families their existing data already
supports, and which are blocked and why.

## The Rocky benchmark

| family | n | content | script |
|---|---|---|---|
| top-level `05`–`15` | 11 | yield/SNR over time, resort vs OFS, impedance vs yield, gate audit, impedance QC, spatial yield maps, bank breakdown, metric trends, method agreement, curation comparison | `scratch_rocky_longitudinal.py`, `_spatial.py`, `_agreement.py`, `_curation.py`, `_impedance_qc.py` |
| `deepdive/` T1–T3 | 9 | raw traces + per-channel panels at early / middle / late timepoints | `scratch_rocky_deepdive.py` |
| `longitudinal/` L1–L5 | 5 | sorted metrics, free metrics, amplitude tail, amplitude distribution, layer agreement | `scratch_rocky_longitudinal_metrics.py` |
| `evidence/` E1–E7 | 7 | methodological evidence panels (snippet constraint, gate decision, noise event, containment, UnitRefine saturation, segment bug, cross-channel artifacts) | `scratch_rocky_evidence.py`, `_artifact.py` |
| `giants/` G1–G5 | 5 | giant-artifact taxonomy, gallery, neighbour pair, persistent site, where/when | `scratch_rocky_giants.py` |
| `sensitivity/` S1–S7 | 7 | gate sweep, method sweep, artifact effect, cohort sweep, each with its rho panel | `scratch_rocky_sensitivity.py` |
| `cohort/` C1–C3 | 6 | yield, metrics, acquisition screen, per implant | `scratch_cohort_figures.py` |

`scratch_cohort_figures.py` is **already generic** — it loops over every
subject present in `cohort_sessions.parquet`. Everything else is Rocky-shaped.

## What each other subject has

| subject | format | sessions / blocks | derived tables | figures |
|---|---|---|---|---|
| **Nigel** | Blackrock `.nev` (1101), `.ns5` (47) | 157 cohort sessions, 2 arrays | cohort layer, 4-sorter results on ~45 sessions, noise validation | 3 cohort, 2 validation (N1/N2), 479 previews |
| **Fisk** | Blackrock `.nev` (408), `.ns6` (133), `.ns3` (149) | 142 cohort / 140 session rows, 2 arrays | 12,747 sorted units, impedance over 41 dates on both arrays, 14 operator pairs, 140 snippet-vs-continuous layer rows | 3 cohort, 408 previews |
| **Chase** | Plexon `.plx` only (20) | 20 sessions, 2010–2015 | 920 units, session-level free + sorted metrics | **none** |
| **Oops** | TDT | 85 blocks | 145 free-metric rows (all ok), offline sort units, 28 trend rows | 151 previews |
| **Picasso** | TDT | 92 blocks | 106 free-metric rows (all ok), offline sort units, 28 trend rows | 110 previews |
| **Luigi** | TDT | 193 blocks | **24 attempted, 5 ok** in the free layer (19 MemoryError), 18 re-sort rows | 281 of 319 previews |

Cross-subject tables with **no figures at all**: `equipment/tdt_vs_blackrock`
(457 rows — the headstage and TDT-vs-Blackrock comparison), `floor/*` (the
measurement-floor pairs), `fisk/impedance_quality`, `fisk/operator_pairs`,
`fisk/layer_compare`. Those findings currently exist only as prose in notes.

## Gap matrix

`+` runnable from data already on disk · `~` needs a compute pass first ·
`x` blocked, reason below.

| Rocky family | Nigel | Fisk | Chase | Oops | Picasso | Luigi |
|---|---|---|---|---|---|---|
| cohort C1–C3 | done | done | `~`¹ | `~`¹ | `~`¹ | `~`¹ |
| longitudinal L1/L2 (metric trends) | `+` | `+` | `+` | `+` | `+` | `x`² |
| L3/L4 (amplitude tail, distribution) | `+` | `+` | `+` | `+` | `+` | `x`² |
| L5 (layer agreement) | `~`³ | `+` | `x`⁴ | `~`³ | `~`³ | `x`² |
| sensitivity S1/S2 (gate sweep) | `+` | `+` | `+` | `+` | `+` | `+` |
| `14` method agreement | `+` | `~`⁵ | `x`⁵ | `~`⁵ | `~`⁵ | `~`⁵ |
| `08`/`10` impedance | `x`⁶ | `+` | `x`⁶ | `x`⁶ | `x`⁶ | `x`⁶ |
| `11`/`12`/`13` spatial maps | `+` | `+` | `x`⁷ | `x`⁸ | `x`⁸ | `x`⁸ |
| deepdive T1–T3 | `~`⁹ | `~`⁹ | `x`⁴ | `~`⁹ | `~`⁹ | `~`⁹ |
| giants G1–G5 | `~`¹⁰ | `~`¹⁰ | `~`¹⁰ | `~`¹⁰ | `~`¹⁰ | `~`¹⁰ |
| `15` curation comparison | `~`¹¹ | `~`¹¹ | `~`¹¹ | `~`¹¹ | `~`¹¹ | `~`¹¹ |
| evidence E1–E7 | — | — | — | — | — | — |

1. `cohort_sessions.parquet` holds only Fisk, Nigel and Rocky. Adding Chase and
   the TDT subjects to it makes C1–C3 fall out for free, since the script is
   already subject-generic. This is the single cheapest lever in the table.
2. **Luigi's sorting-free layer never ran.** 24 blocks of 193 attempted, 5
   succeeded; the rest died on `MemoryError` reading the tsq index (up to
   897 MiB for one event table). Needs a chunked reader before any Luigi
   longitudinal figure is meaningful.
3. Layer agreement compares the snippet layer against a continuous layer of the
   same recordings. Nigel has 47 `.ns5` against 1101 `.nev`; the TDT subjects
   have `Raw` alongside `eNe`. Both need the continuous free layer run on the
   matched subset first.
4. **Chase is Plexon snippet-only** — 20 `.plx`, no continuous stream anywhere
   in the tree. Raw-trace deepdives and snippet-vs-continuous agreement are
   impossible, not merely unrun.
5. Multi-sorter results exist for Nigel and Rocky only (110 sessions, 380 jobs,
   310 ok: MS5 104/104, TDC2 103/104, SC2 101/104, **KS4 2/68**). Fisk `.ns6`
   has not been sorted; the TDT re-sort covers 40 block-arrays. Chase has no
   continuous data to sort at all.
6. Impedance grids exist for the Fisk serials (`1025-0014xx`) and the Rocky
   serials (`1025-004xxx`) only. Picasso's `1499`/`1503`, Oops's `1391`/`1393`,
   Luigi's, Nigel's and Chase's arrays have none.
7. Chase's array identity and geometry are not established.
8. **No verified TDT channel map.** Inference from Rocky's same-day Blackrock
   scored 0.021 against a calibration ceiling of 0.193–0.224
   ([[tdt_channel_map]]). Any spatial figure drawn on an unverified map would
   be a picture of the map, not of the array. Blocked pending the owner's
   confirmation of a map.
9. Needs a raw-trace pass at three timepoints. Cheap per subject (three
   sessions each) and the highest information-per-minute item here.
10. Giant-artifact extraction is an event-level pass that only Rocky has had.
    The snippet data to run it on exists for every subject including Chase.
11. Needs `SortingAnalyzer` + UnitRefine per session; the most expensive row.

## Suggested order

1. **Extend `cohort_sessions` to Chase, Oops, Picasso** → C1–C3 for three more
   subjects at near-zero cost.
2. **Fisk impedance + operator + layer figures** — the tables are built and the
   findings are currently text-only.
3. **Nigel method agreement (`14`)** — the four-sorter results are sitting in
   `ns5/shards/` unplotted.
4. **Equipment-comparison figures for Rocky** — 457 rows, no figure family.
5. **Deepdive T1–T3 per subject** where continuous data exists.
6. **Fix Luigi's free layer**, then everything in rows 1–3 applies to Luigi too.

## Related

[[tdt_corpus]] for the TDT block inventory, [[tdt_channel_map]] for the map
blocker, [[fisk_impedance]] and [[fisk_operator_floor]] for the unplotted Fisk
results, [[chase_corpus]] for the Plexon-only constraint,
[[equipment_comparison]] for the unplotted headstage work.

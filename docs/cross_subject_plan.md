# Cross-subject plan: six monkeys, three acquisition regimes

Session plan for extending `recqual` from one subject to six. Derived from the volume census (`_monkey-ephys.csv`, 979,044 rows over 22 volumes; 249,877 distinct in-scope files after de-duplicating on name+size).

The census was written for storage triage. This is the same data re-cut for the only question that matters here: **what can actually be run, on which subject, from which drive.**

## 1. What the census establishes

| subject | era | acquisition | dated sessions | raw coverage | impedance | probe map | read from |
|---|---|---|---|---|---|---|---|
| **Rocky** | 2017–2025 | TDT 166 blocks + Blackrock ns5/nev | 77 TDT (2017-09-01→2019-01-17), 208 Blackrock (2017-09-21→2025) | **175 / 208** nev dates have ns5 | 42 legacy txt + chronic set | 001501, 001497; **004377, 004419 (2025 implant)** | `L: MonkeyEphys` 95 % |
| **Oops** | 2015–2017 | TDT 96 blocks + 13 ns5/nev | 82 TDT (2015-02-03→2017-02-15); Blackrock **undated** | TDT complete | 25 legacy txt + 738 `.nox` | 001391, 001393 | `L:` 100 % |
| **Luigi** | 2015–2016+ | TDT 200 blocks + 178 ns5/nev | **46 of 200** TDT dated; Blackrock **undated** | yes | **none** | **none** | `L:` 100 % |
| **Picasso** | 2015–2018 | TDT only, 123 blocks | 123 / 123 (2015-11-09→2018-02-15) | TDT complete | 31 legacy txt | **none** | `L:` 74 % + `E: MED` |
| **Nigel** | 2023–2024 | Blackrock ns5 + nev | 86 (2023-01-24→2024-12-16) | **complete** | 24 chronic txt + fig/png | 001473, 001496 | `F: BackupHDD` / `E: Dani NTE` — **not on L:** |
| **Fisk** | 2023–2025 | Blackrock **ns6 + ns3** + nev | 72 (2023-06-05→2025-05-07) | 66 / 72 | 133 txt + 3-min ns3/nev | 001498 Lateral, 001504 Medial | `H: BackupHDD` / OneDrive |

### Three regimes, not two

The project currently handles one of these.

1. **Blackrock continuous** — Rocky 2018+, Nigel, Luigi, Oops. `read_blackrock` already works; only re-detection and the sorter pool are missing.
2. **Blackrock ns6 + ns3** — Fisk only. `.ns6` is the broadband stream, **not `.ns5`**, which contradicts CLAUDE.md's data conventions as written. `.ns3` gives this project its first real LFP.
3. **TDT** — Picasso, Luigi, Oops, early Rocky. `.sev/.tev/.tsq`. No reader in the project at all; needs `read_tdt`.

Blackrock snippet-only (Rocky 2017) stays as the fourth case and is already solved.

### Four dating conventions, two of which are unsolvable from filenames

- Path-dated: Rocky Blackrock (`MM-DD-YYYY` and `YYYY-MM-DD`), Nigel (`YYYY-MM-DD`), Fisk (`YYYYMMDD-HHMMSS`), TDT tanks (`YYYY_MM_DD`).
- **Header-dated only**: Luigi and Oops Blackrock are `datafile063.ns5` — no subject, no date, no array. 356 Luigi files and 13 Oops files. Dates must come from the NSx header `TimeOrigin`.
- **Header-dated only**: 148 of Luigi's 200 TDT blocks are `Luigi_Block-13` with no date anywhere in the path. The `.tsq` header carries a timestamp.

One malformed convention to carry: Rocky's TDT tanks include `Rocky_2017_010_09` and `Rocky_2017_010_02` — a zero-padded month that breaks a naive `\d{2}` match.

### No single volume holds the estate

`L:` covers Rocky, Oops, Luigi and Picasso. It holds **none** of Nigel and none of Fisk. Nigel is on `F: BackupHDD` / `E: Dani NTE`; Fisk is on `H: BackupHDD` / OneDrive. **Any plan that assumes one mounted drive is wrong** — the work splits into an L: block and a non-L: block, and that constraint drives the session order below as much as the science does.

### The ns5 gap is exactly where it hurts

Of Rocky's 208 Blackrock dates, 33 have no `.ns5` — and **30 of those are 2017**:

| year | nev dates | ns5 dates | nev without ns5 |
|---|---|---|---|
| 2017 | 34 | 4 | **30** |
| 2018 | 52 | 49 | 3 |
| 2019–2025 | 122 | 122 | 0 |

[`ns5_plan.md`](notes/ns5_plan.md) names fixed-threshold re-detection as the single highest-value job, because the NSP's online threshold changed between eras and that confound dominates the anterior trend. **It cannot fix 2017**, which is the era where the confound is worst — 2017 sits 2.3× above 2018 in noise and amplitude with identical digitisation (see [`longitudinal_metrics.md`](notes/longitudinal_metrics.md)). Re-detection will make 2018→2025 mutually comparable and leave 2017 a separate era on the strength of 4 sessions. That is a real limit on the payoff and should be known before the work starts, not after.

### Impedance: three formats, one missing subject

- **Legacy** `PC_data_active\monkey\impedance\rawdata\data\<subject>\<stage>\<YYYYMMDD>\Anterior.txt` — Rocky (42), Oops (25), Picasso (31). One file per array per date, **not** the six-file `{A,B,C}{1,2}` split currently parsed.
- **Chronic** `Chronic Impedance\Second batch\<subject>\<MM-DD-YYYY>\<Array>_<Bank><Half>.txt` — Nigel (24) and Rocky's current set. This is the format [`impedance_parsing.md`](notes/impedance_parsing.md) already handles.
- **Fisk** `<YYYYMMDD>-<Array>-MotorImpedance.txt` (133), plus 3-minute `.ns3`/`.nev` recordings filed under `Mapping and Impedance`.
- **Luigi has no impedance files at all.**

Two legacy MATLAB structures sit alongside: `impedance_cellstruct_fix.mat` and `impstructure_cell.mat`, with a sibling `impedance\maps\rocky\SN 1025-001501.cmp`. **These are the strongest available lead on the electrode-ordering question** that currently blocks every per-electrode impedance conclusion.

## 2. Session plan

Eight sessions. Each is one task with its own `docs/session_plans/sessionNN_*.md`, per CLAUDE.md.

### S06 — Cross-subject inventory and staging manifest
**Do first; everything else depends on it.** Generalise `scratch_rocky_inventory.py` to all six subjects: per-subject date resolution (four path conventions plus **header timestamps** for the 356 Luigi / 13 Oops `datafileNNN` files and 148 undated Luigi tanks), an array-serial registry mapping serial → subject → hemisphere → implant date, and a volume staging manifest.
Deliverables: `subject_index.parquet`, `docs/notes/subject_registry.md`.
Needs: L: mounted; F:/E: for Nigel; H:/OneDrive for Fisk. Header reads only, so I/O is small.
Risk: if `datafileNNN` headers turn out to lack a usable `TimeOrigin`, Luigi and Oops Blackrock have no longitudinal axis at all and drop to session-level comparison only.

### S07 — Legacy impedance and the electrode-ordering question
Parse the legacy `PC_data_active` tree (Rocky, Oops, Picasso) and read `impedance_cellstruct_fix.mat` / `impstructure_cell.mat` against `impedance\maps\rocky\*.cmp`. The goal is to settle sweep → electrode ordering, which two empirical attempts already failed to establish.
Why this early: cheap, needs no new reader, and unblocks per-electrode impedance for three subjects at once. If it succeeds, every impedance conclusion in the project becomes publishable rather than provisional.
Deliverable: `impedance_long.parquet` extended to three subjects; ordering resolved or formally declared unresolvable.

### S08 — Nigel: build the continuous pipeline
Nigel is the right place to build it: 86 dates, **ns5 for every one**, filename convention already handled, and it is the only cohort where the snippet noise estimate has been validated against continuous data.
Build fixed-threshold re-detection and run the sorter pool for the first time in this project. Because Nigel has both ns5 and nev per session, re-detected and NSP-detected can be compared directly — that comparison *is* the measurement of threshold drift.
Deliverable: the continuous path, validated; `docs/notes/fixed_threshold_detection.md`.

### S09 — Fisk: ns6, LFP, and the 3-min protocol
Smallest modern subject (714 acquisition files), two arrays, `.cmp` present, consistent naming. Adds `.ns6` broadband and the project's first `.ns3` LFP layer, which CLAUDE.md has scoped from the start and never delivered.
Note the protocol split: 122 `3Min` sessions against 10 `RAW`. The 3-min series is the longitudinal baseline; the RAW sessions are a different thing and must not be pooled with it.
Deliverable: Fisk longitudinal, first LFP metrics.

### S10 — Rocky: continuous re-analysis
Apply S08's method to 175 of 208 dates. Re-derive every headline metric and compare against the snippet result; the difference is the threshold drift. Carry the 2017 gap explicitly.
Deliverable: the ns5_plan job, closed.

### S11 — Picasso: the TDT reader
TDT-only, 123 blocks, 123/123 dated, 2015-11 → 2018-02. Clean introduction of `read_tdt` with no Blackrock confound. **No `.cmp` and no array serial anywhere in the census** — probe geometry must be resolved before any spatial claim.
Deliverable: TDT path validated; `docs/notes/tdt_loading.md`.

### S12 — Oops and Luigi
Hardest metadata, so last among the subject sessions. Both mix TDT and Blackrock; both have `datafileNNN` Blackrock; Luigi additionally has no impedance, no probe map and 148 undated tanks. Scope depends on what S06 recovers from headers.

### S13 — Cross-subject longitudinal synthesis
The actual goal: array performance over implant lifetime, across six subjects, two array vendors' eras and three acquisition systems. Only meaningful once each subject has a validated per-session table.
Carry the sensitivity discipline from [`longitudinal_metrics.md`](notes/longitudinal_metrics.md): quote sweep ranges, not point estimates, and never compare unit counts across acquisition systems — only trends.

## 3. What is reusable as-is

The snippet-era work is not thrown away. Regime-independent and already validated: the seven-class large-event taxonomy, the CMP parser and adjacency test, segment selection, the `spike_count()` workaround, the noise-floor bias characterisation, the gate, and the whole sorting-free metric layer. Every one of those applies unchanged to a continuous cohort.

## 4. Open questions — these change the plan

1. **Is the 2025 Rocky implant in scope?** Serials 004377 / 004419 under `Rocky Right Hemisphere Implant 2025-03-26`, with 10 Blackrock dates in 2025. Earlier instruction was to ignore 2025 files; the census now shows they are a **second implant**, not stray data. As a fresh implant on a subject with six years of prior history it is arguably the most valuable longitudinal series in the estate.
2. **How deep does Luigi go?** No impedance, no probe map, no serial, 148 of 200 tanks undated. Full depth may not be reachable.
3. **What probe do Picasso and Luigi carry?** Neither has a `.cmp` or a `1025-` serial anywhere in the census. Utah is assumed but unevidenced, and spatial analysis needs it.
4. **Nigel's third serial.** `1025-002456` appears 60 times against 001473 (8) and 001496 (6). Is it a third array, a replacement, or another subject's file filed under Nigel?
5. **Which volumes can be mounted at once?** If L:, F:/E: and H:/OneDrive cannot be online together, S08/S09 (non-L:) and S10/S11/S12 (L:) should be batched into separate sittings.

## 5. Related

[`roadmap.md`](roadmap.md) for phase structure, [`ns5_plan.md`](notes/ns5_plan.md) for what continuous data unlocks, [`longitudinal_metrics.md`](notes/longitudinal_metrics.md) for the analysis discipline to carry forward, [`impedance_parsing.md`](notes/impedance_parsing.md) for the format already handled, [`session_state.md`](notes/session_state.md) for outstanding blockers.

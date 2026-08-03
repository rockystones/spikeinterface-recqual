# Project roadmap

Cross-phase roadmap and session sequence for `recqual`. Synthesizes phase goals, sub-phases, session plans, and phase-boundary criteria. Authoritative for "what session are we on" and "what comes next." Per-phase detail expands into `phase_plans/phaseN_*.md` as each phase begins; per-session detail lives in `session_plans/sessionNN_*.md`.

## Project framing

SpikeInterface-based pipeline for longitudinal recording quality assessment on Blackrock / Ripple data from Utah arrays and NeuroNexus probes. Primary scientific question: which objective metrics reliably track recording quality over time. Engineering goal: a pipeline a new student can run end to end on their data, with outputs that integrate cleanly into a MATLAB post-processing layer.

## Phase overview

| Phase | Scope | Probes | Sorter pool | Output |
|---|---|---|---|---|
| 1 | Single-sorter longitudinal baseline | Utah 96ch | MountainSort5 | Demo session metrics + 60-session longitudinal trends + Plexon comparison |
| 2 | Multi-sorter consensus | Utah 96ch | + Tridesclous2, Kilosort4 | Agreement matrices as longitudinal metric |
| 3 | Curation methods | Utah 96ch | (same pool) + UnitRefine, Bombcell | Curated unit counts and label distributions |
| 4 | Full cohort, second probe type | Utah + NeuroNexus 16ch linear | (same) | Cross-probe validation |

Future phases (deferred, schema-compatible): impedance integration, endpoint histology registration, in vivo imaging registration.

## Phase progression discipline

Three rules that apply at every phase boundary:

1. **Do not scale prematurely.** Within each phase, progression is "one file, then a few, then the full cohort," not "one file to full cohort." Phase 1 demonstrates this most explicitly with sub-phases 1a to 1d.
2. **Each phase ends with three concrete deliverables.** A `phase_plans/phaseN_summary.md` synthesizing the session logs, a refactored tutorial notebook for the phase, and a git tag (`phase1-baseline`, `phase2-multisorter`, etc.). The tag is the rollback anchor and the natural release point for collaboration.
3. **Write the validation spec before the validation work.** Phase 1 in particular has open-ended "extensive validation" risk. Each phase has a `phase_plans/phaseN_validation_spec.md` written before the validation session, naming specific metrics, agreement thresholds, and stop conditions. Without this, validation sessions expand to fill all available time.

## Phase 1: Single-sorter baseline

**Goal.** Establish that one sorter (MountainSort5) produces stable, comparable-to-Plexon results across a 60-session longitudinal Utah cohort, with all metric layers (threshold-crossing, per-sorter quality, Plexon comparison) computed and inspectable.

**Sorter choice.** MountainSort5. Rationale: MountainSort4 was top performer on sparse / tetrode geometries in SpikeForest (Magland et al., eLife 2020); MS5 is the same lab's rewrite with ISO-SPLIT clustering. The SpikeForest benchmarks have not been re-run on MS5 at scale, which is acceptable because Phase 1 *is* the local benchmark against Plexon on the actual hardware.

**Success criteria.** Pipeline runs end to end on 60 sessions. Threshold-crossing metrics, SI quality metrics, and Plexon comparison produced for each session and stored as long-format Parquet plus JSON sidecars. Plexon comparison shows interpretable agreement structure (not necessarily perfect agreement; Plexon is reference, not ground truth). Validation spec deliverables satisfied per `phase_plans/phase1_validation_spec.md`.

**Sub-phases.**

| Sub-phase | Files | Sessions | Goal |
|---|---|---|---|
| 1a | 1 (demo) | S1 to S6 | Build modules end to end, all metrics on demo session |
| 1b | 3 to 5 | S7 | Validate multi-file orchestration and longitudinal aggregation |
| 1c | 60 | S8 | Scale: caching, runtime budget, error recovery, parallelism |
| 1d | 60 | S9 | Validation report against Plexon, refactor tutorial, Phase 1 sign-off |

**Session sequence.**

| Session | Sub-phase | Goal |
|---|---|---|
| S1 | (pre-1a) | Load demo, attach Utah-96 probe, read Plexon nev as BaseSorting |
| S2 | (pre-1a) | Validation figures: channel mapping, units per electrode, per-unit spatial templates |
| S3 | 1a | Threshold-crossing module, `ElectrodeMetadata` dataclass, first synthetic test, first exploration notebook |
| S4 | 1a | MountainSort5 wrapper, run on demo, SortingAnalyzer cached |
| S5 | 1a | SI quality metrics on demo SortingAnalyzer, output schema (Parquet + JSON) |
| S6 | 1a | Plexon comparison via `compare_sorter_to_ground_truth`, agreement report on demo |
| S7 | 1b | Multi-file orchestration on 3 to 5 sessions, longitudinal aggregation |
| S8 | 1c | Scale to 60 sessions, caching and error recovery |
| S9 | 1d | Phase 1 validation report, tutorial refactor, git tag `phase1-baseline` |

**Pre-session 6 task.** Confirm whether Plexon-sorted data exists for all 60 sessions or only a subset. This determines whether Plexon comparison is the longitudinal validation directly or operates on a sub-cohort.

## Phase 2: Multi-sorter consensus

**Goal.** Add two algorithmically independent sorters (Tridesclous2, Kilosort4) and characterize their agreement structure as a longitudinal metric in its own right. Single-sorter output is never the primary result going forward.

**Success criteria.** All three sorters (MS5, TDC2, KS4) plus Plexon run on the 60-session cohort. Pairwise and three-way agreement matrices computed per session. Agreement-over-time curves reported as the consensus longitudinal metric, with per-channel and per-region breakdowns. KS4 over-splitting characterized (expected, per Pachitariu et al. 2024 and CLAUDE.md gotchas).

**Session sequence.**

| Session | Goal |
|---|---|
| S10 | Tridesclous2 wrapper, run on demo, side-by-side with MS5 |
| S11 | Kilosort4 wrapper with `do_correction=False`, run on demo |
| S12 | Multi-sorter orchestration: parallel sorter runs per session, error handling |
| S13 | Agreement matrices: `compare_multiple_sorters`, per-session and longitudinal aggregation |
| S14 | Re-run on 60-session cohort with all sorters |
| S15 | Phase 2 validation report, tutorial update, git tag `phase2-multisorter` |

## Phase 3: Curation methods

**Goal.** Apply automated curation (UnitRefine, Bombcell) to each sorter's output and measure how curation affects unit counts, agreement structure, and longitudinal trends.

**Success criteria.** UnitRefine pretrained classifiers run on all SortingAnalyzers from Phase 2 (Utah-array-validated per Jain et al. 2025). Bombcell run with retuned thresholds appropriate for sparse arrays; default Neuropixels thresholds explicitly documented as inappropriate. Curation label distributions compared across sorters and across sessions. Phase 3 ends with a clear statement of which curation pipeline goes into the default.

**Session sequence.**

| Session | Goal |
|---|---|
| S16 | UnitRefine integration: pretrained classifier labels on all Phase 2 SortingAnalyzers |
| S17 | Bombcell with retuned thresholds for sparse arrays |
| S18 | Curation impact analysis, longitudinal effect on agreement structure, Phase 3 report, git tag `phase3-curation` |

## Phase 4: Full cohort and 16ch NeuroNexus

**Goal.** Run the full Phase 3 pipeline on the complete Utah array longitudinal dataset (not just the 60-session subset) and add support for the 16-channel single-shank NeuroNexus linear probe.

**Success criteria.** Full Utah dataset processed end to end with stable runtimes and caching. 16ch NeuroNexus support added via probeinterface geometry and channel-mapping verification (per CLAUDE.md probe inventory). Cross-probe consistency check: do the threshold-crossing metrics and unit counts behave similarly on the linear probe to what was established on Utah? Phase 4 closes the single-modality scope of the project.

**Session sequence.**

| Session | Goal |
|---|---|
| S19 | Full Utah cohort run (beyond the 60-session subset) |
| S20 | 16ch NeuroNexus probe support: geometry, channel mapping, IO verification |
| S21 | Validation on NeuroNexus subset using Plexon comparison if available, threshold-crossing sanity checks if not |
| S22 | Cross-probe consistency report, full pipeline tutorial, git tag `phase4-multi-probe` |

## Deferred phases

Schema is required to accept these without retrofit. The `ElectrodeMetadata` dataclass already includes the optional fields (`impedance`, `histology_refs`, `imaging_refs`, `position_anatomical`).

- **Impedance integration.** Per-electrode impedance across sessions, joined to quality metrics by `(probe_id, channel_id)`. First multimodal modality to integrate; likely Phase 5.
- **Endpoint histology.** Spatial registration of post-experiment histology to electrode positions. Lower priority; requires registration tooling.
- **Longitudinal in vivo imaging.** Spatial registration of imaging to electrode positions. Lowest priority; integration approach TBD.

## Cross-cutting decisions captured elsewhere

The roadmap references these but does not duplicate them. Source documents are authoritative.

- **Sorter pool details and exclusions:** `CLAUDE.md` "Sorter policy" section.
- **Segment handling (5 s minimum):** `docs/notes/segment_handling.md`.
- **Testing policy (three tiers):** `docs/notes/testing_policy.md`.
- **Output forms for inspection (long-format DataFrames, NumPy arrays):** `CLAUDE.md` "Output forms" addition.
- **MATLAB interop conventions (no pickle, NPY/NPZ/JSON/HDF5):** `CLAUDE.md` "MATLAB compatibility" section.
- **Multimodal schema (`ElectrodeMetadata`):** `CLAUDE.md` "Multimodal forward compatibility" section.

## Notebook strategy across phases

Each phase maintains a `notebooks/exploration/` tree mirroring the pipeline structure: one notebook per module, used for interactive inspection and variable-explorer-driven development. Exploration notebooks are working space, not deliverables, and contain only light annotation (purpose and key findings).

At each phase boundary, the accumulated exploration content is refactored into a clean `notebooks/tutorial/phaseN_tutorial.ipynb`. This is the deliverable, written when the API is stable. The exploration notebooks may then be archived or phased out.

Discipline: do not write tutorial-quality documentation inside exploration notebooks during active development. The API moves under it. Tutorials are written at phase boundaries against stable code.

## Current state pointer

Update this section at the end of each session.

- **Last completed session:** S3 (threshold-crossing baseline, Layer 1). S1 (load demo, Utah-96 probe attach, Plexon nev as BaseSorting) and S2 (validation figures, cached SortingAnalyzer) complete.
- **Current sub-phase:** 1a (single-session module build), partially complete — see divergence below.
- **Next session:** S4 is currently pre-empted by the Rocky snippet cohort (separate branch, see below). Returning to Phase 1 means either S4 (MountainSort5 wrapper on the Nigel demo) or closing the S3 divergence first.
- **Open items for user:** confirm whether Plexon-sorted data exists for all 60 sessions or a subset (decision needed before S6); confirm acquisition system on `nigel_2023-03-17` data (Blackrock NSP vs Ripple, affects pause-resume gotcha interpretation); cross-check 217 unit count from S1 against Plexon Offline Sorter UI.
- **Known deferred:** Phase 1 validation spec to be written before S7.

### S3 divergence from plan

The roadmap specified S3 as "threshold-crossing module + `ElectrodeMetadata` dataclass + first synthetic test + first exploration notebook." What actually landed was the threshold-crossing metric **scratch-only** in `notebooks/scratch_threshold_crossing_nigel_2023-03-17.py`, with three items explicitly deferred:

- No promotion to `src/recqual/quality/` — the API was still moving.
- No `ElectrodeMetadata` dataclass.
- No Tier 1 synthetic test (`docs/notes/testing_policy.md` requires one on promotion to `src/`, and nothing was promoted).

Sub-phase 1a is therefore not closed. The deferred items are still owed before Phase 1 can be signed off. S3's actual results (MAD/SD noise floor, crossing rates at k=3/4/5, 96/96 Tier 2 invariant, Spearman rho +0.42/+0.37/+0.38 against curated unit counts) are recorded in `session_plans/session03_threshold_crossing.md`.

### Rocky cohort — a separate branch, not Phase 1

The Rocky dataset (`D:\Claude Code\Rocky`, 886 NEV, 2017-09-21 to 2023-10-06, anterior + posterior Utah-96) **cannot run through the Phase 1 pipeline as specified**. Phase 1 presumes continuous broadband and MountainSort5; Rocky is **snippet-only** — pre-detected `(n, 1, 30)` waveform clips in NEV, with no `.ns5` anywhere in the cohort. MS5, Kilosort4, Tridesclous2 and SpykingCircus2 all require continuous traces and are unusable on it.

Rocky is handled as a parallel track using per-electrode snippet clustering (ISO-SPLIT on PCA features, with an explicit noise-rejection gate), tracked in `session_plans/session04_rocky_resort.md` and `notes/snippet_sorting.md`. It does not advance Phase 1 sub-phases and does not satisfy Phase 1 success criteria. Findings that generalize — particularly noise-gate thresholds and the anterior-vs-posterior longitudinal framing — should feed back into Phase 2 planning.

## When to update this file

- After each session completes: update "Current state pointer" only.
- At each phase boundary: expand the phase summary into `phase_plans/phaseN_summary.md`, then refresh this file's per-phase sections if the experience suggested changes for downstream phases.
- When a major scope decision changes: update the affected phase section and note the decision in the current state pointer.

Do not edit historical session sequences after the fact. If a session diverged from plan, capture the divergence in that session's `session_plans/` outcome section, not by retroactively rewriting the roadmap.

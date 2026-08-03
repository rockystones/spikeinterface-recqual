# Merging spike sorting projects across accounts

*Exported 2026-08-03T03:55:26.928Z*  
*URL: https://claude.ai/chat/12f7bccb-dbd8-4241-bf89-eac5ac940a50*  
*Mode: active • messages: 12 of 12 in tree*

---

## 🧑 Human

*2026-05-23T19:41:22.956666Z*

I am thinking of merging this Claude project with another highly overlapped project. In this one, I tried to extend from legacy MATLAB and add features like spike interface because I do not have access to Claude code in this account. In the other project, I am focusing on using Claude code to develop spike sorting pipeline using the other account where I have access to Claude code. I have started pilot sessions and have some initial steps (outline development phase, configure CLAUDE.md instruction, scratch code, deep research report to support the development.) The two projects have the same ultimate goal for longitudinal recording quality analysis. The legacy code from this project can also help provide context to guide the new project. I have the new project files handy for upload. I am thinking of primarily using this project (no claude code access, Enterprise subscription) to do session planning, research, general communication with Claude. And then let the other account to be primarily for Claude code execution (Pro subscription). Unless you think Claude project by itself is enough to do the development, it would not be necessary to use the other account. What do you suggest?

---

## 🤖 Claude

*2026-05-23T19:42:04.404193Z*

 # Recommendation: Keep two projects, with a sharper division of labor

Your instinct is right. Merging would create more problems than it solves, and the cleaner play is to make the split *more* deliberate rather than collapse it.

## Why keeping them separate is the right call

**Claude Code is not optional for this kind of project.** The pipeline you're building — multi-sorter benchmarking, longitudinal QC across 96-channel Utah array sessions, MATLAB↔Python interop with NWB — requires a lot of file-level work: refactoring across modules, running tests, iterating on configs, profiling, managing the SpikeInterface environment, debugging Docker-based sorter containers, etc. Doing this through a chat interface with manual copy-paste means you'll spend more time on logistics than science. Claude Code earns its keep here.

**The two activities have different working rhythms.** Planning, literature triangulation, architectural decisions, and writing benefit from long, exploratory conversations with full project context — which is what this Enterprise project does well. Execution benefits from a tight read-modify-test loop in the actual repo, which is what Claude Code does well. Forcing both into one interface degrades both.

**Enterprise vs Pro is a real consideration.** Enterprise typically has better data handling guarantees and higher limits, which matters for the planning/research side where you're sharing more context and doing longer sessions. Pro on the Claude Code side is fine because the per-session token load is bounded by the repo state.

## Suggested division of labor

**This project (Enterprise, planning hub):**
- Session planning: before each Claude Code session, draft the goal, scope, files in play, and acceptance criteria here. Paste that brief into Claude Code as the starting prompt.
- Architecture decisions: probe geometry handling, NWB schema choices, sorter comparison metrics, longitudinal data model, MATLAB↔Python boundary conventions.
- Literature and methods research: validating algorithm choices, comparing sorter benchmarks, checking published QC metric definitions.
- Code review: paste diffs or files produced by Claude Code here for a second look, especially anything touching spike detection or sorting logic.
- Legacy MATLAB analysis: the four scripts in this project are useful reference material — what the analysis actually needs to produce, what the array remapping looks like, how impedance and unit yield are correlated, which patterns to preserve and which to abandon (the `eval(strcat(...))` lookup, `caxis` on heatmaps, date-versioned script proliferation).
- Writing: figures captions, methods sections, lab meeting summaries, grant text.

**Other project (Pro, Claude Code execution):**
- All actual code writing, refactoring, and testing.
- Running the SpikeInterface pipeline, Kilosort 4, MountainSort5, etc.
- File-level operations: config files, module structure, test fixtures.
- Debugging runtime errors with full repo context.

## How to keep them synchronized

The friction point in a two-project setup is keeping context aligned. Three concrete practices:

1. **A shared `PROJECT_STATE.md`** in the Claude Code repo, updated at the end of each Claude Code session with: what was built, what was decided, what's blocked, what's next. Paste this into the Enterprise project at the start of planning sessions. This is the bridge.

2. **Upload the legacy MATLAB scripts here too.** You've already got them in this project. When you're planning a migration step in this project, you can reason about it against the real legacy behavior, then hand a precise spec to Claude Code rather than vague intent.

3. **Decisions go here, code goes there.** If you find yourself making architectural decisions inside Claude Code, that's a signal to step back into this project. If you find yourself trying to write code inside this project, that's a signal to move to Claude Code. The two are not interchangeable; resist the temptation to do execution here when Claude Code is the right tool.

## On uploading the new project files here

Yes, upload them. The legacy code in this project plus the new project's scaffolding (CLAUDE.md, outline, deep research report, scratch code) gives this project full context for planning. You don't need to keep them in lockstep — this project just needs enough to advise on direction. Re-upload the key files (CLAUDE.md, current module structure, PROJECT_STATE.md) periodically when they've drifted materially.

## When this project alone would be enough

Only if the entire project stayed in the legacy-MATLAB-modernization phase with no Python migration, no SpikeInterface integration, and no multi-sorter benchmarking. Given your stated objectives — Kilosort 4, MountainSort5, SpyKING CIRCUS 2, Tridesclous2, longitudinal QC, NWB interop — that's not the project you're actually building. Claude Code will pay for itself within the first refactoring pass.

## One thing to flag

The new project apparently has a `CLAUDE.md` already configured. Worth checking that it's consistent with the project instruction you have here — especially the array dimension conventions (MATLAB channels×samples vs NumPy samples×channels), the GPU budget rules for the GTX 1650, and the `.ns5` vs `.ns6` branching logic. Inconsistencies between the two project's instructions are the most likely source of drift between what you plan here and what Claude Code actually does. If you want, upload the new `CLAUDE.md` and I'll cross-check it against this project's instructions before you start running sessions in earnest.

---

## 🧑 Human

*2026-05-23T19:57:20.782523Z*

> **[attachment: project_instructions.md]**

```text
// extracted from project_instructions.md
# Project: longitudinal recording quality pipeline (recqual)

## What this project is

Design partner and planning workspace for a SpikeInterface-based longitudinal extracellular recording quality assessment pipeline. The code itself lives in a Claude Code repo on the user's laptop; this project is for design discussions, session planning, conceptual questions about SI, and phase reviews. Claude Code does the implementation; this project does the thinking that precedes and follows it.

Package name: `recqual`. Hardware: Blackrock / Ripple Neuro acquisition, Utah arrays (16, 96 ch) and NeuroNexus linear / multi-shank probes (16, 64 ch). Sparse / low-density geometries, not Neuropixels-class. Primary goal: identify objective, practical metrics for longitudinal recording quality assessment. Secondary goal: integrate with future multimodal data (electrode impedance, endpoint histology, longitudinal in vivo imaging).

## About the user

Scientist with a doctoral degree. Cross-domain background in medicine, engineering, industry, and science. Comfortable with technical terminology, statistical reasoning, and primary literature conventions. New to Python relative to MATLAB and new to Claude Code. Working solo for now, but the pipeline will be handed to new students and collaborators, so handoff-readiness matters.

## Communication preferences

- Skip preambles and restated questions. Get to substance immediately.
- Use specific numbers, named mechanisms, and concrete examples rather than abstractions.
- Default to prose. Lists only when content is genuinely enumerable.
- Match length to question complexity. Brevity by default; expand only when warranted.
- No em dashes. No opening adjectives about the question ("great question"). No closing validation lines.
- No closing offers to elaborate unless asked.

## How to think

- Do not automatically agree. If reasoning is unsound, flag the issue and proceed with the best version of the question. If reasoning is sound, say so briefly and move on. Do not manufacture objections to perform independence.
- Do not force premature convergence. When a question has multiple defensible answers depending on assumptions, surface the branch point.
- Show load-bearing reasoning steps concisely. Skip micro-inferences.
- Honest uncertainty beats confident fabrication. If you do not know, say so.
- For ambiguous prompts: state the assumption inline and proceed. If genuinely underspecified, ask. If scope is ambiguous, ask before generalizing.
- When technical terms have different meanings across fields (e.g., "objective" in optics vs. epistemics, "signal" in electrophysiology vs. statistics), name the sense being used.

## Citations and sources

When citing a study, give enough detail (authors, year, journal) to locate it. Distinguish sourced claims, derived claims, and informed guesses. For numerical estimates, distinguish values from a specific source, values being computed, and values being guessed within an order of magnitude. Do not invent precision.

## Stack

Python (primary), MATLAB (parallel post-processing layer), GitHub. Sometimes R. Default to conventional scientific computing libraries.

## Project knowledge files

The project knowledge contains (or should contain):

- `CLAUDE.md`: the live policy file Claude Code reads. Authoritative for code conventions, sorter policy, data conventions, segment handling, file layout, etc. When the user asks a question whose answer depends on a project rule, check CLAUDE.md first.
- `pyproject.toml`: dependency pins and package metadata.
- `docs/notes/*.md`: per-topic reference material (segment handling, testing policy, SI function notes, etc.). These are the durable knowledge accumulated across sessions.
- `docs/session_plans/sessionNN_*.md`: per-session plan and outcome logs.
- `docs/phase_plans/phaseN_*.md`: phase-level summaries and validation specs.

Treat these as authoritative. If a chat's content conflicts with them, the files win unless the user is explicitly proposing a change. When the user asks for revisions to CLAUDE.md, pyproject.toml, or a note, generate the full revised file; do not produce diffs.

## Chat type conventions

Chats in this project are organized by purpose. The chat title usually signals which type.

### Session planning chats ("Session NN: <topic>")

One chat per upcoming Claude Code session. The deliverable is a session prompt for Claude Code (the bounded, plan-mode-ready prompt the user pastes into Claude Code). Inputs: the session number, the goal, the upstream state from prior session_plans. Outputs: the session prompt, optionally a list of session_plan outcome questions to verify after the session runs. Keep these focused; do not bleed into architecture or SI literacy questions here. After the Claude Code session runs, the same chat reviews the outcome and recommends what goes into the next session.

### Architecture & design chats ("Design: <topic>")

Long-lived chats on specific cross-cutting topics: multi-sorter consensus methodology, multimodal schema design, MATLAB interop, longitudinal aggregation strategy, etc. Conclusions from these chats land in `docs/notes/` and update CLAUDE.md when policy-level. One chat per topic, not one per question.

### SI literacy chats ("SI: <subsystem>")

Conceptual questions about SpikeInterface organized by subsystem (extractors, preprocessing, sorters, postprocessing & SortingAnalyzer, quality metrics, curation, comparison). The goal is the user's working understanding, not implementation. Conclusions land in `docs/notes/<function_or_concept>.md`. Distinct from Claude Code's in-session "explain this function" because here the explanation is for the user's mental model, not for the next code generation step.

### Phase review chats ("Phase N: review and plan")

End-of-phase chats that synthesize the phase's session_plans into a phase summary and plan the next phase. Output: `docs/phase_plans/phaseN_summary.md` and the rough session sequence for Phase N+1.

### Ad-hoc debugging chats ("Debug: <issue>")

Short chats on a stuck problem. Resolved or archived quickly. Do not let these grow into design discussions; spin out a Design chat if the issue is actually about architecture.

## What this project is not for

- Generating production code. That happens in Claude Code with the repo as context. If a chat here starts producing more than ~20 lines of code, redirect to a Claude Code session.
- Running tests or analysis. No tool access here beyond search and file generation.
- Replacing CLAUDE.md or docs/. If a decision is durable, it goes into a file, not into chat history.

## Project phases

- **Phase 1:** Single-sorter baseline (MountainSort5) on ~60-session Utah cohort with Plexon comparison.
- **Phase 2:** Add Tridesclous2 and Kilosort4; multi-sorter consensus and agreement matrices.
- **Phase 3:** Curation methods (UnitRefine, Bombcell with retuned thresholds).
- **Phase 4:** Full Utah cohort and 16-channel NeuroNexus probe support.

Future phases (impedance integration, histology and imaging registration) are deferred but the schema must accept them without retrofit.

## Defaults when in doubt

- Recommend writing durable conclusions to `docs/notes/` rather than emitting them inline.
- Recommend Claude Code plan mode for any non-trivial code change.
- Recommend MountainSort5 for Phase 1 sorter work unless the discussion is explicitly about sorter choice.
- Recommend pandas DataFrames in long format for analysis outputs that the user will inspect in a variable explorer.
- When the user uploads a CLAUDE.md or notes file revision, treat the upload as the new authoritative version and update the project knowledge accordingly in advice.

```

> **[attachment: roadmap.md]**

```text
// extracted from roadmap.md
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

- **Last completed session:** S1 (load demo, attach Utah-96 probe, read Plexon nev). S2 (validation figures) approved and queued.
- **Current sub-phase:** 1a (single-session module build).
- **Next session:** S3 (threshold-crossing module + ElectrodeMetadata + first exploration notebook).
- **Open items for user:** confirm whether Plexon-sorted data exists for all 60 sessions or a subset (decision needed before S6); confirm acquisition system on `nigel_2023-03-17` data (Blackrock NSP vs Ripple, affects pause-resume gotcha interpretation); cross-check 217 unit count from S1 against Plexon Offline Sorter UI.
- **Known deferred:** Phase 1 validation spec to be written before S7.

## When to update this file

- After each session completes: update "Current state pointer" only.
- At each phase boundary: expand the phase summary into `phase_plans/phaseN_summary.md`, then refresh this file's per-phase sections if the experience suggested changes for downstream phases.
- When a major scope decision changes: update the affected phase section and note the decision in the current state pointer.

Do not edit historical session sequences after the fact. If a session diverged from plan, capture the divergence in that session's `session_plans/` outcome section, not by retroactively rewriting the roadmap.

```

> **[attachment: CLAUDE.md]**

```text
// extracted from CLAUDE.md
# CLAUDE.md

Longitudinal extracellular recording quality assessment pipeline built on SpikeInterface. Primary acquisition: Blackrock / Ripple Neuro (nsX format). Primary probes: Utah arrays (16, 96 ch) and NeuroNexus linear / multi-shank (16, 64 ch). Sparse / low-density geometries, not Neuropixels-class.

Package name: `recqual`. Import as `from recqual.<module> import ...`.

## Versions to pin

Verify at the start of any debugging session:

```bash
python -c "import spikeinterface, probeinterface, neo; print(spikeinterface.__version__, probeinterface.__version__, neo.__version__)"
```

- Python: 3.11
- spikeinterface: pinned to a specific minor version in `pyproject.toml`. The API has moved enough across recent releases that "latest" silently breaks tutorials.
- probeinterface, neo: latest compatible with the SI pin
- mountainsort5, kilosort (4.x), bombcell: latest

If a tutorial or AI suggestion fails on a known-good install, suspect a version mismatch first.

## API conventions

- Use `SortingAnalyzer`, not `WaveformExtractor`. Any code referencing `WaveformExtractor` is outdated and must be ported.
- Use `probeinterface` for all probe geometry. Do not hardcode channel positions.
- Use `run_sorter_by_property(grouping_property="group")` for multi-shank probes.
- Never hardcode sampling rate. Always read it from the recording object.
- Never hardcode gain-to-uV. Always read it from the recording object.
- Curation labels are columns on the metrics DataFrame, never baked into the sorting object.

## Code style

- snake_case for variables, functions, modules. PascalCase for classes. Follows PEP 8.
- Variable names: 3 to ~30 characters typical. Hard cap at 50. If a name wants to grow past that, the abstraction is wrong.
- Short names allowed in two cases: (a) idiomatic Python (`i`, `j`, `df`, `ax`, `fs`, `nch`) and (b) short-lived loop or comprehension variables. Both require a one-line comment on first use describing the role.
- Use type hints on all function signatures and on non-obvious local assignments. Hints replace "what type is this" comments.
- First-time variable definition: one-line comment with purpose, unless purpose is obvious from name + type hint.
- Section headers in scripts and notebooks: `# === Section name: what this does ===`. In notebooks, use `# %%` cell markers.
- Key operations (filtering, indexing, math choices): brief comment on the *intent* of the operation, not its mechanics.
- Do not comment obvious code. Comment intent and non-obvious decisions only.
- Public functions: NumPy-style docstring (one-line summary, `Parameters`, `Returns`). Skip for trivial helpers.
- Optimize for legibility in a variable explorer: prefer `unit_amps` over `ua`, `n_units` over `numUnits`.

See `docs/coding_conventions.md` for worked examples.

## Data conventions

Blackrock / Ripple nsX semantics:

- `.ns5` = broadband, typically 30 kHz
- `.ns3` = LFP, typically 2 kHz. Use this directly for LFP; do not decimate ns5.
- `.nev` = events and externally-sorted spike data (Plexon Offline Sorter writes back to nev)

Blackrock recordings in this project typically report `gain_to_uV = 0.25` (16-bit ADC, quarter-microvolt resolution). This is a sanity-check value; always read gain from the recording object, do not hardcode.

Other supported formats: TDT data tanks, Neuropixels binary (SpikeGLX/OpenEphys), Intan RHD/RHS.

Sampling rates in use: 24414 Hz (TDT), 30000 Hz (Blackrock, Intan).

External event triggers are parsed from the Blackrock digital input stream via the appropriate `stream_id` argument to `read_blackrock`.

LFP is in scope. The pipeline must handle it alongside spikes, not as an afterthought.

## Segment handling

- Drop any segment shorter than 5 seconds at the IO layer with a logged warning. These are typically operator record-verification artifacts (see Gotchas).
- Process kept segments independently. Do not concatenate.
- `segment_index` is an explicit argument throughout the pipeline. Functions must not default to `segment_index=0`; they must require the caller to specify, or operate on all kept segments.

See `docs/notes/segment_handling.md` for rationale.

## Probe inventory and grouping rules

| Probe                          | Channels | `group` property             | Geometry source              |
|--------------------------------|----------|------------------------------|------------------------------|
| Utah 96ch                      | 96       | single group                 | probeinterface               |
| Utah 16ch                      | 16       | single group                 | probeinterface               |
| NeuroNexus 1-shank linear      | 16       | single group                 | probeinterface               |
| NeuroNexus 4-shank linear      | 64       | 4 groups by shank (0..3)     | probeinterface               |
| Custom arrays                  | varies   | config file mapping          | `configs/probes/<name>.json` |

**YOU MUST verify probe channel ordering against the Blackrock electrode IDs before trusting any sort.** Channel-order mismatch is silent and ruinous.

## Sorter policy

Multi-sorter consensus is the goal. Single-sorter output is never the primary result.

Default sorter pool:

- MountainSort5 (scheme 2 for production, scheme 1 for quick tests)
- Tridesclous2 (SpikeInterface-internal, based on `sortingcomponents`)
- Kilosort4 with `do_correction=False`. Drift correction is not effective at site pitch > 40 μm, which excludes all our probes except Neuropixels (Pachitariu et al., Nat Methods 2024).
- SpykingCircus2 as optional fourth for methodological diversity
- Plexon Offline Sorter output, where available, treated as a reference sorting (not ground truth)

Excluded:

- HerdingSpikes2 on linear / multi-shank probes. Designed for planar high-density arrays only (Magland et al., eLife 2020).
- Kilosort 1 / 2 / 3. KS4 replaces them with no loss for our hardware.
- MountainSort4. Superseded by MS5.

## Curation policy

Default: UnitRefine pretrained classifiers from HuggingFace. Validated on Utah arrays in the source paper (Jain et al., bioRxiv 2025).

```python
from spikeinterface.curation import unitrefine_label_units
labels = unitrefine_label_units(
    sorting_analyzer=sa,
    noise_neural_model="SpikeInterface/UnitRefine_noise_neural_classifier",
    sua_mua_model="SpikeInterface/UnitRefine_sua_mua_classifier",
)
```

Alternative: Bombcell via `bombcell_label_units`. Default thresholds are Neuropixels-tuned; retune for sparse probes before relying on output.

## Metrics layers

Three layers, each usable standalone:

1. **Threshold-crossing (no sorter).** Per-channel MAD noise floor, 4 to 5 x MAD crossings, crossing rate, waveform amplitude distribution, peak SNR. Build first.
2. **Per-sorter quality metrics.** SI's `compute_quality_metrics` (ISI violations, presence ratio, amplitude cutoff, SNR, firing rate) plus legacy MATLAB metrics (units per channel, max unit amplitude per channel).
3. **Multi-sorter consensus.** `compare_multiple_sorters` agreement matrix. **Report the agreement structure as a longitudinal metric. Do not collapse to a single consensus sorting as the primary output.**

## Testing

- Every module promoted to `src/` ships with at least one Tier 1 synthetic-data test of its core algorithm.
- Invariants (channel counts match, monotonicity of thresholded counts, peak-amplitude matches assigned electrode) are embedded as light tests or asserts.
- Regression / snapshot tests at milestones only, not per session.
- Do not test SpikeInterface primitives. Do not test plotting code.
- Test files: `tests/test_<module>.py`, run via `pytest tests/ -x`.

See `docs/notes/testing_policy.md` for rationale and worked examples.

## File layout

```
src/recqual/io/             extractors, probe maps, ElectrodeMetadata
src/recqual/preprocessing/
src/recqual/sorting/        sorter wrappers, per-group sorting
src/recqual/quality/        threshold-crossing, SI metrics
src/recqual/consensus/      multi-sorter comparison
src/recqual/lfp/
src/recqual/multimodal/     stubs for impedance / histology / imaging
matlab/                     parallel post-processing
notebooks/                  tutorial last; scratch first
configs/probes/             custom probe geometry definitions
data/                       raw and intermediate (gitignored)
tests/
docs/
```

## MATLAB compatibility

A parallel MATLAB layer consumes Python outputs for post-processing.

**No pickle in any file a MATLAB script will read.** Approved formats for MATLAB-facing outputs: NPY, NPZ, JSON, HDF5.

- Sortings: `sorting.save(folder=..., format="numpy_folder")`
- SortingAnalyzer: zarr or binary folder format with NPY exports
- Metrics: per-session JSON sidecar plus long-format Parquet for cross-session aggregation
- MATLAB reads NPY via npy-matlab (FileExchange)

Sorters run in Python only. MATLAB consumes the exports.

## Multimodal forward compatibility

`src/recqual/io/electrode_metadata.py` (planned, not yet built) defines an `ElectrodeMetadata` dataclass with optional fields for impedance, histology refs, in vivo imaging refs, and stereotaxic position. **All quality metrics report against `ElectrodeMetadata`, not against anonymous channel indices.**

Impedance is the first multimodal modality to integrate. Histology and imaging spatial registration are lower priority but the schema must accept them without retrofit.

**Do not redesign `ElectrodeMetadata` without flagging.** Quiet schema changes break downstream joins.

## Documentation outputs

Three kinds of durable documentation live alongside the code. None of these are optional; they are how the project stays auditable and handoff-ready.

### `docs/session_plans/`

One file per Claude Code session: `sessionNN_<short_topic>.md`.

- Write the approved plan to this file before exiting plan mode.
- At end of session, append an "Outcome" section: what was built, what diverged from the plan, what new uncertainty surfaced, what was deferred.
- 5 to 30 lines per file. This is a logbook entry, not a report.

### `docs/notes/`

One file per non-trivial concept, function, or design decision: `<topic>.md`. Topics are stable across sessions (e.g., `sorting_analyzer.md`, `segment_handling.md`, `utah_channel_mapping.md`).

Write a note when:
- An SI function is used for the first time in the project. Document what it does, what it returns, what alternative was considered, and why this one.
- A design decision is made that future sessions will need to honor.
- A non-obvious gotcha is discovered (these may also earn a line in CLAUDE.md's "Gotchas" section if they recur).

Notes are reference material, not narrative. Aim for 50 to 300 words. Update in place when understanding changes; do not append "edit history" sections.

### `docs/coding_conventions.md`

Examples and rationale for the style rules in CLAUDE.md's "Code style" section. Referenced from CLAUDE.md, not inlined, to keep CLAUDE.md tight.

## SI literacy practice

When introducing a SpikeInterface function not used previously in this project, include in the response (and in `docs/notes/<function>.md`):

1. One sentence on what the function does.
2. What it returns (type and shape if relevant).
3. The alternative considered and the reason for choosing this one.

If no alternative was considered (the function is the obvious or only choice), say so explicitly rather than fabricating one.

At the end of each session, list the SI functions used or introduced in that session as the last lines of the session_plan outcome. This builds a project-specific SI glossary across sessions without separate effort.

## Workflow rules

- Plan mode for any non-trivial change. Read SI source before editing.
- Iterate on 1 to 5 minute data slices, not full longitudinal recordings.
- Cache aggressively via `recording.save()` and SortingAnalyzer zarr.
- End-to-end run on one demo session before scaling.
- One task per session. `/clear` between unrelated tasks.
- When explaining a non-trivial concept or function, write the explanation to `docs/notes/<topic>.md` rather than emitting it inline. The main session is for code, not exposition.

## Gotchas

- Plexon Offline Sorter unit-class IDs in nev: 0 = unsorted, 1..N = sorted units, 255 = noise. Loading these as a `BaseSorting` may need a small wrapper; check NEO behavior before assuming SI handles it natively.
- `return_scaled` vs `return_in_uV` parameter naming changed across SI versions.
- Kilosort4 over-splits on sparse arrays. SLAy (`spikeinterface.curation`) can clean this up if needed.
- UnitRefine pretrained models live on HuggingFace; the first call downloads the model.
- Blackrock NSP firmware can write nsX files with non-contiguous electrode IDs; do not assume channel index equals electrode ID.
- Blackrock NSP often produces a brief (sub-5-second) first segment from operator record-verification before the real recording; this is normal and should be dropped (see `docs/notes/segment_handling.md`).

## Build / test commands

```bash
uv pip install -e ".[dev]"
pytest tests/ -x
ruff check src/
ruff format src/
```

## When in doubt

- Re-check the SI version pin.
- Re-check probe channel ordering against Blackrock electrode IDs.
- Read SI source rather than guess.
- Ask before generalizing a rule across probe types.

```

> **[attachment: scratch_load_nigel_2023-03-17.py]**

```text
// extracted from scratch_load_nigel_2023-03-17.py
"""Diagnostic load of Nigel 2023-03-17 Baseline DigitalHeadstage session.

Run from repo root:

    uv run python notebooks/scratch_load_nigel_2023-03-17.py

Confirms three things before any pipeline build-out:
  1. read_blackrock parses the .ns5 + digital event stream from the .nev
  2. A Utah-96 probe built from the per-array .cmp attaches with full
     contact <-> recording-channel coverage
  3. The Plexon-sorted (-01.nev) and manually curated (-02.nev) load as
     BaseSorting with non-zero unit counts after dropping Plexon
     unit_id 0 (unsorted) and 255 (noise).

Prints to stdout only. No disk writes.
"""

from __future__ import annotations

import re
import sys
import warnings
from collections import Counter
from pathlib import Path

import numpy as np

import neo
import probeinterface as pi
import spikeinterface
from neo.rawio import BlackrockRawIO
from probeinterface import Probe
from spikeinterface.extractors import read_blackrock, read_blackrock_sorting

# NEO emits a benign warning about an "undocumented segment" in Ripple-written
# NEV files. It does not affect the parse.
warnings.filterwarnings(
    "ignore", message="Detected .* undocumented segments within nev data"
)

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "raw"
BASE = "Nigel_Anterior_2023-03-17_Baseline_DigitalHeadstage"

NS5 = DATA / f"{BASE}.ns5"
NEV_PLEXON = DATA / f"{BASE}-01.nev"
NEV_CURATED = DATA / f"{BASE}-02.nev"
CMP = DATA / "SN 1025-001496.cmp"

UTAH_PITCH_UM = 400.0
SPIKE_CHANNEL_NAME_RE = re.compile(r"^ch(?P<elec>\d+)#(?P<unit>\d+)$")


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def asdict(row) -> dict:
    return {n: row[n] for n in row.dtype.names}


# ---------------------------------------------------------------------------
# Step 0  versions
# ---------------------------------------------------------------------------
banner("Step 0  versions")
print(f"python              {sys.version.split()[0]}")
print(f"spikeinterface      {spikeinterface.__version__}")
print(f"probeinterface      {pi.__version__}")
print(f"neo                 {neo.__version__}")
print(f"repo                {REPO}")

# ---------------------------------------------------------------------------
# Step 1  enumerate streams, open .ns5 via SI, list events, slice 1 s
# ---------------------------------------------------------------------------
banner("Step 1a  NEO header on the base recording")
raw_base = BlackrockRawIO(filename=str(DATA / BASE))
raw_base.parse_header()
hdr = raw_base.header

print("signal_streams:")
for s in hdr["signal_streams"]:
    print(f"  {asdict(s)}")
print(f"signal_channels: n={len(hdr['signal_channels'])}")
print(f"  first: {asdict(hdr['signal_channels'][0])}")
print(f"  last:  {asdict(hdr['signal_channels'][-1])}")
print(f"event_channels: n={len(hdr['event_channels'])}")
for ec in hdr["event_channels"]:
    print(f"  {asdict(ec)}")
print(f"spike_channels: n={len(hdr['spike_channels'])} (base .nev = unsorted only, U=0)")

# Resolve the 30 kHz broadband stream by sampling rate (not by hard-coded id).
ns5_stream_id = None
for s in hdr["signal_streams"]:
    rows = hdr["signal_channels"][hdr["signal_channels"]["stream_id"] == s["id"]]
    if len(rows) and abs(float(rows[0]["sampling_rate"]) - 30000.0) < 1.0:
        ns5_stream_id = str(s["id"])
        break
if ns5_stream_id is None:
    sys.exit("FAIL: no 30 kHz signal stream in header")
print(f"\nResolved ns5 stream_id = {ns5_stream_id!r}")

banner("Step 1b  SI read_blackrock on the .ns5")
rec = read_blackrock(file_path=str(NS5), stream_id=ns5_stream_id)
sr = rec.get_sampling_frequency()
nch = rec.get_num_channels()
nseg = rec.get_num_segments()
print(f"channels          {nch}")
print(f"sampling_rate     {sr} Hz")
print(f"num_segments      {nseg}")
for seg in range(nseg):
    ns = rec.get_num_samples(segment_index=seg)
    print(f"  seg[{seg}]  n_samples={ns:>10d}  dur={ns / sr:8.2f} s")
print(f"channel_ids[:10]  {list(rec.channel_ids[:10])}")
print(f"channel_ids[-5:]  {list(rec.channel_ids[-5:])}")

try:
    gains = rec.get_property("gain_to_uV")
    offsets = rec.get_property("offset_to_uV")
    print(f"gain_to_uV[:5]    {gains[:5]}")
    print(f"offset_to_uV[:5]  {offsets[:5]}")
except Exception as e:
    print(f"gain/offset lookup failed: {e!r}")

assert abs(sr - 30000.0) < 1.0, f"unexpected sampling rate {sr}"
assert nch == 96, f"unexpected channel count {nch}"

banner("Step 1c  events on the .nev (digital input)")
for i, ec in enumerate(hdr["event_channels"]):
    try:
        out = raw_base.get_event_timestamps(event_channel_index=i)
        ts = out[0] if isinstance(out, tuple) else out
        n = 0 if ts is None else len(ts)
        head = [] if n == 0 else list(ts[:5])
        print(f"  ch[{i}]  name={str(ec['name'])!r:>22s}  n_events={n:>6d}  first={head}")
    except Exception as e:
        print(f"  ch[{i}]  error: {e!r}")

banner("Step 1d  1-sec trace slice from segment 0  (proves memmap path)")
trace = rec.get_traces(segment_index=0, start_frame=0, end_frame=int(sr))
print(f"shape={trace.shape}  dtype={trace.dtype}")
print(f"first channel, first 5 samples: {trace[:5, 0]}")

# ---------------------------------------------------------------------------
# Step 2  parse CMP, build Utah-96, match contacts to recording channels
# ---------------------------------------------------------------------------
banner("Step 2a  parse Blackrock .cmp")


def parse_blackrock_cmp(path: Path) -> list[dict]:
    """Parse a Blackrock CMP mapfile.

    Returns one dict per electrode with col, row, bank, elec, label, and
    the Blackrock electrode_id = (bank - 'A') * 32 + elec.
    """
    rows = []
    for ln in path.read_text().splitlines():
        s = ln.strip()
        if not s or s.startswith("//"):
            continue
        parts = s.split()
        if len(parts) < 4:
            continue
        # Skip the description line ("Cerebus mapping for array ...")
        if not (parts[0].isdigit() and parts[1].isdigit() and parts[3].isdigit()):
            continue
        col, row, bank, elec = int(parts[0]), int(parts[1]), parts[2], int(parts[3])
        label = parts[4] if len(parts) >= 5 else f"bank{bank}_elec{elec}"
        electrode_id = (ord(bank.upper()) - ord("A")) * 32 + elec
        rows.append(
            dict(col=col, row=row, bank=bank, elec=elec, label=label, electrode_id=electrode_id)
        )
    return rows


cmp_rows = parse_blackrock_cmp(CMP)
eids = sorted(r["electrode_id"] for r in cmp_rows)
print(f"parsed {len(cmp_rows)} CMP rows")
print(f"first 3 rows: {cmp_rows[:3]}")
print(f"electrode_id range: {eids[0]} .. {eids[-1]}  (n_unique={len(set(eids))})")
banks = Counter(r["bank"] for r in cmp_rows)
print(f"banks used: {dict(banks)}")

banner("Step 2b  build Probe, match contacts to recording channels by electrode_id")
positions = np.array(
    [[r["col"] * UTAH_PITCH_UM, r["row"] * UTAH_PITCH_UM] for r in cmp_rows],
    dtype=float,
)
contact_ids = [str(r["electrode_id"]) for r in cmp_rows]

probe = Probe(ndim=2, si_units="um")
probe.set_contacts(
    positions=positions,
    shapes="circle",
    shape_params={"radius": 20.0},
    contact_ids=contact_ids,
)
probe.annotate(name="Utah-96", manufacturer="blackrock", serial="SN 1025-001496")
print(f"probe.contact_count = {probe.get_contact_count()}")

rec_chan_ids = [str(c) for c in rec.channel_ids]
print(f"recording channel_ids: first={rec_chan_ids[:5]}  last={rec_chan_ids[-5:]}")

missing_in_rec = set(contact_ids) - set(rec_chan_ids)
missing_in_cmp = set(rec_chan_ids) - set(contact_ids)
print(f"contacts not found in recording: {len(missing_in_rec)}")
print(f"recording channels not in CMP:   {len(missing_in_cmp)}")

chan_index_by_eid = {eid: i for i, eid in enumerate(rec_chan_ids)}
device_channel_indices = np.array(
    [chan_index_by_eid.get(cid, -1) for cid in contact_ids], dtype=int
)
n_unmapped = int((device_channel_indices == -1).sum())
print(f"unmapped contacts: {n_unmapped}")
assert n_unmapped == 0, "Utah probe attachment incomplete -- aborting"

probe.set_device_channel_indices(device_channel_indices)
rec_with_probe = rec.set_probe(probe, group_mode="by_probe")
locs = rec_with_probe.get_channel_locations()
print(f"rec_with_probe.channel_locations shape: {locs.shape}")

# Per-channel diagnostic: for the first 10 *recording* channels (already ordered
# 1..96), look up which probe row they correspond to and print position.
# device_channel_indices[k] = recording_channel_index for probe contact k.
# Invert to get probe row per recording channel.
probe_row_by_chan = {int(idx): k for k, idx in enumerate(device_channel_indices)}
print("first 10 recording channels (channel_index, electrode_id, x_um, y_um, bank, elec):")
for ch in range(10):
    eid = rec_chan_ids[ch]
    k = probe_row_by_chan[ch]
    r = cmp_rows[k]
    x, y = locs[ch]
    print(
        f"  ch={ch:3d}  eid={eid:>3s}  x={x:7.1f}  y={y:7.1f}  "
        f"bank={r['bank']}  elec={r['elec']:>2d}  label={r['label']}"
    )

# ---------------------------------------------------------------------------
# Step 3  Plexon -01.nev and curated -02.nev as BaseSorting
# ---------------------------------------------------------------------------


def neo_spike_channel_table(nev_path: Path) -> list[dict]:
    """For each NEO spike_channel, return (electrode_id, plexon_unit_id, name).

    Order is preserved -- SI's BlackrockSortingExtractor uses the same index
    as its unit_ids (verified by alignment assert below).
    """
    raw = BlackrockRawIO(filename=str(nev_path.with_suffix("")))
    raw.parse_header()
    rows = []
    for ch in raw.header["spike_channels"]:
        name = str(ch["name"])
        m = SPIKE_CHANNEL_NAME_RE.match(name)
        if m:
            rows.append(
                dict(name=name, electrode_id=int(m["elec"]), plexon_unit_id=int(m["unit"]))
            )
        else:
            # Unknown name format -- record as None so the assert below catches it
            rows.append(dict(name=name, electrode_id=-1, plexon_unit_id=-1))
    return rows


def load_and_summarize(nev_path: Path, label: str) -> dict:
    print()
    print(f"--- {label}  ({nev_path.name}) ---")
    neo_table = neo_spike_channel_table(nev_path)
    sorting = read_blackrock_sorting(file_path=str(nev_path), sampling_frequency=sr)
    n_raw = sorting.get_num_units()
    print(f"NEO spike_channels: {len(neo_table)}   SI n_units (incl. unsorted+noise): {n_raw}")
    assert len(neo_table) == n_raw, (
        f"length mismatch between NEO spike_channels ({len(neo_table)}) "
        f"and SI sorting ({n_raw}) -- positional alignment broken"
    )

    # Filter Plexon unit_id 0 (unsorted) and 255 (noise) per CLAUDE.md.
    sorted_idx = [
        i for i, r in enumerate(neo_table) if r["plexon_unit_id"] not in (0, 255)
    ]
    sorted_unit_ids = [sorting.unit_ids[i] for i in sorted_idx]
    sorting_sorted = sorting.select_units(unit_ids=sorted_unit_ids)
    print(f"after dropping unit_id 0 + 255: n_units = {sorting_sorted.get_num_units()}")

    # Per-electrode unit count (sorted only)
    per_elec = Counter(neo_table[i]["electrode_id"] for i in sorted_idx)
    if per_elec:
        hist = Counter(per_elec.values())  # how many electrodes have N sorted units
        print(f"  units per electrode  (counts): {dict(sorted(hist.items()))}")
        print(f"  electrodes with >=1 unit: {len(per_elec)} / 96")

    # Spike-count summary across all segments
    total_spikes = []
    for u in sorting_sorted.unit_ids:
        cnt = 0
        for seg in range(sorting_sorted.get_num_segments()):
            cnt += len(sorting_sorted.get_unit_spike_train(u, segment_index=seg))
        total_spikes.append(cnt)
    if total_spikes:
        a = np.array(total_spikes)
        print(
            f"  spike_counts  min={a.min()}  median={int(np.median(a))}  "
            f"max={a.max()}  total={int(a.sum())}"
        )
    return dict(
        raw=n_raw,
        sorted=sorting_sorted.get_num_units(),
        per_elec=per_elec,
        sorting=sorting_sorted,
    )


banner("Step 3  Plexon-sorted and curated sortings")
plex = load_and_summarize(NEV_PLEXON, "plexon offline sort (-01.nev)")
cur = load_and_summarize(NEV_CURATED, "manual curation  (-02.nev)")

banner("Step 3c  curated vs plexon diff")
print(f"sorted units  plexon={plex['sorted']}  curated={cur['sorted']}  "
      f"diff={cur['sorted'] - plex['sorted']}")
elecs_plex = set(plex["per_elec"])
elecs_cur = set(cur["per_elec"])
print(f"electrodes with units  plexon={len(elecs_plex)}  curated={len(elecs_cur)}")
print(f"  only in plexon:  {sorted(elecs_plex - elecs_cur)[:20]}{'...' if len(elecs_plex-elecs_cur)>20 else ''}")
print(f"  only in curated: {sorted(elecs_cur - elecs_plex)[:20]}{'...' if len(elecs_cur-elecs_plex)>20 else ''}")

banner("DONE")
print("Eyeball the printed unit counts vs the Plexon Offline Sorter report.")

```

> **[attachment: pyproject.toml]**

```text
// extracted from pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "recqual"
version = "0.1.0"
description = "Longitudinal extracellular recording quality assessment pipeline"
readme = "README.md"
requires-python = ">=3.11,<3.13"
license = { text = "MIT" }
authors = [
    { name = "TBD" },
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering",
]

# Core dependencies. SpikeInterface pin per CLAUDE.md.
# Bump deliberately, not casually; tutorials and AI suggestions assume specific API surfaces.
dependencies = [
    "spikeinterface[extractors,preprocessing,sorters,widgets,qualitymetrics,curation]~=0.102.3",
    "probeinterface>=0.2.21",
    "neo>=0.13.0",
    # Sorters bundled outside SI core
    "mountainsort5>=0.4.0",
    # Numerics and dataframes
    "numpy>=1.26,<3.0",
    "scipy>=1.11",
    "pandas>=2.1",
    # IO formats: parquet for long-format metrics, zarr for SortingAnalyzer, h5py for MATLAB
    "pyarrow>=14.0",
    "zarr>=2.16,<3.0",
    "h5py>=3.10",
    # Plotting
    "matplotlib>=3.8",
    "seaborn>=0.13",
]

[project.optional-dependencies]
# GPU sorters. Install with a CUDA-matched torch wheel separately if needed.
gpu = [
    "kilosort>=4.0",
    "torch>=2.1",
]

# Curation tools that are not yet always pip-installable cleanly.
# Bombcell's Python distribution name may vary; verify on install and adjust here.
curation-extras = [
    "bombcell",
]

# Dev tooling.
dev = [
    "pytest>=7.4",
    "pytest-cov>=4.1",
    "ruff>=0.6",
    "ipykernel>=6.29",
    "jupyterlab>=4.0",
]

# Documentation build (optional, only if building MkDocs site).
docs = [
    "mkdocs>=1.5",
    "mkdocs-material>=9.5",
]

[project.urls]
Repository = "https://github.com/TBD/recqual"

# ---------------------------------------------------------------------------
# Build configuration
# ---------------------------------------------------------------------------
[tool.hatch.build.targets.wheel]
packages = ["src/recqual"]

[tool.hatch.metadata]
allow-direct-references = true

# ---------------------------------------------------------------------------
# Linting and formatting
# ---------------------------------------------------------------------------
[tool.ruff]
line-length = 100
target-version = "py311"
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "UP",   # pyupgrade
    "NPY",  # numpy-specific rules
    "PD",   # pandas-vet
]
ignore = [
    "E501",  # line too long (formatter handles this)
    "PD901", # generic `df` variable name is fine per CLAUDE.md
]

[tool.ruff.lint.per-file-ignores]
"notebooks/**" = ["E402", "F401"]  # notebooks allowed late imports and unused-for-display
"tests/**" = ["B011"]              # asserts in tests are fine

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
]
filterwarnings = [
    "ignore::DeprecationWarning:neo.*",
    "ignore::DeprecationWarning:probeinterface.*",
]
markers = [
    "slow: tests that take more than a few seconds (run with -m slow)",
    "gpu: tests that require CUDA (skipped by default)",
]

[tool.coverage.run]
source = ["src/recqual"]
branch = true
omit = [
    "*/tests/*",
    "*/notebooks/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]

```

> **[attachment: blackrock_loading.md]**

```text
// extracted from blackrock_loading.md
# Blackrock loading

How `read_blackrock` and `read_blackrock_sorting` are used in this project.

## `read_blackrock` (the recording)

`spikeinterface.extractors.read_blackrock(file_path, stream_id=None, ...)` returns a `BaseRecording` wrapping the requested signal stream from one `.nsX` file. One call = one stream.

- **`file_path`** points at the specific `.nsX` (e.g. `.ns5` for broadband, `.ns3` for LFP). Do **not** point it at the base name and let NEO auto-discover — when sibling `-01.nev` / `-02.nev` files exist (Plexon-written copies of the same NEV), auto-discovery is ambiguous.
- **`stream_id`** is a **string** (`"5"` in the Nigel 2023-03-17 file). Resolve it dynamically by scanning the NEO header for the stream whose channels report ~30 kHz (or 2 kHz for LFP). Never hardcode the ID across files. See the session-1 script for the resolver.
- The returned object is multi-segment if the source NEV has multiple `nev_segment` blocks. `get_num_segments()` and `get_num_samples(segment_index=...)` are the truth source; segments < 5 s are dropped at the IO layer per [segment_handling.md](segment_handling.md).
- **`gain_to_uV`** comes back as a per-channel array via `rec.get_property("gain_to_uV")`. Blackrock 16-bit ADC convention is **0.25 µV / count**, and the Nigel file confirms this. Always read; never hardcode.
- **`return_scaled` / `return_in_uV`** keyword naming has shifted across SI minors — that's why the SI pin in `pyproject.toml` matters.

## `read_blackrock_sorting` (Plexon-written NEV)

`spikeinterface.extractors.read_blackrock_sorting(file_path, sampling_frequency, ...)` returns a `BaseSorting` built from the `spike_channels` block of one `.nev`. One call = one NEV file.

- `sampling_frequency` must match the broadband recording (we pass `rec.get_sampling_frequency()` from the matching `.ns5`). Mismatches silently break spike-train sample alignment.
- **`unit_ids` are positional indices `0..N-1`**, not the Plexon unit numbers. Index `i` in the returned sorting corresponds to row `i` of `BlackrockRawIO.header["spike_channels"]`. We assert this length equality at load time.
- The Plexon unit number and assigned electrode live in the NEO `spike_channels[i]["name"]` field, formatted as `"chE#U"` (electrode E, Plexon unit U). The project's regex is `^ch(\d+)#(\d+)$`.
- **Plexon unit-class IDs** per CLAUDE.md gotcha: `0` = unsorted, `1..N` = sorted units, `255` = noise. Filter `unit_id ∈ {0, 255}` to get the user-facing sorted units. Both `-01.nev` (auto-sort) and `-02.nev` (curated) yielded 217 sorted units in the Nigel 2023-03-17 file.
- **Alternative considered**: hand-build a `NumpySorting` from NEO's `get_spike_timestamps` and `rescale_spike_timestamp`. CLAUDE.md flagged this as the likely fallback. It was unnecessary — `read_blackrock_sorting` works as-is — but the wrapper plan is preserved for any future NEV variant SI doesn't natively handle.

```

> **[attachment: coding_conventions.md]**

```text
// extracted from coding_conventions.md
# Good
def compute_threshold_crossings(
    recording: si.BaseRecording,
    threshold_factor: float = 5.0,
    segment_index: int = 0,
) -> pd.DataFrame:
    """Return per-electrode crossing counts at threshold_factor x MAD.
    
    Parameters
    ----------
    recording : BaseRecording
        SpikeInterface recording with probe attached.
    threshold_factor : float
        Multiplier on MAD noise estimate. Typically 4 to 5.
    segment_index : int
        Which segment to process. Segments < 5 s are dropped upstream.

    Returns
    -------
    DataFrame with columns: electrode_id, n_crossings, rate_hz, mad_uv.
    """
    # MAD noise floor per channel, in uV (gain already applied)
    noise_mad: np.ndarray = si.get_noise_levels(recording, method="mad", return_scaled=True)
    threshold_uv = threshold_factor * noise_mad  # one threshold per channel

    # Crossings detected as negative-going excursions past threshold
    ...
	
# Bad (over-commented, types in comments not hints, verbose names)
def computeThresholdCrossingsForRecordingObject(
    inputRecordingObjectFromSpikeInterface,  # the recording object (BaseRecording)
    thresholdMultiplicationFactorForMAD,     # float, the multiplier
):
    # compute the noise floor using MAD
    # noise_floor_in_microvolts_per_channel: numpy ndarray of floats
    noise_floor_in_microvolts_per_channel = si.get_noise_levels(...)
    # multiply noise floor by threshold factor to get threshold
    threshold_value = thresholdMultiplicationFactorForMAD * noise_floor_in_microvolts_per_channel
    ...
```

> **[attachment: segment_handling.md]**

```text
// extracted from segment_handling.md
# Segment handling

## Policy

Drop any segment shorter than 5 seconds at the IO layer with a logged warning. Process kept segments independently; do not concatenate. `segment_index` is an explicit argument throughout the pipeline.

## Why this matters

Blackrock and Ripple NSP firmware commonly produce a brief (sub-5-second) first segment from operator record-verification before the real recording starts. A pause-resume during recording can also produce a short segment. These segments are artifacts, not data, but the pipeline cannot distinguish them from real epochs without a duration rule.

The cost of not having the policy is that every downstream function must handle arbitrarily short segments correctly. Most produce silently bad outputs rather than crashes:

**Spike sorting.** Sorters need hundreds of spikes per unit to estimate templates stably. At realistic firing rates (~5 Hz), a 2.36-second segment yields ~12 spikes per unit, well below the threshold for any modern sorter. MountainSort5 and Tridesclous2 run but produce unreliable templates. Kilosort4 may fail or produce nonsense. Failure modes vary across sorters and not all of them throw clean errors. Failures here can be silent: a unit "exists" in the output but its template is noise.

**Per-segment quality metrics.** Presence ratio, ISI violations, amplitude cutoff, and SNR all assume enough spikes to estimate a distribution. For very short segments these are statistically meaningless. They will still compute a number, which is the problem.

**Threshold-crossing rates.** The rate value itself is well-defined (normalized per second), but the variance is enormous. A true 0.1 Hz crossing rate over 2.36 s yields 0 or 1 actual crossings; the rate estimate is unstable. Pooling unstable estimates into longitudinal trends produces noisy time courses for no benefit.

**Aggregation and longitudinal joins.** Cross-session statistics require either per-segment aggregation weighted by duration or a "longest segment" rule. Both require carrying `segment_index` and duration through every join. The cleanest place for this decision to live is "drop segments below a duration where the question stops mattering."

## Why 5 seconds

5 seconds is a safety floor, calibrated to catch operator-verification artifacts (typically 1 to 3 s) without affecting any legitimate analysis epoch. Real baseline recordings are minutes long; real task epochs are typically tens of seconds at minimum. There is no plausible scientific use case for a 4-second segment in this project.

Downstream operations may impose stricter minimums at their own layer. Spike sorting in particular often requires segments of 60 s or more to estimate templates reliably. These per-stage minimums are separate from the IO-layer policy and are documented in their respective modules.

## Cost of the policy

One filter at the IO layer, approximately 10 lines of code, plus one log entry per dropped segment. The policy lives in `src/recqual/io/` and is applied during recording load, so every downstream consumer sees only kept segments.

## What to log

For each dropped segment, log: source file, segment index in the raw file, duration in seconds, reason ("below 5 s threshold"). Keep the log per-session so the segment-handling decisions are auditable.

## Reference

- Discovered: session 1 on `data/raw/nigel_2023-03-17.ns5` (2.36 s segment 0, 180.01 s segment 1).
- Policy decided: between session 1 and session 2.

```

> **[attachment: segment_selection.md]**

```text
// extracted from segment_selection.md
# Segment selection (recording and sorting)

How to pull a single segment out of a multi-segment SI object. The two sides of the pair (`BaseRecording`, `BaseSorting`) have an inconsistent API — knowing which is which prevents an `AttributeError` halfway through pipeline code.

This is the *mechanics* note. The *why* (the 5 s minimum-segment rule, the rationale for processing segments independently rather than concatenating) is in [segment_handling.md](segment_handling.md).

## Recording: method on the object

```python
rec_seg1 = rec_with_probe.select_segments([1])
```

`BaseRecording.select_segments(segment_indices)` is defined on `BaseRecordingSnippets` (the shared base for recordings and snippets). Internally it returns a `SelectSegmentRecording`. **The attached probe survives the call** — verified during session 2 plan-mode exploration; `rec_with_probe.select_segments([1]).get_channel_locations().shape == (96, 2)`.

`segment_indices` must be a list (or a single int, but pass a list for clarity).

## Sorting: free function, **no** matching method

```python
from spikeinterface.core import select_segment_sorting
sort_seg1 = select_segment_sorting(sort_curated, [1])
```

**`BaseSorting` has no `select_segments` method.** Reaching for the symmetric API is a trap; it throws `AttributeError` at run time. Use `spikeinterface.core.select_segment_sorting`, which returns a `SelectSegmentSorting` (see SI source at `spikeinterface/core/segmentutils.py:576`).

## Composition with `select_units`

Both operations preserve the unit-id set on the result. For curated sortings where we drop `unit_id ∈ {0, 255}`, the composition order is:

```python
sort_filtered = sort_curated.select_units(unit_ids=keep_uids)   # 217 sorted units
sort_seg1     = select_segment_sorting(sort_filtered, [1])      # 1 segment, 217 units
```

`select_units` first (cheap, just a unit-id subset) then `select_segment_sorting` (rewrites the internal segment list). The other order works too in 0.102.3, but this ordering matches the natural "filter, then slice" mental model.

## Why a single-segment sorting matters for templates

`SortingAnalyzer` waveform / template extraction uses the sorting's spike trains as positions to slice from the recording. If the recording is single-segment but the sorting is still multi-segment, `create_sorting_analyzer` will refuse the mismatched segment counts. Always trim both sides together.

If a unit had **all** its spikes in the dropped segment (e.g. only fired during the 2.36 s false-start), it ends up with zero spikes in the kept segment, no waveforms, and an all-NaN template. The validation script surfaces this rather than crashing — none of the Nigel 2023-03-17 curated units had this property.

## Alternative considered

`spikeinterface.core.split_sorting(parent_sorting, recording_list)`: splits a multi-segment sorting into per-segment children. Useful when you want **all** segments individually (e.g. per-segment quality metrics); overkill when you only want one. Session 2 only needed `seg[1]`, so the targeted `select_segment_sorting` is the right tool.

```

> **[attachment: sorting_analyzer.md]**

```text
// extracted from sorting_analyzer.md
# SortingAnalyzer

Replaces the deprecated `WaveformExtractor`. Pairs one `BaseRecording` with one `BaseSorting` and hangs computed quantities (random spikes, waveforms, templates, quality metrics, …) off the pair as named "extensions". The persisted form is a folder (binary or zarr) that can be reloaded with all extensions intact.

## Create / load

```python
from spikeinterface.core import create_sorting_analyzer, load_sorting_analyzer

sa = create_sorting_analyzer(
    sorting, recording,
    format="zarr",                # or "binary_folder" or "memory"
    folder="data/derived/.../sorting_analyzer_curated.zarr",
    sparse=False,                 # dense across all channels; see "Sparsity" below
    return_scaled=True,           # all extensions see uV-scaled traces
    overwrite=False,
)

sa = load_sorting_analyzer("data/derived/.../sorting_analyzer_curated.zarr")
```

`return_scaled=True` is the global gain-scaling switch — set it once at construction so different extensions don't disagree (e.g. an SNR computed against scaled traces vs an amplitude against raw counts).

## Extensions

Computed as a dependency chain. Templates depend on `random_spikes` (or on `waveforms`, which itself depends on `random_spikes`).

```python
sa.compute("random_spikes", method="uniform", max_spikes_per_unit=500, seed=0)
sa.compute("templates", operators=["average"], ms_before=1.0, ms_after=2.0)
```

- Persisted to the analyzer folder on `save=True` (default). Reload via `load_sorting_analyzer` carries them automatically.
- Check with `sa.has_extension("templates")`; access data with `sa.get_extension("templates").get_data(operator="average")` → numpy array `(n_units, n_samples, n_channels)`.

## Sparsity

`sparse=True` (default) computes a per-unit channel mask from a quick template estimate, then propagates it: waveforms and templates only store channels near each unit's peak. **For this project we want `sparse=False`** when the spatial template across every electrode is the point — Figure 3 in session 2 needs all 96 channels per unit to overlay on the Utah grid.

## The "waveforms vs accumulator" gotcha

`sa.compute("templates")` has two code paths:

1. **If the `waveforms` extension is present**, templates are averaged from the cached waveform stack. Memory cost is full: `(n_random_spikes × n_samples × n_channels × dtype)` lives in a single shared buffer.
2. **If `waveforms` is absent**, templates fall through to `spikeinterface.core.template_tools.estimate_templates_with_accumulator`, which streams the recording once and accumulates running means per unit. Memory cost is `(n_units × n_samples × n_channels)` — orders of magnitude smaller.

On Windows, path 1 fails for our parameter range. 217 units × 500 spikes × 96 channels × 90 samples × float32 ≈ **3.75 GB** in a single `multiprocessing.shared_memory.SharedMemory` allocation, which trips `OSError [WinError 1450] Insufficient system resources`. Session 2 settled on path 2: **skip `sa.compute("waveforms", ...)` when only templates are needed**. 6.1 s for 217 units on a 180 s segment; cached zarr is 6.8 MB.

Path 1 is still required if downstream needs individual waveforms (PCA, amplitude scatter, per-spike features). When that day comes, switch to `format="binary_folder"` — the waveforms extension then writes via `numpy.memmap` instead of shared memory, sidestepping the Windows cap.

## Alternative considered

`WaveformExtractor` (older SI API). Excluded: deprecated, removed in 0.102.x. CLAUDE.md hard rule: "Use `SortingAnalyzer`, not `WaveformExtractor`. Any code referencing `WaveformExtractor` is outdated and must be ported."

```

> **[attachment: template_extremum_channel.md]**

```text
// extracted from template_extremum_channel.md
# `get_template_extremum_channel`

`spikeinterface.core.template_tools.get_template_extremum_channel(templates_or_sorting_analyzer, peak_sign="neg", mode="extremum", outputs="id")`

Returns a dict `{unit_id: channel_id_or_index}` mapping each unit to the channel where its template peak is largest. The "where does this unit sit on the probe?" function.

## Inputs and parameters

- First positional argument: a `Templates` object or a `SortingAnalyzer` with the `templates` extension computed (`sa.has_extension("templates")` must be true).
- **`peak_sign`**: `"neg"` (default), `"pos"`, or `"both"`. Extracellular action potentials are dominantly negative-going at the soma, so `"neg"` is the right default for spike sorting outputs. `"both"` falls back to absolute amplitude — useful when units could be either polarity (e.g. axonal recordings) but slower and slightly noisier.
- **`mode`**:
  - `"extremum"` — peak value (min for `peak_sign="neg"`, max for `"pos"`).
  - `"at_index"` — value sampled at `nbefore` (the alignment index). Less robust to template jitter.
  - `"peak_to_peak"` — full range across the template window. Robust to small phase shifts and to units with both positive and negative components. **Session 2 uses this.**
- **`outputs`**: `"id"` returns the SI `channel_id` (string in this project — Blackrock electrode IDs are strings like `"5"`); `"index"` returns the positional channel index (`int`).

## How session 2 uses it

```python
peak_id_by_unit = get_template_extremum_channel(
    sa, peak_sign="neg", mode="peak_to_peak", outputs="id"
)
peak_eid_by_unit = {u: int(cid) for u, cid in peak_id_by_unit.items()}
```

Then compared against the **assigned** electrode from the Plexon `chE#U` name. Found 1/217 mismatches (unit 297, assigned elec90, peak elec89 — adjacent contact). The function is the spatial cross-check on the unit-to-electrode assignment baked into the NEV file.

## Returns

A `dict` keyed by `unit_id`. **Order is not guaranteed**; iterate by `sorting.unit_ids` if you need a stable order matching the sorting object.

## Alternative considered

Computing the peak channel by hand: `np.argmax(np.ptp(templates, axis=1))` per unit, indexed into `sa.channel_ids`. Equivalent for the `peak_to_peak` case but loses the `peak_sign` polarity semantics. The SI helper also handles sparsity correctly (returns the peak within the unit's sparse mask, not the global recording channel) — relevant for any future sparse-analyzer work even if session 2 ran with `sparse=False`.

```

> **[attachment: testing_policy.md]**

```text
// extracted from testing_policy.md
# Testing policy

## The failure mode this addresses

Scientific analysis pipelines do not usually fail by crashing. Crashes are caught immediately. They fail by producing plausible-looking but wrong results: a channel-mapping swap that produces a sensible template plot at the wrong location, an off-by-one in segment indexing that drops one spike per segment, a sign flip in MAD that makes everything appear saturated, a sampling-rate confusion that compresses time by 22%. These errors are silent and propagate through entire pipelines undetected.

Tests exist to catch this class of error. The test suite is not a check on correctness of `if` statements; it is a check on whether the code does what its name says it does.

## Three tiers, ordered by value

### Tier 1: synthetic-data tests for core algorithms

For each algorithm in `quality/`, `sorting/`, and `io/`, write a test that builds synthetic data with known properties and verifies the algorithm recovers them.

Concrete examples for this project:

- **Threshold-crossing detector.** Inject N spikes at known amplitudes into white noise of known std. Verify N crossings detected at the right threshold factor. Verify polarity (negative-going by extracellular convention).
- **MAD noise estimator.** Pure Gaussian noise of known std. `MAD * 1.4826` should approximate std within a tolerance of a few percent.
- **Probe geometry parsing.** Parse a synthetic `.cmp` file with handcrafted electrode/bank assignments. Verify electrode IDs compute correctly via `(bank - 'A') * 32 + elec`.
- **Channel mapping validation.** Given a recording with channel_ids `['3', '1', '2']` and a probe with electrode IDs `[1, 2, 3]`, verify the mapping function correctly identifies the permutation.
- **Segment filtering.** Given a recording with segments of `[2 s, 180 s, 60 s]` and the 5 s threshold, verify the kept indices are `[1, 2]` and the dropped index is `[0]`.

Tier 1 tests are written for every module promoted from `notebooks/scratch/` to `src/`. They pay back forever; the cost of writing them is small relative to the cost of one silent error.

### Tier 2: invariant checks

Properties that must hold regardless of input, embedded as `assert` statements in pipeline code or as light pytest tests.

Examples:

- After loading a recording with a probe attached, `recording.get_num_channels() == probe.get_contact_count()`.
- Crossings at threshold `5 x MAD` are less than or equal to crossings at threshold `4 x MAD` (monotonic).
- After segment filtering, all kept segments have duration above the policy threshold.
- Per-unit assigned electrode (from `chN#U` name in nev) matches the electrode with peak template amplitude. This last one is real scientific validation, not just a software test; it catches Plexon-to-SI channel mapping errors that no synthetic test would find, because it operates on real data and on the chain end-to-end.

Invariants are cheap and catch a lot. They run on real data, not synthetic, so they validate the chain end-to-end rather than the algorithm in isolation. Treat them as a complement to Tier 1, not a substitute.

### Tier 3: regression / snapshot tests at milestones

Once the pipeline runs end-to-end on the demo session, store key outputs (unit count, mean MAD per channel, template peak amplitudes for a handful of units) in a fixture file. A regression test loads the fixture and verifies current outputs match within tolerance.

Catches "I refactored and changed behavior I didn't intend to change." Write only at milestones, not per session. Update the fixture when an intended behavior change occurs, and note the update in the corresponding session_plan.

Milestones to target:

- After threshold-crossing module is stable on the demo session.
- After one full sorter run is stable end-to-end.
- After multi-sorter consensus produces a reproducible agreement matrix on the demo session.
- Before scaling to the longitudinal cohort.

## What not to test

- **SpikeInterface itself.** SI has its own test suite. Do not duplicate.
- **Plotting code.** Visual outputs are validated by eye, against the validation figures from session 2 onward.
- **Trivial glue code.** Tests should cover logic, not plumbing. A function that calls `recording.get_traces()` and returns the result does not need a test.

## When to write tests

- Tier 1 tests ship with the code being promoted to `src/`, not after. The PR that adds the module also adds the test.
- Tier 2 invariants are embedded throughout, both as runtime `assert` statements in pipeline code and as light tests in `tests/`.
- Tier 3 regression tests are written at the milestones above. Each new milestone adds one fixture, not many.

## File layout and execution

- Test files: `tests/test_<module>.py`. One test file per source module is the default; split if test files exceed ~300 lines.
- Synthetic data generators: `tests/fixtures/synthetic.py` for shared generators (white noise + injected events, synthetic `.cmp` files, etc.).
- Regression snapshots: `tests/snapshots/<milestone>/` as NPZ or JSON files. Treat as data; check into git if small (< 1 MB), Git-LFS or external storage if larger.
- Run all tests: `pytest tests/ -x` (stop on first failure during development).
- Run one module: `pytest tests/test_threshold_crossing.py -v`.
- Run only fast tests in CI: `pytest tests/ -m "not slow"` (use the `slow` marker from `pyproject.toml`).

## A worked example: threshold-crossing detector

```python
# tests/test_threshold_crossing.py
import numpy as np
import pytest
from recqual.quality.threshold_crossing import detect_crossings

def test_detects_known_events_above_threshold():
    """White noise plus injected events at -6x MAD. Detector must find them."""
    rng = np.random.default_rng(seed=42)  # rng: seeded generator for reproducibility
    fs = 30000                            # fs: sampling rate, Hz
    n_samples = fs * 10                   # 10 s of synthetic data

    # Pure Gaussian noise, std = 10 uV. Then inject 50 events at -60 uV.
    noise: np.ndarray = rng.normal(0, 10, n_samples).astype(np.float32)
    event_times = rng.integers(100, n_samples - 100, size=50)  # avoid edges
    signal = noise.copy()
    signal[event_times] = -60.0  # negative-going by extracellular convention

    crossings = detect_crossings(signal, fs=fs, threshold_factor=4.0)

    # All 50 events should be detected (with margin for rare double-counts at edges)
    assert 48 <= len(crossings) <= 52


def test_monotonic_in_threshold_factor():
    """Stricter threshold returns equal or fewer crossings. Invariant."""
    rng = np.random.default_rng(seed=42)
    signal = rng.normal(0, 10, 30000 * 10).astype(np.float32)

    c4 = detect_crossings(signal, fs=30000, threshold_factor=4.0)
    c5 = detect_crossings(signal, fs=30000, threshold_factor=5.0)
    c6 = detect_crossings(signal, fs=30000, threshold_factor=6.0)

    assert len(c4) >= len(c5) >= len(c6)
```

These two tests together cover (1) the algorithm recovers known ground truth and (2) an invariant that must hold. The cost is roughly 30 lines and runs in under a second. The benefit is that any future change to `detect_crossings` that breaks either property fails CI before it reaches the longitudinal cohort.

## Reference

- Policy decided: between session 2 and session 3, before threshold-crossing module is built.
- Inspiration: the test-pyramid model (unit tests cheap and many, integration tests rarer, end-to-end tests rarest). Tier 1 corresponds to unit tests of algorithms, Tier 2 to lightweight integration tests, Tier 3 to end-to-end snapshots.

```

> **[attachment: utah_channel_mapping.md]**

```text
// extracted from utah_channel_mapping.md
# Utah channel mapping

Parsing a Blackrock per-array CMP file into a `probeinterface.Probe`, and the four-ID disambiguation needed to verify channel ordering against the recording.

## CMP file format

One row per electrode, whitespace-separated:

```
col  row  bank  elec  label
```

- `col`, `row`: integer position on the 10×10 grid. Row 0 is at the bottom, col 0 is at the left.
- `bank`: `A`, `B`, or `C`. The Cerebus NSP wires 32 contacts per bank.
- `elec`: 1..32, the Blackrock electrode number **within the bank**.
- `label`: free text (often `elecN`).

The header lines and any line starting with `//` are ignored. Lines that don't have `digit digit non-digit digit` in the first 4 columns are skipped (catches the leading descriptive line in Blackrock-issued CMPs).

The 96-electrode Utah array has **4 of the 100 grid positions unused**. In the Nigel array (SN 1025-001496) those are `(0,0)`, `(0,1)`, `(1,1)`, `(3,9)` — not all four corners, which is why we read positions from the CMP rather than assuming a standard pattern.

## Blackrock electrode ID

```python
electrode_id = (ord(bank.upper()) - ord("A")) * 32 + elec   # A1..A32 -> 1..32, B1..B32 -> 33..64, C1..C32 -> 65..96
```

This is the integer that appears in the NEV `signal_channels["id"]` field and in NEO spike-channel names like `chE#U`. It is the join key between the CMP, the recording, and Plexon's unit assignment.

## Probe build

```python
positions = [[r["col"] * 400.0, r["row"] * 400.0] for r in cmp_rows]   # Utah pitch is 400 um
probe.set_contacts(positions=positions, shapes="circle",
                   shape_params={"radius": 20.0},
                   contact_ids=[str(r["electrode_id"]) for r in cmp_rows])
```

`contact_ids` are strings (PI convention). Set them from `electrode_id` so the recording's `channel_id` strings (also derived from `electrode_id`) can be joined by equality.

## Attaching to a recording: `device_channel_indices`

For each probe contact `i`, `device_channel_indices[i]` must equal the recording channel index that has the matching electrode ID. Build by dict lookup, never positionally:

```python
chan_index_by_eid = {rec.channel_ids[i]: i for i in range(rec.get_num_channels())}
device_channel_indices = [chan_index_by_eid[cid] for cid in probe.contact_ids]
probe.set_device_channel_indices(device_channel_indices)
rec_with_probe = rec.set_probe(probe, group_mode="by_probe")
```

**Assert zero unmapped contacts** before continuing. CLAUDE.md: channel-order mismatch is "silent and ruinous".

## The four-ID disambiguation

A given physical contact has four identities in this project; Figure 1 in [session 02](../session_plans/session02_validation_figures.md) prints all four per tile:

| ID                  | Source                                        | Type     | Example |
|---------------------|-----------------------------------------------|----------|---------|
| `electrode_id`      | `(bank - 'A') * 32 + elec` from the CMP       | `int`    | `5`     |
| `channel_id`        | SI `rec.channel_ids[i]` (from NEV header)     | `str`    | `"5"`   |
| `channel_index`     | positional index into `rec.channel_ids`       | `int`    | `4`     |
| `bank` / `elec`     | CMP physical labeling                          | `str`/`int` | `A` / `5` |

In the Nigel 2023-03-17 file the relationship is the simplest possible — `channel_index + 1 == int(channel_id) == electrode_id`. **Do not generalize.** CLAUDE.md gotcha: Blackrock NSP firmware can write nsX files with non-contiguous electrode IDs. The validation script asserts this identity per file, and Figure 1 makes any deviation immediately visible.

## probeinterface used

- `Probe(ndim=2, si_units="um")`, `set_contacts`, `set_device_channel_indices`, `annotate`. The catalog probe (`get_probe`) was not used: building positions directly from the CMP is simpler than reconciling catalog coordinates against per-array missing-position patterns.
- `recording.set_probe(probe, group_mode="by_probe")` returns a probe-attached recording. `group_mode="by_probe"` puts all 96 channels into a single SI group, matching the [CLAUDE.md probe table](../../CLAUDE.md) (Utah arrays are single-group).

```

> **[attachment: session01_load_demo_data.md]**

```text
// extracted from session01_load_demo_data.md
# Session 01  Load demo data

## Plan

First hands-on session against real data: the Nigel 2023-03-17 Baseline DigitalHeadstage session. Greenfield repo (only CLAUDE.md + `data/raw/` present). Three confirmations to land before any pipeline code:

1. **Environment bootstrap.** `uv python install 3.11`, minimal `pyproject.toml` pinning `spikeinterface[full]==0.102.*`, `probeinterface>=0.2.27`, `neo>=0.14.0`. `uv venv --python 3.11` + `uv sync`.
2. **`read_blackrock` on the `.ns5`** — confirm 96 ch at 30 kHz, list event channels from the paired `.nev`, pull a 1 s memmap slice to prove the IO path. Resolve `stream_id` by sampling rate, never hardcode.
3. **Utah-96 probe.** Parse the array CMP, build a `Probe`, attach to the recording with `device_channel_indices` built from electrode-id lookup. Hard-assert zero unmapped contacts (CLAUDE.md: silent channel-order mismatch is ruinous).
4. **Plexon-written `.nev` as `BaseSorting`.** Try `read_blackrock_sorting`; if it under-delivers, fall back to NEO + `NumpySorting`. Filter `unit_id ∈ {0, 255}` (unsorted, noise) per CLAUDE.md gotcha. Do this for both `-01.nev` (Plexon auto) and `-02.nev` (manually curated).

Deliverable: `notebooks/scratch_load_nigel_2023-03-17.py`, prints to stdout, no disk writes.

## Outcome

All three landed clean. `read_blackrock_sorting` works directly; no NEO+NumpySorting wrapper needed. `gain_to_uV` confirmed at 0.25 µV (Blackrock 16-bit ADC quarter-microvolt resolution). Both `-01.nev` and `-02.nev` yield **217 sorted units** after the `{0, 255}` filter.

Discoveries that fed downstream sessions:
- The recording is **two segments**: `seg[0] = 2.36 s` (Ripple "false-start" record-verification artifact), `seg[1] = 180.01 s` (the real recording). Drove the 5 s minimum-segment policy in [segment_handling.md](../notes/segment_handling.md).
- **Channel ordering is contiguous and identity-mapped** in this file: `channel_index + 1 == int(channel_id) == electrode_id_from_cmp`. Captured in [utah_channel_mapping.md](../notes/utah_channel_mapping.md). Future sessions verify this per-recording rather than assume.
- NEO encodes Plexon unit assignment in the spike-channel `name` as `chE#U` (electrode E, unit U). The wrapper for parsing this is in `scratch_load_nigel_2023-03-17.py`; promoted-to-`src/` form deferred.
- The two NEV files have non-standard `-01`/`-02` suffixes; NEO's auto-discovery is unsafe with them. Always construct one `BlackrockRawIO` per explicit base filename.

## SI / PI functions introduced

- `spikeinterface.extractors.read_blackrock` — see [blackrock_loading.md](../notes/blackrock_loading.md)
- `spikeinterface.extractors.read_blackrock_sorting` — see [blackrock_loading.md](../notes/blackrock_loading.md)
- `probeinterface.Probe`, `Probe.set_contacts`, `Probe.set_device_channel_indices` — see [utah_channel_mapping.md](../notes/utah_channel_mapping.md)
- `spikeinterface.BaseRecording.set_probe(group_mode="by_probe")` — see [utah_channel_mapping.md](../notes/utah_channel_mapping.md)
- `neo.rawio.BlackrockRawIO` — used as the truth source for streams, electrode IDs, and spike-channel names

```

> **[attachment: session02_validation_figures.md]**

```text
// extracted from session02_validation_figures.md
# Session 02  Validation figures

## Plan

Three visual guardrails against silent channel-order or unit-assignment errors before any QA metrics. All work in `notebooks/scratch_validation_nigel_2023-03-17.py` + `figures/validation/`. Nothing promoted to `src/`. Inputs from session 1: the loader, the probe attach, the `-01`/`-02` sortings, and the segment decision (drop `seg[0] = 2.36 s`, use `seg[1] = 180.01 s`).

- **Figure 1** — Utah-96 10×10 layout, one tile per electrode, four small text rows: `electrode_id` (CMP), SI `channel_id`, SI `channel_index`, bank/elec. Tile fill colored by bank (A/B/C). Saved as PNG + PDF.
- **Figure 2** — three-panel heatmap on the same grid: auto-sort counts, curated counts, (curated − auto) on diverging colormap. PNG only.
- **Figure 3** — multi-page PDF, one page per curated unit, 96 mini-axes laid out on the Utah grid showing the unit's mean waveform at every electrode. Assigned electrode (from Plexon `chE#U`) highlighted in red; peak-amplitude electrode highlighted in green. Cache the `SortingAnalyzer` to `data/derived/nigel_2023-03-17/sorting_analyzer_curated.zarr`. Iterate on `--first-n 10` before generating all 217 pages.

Report at end: (a) any electrodes where `channel_id` / `electrode_id` / `channel_index` disagree; (b) peak-vs-assigned mismatches with examples; (c) template-compute runtime as a longitudinal budget anchor.

## Outcome

All three figures generated. Sign-off numbers:

- **(a) Channel-mapping disagreements: 0 / 96.** Confirms session 1's contiguous identity mapping on this file.
- **(b) Peak-vs-assigned mismatches: 1 / 217.** Unit 297, assigned elec90, peak elec89 (adjacent contact, 400 µm apart). Plausible spike spread, not a structural issue.
- **(c) Template-compute runtime: 6.1 s** over `seg[1]` (180.01 s @ 30 kHz × 96 ch) on 217 units. Cached zarr is 6.8 MB. Anchor for scaling to longitudinal data: ≈ 0.034 s/unit/180-s-segment.

Gotcha discovered (recorded in [sorting_analyzer.md](../notes/sorting_analyzer.md)): `sa.compute("waveforms")` blows the Windows `SharedMemory` cap at our parameter range (217 × 500 × 96 × 90 × float32 ≈ 3.75 GB). Skipping the `waveforms` extension lets `ComputeTemplates` use `estimate_templates_with_accumulator`, which streams the recording once. Faster, OOM-immune; preferred path for templates-only work.

Two non-zero cells in Figure 2's diff panel: +1 unit on electrode 65 (curator added), −1 on electrode 26 (curator merged or removed) — diff total nets to 0, matching the session 1 counts.

## SI / PI functions introduced

- `spikeinterface.core.create_sorting_analyzer`, `load_sorting_analyzer` — see [sorting_analyzer.md](../notes/sorting_analyzer.md)
- `SortingAnalyzer.compute("random_spikes" | "templates")`, `get_extension(...).get_data(operator="average")` — see [sorting_analyzer.md](../notes/sorting_analyzer.md)
- `spikeinterface.core.select_segment_sorting`, `BaseRecording.select_segments` — see [segment_selection.md](../notes/segment_selection.md)
- `spikeinterface.core.template_tools.get_template_extremum_channel` — see [template_extremum_channel.md](../notes/template_extremum_channel.md)

```

Here are the key files from the new project. Please advise what files I should upload as this project (Enterprise, planning hub) knowledge and how to change this project's instruction and the new project's (Pro, Claude Code execution) instruction.

---

## 🤖 Claude

*2026-05-23T19:58:18.666484Z*

 # Recommendation: keep both projects, with sharper handoff hygiene

After reading the new project's files, the answer is clearer than before. **The new project is materially more advanced than I assumed in the last response.** It has a real `CLAUDE.md`, a working session-1 loader, validation figures completed, a roadmap with phase gates, and a notes/session-plans discipline already running. That changes the recommendation in two ways:

1. **Don't merge.** The new project's structure is exactly what Claude Code projects should look like, and dragging in this project's legacy MATLAB context would dilute it. The clean split is correct.
2. **The new project's project_instructions.md is also exactly right for what it is — a planning hub.** You don't actually have a planning-hub-vs-code-execution split; you have two near-identical planning hubs, one with Code access and one without. That's the actual redundancy to address.

Below is what I'd actually do.

## What the new project already is

Reading the uploaded files: project_instructions.md, CLAUDE.md, roadmap.md, the notes, the session plans. The new project on the Pro account is already operating as a hybrid — both planning and execution. project_instructions.md explicitly says "Claude Code does the implementation; this project does the thinking that precedes and follows it." So the Pro account project is the planning workspace *and* it spawns Claude Code sessions from the same laptop.

This means the real question isn't "planning hub vs execution hub." It's: **what does this Enterprise project add that the Pro project doesn't already have?**

Three honest answers:

- **Higher message limits and longer context windows on Enterprise** for the heavy synthesis work (deep research reports, multi-document architecture chats, long literature triangulations). The Pro project will hit limits on those.
- **A staging ground for the legacy MATLAB context** that shouldn't pollute the Pro project's knowledge base. The four MATLAB scripts in this project are reference material for design, not code-generation input.
- **Cross-checking and second opinions.** Pasting a session outcome here for a sanity check against a different conversation history is a real workflow.

That's enough to justify keeping this project, but it changes what to put in it.

## What to upload to this project (Enterprise planning hub)

Upload selectively. The Pro project has 9+ knowledge files; copying them all here defeats the purpose. Upload only what's needed for the work this project actually does.

**Upload (lightweight reference set):**

- `CLAUDE.md` — the policy file. Needed for any architecture or design discussion to be grounded in the same conventions Claude Code will follow.
- `roadmap.md` — the phase plan. Needed for phase-review chats and for sequencing.
- `pyproject.toml` — dependency pins. Needed for any "which SI version handles X" question.
- `project_instructions.md` from the Pro project — for cross-reference, so you can see when the two project instructions drift apart.

That's it for the standing set. Four files. Re-upload when materially changed (not after every session — that's churn).

**Upload per-chat, not standing:**

- The specific `session_planNN_*.md` file for the next session you're planning.
- The specific `docs/notes/<topic>.md` files relevant to the current architecture discussion.
- The MATLAB legacy scripts when (and only when) the current chat is about migrating a specific behavior from them.

**Do not upload:**

- The deep research reports (the four `compass_artifact_*.md` files). These are dense reference material. Keep them in the Pro project where Claude Code can read them during sessions. Re-uploading them here just consumes context budget on every message in every chat.
- The scratch Python files. They're snapshots of what Claude Code produced; they belong in the repo, not in planning context.
- The full notes/ directory. Upload individual notes per chat when relevant.

The rule: this project's knowledge is the **stable framing layer**. Per-chat uploads are the **specific context** for that conversation. Don't confuse the two.

## How to change this project's instructions

The current project_instructions in this Enterprise project is a 400+ line domain spec — Blackrock SDK details, sorter comparison tables, GPU memory budgets, file-format priorities. It's an artifact from when this was going to be the primary development environment. It's now redundant with the Pro project's CLAUDE.md and counterproductive (it consumes context, and it duplicates rules that should have a single source of truth).

Replace it with something much shorter, focused on what this project actually does. Roughly:

```
This project is the Enterprise planning hub for the `recqual` 
SpikeInterface pipeline. The implementation lives in a separate 
Claude Code project on a Pro account; that project's CLAUDE.md, 
roadmap.md, and project_instructions.md are uploaded to this 
project's knowledge as the authoritative reference.

Use this project for:
- Long architecture discussions that would exhaust Pro context limits
- Literature triangulation and deep research synthesis
- Cross-checking session outcomes from the Pro project
- Reasoning about legacy MATLAB behavior to inform Python migration

Do not use this project for:
- Generating production code (that's Claude Code)
- Replacing CLAUDE.md or roadmap.md (the Pro project's files win)
- Per-session planning that the Pro project handles directly

[Then paste the user's communication preferences and how-to-think 
sections from the Pro project's project_instructions.md verbatim, 
so the two projects respond in the same voice.]

When advising on code, architecture, or sorter policy, defer to 
the uploaded CLAUDE.md and roadmap.md as authoritative. If chat 
conclusions conflict with those files, the files win unless the 
user is explicitly proposing a change to them.
```

That's the whole instruction. The domain details (Blackrock SDK calls, GPU budgets, NWB schema) live in CLAUDE.md, which is in the knowledge base. No duplication.

## How to change the Pro project's instructions

Minimal changes. The current project_instructions.md is well-designed for what it does. Two small additions:

1. **Acknowledge the Enterprise hub exists.** One sentence at the top: "A parallel Enterprise project handles long-form architecture and research synthesis; conclusions from there return as updates to CLAUDE.md, roadmap.md, or docs/notes/. This project remains authoritative for code and session execution."

2. **Define the handoff format.** When you bring a conclusion back from the Enterprise project to the Pro project, what does it look like? Recommend: a single markdown block pasted into the relevant chat, structured as "Decision / Rationale / Files to update / Files to upload to Claude Code." This forces the Enterprise discussion to produce something actionable, not just exploratory.

That's it. Don't restructure the Pro project's instructions — they're working.

## A few specific observations from reading the files

These are independent of the project-structure question but worth flagging since I read everything:

**The MATLAB legacy scripts and the new pipeline are not as overlapping as you might think.** The four MATLAB files do unit-count and amplitude aggregation across longitudinal sessions, with coating-type comparisons and impedance correlation. The new Python pipeline goes much further — multi-sorter consensus, quality metrics, segment handling, agreement matrices. The MATLAB code is best viewed as *what the analysis used to produce* (a target the new pipeline must match or exceed), not as a foundation to migrate function-by-function. The `eval(strcat(...))` patterns, date-versioned scripts, and `caxis` issues from the legacy code are warnings about what not to repeat, not migration targets.

**Phase 1 sub-phase 1c (scaling from 5 sessions to 60) is the highest-risk sub-phase in the roadmap.** This is where most pipelines break — caching, runtime budget, error recovery, parallelism all compound. The "extensive validation" risk you've already flagged in 1d is real, but 1c is where you'll discover whether the architecture decisions made in 1a actually hold. Worth writing a 1c-specific spec before that session, similar to the phase 1 validation spec already planned.

**The "Plexon comparison sub-cohort" open question (pre-session-6) is more important than its current placement suggests.** If Plexon-sorted data exists only on a subset, the entire Phase 1 validation strategy needs to handle two cohorts: the Plexon-comparable subset (for cross-validation against an external reference) and the larger longitudinal cohort (for trends only). That's a phase-level decision, not a session-level one. Worth resolving before S6.

**One inconsistency between the two projects' instruction files:** this project's instructions specify 96-channel Utah arrays as primary with 300-channel Neuropixels as secondary; the Pro project's CLAUDE.md scopes to Utah (16, 96) and NeuroNexus (16, 64) and explicitly says "not Neuropixels-class." Pick one. The Pro project's scope is the more accurate description of what you're actually building; this project's instructions should match.

---

## 🧑 Human

*2026-05-23T20:06:45.199794Z*

What would I use the Pro's project for?

---

## 🤖 Claude

*2026-05-23T20:07:16.107314Z*

 # What the Pro project is actually for

Honest answer after re-reading the files: **the Pro project's job is to host Claude Code sessions, and almost nothing else.**

The project_instructions.md in the Pro project describes it as a "design partner and planning workspace" with elaborate chat-type conventions (Session planning, Architecture & design, SI literacy, Phase review, Debug). On paper, the Pro project does a lot.

In practice, you have Enterprise. Enterprise does all of those things better:

- Higher message limits for long architecture chats
- Bigger context windows for multi-document synthesis
- Better suited to literature triangulation, deep research, phase reviews

So the planning, design, and literacy chats the Pro project was designed for are exactly the chats that should migrate to Enterprise.

What's left for the Pro project?

## What only the Pro project can do

**Claude Code.** That's the unique capability. Pro gives you Claude Code access; Enterprise on your current plan doesn't. Everything else the Pro project's instructions describe can be done elsewhere, but Claude Code sessions have to launch from somewhere with Pro access.

That makes the Pro project's actual job narrow:

1. **Pre-session prompt staging.** You draft the session plan in Enterprise (where the long context and uploaded research live), then paste the resulting bounded prompt into a Pro project chat as the launching point for the Claude Code session.

2. **Claude Code session orchestration.** The actual interactive Claude Code work — running tests, editing files, debugging, iterating — happens in the Pro project context because that's where Claude Code runs.

3. **Immediate post-session capture.** When the Claude Code session ends, the session_plan outcome section gets written in the Pro project (because that's where the artifacts and session memory are freshest), then synced to git.

4. **Short, fast debugging chats.** When something breaks mid-session and you need a 5-message exchange to unstick it, doing that in the same Pro project chat where Claude Code is running is faster than switching to Enterprise.

That's the entire role. The Pro project is a Claude Code launchpad with minimal supporting chat.

## What this means for the Pro project's instructions

The current project_instructions.md is over-scoped for what the Pro project will actually do. It defines five chat types (Session planning, Architecture & design, SI literacy, Phase review, Debug). Of those, only "Session planning" (in the narrow sense of staging the prompt) and "Debug" (in the narrow sense of unsticking a Claude Code session) actually belong there. The other three should move to Enterprise.

Concretely, the Pro project's instructions should shrink to something like:

```
This project is the Claude Code launchpad for the `recqual` 
pipeline. Architecture, design discussions, literature 
triangulation, and phase reviews happen in a parallel Enterprise 
project. This project handles only:

1. Session prompt staging — converting a session plan drafted in 
   Enterprise into a bounded plan-mode prompt for Claude Code.
2. Active Claude Code sessions — the implementation work itself.
3. Immediate post-session capture — writing the session_plan 
   outcome before context fades.
4. Short debugging exchanges when a Claude Code session is stuck.

Do not do long architecture chats, SI literacy explorations, or 
phase reviews here. Redirect those to the Enterprise project. If 
a chat here is producing more than ~20 lines of non-code 
exposition, that's a signal to move it.

[CLAUDE.md is the authoritative policy file for code conventions. 
Refer to it for any code-related question.]

[User's communication preferences here, same as Enterprise.]
```

Most of the existing chat-type machinery (Architecture & design chats, SI literacy chats, Phase review chats) was designed for a project that was going to be everything. It's no longer that project. Removing those sections sharpens the focus and prevents you from accidentally starting an architecture chat there when it should be in Enterprise.

## What this means for the Enterprise project

The Enterprise project absorbs everything the Pro project was over-scoped to do:

- Architecture and design chats
- SI literacy chats
- Phase review chats
- Literature and deep research synthesis
- Anything requiring long context windows or extended back-and-forth

The Enterprise instructions I sketched in the previous response need one addition then: explicit chat-type conventions, copied from the Pro project's instructions but with Session-planning and Debug removed. Those two chat types stay on the Pro side.

## The honest summary

You don't have a planning-hub vs execution-hub split. You have an Enterprise planning hub and a Pro Claude Code launchpad. The Pro project is small. That's fine — Claude Code is doing the work, and the Pro chat surrounding it is just glue.

The mistake to avoid is over-using the Pro project out of habit. If a question takes more than a few messages, or requires uploaded research, or benefits from a long context window, it belongs in Enterprise. The Pro project is for the actions Claude Code needs to take next.

---

## 🧑 Human

*2026-05-23T20:10:21.659606Z*

Please generate the Enterprise project instruction with all the modifications you suggested.

---

## 🤖 Claude

*2026-05-23T20:11:24.160982Z*

 ```markdown
# Project: recqual planning hub (Enterprise)

## What this project is

Enterprise-side planning workspace for the `recqual` SpikeInterface
pipeline. The implementation lives in a parallel Claude Code project on
a Pro account; that project's `CLAUDE.md`, `roadmap.md`, and
`project_instructions.md` are uploaded to this project's knowledge as
the authoritative reference for code conventions, sorter policy, phase
sequencing, and data conventions.

This project hosts the work that benefits from Enterprise's longer
context windows and higher message limits: long-form architecture
discussions, literature triangulation, phase reviews, SpikeInterface
literacy, and cross-checking session outcomes. The Pro project handles
session prompt staging, Claude Code execution, and immediate
post-session capture.

Package name: `recqual`. Hardware: Blackrock / Ripple Neuro acquisition,
Utah arrays (16, 96 ch) and NeuroNexus linear / multi-shank probes
(16, 64 ch). Sparse / low-density geometries, not Neuropixels-class.
Primary goal: identify objective, practical metrics for longitudinal
recording quality assessment. Secondary goal: integrate with future
multimodal data (electrode impedance, endpoint histology, longitudinal
in vivo imaging).

## About the user

Scientist with doctoral training, cross-domain background in medicine,
engineering, industry, and science. Comfortable with technical
language, statistical reasoning, and primary literature conventions in
training areas; will flag when a more introductory explanation is
wanted. New to Python relative to MATLAB and new to Claude Code.
Working solo for now, but the pipeline will be handed to new students
and collaborators, so handoff-readiness matters.

## Communication preferences

- Skip preambles and restated questions. Get to substance immediately.
- Use specific numbers, named mechanisms, and concrete examples
  rather than abstractions.
- Use technical language where it's more accurate than a paraphrase.
- Default to prose. Lists only when content is genuinely enumerable.
- Match length to question complexity. Brevity by default; expand
  only when warranted.
- No em dashes. No opening adjectives about the question. No closing
  validation, hedges, or offers to elaborate. End on substance.
- If a concept might be unfamiliar (term of art, framework, named
  theory, niche jargon), flag it and add a brief inline explanation.

## How to think

The challenge is informational. Don't gatekeep, and don't manufacture
objections.

- Do not automatically agree. If reasoning is unsound, surface the
  issue and proceed with the best version of the question. If
  reasoning is sound, say so briefly and move on. Do not manufacture
  objections to perform independence.
- If a relevant factor, perspective, or alternative hasn't been
  considered, note it briefly. Surface the ones with real weight, not
  every possible consideration.
- If the user pushes back without new evidence, hold position. Update
  only on new arguments or new facts, not on displeasure.
- Do not force premature convergence. When a question has multiple
  defensible answers depending on assumptions, surface the branch
  point rather than picking one silently.
- Show 1 to 3 load-bearing reasoning steps for judgment calls. Skip
  micro-inferences.
- When pointing out reasoning issues, lead with functional analysis
  (the mechanism of what's going wrong), not the label. Named
  fallacies or biases go as parentheticals, not substitutes for the
  explanation.
- Honest uncertainty beats confident fabrication. If you do not know,
  say so.
- Ambiguous prompts: state the assumption inline and proceed. If
  genuinely underspecified, ask. If scope is ambiguous, ask before
  generalizing.
- When technical terms have different meanings across fields (e.g.,
  "objective" in optics vs. epistemics, "signal" in
  electrophysiology vs. statistics), name the sense being used.

## Citations and sources

When citing a study, give enough detail (authors, year, journal) to
locate it. Distinguish sourced claims, derived claims, and informed
guesses. For numerical claims (dates, dollar amounts, statistics,
deadlines, measurements, citations), cite a source or flag the value
as estimated, computed, or from memory. Do not invent precision.

## Defaults

- Dates ISO-8601 with timezone where relevant.
- SI units for physical measurements unless specified otherwise; flag
  explicitly when mixing systems.
- Code blocks include language and filename when applicable.

## Project knowledge files

The standing knowledge in this project is intentionally minimal. Four
files form the stable reference layer:

- `CLAUDE.md` (from the Pro project): authoritative policy file for
  code conventions, sorter policy, data conventions, segment handling,
  file layout. When a question's answer depends on a project rule,
  check `CLAUDE.md` first.
- `roadmap.md` (from the Pro project): phase plan and session
  sequence. Authoritative for "what phase are we in" and "what comes
  next."
- `pyproject.toml` (from the Pro project): dependency pins and package
  metadata.
- `project_instructions.md` (from the Pro project): so the two
  projects' instructions can be cross-checked for drift.

Treat these as authoritative. If a chat's content conflicts with them,
the files win unless the user is explicitly proposing a change. When
the user asks for revisions to `CLAUDE.md`, `roadmap.md`, or
`pyproject.toml`, generate the full revised file; do not produce
diffs.

Re-upload the standing files when materially changed, not after every
session.

Per-chat uploads (not standing knowledge): the specific
`docs/session_plans/sessionNN_*.md`, `docs/notes/<topic>.md`,
`docs/phase_plans/phaseN_*.md`, deep research reports, or legacy
MATLAB scripts relevant to the current discussion. Upload at chat
start; do not assume persistence across chats.

## Chat type conventions

Chats in this project are organized by purpose. The chat title usually
signals the type. The chat types here are the ones that benefit from
Enterprise's context and message budget; session prompt staging,
Claude Code execution, and immediate post-session capture belong in
the Pro project.

### Architecture and design chats ("Design: <topic>")

Long-lived chats on cross-cutting topics: multi-sorter consensus
methodology, multimodal schema design, MATLAB interop, longitudinal
aggregation strategy, validation strategy. Conclusions land in
`docs/notes/` and update `CLAUDE.md` when policy-level. One chat per
topic, not one per question. Output a structured handoff block
(Decision / Rationale / Files to update / Files to upload to Claude
Code) when the discussion produces something actionable for the Pro
project.

### SI literacy chats ("SI: <subsystem>")

Conceptual questions about SpikeInterface organized by subsystem
(extractors, preprocessing, sorters, postprocessing and
SortingAnalyzer, quality metrics, curation, comparison). Goal: the
user's working understanding, not implementation. Conclusions land in
`docs/notes/<function_or_concept>.md`. Distinct from Claude Code's
in-session "explain this function" because here the explanation is
for the user's mental model, not for the next code generation step.

### Phase review chats ("Phase N: review and plan")

End-of-phase synthesis chats. Inputs: the phase's session_plans, the
phase validation spec, the actual outcomes. Outputs:
`docs/phase_plans/phaseN_summary.md` and the rough session sequence
for Phase N+1. Update `roadmap.md` if the phase experience suggested
changes for downstream phases.

### Research synthesis chats ("Research: <topic>")

Literature triangulation, deep research report review, primary
literature reading. Outputs land in `docs/notes/` or in updates to
`CLAUDE.md`'s policy sections (e.g., sorter exclusions backed by
specific papers).

### Cross-check chats ("Cross-check: <session or decision>")

Sanity-checking a Claude Code session outcome or a Pro project
decision against this project's separate context. Useful when the Pro
project's chat history is biased toward one trajectory and a fresh
read is wanted.

### Legacy MATLAB chats ("Legacy: <behavior>")

Reasoning about specific behaviors in the old MATLAB scripts to inform
Python migration. Upload the relevant `.m` files per chat. Output:
notes on what the legacy code produced (as a migration target) and
what to deliberately not replicate (the `eval(strcat(...))` patterns,
date-versioned scripts, `caxis` issues, etc.).

## Handoff format to the Pro project

When a chat here produces something actionable for the Pro project,
end the chat with a structured handoff block:

```
## Handoff to Pro project

Decision: <one sentence>

Rationale: <2 to 5 sentences with load-bearing reasoning>

Files to update:
- <path>: <what changes>
- <path>: <what changes>

Files to upload to Claude Code:
- <path or filename>

Next session implication: <one sentence, or "none">
```

This forces the discussion to produce something the Pro project can
act on, not just exploratory chat. Without this, conclusions get lost
in chat history and never reach the code.

## What this project is not for

- Generating production code. That happens in Claude Code via the Pro
  project. If a chat here starts producing more than ~20 lines of
  code, redirect to a Claude Code session via the Pro project.
- Session prompt staging. The Pro project does that, because the
  prompt has to launch from the same context Claude Code runs in.
- Active debugging of a Claude Code session. The Pro project handles
  short debugging exchanges that need the live session context.
- Running tests or analysis. No tool access here beyond search and
  file generation.
- Replacing `CLAUDE.md` or `roadmap.md`. If a decision is durable, it
  goes into a file in the Pro project's repo, not into chat history
  here.

## Defaults when in doubt

- Recommend writing durable conclusions to `docs/notes/` (in the Pro
  project's repo) rather than emitting them inline.
- Recommend Claude Code plan mode for any non-trivial code change.
- Recommend MountainSort5 for Phase 1 sorter work unless the
  discussion is explicitly about sorter choice.
- Recommend pandas DataFrames in long format for analysis outputs the
  user will inspect in a variable explorer.
- When the user uploads a revised `CLAUDE.md`, `roadmap.md`, or
  `pyproject.toml`, treat the upload as the new authoritative version
  and update advice accordingly.
- If a chat is producing more than ~20 lines of code or starting to
  feel like session execution rather than planning, recommend moving
  to the Pro project.
```

A few notes on what changed and why, since the document is long.

The original Enterprise instructions were a 400-line domain spec (Blackrock SDK details, sorter comparison tables, GPU memory budgets, file-format priorities). All of that is in CLAUDE.md, which is now uploaded as knowledge. Duplicating it in the instructions consumes context on every message and creates two sources of truth. Removed.

The chat-type conventions came from the Pro project's instructions, with two modifications. First, removed Session planning and Debug chat types (they live in the Pro project now). Second, added Research synthesis, Cross-check, and Legacy MATLAB chat types, which are the work this project uniquely does.

The handoff format is new. The Pro project's current instructions don't define how conclusions return from external discussions. Without a forcing function, architecture conversations here will produce insight that never reaches CLAUDE.md or the code. The structured block makes that drift visible.

The communication and how-to-think sections are largely copied from your user preferences, lightly reconciled with the Pro project's existing instructions so the two projects respond in the same voice. If you want them tighter or want to omit anything you'd rather not duplicate across both projects, that's an easy edit.

---

## 🧑 Human

*2026-05-24T03:42:19.159414Z*

Why not upload the deep research reports? I understand Re-uploading them here just consumes context budget on every message in every chat. But they contain important and detailed background information on the sorters, the metrics.

---

## 🤖 Claude

*2026-05-24T03:42:51.098633Z*

 You're right to push back. Let me reconsider.

## What I got wrong

The objection I raised — "they consume context budget on every message" — applies to *any* uploaded file, including CLAUDE.md and roadmap.md. I drew an arbitrary line at "these are too dense" without justifying why density specifically disqualifies them. That's not a real argument.

The real question is: **what do you reach for those reports to answer?** If the answer is "questions that come up often enough that re-uploading per chat is friction," they belong in standing knowledge. If the answer is "occasional deep dives," per-chat upload is fine. I assumed the latter without checking.

Given what the reports are (sorter benchmarking literature, quality metrics definitions and validation, longitudinal QC methodology, likely one more) and what this project's chat types are (Architecture and design, SI literacy, Research synthesis, Phase reviews), those reports are load-bearing for most chats here. They're not occasional reference. They're the substrate for the kind of conversations this project exists to host.

That tips the balance toward uploading them.

## The real tradeoff

Anthropic doesn't publish a hard knowledge-base size limit for Projects, but in practice there's a soft ceiling where retrieval quality degrades and per-message context cost climbs. With four small policy files (CLAUDE.md, roadmap.md, pyproject.toml, project_instructions.md), you're well under any threshold. Adding four deep research reports — each plausibly 5,000 to 15,000 words — moves you into a different regime.

The actual costs:

- **Per-message context overhead.** Larger knowledge bases mean more tokens spent on retrieval and grounding per turn, which can crowd out the working context for the actual conversation.
- **Retrieval noise.** When the knowledge base is small and tightly scoped, the model reliably grounds on the right file. When it's large and topically diverse, retrieval can pull the wrong section into a response. This matters more for policy questions ("what does CLAUDE.md say about X") than for synthesis questions where you want broad grounding.
- **Staleness risk.** Deep research reports are dated artifacts. If a sorter benchmark updates or a metric's recommended threshold changes, the report stays stale until you re-run the research. Standing knowledge that's stale is worse than per-chat uploads of the current version, because the stale standing version influences every chat silently.

The actual benefits:

- **No re-upload friction.** Significant if you'd otherwise upload them in 50%+ of chats.
- **Cross-report synthesis.** Questions like "do the multi-sorter consensus findings in report A square with the quality-metric validation in report B" need both reports in context simultaneously, which is more natural with standing knowledge than per-chat upload.
- **Background grounding for SI literacy chats.** When you ask about a SpikeInterface function, having the sorter and metrics literature already grounded means the answer can reference what actually matters for your hardware, not generic SI documentation.

## What I'd actually recommend

Upload them, with two adjustments to mitigate the costs.

**One.** Add a short "research reports" section to the project instructions naming each report's scope, date, and what questions it's authoritative for. This gives the model a routing layer so it knows which report to ground a given question against, rather than scanning all four for every query. Something like:

```
## Deep research reports in knowledge

These are background reference, not policy. CLAUDE.md and roadmap.md
override them when in conflict.

- `sorter_benchmarks_<date>.md`: sorter selection rationale, 
  algorithm comparisons, known failure modes. Authoritative for 
  "which sorter for which probe geometry."
- `quality_metrics_<date>.md`: SI quality metric definitions, 
  validation studies, threshold recommendations. Authoritative for 
  "what does metric X measure and what's a reasonable threshold."
- `<third report scope>`
- `<fourth report scope>`

If a report conflicts with CLAUDE.md, flag the conflict and ask 
whether CLAUDE.md should be updated.
```

**Two.** Treat them as versioned. When a report gets superseded by new research or by accumulated `docs/notes/` content, retire it from the knowledge base. The risk isn't uploading research; it's letting stale research silently shape advice. A one-line "last reviewed: <date>" at the top of each report, and a quarterly check on whether they're still current, handles this.

The MATLAB scratch files are still per-chat uploads — they're code artifacts, not reference. The session_plans and notes are still per-chat uploads — they're working documents that change too fast for standing knowledge. But the deep research reports are the right kind of artifact for standing knowledge: dense, stable for months at a time, and load-bearing for the conversations this project hosts.

Good catch.

---

## 🧑 Human

*2026-05-24T03:48:35.672681Z*

You can access the four compass artifacts in this chat, the fourth one is supposed to be integration of all three previous reports. Please go through them and write an updated project instruction section.

---

## 🤖 Claude

*2026-05-24T03:50:00.123706Z*

 

```json
// tool_use: view
{
  "description": "Read first compass artifact to understand scope and date",
  "path": "/mnt/user-data/uploads/compass_artifact_wf-b65651f6-f662-4c2e-a081-5a005685b772_text_markdown.md",
  "view_range": [
    1,
    60
  ]
}
```

```json
// tool_result
[
  {
    "type": "text",
    "text": "     1\t# Comparative Review of Spike Sorting Algorithms Supported by SpikeInterface and Benchmarked by SpikeForest\n     2\t\n     3\t## TL;DR\n     4\t- **Kilosort4 (Pachitariu, Sridhar, Pennington & Stringer, Nat Methods 2024, 21:914–921) is the current default first choice for any high-density linear probe with potential drift (Neuropixels 1.0/2.0, dense linear or planar arrays).** Across the authors' simulation suite — drawn from IBL Neuropixels data with 600 ground-truth + 600 multi-units per ~45-min recording — Kilosort4 \"consistently performed better\" than KS2.5/KS3 in all drift conditions and recovered 80–90% of units where IronClust recovered ~50%; Kilosort2/2.5/3/4 all outperformed every non-Kilosort algorithm tested.\n     5\t- **For low-channel-count, sparse, or non-drifting recordings (tetrodes, Utah arrays, micro-wire bundles, single channels) the field's empirical conclusion (Magland et al., eLife 2020, e55167; Buccino et al., eLife 2020, e61834) is that no single sorter dominates.** MountainSort4/5 (Chung et al., Neuron 2017, 95:1381–1394) excels on monotrodes/tetrodes, IronClust (Jun et al., bioRxiv 2017, doi:10.1101/101030) is competitive across nearly every study set, Wave_clus (Chaure, Rey & Quian Quiroga, J Neurophysiol 2018, 120:1859–1871) remains the standard for human/micro-wire single-channel data, and Combinato (Niediek et al., PLOS ONE 2016, 11:e0166598) is the strongest choice for multi-hour clinical recordings.\n     6\t- **Several formerly important sorters are deprecated, legacy, or unmaintained as of May 2026** — YASS, Klusta, the original Tridesclous (v1) and SpyKING CIRCUS (v1) have been moved to SpikeInterface's \"legacy\" list; HDSort and the MATLAB Kilosort 1/2/2.5/3 lines no longer receive in-depth developer support (\"we are no longer providing in-depth support for Kilosort 1-3\", MouseLand/Kilosort README). The SpikeInterface team's actively developed internal alternatives are SpykingCircus2, Tridesclous2, the newer \"Lupin\" (Garcia, Halcrow, Windolf, McKenzie, Adkisson-Floro, Mayorquin, Dichter, Buccino & Yger, eLife Reviewed Preprint v1, doi:10.7554/eLife.110588.1, April 2026) and \"Simple\" sorters, all built on the modular `spikeinterface.sortingcomponents` API.\n     7\t\n     8\t---\n     9\t\n    10\t## Key Findings\n    11\t\n    12\t1. **The field has split into three durable families.** (i) The Kilosort family (template-learning + matching pursuit, GPU) dominates for dense linear silicon probes with drift. (ii) The density/graph-based family (MountainSort, IronClust, HerdingSpikes2) dominates for low-channel-count or planar/CMOS-MEA recordings without strong rigid drift. (iii) The classical wavelet/SPC family (Wave_clus, Combinato) dominates for monotrodes and human micro-wire recordings, especially over multi-hour timescales.\n    13\t\n    14\t2. **Drift handling is now the single most important axis of differentiation.** Only Kilosort 2.5/3/4, IronClust, and (recently) the SpikeInterface motion-correction front-end (DREDge, MEDiCINe, Kilosort-datashift) implement explicit drift correction. Pachitariu et al. (2024) showed that under the simulation conditions tested in the Kilosort4 paper, SpyKING CIRCUS and MountainSort4 matched IronClust at low/medium drift but their performance \"deteriorated drastically with higher drift\", whereas Kilosort 2.5/3/4 maintained accuracy.\n    15\t\n    16\t3. **Maintenance status has shifted dramatically since 2023.** The original SpyKING CIRCUS v1, Tridesclous v1, and YASS are unmaintained; their authors (Yger, Garcia) have moved development into SpikeInterface's internal SpykingCircus2/Tridesclous2 sorters. The Pachitariu lab now formally declines to support Kilosort 1/2/2.5/3 (\"we are no longer providing in-depth support for Kilosort 1-3\", MouseLand/Kilosort README). pyKilosort exists but is wrapped in SpikeInterface mainly for IBL legacy use. Klusta is in SpikeInterface's \"legacy\" bucket. HDSort has had no substantive activity since v1.0.1.\n    17\t\n    18\t4. **There are real, published differences in unit yield that should change interpretation.** On the Buccino et al. (2020) Allen Institute Neuropixels mouse cortex recording (15 min, 246 active channels), six sorters produced wildly different unit counts: Tridesclous 187, HerdingSpikes2 210, IronClust 233, HDSort 317, Kilosort2 446, SpyKING CIRCUS 628. Of 2,031 total units, **all six sorters agreed on only 33**, and \"two or more sorters agree on just 263 of the total units.\" Consensus (k ≥ 2 sorter) curation matches expert manual curation at the ~85–90% level, while non-consensus Kilosort2 units match curated units at only ~19–24%. This argues strongly for **multi-sorter ensemble curation** as standard practice for high-density data.\n    19\t\n    20\t5. **Several sorter-specific failure modes are now well-documented.** Kilosort family is known for **oversplitting** (mitigated in KS4 by graph clustering and cross-correlogram merge logic) and for fewer-spikes-at-batch-boundaries bugs in KS2/2.5/3 (issue #594, fixed in patch1 releases — but unpatched containers still circulate). SpyKING CIRCUS v1 tends toward **overestimation of unit count**. HerdingSpikes2 explicitly fails on probes with channel pitch > 60 μm. KS4's SpikeInterface wrapper has undergone breaking API changes (\"Kilosort4 seems to change very quickly and I seem unable to find a combination of spikeinterface/kilosort4 versions with which I do not encounter problems\" — SI issue #3901).\n    21\t\n    22\t---\n    23\t\n    24\t## Details\n    25\t\n    26\t### A. Inventory of SpikeInterface-Wrapped Sorters (as of SpikeInterface 0.104.3 / May 2026)\n    27\t\n    28\tExternal wrappers (`run_sorter(sorter_name=...)` accepts):\n    29\t`herdingspikes`, `ironclust`, `kilosort`, `kilosort2`, `kilosort2_5`, `kilosort3`, `kilosort4`, `pykilosort`, `mountainsort4`, `mountainsort5`, `rtsort`, `spykingcircus`, `tridesclous`, `waveclus`, `combinato`, `hdsort`.\n    30\t\n    31\tInternal (sortingcomponents-based) sorters: `lupin`, `spykingcircus2`, `tridesclous2`, `simple`.\n    32\t\n    33\tLegacy / no longer supported in current release: `klusta`, `yass`.\n    34\t\n    35\tTwo new wrappers in the past year referenced in the SpikeInterface release notes are **RT-Sort** (van der Molen T, Lim M, Bartram J, Cheng Z, Robbins A, Parks DF et al., PLOS ONE 2024, 19(12):e0312438; \"a spike sorting algorithm that enables the sorted detection of action potentials within 7.5 ms ± 1.5 ms (mean ± STD) after the waveform trough while the recording remains ongoing\") and **Bombcell** (Fabre JMJ, van Beest EH, Peters AJ, Carandini M & Harris KD, 2023, Zenodo doi:10.5281/zenodo.8172821 — \"Bombcell: automated curation and cell classification of spike-sorted electrophysiology data\"). MEDiCINe (Watters et al., eNeuro 2025, 12:ENEURO.0529-24.2025) is integrated as a motion-correction front-end, not a sorter.\n    36\t\n    37\t### B. Algorithmic mechanism, design intent, and probe fit — by sorter\n    38\t\n    39\t#### Kilosort family (Pachitariu lab, HHMI Janelia / Flatiron Institute)\n    40\t\n    41\tAll Kilosort versions share a common backbone: GPU-based whitening and bandpass preprocessing → **template learning** (joint detection + clustering by scaled K-means in KS1; \"drift tracking\" in KS2; modified template-learning + datashift in KS2.5; new clustering in KS3; graph-based modularity-optimisation clustering with merging tree in KS4) → **matching-pursuit template deconvolution** to recover collision spikes → post-processing merges/splits. Kilosort is \"the only major current spike-sorting platform\" that performs this template-subtraction step, allowing it \"to resolve spike collisions better than all\" others (Pachitariu et al., Nat Methods 2024).\n    42\t\n    43\t**Design intent:** awake head-fixed mouse, Neuropixels 1.0, dense linear probes with vertical pitch ≤ 40 μm. KS2.5+ expects probes with site geometry that supports sub-pixel registration; performance is best on probes ≥ 32 channels with dense spacing. CUDA NVIDIA GPU required (≥ 8 GB VRAM minimum; 12 GB+ recommended for standard 384-channel Neuropixels <3 h recording, per the Kilosort4 hardware page).\n    44\t\n    45\t| Version | First public release | Key change | Drift correction | Implementation |\n    46\t|---|---|---|---|---|\n    47\t| KS1 (Pachitariu et al., NeurIPS 2016, bioRxiv 061481) | 2016 | Scaled K-means template learning + matching pursuit | None | MATLAB + CUDA |\n    48\t| KS2 (no peer-reviewed paper) | 2018 | \"Drift tracking\" — templates modified continuously as a function of inferred drift | Template-side | MATLAB + CUDA |\n    49\t| KS2.5 (Steinmetz et al., Science 2021, 372:eabf4588 \"Neuropixels 2.0\") | 2020 | Standalone **datashift** drift correction directly modifying raw voltage data via sub-pixel registration | Data-side | MATLAB + CUDA |\n    50\t| KS3 | 2021 | \"Completely new and much more sophisticated clustering algorithm\" (per repo README); inherits KS2.5 datashift | Data-side | MATLAB + CUDA |\n    51\t| KS4 (Pachitariu et al., Nat Methods 2024, 21:914–921) | Feb 2024 | Pure-Python/PyTorch reimplementation; **graph-based clustering by modularity optimization** + merging tree using refractory-period violation and bimodality criteria; explicit convolutions replace Butterworth filtering; no intermediate processed binary required | Data-side (datashift inherited) | Python + PyTorch, NVIDIA GPU |\n    52\t| pyKilosort | 2021 (IBL-maintained) | Direct Python translation of KS2/KS2.5 kernels; primary purpose is reproducibility for IBL data | Data-side | Python + CuPy |\n    53\t\n    54\t**Known limitations / failure modes:** (a) **Batch-boundary bug** in KS2/2.5/3 producing ~7 ms gaps every 2.1866 s — fixed in patch1, but many published runs predate the fix; (b) tendency to **oversplit** (mitigated in KS4); (c) Buccino et al. (2020, eLife) reported that on simulated Neuropixels data Kilosort2 produced **147 false-positive units out of 415**, reduced to 93 with KS2's built-in contamination filter; (d) KS4's SpikeInterface wrapper has unstable API — open issue #3901 documents that KS4 returns a 4-element tuple where SI expects 2; (e) Kilosort4 paper notes some false-positive results in the SpikeInterface paper (their Extended Data Fig. 3) \"are due to unrealistically long spike durations\" in MEArec simulations — a methodological dispute that should affect how you interpret the SI 2020 comparison.\n    55\t\n    56\t#### MountainSort family (Magland, Chung, Barnett — Flatiron Institute)\n    57\t\n    58\t**Algorithm (MS4, Chung et al., Neuron 2017, 95:1381–1394):** event detection by absolute amplitude threshold per channel → PCA feature extraction on detected events sparsified to local neighborhoods (adjacency_radius) → **Isosplit** non-parametric density-based clustering (Magland & Barnett 2015) that performs binary splits based on a 1-D dip-statistic test, recursively, without requiring K. CPU-only; \"no parameters to tune\" is the design philosophy.\n    59\t\n    60\t**MountainSort5 (flatironinstitute/mountainsort5, 2023):** complete rewrite using SpikeInterface I/O. Three sorting schemes — Scheme 1 single-pass; Scheme 2 catalog-then-classify (handles longer recordings); Scheme 3 chunked with time-segment annealing (handles drift). Uses isosplit6 (later isosplit clustering). \"Runs faster than previous versions, especially for large channel counts; better handles time-overlapping events and drifting waveforms; runs fast on CPU\" (repo README). The subdivision clustering recursively splits and re-extracts PCA features within each subdivision (mountainsort5/docs/scheme1.md).\n[336 lines total]",
    "uuid": "1d663eab-78ca-42ba-9e18-c97d08b29bf1"
  }
]
```

```json
// tool_use: bash_tool
{
  "command": "wc -l /mnt/user-data/uploads/compass_artifact_wf-*.md",
  "description": "Count lines in all four compass artifacts"
}
```

```json
// tool_result
[
  {
    "type": "text",
    "text": "{\"returncode\":0,\"stdout\":\"   361 /mnt/user-data/uploads/compass_artifact_wf-304f2c30-adfe-4c9d-bcdd-f351919f45b8_text_markdown.md\\n   335 /mnt/user-data/uploads/compass_artifact_wf-b65651f6-f662-4c2e-a081-5a005685b772_text_markdown.md\\n   297 /mnt/user-data/uploads/compass_artifact_wf-bc837855-2750-4608-872e-7f4f5013a417_text_markdown.md\\n   444 /mnt/user-data/uploads/compass_artifact_wf-faf36b4c-f9cb-4c91-ace6-036c77a1a6e1_text_markdown.md\\n  1437 total\\n\",\"stderr\":\"\"}",
    "uuid": "6e8376a6-d551-4b25-a1d3-37539b4ac0ce"
  }
]
```

```json
// tool_use: view
{
  "description": "Read title and TLDR of second compass artifact",
  "path": "/mnt/user-data/uploads/compass_artifact_wf-bc837855-2750-4608-872e-7f4f5013a417_text_markdown.md",
  "view_range": [
    1,
    30
  ]
}
```

```json
// tool_result
[
  {
    "type": "text",
    "text": "     1\t# Post-Sorting Curation for Extracellular Spike Sorting: A Comparative Reference\n     2\t\n     3\t*Companion to the sorting-algorithms reference. Scope: rule-based curators, ML classifiers, quality-metric frameworks, manual GUIs, and cell-type classifiers — with formulas, thresholds, failure modes, and probe-specific guidance.*\n     4\t\n     5\t---\n     6\t\n     7\t## TL;DR\n     8\t\n     9\t- **For SpikeInterface-based longitudinal Neuropixels pipelines**: layer (1) Bombcell or Allen-style threshold curation to kill noise/non-somatic units, (2) UnitRefine (random-forest, two-stage noise-vs-neural then SUA-vs-MUA) for SUA/MUA refinement, and (3) the SpikeInterface `qualitymetrics` module to attach per-unit scores for downstream filtering — keep manual review (Phy or SortingView) only for ambiguous/scientifically-critical units. UnitRefine reaches ~83% balanced accuracy vs human curators (Jain et al., bioRxiv 2025.03.30.645770) and Bombcell exposes interpretable thresholds you can lock across sessions for longitudinal consistency.\n    10\t- **Metrics that matter most for longitudinal yield stability**: amplitude_median (µV), presence_ratio, drift_ptp/std/mad, sliding-RP contamination (Llobet 2022 / IBL), and per-channel SNR. Avoid PC-based metrics (isolation_distance, L-ratio, nn_*) as primary filters on Kilosort outputs — they depend on the sorter's PC features and are biased by template-matching artifacts; use them as secondary signals only.\n    11\t- **Probe-type matters**: thresholds tuned on Neuropixels (e.g., Bombcell defaults amplitude_median ≥ 30 µV, snr ≥ 5, presence_ratio ≥ 0.7, rp_contamination ≤ 0.1) systematically over-reject low-density data; for **Utah arrays / NeuroNexus / tetrodes**, drop the amplitude floor, relax non-somatic shape rules (designed against Neuropixels somatic templates), and prefer UnitRefine with a probe-matched pretrained model or retrained classifier rather than threshold-based Bombcell defaults.\n    12\t\n    13\t---\n    14\t\n    15\t## Key Findings\n    16\t\n    17\t1. **Two paradigms have converged**. Threshold-based (Bombcell, IBL, Allen ecephys, SpikeInterface defaults) and ML-classifier (UnitRefine) approaches both consume the same SpikeInterface `qualitymetrics`/`template_metrics` feature set. As of SpikeInterface 0.104, both Bombcell labels and UnitRefine labels are first-class functions in `spikeinterface.curation`, returning per-unit labels in a pandas DataFrame (\"Automatic labeling units after spike sorting\" tutorial, SpikeInterface 0.104 docs).\n    18\t2. **Bombcell is the most mature interpretable curator**: 17 metrics, four-class output (good / MUA / noise / non-somatic), MATLAB + Python ports, validated on Neuropixels 1.0/2.0 + Kilosort; published as Fabre, van Beest, Peters, Carandini & Harris (Zenodo DOI 10.5281/zenodo.8172821, v1.7.0 Nov 2024; manuscript still in preparation as of GitHub README, May 2026).\n    19\t3. **UnitRefine is the most general ML curator**. Authors: Anoushka Jain, Robyn Greene, Chris Halcrow, Jake A. Swann, Alexander Kleinjohann, Federico Spurio, Severin Graff, Alejandro Pan-Vazquez, Björn Kampa, Juergen Gall, Sonja Grün, Olivier Winter, Alessio Buccino, Matthias H. Hennig, Simon Musall (bioRxiv 2025.03.30.645770, Mar 2025). Random-forest classifiers trained on multi-curator labels generalize across Neuropixels, Utah arrays, wire bundles, mice/rats/mole-rats/macaques/humans. On a brain-wide dataset, \"UnitRefine doubled single unit yield and improved behavioral decoding performance\" (abstract verbatim).\n    20\t4. **Allen Institute defaults (Siegle et al. 2021, *Nature* 592:86) remain the de-facto baseline**: per the original paper, filtering based on `ISI violations < 0.5`, `amplitude cutoff < 0.1`, and `presence ratio > 0.95`. These were tuned on Kilosort2 + Neuropixels 1.0 in passive visual cortex; Siegle 2021 yielded over 40,000 units passing quality control across more than 14 brain regions and 4 mouse lines (the often-quoted \"~100,000\" figure refers to pre-QC recorded neurons). They are well-documented to over-include MUA in higher-firing-rate regions and to depend on whether template-scaling or raw amplitudes are used.\n    21\t5. **IBL pipeline** (figshare 19705522 v4 white paper) uses three orthogonal \"bitwise\" criteria: `slidingRP_viol == 1`, `noise_cutoff` Z-score test pass, and `amplitude_median ≥ 50 µV`. A unit is \"good\" iff all three pass; this is the criterion behind `clusters.metrics.label == 1`.\n    22\t6. **Cell-type classification (C4, Beau et al. *Cell* 2025; Bombcell ephys-properties module) is a separate downstream step**, not curation. C4 reports >95% accuracy in cerebellum across labs/probes/species using a semi-supervised deep classifier on waveform + ACG statistics; it does not curate noise.\n    23\t\n    24\t---\n    25\t\n    26\t## Details\n    27\t\n    28\t### 1. Rule-Based Automated Curators\n    29\t\n    30\t#### 1.1 Bombcell (Fabre et al.)\n[298 lines total]",
    "uuid": "762e9365-3858-4d5d-ac07-0e7a6734b4ec"
  }
]
```

```json
// tool_use: view
{
  "description": "Read title and TLDR of third compass artifact",
  "path": "/mnt/user-data/uploads/compass_artifact_wf-faf36b4c-f9cb-4c91-ace6-036c77a1a6e1_text_markdown.md",
  "view_range": [
    1,
    30
  ]
}
```

```json
// tool_result
[
  {
    "type": "text",
    "text": "     1\t# Sorting-Free Metrics for Offline Longitudinal Tracking of Extracellular Recording Quality (Part 3 of 3)\n     2\t\n     3\t## TL;DR\n     4\t\n     5\t- **For chronic implants, the most reproducible longitudinal recording-quality scaffold is a four-metric core computed *before* spike sorting:** (i) noise floor V_RMS estimated from pre-event samples or MAD; (ii) Active Electrode Yield (AEY) = fraction of electrodes with threshold-crossing rate ≥ 2 Hz at −4.5 × robust σ (the BrainGate convention); (iii) per-electrode unsorted peak-to-peak voltage on the top 2 % of snippets (Hughes 2021 convention); and (iv) 1 kHz electrode impedance.\n     6\t- **Sorting-free metrics complement, not replace, sorter-based QC:** they detect dead/degrading channels and noise-floor drift that sorters silently absorb, while Bombcell/UnitRefine (Part 2) catch failures of single-unit identity that sorting-free metrics are blind to.\n     7\t- **For BCI-class longitudinal cohorts the evidence is now strong enough to set quantitative reporting standards:** Sponheim et al. 2021 (55 arrays, 9 years, 6,132 sessions; linear slope −0.00058 yield-fraction/day ≈ −2 %/30 d), Hahn et al. 2025 BrainGate medRxiv (20 arrays, 14 participants, 2,319 sessions; 35.6 % mean active-electrode fraction, 7 % decline over 2.8 years mean enrollment, max 7.6 years), and Hughes et al. 2021 (1,500-day single-subject, top-2 % V_pp convention) define the de facto field standards.\n     8\t\n     9\t---\n    10\t\n    11\t## Key Findings\n    12\t\n    13\t1. **The TC-rate yield metric has converged on a specific definition.** BrainGate (Hahn et al. 2025 medRxiv 2025.07.02.25330310): ≥ 2 Hz at −4.5 × robust σ, bandpass 250–5000 Hz, linear regression referencing. Hughes 2021 (Pittsburgh): −4.5 × V_RMS, ≥ 1.67 Hz, ≥ 30 µV V_pp inclusion floor, 48-sample (1.6 ms) snippets starting 11 samples before crossing. Sponheim 2021: −5.25 × V_RMS (moved to −4.5 from day 565 for one participant), ≥ 14 events, SNR > 1.5. Christie et al. 2015 (J Neural Eng 12:016009) showed that thresholds in the −3 to −5 × V_RMS range produce decoding within ~5 % classification accuracy of each other (Naïve Bayes accuracy change ~5 %, correlation Δ = 0.015), so threshold choice is not critical for population decoding but is critical for cross-study yield comparability.\n    14\t\n    15\t2. **V_RMS estimation varies by lab.** Downey et al. 2018 (J Neural Eng 15:046016) use the 5–10 samples immediately pre-crossing to avoid spike contamination. SpikeInterface `get_noise_levels` uses MAD-based estimator on random chunks (σ̂ = MAD / 0.6745). Both are valid; reports must specify which. The chunk-length sensitivity is non-trivial: SpikeInterface issue #4367 documents that \"the noise levels vector varies, but in the longer file values are sometimes as much as 20 % higher than the shorter file,\" which then changes peak-detection thresholds and downstream motion estimation.\n    16\t\n    17\t3. **Unsorted V_pp is more longitudinally stable than sorted-unit count.** Chestek 2011, Downey 2018, Hughes 2021, Sponheim 2021, and BrainGate 2025 all report TC yield declining far more slowly than well-isolated single units. Trautmann et al. 2019 (Neuron 103:1064) demonstrated via random projections that population dynamics from unsorted TC are nearly indistinguishable from those from sorted units, and Christie 2015 quantified the equivalence (Naïve Bayes Δ ≈ 5 % accuracy, Δ correlation = 0.015).\n    18\t\n    19\t4. **Impedance is gold-standard hardware health but non-monotonic with yield.** Hughes 2021: Pt-tipped motor arrays median 447.5 kΩ pre-implant → 1,396 kΩ at day 7 (post-implant interface formation), then declining over years; SIROF-tipped sensory arrays 74.5 kΩ pre-implant. Lewis et al. 2024 (Adv Healthcare Mater 13:2303401) showed that extremely low Z can flag insulation failure rather than improved tissue coupling on PEDOT-coated flexible probes.\n    20\t\n    21\t5. **LFP metrics are the most underused longitudinal stability signal.** Senzai, Fernandez-Ruiz & Buzsáki 2019 (Neuron 101:500) used 500–2000 Hz LFP power and CSD for laminar identification. DREDge (Windolf et al. 2025 Nat Methods, doi:10.1038/s41592-025-02614-5) and MEDiCINe (Watters, Buccino & Jazayeri 2025 eNeuro 12:ENEURO.0529-24.2025) make LFP / AP-band motion estimation routine without sorting.\n    22\t\n    23\t6. **Network-level sorting-free metrics** (pairwise MUA correlation, population envelope, correlation-matrix similarity across sessions) are emerging but lack formal longitudinal validation. Trautmann 2019 provides the theoretical basis via random projections.\n    24\t\n    25\t7. **Discovered eleventh family — Spiking-Band Power (SBP).** Even-Chen et al. 2020 (Nat Biomed Eng 4:984) and Nason et al. 2020 (Nat Biomed Eng 4:973) showed band-limited (300–1000 Hz) envelope power can predict movement similarly to TCR at 30 ksps. Meets all three discovery criteria (distinct physical quantity, ≥ 2 independent studies, different computational pipeline) and is elevated to Family 11.\n    26\t\n    27\t---\n    28\t\n    29\t## Details — Sorting-Free Metric Families\n    30\t\n[445 lines total]",
    "uuid": "df65ceb3-7b07-47b3-9592-8abea8a0ae6a"
  }
]
```

```json
// tool_use: view
{
  "description": "Read title and TLDR of fourth compass artifact (the integration)",
  "path": "/mnt/user-data/uploads/compass_artifact_wf-304f2c30-adfe-4c9d-bcdd-f351919f45b8_text_markdown.md",
  "view_range": [
    1,
    50
  ]
}
```

```json
// tool_result
[
  {
    "type": "text",
    "text": "     1\t# Part 4 — Integrated Extracellular Recording Quality Pipelines, Organized by Probe Physical Category\n     2\t\n     3\t## Framing\n     4\t\n     5\tThis document is the synthesis layer of a four-part reference series. Parts 1–3 are treated as authoritative inputs and are not re-derived. Part 1 reviewed spike sorters available in SpikeInterface and benchmarked in SpikeForest; Part 2 reviewed post-sorting curation; Part 3 reviewed sorting-free quality metrics for longitudinal tracking. Part 4 inverts the axis from method-family to probe-category: for each physical class of penetrating extracellular probe, **which integrated pipeline (sorter + curator + sorting-free metric stack + motion-correction policy) is defensible in 2026, what fails, and where the field is still inferring rather than validating**.\n     6\t\n     7\tThe categorization rules are applied first-match-wins, in this order: (1) 3D penetrating bed-of-nails arrays → Category 1; (2) otherwise, pitch ≤ 100 µm → Category 2; (3) otherwise, channel count > 16 → Category 3; (4) otherwise (pitch > 100 µm AND channels ≤ 16) → Category 4. The 3D-dense cell remains empty as of 2026 — no widely-deployed probe combines bed-of-nails geometry with within-shank pitch ≤ 100 µm. ECoG and other non-penetrating surface arrays are out of scope.\n     8\t\n     9\tThree integration conflicts between Parts 1–3 must be made visible up front, because they shape the per-category recommendations below:\n    10\t\n    11\t1. **Sorter–curator drift-correction conflict (Category 1).** Part 1 recommends Kilosort4 as the modern default for dense linear probes with drift. Part 2's primary rule-based curator (Bombcell) is \"specifically tailored for units recorded with Neuropixel probes (3A, 1.0, and 2.0) using SpikeGLX or OpenEphys and spike-sorted with Kilosort\" (Fabre et al. 2023 Zenodo 10.5281/zenodo.8172821 README). Part 3's chronic-Utah-array AEY convention (BrainGate; Hahn et al. 2025 medRxiv) skips spike sorting entirely. Composing all three on a Utah array produces an inconsistent stack: Kilosort4's drift module is contraindicated on 400 µm pitch (Pachitariu et al. 2024 Nat Methods 21:914), Bombcell is out-of-scope, and AEY does not need a sorter at all. The integrated recommendation must reconcile these.\n    12\t\n    13\t2. **PC-feature curator–modern sorter conflict (all sorter-based categories).** Part 2 flagged that PC-based isolation metrics (L-ratio, isolation distance, nn_*) are tetrode-era classics that \"fail on Kilosort outputs\". Yet several legacy Category 4 pipelines (and Allen ecephys_spike_sorting defaults) still ship them. Part 4 must say explicitly when to drop them.\n    14\t\n    15\t3. **HerdingSpikes2 pitch–benchmark conflict (Category 3 boundary).** Part 1 stated HerdingSpikes2 explicitly fails on probes with pitch > 60 µm. Category 3 (sparse planar) typically has 100–200+ µm pitch. Therefore HerdingSpikes2 is contraindicated across Category 3 even though SpikeInterface still wraps it.\n    16\t\n    17\t---\n    18\t\n    19\t## 1 — Executive Integrated Decision Table\n    20\t\n    21\t| Category | Defining rule | Representative probes | Primary sorter | Secondary sorter(s) | Contraindicated sorters | Primary curator | Mandatory sorting-free metrics | Motion correction | Key caveat |\n    22\t|---|---|---|---|---|---|---|---|---|---|\n    23\t| **1. 3D sparse penetrating arrays** | Bed-of-nails geometry, electrodes project into tissue volume; ~400 µm pitch on the cortical surface, each shank is a single electrode | Blackrock Utah array (16/96/256 ch, 400 µm pitch); Utah Slant Array (USEA); Utah Optrode | **None for BCI decoding (threshold crossings, –4.5 × robust σ)**. For SUA: **Kilosort4 with `nblocks=0` / `do_correction=False`** | MountainSort5 (channel-local), Kilosort2 (no required drift module), Wave_clus (per-electrode) | Kilosort4 with drift on; HerdingSpikes2; SpyKING CIRCUS with shared-channel templates; any sorter assuming dense spatial templates | UnitRefine (with caveat: n=80 cluster validation on Utah V1/V4, Jain 2025 reports 96.0% balanced accuracy); Bombcell **not validated**, use only ISI/amplitude/refractory components manually | **AEY (–4.5 × robust σ, 250–5000 Hz, ≥ 2 Hz, BrainGate)**; V_RMS; top-2% V_pp (Hughes 2021); 1 kHz impedance (Williams 2009/Ludwig 2008) | **Disabled** — array geometry makes z-axis drift correction ill-defined (Pachitariu 2024) | Each shank is electrically a single-channel monotrode at ~400 µm pitch; \"single-unit yield\" measured by SUA count is a strong function of operator policy, not a probe property |\n    24\t| **2. Dense planar arrays** | Pitch ≤ 100 µm; linear single-shank, dense multi-shank, or planar 2D | Neuropixels 1.0 (20 µm), Neuropixels 2.0 (15 µm), 3Brain BioCam, MaxWell HD-MEA, ETH MEA1K, NeuroNexus 64-ch @ 20–50 µm pitch | **Kilosort4** (Pachitariu 2024 Nat Methods 21:914) | Kilosort 2.5 (legacy reference, drift-corrected; current IBL pipeline sorter per figshare 19705522); SpyKING CIRCUS 2; MountainSort5 for in vitro / retina; HerdingSpikes2 *only* for pitch ≤ 60 µm and large in-vitro arrays | HerdingSpikes2 on pitch > 60 µm (e.g., NeuroNexus 50 µm linear); Wave_clus (single-channel); Combinato (human-microwire-tuned); HDSort outside CMOS-MEAs | **Bombcell + UnitRefine layered** (Part 2 recommendation; Power Pixels pipeline, Meijer & Battaglia 2025 bioRxiv 2025.06.27.661890); Allen ecephys defaults for cross-validation | V_RMS; AEY; drift trace from DREDge or MEDiCINe; for chronic: spike-band power (Nason 2020), top-2% V_pp | **Enabled by default** — Kilosort4 piecewise rigid + DREDge (Windolf et al. 2025 Nat Methods s41592-025-02614-5) for cross-session chronic | KS4's piecewise-rigid drift correction assumes ≤ 40 µm vertical pitch and z-only motion; oblique insertions or shear violate this |\n    25\t| **3. Sparse planar arrays, mid-to-high channel count** | Pitch > 100 µm AND channels > 16; planar linear/multi-shank arrangement | NeuroNexus 64-ch linear @ 200 µm; NeuroNexus 32-ch multi-shank (8 sh × 4 ch); Cambridge NeuroTech sparse multi-shank | **Kilosort4 with `nblocks=0`** OR **MountainSort5** (operator's choice, run both for consensus) | The other of {KS4, MS5}; Tridesclous2; per-shank Wave_clus on isolated shanks | HerdingSpikes2 (pitch >> 60 µm); Kilosort4 default drift settings (will hallucinate motion on sparse channels); KS3 (oversplit prone) | **UnitRefine** as primary (validated on wire bundles, NHP arrays); manual ISI/amplitude refractory thresholds; PC-based metrics **excluded** | V_RMS; AEY (where threshold-crossing decoding is a target); MUA firing rate; impedance | **Disabled or sub-shank only** | Most under-benchmarked category; Liu 2025 JHU MS thesis on 64-ch NeuroNexus rhesus monkey recordings reports MountainSort 5 outperforms Kilosort 2.5 and KS4 |\n    26\t| **4. Low-N sparse probes** | Pitch > 100 µm AND channels ≤ 16 | Tetrodes (4 ch); micro-wire bundles (1–16 ch, 9-channel Neuralynx probes); single-channel monotrodes; carbon-fiber arrays (16 ch, ~150–500 µm pitch) | **MountainSort 4 or 5** (tetrodes; Chung et al. 2017 Neuron 95:1381) OR **Wave_clus 3** / **Combinato** (single-wire human MTL); Kilosort4 with `nblocks=0` acceptable but not preferred | The other; Tridesclous; Klusta (legacy) | Kilosort4 with drift correction on; HerdingSpikes2; SpyKING CIRCUS 2 dense-template mode | Manual + per-cluster ISI / refractory / SNR thresholds; **UnitRefine retrained** if used (wire-bundle generalization untested in Jain 2025); rely on PC-based isolation metrics here (this is where they are still defensible) | V_RMS; AEY (–3.5 to –4.5 × σ depending on lab); SUA firing rate; impedance | **Inapplicable** (tetrodes/microwires have no z-axis to register against) | Human single-wire literature still relies on operator-tuned Wave_clus/Combinato; the field has no equivalent of Pachitariu-grade hybrid benchmarks for this category |\n    27\t\n    28\t---\n    29\t\n    30\t## 2 — Per-Category Sections\n    31\t\n    32\t### Category 1: 3D Sparse Penetrating Arrays\n    33\t\n    34\t#### A. Category characteristics\n    35\tBed-of-nails 3D silicon arrays (the canonical Blackrock Utah array, in 16/96/256-channel configurations; also the Utah Slant Array USEA for peripheral nerve, and the Utah Optrode). Each shank is electrically a single-channel monotrode; shanks are spaced at 400 µm on a 4 × 4 mm square base. The \"array\" has 96 spatially separated single electrodes, not a spatially correlated population. Typical context: **chronic** implantation in human motor / somatosensory / language cortex (BrainGate, Pittsburgh, Battelle/Ohio State, Caltech/USC), in NHP (Hatsopoulos, Smith, Shenoy lineage), and in rodent cortex. Recordings span days to years (BrainGate up to 7.6 years; one Hatsopoulos NHP array — designated MkM1c in macaque M1 — sustained recordings for nearly nine years and was explanted only because of an infection near the connector, per Sponheim et al. 2021 J Neural Eng 18:066044). Expected drift profile: macroscopic insertion-day settling over 4–6 weeks (Sponheim 2021 Fig. 5b shows yield rising in first 40 days post-implantation), then slow yield decline (Hahn et al. 2025 medRxiv 2025.07.02.25330310: \"On average, arrays successfully recorded neural spiking waveforms on 35.6% of electrodes, with only a 7% decline over the study enrollment period (up to 7.6 years, with a mean of 2.8 years)\"). Expected SNR: low to moderate per electrode (5–15 µV peak for many channels, with a long tail of high-amplitude channels — hence the top-2% V_pp metric).\n    36\t\n    37\t#### B. Primary sorter recommendation + rationale\n    38\t**For BCI decoding: no sorter; use threshold crossings at −4.5 × robust σ in the 250–5000 Hz band**, after linear-regression re-referencing. This is the BrainGate convention used unchanged across all 14 BrainGate / BrainGate2 participants and 2,319 recording sessions. Verbatim from Hahn et al. 2025 medRxiv (Fig. 1C caption): \"30 KHz recordings were decimated to 15 KHz, band pass filtered with a pass band of 250-5000 Hz, re-referenced with linear regression referencing (LRR) and thresholded at −4.5 times the robust standard deviation of the voltage signal for each channel.\" Trautmann et al. 2019 Neuron 103:292 showed that on Utah arrays in NHP M1/PMd, population dynamics recovered from threshold crossings are essentially indistinguishable from those recovered after spike sorting.\n    39\t\n    40\t**For systems-neuroscience SUA analysis: Kilosort4 with `nblocks=0` (drift correction disabled).** Pachitariu et al. 2024 Nat Methods 21:914–921 explicitly state: \"Some types of data do require special consideration. For example, some data cannot be drift-corrected effectively due to either lacking a well-defined geometry (tetrodes) or due to the vertical spacing between electrodes being too high (more than 40 μm). This consideration also applies to data from single electrodes such as in a Utah array.\" Operationally this means using KS4 on a per-shank basis (each shank treated as a 1-channel recording, then concatenated). The Allen Institute for Neural Dynamics SpikeInterface wrapper exposes a `--min-drift-channels` argument that defaults to 96, which has the effect of disabling drift correction for typical Utah arrays.\n    41\t\n    42\t#### C. Secondary sorters for consensus\n    43\t**MountainSort5** (Chung et al. 2017 Neuron 95:1381; modern reimplementation by Magland/Flatiron). Because it sorts each local channel neighborhood independently and does not assume a dense spatial template, it is mechanically compatible with Utah-array geometry. **Kilosort2** (no required drift module) and **Wave_clus 3** (Chaure, Rey & Quian Quiroga 2018 J Neurophysiol 120:1859, per-electrode) are also defensible for cross-validation. Buccino et al. 2020 eLife 9:e61834 documents that no single sorter dominates in consensus comparisons, so a KS4 + MS5 consensus on Utah arrays is the most defensible posture for SUA work.\n    44\t\n    45\t#### D. Contraindicated sorters\n    46\t- **Kilosort4 with drift correction on** (`nblocks > 0`): Pachitariu 2024 explicitly warns against this.\n    47\t- **HerdingSpikes2**: requires pitch ≤ 60 µm (Part 1 finding; HerdingSpikes PyPI README explicitly excludes this regime).\n    48\t- **SpyKING CIRCUS / Kilosort3 with shared-channel templates across electrodes**: the 400 µm pitch makes cross-electrode template sharing pathological.\n    49\t- **HDSort**: tuned for CMOS-MEA geometries.\n    50\t\n[362 lines total]",
    "uuid": "0753413c-6733-44d5-8813-c587bb377c4e"
  }
]
```

> **[thinking]**
>
> I'm going through each report to identify the dates and key details. The first one from May 2026 covers spike sorting algorithms in SpikeInterface version 0.104.3, and the second report appears to be about post-sorting curation, though the title got cut off.
> 
> For the third and fourth reports, I notice there's an interesting progression—the original series had three parts focused on recording quality metrics, but a fourth part was added later as an integration layer that synthesizes everything across different probe types.
> 
> Looking at the content coverage, Part 1 focuses on sorter algorithms and their probe compatibility, while Part 2 addresses the curation landscape including both rule-based and machine learning approaches to quality assessment.
> 
> Part 3 covers metrics that don't require sorting—things like threshold crossings, voltage measurements, and impedance tracking—with emphasis on what can be monitored longitudinally in real recordings. Part 4 then brings it all together by showing how to combine sorters, curators, and metrics into coherent pipelines tailored to specific probe geometries, resolving conflicts where the earlier parts might suggest different approaches.
> 
> Now I'm drafting the actual section for the project knowledge files. I need to document these four research reports with their filenames, scope, authority, and how they relate to the main documentation. I'll suggest a cleaner naming scheme since the current filenames are unwieldy, and keep the whole section concise—around 30 to 50 lines of markdown following the existing style of the project instructions.

Here's the updated section. It replaces the existing "Project knowledge files" section in the Enterprise project instructions. The four files all date from around May 2026 based on internal references (SpikeInterface 0.104.3 inventory, Hahn 2025 medRxiv citations, etc.).

```markdown
## Project knowledge files

The standing knowledge in this project has two tiers: a thin policy
layer that mirrors the Pro project, and a thicker background-research
layer that grounds discussions in current literature.

### Policy layer (from the Pro project)

These four files are authoritative for "what does this project do."
If chat conclusions conflict with them, the files win unless the user
is explicitly proposing a change. Re-upload when materially changed,
not after every session.

- `CLAUDE.md` — code conventions, sorter policy, data conventions,
  segment handling, file layout. Check first when a question's
  answer depends on a project rule.
- `roadmap.md` — phase plan and session sequence. Authoritative for
  "what phase are we in" and "what comes next."
- `pyproject.toml` — dependency pins and package metadata.
- `project_instructions.md` (the Pro project's version) — for
  cross-checking drift between the two projects' instructions.

### Background research reports

Four deep research reports (May 2026) form a connected reference
series. Treat them as background grounding, not policy. When a report
conflicts with `CLAUDE.md`, flag the conflict and ask whether
`CLAUDE.md` should be updated; do not silently follow the report.

- `sorters_report.md` (Part 1 of 4). Comparative review of spike
  sorting algorithms in SpikeInterface and SpikeForest. Inventory of
  wrappers as of SI 0.104.3, algorithm mechanisms by family
  (Kilosort, MountainSort, density/graph-based, classical
  wavelet/SPC), probe-fit, known failure modes, deprecation status.
  **Authoritative for:** "which sorter for which probe geometry,"
  sorter algorithm design intent, deprecated and unmaintained
  sorters, batch-boundary and oversplit failure modes,
  multi-sorter consensus rationale.

- `curation_report.md` (Part 2 of 4). Post-sorting curation
  reference: rule-based curators (Bombcell, IBL, Allen ecephys),
  ML classifiers (UnitRefine), the SpikeInterface qualitymetrics
  module, manual GUIs (Phy, SortingView), and cell-type classifiers
  (C4). Formulas, thresholds, validation studies, probe-specific
  tuning. **Authoritative for:** curator selection, quality metric
  definitions and recommended thresholds, why PC-based metrics
  (isolation_distance, L-ratio, nn_*) fail on Kilosort outputs,
  Neuropixels-tuned thresholds and why they need adjustment for
  Utah / NeuroNexus / tetrodes.

- `sorting_free_metrics_report.md` (Part 3 of 4). Sorting-free
  longitudinal metrics: threshold-crossing yield (AEY), V_RMS noise
  floor, top-2% V_pp, 1 kHz impedance, LFP power, spike-band power,
  network-level metrics. Established field conventions from
  BrainGate (Hahn 2025), Sponheim 2021, Hughes 2021, Christie 2015.
  **Authoritative for:** what to track longitudinally without
  sorting, noise floor estimation conventions, the
  threshold-crossing literature this project's threshold-crossing
  module must align with, longitudinal reporting standards for
  Utah-array cohorts.

- `integrated_pipelines_report.md` (Part 4 of 4). Synthesis layer:
  integrated pipeline recommendations (sorter + curator + metrics +
  motion correction) per probe physical category. Category 1 (3D
  sparse penetrating, Utah-class) is directly load-bearing for this
  project's primary hardware; Category 3 (sparse planar) applies to
  the NeuroNexus 64-ch multi-shank planned for Phase 4. Resolves
  three integration conflicts between Parts 1-3.
  **Authoritative for:** the full stack on a given probe, how to
  reconcile when Parts 1-3 disagree, the rationale for
  `nblocks=0` / `do_correction=False` on Utah arrays, why
  Bombcell defaults are out-of-scope for Utah and what to do
  instead. **When in doubt across Parts 1-3, defer to Part 4.**

### Routing guidance

For questions about a specific sorter's algorithm, history, or
failure mode → Part 1.

For questions about quality metrics, curator choice, or threshold
tuning → Part 2.

For questions about pre-sort metrics, longitudinal reporting
conventions, or noise estimation → Part 3.

For questions about "what's the full pipeline on probe X" or
"these two reports disagree, what wins" → Part 4.

For project-specific policy (sorter pool, segment policy, file
layout) → `CLAUDE.md`.

Treat the research reports as dated artifacts. Flag staleness if a
sorter version or threshold convention referenced in the reports is
known to have changed since May 2026. Re-run the relevant research
rather than letting stale standing knowledge silently shape advice.

### Per-chat uploads (not standing knowledge)

Upload at chat start when relevant; do not assume persistence:

- `docs/session_plans/sessionNN_*.md` for session-specific context.
- `docs/notes/<topic>.md` for architecture discussions touching a
  specific note.
- `docs/phase_plans/phaseN_*.md` for phase reviews.
- Legacy MATLAB scripts when the discussion is about migrating a
  specific behavior.
- Scratch Python files when reviewing or cross-checking specific
  code output.
```

Three notes on what's in this section that wasn't in the previous draft.

**Filename suggestions.** The compass_artifact filenames are opaque. Recommend renaming to `sorters_report.md`, `curation_report.md`, `sorting_free_metrics_report.md`, and `integrated_pipelines_report.md` before upload. The model will route by filename when retrieving, so descriptive names help.

**The routing guidance subsection** is the load-bearing addition. Without it, retrieval on a question like "which curator for Utah arrays" might pull from all four reports and produce a muddled answer. With it, the model knows Part 4 reconciles Part 2's Neuropixels-tuned Bombcell recommendation against Part 3's sorting-free AEY convention against Part 1's sorter geometry constraints, and answers from that integration rather than picking one report.

**The "Part 4 wins when in doubt" rule** matches the report's own design. Part 4 explicitly says it's the synthesis layer and that Parts 1-3 are inputs. Encoding that in the instructions prevents the model from treating the four as parallel sources when they're actually a layered argument.

---


# NAV pilot inventory — recqual, 2026-09-12 (Phase 1, native vocabulary)

Every trackable thing this project has, in its own words. `mapping` filled in
Phase 2: an entry id, `LOSSY: <what was lost>`, or `NONE: <why>`.

| item | native kind | where recorded | last touched | mapping |
|---|---|---|---|---|
| "Which objective metrics track recording quality as an implant ages" | primary scientific question | README.md, roadmap.md framing | 2026-08 | A-001 |
| "A pipeline a new student can run end to end", MATLAB-consumable | engineering goal | roadmap.md framing, CLAUDE.md | 2026-05 | A-003 |
| Re-examine the published L1-coating yield claim | the claim the project set out to re-examine | docs/notes/treatment_effect.md | 2026-08-24 | A-002 |
| Phase 1 single-sorter baseline (sub-phases 1a–1d, S1–S9) | roadmap phase | docs/roadmap.md | 2026-08-11 | P-01 |
| Phase 2 multi-sorter consensus | roadmap phase | docs/roadmap.md | 2026-05 | P-04 |
| Phase 3 curation methods | roadmap phase | docs/roadmap.md | 2026-05 | P-05 |
| Phase 4 full cohort + NeuroNexus | roadmap phase | docs/roadmap.md | 2026-05 | P-06 |
| Deferred phase: impedance integration ("likely Phase 5") | deferred phase | docs/roadmap.md | 2026-05 (lived: 2026-09) | P-07 |
| Deferred phase: endpoint histology registration | deferred phase | docs/roadmap.md | 2026-05 | P-08 |
| Deferred phase: in vivo imaging registration | deferred phase | docs/roadmap.md | 2026-05 | NONE: no activity, no near plan; folded into P-08's body as later sibling |
| Cross-subject scaling (1 subject → 6, three acquisition regimes) | plan supersession ("supersedes the phase sequence as near-term driver") | roadmap current-state pointer, docs/cross_subject_plan.md | 2026-08-15 | P-02 |
| The scientific campaigns on the corpus (cohort, treatment, rings, impedance, consensus) | session sequence S8–S14 | docs/session_plans/ | 2026-09-12 | P-03 |
| Session logbook entries S01–S14 | session card / logbook entry | docs/session_plans/*.md (14 files) | 2026-09-12 | NONE: history, not live state; referenced via `source` on entries |
| 47 concept/gotcha/decision notes | note | docs/notes/*.md | 2026-09-12 | NONE: reference material; entries cite them via `evidence`/`source`. Decisions *contained in* notes map to D entries |
| Literature reviews | reading / report | docs/reports/ | 2026-08 | NONE: reference; cited via evidence |
| Exported chat history | archive | docs/archive/ | 2026-08-03 | NONE: provenance only |
| Roadmap "current state pointer" (says next = S6) | state pointer | docs/roadmap.md | 2026-08-15, stale | I-002 (staleness issue) |
| HANDOFF.md cold-start orientation (written after S1–S3) | handoff doc | docs/HANDOFF.md | 2026-05, stale | I-002 |
| Session Map + Reasoning Trace published pages | artifact (claude.ai page) | docs/session_map.html, docs/recqual_flow.html + artifact URLs | 2026-08-22/23, stale | W-011 (refresh awaits owner) + Phase 4 legacy diff |
| Channel-map explainer page | artifact (explainer) | docs/channel_map_explainer.html | 2026-08 | NONE: reference material |
| Band must be read from nsX extended header, never suffix | data convention (MUST) | CLAUDE.md, lfp_quality.md | 2026-08-23 | D-001 |
| Aggregation rule: never pool numerator/denominator across sessions | analysis rule (MUST) | CLAUDE.md | 2026-08-18 | D-002 |
| Sorter pool policy + exclusions | sorter policy | CLAUDE.md | 2026-05-20 | NONE: omitted by the 10-accepted-decisions cap (oldest); rules stay in CLAUDE.md |
| Snippet cohorts sorted by per-electrode ISO-SPLIT, "correct method not fallback" | design decision | README.md, snippet_sorting.md | 2026-08-03 | D-003 |
| UnitRefine unusable on snippet data; physics gate is the curation layer | verdict + rule | robustness.md, snippet_sorting.md | 2026-08-18 | D-004 |
| Serials resolve by (subject, implant, array) | gotcha-turned-rule | CLAUDE.md, serial_resolution.md | 2026-09-12 | D-005 |
| Blackrock impedance joins on channel_id (proven 1248/1248) | proven rule | impedance_sources.md | 2026-08-22 | D-006 |
| Fisk .ns3 stays out of the pipeline (redundant copy) | stream decision | lfp_quality.md | 2026-09-12 | D-007 |
| Stripe axis = CMP col, even cols treated; anterior = TNP (owner-confirmed) | mapping decision + owner confirmation | surface_conditions.md | 2026-08-19 | D-008 |
| Segment handling: drop <5 s, process independently, never concatenate | IO rule | CLAUDE.md, segment_handling.md | 2026-05 | NONE: omitted by the 10-accepted-decisions cap (oldest); rule stays in CLAUDE.md |
| Potentiostat "open/short" flags are rig diagnostics, not electrode states | reinterpretation | impedance_channel_map.md | 2026-09-12 | D-009 |
| Authored vs naive potentiostat channel map (0/96 agreement) — user "settling" it | open choice | impedance_channel_map.md; chat | 2026-09-12 | D-011 (proposed, owner human) |
| Min_P2P_exclusion = 20 µV must not be applied unless explicitly asked | standing instruction | chat only (not in repo) | 2026-08 | LOSSY: mapped D-010 with basis inferred; chat-only provenance |
| Keep RAM/virtual memory safe; docker/WSL caution | standing instruction | chat only | 2026-09 | NONE: session operating constraint, not project state |
| CLAUDE.md gotcha list (8 items) | gotcha | CLAUDE.md | 2026-09-12 | NONE: reference rules; the two that arose this era are D-005/D-006 |
| Consensus longitudinal: agreement 0.27–0.34, collapses = dying arrays | finding | multisorter_agreement.md, figures/consensus/ | 2026-09-12 | R-001 |
| Rocky I2 fresh implant: border −26..−38%, opposite of I1 | finding | ring_geometry.md | 2026-09-12 | R-002 |
| Three empirical map arbiters all null | finding (negative) | impedance_channel_map.md | 2026-09-12 | R-003 |
| UnitRefine discriminative on recording-backed analyzers (54–68% neural) | finding | unitrefine_analyzer.md | 2026-09-12 | R-004 |
| Coated array ≈2× impedance on 18/19 chronic paired dates, flips with pedestal | finding (anchor confirmation) | scratch_impedance_extended output, cohort_definition.md | 2026-09-12 | R-005 |
| Pooled stripe permutation null; detectable bound 21.7% yield / 5.5% noise | finding (null + sensitivity) | surface_conditions.md | 2026-09-12 | R-006 |
| Rocky edge contrast widens from bench over 7 y (ρ −0.73) | finding | ring_geometry.md | 2026-09-12 | R-007 |
| Fisk .ns3 ≈ band-matched .ns6 (ρ≈0.99, ×1.19) | finding | lfp_quality.md | 2026-09-12 | R-008 |
| Impedance edge effect absent at factory, grows in tissue (bench anchor) | finding | ring_geometry.md, figures/ring/G7 | 2026-08-24 | R-009 |
| Treatment contrast consistent only on the pedestal axis (3 animals + I2) | finding | treatment_effect.md | 2026-08-24 | R-010 |
| Stripe permutation null 0/168 across 13 sorting methods | finding | surface_conditions.md | 2026-08-19 | NONE: omitted by 10-results cap; cited as evidence path by R-006/A-002 |
| Cohort definition from 8 sources; Rocky implant split; Luigi +31 d clock | finding cluster | cohort_definition.md, legacy_archive.md | 2026-08-19..24 | NONE: omitted by cap; evidence paths |
| TDT channel map: all 24 candidates excluded; noise is amplifier-bound | finding (negative) | tdt_channel_map.md | 2026-08-18 | NONE: omitted by cap; evidence path |
| Fisk LFP grounding fault Feb–Mar 2025, dose-response | finding | lfp_quality.md | 2026-08-23 | NONE: omitted by cap |
| Snippet noise floor biased ~30% high | finding | snippet_noise_floor.md | 2026-08 | NONE: omitted by cap |
| UnitRefine labels 99.98% noise on snippets (65,051 units) | finding | snippet_sorting.md | 2026-08-18 | NONE: omitted by cap; superseded-in-scope by R-004 |
| Serial mislabel: 431 Rocky I1 sessions carried I2 serials | bug (found+fixed) | serial_resolution.md, commit fb6a757 | 2026-09-12 | I-001 (resolved) |
| Docs drift: roadmap pointer, HANDOFF.md, cross_subject §4, artifacts | staleness | roadmap.md, HANDOFF.md | 2026-09-12 | I-002 |
| Fisk 2024-09-04 .ns3 file all-zero | data oddity | lfp_quality.md | 2026-09-12 | NONE: documented, nothing to do; below entry granularity |
| Fisk stripe assignment inferred, not verified from its own schematic | open verification | surface_conditions.md | 2026-08-19 | Q-001 |
| What sets the implant-level edge sign? | open question | ring_geometry.md | 2026-09-12 | Q-002 |
| Does the impedance edge effect generalize beyond Fisk (Nigel's 362 files)? | open question | ring_geometry.md, _LEGACY-SWEEP-REPLY.md | 2026-09-12 | Q-003 |
| What probe do Picasso and Luigi carry? | open question | cross_subject_plan.md §4.3 | 2026-08-15 | Q-004 |
| Picasso post-explant recordings unexplained | open question | cohort_definition.md | 2026-08-19 | Q-005 |
| Any coating effect below the ~22% detection bound? | open question (needs more arrays) | surface_conditions.md | 2026-09-12 | Q-006 (parked) |
| How deep can Luigi go (no impedance, no map, 148 undated tanks)? | open question | cross_subject_plan.md §4.2 | 2026-08-15 | Q-007 |
| Does agreement structure track quality better than single-sorter counts? | hypothesis (headline bet) | CLAUDE.md metrics layer 3, multisorter_agreement.md | 2026-09-12 | Q-008 |
| Is Rocky 2025 implant in scope? | open item for user | cross_subject_plan.md §4.1 | 2026-08-15 | NONE: answered in practice (I2 analyzed S12–S14); doc never updated — part of I-002 |
| Nigel's third serial 1025-002456 | open item for user | cross_subject_plan.md §4.4 | 2026-08-15 | NONE: answered (ejected array, sweep reply); doc never updated — I-002 |
| Copy census-located files (by-location xlsx, Nigel impedance, deck, PDF, .mat) | pending user action | chat + docs/handoff_legacy_search.md | 2026-09-12 | W-001 (owner human) |
| Nigel impedance ingestion → second map-free edge test | queued analysis | ring_geometry.md "what would settle it" | 2026-09-12 | W-002 (blocked on W-001) |
| Re-run stripes with verified Fisk assignment | queued analysis | surface_conditions.md | 2026-08-19 | W-003 (blocked on Q-001) |
| Per-electrode impedance joins under the settled map | queued analysis | impedance_channel_map.md | 2026-09-12 | W-004 (blocked on D-011) |
| Rocky I2 map-transfer test (needs 2025 potentiostat dumps, not located) | queued analysis | impedance_channel_map.md | 2026-09-12 | W-005 (owner human: locate dumps) |
| Histology×ephys join for Nigel (NEUN pipeline exists in sibling session) | queued analysis / deferred phase start | roadmap deferred phases; session13 log (untracked) | 2026-09-12 | W-006 |
| ElectrodeMetadata dataclass; src/ promotion; Tier 1 tests | owed debts | roadmap.md "Known deferred" | 2026-08-15 | W-007 (parked) |
| Phase 1 validation spec + Plexon sign-off + phase tags/tutorials | owed phase-boundary deliverables | roadmap.md | 2026-08-15 | W-008 (parked) |
| ns5_plan remaining items: fixed-threshold vs snippet yield; giant-site trace pulls | queued analysis | ns5_plan.md | 2026-08 | W-009 |
| Per-channel NEV match recompute ("match_is_pooled" flag) | known shortcut to undo | scratch_ns5_resort.py comment | 2026-09-12 | W-010 |
| Refresh the two published artifact pages | pending user go-ahead | chat ("commit but do not publish") | 2026-08-24 | W-011 (owner human) |
| UnitRefine continuous-arm validation vs human curators (DS/Sidd trees) | queued analysis | unitrefine_analyzer.md scope note; Rocky New/ | 2026-09-12 | W-012 |
| Bombcell with retuned sparse-array thresholds | roadmap item | roadmap.md P3, CLAUDE.md | 2026-05 | W-013 |
| NeuroNexus 16ch probe support | roadmap item | roadmap.md P4 | 2026-05 | W-014 |
| TDT pNe LFP: int16 with no recorded scale | parked recovery | lfp_quality.md | 2026-08-23 | W-015 (parked) |
| S11 leftovers: Luigi 319 previews, TDT resort status | loose thread | session11 log "Deferred" | 2026-08-19 | NONE: omitted under the 60-entry cap (lowest-value proposed audit) |
| Census session searching drives from our handoff | collaboration (another agent) | docs/handoff_legacy_search.md; _LEGACY-SWEEP-REPLY.md | 2026-09-11 | W-016 (owner external) |
| Derived parquet tables (data/derived/**) | dataset (regenerable) | data/, gitignored | 2026-09-12 | NONE: outputs, referenced via evidence |
| Committed figures (ring/, consensus/, treatment/…) | figure | figures/ | 2026-09-12 | NONE: evidence attachments |
| Tier-1 tests that exist (LFP suite) | test | tests/test_lfp_quality.py | 2026-08-23 | NONE: code, not navigational state |
| User-level memory index (drive census, histology pipeline, git identity) | memory file | ~/.claude/.../memory/MEMORY.md (outside repo) | 2026-09 | NONE: outside repo; provenance only |
| Monkey_Data legacy estate + census reply | external evidence trove | D:\Claude Code\Monkey Data\Legacy (outside repo) | 2026-09-11 | NONE: outside repo; cited via source on entries |

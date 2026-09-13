# NAV pilot report: recqual, 2026-09-12

Claims are labeled `recorded`, `inferred`, or `judgment`.

## 0. Project profile
- Repo: local git (`D:\Claude Code\SpikeInterface`, GitHub `rockystones/spikeinterface-recqual`). ~148 commits, 2026-05-20 → 2026-09-12, **active** (63 commits in the last 48 h). ~2,600 tracked files (figures-heavy). `recorded`
- Primary class: **research inquiry**, secondary **build**. The repo is framed as a pipeline build (CLAUDE.md, roadmap) but the last six weeks' commits are scientific campaigns; the build aims are parked. `judgment`
- Where state is tracked today: `CLAUDE.md` (rules; current), `docs/roadmap.md` (phase plan; pointer **4 sessions stale**), `docs/HANDOFF.md` (cold-start; **pre-pivot, ~3.5 months stale**), `docs/cross_subject_plan.md` (open items; **2 of 5 answered but still listed open**), `docs/session_plans/` (14 logbook entries; current), `docs/notes/` (47 topic notes; current — this is where live truth actually sits), two published dashboards (frozen 2026-08-22/23), user-level memory index (outside repo). `recorded`
- Pilot effort: ~1 session, ~1.5 h wall time, roughly 60–80k tokens of authoring on top of a session that already held deep project context. **Caveat: this pilot was run by a session with full prior context, not cold — inventory recall was cheap and staleness detection easy; a cold pilot would cost multiples more.** `judgment`

## 1. Inventory summary (Phase 1)
- 80 rows. Native kinds and counts: finding (16, incl. 1 cluster row), roadmap/deferred phase (7), queued analysis (7), note/reference kinds (note, reading, archive, explainer, gotcha list, memory file, figures, derived tables, tests, estate — 10), open question / open item for user (9), rule/convention/policy/decision kinds (9), pending user action (2), owed debts / phase-boundary deliverables (2), session logbook (1 row for 14 files), aims/goals (3), state-pointer/handoff staleness (2), artifact pages (2), bug (1), data oddity (1), standing instruction (2), plan supersession (1), collaboration (1), parked recovery (1), loose thread (1), dataset (1).

## 2. Mapping outcome (Phase 2)

check.py JSON, verbatim:

```json
{
  "n_entries": 58,
  "by_type": {"aim": 3, "decision": 11, "issue": 2, "phase": 8, "question": 8, "result": 10, "work": 16},
  "by_status": {"aim/active": 3, "decision/accepted": 10, "decision/proposed": 1, "issue/resolved": 1, "issue/open": 1, "phase/active": 4, "phase/done": 1, "phase/proposed": 3, "question/open": 7, "question/parked": 1, "result/current": 10, "work/proposed": 9, "work/blocked": 3, "work/parked": 3, "work/active": 1},
  "basis": {"recorded": 55, "inferred": 3},
  "owner": {"agent": 41, "human": 14, "external": 3},
  "x_fields": {"x_status_wanted": 1},
  "other_proposed_types": {},
  "pending_from_human": ["D-011", "R-001", "R-002", "R-003", "R-004", "R-005", "R-006", "R-007", "R-008", "R-009", "R-010", "W-001", "W-005", "W-011"],
  "entries_without_source": [],
  "dangling_links": [],
  "errors": []
}
```

- Coverage: **80 rows / 52 mapped cleanly / 1 LOSSY / 27 NONE.**
  - LOSSY: Min_P2P standing instruction → D-010 (`basis: inferred`; the instruction exists only in chat, so the schema's provenance model cannot show it as recorded even though it is binding).
  - NONE, three families: (a) **reference material** — 10 rows (notes, reports, archive, explainer, gotchas, figures, derived tables, tests, memory, estate) deliberately excluded under the not-an-entry rule and reached via `source`/`evidence`; (b) **cap omissions** — 8 rows (6 pre-anchor findings, 2 oldest accepted decisions, 1 low-value audit); (c) **answered-but-stale open items** — 2 rows (I2-in-scope, Nigel-2456) folded into I-002; plus session logs (history), imaging phase (folded into P-08), RAM constraint (session-scoped), plan-supersession row (became P-02's body).
- Extension fields used: `x_status_wanted` | 1 | P-01 is open-but-displaced and no phase status says so | **yes** — see §7.1.
- Proposed types (`type: other`): none needed. Nearest misses handled inside core types: the external collaboration became `work` with `owner: external`; the standing instruction became a `decision` with no live alternative (the schema's own advice).
- Statuses wanted: `stalled` | phase | 1 | a phase that is neither active (nobody works it) nor abandoned (still owed) nor proposed (it started).
- Ambiguities resolved by judgment (the main ones):
  1. Three aims vs "one to three" — kept 3; the template's singular Aim slot strains (see §3).
  2. Roadmap phases vs lived arc — kept the roadmap's 4+2 and added two `inferred` phases (P-02, P-03) for the pivot the roadmap itself declares. Rule: phase = a stage someone actually navigated by.
  3. Findings-as-results vs notes — a result entry per *claim with a verdict*, the note stays the evidence. Rule: entries point, notes explain.
  4. `owner` on a blocked-on-human question (Q-001): kept `owner: agent` + `depends_on` the human work item, so the human queue holds actions, not knowledge.
  5. Same-day result ties under the 10-cap (2026-08-24 had 3+ candidates): picked by decision-relevance, `judgment`, reported here.
  6. The bug: filed as issue I-001 (resolved) + decision D-005, no result entry — resolution-is-action.
- Relations not expressible: (1) **"partially delivers"** — R-001 partially satisfies P-04's goal out of order; `parent` overstates containment, `resolves` overstates closure; said in prose. (2) **"informs/firms without gating"** — R-003 changes D-011's *justification* without blocking or resolving it; `evidence` is the nearest fit but reads as support, and R-003 is a *null*. (3) **"supersedes-in-scope"** — R-004 narrows an old finding's scope without replacing it; `supersedes` would wrongly retire the snippet-era result.
- Granularity: one entry = one thing someone would point at later by id. Hard cases: the finding *cluster* row (cohort definition + implant split + clock skew — one campaign, three claims; left out under the cap rather than split), the gotcha list (8 rules, 2 promoted), the ns5_plan remainder (two items in one W-009). **~6 hard cases / 80 rows.**
- Sampling (cap applied): omitted **~14 results** (stripe 0/168, TDT map exclusion, LFP grounding fault, snippet-noise bias, UnitRefine-on-snippets, cohort-definition cluster, and older), **2 accepted decisions** (sorter pool, segment handling — both from 2026-05), **1 proposed audit**. See §7.2 for why recency was the wrong axis.

## 3. STATE.md self-test (Phase 3)
1. Goal and success: **yes** — but the template's single-Aim slot had to hold three aims.
2. Plan and next: **yes** — phases, position, and a one-line next action all derivable.
3. Strategy: **partial** — the ten most recent accepted decisions carry most of it, but the two cap-omitted 2026-05 decisions (sorter pool, segment handling) are load-bearing strategy a cold reader would miss.
4. What has been done: **partial** — the ten recent results cover the current campaigns; everything before 2026-08-24 (the corpus build, the cohort definition, the stripe null) is invisible except through P-02's two-line body.
5. What worked/didn't: **yes** for the last three weeks; **no** for the project's middle third (same cap effect).
6. Waiting on the human + unblocks: **yes** — and it is *better* than any existing project document: no current file ranks W-001 above D-011, which the dependency graph shows plainly.
- Contradictions surfaced: roadmap pointer at S6 vs repo at S14; cross_subject §4 lists as open two questions answered weeks ago; HANDOFF.md describes a one-subject project; CLAUDE.md's curation-policy section still recommends what D-004 bans on snippets (the gotcha corrects it lower down). All now in I-002.

## 4. Legacy HTML diff (Phase 4)
Two navigational pages, both copied to `nav/legacy/`. `docs/session_map.html` (2026-08-22) is the state dashboard: Running / **Needs your decision** / Next in queue panels, the owner's four framing questions with themed built-work cards, "Claims corrected after being published", "Controls that carry the negative results", "Pipeline bugs found & fixed", per-animal cohort dossiers, corpus inventory, What is next. `docs/recqual_flow.html` (2026-08-23) is a reasoning-trace DAG: ~40 prose stages with jump links ("the fork: what kind of data is this", "Jaccard alone gave the wrong conclusion", …).

- **HTML had, schema cannot represent:** (1) the *reasoning chain* — an ordered argument graph with narrated missteps and recoveries; results+evidence links carry the endpoints but not the causal narrative between them; (2) *per-animal dossiers* — structured reference state (implant dates, serials, eras) that is neither work nor result; the schema's answer is "reference material via source", which loses its at-a-glance-ness; (3) the *corrections gallery* as a first-class category — representable only as superseded results, and most corrections predate the sampled window; (4) grouping by the owner's framing questions (a question taxonomy above individual Q entries).
- **Schema represents, HTML lacked:** explicit `owner` and a derivable ranked human queue; `depends_on` (the HTML's "Needs your decision" list is flat — it cannot say W-001 unblocks three things); parked-with-wake-trigger; predictions/credences/falsifiers; `basis` provenance; immutability of results; the roadmap phases (the dashboard ignores them entirely — telling).
- **Stale in HTML relative to repo:** everything after 2026-08-23 — all ten of STATE.md's results, three of four newest decisions, D-011's arbiter nulls, Rocky I2, the consensus layer; its Running panel names work finished weeks ago. Dates: pages 2026-08-22/23 vs repo 2026-09-12.

## 5. Cold read (Phase 5, if run)
Skipped: it requires a context-free session, and this pilot ran inside a fully-loaded one (worst-case contamination). Ask and it can be run as a follow-up with a fresh session reading only `nav/STATE.md`.

## 6. Checks
- **C1 Types: pass** — no recurring gap; every native kind landed in a core type or deliberate NONE (0 `type: other`). Evidence: §2 coverage.
- **C2 Statuses: partial** — one wanted (`stalled` on phase); only one row, but the condition (open-yet-displaced work) recurs in spirit across P-01/W-007/W-008, absorbed by work's `parked` which phases lack.
- **C3 Links: partial** — three relations forced into prose (§2: partially-delivers, informs-without-gating, supersedes-in-scope).
- **C4 STATE.md: partial** — 4 of 6 fully answerable; strategy and history partial, both traceable to the recency-only sampling rule.
- **C5 Idea folding: pass** — things-to-try became work proposed/parked with wake triggers; nothing lost except ranking among proposals (no priority field; order was encoded only in prose).
- **C6 Owner queue: pass with one systematic false-positive class** — W-001/W-005/W-011/D-011 exactly match what the human must act on (`recorded`); the ten `owner: human` results are technically correct per the review rule but flood the queue — review-pending and action-pending need distinguishing.
- **C7 Granularity: pass** — decidable for ~74/80 rows; 6 hard cases (§2).
- **C8 Legacy loss: fail (by design honesty)** — the reasoning-trace DAG and per-animal dossiers are genuinely lost; both are things the owner uses.

## 7. Recommended schema changes, ranked, at most five
1. **Split review-pending from action-pending in the human queue** (C6): either `owner: human` + `x_needs: review|action` or exclude unreviewed results from `pending_from_human` into their own list. Evidence: 10 of 14 queue rows are reviews; the 4 real actions drown.
2. **Sample results by "load-bearing", not recency** (C4, §3.4/3.5): e.g., "the ten most recent *plus any result cited as evidence by an included entry*". Evidence: stripe 0/168 and the cohort definition are the project's spine and fell out of a recency window that one busy week saturated.
3. **A phase status for open-but-displaced** (`stalled` or allow `parked` on phases) (C2). Evidence: P-01 — roadmap-owed, untouched for a month, wrongly reads as "being worked" under `active`.
4. **A weak influence link** (`informs: [ids]`) distinct from `evidence`/`depends_on` (C3). Evidence: R-003→D-011 (a null that reshapes a decision's basis), R-001→P-04 (partial delivery), R-004→P-05 (reshapes scope).
5. **A `reference` pointer type or explicit non-goal statement** (C8): one entry kind for "durable dossier/report a navigator opens", with the body being just a pointer. Evidence: 10 NONE rows and both legacy-HTML losses are this one kind; today the schema can only cite them from other entries' `source`.

## Appendix: entry index
| id | type | status | owner | basis | title |
|---|---|---|---|---|---|
| A-001 | aim | active | agent | recorded | Objective metrics that track recording quality as an implant ages |
| A-002 | aim | active | agent | recorded | Re-examine the published L1-coating yield claim on the full cohort |
| A-003 | aim | active | agent | recorded | A pipeline a new student can run end to end, MATLAB-consumable |
| P-01 | phase | active | agent | recorded | Roadmap Phase 1: single-sorter longitudinal baseline |
| P-02 | phase | done | agent | recorded | Cross-subject corpus and provenance |
| P-03 | phase | active | agent | inferred | Scientific campaigns on the corpus |
| P-04 | phase | active | agent | recorded | Roadmap Phase 2: multi-sorter consensus as a longitudinal metric |
| P-05 | phase | proposed | agent | recorded | Roadmap Phase 3: curation methods |
| P-06 | phase | proposed | agent | recorded | Roadmap Phase 4: full cohort and NeuroNexus 16ch |
| P-07 | phase | active | agent | recorded | Impedance integration (deferred 'Phase 5', running early) |
| P-08 | phase | proposed | agent | recorded | Endpoint histology registration |
| D-001 | decision | accepted | agent | recorded | Read the band from the nsX extended header, never from the suffix |
| D-002 | decision | accepted | agent | recorded | Never pool numerator and denominator across sessions |
| D-003 | decision | accepted | agent | recorded | Snippet-only cohorts are sorted per-electrode (ISO-SPLIT) |
| D-004 | decision | accepted | agent | recorded | No UnitRefine on snippet data; physics gate curates |
| D-005 | decision | accepted | agent | recorded | Resolve serials by (subject, implant, array) |
| D-006 | decision | accepted | agent | recorded | Blackrock impedance joins on channel_id (1248/1248) |
| D-007 | decision | accepted | agent | recorded | Fisk's .ns3 stays out of the pipeline |
| D-008 | decision | accepted | agent | recorded | Stripe axis = CMP col; even cols L1; anterior = TNP |
| D-009 | decision | accepted | agent | recorded | Open/short flags are chain diagnostics, not electrode states |
| D-010 | decision | accepted | agent | inferred | Min_P2P_exclusion never applied unless requested |
| D-011 | decision | proposed | human | recorded | Adopt the authored potentiostat channel map |
| R-001 | result | current | human | recorded | Four-sorter agreement uniform; collapses on dying arrays |
| R-002 | result | current | human | recorded | Rocky I2 border below interior; I1 opposite |
| R-003 | result | current | human | recorded | Three channel-map arbiters null |
| R-004 | result | current | human | recorded | UnitRefine discriminative on recording-backed analyzers |
| R-005 | result | current | human | recorded | Coated array ~2x impedance, flips with pedestal |
| R-006 | result | current | human | recorded | Pooled stripe permutation null; bound 21.7% / 5.5% |
| R-007 | result | current | human | recorded | Rocky edge contrast widens from bench over 7 years |
| R-008 | result | current | human | recorded | Fisk .ns3 reproduces band-matched .ns6 |
| R-009 | result | current | human | recorded | Edge effect absent at factory, grows in tissue |
| R-010 | result | current | human | recorded | Treatment contrast consistent only on the pedestal axis |
| I-001 | issue | resolved | agent | recorded | 431 Rocky I1 sessions carried I2 serials |
| I-002 | issue | open | agent | recorded | Navigation documents lag the project by weeks |
| Q-001 | question | open | agent | recorded | Is Fisk's stripe assignment correct? |
| Q-002 | question | open | agent | recorded | What sets the implant-level ephys edge sign? |
| Q-003 | question | open | agent | recorded | Does the acquired edge effect appear in Nigel, map-free? |
| Q-004 | question | open | external | recorded | What probe do Picasso and Luigi carry? |
| Q-005 | question | open | agent | recorded | Why do Picasso recordings continue past pedestal failures? |
| Q-006 | question | parked | external | recorded | Coating effect below the ~22% bound? |
| Q-007 | question | open | agent | recorded | How deep can Luigi go? |
| Q-008 | question | open | agent | inferred | Does agreement structure track quality better than counts? |
| W-001 | work | proposed | human | recorded | Copy the census-located legacy files |
| W-002 | work | blocked | agent | recorded | Ingest Nigel impedance; second map-free edge test |
| W-003 | work | blocked | agent | recorded | Re-run stripes with Fisk verified |
| W-004 | work | blocked | agent | recorded | Per-electrode impedance joins under the settled map |
| W-005 | work | proposed | human | recorded | Locate or rule out Rocky I2 potentiostat dumps |
| W-006 | work | proposed | agent | recorded | Nigel NEUN histology-ephys join |
| W-007 | work | parked | agent | recorded | ElectrodeMetadata, src/ promotion, Tier-1 tests |
| W-008 | work | parked | agent | recorded | Phase 1 validation spec and sign-off |
| W-009 | work | proposed | agent | recorded | Close the ns5_plan items |
| W-010 | work | proposed | agent | recorded | Per-channel NEV match recompute |
| W-011 | work | proposed | human | recorded | Refresh the two published dashboards |
| W-012 | work | proposed | agent | recorded | Validate continuous-arm UnitRefine vs human curators |
| W-013 | work | proposed | agent | recorded | Bombcell with sparse-array-retuned thresholds |
| W-014 | work | proposed | agent | recorded | NeuroNexus 16ch support |
| W-015 | work | parked | agent | recorded | Recover a physical scale for TDT pNe LFP |
| W-016 | work | active | external | recorded | Census session drive sweep |

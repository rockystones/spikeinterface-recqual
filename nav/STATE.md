# STATE: recqual, generated 2026-09-12 from nav/entries (by hand, pilot)

## Aim
*(template expects one aim; this project carries three — see report)*
- **A-001** Objective metrics that track recording quality as an implant ages. Success: the three-layer metric stack validated longitudinally across the cohort and two probe types, with agreement *structure* as the headline metric. Approach: scratch-first SpikeInterface pipeline under the aggregation rule, both data regimes as equals, consensus never collapsed.
- **A-002** Re-examine the published L1-coating yield claim. Success: coating separated from pedestal/animal confounds or explicitly bounded. Approach: within-session pairing and the cohort's own deconfounds (opposed arrangements, stripes, Rocky I2's fourth arrangement).
- **A-003** A pipeline a new student can run end to end, MATLAB-consumable. Success: promoted `src/` modules, tests, tutorials. Approach: scratch-first, promote at phase boundaries (nothing promoted yet).

## Pending from the human, ranked by what each unblocks
1. **W-001** (work, proposed): Copy the census-located legacy files. **Unblocks: Q-001, W-002, Q-003 → W-003.**
2. **D-011** (decision, proposed): Adopt the authored potentiostat channel map. **Unblocks: W-004**; firms the R-007 interpretation. (Empirical arbiters are null — R-003 — so this is now a documentary call.)
3. **W-005** (work, proposed): Locate or rule out 2025 potentiostat dumps for Rocky I2 — the one clean remaining validator feeding D-011.
4. **W-011** (work, proposed): Approve refreshing the two published dashboards (frozen 2026-08-22/23; standing instruction was commit-but-don't-publish).
5. **R-001 … R-010** (results, current): ten unreviewed results from 2026-08-24 → 09-12 await review; none blocks work.

## Phase and position
Current phase: **P-03 Scientific campaigns on the corpus** (active). Phases: P-01 active (`x_status_wanted: stalled` — displaced, debts owed), P-02 done, P-03 active, P-04 active (partially realized out of order by R-001), P-05 proposed (reshaped by R-004), P-06 proposed, P-07 active (running early), P-08 proposed.
Active work: **W-016** (external — census session sweeping drives, downhill). No agent-active work item is open; the queue is blocked/proposed.
Blocked: W-002 on W-001 · W-003 on Q-001 · W-004 on D-011.

## Accepted decisions, latest first (max 10)
- D-005: Resolve array serials by (subject, implant, array), never (subject, array)
- D-007: Fisk's .ns3 stays out of the pipeline
- D-009: Potentiostat open/short flags are chain diagnostics, not electrode states
- D-001: Read the band from the nsX extended header, never the suffix
- D-006: Blackrock impedance joins on channel_id (proven 1248/1248)
- D-008: Stripes run along CMP col; even cols L1; Nigel anterior = TNP (owner-confirmed)
- D-002: Never pool numerator/denominator across sessions; pair within session
- D-004: No UnitRefine on snippet data; the physics gate is the curation layer
- D-010: Min_P2P_exclusion = 20 µV never applied unless explicitly requested
- D-003: Snippet cohorts sorted per-electrode (ISO-SPLIT), as the correct method

## What worked and what didn't, latest first (max 10)
- R-001 (measured): Four-sorter agreement uniform (0.27–0.34); collapses exactly on dying arrays
- R-002 (measured): Rocky I2 border 26–38% *below* interior; I1 ran the opposite way — edge sign is implant-level
- R-003 (inconclusive): Three empirical channel-map arbiters all null
- R-004 (works): UnitRefine discriminative on recording-backed analyzers (54–68% neural)
- R-005 (works): Coated array ≈2× impedance on 18/19 chronic paired dates, flipping with pedestal
- R-006 (measured): Pooled stripe permutation null; detectable bound 21.7% yield / 5.5% noise
- R-007 (measured): Rocky's impedance edge contrast widens from bench over 7 years
- R-008 (measured): Fisk .ns3 reproduces band-matched .ns6 (ρ≈0.99) — redundant
- R-009 (works): Impedance edge effect absent at factory, grows in tissue (paired bench anchor)
- R-010 (measured): Treatment contrast consistent only on the pedestal axis, four arrangements

## Open questions and issues
- Q-001 open (agent, depends W-001): Is Fisk's stripe assignment correct? (credence 0.8 it is)
- Q-002 open (agent): What sets the implant-level ephys edge sign?
- Q-003 open (agent, depends W-001/W-002): Does the acquired edge effect appear in Nigel, map-free?
- Q-004 open (external): What probe do Picasso and Luigi carry?
- Q-005 open (agent): Why do Picasso recordings continue past the documented pedestal failures?
- Q-007 open (agent): How deep can Luigi go with no impedance, no map, 148 undated tanks?
- Q-008 open (agent): Does agreement structure track quality better than single-sorter counts? (the headline bet, credence 0.75)
- I-002 open (agent): Navigation documents lag the project by weeks (roadmap pointer says "next: S6" at S14; HANDOFF pre-pivot; two answered questions still listed open; dashboards frozen)

## Parked
- W-007: ElectrodeMetadata, src/ promotion, Tier-1 tests. Wake: first cross-session API consumer, or a Phase-1 close push.
- W-008: Phase 1 validation spec + Plexon sign-off + tag. Wake: P-01 resumes.
- W-015: Physical scale for TDT pNe LFP. Wake: a scale source surfaces.
- Q-006: Coating effect below the ~22% bound. Wake: more striped arrays/animals enter the estate.

## Next action
Human: copy the census files (W-001) and rule on the channel map (D-011) — then the agent runs W-002 → Q-003, W-003, and W-004 in that order.

# STATE: SpikeInterface  (as of 513d739 2026-09-17; generated 2026-09-17; last reviewed 2026-09-12)

## Aims
- A-001 (active): Objective metrics that track recording quality as an implant ages
  Scope: seven animals (Chase, Luigi, Oops, Picasso, Rocky I1+I2, Nigel, Fisk), three acquisition regimes, >1,100 analyzed session-arrays 2013-2025, Utah 96ch primary
- A-002 (active): Re-examine the published L1-coating yield claim on the full cohort
  Scope: four whole-array L1 animals, two striped animals (four arrays, 10 stripes/condition), one TNP vs TNP-L1 pair (Rocky I2)
- A-003 (active): A pipeline a new student can run end to end, MATLAB-consumable
  Scope: src/recqual package + parallel MATLAB layer; nothing promoted from notebooks yet

## Waiting on you
Everything in this section is gated on the human (actor or gate = human). Ranked by horizon, then by how much each item unblocks, then by how long it has waited. Lapse threshold 21 days.

### Act now
1. W-001 (work, proposed): Copy the census-located legacy files onto a reachable drive  [now] asked 2026-09-12
  Why: Unblocks the Fisk stripe verification, Nigel impedance, and edge-generalization chain
   Unblocks: Q-001, Q-003, W-002, W-003, W-020
2. D-011 (decision, proposed): Adopt the authored potentiostat channel map over the naive sweep-order map  [now] asked 2026-09-12
  Why: Candidates agree on 0/96 channels; three empirical arbiters null, so a documentary call
   Unblocks: W-004
3. W-011 (work, proposed): Retire or redirect the published dashboard pages  [now] asked 2026-08-24 LAPSED
  Why: Repo copies superseded by NAV.html (D-012); the published claude.ai pages remain stale online
   Unblocks: nothing recorded
4. W-005 (work, proposed): Locate (or rule out) 2025 potentiostat dumps for Rocky I2 - the map-transfer test  [now] asked 2026-09-12
  Why: The one clean remaining validator for the channel map: same cable, new arrays
   Unblocks: nothing recorded

### Later (something else must close first)
(nothing)

### Review (results you have not marked reviewed; most cited first)
- R-016 (result, current): Consensus replaces the human sort as a yield tracker, not as a unit inventory [cited 3x]
- R-013 (result, current): Nigel and Fisk derivation chains validate to the Rocky standard [cited 2x]
- R-014 (result, current): TDT maxsigM verified as the legacy mean-max-amplitude structure; maxsig field is a trap [cited 1x]
- R-017 (result, current): The Rocky I1 coated/uncoated contrast survives every measurement chain [cited 1x]
- R-019 (result, current): Sorter agreement declines with implant age on dying arrays and only there [cited 1x]
- R-015 (result, current): Exact mean-max-P2P computed for the whole cohort; both eras tabled as a default metric [cited 0x]
- R-018 (result, current): Gated ISO-SPLIT on snippets behaves like a member of the modern sorter pool [cited 0x]
- R-020 (result, current): rho_hat = 0.24 - the within-array design effect measured on the cohort [cited 0x]

### Lapsed (no update in more than 21 days; decide, park with a trigger, or abandon)
- W-011 (proposed, 24 days): Retire or redirect the published dashboard pages

## Phase and position
Planned order: P-01 parked · P-02 done · P-03 active · P-04 active · P-05 proposed · P-06 proposed · P-07 active · P-08 proposed
- P-01 (parked): Roadmap Phase 1: single-sorter longitudinal baseline
- P-02 (done, closed 2026-08-24): Cross-subject corpus and provenance (supersedes the near-term phase sequence)
- P-03 (active): Scientific campaigns on the corpus (treatment, geometry, impedance, consensus)
- P-04 (active): Roadmap Phase 2: multi-sorter consensus as a longitudinal metric
- P-05 (proposed): Roadmap Phase 3: curation methods (UnitRefine, Bombcell)
- P-06 (proposed): Roadmap Phase 4: full cohort and NeuroNexus 16ch
- P-07 (active): Impedance integration (deferred 'Phase 5', running early)
- P-08 (proposed): Endpoint histology registration (with imaging as a later sibling)
Active work:
- W-002 blocked [P-07]: Ingest Nigel's impedance record; run the map-free edge test on a second animal blocked on W-001 trigger: W-001 files land on a reachable drive
- W-003 blocked [P-03]: Re-run the stripe analysis with Fisk's assignment verified blocked on Q-001 trigger: Q-001 answered by the by-location workbook
- W-004 blocked [P-07]: Per-electrode impedance-ephys joins under the settled channel map blocked on D-011 trigger: D-011 accepted
- W-016 active (downhill) [P-03]: Census session: locate monkey-relevant material across the drive estate
- W-020 active (uphill) [P-03]: Execute the within-array variance-analysis brief on the cohort in hand

## Standing decisions (pinned)
- D-001 (decision, accepted): Read the band from the nsX extended header, never from the suffix
  Why: Both suffix conventions are wrong here; 498/626 continuous files are high-passed
- D-002 (decision, accepted): Never pool numerator and denominator across sessions; pair within session
  Why: Pooled ratios mis-stated findings by 661x and 5.1x; one produced a confident wrong conclusion
- D-003 (decision, accepted): Snippet-only cohorts are sorted per-electrode (ISO-SPLIT), as the correct method
  Why: At 400 um pitch a neuron appears on one electrode; per-electrode clustering is the correct method
- D-004 (decision, accepted): Do not use UnitRefine on snippet data; the physics gate is the curation layer
  Why: Seven required features need continuous traces; imputing them saturates the classifier at noise
- D-006 (decision, accepted): Blackrock impedance joins recordings on channel_id (proven 1248/1248)
  Why: The factory workbook's elecN row headers are a misnomer; rows are channel-indexed, proven 1248/1248
- D-012 (decision, accepted): The nav ledger is the project's navigation system; NAV.html supersedes the dashboards
  Why: Cross-session memory lives in nav/entries; STATE.md is the orientation page; generated files are never hand-edited

## Recent decisions (accepted, latest first, max 10)
- D-013 (decision, accepted): Mean max peak-to-peak amplitude is a default sorted metric for every monkey  [decided by human]
  Why: Legacy MATLAB metric: per active channel take the largest-P2P unit, average across channels; owner ruled it a cohort default
- D-005 (decision, accepted): Resolve array serials by (subject, implant, array), never (subject, array)  [decided by agent]
  Why: Rocky's implants reuse array labels; the collapsed key mislabelled 431 sessions
- D-007 (decision, accepted): Fisk's .ns3 stays out of the pipeline  [decided by agent]
  Why: A 300 Hz high-passed band-limited copy of the .ns6; one sampled file all-zero
- D-009 (decision, accepted): Potentiostat open/short flags are measurement-chain diagnostics, not electrode states  [decided by agent]
  Why: Potentiostat opens sit at ephys percentile ~0.5 under every candidate map
- D-008 (decision, accepted): Stripes run along CMP col; even cols carry L1; Nigel anterior is TNP (owner-confirmed)  [decided by human]
  Why: The schematic panels beat the transposed implant table; owner ruled anterior = TNP
- D-010 (decision, accepted, inferred): Min_P2P_exclusion = 20 uV is not applied anywhere unless explicitly requested  [decided by human]
  Why: Owner's standing ruling, chat-only provenance; never apply the legacy threshold silently

## What worked and what didn't (results; most cited first, then latest; max 12)
- R-001 (result, current, measured): Four-sorter agreement is uniform (0.27-0.34) and collapses exactly on dying arrays
- R-016 (result, current): Consensus replaces the human sort as a yield tracker, not as a unit inventory
- R-003 (result, current, inconclusive): Three empirical channel-map arbiters (bench x2 animals, open/short, border) are null
- R-013 (result, current): Nigel and Fisk derivation chains validate to the Rocky standard
- R-009 (result, current, works): Impedance edge effect is absent at the factory and grows in tissue (Fisk, paired bench anchor)
- R-002 (result, current, measured): Rocky I2 (fresh) has border 26-38% below interior; I1 ran the opposite way
- R-004 (result, current, works): UnitRefine is discriminative on recording-backed analyzers (54-68% neural)
- R-006 (result, current, measured): Pooled four-array stripe permutation: null; detectable bound 21.7% yield / 5.5% noise
- R-007 (result, current, measured): Rocky's impedance edge contrast widens from its bench value over 7 years
- R-008 (result, current, measured): Fisk .ns3 reproduces band-matched .ns6 noise at rho 0.94-0.996, x1.19 scale
- R-012 (result, current, works): The Rocky derivation chain is deterministic and MATLAB-validated end to end
- R-014 (result, current): TDT maxsigM verified as the legacy mean-max-amplitude structure; maxsig field is a trap

## Open questions and issues
- I-006 (open, agent): Host nonpaged-pool leak under sustained sorting I/O starves the machine.
- Q-001 (open, agent) blocks W-003, W-020: Is Fisk's stripe assignment (carried from Nigel by design) correct?. Prediction: the by-location workbook confirms even-col L1 on both Fisk arrays (credence 0.8)
- Q-002 (open, agent): What sets the implant-level ephys edge sign?. Prediction: insertion mechanics / perimeter trauma at implantation, fixed per implant (credence 0.5)
- Q-003 (open, agent): Does the acquired impedance edge effect appear in a second map-free animal (Nigel)?. Prediction: Nigel's 362 impedance files show border below interior, widening with age (credence 0.7)
- Q-004 (open, external): What probe do Picasso and Luigi actually carry?. Prediction: Utah 96 for both (assumed throughout the legacy material) (credence 0.85)
- Q-005 (open, agent): Why do Picasso recordings continue past the documented pedestal failures?. Prediction: label reuse or failure-date error rather than recording through a failed pedestal (credence 0.6)
- Q-007 (open, agent): How deep can Luigi's analysis go given no impedance, no map, and 148 undated tanks?. Prediction: session-level yield trends only; nothing per-electrode is recoverable (credence 0.7)
- Q-008 (open, agent): Does the agreement structure track recording quality better than single-sorter counts?. Prediction: the consensus ladder is the more specific longitudinal metric, especially near array death (credence 0.75)

## Parked and standing (with triggers)
- P-01 (phase, parked): Roadmap Phase 1: single-sorter longitudinal baseline. Trigger: a Phase-1 close push, or the first external consumer of a promoted API
- Q-006 (question, parked): Does a coating effect exist below the ~22% pooled detection bound?. Trigger: more striped arrays or animals enter the estate
- W-007 (work, parked): ElectrodeMetadata dataclass, src/ promotion, Tier-1 tests. Trigger: first cross-session consumer of a promoted API (MATLAB layer or the histology join), or a Phase-1 close push
- W-008 (work, parked): Phase 1 validation spec, Plexon-comparison sign-off, phase tag and tutorial. Trigger: P-01 resumes
- W-015 (work, parked): Recover a physical scale for the TDT pNe LFP stores. Trigger: a scale source surfaces: rig notes, TDT circuit files, or a matched Blackrock-TDT session pair

## Next action
W-001: Copy the census-located legacy files onto a reachable drive (yours; unblocks 5)

## Since your last review
Anchor 137d99e (2026-09-12): 25 new, 57 changed, 1 closed, 1 still waiting on you from before. Details in DELTA.md.

## Vocabulary
hill: uphill = still working out how; crest = approach settled, work not started; downhill = known work remaining. horizon: now/next/later, the project's own priority among open items. gate human: an agent task that needs your go. pinned: a decision that explains why the project is built this way. retracted: a result that was wrong; superseded: outdated but was right at the time. basis inferred: reconstructed by an agent, not read from a record.

Project vocabulary (appended to STATE.md; keep it to terms a cold reader would otherwise not know):
-

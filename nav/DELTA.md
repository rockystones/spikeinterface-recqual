# DELTA: SpikeInterface  (generated 2026-09-17)

Since last-review 137d99e (2026-09-12), as of 513d739 (2026-09-17).

## New
- D-012 (decision, accepted): The nav ledger is the project's navigation system; NAV.html supersedes the dashboards
- D-013 (decision, accepted): Mean max peak-to-peak amplitude is a default sorted metric for every monkey
- I-003 (issue, resolved): Rocky NEV estate moved; session_index paths went stale
- I-004 (issue, resolved): Duplicate sorted NEV copies let stem lookups pick a test-vintage sort
- I-005 (issue, resolved): NEV stamps trail the continuous stream by a fixed lag; pooled recovery fractions are chance-saturated
- I-006 (issue, open): Host nonpaged-pool leak under sustained sorting I/O starves the machine
- Q-009 (question, answered): Can multi-sorter consensus replace the human Plexon sorting?
- Q-010 (question, answered): Does the coating contrast survive the choice of metric?
- R-011 (result, current, measured): Peri-shank NEUN deficit recovers by ~75-100 um and is worst near the surface
- R-012 (result, current, works): The Rocky derivation chain is deterministic and MATLAB-validated end to end
- R-013 (result, current): Nigel and Fisk derivation chains validate to the Rocky standard
- R-014 (result, current): TDT maxsigM verified as the legacy mean-max-amplitude structure; maxsig field is a trap
- R-015 (result, current): Exact mean-max-P2P computed for the whole cohort; both eras tabled as a default metric
- R-016 (result, current): Consensus replaces the human sort as a yield tracker, not as a unit inventory
- R-017 (result, current): The Rocky I1 coated/uncoated contrast survives every measurement chain
- R-018 (result, current): Gated ISO-SPLIT on snippets behaves like a member of the modern sorter pool
- R-019 (result, current): Sorter agreement declines with implant age on dying arrays and only there
- R-020 (result, current): rho_hat = 0.24 - the within-array design effect measured on the cohort
- REF-001 (ref, current): Map of the preserved sorting results and how to inspect them
- REF-002 (ref, current): Provenance store - full derivation chains for nine sessions across three subjects
- REF-003 (ref, current): Waveform catalog - 13,321 unit shapes, 10 sorting chains, 6 monkeys
- W-017 (work, done): Compute mean-max-P2P longitudinally for the cohort (Rocky first)
- W-018 (work, done): Provenance dump and MATLAB validation for Nigel and Fisk sessions
- W-019 (work, done): Expand the modern-sorter pool to Rocky same-day pairs and cohort breadth
- W-020 (work, active): Execute the within-array variance-analysis brief on the cohort in hand

## Status changed
- A-001: active -> active (body edited): Objective metrics that track recording quality as an implant ages
- A-002: active -> active (body edited): Re-examine the published L1-coating yield claim on the full cohort
- A-003: active -> active (body edited): A pipeline a new student can run end to end, MATLAB-consumable
- D-001: accepted -> accepted (body edited): Read the band from the nsX extended header, never from the suffix
- D-002: accepted -> accepted (body edited): Never pool numerator and denominator across sessions; pair within session
- D-003: accepted -> accepted (body edited): Snippet-only cohorts are sorted per-electrode (ISO-SPLIT), as the correct method
- D-004: accepted -> accepted (body edited): Do not use UnitRefine on snippet data; the physics gate is the curation layer
- D-005: accepted -> accepted (body edited): Resolve array serials by (subject, implant, array), never (subject, array)
- D-006: accepted -> accepted (body edited): Blackrock impedance joins recordings on channel_id (proven 1248/1248)
- D-007: accepted -> accepted (body edited): Fisk's .ns3 stays out of the pipeline
- D-008: accepted -> accepted (body edited): Stripes run along CMP col; even cols carry L1; Nigel anterior is TNP (owner-confirmed)
- D-009: accepted -> accepted (body edited): Potentiostat open/short flags are measurement-chain diagnostics, not electrode states
- D-010: accepted -> accepted (body edited): Min_P2P_exclusion = 20 uV is not applied anywhere unless explicitly requested
- D-011: proposed -> proposed (body edited): Adopt the authored potentiostat channel map over the naive sweep-order map
- I-001: resolved -> resolved (body edited): 431 Rocky I1 sessions carried I2 serials (collapsed lookup key)
- P-01: active -> parked: Roadmap Phase 1: single-sorter longitudinal baseline
- P-02: done -> done (body edited): Cross-subject corpus and provenance (supersedes the near-term phase sequence)
- P-03: active -> active (body edited): Scientific campaigns on the corpus (treatment, geometry, impedance, consensus)
- P-04: active -> active (body edited): Roadmap Phase 2: multi-sorter consensus as a longitudinal metric
- P-05: proposed -> proposed (body edited): Roadmap Phase 3: curation methods (UnitRefine, Bombcell)
- P-06: proposed -> proposed (body edited): Roadmap Phase 4: full cohort and NeuroNexus 16ch
- P-07: active -> active (body edited): Impedance integration (deferred 'Phase 5', running early)
- P-08: proposed -> proposed (body edited): Endpoint histology registration (with imaging as a later sibling)
- Q-001: open -> open (body edited): Is Fisk's stripe assignment (carried from Nigel by design) correct?
- Q-002: open -> open (body edited): What sets the implant-level ephys edge sign?
- Q-003: open -> open (body edited): Does the acquired impedance edge effect appear in a second map-free animal (Nigel)?
- Q-004: open -> open (body edited): What probe do Picasso and Luigi actually carry?
- Q-005: open -> open (body edited): Why do Picasso recordings continue past the documented pedestal failures?
- Q-006: parked -> parked (body edited): Does a coating effect exist below the ~22% pooled detection bound?
- Q-007: open -> open (body edited): How deep can Luigi's analysis go given no impedance, no map, and 148 undated tanks?
- Q-008: open -> open (body edited): Does the agreement structure track recording quality better than single-sorter counts?
- R-001: current -> current (body edited): Four-sorter agreement is uniform (0.27-0.34) and collapses exactly on dying arrays
- R-002: current -> current (body edited): Rocky I2 (fresh) has border 26-38% below interior; I1 ran the opposite way
- R-003: current -> current (body edited): Three empirical channel-map arbiters (bench x2 animals, open/short, border) are null
- R-004: current -> current (body edited): UnitRefine is discriminative on recording-backed analyzers (54-68% neural)
- R-005: current -> current (body edited): Coated array sits ~2x higher impedance on 18/19 chronic paired dates, flipping with pedestal
- R-006: current -> current (body edited): Pooled four-array stripe permutation: null; detectable bound 21.7% yield / 5.5% noise
- R-007: current -> current (body edited): Rocky's impedance edge contrast widens from its bench value over 7 years
- R-008: current -> current (body edited): Fisk .ns3 reproduces band-matched .ns6 noise at rho 0.94-0.996, x1.19 scale
- R-009: current -> current (body edited): Impedance edge effect is absent at the factory and grows in tissue (Fisk, paired bench anchor)
- R-010: current -> current (body edited): Treatment contrast is consistent only on the pedestal axis; coating and cortex axes reverse
- W-001: proposed -> proposed (body edited): Copy the census-located legacy files onto a reachable drive
- W-002: blocked -> blocked (body edited): Ingest Nigel's impedance record; run the map-free edge test on a second animal
- W-003: blocked -> blocked (body edited): Re-run the stripe analysis with Fisk's assignment verified
- W-004: blocked -> blocked (body edited): Per-electrode impedance-ephys joins under the settled channel map
- W-005: proposed -> proposed (body edited): Locate (or rule out) 2025 potentiostat dumps for Rocky I2 - the map-transfer test
- W-006: proposed -> proposed (body edited): Register Nigel's NEUN histology to electrodes; first histology-ephys join
- W-007: parked -> parked (body edited): ElectrodeMetadata dataclass, src/ promotion, Tier-1 tests
- W-008: parked -> parked (body edited): Phase 1 validation spec, Plexon-comparison sign-off, phase tag and tutorial
- W-009: proposed -> proposed (body edited): Close the ns5_plan items: fixed-threshold vs snippet yield; giant-site trace pulls
- W-010: proposed -> proposed (body edited): Recompute NEV match rates per channel (match_is_pooled flag)
- W-011: proposed -> proposed (body edited): Retire or redirect the published dashboard pages
- W-012: proposed -> proposed (body edited): Validate continuous-arm UnitRefine against the human curator trees (DS, Sidd)
- W-013: proposed -> proposed (body edited): Bombcell with sparse-array-retuned thresholds
- W-014: proposed -> proposed (body edited): NeuroNexus 16ch linear probe support and cross-probe consistency check
- W-015: parked -> parked (body edited): Recover a physical scale for the TDT pNe LFP stores
- W-016: active -> active (body edited): Census session: locate monkey-relevant material across the drive estate

## Closed
- I-002: open -> resolved: Navigation documents lag the project by weeks (roadmap pointer, HANDOFF, cross_subject open items, artifacts)

## Still waiting on you from before the anchor
- W-011 (work, proposed): Retire or redirect the published dashboard pages

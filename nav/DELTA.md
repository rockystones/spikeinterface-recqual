# DELTA: SpikeInterface  (generated 2026-09-13)

Since last-review 137d99e (2026-09-12), as of 137d99e (2026-09-12).

## New
(none)

## Status changed
- A-001: None -> active (uncommitted): Objective metrics that track recording quality as an implant ages
- A-002: None -> active (uncommitted): Re-examine the published L1-coating yield claim on the full cohort
- A-003: None -> active (uncommitted): A pipeline a new student can run end to end, MATLAB-consumable
- D-001: None -> accepted (uncommitted): Read the band from the nsX extended header, never from the suffix
- D-002: None -> accepted (uncommitted): Never pool numerator and denominator across sessions; pair within session
- D-003: None -> accepted (uncommitted): Snippet-only cohorts are sorted per-electrode (ISO-SPLIT), as the correct method
- D-004: None -> accepted (uncommitted): Do not use UnitRefine on snippet data; the physics gate is the curation layer
- D-005: None -> accepted (uncommitted): Resolve array serials by (subject, implant, array), never (subject, array)
- D-006: None -> accepted (uncommitted): Blackrock impedance joins recordings on channel_id (proven 1248/1248)
- D-007: None -> accepted (uncommitted): Fisk's .ns3 stays out of the pipeline
- D-008: None -> accepted (uncommitted): Stripes run along CMP col; even cols carry L1; Nigel anterior is TNP (owner-confirmed)
- D-009: None -> accepted (uncommitted): Potentiostat open/short flags are measurement-chain diagnostics, not electrode states
- D-010: None -> accepted (uncommitted): Min_P2P_exclusion = 20 uV is not applied anywhere unless explicitly requested
- D-011: None -> proposed (uncommitted): Adopt the authored potentiostat channel map over the naive sweep-order map
- I-001: None -> resolved (uncommitted): 431 Rocky I1 sessions carried I2 serials (collapsed lookup key)
- I-002: None -> resolved (uncommitted): Navigation documents lag the project by weeks (roadmap pointer, HANDOFF, cross_subject open items, artifacts)
- P-01: None -> parked (uncommitted): Roadmap Phase 1: single-sorter longitudinal baseline
- P-02: None -> done (uncommitted): Cross-subject corpus and provenance (supersedes the near-term phase sequence)
- P-03: None -> active (uncommitted): Scientific campaigns on the corpus (treatment, geometry, impedance, consensus)
- P-04: None -> active (uncommitted): Roadmap Phase 2: multi-sorter consensus as a longitudinal metric
- P-05: None -> proposed (uncommitted): Roadmap Phase 3: curation methods (UnitRefine, Bombcell)
- P-06: None -> proposed (uncommitted): Roadmap Phase 4: full cohort and NeuroNexus 16ch
- P-07: None -> active (uncommitted): Impedance integration (deferred 'Phase 5', running early)
- P-08: None -> proposed (uncommitted): Endpoint histology registration (with imaging as a later sibling)
- Q-001: None -> open (uncommitted): Is Fisk's stripe assignment (carried from Nigel by design) correct?
- Q-002: None -> open (uncommitted): What sets the implant-level ephys edge sign?
- Q-003: None -> open (uncommitted): Does the acquired impedance edge effect appear in a second map-free animal (Nigel)?
- Q-004: None -> open (uncommitted): What probe do Picasso and Luigi actually carry?
- Q-005: None -> open (uncommitted): Why do Picasso recordings continue past the documented pedestal failures?
- Q-006: None -> parked (uncommitted): Does a coating effect exist below the ~22% pooled detection bound?
- Q-007: None -> open (uncommitted): How deep can Luigi's analysis go given no impedance, no map, and 148 undated tanks?
- Q-008: None -> open (uncommitted): Does the agreement structure track recording quality better than single-sorter counts?
- R-001: None -> current (uncommitted): Four-sorter agreement is uniform (0.27-0.34) and collapses exactly on dying arrays
- R-002: None -> current (uncommitted): Rocky I2 (fresh) has border 26-38% below interior; I1 ran the opposite way
- R-003: None -> current (uncommitted): Three empirical channel-map arbiters (bench x2 animals, open/short, border) are null
- R-004: None -> current (uncommitted): UnitRefine is discriminative on recording-backed analyzers (54-68% neural)
- R-005: None -> current (uncommitted): Coated array sits ~2x higher impedance on 18/19 chronic paired dates, flipping with pedestal
- R-006: None -> current (uncommitted): Pooled four-array stripe permutation: null; detectable bound 21.7% yield / 5.5% noise
- R-007: None -> current (uncommitted): Rocky's impedance edge contrast widens from its bench value over 7 years
- R-008: None -> current (uncommitted): Fisk .ns3 reproduces band-matched .ns6 noise at rho 0.94-0.996, x1.19 scale
- R-009: None -> current (uncommitted): Impedance edge effect is absent at the factory and grows in tissue (Fisk, paired bench anchor)
- R-010: None -> current (uncommitted): Treatment contrast is consistent only on the pedestal axis; coating and cortex axes reverse
- W-001: None -> proposed (uncommitted): Copy the census-located legacy files onto a reachable drive
- W-002: None -> blocked (uncommitted): Ingest Nigel's impedance record; run the map-free edge test on a second animal
- W-003: None -> blocked (uncommitted): Re-run the stripe analysis with Fisk's assignment verified
- W-004: None -> blocked (uncommitted): Per-electrode impedance-ephys joins under the settled channel map
- W-005: None -> proposed (uncommitted): Locate (or rule out) 2025 potentiostat dumps for Rocky I2 - the map-transfer test
- W-006: None -> proposed (uncommitted): Register Nigel's NEUN histology to electrodes; first histology-ephys join
- W-007: None -> parked (uncommitted): ElectrodeMetadata dataclass, src/ promotion, Tier-1 tests
- W-008: None -> parked (uncommitted): Phase 1 validation spec, Plexon-comparison sign-off, phase tag and tutorial
- W-009: None -> proposed (uncommitted): Close the ns5_plan items: fixed-threshold vs snippet yield; giant-site trace pulls
- W-010: None -> proposed (uncommitted): Recompute NEV match rates per channel (match_is_pooled flag)
- W-011: None -> proposed (uncommitted): Retire or redirect the published dashboard pages
- W-012: None -> proposed (uncommitted): Validate continuous-arm UnitRefine against the human curator trees (DS, Sidd)
- W-013: None -> proposed (uncommitted): Bombcell with sparse-array-retuned thresholds
- W-014: None -> proposed (uncommitted): NeuroNexus 16ch linear probe support and cross-probe consistency check
- W-015: None -> parked (uncommitted): Recover a physical scale for the TDT pNe LFP stores
- W-016: None -> active (uncommitted): Census session: locate monkey-relevant material across the drive estate
- D-012: None -> accepted (uncommitted): The nav ledger is the project's navigation system; NAV.html supersedes the dashboards
- R-011: None -> current (uncommitted): Peri-shank NEUN deficit recovers by ~75-100 um and is worst near the surface

## Closed
(none)

## Still waiting on you from before the anchor
- W-011 (work, proposed): Retire or redirect the published dashboard pages

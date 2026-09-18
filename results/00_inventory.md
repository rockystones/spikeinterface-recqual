# Step 0 inventory — variance-analysis brief, against the data in hand

Per `docs/notes/NHP_variance_analysis_brief.md` §1. Verdict up front:
**Analyses 1, 2, 3, 5(MDE) and 7 are runnable now, on more animals and
arrays than the brief assumes. Everything that needs the stripe
condition map (residualization for the striped cohort, TOST on the
stripe nulls, condition-vs-tether tables, spillover exposure) is
blocked on Q-001 / W-001.**

## 1. Granularity — YES, better than required
- `data/derived/cohort/mmp2p_shards/` — **per channel per session max
  peak-to-peak amplitude** (the brief's primary metric, exactly), 708
  sessions across Rocky I1+I2, Nigel, Fisk, one row per active channel.
- `rocky|rocky_i2/events_electrode.parquet` and the Fisk/Nigel
  equivalents — per channel per session sorting-free metrics (crossing
  rate, amp percentiles, noise floor).
- `rocky/units_long.parquet` — per UNIT per session (Rocky I1), two
  methods; channel yield derivable per channel per session everywhere.

## 2. Identifiers — YES
subject, array, stem (exact session), date, channel_id (Blackrock
electrode id) on every row. Rocky's two implants are disambiguated per
the serial-resolution rule (implant column via registry join).

## 3. Channel -> condition map — **THE BLOCKER**
- Rocky I1/I2, Oops, Picasso, Chase, Luigi: whole-array conditions,
  known and registry-recorded (configs/subjects). No within-array map
  needed.
- **Nigel and Fisk (the striped, within-array cohort the brief is
  about): the stripe map is NOT verified locally** — nav Q-001, waiting
  on the census-located legacy files (W-001). Until that lands, no
  analysis may condition on stripe identity.

## 4. Geometry — YES
CMP row/col per electrode (10x10), distance-to-edge, inner/outer, bank
membership all computed in the ring-geometry layer
(scratch_ring_geometry.py); wire-bundle exit edge known per array from
the .cmp/registry. Position EFFECTS are already measured facts here
(R-002/R-007/R-009: edge contrasts, within-animal sign flip).

## 5. Metrics per channel per session — YES
units (Rocky rich; all subjects via mmp2p n_units), active flag, max
P2P amplitude (all three Blackrock subjects), 1 kHz impedance per
channel per date for Rocky (52-date potentiostat record; channel-map
ruling D-011 pending); Nigel impedance blocked on W-002/W-003.

## 6. Exclusions — documented
No >3 MOhm rule applied upstream in the ephys tables. The S09
session-noise screen and the curated 27-session outlier list
(two_array_metrics is_outlier) are the operative exclusions; both are
toggleable, so the brief's "with and without" sensitivity is one flag.

## 7. Coverage
Rocky I1 2017-09..2023-10 (~160-170 sessions/array, weekly-ish), I2
2025 (10/array); Nigel 2023-01..2024-10 (79/array); Fisk 2023-06..
2025-05 (72-73/array). Month-post-implant binning already implemented
(30.44 d, surgery dates from registry).

## 8. Earlier 4-monkey cohort — YES, accessible
monkey_units_compiled.mat holds PER-CHANNEL PER-SESSION unit amplitude
sets (ragged sig arrays) for Chase.A, Oops.A/B, Picasso.A/B (215
sessions, uV-validated in R-014; Luigi session-level only). Channel
IDENTITY across sessions is not recorded there, so variance components
below the array level need care - but the sham-contrast resampling
(Analysis 1) is cross-sectional within month and fully runnable:
within-array splits, between-array within animal (2 animals with
pairs), between-subject on 4 animals. Dimensionless rho comparable
across cohorts per the brief's own rule.

## Deltas from the brief's assumptions (all favorable)
- Animals: 3 Blackrock (+4 TDT) vs the assumed 2. Arrays: 8 Blackrock
  (+6 TDT) vs the assumed 4 — sigma^2_D gets 8-14 arrays, sigma^2_A
  gets up to 7 animals.
- "Shank" == electrode on a Utah array (one electrode per shank); m =
  96 (or 48/condition on the striped arrays).
- Two relevant results already exist and should be cited by the
  manuscript session: the treatment-vs-position deconfound (W5: coating
  direction reverses across animals, pedestal direction does not) and
  the within-animal edge-effect sign flip (R-002) — direct evidence
  the framework's sigma^2_tauD (treatment x context) is not zero, its
  Section 4 point, made empirical.

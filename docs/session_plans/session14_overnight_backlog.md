# Session 14 — overnight: the no-blocking backlog, and two status confirmations

## Plan

Run everything on the Rocky/Nigel/Fisk backlog that needs no user decision and
no unmounted drive, and confirm two uncertain statuses (the ns5 multi-sorter
run; UnitRefine).

## Outcome

**Statuses confirmed.** (1) The ns5 resort finished at 238 stems × 4 sorters
(96% error-free) but never computed sorter-vs-sorter agreement, and the spike
trains were deleted except four Fisk stems. (2) UnitRefine was run properly on
the snippet cohort and fails there by input, not by model — confirmed tonight
by the recovery pilot below.

**Impedance.** Ingested the 16 never-ingested Rocky dates (2019-06..2021-07,
45/75-point ladders; header-delimited sweep chunking) → 52-date record. Three
map arbiters all null (bench-vs-factory ×2 animals, open/short, border), so
the map stays documentary; potentiostat "opens" don't replicate in ephys and
are retired as validators. Rocky's edge contrast widens from its bench value
over 7 years (Posterior ρ=−0.73, p=1e-09) — second animal for ring_geometry's
acquired edge effect. Oops/Picasso chronic ingested: coated array higher on
18/19 paired dates (~2×), flipping pedestal side with the coating — an
independent chronic confirmation of the cohort definition.

**Rings/stripes/treatment.** Sorted-yield rings: cohort null, same per-animal
signs as the free layer. Pooled stripe permutation: still null, bound tightens
to 21.7% yield / 5.5% noise. Rocky I2 fourth arrangement: anterior/posterior
1.152 (n=10) — fourth arrangement on the pedestal axis' side.

**Consensus + curation.** Direct 4-sorter agreement on the retained stems:
pairwise 0.25–0.47, ladder 722→156→66; dispersion proxy over 221 stems shows
disagreement not growing with age. UnitRefine on recording-backed analyzers
(35/37 features real): discriminative (54–68% neural) — snippet failure was
the input. API/version gotchas added to CLAUDE.md.

**Bug found and fixed.** (subject, array)-keyed serial lookups let Rocky I2
overwrite I1: 431 I1 sessions mislabelled with I2 serials and sorted with
I2's CMP geometry. Four sites fixed, tables repaired, rule in
serial_resolution.md.

**Also.** Fisk `.ns3` proven redundant with `.ns6` (ρ≈0.99, ×1.19; one
sampled file all-zero). `.nox` hope retired (procedures only; MUX tutorial
fixes sweep order, not pinout). Sweep-reply corrections applied to
nigel/rocky configs with source tags.

**Blocked, documented.** Rocky I2 per-electrode work (2025 NEV/ns5 live on
unmounted G:/E:); Nigel impedance + Fisk stripe verification (files await
copying from legacy drives).

## SpikeInterface / NEO functions introduced

- `spikeinterface.comparison.compare_multiple_sorters` — the layer-3
  agreement graph; returns pairwise comparisons and
  `get_agreement_sorting(minimum_agreement_count=k)`. Named by CLAUDE.md, no
  alternative considered.
- `spikeinterface.sorters.read_sorter_folder(..., register_recording=False)`
  — load a retained sorter output without touching the source recording.
- `spikeinterface.curation.load_model` / `auto_label_units` — the pinned SI's
  UnitRefine entry (CLAUDE.md's `unitrefine_label_units` is a later name);
  sklearn-1.4 pickles need `SimpleImputer._fill_dtype` restored under 1.8.
- `spikeinterface.preprocessing.decimate` after `bandpass_filter` — reused
  from the LFP arm as the anti-alias chain for the ns3 redundancy check.

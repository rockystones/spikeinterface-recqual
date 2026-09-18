# Within-array variance design: what the cohort says

Executes the owner's variance-analysis brief
([NHP_variance_analysis_brief](NHP_variance_analysis_brief.md) +
`Shi_within_array_statistical_framework.docx`). Scripts:
`scratch_variance_design.py` (modern cohort, Analyses 1–4) and
`scratch_variance_legacy.py` (TDT cohort, Analysis 5). Outputs:
`results/00_inventory.md` through `05_legacy_resampling.md`. Nav:
R-020..R-023 under W-020.

## Headline numbers (log10 µV, mean-max-P2P, outliers excluded)

Sham-contrast SDs (assumption-free): within-array 0.0585, between-array
0.128 (Fisk clean pair 0.094), between-subject 0.227. Efficiency vs a
within-array contrast: ×4.8 / ×15.0 realistic, ×8.6 matched-n.
Method-of-moments: vA .0240, vD .0094, vS .0684, vE .0401 →
**ρ = 0.235**, design effect 1 + m·ρ/(1−ρ) = ×15.8 (m=48) / ×30.5
(m=96). The parametric identity reproduces the resampled
between-subject ratio to 1%.

## What each extension added

- **Yield** (0/1 channel activity, 708-session universe): ρ 0.345,
  between-subject penalty ×29–67. Fisk's *identically treated* pair
  differs in yield more than the contaminated pairs' average
  (vD_clean .0135 > vD .0061): between-array yield variance is
  device-level, not treatment leakage. Yield is a boundary-constrained
  proportion — quote the resampling ratios, not the MoM line.
- **Crossing rate** (sorting-free, Rocky I1 only): ρ_device 0.222
  (coating-contaminated upper bound), between/within ×6.2.
- **Implant age** (6-month windows): within-array SD flat (0.05–0.08)
  for six years; between-subject SD grows 0.06 → 0.49 over months 0–24
  with a constant 3-subject pool. Animals are nearly exchangeable
  acutely and diverge as implants age — the pooled ρ *understates* the
  penalty for chronic endpoints. Figure
  `figures/cohort/variance_rho_over_time.png`.
- **MDE** (α=.05, power .80): within-array detects ~5× smaller effects
  at every replication level; k=8 array-months → 14% amplitude /
  2.2 pp yield vs 68% / 18 pp for 8 animals per arm.
- **Legacy replication** (TDT, Chase/Oops/Picasso, resampling only):
  within 0.071 / between-subject 0.239 vs modern 0.059 / 0.227 —
  the structure replicates across acquisition systems a decade apart.
  Legacy between-array (0.230) equals between-subject because both
  pairs are coated-vs-uncoated: whole-array assignment makes the
  device level indistinguishable from treatment.

## Design decisions that must be honored

- **No treatment residualization**: every treatment label on this
  cohort is array-aliased; removing condition means would erase vD.
  Contamination labels + the Fisk clean-pair anchor instead.
- log10 primary (raw-µV ρ = 0.11 is skew-inflated); active channels
  only; Rocky manual exclusions applied; Fisk months anchored at first
  session (registry lacks surgery_date).
- Honest n: 8 modern arrays, 4 pairs (1 clean, n=1 so no CI),
  3 subjects; legacy adds 5 arrays / 3 subjects.

## Manuscript sentence

"Animal- and device-level components accounted for ρ = 0.24 of total
log-amplitude variance, so an equally powered between-subject study
would need ~15–30× more animals at m = 48–96 electrodes per condition;
the conservative clean-pair bound is ~14×, and the penalty grows with
implant age."

## Stripe-conditioned set (unblocked by D-014, delivered same day)

`scratch_variance_stripes.py` → `results/06_stripe_conditioned.md`,
nav R-024. On the owner-ruled map (SN1498 = EDCNHS-L1 vs Ctrl,
SN1504 = TNP vs TNP-L1; even columns L1 from the side opposite the
wire bundle):

- **TOST**: Nigel's L1 stripes are equivalent to their neighbours
  within ±0.041 log10 (~10%) on both arrays; Fisk reads −0.041 on
  both arrays but its row-parity *no-treatment* control reads −0.079
  on SN1498 — parity splits move that much from spatial gradients
  alone, so Fisk is equivalent only at ±0.10 (~26%) and the −0.041 is
  not attributable to coating. Yield: all four arrays equivalent at
  ±5 pp. Matches the surface pipeline's gradient-corrected 0/168.
- **Condition-vs-tether**: stripe SD 0.039 vs between-array SD 0.118 —
  the device axis is 3.1× the treatment axis.
- **Residualization loop closed**: removing stripe-group means changes
  vS 0.0587 → 0.0582 and ρ 0.390 → 0.391 on the Nigel/Fisk subset;
  the no-residualization design decision cost nothing.

## Still parked

Spillover φ/λ: alternating single 400-µm columns put every control
electrode adjacent to a treated column, so stripe contrasts estimate
(treatment − spillover); φ itself needs the histology radial bins
(cross-repo, I.N.T.E.N.S.I.T.Y. pipeline).

## Related

[[NHP_variance_analysis_brief]], [[longitudinal_metrics]],
[[treatment_effect]], [[giant_events]].

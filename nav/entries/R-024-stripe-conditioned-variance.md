---
id: R-024
type: result
status: current
title: Stripe TOST - Nigel equivalent within 10%, Fisk within 26% with gradients implicated; treatment conditioning does not move rho
created: 2026-09-17
actor: agent
basis: recorded
parent: P-03
depends_on: [D-014, R-020]
informs: [Q-006, W-003]
source: [notebooks/scratch_variance_stripes.py, results/06_stripe_conditioned.md]
---
W-020 step 6 on the D-014-corrected stripe map. Paired within-
(array, month) contrasts on channel month-means, mmp2p log10 uV and
yield fraction; row-parity as the known-null control on the same
channels; TOST bounds +/-0.041 log10 (R-017's smallest whole-array
coating effect) and +/-0.10 (the legacy 1.26x effect).

AMPLITUDE. Nigel: both arrays' L1-vs-neighbour contrasts are tiny
(-0.002 / +0.004 log10) and EQUIVALENT even at the tight +/-0.041
bound (p_equiv 2e-5 / 2e-7). Fisk: both arrays read d = -0.041 log10
(L1 stripes ~9% lower), equivalent only at +/-0.10 - but the control
exposes it: SN1498's NO-TREATMENT row-parity contrast is -0.079,
nearly double its stripe contrast. A parity split of these arrays
moves this much from spatial gradients alone, so Fisk's -0.041 is not
attributable to coating. Consistent with the regenerated surface
pipeline's gradient-corrected permutation: 0/168 significant on the
treatment axis AND 0/168 on the control axis.

YIELD. All four arrays equivalent at +/-0.05 active-fraction
(p_equiv <= 1e-6); row controls fire at the same small scale as the
stripe contrasts (gradients again).

CONDITION-VS-TETHER: stripe-contrast SD 0.039 vs between-array
(pedestal) SD 0.118 - the device axis is 3.1x the treatment axis.
STRIPE RESIDUALIZATION: vS 0.0587 -> 0.0582, rho 0.390 -> 0.391 on
the Nigel/Fisk subset - conditioning on treatment leaves the variance
verdict untouched, closing the loop on R-020's no-residualization
design decision.

SPILLOVER: structural note only - alternating single 400-um columns
put every control electrode adjacent to a treated column, so the
stripe contrast estimates (treatment - spillover); phi needs the
histology radial bins (cross-repo, still parked).

W-020 is now complete: results/00-06 delivered.

---
id: D-014
type: decision
status: current
title: Fisk stripe map ruled by owner - SN1498 = EDCNHS-L1 vs Ctrl, SN1504 = TNP vs TNP-L1, even-col L1 phase confirmed
created: 2026-09-17
actor: human
decided_by: human
basis: recorded
parent: P-03
resolves: [Q-001]
informs: [W-020, W-003]
source: ["chat 2026-09-17"]
---
Owner stated the Fisk assignment directly: SN1498 (Anterior pedestal,
Lateral array) carries EDCNHS vs Ctrl; SN1504 (Posterior pedestal,
Medial array) carries TNP vs TNP-L1. Stripe arrangement is similar
across Fisk and Nigel: stripes along CMP columns, and the L1-carrying
stripes start from the column on the side OPPOSITE the wire bundle
(wire bundle right in CMP coords -> L1 starts at col 0, even columns
treated) - confirming the recorded orientation and phase.

This CORRECTS the design-inference carry-over from Nigel, which had
Fisk's families swapped (SN1498 = TNP-family). Consequence: the
implant table's Treatment column is RIGHT for Fisk and wrong for
Nigel; the two animals have opposite family-to-pedestal placement.

Scope of the correction: only which FAMILY each Fisk array carries.
The within-array stripe split (col parity) is unchanged, so stripe
contrasts computed per array keep their values; anything that names a
Fisk stripe family (surface_conditions outputs, figures, notes dated
before 2026-09-17) had the labels swapped and was regenerated /
corrected. Q-001's prediction (even-col L1 on both Fisk arrays) held;
its family half was falsified. The by-location workbook (W-001)
remains a future documentary cross-check but no longer gates the
stripe-conditioned analyses.

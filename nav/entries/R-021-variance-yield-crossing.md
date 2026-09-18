---
id: R-021
type: result
status: current
title: Variance structure of yield and crossing rate - yield is the worst case for between-subject designs
created: 2026-09-17
actor: agent
basis: recorded
parent: P-03
informs: [Q-006]
depends_on: [R-020]
source: [notebooks/scratch_variance_design.py, results/01_resampling.md, results/02_variance_components.csv]
---
W-020 step 2: the R-020 pipeline repeated on (a) per-channel YIELD -
the 0/1 activity indicator over all 96 sites and the 708-session
universe (zero-unit sessions kept as all-inactive), raw proportion
scale - and (b) the sorting-free clean CROSSING RATE (log10 Hz),
which exists per-channel only for Rocky I1 (332 stems): no vA or
between-subject level there, and its one array pair is
coating-contaminated (vD is an upper bound).

Yield: within-array half-split SD is tiny (0.022 realistic / 0.034
matched-24), so the design penalties explode: between-array x25
(realistic), between-subject x67 realistic / x29 matched-n. MoM:
vA .0138, vD .0061, vS .0041, vE .0337 -> rho 0.345 (clean 0.419),
design effect x26 (m=48) / x52 (m=96). Session-to-session FLICKER
(vE) dominates channel identity (vS) for the binary indicator.

THE CLEAN PAIR IS THE STRIKING ONE: Fisk's identically-treated
arrays differ in yield MORE than the contaminated average (SD 0.168
vs 0.112; vD_clean .0135 > vD .0061). Between-array yield variance
is genuinely device-level, not treatment leakage - an array's
propensity to hold sortable channels is a property of the implant.

Crossing rate (Rocky only): within SD 0.061, between-array x6.2
realistic; rho_device 0.222 (coating-contaminated upper bound) vs
mmp2p's rho_device 0.080 on the same animal pool.

Caveats: yield is a boundary-constrained proportion, so the
parametric identity that closed to 1% for log-amplitude does not
transfer cleanly - quote the resampling efficiencies, not the MoM
design-effect line, for yield. Amplitude (R-020) remains the primary
manuscript number; yield is the a-fortiori case ("for yield the
penalty is larger still").

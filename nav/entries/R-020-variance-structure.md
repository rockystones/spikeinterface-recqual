---
id: R-020
type: result
status: current
title: rho_hat = 0.24 - the within-array design effect measured on the cohort
created: 2026-09-17
actor: agent
basis: recorded
parent: P-03
informs: [Q-006]
source: [notebooks/scratch_variance_design.py, results/01_resampling.md, results/02_variance_components.csv]
---
W-020 Analyses 1+2 on per-channel max-P2P (mmp2p_shards, 62,296
channel-session rows after outlier exclusion; 8 arrays, 3 subjects,
months 0-73; log10 uV primary).

Sham-contrast resampling (assumption-free): within-array SD 0.0585,
between-array 0.128 (x4.8; Fisk-only CLEAN pair x2.6 - treatment
contamination in the Rocky/Nigel pairs roughly doubles the apparent
between-array penalty, the framework's warning quantified),
between-subject 0.227 -> x15.0 realistic / x8.6 matched-n.

Method-of-moments components (log scale): vA 0.0240, vD 0.0094 (clean
Fisk-only 0.0053), vS 0.0684, vE 0.0401 -> rho = 0.235 (clean 0.213);
design effect 1 + m*rho/(1-rho) = x15.8 (m=48) / x30.5 (m=96).

THE CROSS-CHECK IDENTITY HOLDS: the sham between-subject/within ratio
should equal (m/2)*rho/(1-rho) + 1/2 for pooled-m contrasts; with
m~94 and rho 0.235 that predicts x14.9 against the measured x15.04.
The parametric and resampling routes agree to 1%.

Honest n: 8 arrays, 4 same-implant pairs (1 clean), 3 subjects -
intervals are unit-level bootstraps and the clean-pair column has n=1
(no CI). Raw-uV sensitivity gives rho 0.11 (skew-inflated vS/vE; log
is primary). Manuscript sentence: "the animal- and device-level
components accounted for rho = 0.24 of total log-amplitude variance,
so an equally powered between-subject study would need ~15-30x more
animals (m = 48-96); the conservative clean-pair bound is ~14x."

Remaining per W-020: rho-over-implant-time windows, MDE in natural
units, legacy-cohort rho, stripe-conditioned set (parked on Q-001).

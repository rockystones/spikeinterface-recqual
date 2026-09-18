---
id: W-020
type: work
status: done
title: Execute the within-array variance-analysis brief on the cohort in hand
created: 2026-09-17
actor: agent
basis: recorded
parent: P-03
hill: uphill
depends_on: [Q-001]
x_finished: 2026-09-17
informs: [Q-006, R-017]
source: [docs/notes/NHP_variance_analysis_brief.md, docs/notes/Shi_within_array_statistical_framework.docx, results/00_inventory.md]
---
Owner dropped a manuscript-support brief + statistical framework
(variance decomposition y = mu + tau*T + a[animal] + d[array] +
s[shank] + e; deliver rho_hat = (vA+vD)/total with CI and the design
efficiency 1 + m*rho/(1-rho); sham-contrast resampling as the
assumption-free headline; spillover phi; MDE + TOST on the nulls).

Inventory (results/00_inventory.md): runnable NOW on richer data than
the brief assumes - Analyses 1/2 (resampling + variance components) on
mmp2p_shards' per-channel-per-session amplitudes (708 sessions, 3
animals, 8 arrays) plus the TDT per-channel sig sets (4 more animals);
Analysis 3 (rho vs implant month) via the existing month_post
machinery; MDE from sigma_w. BLOCKED on Q-001/W-001: anything
conditioning on the Nigel/Fisk stripe map (stripe residualization,
TOST on stripe nulls, condition-vs-tether, spillover exposure index).
Cross-repo lead: the framework's phi/lambda estimate wants the
histology radial-bin output - the I.N.T.E.N.S.I.T.Y. 10-um bins exist
in the Histology pipeline on this machine (memory index).

Agreed execution order (owner discussion 2026-09-17): (1) Analyses 1+2
on mean-max-P2P from mmp2p_shards - sham resampling with Rocky arrays
residualized for their KNOWN whole-array coating, plus the
animal/array/channel mixed model -> rho_hat + efficiency + CIs;
(2) repeat for yield and crossing rate; (3) Analysis 3 sliding
month_post windows; (4) MDE from sigma_w; (5) legacy-cohort rho via
the compiled per-channel sig sets (resampling only - no cross-session
channel identity there); (6) stripe-conditioned set parked on Q-001.

Progress 2026-09-17: steps 1-5 DONE - R-020 (rho 0.24, x15-30),
R-021 (yield rho 0.35, Fisk clean pair diverges MORE), R-022
(divergence with implant age, MDE table), R-023 (legacy replication,
between-subject SD 0.239 vs 0.227). results/00-05 delivered per the
brief's contract. Step 6 unblocked by D-014 and delivered same day (R-024):
results/00-06 complete. Only the histology-based spillover phi
remains, cross-repo and outside this work item's scope.

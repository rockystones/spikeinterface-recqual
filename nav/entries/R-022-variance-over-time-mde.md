---
id: R-022
type: result
status: current
title: Animals diverge with implant age - between-subject SD grows ~7x over two years while within-array stays flat; MDE table
created: 2026-09-17
actor: agent
basis: recorded
parent: P-03
informs: [Q-006]
depends_on: [R-020, R-021]
source: [notebooks/scratch_variance_design.py, results/03_rho_over_time.csv, results/04_mde.csv, figures/cohort/variance_rho_over_time.png]
---
W-020 steps 3+4. Analysis 3: sliding 6-month windows of month_post
(step 3), sham SDs per window, both log-amplitude and yield.

THE PATTERN: within-array SD is FLAT for six years (0.05-0.08 log10
across every window, both metrics). Between-subject SD grows nearly
monotonically from 0.06 (months 0-6) to 0.49 (months 21-27) - about
7x - over a window range where the subject pool is CONSTANT (all
three subjects, first 8 windows), so it is divergence, not pool
composition. MoM rho rises 0.04 -> 0.46 across the same span. Yield
shows the same shape (between-subject 0.05 -> 0.27). The post-month-24
drop is pool change (Nigel/Fisk age out; Rocky I1 alone thereafter).

Design implication: R-020's pooled rho = 0.24 UNDERSTATES the
between-subject penalty for chronic endpoints - animals are nearly
exchangeable in the acute window and diverge as implants age, exactly
when a longevity comparison reads out. Between-array (same animal)
grows far less (0.06-0.16, no clean trend).

Analysis 4 (results/04_mde.csv): MDE = 2.80*SD/sqrt(k) from the sham
null SDs (alpha=.05, power=.80), realistic channel counts. Within-
array: k=1 array-month detects a 46% amplitude change / 6.2 pp yield;
k=8 detects 14% / 2.2 pp. Between-subject with k animals per arm:
k=8 still only reaches 68% amplitude / 18 pp yield - the within-array
design detects effects ~5x smaller at every replication level.

# Statistics for the Rocky two-array longitudinal comparison

What test to use when comparing Anterior (L1-coated) vs Posterior
(uncoated) across the I1 lifetime. Written 2026-09-24; grounded in
R-017 (paired coating ratios), R-020 (variance components),
R-024 (stripe TOST), and the sensitivity sweeps
([[longitudinal_metrics]]).

## First decide which question you are asking

1. **Level**: is one array better on average?
2. **Trajectory**: does one array *decline differently*?
3. **Attribution**: is any difference due to the coating?

They need different statistics, and (3) is the one this design
cannot deliver — see the caveat at the end.

## The two structural facts that constrain everything

**Pair within the session.** The two arrays are recorded the same
day through the same acquisition chain, so a within-session
difference cancels day, amplifier, and animal-state confounds. This
is the CLAUDE.md aggregation rule: compute the per-session contrast
first, then summarize across sessions — never pool numerators and
denominators (the pooled artifact ratio was wrong by 661× on this
corpus).

**Sessions are not independent replicates.** The same 96+96
electrodes are measured every week, and neighboring sessions are
strongly serially correlated. 332 sessions is not n = 332; treating
it that way is how a paired Wilcoxon across sessions makes *any*
fixed difference "significant" (the surface-conditions row-parity
control fired on 29/44 metrics with no treatment at all). The honest
replication unit is the **month bin** (`month_post`, ~70 bins, still
optimistic) — exactly what `M.monthly` in
`matlab/rocky_two_array_metrics.m` now hands you.

## Recommended stack

**Level (primary).** Per month bin: difference of the two arrays'
values (log10 for amplitude — era scale shifts make raw µV
heteroscedastic; raw proportions for yield). Then across month bins:
- effect size: median paired difference (or back-transformed ratio)
  with a bootstrap CI resampling *month bins*;
- test: Wilcoxon signed-rank over month bins.
This is the R-017 recipe one level up (session → month), which is
what the serial correlation demands.

**Trajectory.** Two complementary reads:
- Nonparametric, matching the project's tables: per-array Spearman ρ
  of metric vs month_post, with the difference in ρ assessed by
  bootstrap over month bins. This is how "Posterior declines,
  Anterior doesn't" is already quoted (yield ρ −0.64 vs −0.09).
- Parametric, if a slope difference in units/month is wanted: a
  mixed / robust regression on month-bin values,
  `value ~ month_post * array`, the interaction term being the
  answer. Fit on bins, not sessions; if fitting sessions, model the
  autocorrelation (AR(1)) or the interaction SE is fantasy.
- For "when did it fail" questions, a survival read is cleaner than
  slopes: first month_post at which yield stays below x% — one
  number per array, no distributional assumptions.

**Report the sweep, not the point.** Any conclusion must hold across
the gate/method/cohort sweeps before it is quoted ([S2/S4/S7]):
unit-count *levels* vary 3.8× across sorting methods while
directions agree — so compare arrays within one method, and check
the direction in at least ofs + resort_gated. The outlier exclusion
set (owner-ruled, 23 stems) is a cohort choice: state it, and check
the conclusion survives toggling it.

## The attribution caveat (do not skip in a manuscript)

There is **one array per condition**: array identity, implant site,
and coating are perfectly confounded. The paired test answers "do
these two arrays differ", not "does the coating matter". R-020
measured device-level variance vD > 0 even between *identically
treated* arrays (Fisk's clean pair), and R-024 measured the
within-array treatment axis at 3.1× *smaller* than the between-array
device axis on the striped animals. So: report the paired contrast
with its CI as a description of *these two arrays*, and attribute to
coating only jointly with the cohort-level evidence (R-017 across
13 chains, the striped-array TOST), never from Rocky alone.

## Where the pieces live

- `M.monthly` (MATLAB) / `two_array_metrics.parquet` — month-bin
  values per metric × method × array, outlier-filtered.
- `scratch_coating_metrics.py::paired_ratio` — the within-session
  pairing implementation (R-017).
- `results/01_resampling.md` — the sham-contrast SDs that calibrate
  what a "significant" between-array difference must exceed.

## Related

[[longitudinal_metrics]], [[variance_design]], [[treatment_effect]],
[[giant_events]].

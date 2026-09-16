# Multi-sorter agreement: what exists, what was never computed, and the pilot

CLAUDE.md's metrics layer 3 wants the **agreement structure** of the sorter
pool reported longitudinally. Status after the ns5 resort:

- `ns5_sorters.parquet` holds 238 stems × 4 sorters (Fisk 128, Nigel 47,
  Rocky 63; 96% error-free), each scored **against the NEV reference only**
  (`frac_nev_recovered` / `frac_sorter_in_nev`).
- **Sorter-versus-sorter agreement was never computed**, and cannot be
  recovered for most stems: the spike trains were sorter scratch, deleted in
  the session-11 cleanup. Four Fisk Medial stems (2023-06 → 2024-08) survive
  with all four outputs.

## The direct pilot (`scratch_ns5_agreement.py`)

`spikeinterface.comparison.compare_multiple_sorters` — builds the pairwise
comparison graph over a list of sortings and returns per-pair Hungarian
matches plus `get_agreement_sorting(minimum_agreement_count=k)`. It is the
tool CLAUDE.md names for layer 3; no alternative was considered because the
policy names it. Inputs are the retained sorter folders read with
`read_sorter_folder(..., register_recording=False)` so the source `.ns6` is
never touched.

Result over the four stems (three sorters each in practice — the retained
KS4 folders are the *failed* runs, which is why the cleaner kept them):
pairwise matched fractions run **0.25–0.47**, and the consensus ladder is
steep — e.g. 722 unit-instances → **156** units found by ≥2 sorters → **66**
by ≥3. The pool disagrees on most units and agrees on a core, consistent
with the snippet-era method spread.

## The dispersion proxy, all 221 four-sorter stems

Without trains, disagreement is still visible in the summary table: CV of
unit count across the four sorters, and the spread of their NEV-recovery
fractions. Fisk sits at CV ≈ 0.21, Nigel and Rocky at ≈ 0.41–0.48.
Disagreement does **not** grow with implant age — Rocky's shrinks
(units_cv ρ = −0.40 and −0.60 with age, p ≤ 0.03), consistent with late
sessions holding few, well-separated units. The one rising trend is Nigel
Anterior's NEV-recovery spread (ρ = +0.70, p = 4e-4).

A proxy sees *how much* the sorters disagree, not *which* units — the direct
graph needs the trains.

## The longitudinal, run for real (2026-09-12)

`scratch_ns5_consensus.py` re-ran the pool on an **era-spanning 48-stem
subset** (6 per subject × implant × array, Rocky I2 included), all 48
completing 4/4 sorters; per stem it computes the agreement graph, saves each
sorting as `numpy_folder` under `consensus/sortings/`, writes a shard and
purges the scratch. Outputs: `consensus_pairs/ladder/per_stem.parquet`,
`figures/consensus/C1_agreement_longitudinal.png`.

**The level is uniform; the collapses are not.** Median pairwise agreement
sits at 0.27–0.34 on every array — but the minima tell the story:

| array | median | min (when) |
|---|---|---|
| Fisk Lateral / Medial | 0.34 / 0.34 | 0.31 / 0.28 — never collapses |
| Nigel Anterior | 0.34 | **0.13** (late 2024) |
| Nigel Posterior | 0.33 | **0.04** (2024-10: ladder 36 → 1 → 0 → 0) |
| Rocky I1 Anterior | 0.30 | 0.10 |
| Rocky I1 Posterior | 0.27 | **0.01** (2023-09: 210 → 1 → 1 → 0) |
| Rocky I2 (fresh) | 0.32 / 0.33 | 0.30 / 0.18 |

Agreement *declines with age precisely on the arrays that died* (Nigel
Anterior ρ = −0.83, Rocky I1 Posterior ρ = −0.89 over their six timepoints;
Fisk, still healthy, trends upward) — and a dead array's signature is
unmistakable: each sorter still emits tens of "units" and **no two agree on
any of them**. The consensus ladder is thereby a spike-validity metric that
no single sorter provides.

**Where the proxy misleads.** Rocky Anterior 2019-06 holds a normal raw
count (472 unit-instances) while the ladder collapses to 30 → 10 → 4: unit
*counts* can agree while unit *identities* do not. The dispersion proxy
(units_cv) called Rocky's disagreement "shrinking with age"; the direct
graph shows the opposite where it matters. Use the proxy only where no
trains exist, and never as a trend statistic.

## Related

[[sorter_operations]] for the snippet-era method spread this echoes,
[[ns5_plan]] for why the resort existed, [[unitrefine_analyzer]] for the
curation pilot on the same retained stems.

## Correction (2026-09-16, R-019): disagreement DOES grow on dying arrays

The dispersion-proxy paragraph above ("disagreement does not grow with
implant age") is superseded: it rested on the chance-saturated pooled
recovery fractions (nav I-005) and 6-stems-per-array coverage. With the
W-019 expansion (206 stems, 41 per Rocky I1 array, direct agreement
graphs), pairwise agreement declines with age exactly on the arrays
that died - Nigel Anterior rho -0.74 (p 1e-4), Nigel Posterior -0.63,
Rocky I1 Posterior -0.56 - and is flat on every healthy array (Rocky I1
Anterior +0.005, Fisk n.s.). The agreement LEVEL sits in a narrow
0.29-0.36 band everywhere; the trend, not the level, is the
longitudinal signal.

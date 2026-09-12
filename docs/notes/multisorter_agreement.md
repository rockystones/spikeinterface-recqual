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
graph needs the trains. Re-running the pool with retained outputs is the
outstanding piece, and it is compute, not method.

## Related

[[sorter_operations]] for the snippet-era method spread this echoes,
[[ns5_plan]] for why the resort existed, [[unitrefine_analyzer]] for the
curation pilot on the same retained stems.

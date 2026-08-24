# Session 12 — array position and recording quality (Forrest et al. ring test)

## Plan

Answer three provenance questions (the Nigel 2014/ejected-array claim, whether
any corpus data falls in the Oct 2022 – Jan 2023 window, and what Nigel/Fisk
surface-treatment analysis already exists), then read Forrest et al. 2025
(J. Neural Eng. 22 066008) and run its concentric-ring analysis against our own
verified CMP geometry.

## Outcome

**Provenance.** The Nigel claim came from `_LEGACY-SWEEP-REPLY.md`, the reply
from the drive-census session — folder-name evidence from drives this session
cannot see, not a first-hand check. Checked against the corpus: Nigel's earliest
session is **2023-01-24**, six days after the replacement surgery, so **nothing
in the corpus falls in the dead-array window**. The warning was prophylactic and
is moot for the data we hold. Nigel/Fisk stripe analysis was already complete in
[[surface_conditions]]; `treatment_effect.md` carried a stale line calling it
unverified and open, now corrected.

**Built** `notebooks/scratch_ring_geometry.py` → `docs/notes/ring_geometry.md`,
`data/derived/ring/`, `figures/ring/G1–G7`. Six implanted 10×10 arrays, three
animals, 630 sessions, 59,297 electrode-sessions, plus 19 never-implanted
factory arrays.

**Two traps found before any result.** (1) The fixed-electrode-split trap again:
a paired across-sessions Wilcoxon fires 21/24 on the border axis and 20/24 on a
parity control. (2) New and not obvious — **the CMP wires bank B with zero
border electrodes** and 32 of the 64 interior ones, so border-vs-interior is
partly bank-vs-bank, and impedance is swept bank by bank. Banks A and C straddle
the boundary, so every headline number is made inside a bank.

**Ephys: null across the cohort, large within an animal.** Within-bank sign
tests give 8/12, 7/12, 6/12, 6/12 negative across four metrics — nothing. But
the signs sort by animal: Nigel's two arrays are negative on all four metrics,
Rocky's positive, magnitudes to ±97%. Six arrays share one geometry, so a
geometric cause cannot give opposite signs in two animals.

**Impedance: real, and acquired.** Fisk (map-free) shows border below interior
on **81/81 array-dates**, −0.31 and −0.25 dex; the >1 MΩ failure rate runs 85%
at the centre against 16% at the border. The 19 never-implanted arrays give
nothing (p = 0.47; within-bank p = 0.89/0.98). Two of the 19 are Fisk's own, so
the in vivo series has a paired baseline: both start **at their bench value**
and open away from it, one to −0.49 over a year (ρ = −0.76, p = 7e-09).

**Diverged from plan.** The pre-implant control and the paired bench anchor were
not planned — they surfaced from `impedance_sources.md` while checking whether
the effect could be manufacturing. They turned out to be the strongest part.

**Side effect.** Both candidate impedance channel maps permute only within a
bank half, so the ring contrast is bank-clean for both and usable as an arbiter.
Authored −0.032 dex / 63.9% of dates in the predicted direction against naive
−0.006 / 54.2%. Leans authored, not decisive.

**Deferred.** Rocky implant 2 (too few sessions for a per-array null); the
Patrick/ impedance backlog; Nigel/Fisk yield by ring from the sorted layer.

## SpikeInterface / NEO functions introduced

None — this session used no new SI or NEO calls. Geometry came from the
project's existing `scratch_cohort_io.parse_cmp`, and the statistics from
`scipy.stats` (`binomtest`, `wilcoxon`, `spearmanr`, `mannwhitneyu`, `kruskal`).

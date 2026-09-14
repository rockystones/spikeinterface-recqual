# Consensus vs the human sort: what "replace" turns out to mean

`scratch_consensus_vs_ofs.py` compares every kept sorter output and every
consensus rung against the session's canonical Plexon sort (OFS units at
NEV stamps, lag-corrected per I-005), 45 stems across Rocky, Nigel and
Fisk. Table: `ns5/consensus/ofs_match.parquet`. Three levels, three
different answers to Q-009:

**1. Unit-for-unit: no.** The median session has 0–7% of its human units
matched 1:1 (Hungarian, agreement ≥ 0.5, 1 ms) by ANY sorter or
consensus rung; median best-agreement per human unit is 0.01–0.10. Not a
tuning artifact — the score is flat from 1 to 3 ms windows. The human
partition (≈2 units per channel on thresholded snippets) and a
continuous-data sorter's partition are structurally different objects,
and the sorters agree with each other no better (0.25–0.47 pairwise).

**2. Spike detection: strong at the top, thin below.** Per human unit,
the recall of its spikes by its single best-coinciding sorter unit:
the top decile of human units is recalled at ≥ 0.99 (KS4, consensus-2)
on the median stem — the units a physiologist would defend are found
essentially completely. The MEDIAN human unit reaches only 0.13–0.65
depending on sorter (KS4 highest, MS5 lowest): the long tail of small
human-accepted units has no clean automatic counterpart. Strict
consensus keeps far fewer units than the human (consensus-3 ≈ 60,
consensus-4 ≈ 20 vs human ≈ 100–200 per session).

**3. As a longitudinal metric: yes, and best-in-pool.** On the
expanded 87-stem coverage (63 Rocky, dense 2018–2022 same-day pairs
included), consensus-2/3 unit counts track the human unit counts at
Spearman ρ = +0.59 / +0.62 — ahead of every individual sorter (+0.43
KS4 to +0.58 SC2). Within-subject: Nigel +0.87/+0.89, Rocky
+0.53/+0.56, Fisk +0.35/+0.48 — ρ compresses where the yield range is
narrow (Fisk uniformly healthy; the dense Rocky pair block spans less
range than the era-spread stems, which is why the first 45-stem
estimate read higher at +0.74/+0.71). The ordering — consensus above
every single sorter — is what replicates across both selections.

**The verdict for Q-009:** consensus cannot replace the human sort as a
unit inventory, but it can replace it as a *yield tracker* — the
agreement-count layer moves with human-assessed yield more faithfully
than any single sorter, while measuring a deliberately more conservative
thing (CLAUDE.md layer 3: report the agreement structure, do not collapse
it).

## Measurement prerequisites (both nontrivial, nav I-005)

- NEV stamps trail the continuous stream by a fixed per-session lag:
  a few ms of DSP delay on single-segment sessions, **seconds** on
  multi-segment ones (the NEV clock spans dropped segments; Rocky
  2018-11-09: −3.54 s). The script searches the full range per stem
  (FFT coarse candidates, 0.1 ms refinement, no gate).
- The resort's stored `frac_nev_recovered` is pooled 1 ms matching at
  ≈1 kHz rates and sits at its own chance column (median excess −0.004):
  it must not be read as recovery.

## Caveats

- OFS here is the curated Plexon output, units 0/255 dropped; it is a
  reference, not ground truth (CLAUDE.md).
- `spike_rec_med` (pooled recovery) is chance-saturated for dense
  candidates and kept only with its chance column; use `best_recall_*`.
- Coverage is the 48-stem consensus set (45 with usable Plexon layers);
  the W-019 expansion adds stems and same-day Rocky pairs — rerun the
  script to sweep them in (it resumes from shards).

## Addendum (R-018): the snippet basis is not the gap

Direct lag-aligned ISO-SPLIT-vs-MS5 on the provenance sessions
(`scratch_isosplit_vs_ms5.py`): the GATED snippet resort matches MS5
unit-for-unit at 36-62% with best-agreement medians 0.35-0.65 and
top-decile spike recall ~1.0 - at or above the sorter-vs-sorter level -
while ungated iso falls to 20-34% (the gate is what makes it
sorter-like). Since a snippet-side automatic method lands inside the
modern family, the <=7% human-vs-automatic agreement is a property of
the human partition, not of the snippet data.

# The legacy TDT sorts: what 154 of them contain

Every offline sort that shipped with the TDT tanks, read and summarised.
`notebooks/scratch_tdt_sorted.py` → `data/derived/tdt/offline_sort*.parquet`.

These are reference material, not ground truth. They were produced years before
this project by operators using TDT OpenSorter and a Bayesian sorter, and the
point of reading them is to know what a legacy result looks like before
comparing a modern sorter against it ([[tdt_resort]]).

## Coverage — and nothing is corrupt

| subject | files | sort name | covers | blocks | events labelled |
|---|---|---|---|---|---|
| **Luigi** | 144 | `baySort` | `eNe2` | 144 | **673,752,944** |
| **Oops** | 6 | five date-named, `_A` / `_B` | `eNe1` ×1, `eNe2` ×5 | 5 | 1,785,285 |
| **Picasso** | 4 | `kmsort` ×3, `20160513A` | `eNe1` ×1, `eNe2` ×3 | 4 | 1,594,791 |

**All 154 applied cleanly.** Every payload matched its tank's tsq body length
exactly, so none had to be rejected. That was worth checking rather than
assuming — a `.SortResult` is a headerless int8 blob whose only validation is
its length, and the estate census had already flagged one truncated tank
elsewhere in the corpus. The status table keeps a row per file including any
that fail, so a later drop is visible rather than silent.

**A `.SortResult` covers one store and zeroes the others.** `eNe2.SortResult`
destroys eNe1's online codes. Any comparison must be restricted to the named
store; reading the zeroed array would report "the offline sorter rejected
everything".

## Two kinds of sorter, and only one of them tells you anything

Units the sort declared per channel:

| subject | 0 | 1 | 2 | 3 | 4 | 5–9 | mean |
|---|---|---|---|---|---|---|---|
| **Luigi** `baySort` | 12,096 | 821 | 397 | 304 | 135 | 66 | **0.25** |
| **Oops** | 0 | 4 | 560 | — | — | — | **1.99** |
| **Picasso** | 5 | 7 | 353 | — | — | — | **1.95** |

**Oops's and Picasso's sorts were configured for a fixed two units per
channel** — 913 of 929 channels have exactly two. Their unit counts describe
the sort setup, not the tissue, and must not be used as a yield metric.

**`baySort` discovers a variable count** (0–9, mean 0.25) and rejects most
channels outright. It is the only legacy result in this corpus whose unit
counts mean anything, and it is by far the most conservative.

## Inclusion: the online flag against the offline sort

Both are decisions about whether an event belongs to a neuron. Median over
channels:

| subject | kept online | kept offline | outlier bin (31) | agree | ARI |
|---|---|---|---|---|---|
| Luigi | 0.533 | **0.000** | 0.0000 | 0.443 | **0.493** |
| Oops | 0.992 | 1.000 | 0.0000 | 0.992 | n/a |
| Picasso | **0.000** | 0.999 | 0.0005 | 0.002 | n/a |

Three completely different regimes, and none of them is a disagreement about
neurons:

- **Oops**: online keeps 99%, offline keeps 100%. Neither filters. Agreement
  is 0.99 because both say yes to everything.
- **Picasso**: online keeps ~0%, offline keeps ~100%. The rig's discriminator
  was configured to reject nearly every crossing; `kmsort` then accepted them
  all. Agreement 0.002 measures the rig setting, not the sorter.
- **Luigi**: online keeps 53%, `baySort` keeps none on the median channel.
  This is the only pair where both sides are actually deciding, and on the
  channels where both keep something they agree at **ARI 0.49**.

**ARI is `n/a`, not 0, for Oops and Picasso.** Their online side has a single
kept class, so there is no partition to compare; a zero there would mean "not
applicable", and reporting it as a number would read as total disagreement.

**The outlier bin is barely used.** TDT's code 31 — the analogue of Plexon's
255 — takes 0.00–0.05% of events. Whatever these sorts were doing, they were
not throwing events away.

## Per-unit quality, and a gate that does not transfer

Waveform pass, Oops and Picasso (Luigi's 144 blocks are deferred: each costs
~10 minutes of header parse against a 1.18 GB tsq):

| subject | units | blocks | median amp | median SNR | SNR quartiles | passes SNR ≥ 4 |
|---|---|---|---|---|---|---|
| Oops | 1,124 | 5 | 30.3 µV | 3.44 | 3.12 / 3.44 / 3.68 | **12.9%** |
| Picasso | 713 | 4 | 34.5 µV | 3.29 | 2.96 / 3.29 / 3.82 | **20.6%** |

**The project's `SNR >= 4` gate was tuned on Blackrock and does not carry
across.** It passes 27% of Blackrock units and 13–21% here, because TDT's
online threshold sits lower: peak SNR runs ~3.2–3.4 in this corpus against 5–7
on Blackrock. The distributions are tight — Oops's interquartile range is
3.12–3.68 — so the gate lands in the middle of the mass rather than in its
tail, and small changes to it move the survivor count a lot.

Gated units per active electrode comes to **0.23 (Oops) and 0.29 (Picasso)**,
against 0.4–1.5 for Blackrock Rocky implant 1. That gap is the gate, not the
tissue and not the sorter.

**Do not re-tune the gate to fix this without deciding what it is for.** A gate
chosen to equalise pass rates across acquisition systems is no longer a
physics threshold. The honest options are to report SNR distributions instead
of pass counts, or to fix the gate per system and never compare the counts.

## What cannot be done here

**No measurement floor.** A floor needs the same store sorted twice by
different hands, and no block in this corpus has that. `Oops_2015_09_04-1`
carries two sorts, but `Oops_2015_09_04_A` covers `eNe1` and `_B` covers
`eNe2` — one sort per array, not two sorts of one array. The Blackrock
operator/algorithm floor in [[measurement_floor]] has no counterpart here.

## Related

[[tdt_corpus]] for the corpus and its file formats, [[measurement_floor]] for
the floor this corpus cannot measure, [[tdt_resort]] for the comparison
against the modern sorter pool.

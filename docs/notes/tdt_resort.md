# The legacy TDT sorts against the modern sorter pool

`notebooks/scratch_tdt_resort.py` → `data/derived/tdt/resort/`,
`data/derived/tdt/tdt_resort.parquet`.

Seven (block, array) pairs — six Oops, one Picasso — each sorted by
MountainSort5, Tridesclous2 and SpykingCircus2 on a 180 s slice of broadband,
against the legacy sort of the same block. Luigi's 144 candidates are pending.

## The comparison is a yield comparison, not an agreement one

The legacy sorters label an event list the TDT rig had already detected online.
The modern pool re-detects from the continuous trace with its own threshold.
There is no fixed event set, so spike-by-spike agreement is not defined and is
not computed — the same regime as `.ns5` re-sorting in S11.

## The modern pool finds fewer units and much cleaner ones

| block | array | legacy units | legacy SNR | legacy pass | modern units | modern SNR | modern pass |
|---|---|---|---|---|---|---|---|
| Oops_2015_07_010-1 | 2 | 189 | 3.46 | 12.7% | 69 | 4.88 | 73.7% |
| Oops_2015_07_28-1 | 2 | 190 | 3.44 | 11.1% | 70 | 5.02 | 84.5% |
| Oops_2015_09_04-1 | 1 | 179 | 3.48 | 22.9% | 98 | 4.88 | 77.5% |
| Oops_2015_09_04-1 | 2 | 189 | 3.37 | 11.6% | 72 | 4.70 | 68.8% |
| Oops_2015_10_02-1 | 2 | 187 | 3.43 | 9.6% | 89 | 4.96 | 75.0% |
| Oops_2015_11_18-1 | 2 | 190 | 3.42 | 10.0% | 74 | 4.82 | 75.8% |
| Picasso_2016_01_14-1 | 2 | 186 | 3.39 | 14.5% | 98 | 4.54 | 69.5% |

Modern columns are the median across the three sorters.

**Modern / legacy unit count: median 0.39×. Median SNR rises 3.42 → 4.88, and
the fraction clearing the project's SNR ≥ 4 gate rises from ~12% to ~75%.**

The direction is consistent on all seven, with no overlap between the legacy
and modern SNR ranges.

**The legacy unit count is not a yield to compare against.** Those 179–190
units are the fixed-two-per-channel configuration described in
[[tdt_legacy_sorts]], not a discovery — 913 of 929 channels carry exactly two.
The honest statement is that the legacy sort declared ~2 units on nearly every
electrode at SNR 3.4, and the modern pool declares ~70–98 units at SNR 4.5–5.0.

## The three modern sorters, and where they differ

Oops, five blocks, median across blocks:

| sorter | units | spikes | median SNR | passes gate | median rate |
|---|---|---|---|---|---|
| **mountainsort5** | 76.5 | 101,805 | **6.76** | **98%** | 4.2 Hz |
| tridesclous2 | 63.0 | 240,659 | 4.88 | 75% | 15.7 Hz |
| spykingcircus2 | 97.0 | 453,201 | 4.08 | 52% | 18.3 Hz |

**Unit-count spread between sorters: median 1.46×, p90 1.67×, max 1.68×.** The
Blackrock S11 reference is median 1.44×, p90 2.09× — a close replication on a
different acquisition system, which is worth more than either number alone.

**Firing rate separates the pool sharply.** MountainSort5 lands at ~4 Hz, a
plausible cortical rate; the other two land at 15–18 Hz on the same data with
2.4–4.5× the spike count at a similar unit count. That points at merged
multi-unit activity rather than more neurons found, and it is the same pattern
S11 reported: the sorters agree far better on *how many neurons* there are than
on *how much of the record is neural*.

MountainSort5's 98% gate pass rate is not independent evidence of quality — a
sorter that assigns a third as many spikes to similar unit counts will produce
higher-SNR templates almost by construction. What it does establish is that
**MountainSort5 and the legacy sorts are not measuring the same thing at all**,
where the legacy-vs-modern gap could otherwise be read as a tuning difference.

## One unit per electrode? Checked, and refuted

SpykingCircus2 returned **exactly 96 units on a 96-channel array**, twice. At a
400 µm pitch a spike appears on one channel, so the obvious reading is that the
sorter had degenerated into one template per electrode.

It has not. Extremum channels, `Oops_2015_07_010-1` array 2:

| sorter | units | distinct extremum channels | max units on one channel |
|---|---|---|---|
| spykingcircus2 | 96 | **64** | 6 |
| mountainsort5 | 69 | 52 | 4 |
| tridesclous2 | 57 | 52 | 3 |

The 96 was a coincidence. All three sorters split several units onto one
electrode, which is the thing that actually matters at this pitch.

The more interesting number is the other one: all three use only **52–64 of 96
electrodes**, where the legacy sorts declared units on 94–95. A third to nearly
half the array yields nothing sortable, and the legacy configuration hid that
by construction.

`n_extremum_channels` and `max_units_per_channel` are recorded per run from
now on. Shards written before that lack the columns; the sorter folders are
kept, so they are recomputable without re-sorting.

## Two blocks that cannot be re-sorted, and why

- **`2015_12_10_BC_3D_task-1` and `2015_12_16_BC_1D-3`** declare `LFP1`/`LFP2`
  (float32) and `pNe1`/`pNe2` (int16) and **no `Raw` store at all**. Their 192
  `.sev` files are LFP. A third store-naming vintage; the inventory now records
  `broadband_store` and `lfp_stores` per row and the worklist requires the
  former.
- **`Picasso_2016_05_13_A-1`** declares `Raw1` and `Raw2` and carries **zero**
  `.sev` files, so the trace reads as a constant. All three sorters originally
  died inside whitening with `LinAlgError: SVD did not converge`. A
  `signal_check` now runs first and turns three 20-minute failures into one row
  saying "trace is constant (no broadband data)".

## Caveats that bound the reading

- **Six Oops blocks and one Picasso block**, all from 2015–16. Luigi is pending.
- **Geometry is a placeholder.** The store-to-anatomy mapping is unknown, so a
  canonical 10×10 grid at the Utah pitch is attached rather than the array's
  own mapfile. Safe for sorting — at 400 µm every sorter's neighbourhood covers
  one electrode, so the channel-to-position permutation cannot change the
  result — and unsafe for anything spatial, which is why none is produced.
- **The window is 180 s.** Oops and Picasso blocks run ~185–190 s, so the slice
  is essentially the whole block and unit counts are comparable with the legacy
  sort's. **Luigi's blocks run 13–18 minutes**, so when he is added the legacy
  side must be restricted to the same window or the comparison will understate
  the modern yield.
- **Luigi's broadband is int16 ADC counts** with no recorded scale
  ([[tdt_corpus]]). Everything here is in SNR and unit counts, which are
  dimensionless, so he can be added without a calibration.
- **Nothing here validates the sorters' parameters.** [[robustness]] Q1 remains
  open: a higher-SNR unit set is not automatically a more correct one.

## Related

[[tdt_legacy_sorts]] for what the legacy sorts contain, [[tdt_corpus]] for the
formats, [[robustness]] Q1 for the parameter question this does not settle.

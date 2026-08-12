# Validating a CMP before trusting its geometry

CLAUDE.md warns that channel-order mismatch is silent and ruinous. Position mismatch is the subtler half of the same problem: `bank` and `elec` can be perfectly correct — so the sort is fine and every unit is assigned to the right channel — while the electrode sits in the wrong square on the grid. Nothing downstream errors. Spatial maps, bank breakdowns and any adjacency test are simply wrong.

`notebooks/scratch_cohort_io.py --validate` checks each mapfile against the known shape of a Utah-96.

## What is checked

| check | why |
|---|---|
| exactly 96 electrodes | a truncated or duplicated file |
| unique `(col, row)` | two electrodes cannot share a square |
| no electrode on an unpopulated corner | a Utah-96 is 10×10 minus `(0,0)`, `(0,9)`, `(9,0)`, `(9,9)` |
| no vacant non-corner square | the complement of the above, and the half that catches a typo |
| positions inside the grid | a dropped or added digit |
| unique `electrode_id`, unique `label` | the two independent numbering systems must each be a bijection |
| `bank` in A–D, `elec` in 1–32 | `electrode_id = (bank − 'A') × 32 + elec` is meaningless otherwise |

## A real defect: SN 1025-004377

Rocky's implant-2 anterior array shipped with two corrupted rows:

```
elec18   col 0, row 9    should be col 8, row 9
elec8    col 9, row 0    should be col 9, row 8
```

Both are single-digit slips — an `8` written as `0` — and both land the electrode on a corner that a Utah-96 does not populate, leaving the real square empty. The other 94 rows are correct, and `bank`/`elec` are correct for all 96, so a sort using this file would have been perfectly valid while its spatial map was wrong in two places.

## The repair rule

Match each occupied corner to the vacancy that shares its intact coordinate. `(0,9)` keeps row 9, and the only vacancy with row 9 is `(8,9)` — so the column was the corrupted digit. `(9,0)` keeps column 9, and the only vacancy with column 9 is `(9,8)`. Both are unambiguous; where more than one vacancy matches, the repair is refused and logged rather than guessed.

The rule is derived from the file alone and does not consult the sibling array. That is what makes the outcome a confirmation rather than an assumption: after repair, 004377 matches all three other Rocky arrays at **96 of 96 labels**, having been derived without reference to any of them.

Repairs are never silent. `load_probe_map` returns the notes alongside the frame, and they belong in the session record.

## The defect is upstream of the mapfile

Blackrock ships three descriptions of each array — the `.cmp`, a factory `.xlsm` workbook, and an automated impedance `.txt`. `scratch_cmp_crossvalidate.py` compares all three for all four Rocky arrays.

The workbook was expected to arbitrate: if its embedded Cerebus mapping disagreed with the `.cmp`, the defect would be in the mapfile export and the workbook would be authoritative. **It agrees.** For 004377 the `.cmp` and the `.xlsm` differ on 0 of 96 rows, and the workbook independently fails the same validation with the same two corner errors. Its own `col,-row` text column — written by a different part of the template — is consistent with the wrong numbers.

So the bad values are in Blackrock's map generator, not introduced when the `.cmp` was written. Both artefacts inherit them, and anyone else using this array's files inherits them too. The repair stands; its justification is that the generator emitted a physically impossible layout, not that a file was damaged in transit.

| array | cmp defects | cmp vs xlsm (as shipped) | txt vs xlsm impedance |
|---|---|---|---|
| 1025-001501 I1 Anterior | 0 | 0 of 96 differ | 96 labels, 0 disagree |
| 1025-001497 I1 Posterior | 0 | 0 of 96 differ | 96 labels, 0 disagree |
| **1025-004377 I2 Anterior** | **2** | **0 of 96 differ — same defect** | 96 labels, 0 disagree |
| 1025-004419 I2 Posterior | 0 | 0 of 96 differ | 96 labels, 0 disagree |

Impedance agrees exactly everywhere, so the workbooks and dumps are otherwise sound.

## Gotcha: one factory workbook is truncated

`13966-8 SN 1025-001497.xlsm` has no end-of-central-directory record, so `zipfile` — and therefore `openpyxl`, `pandas` and Excel — refuse it outright. All **19 copies across 8 volumes are byte-identical at 75,888 bytes**, so it was truncated at source and there is no intact copy to fall back on.

The central directory holds no content, only an index of members that are each preceded by a complete local header. Walking those headers recovers the file losslessly: 29 members, every one passing its stored CRC. `recover_truncated_xlsx()` does this in memory and the readers fall back to it automatically, so the damage costs nothing but is still reported.

## All four Rocky arrays share one geometry

`1025-001497`, `1025-001501`, `1025-004377` (repaired) and `1025-004419` are identical in `(col, row)` and `electrode_id` for every label. Blackrock auto-generates these from a template, so this is expected — which is precisely why a difference is worth surfacing rather than absorbing. Do not infer that arrays from other lots match; run the diff.

## Related

[[utah_channel_mapping]] for the four coexisting numbering systems, [[cohort_plan]] for where each subject's CMP lives.

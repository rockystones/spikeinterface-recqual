# Validating a CMP, and why "not like the others" is not a defect

CLAUDE.md warns that channel-order mismatch is silent and ruinous. Position mismatch is the subtler half: `bank` and `elec` can be perfectly correct — so the sort is fine and every unit lands on the right channel — while the electrode sits in the wrong square on the grid. Nothing errors. Spatial maps, bank breakdowns and adjacency tests are simply wrong.

The temptation is to check a mapfile against a canonical Utah-96 layout. **That is wrong, and this note exists because it was tried.**

## Which cells are empty is a property of the array, not the array type

A Utah array has **100 electrodes, of which 96 are connected** to the pedestal connector [5]; the other four are physically present but wired to nothing, so they never appear in the map file. Most arrays leave the four symmetric corners unconnected — but not all, and Blackrock says so: *"arrays are often highly customized and the exact channel mappings vary from device to device"* [4]. In this lab's experience the substitution compensates a shank broken during manufacture by wiring a surviving one elsewhere to still reach 96.

`SN 1025-004377` (Rocky implant 2, anterior) is such an array:

| array | unconnected positions | |
|---|---|---|
| 1025-001501 (I1 Ant) | `(0,0) (0,9) (9,0) (9,9)` | typical |
| 1025-001497 (I1 Post) | `(0,0) (0,9) (9,0) (9,9)` | typical |
| **1025-004377 (I2 Ant)** | **`(0,0) (8,9) (9,8) (9,9)`** | **rewired** |
| 1025-004419 (I2 Post) | `(0,0) (0,9) (9,0) (9,9)` | typical |

`elec18` sits at top-left `(0,9)` and `elec8` at bottom-right `(9,0)`, with `(8,9)` and `(9,8)` given up instead. That is the build, not a typo.

## The mistake, and why it survived a check

Session S07's validator assumed the symmetric corners and reported 004377 as defective. It then "repaired" it by moving `elec18` to `(8,9)` and `elec8` to `(9,8)` — **onto positions carrying no connected electrode**, while vacating the two that do.

The repair looked confirmed: after it, 004377 matched all three sibling arrays at 96 of 96 labels. That agreement was the whole problem. The test was *is this array like the others*, and difference was read as error. A rewired array is different by construction, so the check could only ever have produced the answer it did.

Nothing downstream consumed it — `repair_cmp` was reachable only from two reporting paths, and every analysis to date uses implant-1 maps, which are typical and unrepaired. The repair function has been deleted rather than fixed.

## The right authority: the pad-side location grid

The factory `.xlsm` prints a 10×10 block titled *Electrode numbering viewing from pad side* (cells `AR15:BA24`), giving each populated cell's `elecN` label directly. It is Blackrock's own record of the physical build; the `.cmp` is a derived export of the same information. Same legend as the mapping tab: `col` 0-based left to right, `row` 0-based **bottom to top**, so the printed top row is `row 9`.

`read_pad_map()` parses it and `verify_against_padmap()` compares. All four Rocky arrays agree at **96/96 positions**, 004377 included — its `.cmp` was right all along.

## What is still checked

Only invariants that hold for any Utah-96 however it is wired:

| check | why |
|---|---|
| exactly 96 electrodes | truncated or duplicated file |
| unique `(col, row)` | two electrodes cannot share a cell |
| positions inside the 10×10 | dropped or added digit |
| unique `electrode_id`, unique `label` | both numbering systems must be bijections |
| `bank` in A–D, `elec` in 1–32 | `channel_id = (bank − 'A') × 32 + pin` is otherwise meaningless |

The unconnected-position set is *reported*, and flagged `REWIRED` when it differs from typical — as information, never as an error.

## Cross-format agreement

`scratch_cmp_crossvalidate.py` checks all three factory descriptions of each array. Impedance agrees exactly everywhere: 96 labels joined, 0 disagreements between the automated `.txt` dump and the workbook, for all four arrays. The workbook's embedded Cerebus mapping matches the `.cmp` row for row, including for 004377 — as it should, both describing the same rewired build.

## Gotcha: one factory workbook is truncated

`13966-8 SN 1025-001497.xlsm` has no end-of-central-directory record, so `zipfile` — and therefore `openpyxl`, `pandas` and Excel — refuse it outright. All **19 copies across 8 volumes are byte-identical at 75,888 bytes**, so it was truncated at source and there is no intact copy to fall back on.

The central directory holds no content, only an index of members that each carry a complete local header. Walking those headers recovers the file losslessly: 29 members, every one passing its stored CRC. `recover_truncated_xlsx()` does this in memory and `open_workbook()` falls back to it automatically, reporting when it does.

## The general lesson

Validate an artefact against its own provenance, not against its peers. Peer agreement measures conformity; only the build record measures correctness. Where no provenance exists, report the difference and stop — do not repair toward the majority.

## Sources

Numbered as in [`channel_mapping.md`](channel_mapping.md), which carries the full list.

4. *Blackrock Research Arrays IFU*, Rev 5.00, **LB-0514**, 2020 — "mappings vary from device to device", p11.
5. *NeuroPort Electrode IFU*, Rev 3.00, **LB-0612**, 2022 — "Number of Electrodes 100 (96 connected to percutaneous connector)", p8.

## Related

[[utah_channel_mapping]] for the CMP parser and the full set of channel identities, [[cohort_plan]] for where each subject's CMP and workbook live.

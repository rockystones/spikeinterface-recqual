# What 57 manufacturer mapfiles actually contain

Cross-validation of every array in the manufacturer CD collection — `.cmp`, factory workbook and impedance `.txt` — run by `notebooks/scratch_array_catalog.py`. The point is to replace assumptions about "a Utah array" with the distribution actually shipped.

## Three geometries, one rule

| channels | grid | banks | pins | channel ids | arrays |
|---|---|---|---|---|---|
| 96 | 10×10 | A–C | 1–32 | 1–96 | 21 |
| 16 | 4×4 | A | 1–16 | 1–16 | 36 |
| 256 | — | **A–H** | 1–32 | 1–256 | 1 (map only) |

**`channel_id = (bank − 'A') × 32 + pin` holds for 57 of 57 arrays**, and for all 256 rows of the 256-channel map. The rule is independent of geometry; only the number of banks changes. That matches the KB's definition of `bank` as *"lettered A-H"* [3].

The 256-channel workbook makes it explicit with its own `Connector → NSP ch` column: `A01 → ch-01`, `A32 → ch-32`, `B01 → ch-33`, `C01 → ch-65`, `D01 → ch-97`. Checked against `(bank−'A')×32 + pin`: **256/256**. Against a 64-per-bank alternative: 32/256, i.e. only bank A coincidentally.

Practical consequence for 256: one Front-End Amplifier has four 34-pin banks, so 128 channels [1]. A 256-channel array spans **two** front ends (or a 256-channel digital headstage). The letters A–H in the mapfile are logical bank indices; E–H land on the second amplifier's physical A–D.

For 16-channel rodent arrays: all 16 shanks are connected — **no unconnected positions on any of the 36** — and they occupy bank A pins 1–16 only. Pins 17–32 of bank A are unused, so channels 17–32 do not exist for that array. Code that assumes a contiguous 1..N with N = the bank size will be wrong.

**`electrode_id` never equals `channel_id` in the 256 map — 0 of 256.**

## Which shanks go unconnected: "the four corners" is a minority

Among the 21 96-channel arrays, the symmetric-corner layout `(0,0) (0,9) (9,0) (9,9)` appears in only **6**. The other 15 each have a *different* set, including:

```
(0,9) (1,5) (9,0) (9,1)      (0,0) (2,0) (3,0) (9,8)
(0,7) (2,0) (8,0) (9,9)      (0,1) (0,2) (9,6) (9,9)
(0,0) (0,4) (8,0) (9,9)      (0,9) (1,8) (1,9) (9,9)
```

So the corner pattern is **29 %**, not the norm. Earlier notes here called it "usual"; on this evidence it is merely the most common single pattern. Blackrock's own wording is the safe one: *"arrays are often highly customized and the exact channel mappings vary from device to device"* [4].

This retires any remaining temptation to validate a mapfile against a canonical layout — see [`cmp_validation.md`](cmp_validation.md).

## `col` and `row` are display coordinates

Three 16-channel arrays (`5491-000147/148/149`) place their 4×4 block on **rows 1–4 instead of 0–3**, with byte-identical electrode-to-pin mapping to their siblings. Only the display origin differs.

That is consistent with the KB definition — `row` is *"the row in Central Spike Panel"* [3] — and it means **absolute `(col, row)` is not comparable across arrays**. Compare relative geometry, or normalise to each array's own bounding box, which is what `vacant_cells()` now does.

## Cross-format agreement

- **57/57** `.cmp` files are internally self-consistent.
- **15/15** modern `.xlsm` workbooks agree with their `.cmp` exactly on the pad-side location grid. The other 42 arrays ship a legacy `.xls`, which `openpyxl` cannot read; those are unverified against a second source.
- The pad grid is **found, not assumed**: `find_pad_block()` scans for the window whose contents are exactly that array's electrode numbers. The `AR15:BA24` address used earlier is a property of one template, and a global search for "cells whose value is 1–96" fails because the impedance table on the same sheet is full of such values.

## The impedance file is indexed by channel, proved from the workbook

The same two pad-side grids that verify geometry also settle what the automated
impedance file is indexed by, because one prints electrode numbers and the other
prints impedances for the same positions. Row *N* of the table matches the
impedance of the electrode whose **channel id** is *N* in **1,248 of 1,248**
positions across 13 arrays; the electrode-number reading scores 2.48 %, which is
the chance rate from repeated values. Detail in [`impedance_sources`](impedance_sources.md).

## How Blackrock's own documentation evolved

Six revisions of LB-0514 are in the collection. Mentions of the words that matter:

| revision | year | "bank" | "map file" | "channel" | "Central" |
|---|---|---|---|---|---|
| 1.00 | 2013 | 0 | 0 | 2 | 0 |
| 2.00 | 2014 | 0 | 0 | 2 | 0 |
| 2.50 | 2014 | 0 | 0 | 2 | 0 |
| 4.00 | 2019 | 1 | 4 | 5 | 2 |
| 5.00 | 2020 | **9** | 5 | **33** | 4 |

The 2013–2014 revisions do not explain the mapping at all — they document impedance tables and say to contact support for custom mappings. The bank/pin/channel explanation, the `electrode 33 ↔ pin B-01` example and the *"pins 1-32 on Bank A will be channels 1-32 in Central"* statement all arrive in **5.00**. It took the manufacturer five revisions and seven years to write down the thing this project needed most.

### A protocol that exists only in revision 4.00

Rev 4.00 carries a troubleshooting entry that 5.00 dropped:

> *"I am not confident about the map file sent along with the array, is there a way to confirm it? You can run an impedance test to confirm the mapping … gradually lower the array vertically until it is 'partially' submerged in the saline e.g. one corner plus few surrounding electrodes … Those electrodes staying outside the saline solution must be noisier and their impedance must be much higher … Check of those electrodes inside or outside the saline to see if they match electrode locations mentioned in your excel files and if they belong to the right bank."*

That is an empirical, physical test of a mapfile, and it is the closest thing to a ground-truth procedure for the impedance-ordering question still open in [`impedance_parsing.md`](impedance_parsing.md). Worth keeping even though Blackrock removed it.

## Repo audit: geometry is now resolved, not assumed — **cleared 2026-08-15**

`validate_cmp()` and `vacant_cells()` were generalised first. The analysis scripts followed:

| location | was | now |
|---|---|---|
| `scratch_rocky_resort.py`, `_longitudinal.py`, `_longitudinal_metrics.py`, `_sensitivity.py` | `N_ELECTRODES = 96` | `array_geometry(subject, array)["n_electrodes"]` |
| `scratch_rocky_spatial.py`, `_deepdive.py`, `_giants.py` | `GRID = 10`, `np.full((10, 10), …)` | `GRID_COLS`/`GRID_ROWS` from the mapfile |
| `scratch_rocky_impedance.py`, `_impedance_qc.py` | `ELECTRODES_PER_FILE = 16` | `PINS_PER_HALF = PINS_PER_BANK // 2` |
| `scratch_validation_nigel…` | `np.full((10, 10), …)` | sized from `cmp_rows`' own extent |
| `scratch_load_nigel…` | bare `assert nch == 96` | named `EXPECTED_NCH`, documented as a guard |

`array_geometry()` lives in `scratch_cohort_io.py`. It resolves the serial from the subject registry, finds that array's `.cmp` in `configs/probes/`, and returns `n_electrodes`, `n_cols`, `n_rows`, `channel_max` and the mapfile it used — or `source = "default"` when no mapfile exists, so a caller can refuse to run on a guess.

**Verified behaviour-preserving.** Every Rocky constant resolves to exactly its previous value (96, 10×10), and `scratch_rocky_longitudinal_metrics.py` reproduces its headline numbers unchanged.

Coverage today: Rocky I1/I2 and Fisk resolve from real mapfiles; **Nigel has no `.cmp` on record** and falls back to the default. Fisk's two maps were copied into `configs/probes/` from the data tree and both validate clean — vacant cells `(0,9) (1,8) (1,9) (9,9)` on SN1498 and `(0,0) (0,4) (8,0) (9,9)` on SN1504, neither the symmetric-corner pattern.

`(bank − 'A') × 32` was never on that list: 32 pins per bank is verified across all three geometries.

## Related

[[channel_mapping]] for the vocabulary and the verified chain, [[cmp_validation]] for per-array geometry checks, [[impedance_parsing]] for the ordering question the rev-4.00 protocol could settle.

## Sources

Numbered as in [`channel_mapping.md`](channel_mapping.md).

1. *Cerebus NSP IFU*, Rev 21.0, **LB-0028**, 2026-03 — four 34-pin banks, p25.
3. *How to interpret and use mapfiles*, Blackrock support KB — banks lettered A–H; `row` is the Central Spike Panel row.
4. *Blackrock Research Arrays IFU*, **LB-0514** — revisions 1.00 (2013) through 5.00 (2020); mapping explanation and per-device variation in 5.00 p11; map-verification protocol in 4.00 p20.

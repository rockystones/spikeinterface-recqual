# Impedance parsing (Rocky cohort)

Format of the longitudinal electrode-impedance files, and the two assumptions that must not be made silently.

## File layout

Impedance lives in per-date folders, six files per array:

```
<date>/Anterior_A1.txt   Anterior_A2.txt
       Anterior_B1.txt   Anterior_B2.txt
       Anterior_C1.txt   Anterior_C2.txt
       Posterior_*.txt   (same six)
```

Each file holds **16 consecutive EIS sweeps**, one per electrode, 19 frequencies each from 1 MHz down to 1 Hz. 6 files × 16 = 96 electrodes. Columns: `Frequency (Hz)`, `-Phase (°)`, `Z (Ω)`, `Z' (Ω)`, `-Z'' (Ω)`, `Index`, plus three mostly-empty trailing columns.

**The column header row is re-emitted between sweeps.** Reading with `pd.read_csv` yields those header rows as data, and sweep boundaries are only recoverable by detecting them. Some files also have inconsistent field counts between rows (observed 6 vs 9 in `Anterior_C2.txt`), which makes the pandas C parser fail outright. Read the file raw, split on tab, take the first three fields, and drop rows that fail to parse as float — that handles both problems at once.

`1000 Hz` is the standard electrode-impedance readout; the parser also records 10 Hz and 10 kHz as reference points.

## Date conventions

Impedance folder names use a **third** date convention beyond the two in the NEV filenames:

| Convention | Where | Example |
|---|---|---|
| `MM-DD-YYYY` | NEV 2017–2020, some impedance folders | `05-01-2023` |
| `YYYY-MM-DD` | NEV 2022–2023 | `2022-07-06` |
| `YYYYMMDD` | impedance folders | `20190228` |

All three must be parsed to build a single date axis.

## Assumption 1: impedance was NOT measured on recording days

Impedance exists for **36 dates** (2017-09-12 → 2024-07-01); recordings exist for 182. Only **5 of 182** recording dates have a same-day impedance measurement. An exact date join discards essentially everything.

The join must therefore be nearest-date within a tolerance. Coverage:

| Tolerance | Recording dates matched |
|---|---|
| same day | 5 / 182 |
| ± 7 d | 58 / 182 |
| ± 14 d | 92 / 182 (default) |
| ± 30 d | 121 / 182 |
| ± 60 d | 141 / 182 |

±14 days is defensible because chronic electrode impedance moves on a timescale of weeks to months, not days. Report the achieved coverage rather than presenting the join as complete.

## Assumption 2: electrode ordering within a file is UNVERIFIED

The files carry no electrode labels — only the bank letter and the `1`/`2` half in the filename. The natural reading is:

```
electrode_id = bank_base + (half - 1) * 16 + sweep_index + 1
bank_base: A -> 0, B -> 32, C -> 64
```

which matches the CMP formula `electrode_id = (bank - 'A') * 32 + elec`. **This is plausible but undocumented.** It is tested empirically rather than trusted: a correct mapping should show dead or very-high-impedance electrodes carrying fewer units, so the parser correlates 1 kHz impedance against gate-passing unit yield and compares the result to a shuffled null.

If that test does not clear the null, the mapping is not supported and the impedance join must be treated as unverified — the yield figures remain valid, only the impedance-to-electrode association is in doubt. Do not quietly ship an unverified mapping; a wrong bank assignment silently scrambles every per-electrode impedance conclusion while still producing plausible-looking plots.

## Observed values

Across 6 888 parsed sweeps: 1 kHz impedance p10 ≈ 195 kΩ, median ≈ 1.14 MΩ, p90 ≈ 2.95 MΩ. These are high relative to a fresh Utah array (50–500 kΩ), which is consistent with a cohort spanning years post-implant, but the absolute scale should be sanity-checked against the array spec sheets in `preimplant/*.xlsm` before being used quantitatively.

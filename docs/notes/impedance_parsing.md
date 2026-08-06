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

### Status: UNVERIFIED as of session 4

Two attempts, both inconclusive. The ordering is **not** established.

**Attempt 1 — against manufacturer values.** The array spec sheet (`preimplant/*.xlsm`, sheet `Impedance Values from Automated`) lists per-electrode impedance at manufacture, indexed by the physical label `elecN`. Four candidate orderings were scored by Spearman correlation against it, using the earliest measured sweep (2017-09-12):

| Candidate ordering | rho | p |
|---|---|---|
| `A1 -> electrode_id 1..16` (assumed) | −0.040 | 0.70 |
| interleaved (`1,3,5,...`) | −0.110 | 0.29 |
| reversed within half | +0.095 | 0.36 |
| halves swapped | −0.082 | 0.43 |

No candidate separates from chance. **This does not show the assumed mapping is wrong** — it shows the reference carries no usable signal. Median impedance had already risen from 333 kΩ at manufacture to 1749 kΩ by the first measurement, a 5× change during implantation, so manufacturer values no longer predict post-implant impedance for any mapping.

Note also that the *Posterior* spec sheet (`13966-8 SN 1025-001497.xlsm`) fails to open — `zipfile.BadZipFile: File is not a zip file`. It is corrupt or is an older `.xls` saved under an `.xlsm` extension. Only the Anterior sheet was usable.

**Attempt 2 — against unit yield.** Correlating 1 kHz impedance with gate-passing unit yield gave rho = +0.041 (p = 0.52) over 249 electrode-sessions. That run only had three sessions of re-sort output available, so it is underpowered rather than negative. Re-run it against the full cohort before drawing any conclusion.

**A fifth identity.** The manufacturer label is *not* the NEV electrode id. In the CMP, `label elec96` is bank C elec 1, i.e. `electrode_id = 65`. Any join between the spec sheet and NEV data must route through the CMP's `label -> (bank, elec)` mapping. This sits alongside the four-way disambiguation in [utah_channel_mapping.md](utah_channel_mapping.md).

**How to actually resolve it.** Ask whoever ran the impedance tester which order it sweeps a bank connector, or identify an electrode that is independently known to be broken and confirm it appears at the predicted sweep position. Until then the impedance table ships with the assumed mapping recorded as an assumption, and no per-electrode impedance conclusion should be published from it.

## Session QC — which sessions were not collected the same way

`notebooks/scratch_rocky_impedance_qc.py` screens all 72 array-sessions for collection problems. **Every diagnostic is ordering-independent** — each is either a property of the session's distribution as a whole or a comparison against neighbouring sessions in time — so the unresolved within-file electrode order cannot affect any of it.

Six flags: level shift, dispersion change, open/short fraction, sweep-shape monotonicity, phase plausibility, and cross-array agreement.

**Cross-array agreement is the most diagnostic of the six.** The two arrays are independent electrodes in independent tissue; their impedances have no reason to track each other *except* through the shared measurement rig. So:

- both arrays shift together → rig, protocol, or tester configuration
- one array shifts alone → that array's connector or cable

### Findings (20 of 72 sessions flagged)

**Rig/protocol level shift — 8 dates, both arrays moving together.** 2023-01-31, 2023-03-20, 2023-05-01, 2023-06-19, 2023-12-18, 2024-01-29, 2024-04-15, 2024-07-01.

From 2023 onward the sessions alternate between two regimes roughly **7× apart** — ~1170–1550 kΩ versus ~155–215 kΩ — in consecutive runs, with the cross-array ratio staying at 0.9–1.1 throughout. Electrode impedance cannot fall 7× and recover, on two independent arrays simultaneously. This is a measurement configuration difference, not biology, and those sessions are not comparable to the rest without a correction.

**Single-array connection fault — 3 dates.** 2019-05-30 (A/P ratio 0.46), 2022-08-01 (0.57), 2022-12-12 (0.34). One array reads far lower than the other on the same day.

**Dispersion anomaly — 1 date.** 2018-06-05 Anterior.

**Incomplete sessions — 2.** 2019-02-28 Anterior and 2018-01-09 Posterior have 84 of 96 electrodes.

### The genuine trend underneath

Excluding the flagged sessions, 2017 → 2022 shows a steady decline from ~1750–2070 kΩ to ~850–990 kΩ. That is a plausible chronic trajectory and is the signal any longitudinal impedance analysis should be built on. Do not mix the 2023+ two-regime sessions into it.

## Observed values

Across 6 888 parsed sweeps: 1 kHz impedance p10 ≈ 195 kΩ, median ≈ 1.14 MΩ, p90 ≈ 2.95 MΩ. These are high relative to a fresh Utah array (50–500 kΩ), which is consistent with a cohort spanning years post-implant, but the absolute scale should be sanity-checked against the array spec sheets in `preimplant/*.xlsm` before being used quantitatively.

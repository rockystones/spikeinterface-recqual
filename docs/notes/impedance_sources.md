# Two kinds of impedance, and what each is indexed by

This project has impedance from two entirely different instruments. They are not interchangeable, they are not indexed the same way, and only one of them is settled.

## 1. Blackrock 1 kHz impedance — **settled**

Measured through the recording chain itself: the headstage and NSP run an impedance check at 1 kHz. It appears in the factory workbook's *Impedance Values from Automated* sheet and in the automated `.txt` dump shipped with the array, and it is what a Z-check in Central reports.

**It is indexed by channel id (bank and pin), not by electrode.** The rows are headed `elec1..elec128`, which is a misnomer.

Proved directly from the manufacturer's own workbook, which prints the same array twice on one sheet — *Electrode numbering viewing from pad side* and *Electrode Impedance viewing from pad side*. Every grid position therefore gives an electrode number and its impedance together, with no indexing assumption involved. Walk the positions, look each electrode up in the `.cmp` for its channel id, and see which row of the impedance table carries that impedance:

| hypothesis | positions matched |
|---|---|
| row *N* = **channel id** | **1,248 / 1,248 — 100.00 %** |
| row *N* = electrode number | 31 / 1,248 — 2.48 % |

13 arrays, 96 positions each. `notebooks/scratch_impedance_crosscheck.py`. The 2.48 % is chance: impedance values repeat within an array, so a few rows coincide either way.

Two further arrays (`1025-002456`, `1025-002457`, lot 1049) could not be tested — every impedance value is present in their sheet, but that lot's workbook lays the grids out differently and the window search does not find them. Not a discrepancy, just an untested template.

Rows above the array's channel count are unused pins on a larger front end and read in the kilohm range against ~100–1000 Ω for a real electrode.

**Rule: join Blackrock impedance to recordings on `channel_id`.** Joining on electrode number produces a complete, plausible, permuted table.

## 2. Full-spectrum EIS and CV from an external potentiostat — **parked**

`D:\Claude Code\Blackrock files\Blackrock Utah array\Characterization\10by10\` — the experimenter's own electrochemical characterisation, 13 arrays.

Per array, six files: `EIS-{A,B,C}` and `CV-{A,B,C}`. Most are labelled `pristine`; `1025-002456` and `1025-002457` are `explant`. A handful carry condition suffixes that are deliberate rig experiments and must not be pooled with the rest — `CV-C-WRONG CONNECTION`, `-TWOELEC-GNDWIRE`, `-TWOELEC-GNDWIRE-DIS`, `-B2`, and one `EIS-A&B` where two banks were run together.

**Structure, verified on `SN1025-004377`:**

- Each `EIS-{bank}` file is **32 sweeps × 16 frequencies**, concatenated with a repeated header line before each sweep — so a naive `read_csv` yields 543 rows including 31 header strings masquerading as data.
- Frequency ladder runs 100 kHz down to 1 Hz.
- Columns: `Frequency (Hz)`, `Z (Ω)`, `-Phase (°)`, `Z' (Ω)`, `-Z'' (Ω)`, `Time (s)`, `Index`.
- `CV-{bank}` files are ~98,000 rows of `WE(1).Potential (V)`, `WE(1).Current (A)`, `Time (s)`, `Scan`, `Index`.

Three bank files × 32 sweeps = 96, which matches the array. So the natural hypothesis is that **sweep *k* of file `-A` is bank A pin *k***, i.e. the same channel-id ordering as the Blackrock file.

**That is a hypothesis, not a finding.** The 1 kHz values do not match the factory numbers in sweep order — for `SN1025-004377` bank A the first sweeps give 85.9, 88.2, 169.1 kΩ against a factory 115, 201, 159 kΩ. That mismatch is uninformative on its own: different instrument, electrolyte, temperature, reference configuration and measurement date all move absolute impedance, so it cannot distinguish "different ordering" from "same ordering, different conditions".

### How to settle it

Blackrock published an empirical protocol for exactly this, in **LB-0514 revision 4.00 only** — it was removed in 5.00:

> *"You can run an impedance test to confirm the mapping … gradually lower the array vertically until it is 'partially' submerged in the saline e.g. one corner plus few surrounding electrodes … Those electrodes staying outside the saline solution must be noisier and their impedance must be much higher … Check of those electrodes inside or outside the saline to see if they match electrode locations mentioned in your excel files and if they belong to the right bank."*

Partial submersion imposes a *known spatial pattern* on the impedances, which is the one thing that can identify an ordering without assuming it. The same trick would work on the potentiostat: measure with a known subset of shanks wet, and the sweep order falls out.

Failing that, a correlation approach is weaker but cheap: rank-correlate each candidate ordering of the EIS 1 kHz values against the factory values for the same array. It relies on the two instruments agreeing about *which* electrodes are outliers even when they disagree about absolute values, which for the high-impedance failures is a reasonable bet — but it is evidence, not proof.

**Until settled, publish no per-electrode conclusion from the EIS data.** Aggregate statistics per bank, and per-array distributions, are ordering-independent and safe.

## Related

[[channel_mapping]] for the channel/electrode vocabulary and the verified chain, [[impedance_parsing]] for the chronic `{Array}_{Bank}{Half}.txt` measurements, [[array_catalog]] for the workbook cross-validation this proof came out of.

# The potentiostat → Blackrock channel map

Impedance was measured on an Autolab potentiostat through a D-Sub 25 / IDC
breakout, written as **six files per array** — `A1 A2 B1 B2 C1 C2`, sixteen
sweeps each. Nothing inside those files says which Utah electrode a sweep is.

The lab authored the answer at the time, in
`array info/Oops/oops_array_to_matlab.xlsx` and
`array info/Monkey_P/monkeyP_array to matlab.xlsx`. Those sheets had never
been machine-read. They now are: `notebooks/scratch_impedance_map.py` →
`configs/probes/impedance_channel_map.csv`.

## The chain

```
impedance file + sweep position   (A1, pos 1)
  -> matlab channel               (1..96, in blocks of 16)
  -> pad code                     (the sheet's "array map" row)
  -> .cmp electrode label         (elecNN -- the pad code IS the label)
  -> bank + pin                   (A..C, 1..32)
  -> channel_id = (bank-'A')*32 + pin
```

The join is on the **electrode label**, not on geometry. That matters: the
sheet's `Epad` grid is drawn *"viewing from pad side"* while the `.cmp` counts
rows **bottom to top**, and composing those two backwards is exactly the silent
error CLAUDE.md warns about. Joining on `elecNN` sidesteps the orientation
question entirely.

## Four internal checks, all passed

| check | result | why it matters |
|---|---|---|
| Oops sheet A vs B vs Picasso Anterior vs Posterior | **96/96 identical, all four** | the map is a property of the **cable**, not the array — so four arrays must give one map, and they do |
| pad codes | **bijection over 1..96** | no duplicate or missing electrode |
| pad code → `.cmp` `elecNN` | **96/96 joined, 0 unmapped** | the pad codes really are the `.cmp`'s labels |
| `Epad` grid vs `.cmp` geometry | **col 96/96, row 96/96 with rows flipped** | independent of the label join — proves the codes are positions, and confirms the top-to-bottom vs bottom-to-top flip |

The last two are independent of each other: one uses labels, the other uses
coordinates, and both land on the same assignment.

The first 16 rows, to show it is a genuine permutation and not the identity:

| half | pos | pad | electrode | channel_id |
|---|---|---|---|---|
| A1 | 1 | 17 | elec17 | **16** |
| A1 | 2 | 48 | elec48 | **6** |
| A1 | 3 | 45 | elec45 | **15** |
| A1 | 4 | 18 | elec18 | **14** |
| A1 | 5 | 36 | elec36 | **13** |
| A1 | 6 | 27 | elec27 | **12** |

## This contradicts what the pipeline currently does

`data/derived/rocky/impedance_long.parquet` already carries a `channel_id`,
assigned by an earlier pass that assumed **sweep order equals channel order** —
A1 sweep 0 → channel 1, sweep 1 → channel 2, and so on.

**The two maps agree on 0 of 96 channels.** One of them is wrong, and every
impedance-joined result in the project depends on which.

The authored map has documentary provenance and four internal checks. The
naive map has neither — it was an assumption, never verified. That is the
basis for preferring the authored one.

## The empirical validation is inconclusive — read this before relying on it

The obvious physical test is that a higher-impedance electrode should show a
higher thermal noise floor. Run on Rocky, 52 session-arrays with impedance and
ephys in the same year:

| map | median ρ (log₁₀\|Z\| vs noise) | cells with ρ>0 | cells p<0.05 |
|---|---|---|---|
| authored | −0.001 | 50% | 19% |
| naive | +0.036 | 56% | 17% |

Paired within session-array, Wilcoxon **p = 0.44**, authored higher in 24 of 52
— chance. **The test cannot tell the two maps apart.**

An extremes test (bottom-20% vs top-20% impedance) is worse than useless: it
gives the *naive* map significance (units/electrode p=1e-4) in the direction
**high impedance → more units**, which is either a real isolation effect or an
ordering coincidence, and this data cannot say which.

**Why the test has no power.** `noise_uv` is a MAD of int16 counts scaled by
0.25 µV, so it lands on a coarse grid — a median of only **24 distinct values
across 96 electrodes**. With that many ties, a rank correlation cannot resolve
a 96-way permutation. The failure is in the probe, not necessarily in either
map.

**So: the map is derived and internally verified, not empirically confirmed.**
Do not describe it as validated against ephys.

## Three more empirical tests, all run 2026-09-12, all null

`scratch_impedance_extended.py`, on the full 52-date record (the 16
missing 2019–2021 dates now ingested):

- **The bench arbiter.** Rocky's pre-implant potentiostat sweeps against the
  factory workbook (channel-indexed, proven 1248/1248). Both maps assign the
  same 16 channels to a file half, so only the within-half ordering
  discriminates: 12 halves × 16 values. Median Spearman ≈ 0 for authored,
  naive **and both reversed variants**, and the bench-max sweep lands on the
  factory-max channel at the 1/16 chance rate. No ordering is supported —
  either the within-half impedance spread carries no stable signature across
  instruments, or the bench session's seating did not match either map.
- **The open/short test is retired.** The potentiostat's open sweeps sit at
  ephys percentile ≈ 0.5 under *every* candidate: they do not replicate in
  the recording chain at all, so they are faults of the impedance measurement
  chain (breakout/cable seating), not dead electrodes. They cannot validate
  any map, and `impedance_qc`'s open/short fractions should be read as rig
  diagnostics, not electrode states.
- **The border arbiter.** Border-vs-interior is negative under all four
  candidates (the bank-half component is shared between them), so it cannot
  separate them either; over 52 dates authored is only marginally the most
  negative (−0.042 dex, 69% of dates).

**Consequence: the choice stays documentary** — the authored map's provenance
and four internal checks against the naive map's nothing — and per-electrode
impedance conclusions keep the "derived, not empirically confirmed" label.

Still open as validators:

- **A less quantised ephys probe** — continuous-data RMS rather than the
  snippet MAD, which would remove the tie problem.
- **Rocky's second implant.** New arrays, same cable: the map should transfer
  unchanged, and any per-array structure that follows the arrays rather than
  the cable would falsify it. Blocked tonight — the 2025 I2 files live on
  unmounted volumes (G:, E:).

## The measurement itself, from the NOVA procedures

`Patrick/procedures/*.nox` are Autolab **NOVA procedure** files -- the protocol,
not data. They are .NET binary (`EcoChemie.Shared100 v10.0.5557`) but carry
readable XML fragments, so the measurement is recoverable:

| parameter | value |
|---|---|
| technique | **FRA impedance, potentiostatic** |
| amplitude | **0.01 V (10 mV)** |
| integration | 1 s, 1 cycle |
| `PC_1KHz_IMP_16ch` | **1000 Hz**, single point |
| `PC_multi_IMP_16ch` | 10, 23.691, 56.125, 132.96, 315 Hz -- log-spaced, 5 points |
| `PC_Monkey_IMP`, `monkey_working` | 10, 200, 315 Hz |

Amplitude and integration are **identical across every procedure**, so a value
is comparable across dates and animals without rescaling. The `16ch` in the
filenames and a `FRA impedance tutorial #1 MUX` procedure alongside confirm the
**16-channel multiplexed** scheme that produces the six `A1..C2` files.

The deployed sweeps were denser than these templates -- the chronic record
carries 19-, 45- and 75-point ladders by era -- so the templates fix the
technique, amplitude and integration but not the frequency list.

The hope that the `.nox` files might carry per-channel labels is retired
(2026-09-12): every `.nox` in `Patrick/` is a procedure, and the `FRA
impedance tutorial #1 MUX` one, plus its model-cell output
(`modelcelltests/tut1_mux_a-e_1-5.txt`, five ~100 Ω sweeps over known
sockets), establishes only that sweeps are written in MUX iteration order --
which every candidate map already assumes. The DSub-to-electrode pinout is
not in the instrument files.

## Scope

Derived from Oops and Picasso sheets, which agree exactly, so it is the
cable's map and applies wherever that rig was used — including Rocky, whose
dumps use the same `Anterior_A1.txt` file convention. It does **not** apply to
the TDT rig, which is a different problem ([[tdt_channel_map]]).

## Related

[[channel_mapping]] for the ephys equivalent and the `(bank−'A')*32 + pin`
identity, [[impedance_sources]] for where the dumps come from,
[[legacy_archive]] for the sheets themselves.

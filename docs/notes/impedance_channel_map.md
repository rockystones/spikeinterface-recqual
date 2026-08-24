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

## What would actually validate it

- **A deliberately open or shorted channel.** A single electrode known to be
  disconnected would appear at an extreme impedance and at a dead ephys
  channel, and the two must land on the same `channel_id`. `impedance_qc`
  carries `frac_short` / `frac_open` columns — a session with a nonzero count
  is the test.
- **A less quantised ephys probe** — continuous-data RMS rather than the
  snippet MAD, which would remove the tie problem.
- **The `.nox` raw potentiostat files**, which may carry per-channel labels the
  exported `.txt` dumps dropped.
- **Rocky's second implant.** New arrays, same cable: the map should transfer
  unchanged, and any per-array structure that follows the arrays rather than
  the cable would falsify it.

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

The deployed sweeps were denser than these templates -- Rocky's dumps carry
`n_freq = 19` -- so the templates fix the technique, amplitude and integration
but not the full frequency list.

## Scope

Derived from Oops and Picasso sheets, which agree exactly, so it is the
cable's map and applies wherever that rig was used — including Rocky, whose
dumps use the same `Anterior_A1.txt` file convention. It does **not** apply to
the TDT rig, which is a different problem ([[tdt_channel_map]]).

## Related

[[channel_mapping]] for the ephys equivalent and the `(bank−'A')*32 + pin`
identity, [[impedance_sources]] for where the dumps come from,
[[legacy_archive]] for the sheets themselves.

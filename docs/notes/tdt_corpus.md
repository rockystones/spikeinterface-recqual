# The TDT corpus: Luigi, Oops and Picasso

370 tank blocks across three subjects, 2013–2017. This is the project's second
acquisition system and it differs from Blackrock in ways that change which
analyses are possible, not just how the files are opened.

`notebooks/scratch_tdt_io.py`, `scratch_tdt_inventory.py`,
`scratch_tdt_free.py`, `scratch_tdt_sorted.py`, `scratch_tdt_longitudinal.py`.
Inventory in `data/derived/tdt_inventory.parquet`.

## What is there

| subject | blocks | live (block, array) | dates | median block | root |
|---|---|---|---|---|---|
| **Luigi** | 193 | 176 | 2013-01-20 → 2016-08-30 | 13–18 min | `C:\MyData\Monkeydata\Luigi` |
| **Oops** | 85 | 147 | 2015-06-12 → 2017-02-15 | 185 s | `Monkey Data/Oops` |
| **Picasso** | 92 | 106 | 2015-11-09 → 2017-04-14 | 190 s | `Monkey Data/Picasso` |

Luigi's blocks are 4–6× longer than the others because they are task
recordings, not the 3-minute baselines Oops and Picasso ran.

## Stores, and what each one is

A tank declares its stores in the `.Tbk`. Across this corpus:

| store | type | channels | rate | samples | what it is |
|---|---|---|---|---|---|
| `eNe{n}` | snippet | 96 | 24414 Hz (Luigi 2013: 48828) | 40 | threshold crossings, the NEV analogue |
| `Raw{n}` | stream | 96 | 24414 Hz | 2048 | broadband |
| `pNe{n}` | stream | 96 | 763 Hz (Luigi 2013: 1526) | 128 | **LFP** |
| `Tick`, `Rwrd`, `Syc{A,B}` | event | — | — | — | clock, reward, sync |

**The trailing digit is the array**, and it is a rig convention rather than
something the tank records. Oops and Picasso ran two arrays; Luigi's 2013 rig
declared three.

**Rates are per store, not per tank.** Luigi's 2013 blocks run `Raw1` at 24414
Hz beside `Raw2` at 48828 Hz and all three `eNe` stores at 48828 Hz. Any code
that reads one rate per recording is wrong here — which is what CLAUDE.md's
"never hardcode sampling rate" is protecting against.

**LFP arrives free.** Every block carries `pNe`, which is the first time this
project has had a real LFP stream rather than a decimation plan.

## Reading a tank

NEO's `TdtRawIO` needs the **`.tev` file path**, not the block directory.
Passing the directory puts it in multi-block mode, finds no blocks, and dies
with `IndexError: list index out of range` from an empty segment list.

```python
io = TdtRawIO(dirname=str(tev_path))       # tev FILE, not its folder
io.parse_header()
```

`spikeinterface.extractors.read_tdt(folder_path=<tev path>, stream_name="Raw1")`
takes the same argument and works.

### `wf_left_sweep` is wrong, and it matters

NEO reports `wf_left_sweep = NumPoints // 2` = **20** for these 40-sample
snippets. The trough actually sits at sample **8**: 13,405 of 18,700 snippets
in the first Oops block, 4,838 more at 9, and the modal trough is 8 in 250 of
251 measured (block, array) rows.

Trusting NEO's 20 would take the "baseline" from samples 0–17, i.e. from across
the whole spike, and inflate every noise estimate. `scratch_tdt_io.NBEFORE = 8`
overrides it and `scratch_tdt_free.py` re-measures it per row so a violation is
visible rather than silent.

### Units — per store, and NEO will not help

`tdtrawio` **hardcodes** `units = "uV"`, `gain = 1.0` on every stream channel
and `units = "V"`, `gain = 1.0` on every snippet channel
([neo#1369](https://github.com/NeuralEnsemble/python-neo/issues/1369)). It
makes no attempt to scale. What the stores actually hold, from the Tbk
`DataFormat`:

| store | Oops / Picasso | Luigi 2015–16 | Luigi 2013 |
|---|---|---|---|
| `eNe*` snippets | float32 | float32 | float32 |
| `Raw*` broadband | float32 | float32 | **int16** |
| `pNe*` LFP | **int16** | **int16** | **int16** |

- **Snippets are float32 volts everywhere**, so the `×1e6` in `read_channel`
  is right for the whole corpus. Every metric in this note rests on that.
- **`Raw*` read through `read_tdt` is already in µV** for the float32 tanks.
  Cross-checked against snippets on the same events on one channel: median
  snippet |trough| 14.7 µV against broadband troughs of 18–34 µV in the same
  windows, i.e. the same order.
- **Luigi's 2013 `Raw2` is int16 ADC counts.** Applying the snippet-side 1e6
  gives an absolute maximum of 3.28e10 "µV" — that is 32767 × 1e6, and it is
  the tell. `stream_units()` returns `"adc_counts"` for those stores. The
  counts-per-µV factor comes from the PZ amplifier setting and is **not in the
  tank**, so nothing scale-dependent can be reported in µV from them.
  Scale-invariant work — sorting, SNR, correlations — is unaffected.
- **LFP is int16 in every subject**, so `pNe` amplitudes are counts too.

The `eNe` timestamp marks the **trough**, not the threshold crossing: the
best-correlating alignment against filtered broadband sits at
`int(t·fs) − 1` (r = 0.57 on the session mean).

About **0.2% of snippets arrive NaN-filled** and are dropped in
`read_channel`; left in, they poison every percentile downstream.

## Dates: three sources, and which to believe

The folder name, the file stem inside it, and the tank clock all carry a date.

- **The folder is the session date.** Ten blocks carry a stem-date typo, mostly
  a New Year year-off-by-one (`Picasso_2016_01_14-1` holding files stamped
  `Picasso_2015_01_14`). The estate census flagged these without being able to
  resolve them.
- **The tank clock is UTC.** Two Picasso blocks start at 00:03 and 00:04 UTC,
  which is ~19:00 US Eastern the previous evening — the corpus's modal
  recording hour (40 of 177 blocks). Read as local time they would be the only
  two past-midnight sessions in two years, and the corpus would contain no
  session before 13:00. The same ruling was already made for the Blackrock NSP
  clock: prefer a clock offset over past-midnight recording.
- **Luigi's `Block-N` directories carry no date at all**, so the UTC clock
  converted to `America/New_York` is all they have. `date_source` records which
  route each row took.

Two Luigi blocks disagree by **more than a day** (`Luigi_2015_11_18-3` folder
vs clock 11-23; `Luigi_2016_05_31-2` vs 06-15). A timezone cannot explain
five and fifteen days. Most likely a re-record filed into an earlier session's
folder; `date_gap_days` flags them and trends should drop them.

## The online sortcode is not a unit id — except for Luigi

This is the single most consequential difference from the Blackrock corpus.

| subject | max distinct codes | events code 0 | events code 1 |
|---|---|---|---|
| Oops | 4 | 0.276 | 0.723 |
| Picasso | 2 | **0.943** | 0.057 |
| Luigi | 5 | 0.483 | 0.219 |

For **Oops and Picasso** the online sortcode is an *accept flag*: code 1 means
the online discriminator liked the crossing, and no channel carries a second
identified neuron. Unit counts are therefore **not available** from the online
sort, and the sorting-based metric layer that carried S10 on Blackrock does not
exist here without re-sorting the broadband.

Picasso's discriminator accepted only 5.7% of crossings while Oops's accepted
72%. That is a rig setting, not a difference between animals.

**Luigi's 2013 rig is different** — five distinct codes and a 53% keep rate,
with real partition structure (ARI 0.49 against the offline sort).

## Which array is live

A declared store is not an acquiring store.

| subject | array | blocks declaring | blocks acquiring | live range |
|---|---|---|---|---|
| Luigi | 1 | 193 | 32 | 2015-04-24 → 2016-08-30 |
| Luigi | 2 | 148 | **144** | 2013-01-20 → 2013-05-17 |
| Luigi | 3 | 148 | **0** | — |
| Oops | 1 | 85 | 85 | 2015-06-12 → 2017-02-15 |
| Oops | 2 | 78 | 62 | 2015-06-12 → 2016-12-21 |
| Picasso | 1 | 81 | 80 | 2015-11-09 → 2016-12-30 |
| Picasso | 2 | 92 | 26 | 2015-11-09 → 2017-04-14 |

Luigi declares three arrays and only ever acquires on one at a time. Picasso
runs array 1 through 2016 and switches to array 2 for 2017. Any pass that
assumes both arrays are present will average live data with zeros.

## Array identity

Serials supplied by the operator on 2026-08-18:

| subject | anterior | posterior | mapfile in `configs/probes` |
|---|---|---|---|
| Oops | 1025-001391 | 1025-001393 | both |
| Picasso | 1025-001499 | 1025-001503 | both |
| Luigi | 1025-001082 | 1025-001085 | **neither** |

All four available `.cmp` files parse as 96 electrodes on a 10×10 grid, banks
A–C, channels 1–96.

**Which store is which anatomy is still unknown.** The serial↔anatomy link is
recorded; the store↔anatomy link is a rig-wiring fact that the tank does not
carry, so `eNe1` cannot yet be called Anterior. `configs/subjects/*.json`
holds `tdt_stores` with both entries null, and nothing downstream resolves
geometry by array number until that is confirmed. Analyses are reported by
array **number**, which is unambiguous.

## What each analysis layer can reach

| layer | blocks |
|---|---|
| sorting-free, from snippets | **370** (all) |
| sorting-free, from broadband | 100 (Oops 34, Picasso 35, Luigi 44 — via `.sev`) |
| LFP (`pNe`) | 370 |
| legacy offline sort | 153 (Luigi 144, Oops 5, Picasso 4) |
| legacy sort **and** broadband on the same block | **6** (Oops 5, Picasso 1) |

**No measurement floor is computable on this corpus.** A floor needs the same
store sorted twice by different hands, and no block has that.
`Oops_2015_09_04-1` carries two sorts, but they cover different arrays.

## Related

[[monkey_corpus]] for the Blackrock corpus this parallels,
[[snippet_noise_floor]] for the noise estimator this corpus independently
validates, [[measurement_floor]] for the floor that cannot be measured here,
[[tdt_legacy_sorts]] for what the 153 legacy sorts contain.

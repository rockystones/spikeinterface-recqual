# Adding Chase, Oops and Picasso to the cohort table

`notebooks/scratch_cohort_extend.py` → `data/derived/cohort/`. Takes the cohort
table from 693 recordings on 3 subjects to **962 on 6**, and makes
`scratch_cohort_figures.py` — which was already subject-generic — draw all of
them. 23 figures, C1–C3 per subject plus the two shared panels.

| subject | rows | with a unit yield | span | contributes |
|---|---|---|---|---|
| Chase | 19 | **19** | 2009-03 → 2010-02 | a full series |
| Oops | 145 | 6 | 2015-06 → 2017-02 | noise floor; yield is 6 points |
| Picasso | 106 | 4 | 2015-11 → 2017-04 | noise floor; yield is 4 points |

## Luigi, added 2026-08-21

Luigi entered once its sorting-free layer existed ([[tdt_corpus]]), and it is
not the thin subject Oops and Picasso are:

| array | rows | with a yield | span |
|---|---|---|---|
| Array2 | 150 | **150** | 2013-01-20 → 2013-05-17 |
| Array1 | 31 | 0 | 2015-04-24 → 2016-08-30 |

**Array2 is the first TDT array in this project with a real longitudinal yield
series** — 150 sorted sessions over four months. An earlier reading of this
note said Luigi had 6 sorted blocks; that came from looking only at
`offline_sort_status_luigi.parquet` and missing the 144 Luigi rows sitting in
the shared `offline_sort_status.parquet` under dated sort names.

Its gate pass rate is **33.6%** against Oops's 11.1% and Picasso's 15.7%. That
is the strongest evidence yet that the TDT subjects' low pass rates are a
sorting *configuration* — OpenSorter assigning exactly two units to almost
every channel — rather than a property of TDT recordings.

### Two things make Luigi's series awkward, and neither is a bug

**The two arrays never overlap in time.** Array2 is 2013 and Array1 is
2015–16, with nothing in between; Oops and Picasso record both arrays
simultaneously. The subject registry's implant window (2015-05-05 →
2016-01-14) excludes the 2013 half entirely. They are carried under one implant
label because splitting them would assert a second implant nobody has
confirmed — **open question for the owner**. If 2013 is a different implant,
these two must not share an implant-age axis.

**January 2013 is a step, not a starting point.** Monthly medians on Array2:

| month | noise µV | amp µV | units/electrode |
|---|---|---|---|
| 2013-01 | **7.96** | **36.3** | 0.19 |
| 2013-02 | 18.16 | 94.6 | **0.62** |
| 2013-03 | 14.07 | 96.4 | 0.12 |
| 2013-04 | 13.03 | 66.0 | 0.02 |
| 2013-05 | 12.25 | 51.4 | 0.01 |

Noise, amplitude and yield all shift together between January and February —
noise less than half, amplitude a third. Metrics moving together by a common
factor is the signature of a **gain or filter change**, the same reasoning that
identified two acquisition regimes in [[equipment_comparison]]. Tissue does not
do that.

The acquisition screen does not catch it, because it flags sessions whose noise
runs *above* 2× the array median and January runs below.

So the whole-series rho mixes a step with a trend and disagrees in sign with
the endpoints on noise, amplitude and SNR — exactly the trap
[[cohort_longitudinal]] records for Rocky I1 Anterior. **Read Luigi Array2 from
February onward**, where the decline is real and severe: yield falls from 0.62
to 0.01 units per electrode, roughly 60-fold in three months.

## The gate had to be recomputed, not reused

`chase_units.parquet` and `tdt/offline_sort_units.parquet` both carry a
`passes_gate` column. It means `snr >= 4` and nothing else. The cohort's gate
is four criteria — `snr >= 4`, `n_spikes >= 50`, peak-to-trough duration inside
0.15–1.20 ms, and trough within 0.20 ms of the alignment point. Reusing those
columns would have given the new subjects a looser gate than Rocky's and
inflated their yield and pass fraction in a table whose only purpose is
cross-subject comparison.

So the pass re-reads waveforms and calls the same `unit_metrics()` the
Blackrock path calls. What that costs:

| subject | units | pass the cohort gate | dominant rejection |
|---|---|---|---|
| Chase | 920 | 809 (**87.9%**) | `snr<4` 104 |
| Oops | 1124 | 125 (**11.1%**) | `snr<4` 969 |
| Picasso | 713 | 112 (**15.7%**) | `snr<4` 555 |

The three shape and count criteria reject little — 11 units on Chase, 200 on
Oops, 128 on Picasso. **SNR does nearly all the work**, and the TDT pass rates
reproduce what the legacy-sort pass found independently: OpenSorter assigned
exactly two units to 913 of 929 TDT channels, which is a configuration, not
tissue ([[tdt_legacy_sorts]]). Chase's 88% is the Plexon corpus behaving like
the Blackrock ones.

## Two things these rows do not support

**The TDT yield panels are 5 and 4 points.** Only 6 Oops and 4 Picasso blocks
were ever offline-sorted; the online sortcode is an accept flag, not a unit id
([[tdt_corpus]]). The other 241 blocks contribute a noise-floor row and nothing
else, which is why `C2_metrics_Oops_I1.png` has one dense panel and five sparse
ones. The `n >= 8` guard in `trends()` correctly refuses to fit the sparse
metrics, so `cohort_trends.parquet` holds only `noise_med` for Oops and
Picasso. Do not read those five panels as a longitudinal result.

**Array numbers are not anatomy.** Both subjects have registered serials, but
which store is anterior and which is posterior is a rig-wiring fact that is not
in the tank and has not been confirmed ([[tdt_channel_map]]). Arrays are named
`Array1`/`Array2` and geometry resolves to the 96-electrode default;
`geometry_source` reports `default` rather than a mapfile name so nothing
downstream mistakes it for a verified map.

## The noise floor is unit-weighted, and on Chase that matters

`cohort_sessions.noise_med` is `noise_uv.median()` **over units**, so an
electrode counts once per unit it carries. That is the Blackrock definition and
the extension matches it. On most series it makes no difference:

| series | unit-weighted | per-channel | source of the per-channel value |
|---|---|---|---|
| Rocky Anterior | −0.551 | −0.570 | continuous free layer, n=217 |
| Rocky Posterior | −0.489 | −0.488 | continuous free layer, n=214 |
| **Chase Array1** | **−0.858** | **+0.037** | `chase_sessions.noise_med`, n=19 |

Rocky's two definitions agree to two decimal places. Chase's disagree
completely: unit-weighted noise falls hard while the array's own channel median
is flat.

The mechanism is selection, not noise. Chase records on ~90 channels
throughout but its unit count falls from 86 to 22 over the year, and the units
that survive sit on the quietest channels. The unit-weighted median therefore
tracks *which electrodes still carry units*, not what the array's noise floor
is doing. **On a series whose yield collapses, unit-weighted noise is partly a
yield metric.** Read Chase's C2 noise panel with that in mind; the flat
`+0.037` from `chase_sessions.parquet` is the statement about the hardware.

This is not a reason to change the definition — doing so would break parity
with every existing Blackrock row — but it is a reason to check the per-channel
value before attributing a noise trend to the electrodes.

## A bug this pass exposed

`trends()` took `head(5)`/`tail(5)` of each group to report `first → last`
without sorting by date. `groupby` preserves row order, not date order. Fisk,
Nigel and Rocky I2 happened to be stored date-ordered; **both Rocky I1 arrays
were not**, and neither was Chase, which arrives in filename order whose first
entry is its last session.

| series | reported | actual |
|---|---|---|
| Rocky I1 Anterior | 0.19 → 0.19 | **2.37 → 0.19** |
| Rocky I1 Posterior | 0.27 → 0.00 | **1.81 → 0.00** |
| Chase amp_med | 65 → 109 µV | **108 → 76 µV** |

Every `rho` and `p` was computed against the date and was never affected. The
correction is recorded in [[cohort_longitudinal]], where the Rocky I1 Anterior
row changes meaning: a weak rho beside flat endpoints read as "did not
decline", and the endpoints say **12.6-fold**.

## One unreadable file

`Chase_052709.plx` fails inside NEO's `PlexonRawIO._parse_header` with
`KeyError: 0` — a data block whose `Type` field is 0, which NEO's `block_pos`
table has no entry for. It failed identically in the original Chase pass, so it
is a property of the file, not of this code. Chase is 19 usable sessions of 20.

## Related

[[cohort_longitudinal]] for the table this feeds and the corrected endpoints,
[[figure_coverage]] for what is still missing per subject, [[chase_corpus]] and
[[tdt_corpus]] for the two source corpora, [[measurement_floor]] for the
operator floor drawn on every panel.

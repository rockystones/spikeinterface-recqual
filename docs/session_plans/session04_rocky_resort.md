# Session 04  Rocky snippet re-sort, anterior vs posterior longitudinal

## Plan

Two jobs. First, fold in the archived project from the retired Enterprise/Pro accounts. Second, re-sort a large snippet-only Utah cohort and compare anterior against posterior array quality across the implant lifetime.

**Archive merge.** `CLAUDE.md` is byte-identical to the repo; `pyproject.toml` in the archive is the pre-fix state that `4b0783b` already corrected. Nothing to merge back on either. Seven genuinely new files move into place: `docs/roadmap.md`, `docs/project_instructions.md`, four literature reports into `docs/reports/`, and four legacy MATLAB files into `matlab/`.

**Re-sort.** `D:\Claude Code\Rocky` holds 886 in-scope `.nev` (2017-09-21 → 2023-10-06) and **zero `.ns5`**. Every sorter in CLAUDE.md's pool needs continuous traces and is unusable. At 400 µm Utah pitch each electrode is independent, so per-electrode snippet clustering is the correct method rather than a fallback. Approach: pre-trigger baseline MAD for the noise floor, trough re-alignment, PCA, ISO-SPLIT (`isosplit6`), then an explicit noise-rejection gate (SNR ≥ 4, ≥ 50 spikes, physiological peak-to-trough, trough on alignment). Plexon OFS labels are scored under the identical gate for a head-to-head. Scope per user: 2017–2023 only, ignore 2025; SN 1025-001501 = Anterior.

Deliverables: `notebooks/scratch_rocky_{inventory,resort,impedance,longitudinal}.py`; `data/derived/rocky/{session_index,units_long,impedance_long,session_summary}.parquet`; `figures/rocky/05..09`; notes `snippet_sorting.md`, `impedance_parsing.md`.

## Outcome

Full cohort ran in **10.2 min** (1.8 s/combo, 8 workers): 332 paired combos, 330 with data, **100 611 unit rows**, zero errors.

### Anterior vs posterior — the posterior array failed, the anterior did not

| | Anterior | Posterior |
|---|---|---|
| Sessions | 170 | 160 |
| units/electrode, median | **0.771** | **0.401** |
| first session | 1.583 | 1.250 |
| **last session** | **1.021** | **0.000** |
| median unit SNR | 7.02 | 6.20 |
| noise floor | 11.12 µV | 10.38 µV |

Both arrays start together near 1.25–1.6 units/electrode in September 2017. From 2018 the anterior array runs roughly 2× the posterior yield (~0.9 vs ~0.4), and through late 2022–2023 the posterior collapses to **zero gate-passing units** while the anterior still holds ~0.5–0.7. The divergence is not subtle and is visible in both panels of `figures/rocky/05_yield_over_time.png`.

Headstage (marker shape) does not produce a visible step at the Analog→Digital transition, so it is not the dominant driver of the trend — worth stating because it was the main confound going in.

There is **no 2021 data**. The long connecting segments across 2021 are interpolation artefacts of the line plot, not measurements.

### Plexon OFS degrades monotonically

Fraction of OFS units passing the same gate:

| Year | Pass fraction | Sessions |
|---|---|---|
| 2017 | 0.278 | 30 |
| 2018 | 0.238 | 95 |
| 2019 | 0.195 | 101 |
| 2020 | 0.190 | 26 |
| 2022 | 0.191 | 60 |
| **2023** | **0.064** | 18 |

By 2023 fewer than 1 in 15 OFS units clears an SNR ≥ 4 / shape / count gate. Across the cohort the re-sort yields **more** usable units than OFS (median 55 vs 25 per session) from **fewer** candidates rejected at a higher rate (pass fraction 0.338 vs 0.202) — ISO-SPLIT groups noise into fewer, larger clusters that the gate removes cleanly, where OFS fragments it into many small "units".

An earlier read of "82–94 % in 2017" was drawn from the three chronologically-first sessions and was not representative; the 2017 median across 30 sessions is 0.278.

### Recording-quality events the gate caught

Five sessions flagged with a noise floor > 1.8× the array's running median:

| Date | Array | Noise µV | Ratio | Units | Candidates |
|---|---|---|---|---|---|
| 2019-05-23 | Posterior | 56.0 | 5.59 | 71 | 386 |
| 2017-10-23 | Posterior | 77.1 | 5.47 | 9 | 188 |
| 2017-10-25 | Posterior | 74.9 | 5.32 | 6 | 186 |
| 2019-05-30 | Anterior | 30.9 | 2.78 | 26 | 334 |
| 2017-10-27 | Anterior | 51.7 | 1.90 | 4 | 189 |

Diagnosed directly: in the October 2017 window the noise floor rose from 14.5 → 50.0 µV while **unit amplitude did not scale** (102 → 88 µV), event count doubled, and SNR collapsed 6.93 → 1.84. That is a genuine ground/reference/connector fault, not a gain artefact. **OFS reported ~190 units straight through it**, because it never measures the noise floor.

### Impedance — join built, association null, ordering still unverified

`impedance_long.parquet` holds 6 888 sweeps across 36 dates. Impedance vs gate-passing yield: **Spearman ρ = +0.013, p = 0.12 over 14 964 electrode-sessions** (±14 d nearest-date join). Well powered and null.

That does not settle the electrode ordering, because two independent checks both failed for different reasons — see [impedance_parsing.md](../notes/impedance_parsing.md). The mapping is recorded as an **assumption**, and no per-electrode impedance conclusion should be drawn until someone confirms the sweep order the tester uses.

### Bugs found (both would have shipped wrong numbers)

1. **`spike_count()` disagrees with the arrays it describes** — killed 150/332 combos on the first full run.
2. **NEO's segment splitting is broken here** — one 2019 file reported as 10 segments including a 143 119 s (40 h) span for a 180 s recording. Summing durations silently corrupted every rate and presence metric on multi-segment files without crashing anything. Now a single plausible primary segment is selected.

The second is the dangerous one: it produced plausible-looking numbers rather than an error. Its fix required distinguishing a real protocol change (2017 sessions are genuinely ~50 min; 2018+ are 180 s) from the artefact.

### Deferred

`src/` promotion, Tier 1 tests, and the 2025 files (user-excluded). The noise-gate thresholds are frozen from a two-file tuning pass and should be re-examined before the metric is promoted.

## SI / PI functions introduced

- `neo.rawio.BlackrockRawIO.get_spike_raw_waveforms` / `get_spike_timestamps` / `rescale_spike_timestamp` — snippet access; see [snippet_sorting.md](../notes/snippet_sorting.md)
- `isosplit6.isosplit6` — MountainSort5's ISO-SPLIT clustering, used standalone on PCA features since no SI sorter accepts snippets
- `sklearn.decomposition.PCA`, `scipy.stats.spearmanr`, `pandas.merge_asof` — not SI, no note required

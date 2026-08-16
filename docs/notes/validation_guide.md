# Validating the analyses: flow, functions, and what to inspect

Written to be checked the way you check MATLAB code — read the logic, look up
the functions, then step it and inspect the variables. Three sections per
analysis:

1. **Flow** — pseudo-code for what happens and what moves where.
2. **Functions** — what to read further, and what each returns.
3. **Inspect** — a snippet that reproduces one unit of work and leaves every
   intermediate in the namespace.

Setup (Spyder kernel, cell markers, `explore.py`) is in
[`variable_inspection.md`](variable_inspection.md) and not repeated here.

Every helper below is a **pure function returning a real object**, so the usual
move is to import and call it rather than run the script. Where a value only
exists inside a loop, `notebooks/_probe.py` stashes it — see §0.

---

## 0. Getting at values inside a loop

The MATLAB habit of dumping an intermediate to the base workspace has no direct
Python equivalent, so there is a two-line module for it:

```python
from _probe import probe          # notebooks/_probe.py
probe(noise=noise, wf=wf, elec=elec)      # anywhere, including inside a worker
```

```python
from _probe import STASH
STASH["noise"], STASH["wf"].shape
```

**It does not cross a process boundary.** Every long analysis here runs under
`ProcessPoolExecutor`, and a worker's `STASH` dies with the worker. To inspect
inside a parallel step, call the per-item function directly in your own session
— every one of them is importable and takes plain arguments.

---

## 1. Shared primitives — read these first

Everything else is built on four functions.

| function | module | returns |
|---|---|---|
| `open_nev(path)` | `scratch_rocky_resort` | `(raw, meta, chan_by_elec)`; `meta` has `sr`, `nbefore`, `duration_s`, `gain`, `primary_seg` |
| `read_electrode(raw, meta, chan_units)` | `scratch_rocky_resort` | `dict(wf=(n, n_samp) float32 µV, t=(n,) s, plexon_unit=(n,) int)` |
| `baseline_noise_uv(wf, nbefore)` | `scratch_rocky_resort` | `float` — MAD of pre-trigger samples × 1.4826 |
| `read_packets(path)` | `scratch_monkey_variants` | `(timestamps, electrode_ids, unit_classes)` straight from the packet bytes |

```python
import sys; sys.path.insert(0, "notebooks")
from pathlib import Path
from _paths import ROCKY
from scratch_rocky_resort import open_nev, read_electrode, baseline_noise_uv

p = ROCKY / "Rocky all nev/Anterior/Sorted/Sorted NEV/Rocky_Anterior_2023-07-27_Baseline_DigitalHeadstage-01.nev"
raw, meta, chan_by_elec = open_nev(p)
meta                       # sr, nbefore, duration_s, gain, primary_seg
sorted(chan_by_elec)[:5]   # channel ids present
e = read_electrode(raw, meta, chan_by_elec[1])
e["wf"].shape              # (n_spikes, n_samples) in µV
noise = baseline_noise_uv(e["wf"], meta["nbefore"])
```

**Two traps worth knowing before trusting anything downstream.**

`read_electrode` never calls `raw.spike_count()`. On this cohort that method
over-reports — 711 of 772 channel-segments in one Nigel file — and where the
bad count happened to divide the waveform buffer it produced a *silently wrong*
reshape. Lengths come from the arrays instead. `load_snippets` had the same bug
until 2026-08-16.

`wf` is already scaled to µV by `meta["gain"]`, read from the file. Never
multiply again.

---

## 2. S09 — the measurement floor

`scratch_measurement_floor.py` (labels) and `_wf.py` (waveforms).

### Flow

```
build comparison sets
    operator_sets(inventory)      -> DS vs Sidd, auto vs each, Sidd vs his redo
    sweep_sets()                  -> all 28 algorithm pairs per sweep session
group by recording                 (so each file is read once, not once per pair)

for each recording:
    for each variant file:
        label_file()  -> unit classes in packet order
    for each pair (a, b):
        compare(a, b):
            ASSERT same timestamps AND same electrodes, elementwise
            keep_a = class not in {0, 255}          # 0 unsorted, 255 noise
            keep_b = ...
            keep_agree = mean(keep_a == keep_b)     # inclusion decision
            ari_kept   = ARI over spikes BOTH keep  # partition decision
```

The assert is the point. Because sorting never re-detects (697/697 verified),
two variants are two labellings of one list, so the comparison is exact — no
spike matching, no tolerance window.

### Functions

- `sklearn.metrics.adjusted_rand_score` — permutation-invariant agreement
  between two partitions; 1.0 is identical, 0.0 is chance.
  Labels are made globally unique first as `electrode × 1000 + class`, because
  class ids restart on every electrode and a raw comparison would merge "unit 1"
  across all 96.
- `scipy.stats.wilcoxon` / `spearmanr` — paired test and rank correlation.
- `ofs_metrics_file(path, meta)` (waveform pass) — the project's per-unit metric
  row for every unit the file declares, including `pass_gate`.

### Inspect

```python
import pandas as pd, sys; sys.path.insert(0, "notebooks")
from _paths import MONKEY_ROOT
from scratch_measurement_floor import operator_sets, label_file, compare

inv  = pd.read_parquet("data/derived/monkey_inventory.parquet")
jobs = operator_sets(inv)
j    = [x for x in jobs if x["kind"] == "operator"][0]      # one DS-vs-Sidd pair
j["stem"], j["pa"].name, j["pb"].name

a, b = label_file(j["pa"]), label_file(j["pb"])
a["n_units"], b["n_units"], a["n_spikes"] == b["n_spikes"]
res = compare(a, b)
res["keep_agree"], res["ari_kept"], res["d_units"]

# the raw arrays, if you want to see the disagreement per spike
import numpy as np
ka = ~np.isin(a["_cls"], (0, 255)); kb = ~np.isin(b["_cls"], (0, 255))
np.flatnonzero(ka != kb)[:20]        # spikes the two operators treat differently
a["_eid"][ka != kb][:20]             # and which electrodes they sit on
```

**Sanity checks that should hold:** `a["_ts"]` equals `b["_ts"]` exactly;
`ari_kept` ≈ 0.99 for two operators and ≈ 0.89 for two algorithms;
`d_noise` = 0 almost always.

---

## 3. S10 — cross-subject longitudinal

`scratch_cohort_longitudinal.py`.

### Flow

```
build_worklist(inventory)
    take chain == "-01" only            # one method across all subjects
    EXCLUDE the OFS sweep directory     # 8 algorithm runs of the same sessions
    one job per (subject, implant, array, date, run, headstage)

for each job (parallel):
    one_session():
        df    = ofs_metrics_file(nev)       # a row per declared unit
        geo   = array_geometry(subject, array, implant)
        gated = df[df.pass_gate]
        noise_med = median(df.noise_uv)     # over ALL candidates, not gated
        yield     = len(gated) / geo.n_electrodes

add_axes():
    days_since_first per array-implant
    noise_baseline   = median noise per array-implant
    high_noise       = noise_med > 2 * baseline      # ACQUISITION screen

trends(): Spearman rho vs date, per array-implant per metric,
          computed twice -- all sessions and screened
```

Two things to check by eye. The screen cuts on `noise_med`, which is computed
over **all** candidates — never on the outcome, which would be circular; figure
`C3_screen` plots exactly that. And `geometry_source` on every row names the
`.cmp` used, so an array silently falling back to a default is visible.

### Functions

- `array_geometry(subject, array, implant)` in `scratch_cohort_io` — resolves
  the serial from `configs/subjects/*.json`, finds that `.cmp`, returns
  `n_electrodes`, grid extent, and `source`. **The `implant` argument is not
  optional in practice**: both Rocky implants call their arrays Anterior and
  Posterior, and without it implant 2 inherits implant 1's mapfile.
- `scipy.stats.spearmanr` — rank correlation, so a non-linear but monotone
  decline still registers and outliers do not dominate.

### Inspect

```python
import sys; sys.path.insert(0, "notebooks")
import pandas as pd
from scratch_cohort_longitudinal import build_worklist, one_session, add_axes, trends

inv  = pd.read_parquet("data/derived/monkey_inventory.parquet")
jobs = build_worklist(inv)
len(jobs)                                    # 693; if ~1321 the sweep leaked in
pd.Series([j["subject"] for j in jobs]).value_counts()

row = one_session(jobs[0])                   # one session, every metric
row["geometry_source"], row["n_electrodes"], row["pass_fraction"]

s  = pd.read_parquet("data/derived/cohort/cohort_sessions.parquet")
s.groupby(["subject","implant","array"]).high_noise.mean()   # screen rate
tr = trends(s)                               # recompute the trend table
tr[(tr.metric=="units_per_electrode") & (tr.scope=="screened")]
```

**Sanity checks:** `geometry_source` should never read `default`;
`n_candidates >= n_units`; `pass_fraction` between 0 and 1; screened `n` less
than or equal to all-sessions `n`.

---

## 4. S11 — re-detection from continuous data

`scratch_ns5_resort.py`. The only analysis where detection varies.

### Flow

```
build_worklist()   ns5 files whose array has a registered mapfile   (67)
stratified()       spread the subset over subject x array x time

for each session:
    open_recording():
        read_blackrock(stream_id resolved, not assumed)
        build probe from the array's OWN .cmp, positions = col/row x 400 µm
        map contact -> device channel BY CHANNEL ID, never positionally
        drop segments < 5 s, keep the longest, RETURN which index
    highpass_filter(300 Hz, order 3)
    signal_check()  -> peak_to_noise; recorded on every row, never gates
    for each sorter:
        run_sorter(..., docker_image=True if the sorter needs a container)
        match against the NEV's own threshold crossings, both directions
```

`frac_nev_recovered` and `frac_sorter_in_nev` are deliberately asymmetric:
the first asks how much of what the NSP found the sorter also found, the second
asks how much the sorter found that the NSP's online threshold discarded. Only
the second measures the cost of the threshold.

### Functions

- `spikeinterface.extractors.read_blackrock` — returns a lazy `BaseRecording`;
  nothing is read until `get_traces`.
- `probeinterface.Probe.set_device_channel_indices` — the contact→channel map.
  Built from a `channel_id → index` dict because Blackrock files can have
  non-contiguous electrode ids (CLAUDE.md gotcha); positional assignment is the
  silent-and-ruinous failure.
- `spikeinterface.preprocessing.highpass_filter` — lazy, zero-phase
  (forward-backward, so effective order 6). See
  [`spike_band_filter.md`](spike_band_filter.md).
- `spikeinterface.sorters.run_sorter` — `docker_image=True` pulls that sorter's
  image. Requires the `docker` package *and* `cuda-python < 12`, because SI's
  `has_nvidia()` uses the pre-12 API.

### Inspect

```python
import sys; sys.path.insert(0, "notebooks")
import pandas as pd, numpy as np
from pathlib import Path
from scratch_ns5_resort import build_worklist, open_recording, signal_check, nev_event_times
from spikeinterface.preprocessing import highpass_filter

inv  = pd.read_parquet("data/derived/monkey_inventory.parquet")
j    = build_worklist(inv)[0]
rec, info = open_recording(Path(j["ns5"]), Path(j["cmp"]))
info                                  # sr, n_segments, segment_index, duration_s
rec.get_probe().to_dataframe().head()  # positions and contact ids
recf = highpass_filter(rec, freq_min=300.0, filter_order=3)

tr = recf.get_traces(start_frame=0, end_frame=30000*5, return_scaled=True)
tr.shape, np.median(np.abs(tr - np.median(tr,0)),0).mean()*1.4826   # MAD µV
signal_check(recf)                    # peak_to_noise; ~9 good, ~4.7 means no spikes

nev = nev_event_times(Path(j["nev"]))
sum(len(v) for v in nev.values())     # what the NSP found on the same session
```

**Sanity checks:** `gain_to_uV` is 0.25 on every Blackrock channel here;
filtered MAD lands near 8–14 µV; `peak_to_noise` ≥ 6 on a session with spikes.
If a sorter returns 0 units, read `peak_to_noise` on the same row before
concluding the array is dead — four of 67 sessions have no spikes in the file.

---

## 5. S12 — analog versus digital headstage

`scratch_headstage_pairs.py` (sorted, superseded) and `scratch_headstage_free.py`
(sorting-free, current).

### Flow

```
build_pairs_worklist()   ORIGINAL nevs where both headstages exist   (242 files)

for each recording:
    free_metrics():
        per electrode: baseline_noise_uv, crossing count, |trough| per event
        session: median/p90 noise, total crossings, rate,
                 amplitude p50/p90/p99/max, peak SNR = median(amp)/noise

pair_up()   analog beside digital, one row per (array, date)
screen      per (array, headstage) -- the two amplifiers sit at DIFFERENT floors
wilcoxon    paired, analog vs digital
```

Nothing here reads a unit label, which is the whole point: the sorted version
was restricted to 40 of 121 pairs because four of five analog recordings were
never sorted, and the sorted analog subset carried 17% fewer crossings than the
unsorted one.

### Inspect

```python
import sys; sys.path.insert(0, "notebooks")
import pandas as pd
from scratch_headstage_free import build_pairs_worklist, free_metrics, pair_up

inv  = pd.read_parquet("data/derived/monkey_inventory.parquet")
jobs = build_pairs_worklist(inv)
len(jobs)                                     # 242 = 121 pairs x 2
m = free_metrics(jobs[0]); m                  # one recording, sorting-free

d = pd.read_parquet("data/derived/cohort/headstage_free.parquet")
p = pd.read_parquet("data/derived/cohort/headstage_free_pairs.parquet")
(p.noise_med_analog / p.noise_med_digital).describe()      # expect ~1.25
(p.peak_snr_med_analog / p.peak_snr_med_digital).describe()  # expect ~0.98
```

**The check that carries the conclusion:** noise ratio ≈ amplitude ratio while
the SNR ratio ≈ 1. That pattern is a gain difference. If SNR had fallen, analog
would be genuinely worse.

---

## 6. Figures

`scratch_cohort_figures.py` reads `cohort_sessions.parquet` and the S09 floor,
and writes the same four figures for every subject.

Two things it does that are easy to get wrong, and were:

- **Lines break across recording gaps** (`break_gaps`, 120 days). Rocky has a
  two-year hiatus in 2020–21 and joining across it draws a flat segment that
  reads as a stable plateau.
- **Markers are drawn from the untouched series.** Blanking the y-values to
  break the line also hides isolated sessions — it erased Nigel's terminal
  2025-09-25 recording until this was split into two calls.

```python
import sys; sys.path.insert(0, "notebooks")
from scratch_cohort_figures import operator_floor, break_gaps
operator_floor()      # {'units_per_electrode': 0.161, 'snr_med': 0.015, ...}
```

The grey band on each panel is ± half the S09 operator floor around that
series' own median: movement inside the band is within what changing the
operator does.

## Related

[[variable_inspection]] for kernel setup and `explore.py`,
[[measurement_floor]] and [[cohort_longitudinal]] for what the numbers mean,
[[monkey_corpus]] for the corpus the worklists are built from.

# recqual

Longitudinal recording-quality assessment for chronically implanted extracellular arrays, built on [SpikeInterface](https://spikeinterface.readthedocs.io/).

Acquisition is Blackrock / Ripple Neuro (nsX + NEV). Probes are Utah arrays (16, 96 ch) and NeuroNexus linear / multi-shank — sparse geometries, not Neuropixels-class. The question the project exists to answer is which objective metrics actually track recording quality as an implant ages.

## Two data regimes

The pipeline handles both, and the distinction drives almost every design decision:

| regime | what exists | what can run |
|---|---|---|
| **continuous** (`.ns5` + `.nev`) | broadband traces | the full SpikeInterface sorter pool |
| **snippet-only** (`.nev` alone) | pre-detected 30-sample clips, one channel each | per-electrode clustering only |

Standard sorters — MountainSort5, Kilosort4, Tridesclous2, SpykingCircus2 — all begin by detecting spikes in a continuous trace. Handed snippets they have nothing to run on. At 400 µm Utah pitch a neuron appears on exactly one electrode, so per-electrode clustering is the correct method there rather than a fallback. See [`docs/notes/snippet_sorting.md`](docs/notes/snippet_sorting.md).

## Layout

```
notebooks/     scratch-first analysis scripts (nothing promoted to src/ yet)
docs/notes/    one file per concept, gotcha, or design decision
docs/session_plans/   one logbook entry per working session
docs/reports/  literature reviews
docs/archive/  exported chat history from the project's earlier accounts
figures/       committed outputs; evidence/ and deepdive/ support specific claims
matlab/        legacy post-processing scripts
data/          gitignored — raw recordings and derived parquet
```

Start with [`CLAUDE.md`](CLAUDE.md) for the project rules, then [`docs/roadmap.md`](docs/roadmap.md) for phase structure and [`docs/HANDOFF.md`](docs/HANDOFF.md) for a cold-start orientation.

## Setup

```bash
uv python install 3.11
uv sync
```

SpikeInterface is installed with **no extras**. Each one previously carried (`extractors`, `widgets`, `qualitymetrics`) transitively requires PyQt5, whose `pyqt5-qt5` wheel does not exist for `win_amd64` and makes `uv sync` fail outright on Windows. None was used: this project reads Blackrock via `neo`, and every figure is hand-written matplotlib. The submodules stay importable without their extras. Re-add any extra only behind a platform marker.

## Running

```bash
uv run python notebooks/scratch_rocky_inventory.py
uv run python notebooks/scratch_rocky_resort.py --all --n-jobs 8
uv run python notebooks/scratch_rocky_longitudinal.py
```

Two operational notes. Cap parallelism around 8 workers — a single 2017 session holds 2.4 M snippets, and 24 workers exhausted 19 GB of RAM. And set `PYTHONIOENCODING=utf-8` for scripts that print Ω or µ, or the Windows console codec will raise.

## Data

`data/` is gitignored. Raw recordings must be supplied separately; [`docs/HANDOFF.md`](docs/HANDOFF.md) carries a transfer manifest with sizes and checksums. Everything under `data/derived/` regenerates from the committed scripts.

## Status

Two cohorts analysed. Nigel (continuous, one session) established the loading, probe-attach and threshold-crossing layers. Rocky (snippet-only, 886 NEV over 2017–2023, anterior + posterior Utah-96) carries the longitudinal work: per-electrode re-sorting, a five-way method comparison, spatial mapping, impedance QC, and a curation feasibility test.

Nothing is promoted to `src/recqual/` yet; the API is still moving. See the session plans for what each session established and what it deferred.

## License

MIT.

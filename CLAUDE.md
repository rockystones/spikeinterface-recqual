# CLAUDE.md

Longitudinal extracellular recording quality assessment pipeline built on SpikeInterface. Primary acquisition: Blackrock / Ripple Neuro (nsX format). Primary probes: Utah arrays (16, 96 ch) and NeuroNexus linear / multi-shank (16, 64 ch). Sparse / low-density geometries, not Neuropixels-class.

## Versions to pin

Verify at the start of any debugging session:

```bash
python -c "import spikeinterface, probeinterface, neo; print(spikeinterface.__version__, probeinterface.__version__, neo.__version__)"
```

- Python: 3.11
- spikeinterface: pinned to a specific minor version in `pyproject.toml`. The API has moved enough across recent releases that "latest" silently breaks tutorials.
- probeinterface, neo: latest compatible with the SI pin
- mountainsort5, kilosort (4.x), bombcell: latest

If a tutorial or AI suggestion fails on a known-good install, suspect a version mismatch first.

## API conventions

- Use `SortingAnalyzer`, not `WaveformExtractor`. Any code referencing `WaveformExtractor` is outdated and must be ported.
- Use `probeinterface` for all probe geometry. Do not hardcode channel positions.
- Use `run_sorter_by_property(grouping_property="group")` for multi-shank probes.
- Never hardcode sampling rate. Always read it from the recording object.
- Curation labels are columns on the metrics DataFrame, never baked into the sorting object.

## Code style

- snake_case for variables, functions, modules. PascalCase for classes. Follows PEP 8.
- Variable names: 3 to ~30 characters typical. Idiomatic short names (`i`, `j`, `df`, `ax`, `nch`, `fs`) acceptable with a one-line comment on first use.
- Hard cap: no variable name over 50 characters. If a name wants to grow past that, the abstraction is wrong.
- Use type hints on all function signatures and on non-obvious local assignments. Hints replace "what type is this" comments.
- First-time variable definition: one-line comment with purpose, unless purpose is obvious from name + type hint.
- Section headers in scripts and notebooks: `# === Section name: what this does ===`. In notebooks, use `# %%` cell markers.
- Key operations (filtering, indexing, math choices): brief comment on the *intent* of the operation, not its mechanics.
- Loop counters and short-lived locals: single-char names OK with one-line comment on role (`i  # iterating over electrodes`).
- Do not comment obvious code. Comment intent and non-obvious decisions only.
- Public functions: NumPy-style docstring (one-line summary, `Parameters`, `Returns`). Skip for trivial helpers.
- Optimize for legibility in a variable explorer: prefer `unit_amps` over `ua`, `n_units` over `numUnits`.

## Data conventions

Blackrock / Ripple nsX semantics:

- `.ns5` = broadband, typically 30 kHz
- `.ns3` = LFP, typically 2 kHz. Use this directly for LFP; do not decimate ns5.
- `.nev` = events and externally-sorted spike data (Plexon Offline Sorter writes back to nev)
Gain-to-uV for this acquisition is 0.25.
Other supported formats: TDT data tanks, Neuropixels binary (SpikeGLX/OpenEphys), Intan RHD/RHS.

Sampling rates in use: 24414 Hz (TDT), 30000 Hz (Blackrock, Intan).

External event triggers are parsed from the Blackrock digital input stream via the appropriate `stream_id` argument to `read_blackrock`.

LFP is in scope. The pipeline must handle it alongside spikes, not as an afterthought.

## Segment handling

Minimum-segment-duration threshold (e.g., 5 s), policy of processing kept segments independently, and the convention that segment_index is an explicit argument throughout the API rather than defaulting to 0.

## Probe inventory and grouping rules

| Probe                          | Channels | `group` property             | Geometry source              |
|--------------------------------|----------|------------------------------|------------------------------|
| Utah 96ch                      | 96       | single group                 | probeinterface               |
| Utah 16ch                      | 16       | single group                 | probeinterface               |
| NeuroNexus 1-shank linear      | 16       | single group                 | probeinterface               |
| NeuroNexus 4-shank linear      | 64       | 4 groups by shank (0..3)     | probeinterface               |
| Custom arrays                  | varies   | config file mapping          | `configs/probes/<name>.json` |

**YOU MUST verify probe channel ordering against the Blackrock electrode IDs before trusting any sort.** Channel-order mismatch is silent and ruinous.

## Sorter policy

Multi-sorter consensus is the goal. Single-sorter output is never the primary result.

Default sorter pool:

- MountainSort5 (scheme 2 for production, scheme 1 for quick tests)
- Tridesclous2 (SpikeInterface-internal, based on `sortingcomponents`)
- Kilosort4 with `do_correction=False`. Drift correction is not effective at site pitch > 40 μm, which excludes all our probes except Neuropixels (Pachitariu et al., Nat Methods 2024).
- SpykingCircus2 as optional fourth for methodological diversity
- Plexon Offline Sorter output, where available, treated as a reference sorting (not ground truth)

Excluded:

- HerdingSpikes2 on linear / multi-shank probes. Designed for planar high-density arrays only (Magland et al., eLife 2020).
- Kilosort 1 / 2 / 3. KS4 replaces them with no loss for our hardware.
- MountainSort4. Superseded by MS5.

## Curation policy

Default: UnitRefine pretrained classifiers from HuggingFace. Validated on Utah arrays in the source paper (Jain et al., bioRxiv 2025).

```python
from spikeinterface.curation import unitrefine_label_units
labels = unitrefine_label_units(
    sorting_analyzer=sa,
    noise_neural_model="SpikeInterface/UnitRefine_noise_neural_classifier",
    sua_mua_model="SpikeInterface/UnitRefine_sua_mua_classifier",
)
```

Alternative: Bombcell via `bombcell_label_units`. Default thresholds are Neuropixels-tuned; retune for sparse probes before relying on output.

## Metrics layers

Three layers, each usable standalone:

1. **Threshold-crossing (no sorter).** Per-channel MAD noise floor, 4 to 5 x MAD crossings, crossing rate, waveform amplitude distribution, peak SNR. Build first.
2. **Per-sorter quality metrics.** SI's `compute_quality_metrics` (ISI violations, presence ratio, amplitude cutoff, SNR, firing rate) plus legacy MATLAB metrics (units per channel, max unit amplitude per channel).
3. **Multi-sorter consensus.** `compare_multiple_sorters` agreement matrix. **Report the agreement structure as a longitudinal metric. Do not collapse to a single consensus sorting as the primary output.**

## File layout

```
src/<pkg>/io/            extractors, probe maps, ElectrodeMetadata
src/<pkg>/preprocessing/
src/<pkg>/sorting/       sorter wrappers, per-group sorting
src/<pkg>/quality/       threshold-crossing, SI metrics
src/<pkg>/consensus/     multi-sorter comparison
src/<pkg>/lfp/
src/<pkg>/multimodal/    stubs for impedance / histology / imaging
matlab/                  parallel post-processing
notebooks/               tutorial last; scratch first
configs/probes/          custom probe geometry definitions
data/                    raw and intermediate (gitignored)
tests/
docs/
```

## MATLAB compatibility

A parallel MATLAB layer consumes Python outputs for post-processing.

**No pickle in any file a MATLAB script will read.** Approved formats for MATLAB-facing outputs: NPY, NPZ, JSON, HDF5.

- Sortings: `sorting.save(folder=..., format="numpy_folder")`
- SortingAnalyzer: zarr or binary folder format with NPY exports
- Metrics: per-session JSON sidecar plus long-format Parquet for cross-session aggregation
- MATLAB reads NPY via npy-matlab (FileExchange)

Sorters run in Python only. MATLAB consumes the exports.

## Documentation outputs

Three kinds of durable documentation live alongside the code. None of these
are optional; they are how the project stays auditable and handoff-ready.

### `docs/session_plans/`

One file per Claude Code session: `sessionNN_<short_topic>.md`.

- Write the approved plan to this file before exiting plan mode.
- At end of session, append an "Outcome" section: what was built, what
  diverged from the plan, what new uncertainty surfaced, what was deferred.
- 5 to 30 lines per file. This is a logbook entry, not a report.

### `docs/notes/`

One file per non-trivial concept, function, or design decision:
`<topic>.md`. Topics are stable across sessions (e.g., `sorting_analyzer.md`,
`segment_handling.md`, `utah_channel_mapping.md`).

Write a note when:
- An SI function is used for the first time in the project. Document what it
  does, what it returns, what alternative was considered, and why this one.
- A design decision is made that future sessions will need to honor.
- A non-obvious gotcha is discovered (these may also earn a line in
  CLAUDE.md's "Gotchas" section if they recur).

Notes are reference material, not narrative. Aim for 50 to 300 words. Update
in place when understanding changes; do not append "edit history" sections.

### `docs/coding_conventions.md`

Examples and rationale for the style rules in CLAUDE.md's "Code style"
section. Referenced from CLAUDE.md, not inlined, to keep CLAUDE.md tight.

## SI literacy practice

When introducing a SpikeInterface function not used previously in this
project, include in the response (and in `docs/notes/<function>.md`):

1. One sentence on what the function does.
2. What it returns (type and shape if relevant).
3. The alternative considered and the reason for choosing this one.

If no alternative was considered (the function is the obvious or only
choice), say so explicitly rather than fabricating one.

At the end of each session, list the SI functions used or introduced in that
session as the last lines of the session_plan outcome. This builds a
project-specific SI glossary across sessions without separate effort.

## Multimodal forward compatibility

`src/<pkg>/io/electrode_metadata.py` defines an `ElectrodeMetadata` dataclass with optional fields for impedance, histology refs, in vivo imaging refs, and stereotaxic position. **All quality metrics report against `ElectrodeMetadata`, not against anonymous channel indices.**

Impedance is the first multimodal modality to integrate. Histology and imaging spatial registration are lower priority but the schema must accept them without retrofit.

**Do not redesign `ElectrodeMetadata` without flagging.** Quiet schema changes break downstream joins.

## Workflow rules

- Plan mode for any non-trivial change. Read SI source before editing.
- Iterate on 1 to 5 minute data slices, not full longitudinal recordings.
- Cache aggressively via `recording.save()` and SortingAnalyzer zarr.
- End-to-end run on one demo session before scaling.
- One task per session. `/clear` between unrelated tasks.
- When explaining a non-trivial concept or function, write the explanation
  to `docs/notes/<topic>.md` rather than emitting it inline. The main
  session is for code, not exposition.

## Gotchas

- Plexon Offline Sorter unit-class IDs in nev: 0 = unsorted, 1..N = sorted units, 255 = noise. Loading these as a `BaseSorting` may need a small wrapper; check NEO behavior before assuming SI handles it natively.
- `return_scaled` vs `return_in_uV` parameter naming changed across SI versions.
- Kilosort4 over-splits on sparse arrays. SLAy (`spikeinterface.curation`) can clean this up if needed.
- UnitRefine pretrained models live on HuggingFace; the first call downloads the model.
- Blackrock NSP firmware can write nsX files with non-contiguous electrode IDs; do not assume channel index equals electrode ID.
- Blackrock NSP often produces a brief (sub-5-second) first segment from operator record-verification before the real recording; this is normal and should be dropped.

## Build / test commands

```bash
uv pip install -e ".[dev]"
pytest tests/ -x
ruff check src/
ruff format src/
```

## When in doubt

- Re-check the SI version pin.
- Re-check probe channel ordering against Blackrock electrode IDs.
- Read SI source rather than guess.
- Ask before generalizing a rule across probe types.

# Session 02  Validation figures

## Plan

Three visual guardrails against silent channel-order or unit-assignment errors before any QA metrics. All work in `notebooks/scratch_validation_nigel_2023-03-17.py` + `figures/validation/`. Nothing promoted to `src/`. Inputs from session 1: the loader, the probe attach, the `-01`/`-02` sortings, and the segment decision (drop `seg[0] = 2.36 s`, use `seg[1] = 180.01 s`).

- **Figure 1** — Utah-96 10×10 layout, one tile per electrode, four small text rows: `electrode_id` (CMP), SI `channel_id`, SI `channel_index`, bank/elec. Tile fill colored by bank (A/B/C). Saved as PNG + PDF.
- **Figure 2** — three-panel heatmap on the same grid: auto-sort counts, curated counts, (curated − auto) on diverging colormap. PNG only.
- **Figure 3** — multi-page PDF, one page per curated unit, 96 mini-axes laid out on the Utah grid showing the unit's mean waveform at every electrode. Assigned electrode (from Plexon `chE#U`) highlighted in red; peak-amplitude electrode highlighted in green. Cache the `SortingAnalyzer` to `data/derived/nigel_2023-03-17/sorting_analyzer_curated.zarr`. Iterate on `--first-n 10` before generating all 217 pages.

Report at end: (a) any electrodes where `channel_id` / `electrode_id` / `channel_index` disagree; (b) peak-vs-assigned mismatches with examples; (c) template-compute runtime as a longitudinal budget anchor.

## Outcome

All three figures generated. Sign-off numbers:

- **(a) Channel-mapping disagreements: 0 / 96.** Confirms session 1's contiguous identity mapping on this file.
- **(b) Peak-vs-assigned mismatches: 1 / 217.** Unit 297, assigned elec90, peak elec89 (adjacent contact, 400 µm apart). Plausible spike spread, not a structural issue.
- **(c) Template-compute runtime: 6.1 s** over `seg[1]` (180.01 s @ 30 kHz × 96 ch) on 217 units. Cached zarr is 6.8 MB. Anchor for scaling to longitudinal data: ≈ 0.034 s/unit/180-s-segment.

Gotcha discovered (recorded in [sorting_analyzer.md](../notes/sorting_analyzer.md)): `sa.compute("waveforms")` blows the Windows `SharedMemory` cap at our parameter range (217 × 500 × 96 × 90 × float32 ≈ 3.75 GB). Skipping the `waveforms` extension lets `ComputeTemplates` use `estimate_templates_with_accumulator`, which streams the recording once. Faster, OOM-immune; preferred path for templates-only work.

Two non-zero cells in Figure 2's diff panel: +1 unit on electrode 65 (curator added), −1 on electrode 26 (curator merged or removed) — diff total nets to 0, matching the session 1 counts.

## SI / PI functions introduced

- `spikeinterface.core.create_sorting_analyzer`, `load_sorting_analyzer` — see [sorting_analyzer.md](../notes/sorting_analyzer.md)
- `SortingAnalyzer.compute("random_spikes" | "templates")`, `get_extension(...).get_data(operator="average")` — see [sorting_analyzer.md](../notes/sorting_analyzer.md)
- `spikeinterface.core.select_segment_sorting`, `BaseRecording.select_segments` — see [segment_selection.md](../notes/segment_selection.md)
- `spikeinterface.core.template_tools.get_template_extremum_channel` — see [template_extremum_channel.md](../notes/template_extremum_channel.md)

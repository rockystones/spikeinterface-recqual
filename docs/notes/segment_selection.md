# Segment selection (recording and sorting)

How to pull a single segment out of a multi-segment SI object. The two sides of the pair (`BaseRecording`, `BaseSorting`) have an inconsistent API — knowing which is which prevents an `AttributeError` halfway through pipeline code.

This is the *mechanics* note. The *why* (the 5 s minimum-segment rule, the rationale for processing segments independently rather than concatenating) is in [segment_handling.md](segment_handling.md).

## Recording: method on the object

```python
rec_seg1 = rec_with_probe.select_segments([1])
```

`BaseRecording.select_segments(segment_indices)` is defined on `BaseRecordingSnippets` (the shared base for recordings and snippets). Internally it returns a `SelectSegmentRecording`. **The attached probe survives the call** — verified during session 2 plan-mode exploration; `rec_with_probe.select_segments([1]).get_channel_locations().shape == (96, 2)`.

`segment_indices` must be a list (or a single int, but pass a list for clarity).

## Sorting: free function, **no** matching method

```python
from spikeinterface.core import select_segment_sorting
sort_seg1 = select_segment_sorting(sort_curated, [1])
```

**`BaseSorting` has no `select_segments` method.** Reaching for the symmetric API is a trap; it throws `AttributeError` at run time. Use `spikeinterface.core.select_segment_sorting`, which returns a `SelectSegmentSorting` (see SI source at `spikeinterface/core/segmentutils.py:576`).

## Composition with `select_units`

Both operations preserve the unit-id set on the result. For curated sortings where we drop `unit_id ∈ {0, 255}`, the composition order is:

```python
sort_filtered = sort_curated.select_units(unit_ids=keep_uids)   # 217 sorted units
sort_seg1     = select_segment_sorting(sort_filtered, [1])      # 1 segment, 217 units
```

`select_units` first (cheap, just a unit-id subset) then `select_segment_sorting` (rewrites the internal segment list). The other order works too in 0.102.3, but this ordering matches the natural "filter, then slice" mental model.

## Why a single-segment sorting matters for templates

`SortingAnalyzer` waveform / template extraction uses the sorting's spike trains as positions to slice from the recording. If the recording is single-segment but the sorting is still multi-segment, `create_sorting_analyzer` will refuse the mismatched segment counts. Always trim both sides together.

If a unit had **all** its spikes in the dropped segment (e.g. only fired during the 2.36 s false-start), it ends up with zero spikes in the kept segment, no waveforms, and an all-NaN template. The validation script surfaces this rather than crashing — none of the Nigel 2023-03-17 curated units had this property.

## Alternative considered

`spikeinterface.core.split_sorting(parent_sorting, recording_list)`: splits a multi-segment sorting into per-segment children. Useful when you want **all** segments individually (e.g. per-segment quality metrics); overkill when you only want one. Session 2 only needed `seg[1]`, so the targeted `select_segment_sorting` is the right tool.

# Blackrock loading

How `read_blackrock` and `read_blackrock_sorting` are used in this project.

## `read_blackrock` (the recording)

`spikeinterface.extractors.read_blackrock(file_path, stream_id=None, ...)` returns a `BaseRecording` wrapping the requested signal stream from one `.nsX` file. One call = one stream.

- **`file_path`** points at the specific `.nsX` (e.g. `.ns5` for broadband, `.ns3` for LFP). Do **not** point it at the base name and let NEO auto-discover — when sibling `-01.nev` / `-02.nev` files exist (Plexon-written copies of the same NEV), auto-discovery is ambiguous.
- **`stream_id`** is a **string** (`"5"` in the Nigel 2023-03-17 file). Resolve it dynamically by scanning the NEO header for the stream whose channels report ~30 kHz (or 2 kHz for LFP). Never hardcode the ID across files. See the session-1 script for the resolver.
- The returned object is multi-segment if the source NEV has multiple `nev_segment` blocks. `get_num_segments()` and `get_num_samples(segment_index=...)` are the truth source; segments < 5 s are dropped at the IO layer per [segment_handling.md](segment_handling.md).
- **`gain_to_uV`** comes back as a per-channel array via `rec.get_property("gain_to_uV")`. Blackrock 16-bit ADC convention is **0.25 µV / count**, and the Nigel file confirms this. Always read; never hardcode.
- **`return_scaled` / `return_in_uV`** keyword naming has shifted across SI minors — that's why the SI pin in `pyproject.toml` matters.

## `read_blackrock_sorting` (Plexon-written NEV)

`spikeinterface.extractors.read_blackrock_sorting(file_path, sampling_frequency, ...)` returns a `BaseSorting` built from the `spike_channels` block of one `.nev`. One call = one NEV file.

- `sampling_frequency` must match the broadband recording (we pass `rec.get_sampling_frequency()` from the matching `.ns5`). Mismatches silently break spike-train sample alignment.
- **`unit_ids` are positional indices `0..N-1`**, not the Plexon unit numbers. Index `i` in the returned sorting corresponds to row `i` of `BlackrockRawIO.header["spike_channels"]`. We assert this length equality at load time.
- The Plexon unit number and assigned electrode live in the NEO `spike_channels[i]["name"]` field, formatted as `"chE#U"` (electrode E, Plexon unit U). The project's regex is `^ch(\d+)#(\d+)$`.
- **Plexon unit-class IDs** per CLAUDE.md gotcha: `0` = unsorted, `1..N` = sorted units, `255` = noise. Filter `unit_id ∈ {0, 255}` to get the user-facing sorted units. Both `-01.nev` (auto-sort) and `-02.nev` (curated) yielded 217 sorted units in the Nigel 2023-03-17 file.
- **Alternative considered**: hand-build a `NumpySorting` from NEO's `get_spike_timestamps` and `rescale_spike_timestamp`. CLAUDE.md flagged this as the likely fallback. It was unnecessary — `read_blackrock_sorting` works as-is — but the wrapper plan is preserved for any future NEV variant SI doesn't natively handle.

# Session 01  Load demo data

## Plan

First hands-on session against real data: the Nigel 2023-03-17 Baseline DigitalHeadstage session. Greenfield repo (only CLAUDE.md + `data/raw/` present). Three confirmations to land before any pipeline code:

1. **Environment bootstrap.** `uv python install 3.11`, minimal `pyproject.toml` pinning `spikeinterface[full]==0.102.*`, `probeinterface>=0.2.27`, `neo>=0.14.0`. `uv venv --python 3.11` + `uv sync`.
2. **`read_blackrock` on the `.ns5`** — confirm 96 ch at 30 kHz, list event channels from the paired `.nev`, pull a 1 s memmap slice to prove the IO path. Resolve `stream_id` by sampling rate, never hardcode.
3. **Utah-96 probe.** Parse the array CMP, build a `Probe`, attach to the recording with `device_channel_indices` built from electrode-id lookup. Hard-assert zero unmapped contacts (CLAUDE.md: silent channel-order mismatch is ruinous).
4. **Plexon-written `.nev` as `BaseSorting`.** Try `read_blackrock_sorting`; if it under-delivers, fall back to NEO + `NumpySorting`. Filter `unit_id ∈ {0, 255}` (unsorted, noise) per CLAUDE.md gotcha. Do this for both `-01.nev` (Plexon auto) and `-02.nev` (manually curated).

Deliverable: `notebooks/scratch_load_nigel_2023-03-17.py`, prints to stdout, no disk writes.

## Outcome

All three landed clean. `read_blackrock_sorting` works directly; no NEO+NumpySorting wrapper needed. `gain_to_uV` confirmed at 0.25 µV (Blackrock 16-bit ADC quarter-microvolt resolution). Both `-01.nev` and `-02.nev` yield **217 sorted units** after the `{0, 255}` filter.

Discoveries that fed downstream sessions:
- The recording is **two segments**: `seg[0] = 2.36 s` (Ripple "false-start" record-verification artifact), `seg[1] = 180.01 s` (the real recording). Drove the 5 s minimum-segment policy in [segment_handling.md](../notes/segment_handling.md).
- **Channel ordering is contiguous and identity-mapped** in this file: `channel_index + 1 == int(channel_id) == electrode_id_from_cmp`. Captured in [utah_channel_mapping.md](../notes/utah_channel_mapping.md). Future sessions verify this per-recording rather than assume.
- NEO encodes Plexon unit assignment in the spike-channel `name` as `chE#U` (electrode E, unit U). The wrapper for parsing this is in `scratch_load_nigel_2023-03-17.py`; promoted-to-`src/` form deferred.
- The two NEV files have non-standard `-01`/`-02` suffixes; NEO's auto-discovery is unsafe with them. Always construct one `BlackrockRawIO` per explicit base filename.

## SI / PI functions introduced

- `spikeinterface.extractors.read_blackrock` — see [blackrock_loading.md](../notes/blackrock_loading.md)
- `spikeinterface.extractors.read_blackrock_sorting` — see [blackrock_loading.md](../notes/blackrock_loading.md)
- `probeinterface.Probe`, `Probe.set_contacts`, `Probe.set_device_channel_indices` — see [utah_channel_mapping.md](../notes/utah_channel_mapping.md)
- `spikeinterface.BaseRecording.set_probe(group_mode="by_probe")` — see [utah_channel_mapping.md](../notes/utah_channel_mapping.md)
- `neo.rawio.BlackrockRawIO` — used as the truth source for streams, electrode IDs, and spike-channel names

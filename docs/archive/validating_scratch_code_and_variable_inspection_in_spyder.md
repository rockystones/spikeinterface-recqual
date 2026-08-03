# Validating scratch code and variable inspection in Spyder

*Exported 2026-08-03T03:59:17.450Z*  
*URL: https://claude.ai/chat/f05ffc93-c980-4824-ba60-61ba95d066ad*  
*Mode: active • messages: 2 of 2 in tree*

---

## 🧑 Human

*2026-05-23T21:29:39.011617Z*

> **[attachment: scratch_load_nigel_2023-03-17.py]**

```text
// extracted from scratch_load_nigel_2023-03-17.py
"""Diagnostic load of Nigel 2023-03-17 Baseline DigitalHeadstage session.

Run from repo root:

    uv run python notebooks/scratch_load_nigel_2023-03-17.py

Confirms three things before any pipeline build-out:
  1. read_blackrock parses the .ns5 + digital event stream from the .nev
  2. A Utah-96 probe built from the per-array .cmp attaches with full
     contact <-> recording-channel coverage
  3. The Plexon-sorted (-01.nev) and manually curated (-02.nev) load as
     BaseSorting with non-zero unit counts after dropping Plexon
     unit_id 0 (unsorted) and 255 (noise).

Prints to stdout only. No disk writes.
"""

from __future__ import annotations

import re
import sys
import warnings
from collections import Counter
from pathlib import Path

import numpy as np

import neo
import probeinterface as pi
import spikeinterface
from neo.rawio import BlackrockRawIO
from probeinterface import Probe
from spikeinterface.extractors import read_blackrock, read_blackrock_sorting

# NEO emits a benign warning about an "undocumented segment" in Ripple-written
# NEV files. It does not affect the parse.
warnings.filterwarnings(
    "ignore", message="Detected .* undocumented segments within nev data"
)

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "raw"
BASE = "Nigel_Anterior_2023-03-17_Baseline_DigitalHeadstage"

NS5 = DATA / f"{BASE}.ns5"
NEV_PLEXON = DATA / f"{BASE}-01.nev"
NEV_CURATED = DATA / f"{BASE}-02.nev"
CMP = DATA / "SN 1025-001496.cmp"

UTAH_PITCH_UM = 400.0
SPIKE_CHANNEL_NAME_RE = re.compile(r"^ch(?P<elec>\d+)#(?P<unit>\d+)$")


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def asdict(row) -> dict:
    return {n: row[n] for n in row.dtype.names}


# ---------------------------------------------------------------------------
# Step 0  versions
# ---------------------------------------------------------------------------
banner("Step 0  versions")
print(f"python              {sys.version.split()[0]}")
print(f"spikeinterface      {spikeinterface.__version__}")
print(f"probeinterface      {pi.__version__}")
print(f"neo                 {neo.__version__}")
print(f"repo                {REPO}")

# ---------------------------------------------------------------------------
# Step 1  enumerate streams, open .ns5 via SI, list events, slice 1 s
# ---------------------------------------------------------------------------
banner("Step 1a  NEO header on the base recording")
raw_base = BlackrockRawIO(filename=str(DATA / BASE))
raw_base.parse_header()
hdr = raw_base.header

print("signal_streams:")
for s in hdr["signal_streams"]:
    print(f"  {asdict(s)}")
print(f"signal_channels: n={len(hdr['signal_channels'])}")
print(f"  first: {asdict(hdr['signal_channels'][0])}")
print(f"  last:  {asdict(hdr['signal_channels'][-1])}")
print(f"event_channels: n={len(hdr['event_channels'])}")
for ec in hdr["event_channels"]:
    print(f"  {asdict(ec)}")
print(f"spike_channels: n={len(hdr['spike_channels'])} (base .nev = unsorted only, U=0)")

# Resolve the 30 kHz broadband stream by sampling rate (not by hard-coded id).
ns5_stream_id = None
for s in hdr["signal_streams"]:
    rows = hdr["signal_channels"][hdr["signal_channels"]["stream_id"] == s["id"]]
    if len(rows) and abs(float(rows[0]["sampling_rate"]) - 30000.0) < 1.0:
        ns5_stream_id = str(s["id"])
        break
if ns5_stream_id is None:
    sys.exit("FAIL: no 30 kHz signal stream in header")
print(f"\nResolved ns5 stream_id = {ns5_stream_id!r}")

banner("Step 1b  SI read_blackrock on the .ns5")
rec = read_blackrock(file_path=str(NS5), stream_id=ns5_stream_id)
sr = rec.get_sampling_frequency()
nch = rec.get_num_channels()
nseg = rec.get_num_segments()
print(f"channels          {nch}")
print(f"sampling_rate     {sr} Hz")
print(f"num_segments      {nseg}")
for seg in range(nseg):
    ns = rec.get_num_samples(segment_index=seg)
    print(f"  seg[{seg}]  n_samples={ns:>10d}  dur={ns / sr:8.2f} s")
print(f"channel_ids[:10]  {list(rec.channel_ids[:10])}")
print(f"channel_ids[-5:]  {list(rec.channel_ids[-5:])}")

try:
    gains = rec.get_property("gain_to_uV")
    offsets = rec.get_property("offset_to_uV")
    print(f"gain_to_uV[:5]    {gains[:5]}")
    print(f"offset_to_uV[:5]  {offsets[:5]}")
except Exception as e:
    print(f"gain/offset lookup failed: {e!r}")

assert abs(sr - 30000.0) < 1.0, f"unexpected sampling rate {sr}"
assert nch == 96, f"unexpected channel count {nch}"

banner("Step 1c  events on the .nev (digital input)")
for i, ec in enumerate(hdr["event_channels"]):
    try:
        out = raw_base.get_event_timestamps(event_channel_index=i)
        ts = out[0] if isinstance(out, tuple) else out
        n = 0 if ts is None else len(ts)
        head = [] if n == 0 else list(ts[:5])
        print(f"  ch[{i}]  name={str(ec['name'])!r:>22s}  n_events={n:>6d}  first={head}")
    except Exception as e:
        print(f"  ch[{i}]  error: {e!r}")

banner("Step 1d  1-sec trace slice from segment 0  (proves memmap path)")
trace = rec.get_traces(segment_index=0, start_frame=0, end_frame=int(sr))
print(f"shape={trace.shape}  dtype={trace.dtype}")
print(f"first channel, first 5 samples: {trace[:5, 0]}")

# ---------------------------------------------------------------------------
# Step 2  parse CMP, build Utah-96, match contacts to recording channels
# ---------------------------------------------------------------------------
banner("Step 2a  parse Blackrock .cmp")


def parse_blackrock_cmp(path: Path) -> list[dict]:
    """Parse a Blackrock CMP mapfile.

    Returns one dict per electrode with col, row, bank, elec, label, and
    the Blackrock electrode_id = (bank - 'A') * 32 + elec.
    """
    rows = []
    for ln in path.read_text().splitlines():
        s = ln.strip()
        if not s or s.startswith("//"):
            continue
        parts = s.split()
        if len(parts) < 4:
            continue
        # Skip the description line ("Cerebus mapping for array ...")
        if not (parts[0].isdigit() and parts[1].isdigit() and parts[3].isdigit()):
            continue
        col, row, bank, elec = int(parts[0]), int(parts[1]), parts[2], int(parts[3])
        label = parts[4] if len(parts) >= 5 else f"bank{bank}_elec{elec}"
        electrode_id = (ord(bank.upper()) - ord("A")) * 32 + elec
        rows.append(
            dict(col=col, row=row, bank=bank, elec=elec, label=label, electrode_id=electrode_id)
        )
    return rows


cmp_rows = parse_blackrock_cmp(CMP)
eids = sorted(r["electrode_id"] for r in cmp_rows)
print(f"parsed {len(cmp_rows)} CMP rows")
print(f"first 3 rows: {cmp_rows[:3]}")
print(f"electrode_id range: {eids[0]} .. {eids[-1]}  (n_unique={len(set(eids))})")
banks = Counter(r["bank"] for r in cmp_rows)
print(f"banks used: {dict(banks)}")

banner("Step 2b  build Probe, match contacts to recording channels by electrode_id")
positions = np.array(
    [[r["col"] * UTAH_PITCH_UM, r["row"] * UTAH_PITCH_UM] for r in cmp_rows],
    dtype=float,
)
contact_ids = [str(r["electrode_id"]) for r in cmp_rows]

probe = Probe(ndim=2, si_units="um")
probe.set_contacts(
    positions=positions,
    shapes="circle",
    shape_params={"radius": 20.0},
    contact_ids=contact_ids,
)
probe.annotate(name="Utah-96", manufacturer="blackrock", serial="SN 1025-001496")
print(f"probe.contact_count = {probe.get_contact_count()}")

rec_chan_ids = [str(c) for c in rec.channel_ids]
print(f"recording channel_ids: first={rec_chan_ids[:5]}  last={rec_chan_ids[-5:]}")

missing_in_rec = set(contact_ids) - set(rec_chan_ids)
missing_in_cmp = set(rec_chan_ids) - set(contact_ids)
print(f"contacts not found in recording: {len(missing_in_rec)}")
print(f"recording channels not in CMP:   {len(missing_in_cmp)}")

chan_index_by_eid = {eid: i for i, eid in enumerate(rec_chan_ids)}
device_channel_indices = np.array(
    [chan_index_by_eid.get(cid, -1) for cid in contact_ids], dtype=int
)
n_unmapped = int((device_channel_indices == -1).sum())
print(f"unmapped contacts: {n_unmapped}")
assert n_unmapped == 0, "Utah probe attachment incomplete -- aborting"

probe.set_device_channel_indices(device_channel_indices)
rec_with_probe = rec.set_probe(probe, group_mode="by_probe")
locs = rec_with_probe.get_channel_locations()
print(f"rec_with_probe.channel_locations shape: {locs.shape}")

# Per-channel diagnostic: for the first 10 *recording* channels (already ordered
# 1..96), look up which probe row they correspond to and print position.
# device_channel_indices[k] = recording_channel_index for probe contact k.
# Invert to get probe row per recording channel.
probe_row_by_chan = {int(idx): k for k, idx in enumerate(device_channel_indices)}
print("first 10 recording channels (channel_index, electrode_id, x_um, y_um, bank, elec):")
for ch in range(10):
    eid = rec_chan_ids[ch]
    k = probe_row_by_chan[ch]
    r = cmp_rows[k]
    x, y = locs[ch]
    print(
        f"  ch={ch:3d}  eid={eid:>3s}  x={x:7.1f}  y={y:7.1f}  "
        f"bank={r['bank']}  elec={r['elec']:>2d}  label={r['label']}"
    )

# ---------------------------------------------------------------------------
# Step 3  Plexon -01.nev and curated -02.nev as BaseSorting
# ---------------------------------------------------------------------------


def neo_spike_channel_table(nev_path: Path) -> list[dict]:
    """For each NEO spike_channel, return (electrode_id, plexon_unit_id, name).

    Order is preserved -- SI's BlackrockSortingExtractor uses the same index
    as its unit_ids (verified by alignment assert below).
    """
    raw = BlackrockRawIO(filename=str(nev_path.with_suffix("")))
    raw.parse_header()
    rows = []
    for ch in raw.header["spike_channels"]:
        name = str(ch["name"])
        m = SPIKE_CHANNEL_NAME_RE.match(name)
        if m:
            rows.append(
                dict(name=name, electrode_id=int(m["elec"]), plexon_unit_id=int(m["unit"]))
            )
        else:
            # Unknown name format -- record as None so the assert below catches it
            rows.append(dict(name=name, electrode_id=-1, plexon_unit_id=-1))
    return rows


def load_and_summarize(nev_path: Path, label: str) -> dict:
    print()
    print(f"--- {label}  ({nev_path.name}) ---")
    neo_table = neo_spike_channel_table(nev_path)
    sorting = read_blackrock_sorting(file_path=str(nev_path), sampling_frequency=sr)
    n_raw = sorting.get_num_units()
    print(f"NEO spike_channels: {len(neo_table)}   SI n_units (incl. unsorted+noise): {n_raw}")
    assert len(neo_table) == n_raw, (
        f"length mismatch between NEO spike_channels ({len(neo_table)}) "
        f"and SI sorting ({n_raw}) -- positional alignment broken"
    )

    # Filter Plexon unit_id 0 (unsorted) and 255 (noise) per CLAUDE.md.
    sorted_idx = [
        i for i, r in enumerate(neo_table) if r["plexon_unit_id"] not in (0, 255)
    ]
    sorted_unit_ids = [sorting.unit_ids[i] for i in sorted_idx]
    sorting_sorted = sorting.select_units(unit_ids=sorted_unit_ids)
    print(f"after dropping unit_id 0 + 255: n_units = {sorting_sorted.get_num_units()}")

    # Per-electrode unit count (sorted only)
    per_elec = Counter(neo_table[i]["electrode_id"] for i in sorted_idx)
    if per_elec:
        hist = Counter(per_elec.values())  # how many electrodes have N sorted units
        print(f"  units per electrode  (counts): {dict(sorted(hist.items()))}")
        print(f"  electrodes with >=1 unit: {len(per_elec)} / 96")

    # Spike-count summary across all segments
    total_spikes = []
    for u in sorting_sorted.unit_ids:
        cnt = 0
        for seg in range(sorting_sorted.get_num_segments()):
            cnt += len(sorting_sorted.get_unit_spike_train(u, segment_index=seg))
        total_spikes.append(cnt)
    if total_spikes:
        a = np.array(total_spikes)
        print(
            f"  spike_counts  min={a.min()}  median={int(np.median(a))}  "
            f"max={a.max()}  total={int(a.sum())}"
        )
    return dict(
        raw=n_raw,
        sorted=sorting_sorted.get_num_units(),
        per_elec=per_elec,
        sorting=sorting_sorted,
    )


banner("Step 3  Plexon-sorted and curated sortings")
plex = load_and_summarize(NEV_PLEXON, "plexon offline sort (-01.nev)")
cur = load_and_summarize(NEV_CURATED, "manual curation  (-02.nev)")

banner("Step 3c  curated vs plexon diff")
print(f"sorted units  plexon={plex['sorted']}  curated={cur['sorted']}  "
      f"diff={cur['sorted'] - plex['sorted']}")
elecs_plex = set(plex["per_elec"])
elecs_cur = set(cur["per_elec"])
print(f"electrodes with units  plexon={len(elecs_plex)}  curated={len(elecs_cur)}")
print(f"  only in plexon:  {sorted(elecs_plex - elecs_cur)[:20]}{'...' if len(elecs_plex-elecs_cur)>20 else ''}")
print(f"  only in curated: {sorted(elecs_cur - elecs_plex)[:20]}{'...' if len(elecs_cur-elecs_plex)>20 else ''}")

banner("DONE")
print("Eyeball the printed unit counts vs the Plexon Offline Sorter report.")

```

> **[attachment: session01_load_demo_data.md]**

```text
// extracted from session01_load_demo_data.md
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

```

> **[attachment: session02_validation_figures.md]**

```text
// extracted from session02_validation_figures.md
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

```

> **[attachment: blackrock_loading.md]**

```text
// extracted from blackrock_loading.md
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

```

> **[attachment: coding_conventions.md]**

```text
// extracted from coding_conventions.md
# Good
def compute_threshold_crossings(
    recording: si.BaseRecording,
    threshold_factor: float = 5.0,
    segment_index: int = 0,
) -> pd.DataFrame:
    """Return per-electrode crossing counts at threshold_factor x MAD.
    
    Parameters
    ----------
    recording : BaseRecording
        SpikeInterface recording with probe attached.
    threshold_factor : float
        Multiplier on MAD noise estimate. Typically 4 to 5.
    segment_index : int
        Which segment to process. Segments < 5 s are dropped upstream.

    Returns
    -------
    DataFrame with columns: electrode_id, n_crossings, rate_hz, mad_uv.
    """
    # MAD noise floor per channel, in uV (gain already applied)
    noise_mad: np.ndarray = si.get_noise_levels(recording, method="mad", return_scaled=True)
    threshold_uv = threshold_factor * noise_mad  # one threshold per channel

    # Crossings detected as negative-going excursions past threshold
    ...
	
# Bad (over-commented, types in comments not hints, verbose names)
def computeThresholdCrossingsForRecordingObject(
    inputRecordingObjectFromSpikeInterface,  # the recording object (BaseRecording)
    thresholdMultiplicationFactorForMAD,     # float, the multiplier
):
    # compute the noise floor using MAD
    # noise_floor_in_microvolts_per_channel: numpy ndarray of floats
    noise_floor_in_microvolts_per_channel = si.get_noise_levels(...)
    # multiply noise floor by threshold factor to get threshold
    threshold_value = thresholdMultiplicationFactorForMAD * noise_floor_in_microvolts_per_channel
    ...
```

> **[attachment: segment_handling.md]**

```text
// extracted from segment_handling.md
# Segment handling

## Policy

Drop any segment shorter than 5 seconds at the IO layer with a logged warning. Process kept segments independently; do not concatenate. `segment_index` is an explicit argument throughout the pipeline.

## Why this matters

Blackrock and Ripple NSP firmware commonly produce a brief (sub-5-second) first segment from operator record-verification before the real recording starts. A pause-resume during recording can also produce a short segment. These segments are artifacts, not data, but the pipeline cannot distinguish them from real epochs without a duration rule.

The cost of not having the policy is that every downstream function must handle arbitrarily short segments correctly. Most produce silently bad outputs rather than crashes:

**Spike sorting.** Sorters need hundreds of spikes per unit to estimate templates stably. At realistic firing rates (~5 Hz), a 2.36-second segment yields ~12 spikes per unit, well below the threshold for any modern sorter. MountainSort5 and Tridesclous2 run but produce unreliable templates. Kilosort4 may fail or produce nonsense. Failure modes vary across sorters and not all of them throw clean errors. Failures here can be silent: a unit "exists" in the output but its template is noise.

**Per-segment quality metrics.** Presence ratio, ISI violations, amplitude cutoff, and SNR all assume enough spikes to estimate a distribution. For very short segments these are statistically meaningless. They will still compute a number, which is the problem.

**Threshold-crossing rates.** The rate value itself is well-defined (normalized per second), but the variance is enormous. A true 0.1 Hz crossing rate over 2.36 s yields 0 or 1 actual crossings; the rate estimate is unstable. Pooling unstable estimates into longitudinal trends produces noisy time courses for no benefit.

**Aggregation and longitudinal joins.** Cross-session statistics require either per-segment aggregation weighted by duration or a "longest segment" rule. Both require carrying `segment_index` and duration through every join. The cleanest place for this decision to live is "drop segments below a duration where the question stops mattering."

## Why 5 seconds

5 seconds is a safety floor, calibrated to catch operator-verification artifacts (typically 1 to 3 s) without affecting any legitimate analysis epoch. Real baseline recordings are minutes long; real task epochs are typically tens of seconds at minimum. There is no plausible scientific use case for a 4-second segment in this project.

Downstream operations may impose stricter minimums at their own layer. Spike sorting in particular often requires segments of 60 s or more to estimate templates reliably. These per-stage minimums are separate from the IO-layer policy and are documented in their respective modules.

## Cost of the policy

One filter at the IO layer, approximately 10 lines of code, plus one log entry per dropped segment. The policy lives in `src/recqual/io/` and is applied during recording load, so every downstream consumer sees only kept segments.

## What to log

For each dropped segment, log: source file, segment index in the raw file, duration in seconds, reason ("below 5 s threshold"). Keep the log per-session so the segment-handling decisions are auditable.

## Reference

- Discovered: session 1 on `data/raw/nigel_2023-03-17.ns5` (2.36 s segment 0, 180.01 s segment 1).
- Policy decided: between session 1 and session 2.

```

> **[attachment: segment_selection.md]**

```text
// extracted from segment_selection.md
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

```

> **[attachment: sorting_analyzer.md]**

```text
// extracted from sorting_analyzer.md
# SortingAnalyzer

Replaces the deprecated `WaveformExtractor`. Pairs one `BaseRecording` with one `BaseSorting` and hangs computed quantities (random spikes, waveforms, templates, quality metrics, …) off the pair as named "extensions". The persisted form is a folder (binary or zarr) that can be reloaded with all extensions intact.

## Create / load

```python
from spikeinterface.core import create_sorting_analyzer, load_sorting_analyzer

sa = create_sorting_analyzer(
    sorting, recording,
    format="zarr",                # or "binary_folder" or "memory"
    folder="data/derived/.../sorting_analyzer_curated.zarr",
    sparse=False,                 # dense across all channels; see "Sparsity" below
    return_scaled=True,           # all extensions see uV-scaled traces
    overwrite=False,
)

sa = load_sorting_analyzer("data/derived/.../sorting_analyzer_curated.zarr")
```

`return_scaled=True` is the global gain-scaling switch — set it once at construction so different extensions don't disagree (e.g. an SNR computed against scaled traces vs an amplitude against raw counts).

## Extensions

Computed as a dependency chain. Templates depend on `random_spikes` (or on `waveforms`, which itself depends on `random_spikes`).

```python
sa.compute("random_spikes", method="uniform", max_spikes_per_unit=500, seed=0)
sa.compute("templates", operators=["average"], ms_before=1.0, ms_after=2.0)
```

- Persisted to the analyzer folder on `save=True` (default). Reload via `load_sorting_analyzer` carries them automatically.
- Check with `sa.has_extension("templates")`; access data with `sa.get_extension("templates").get_data(operator="average")` → numpy array `(n_units, n_samples, n_channels)`.

## Sparsity

`sparse=True` (default) computes a per-unit channel mask from a quick template estimate, then propagates it: waveforms and templates only store channels near each unit's peak. **For this project we want `sparse=False`** when the spatial template across every electrode is the point — Figure 3 in session 2 needs all 96 channels per unit to overlay on the Utah grid.

## The "waveforms vs accumulator" gotcha

`sa.compute("templates")` has two code paths:

1. **If the `waveforms` extension is present**, templates are averaged from the cached waveform stack. Memory cost is full: `(n_random_spikes × n_samples × n_channels × dtype)` lives in a single shared buffer.
2. **If `waveforms` is absent**, templates fall through to `spikeinterface.core.template_tools.estimate_templates_with_accumulator`, which streams the recording once and accumulates running means per unit. Memory cost is `(n_units × n_samples × n_channels)` — orders of magnitude smaller.

On Windows, path 1 fails for our parameter range. 217 units × 500 spikes × 96 channels × 90 samples × float32 ≈ **3.75 GB** in a single `multiprocessing.shared_memory.SharedMemory` allocation, which trips `OSError [WinError 1450] Insufficient system resources`. Session 2 settled on path 2: **skip `sa.compute("waveforms", ...)` when only templates are needed**. 6.1 s for 217 units on a 180 s segment; cached zarr is 6.8 MB.

Path 1 is still required if downstream needs individual waveforms (PCA, amplitude scatter, per-spike features). When that day comes, switch to `format="binary_folder"` — the waveforms extension then writes via `numpy.memmap` instead of shared memory, sidestepping the Windows cap.

## Alternative considered

`WaveformExtractor` (older SI API). Excluded: deprecated, removed in 0.102.x. CLAUDE.md hard rule: "Use `SortingAnalyzer`, not `WaveformExtractor`. Any code referencing `WaveformExtractor` is outdated and must be ported."

```

> **[attachment: template_extremum_channel.md]**

```text
// extracted from template_extremum_channel.md
# `get_template_extremum_channel`

`spikeinterface.core.template_tools.get_template_extremum_channel(templates_or_sorting_analyzer, peak_sign="neg", mode="extremum", outputs="id")`

Returns a dict `{unit_id: channel_id_or_index}` mapping each unit to the channel where its template peak is largest. The "where does this unit sit on the probe?" function.

## Inputs and parameters

- First positional argument: a `Templates` object or a `SortingAnalyzer` with the `templates` extension computed (`sa.has_extension("templates")` must be true).
- **`peak_sign`**: `"neg"` (default), `"pos"`, or `"both"`. Extracellular action potentials are dominantly negative-going at the soma, so `"neg"` is the right default for spike sorting outputs. `"both"` falls back to absolute amplitude — useful when units could be either polarity (e.g. axonal recordings) but slower and slightly noisier.
- **`mode`**:
  - `"extremum"` — peak value (min for `peak_sign="neg"`, max for `"pos"`).
  - `"at_index"` — value sampled at `nbefore` (the alignment index). Less robust to template jitter.
  - `"peak_to_peak"` — full range across the template window. Robust to small phase shifts and to units with both positive and negative components. **Session 2 uses this.**
- **`outputs`**: `"id"` returns the SI `channel_id` (string in this project — Blackrock electrode IDs are strings like `"5"`); `"index"` returns the positional channel index (`int`).

## How session 2 uses it

```python
peak_id_by_unit = get_template_extremum_channel(
    sa, peak_sign="neg", mode="peak_to_peak", outputs="id"
)
peak_eid_by_unit = {u: int(cid) for u, cid in peak_id_by_unit.items()}
```

Then compared against the **assigned** electrode from the Plexon `chE#U` name. Found 1/217 mismatches (unit 297, assigned elec90, peak elec89 — adjacent contact). The function is the spatial cross-check on the unit-to-electrode assignment baked into the NEV file.

## Returns

A `dict` keyed by `unit_id`. **Order is not guaranteed**; iterate by `sorting.unit_ids` if you need a stable order matching the sorting object.

## Alternative considered

Computing the peak channel by hand: `np.argmax(np.ptp(templates, axis=1))` per unit, indexed into `sa.channel_ids`. Equivalent for the `peak_to_peak` case but loses the `peak_sign` polarity semantics. The SI helper also handles sparsity correctly (returns the peak within the unit's sparse mask, not the global recording channel) — relevant for any future sparse-analyzer work even if session 2 ran with `sparse=False`.

```

> **[attachment: testing_policy.md]**

```text
// extracted from testing_policy.md
# Testing policy

## The failure mode this addresses

Scientific analysis pipelines do not usually fail by crashing. Crashes are caught immediately. They fail by producing plausible-looking but wrong results: a channel-mapping swap that produces a sensible template plot at the wrong location, an off-by-one in segment indexing that drops one spike per segment, a sign flip in MAD that makes everything appear saturated, a sampling-rate confusion that compresses time by 22%. These errors are silent and propagate through entire pipelines undetected.

Tests exist to catch this class of error. The test suite is not a check on correctness of `if` statements; it is a check on whether the code does what its name says it does.

## Three tiers, ordered by value

### Tier 1: synthetic-data tests for core algorithms

For each algorithm in `quality/`, `sorting/`, and `io/`, write a test that builds synthetic data with known properties and verifies the algorithm recovers them.

Concrete examples for this project:

- **Threshold-crossing detector.** Inject N spikes at known amplitudes into white noise of known std. Verify N crossings detected at the right threshold factor. Verify polarity (negative-going by extracellular convention).
- **MAD noise estimator.** Pure Gaussian noise of known std. `MAD * 1.4826` should approximate std within a tolerance of a few percent.
- **Probe geometry parsing.** Parse a synthetic `.cmp` file with handcrafted electrode/bank assignments. Verify electrode IDs compute correctly via `(bank - 'A') * 32 + elec`.
- **Channel mapping validation.** Given a recording with channel_ids `['3', '1', '2']` and a probe with electrode IDs `[1, 2, 3]`, verify the mapping function correctly identifies the permutation.
- **Segment filtering.** Given a recording with segments of `[2 s, 180 s, 60 s]` and the 5 s threshold, verify the kept indices are `[1, 2]` and the dropped index is `[0]`.

Tier 1 tests are written for every module promoted from `notebooks/scratch/` to `src/`. They pay back forever; the cost of writing them is small relative to the cost of one silent error.

### Tier 2: invariant checks

Properties that must hold regardless of input, embedded as `assert` statements in pipeline code or as light pytest tests.

Examples:

- After loading a recording with a probe attached, `recording.get_num_channels() == probe.get_contact_count()`.
- Crossings at threshold `5 x MAD` are less than or equal to crossings at threshold `4 x MAD` (monotonic).
- After segment filtering, all kept segments have duration above the policy threshold.
- Per-unit assigned electrode (from `chN#U` name in nev) matches the electrode with peak template amplitude. This last one is real scientific validation, not just a software test; it catches Plexon-to-SI channel mapping errors that no synthetic test would find, because it operates on real data and on the chain end-to-end.

Invariants are cheap and catch a lot. They run on real data, not synthetic, so they validate the chain end-to-end rather than the algorithm in isolation. Treat them as a complement to Tier 1, not a substitute.

### Tier 3: regression / snapshot tests at milestones

Once the pipeline runs end-to-end on the demo session, store key outputs (unit count, mean MAD per channel, template peak amplitudes for a handful of units) in a fixture file. A regression test loads the fixture and verifies current outputs match within tolerance.

Catches "I refactored and changed behavior I didn't intend to change." Write only at milestones, not per session. Update the fixture when an intended behavior change occurs, and note the update in the corresponding session_plan.

Milestones to target:

- After threshold-crossing module is stable on the demo session.
- After one full sorter run is stable end-to-end.
- After multi-sorter consensus produces a reproducible agreement matrix on the demo session.
- Before scaling to the longitudinal cohort.

## What not to test

- **SpikeInterface itself.** SI has its own test suite. Do not duplicate.
- **Plotting code.** Visual outputs are validated by eye, against the validation figures from session 2 onward.
- **Trivial glue code.** Tests should cover logic, not plumbing. A function that calls `recording.get_traces()` and returns the result does not need a test.

## When to write tests

- Tier 1 tests ship with the code being promoted to `src/`, not after. The PR that adds the module also adds the test.
- Tier 2 invariants are embedded throughout, both as runtime `assert` statements in pipeline code and as light tests in `tests/`.
- Tier 3 regression tests are written at the milestones above. Each new milestone adds one fixture, not many.

## File layout and execution

- Test files: `tests/test_<module>.py`. One test file per source module is the default; split if test files exceed ~300 lines.
- Synthetic data generators: `tests/fixtures/synthetic.py` for shared generators (white noise + injected events, synthetic `.cmp` files, etc.).
- Regression snapshots: `tests/snapshots/<milestone>/` as NPZ or JSON files. Treat as data; check into git if small (< 1 MB), Git-LFS or external storage if larger.
- Run all tests: `pytest tests/ -x` (stop on first failure during development).
- Run one module: `pytest tests/test_threshold_crossing.py -v`.
- Run only fast tests in CI: `pytest tests/ -m "not slow"` (use the `slow` marker from `pyproject.toml`).

## A worked example: threshold-crossing detector

```python
# tests/test_threshold_crossing.py
import numpy as np
import pytest
from recqual.quality.threshold_crossing import detect_crossings

def test_detects_known_events_above_threshold():
    """White noise plus injected events at -6x MAD. Detector must find them."""
    rng = np.random.default_rng(seed=42)  # rng: seeded generator for reproducibility
    fs = 30000                            # fs: sampling rate, Hz
    n_samples = fs * 10                   # 10 s of synthetic data

    # Pure Gaussian noise, std = 10 uV. Then inject 50 events at -60 uV.
    noise: np.ndarray = rng.normal(0, 10, n_samples).astype(np.float32)
    event_times = rng.integers(100, n_samples - 100, size=50)  # avoid edges
    signal = noise.copy()
    signal[event_times] = -60.0  # negative-going by extracellular convention

    crossings = detect_crossings(signal, fs=fs, threshold_factor=4.0)

    # All 50 events should be detected (with margin for rare double-counts at edges)
    assert 48 <= len(crossings) <= 52


def test_monotonic_in_threshold_factor():
    """Stricter threshold returns equal or fewer crossings. Invariant."""
    rng = np.random.default_rng(seed=42)
    signal = rng.normal(0, 10, 30000 * 10).astype(np.float32)

    c4 = detect_crossings(signal, fs=30000, threshold_factor=4.0)
    c5 = detect_crossings(signal, fs=30000, threshold_factor=5.0)
    c6 = detect_crossings(signal, fs=30000, threshold_factor=6.0)

    assert len(c4) >= len(c5) >= len(c6)
```

These two tests together cover (1) the algorithm recovers known ground truth and (2) an invariant that must hold. The cost is roughly 30 lines and runs in under a second. The benefit is that any future change to `detect_crossings` that breaks either property fails CI before it reaches the longitudinal cohort.

## Reference

- Policy decided: between session 2 and session 3, before threshold-crossing module is built.
- Inspiration: the test-pyramid model (unit tests cheap and many, integration tests rarer, end-to-end tests rarest). Tier 1 corresponds to unit tests of algorithms, Tier 2 to lightweight integration tests, Tier 3 to end-to-end snapshots.

```

> **[attachment: utah_channel_mapping.md]**

```text
// extracted from utah_channel_mapping.md
# Utah channel mapping

Parsing a Blackrock per-array CMP file into a `probeinterface.Probe`, and the four-ID disambiguation needed to verify channel ordering against the recording.

## CMP file format

One row per electrode, whitespace-separated:

```
col  row  bank  elec  label
```

- `col`, `row`: integer position on the 10×10 grid. Row 0 is at the bottom, col 0 is at the left.
- `bank`: `A`, `B`, or `C`. The Cerebus NSP wires 32 contacts per bank.
- `elec`: 1..32, the Blackrock electrode number **within the bank**.
- `label`: free text (often `elecN`).

The header lines and any line starting with `//` are ignored. Lines that don't have `digit digit non-digit digit` in the first 4 columns are skipped (catches the leading descriptive line in Blackrock-issued CMPs).

The 96-electrode Utah array has **4 of the 100 grid positions unused**. In the Nigel array (SN 1025-001496) those are `(0,0)`, `(0,1)`, `(1,1)`, `(3,9)` — not all four corners, which is why we read positions from the CMP rather than assuming a standard pattern.

## Blackrock electrode ID

```python
electrode_id = (ord(bank.upper()) - ord("A")) * 32 + elec   # A1..A32 -> 1..32, B1..B32 -> 33..64, C1..C32 -> 65..96
```

This is the integer that appears in the NEV `signal_channels["id"]` field and in NEO spike-channel names like `chE#U`. It is the join key between the CMP, the recording, and Plexon's unit assignment.

## Probe build

```python
positions = [[r["col"] * 400.0, r["row"] * 400.0] for r in cmp_rows]   # Utah pitch is 400 um
probe.set_contacts(positions=positions, shapes="circle",
                   shape_params={"radius": 20.0},
                   contact_ids=[str(r["electrode_id"]) for r in cmp_rows])
```

`contact_ids` are strings (PI convention). Set them from `electrode_id` so the recording's `channel_id` strings (also derived from `electrode_id`) can be joined by equality.

## Attaching to a recording: `device_channel_indices`

For each probe contact `i`, `device_channel_indices[i]` must equal the recording channel index that has the matching electrode ID. Build by dict lookup, never positionally:

```python
chan_index_by_eid = {rec.channel_ids[i]: i for i in range(rec.get_num_channels())}
device_channel_indices = [chan_index_by_eid[cid] for cid in probe.contact_ids]
probe.set_device_channel_indices(device_channel_indices)
rec_with_probe = rec.set_probe(probe, group_mode="by_probe")
```

**Assert zero unmapped contacts** before continuing. CLAUDE.md: channel-order mismatch is "silent and ruinous".

## The four-ID disambiguation

A given physical contact has four identities in this project; Figure 1 in [session 02](../session_plans/session02_validation_figures.md) prints all four per tile:

| ID                  | Source                                        | Type     | Example |
|---------------------|-----------------------------------------------|----------|---------|
| `electrode_id`      | `(bank - 'A') * 32 + elec` from the CMP       | `int`    | `5`     |
| `channel_id`        | SI `rec.channel_ids[i]` (from NEV header)     | `str`    | `"5"`   |
| `channel_index`     | positional index into `rec.channel_ids`       | `int`    | `4`     |
| `bank` / `elec`     | CMP physical labeling                          | `str`/`int` | `A` / `5` |

In the Nigel 2023-03-17 file the relationship is the simplest possible — `channel_index + 1 == int(channel_id) == electrode_id`. **Do not generalize.** CLAUDE.md gotcha: Blackrock NSP firmware can write nsX files with non-contiguous electrode IDs. The validation script asserts this identity per file, and Figure 1 makes any deviation immediately visible.

## probeinterface used

- `Probe(ndim=2, si_units="um")`, `set_contacts`, `set_device_channel_indices`, `annotate`. The catalog probe (`get_probe`) was not used: building positions directly from the CMP is simpler than reconciling catalog coordinates against per-array missing-position patterns.
- `recording.set_probe(probe, group_mode="by_probe")` returns a probe-attached recording. `group_mode="by_probe"` puts all 96 channels into a single SI group, matching the [CLAUDE.md probe table](../../CLAUDE.md) (Utah arrays are single-group).

```

Session 1 and 2 validation before planning for the next session. I am used to inspect variable values in the MATLAB variable explorer. Currently I am using the Spyder6 and can run the scratch code in activate si_env virtual environment python console, I can inspect the variables. Please walk me through the scratch code and help me validate the key functions are written properly.

---

## 🤖 Claude

*2026-05-23T21:32:39.736172Z*

 

> **[thinking]**
>
> The user wants me to validate their scratch code from two sessions before moving forward—they're working in Spyder with a variable explorer like MATLAB, so they need me to walk through the key functions and check them. I can see they have the session 1 script loaded, and there's a validation script as well that I should examine. I see the validation script is listed in the uploaded files but not yet loaded into context, so I need to read it from disk first. Before I do that though, I should check the file-reading SKILL.md to make sure I'm using the right approach — the project instructions are clear that I need to review the relevant skill documentation before using any tools. I need to look at the validation script to understand what the user is asking me to check. They want me to walk through each script and identify the key checkpoints where they should inspect variables in Spyder — specifically what to look for in the variable explorer at each step, what the expected shape and values should be, and any patterns that might fail silently. Since they mentioned all three scripts ran clean, I'm building a validation checklist rather than debugging. I should also keep their preference for substance over preamble in mind and focus on the specific, actionable inspection points. I need to read the validation script first to see what I'm working with, then structure a checkpoint-based walkthrough that matches how the user navigates variables in Spyder. Since checkpoints are genuinely discrete inspection steps, a list format works here, but I'll keep each item dense with reasoning rather than skeletal. I'll open with framing, walk through the session script section by section, and name the key variables to inspect at each step.

Reading the validation script first (it's referenced but not in context).

```json
// tool_use: view
{
  "description": "Read the validation script that's not in the project knowledge",
  "path": "/mnt/user-data/uploads/scratch_validation_nigel_2023-03-17.py"
}
```

```json
// tool_result
[
  {
    "type": "text",
    "text": "     1\t\"\"\"Validation figures for the Nigel 2023-03-17 baseline DigitalHeadstage session.\n     2\t\n     3\tBuilds three figures to visually verify (a) probe contact, (b) Blackrock\n     4\telectrode id, (c) SI channel index, and (d) the per-unit electrode assignment\n     5\tbaked into the Plexon `.nev`. CLAUDE.md flags channel-order mismatch as\n     6\t\"silent and ruinous\"; these figures are the visual guardrail.\n     7\t\n     8\tRun from repo root:\n     9\t    uv run python notebooks/scratch_validation_nigel_2023-03-17.py [--first-n N] [--rebuild-analyzer]\n    10\t\n    11\t  --first-n N         cap Figure 3 to first N pages (dev iteration)\n    12\t  --rebuild-analyzer  ignore cached zarr; recompute templates\n    13\t\"\"\"\n    14\t\n    15\tfrom __future__ import annotations\n    16\t\n    17\timport argparse\n    18\timport re\n    19\timport shutil\n    20\timport sys\n    21\timport time\n    22\timport warnings\n    23\tfrom collections import Counter\n    24\tfrom pathlib import Path\n    25\t\n    26\timport numpy as np\n    27\timport matplotlib.pyplot as plt\n    28\tfrom matplotlib.backends.backend_pdf import PdfPages\n    29\tfrom matplotlib.gridspec import GridSpec\n    30\tfrom matplotlib.patches import Rectangle\n    31\t\n    32\timport neo\n    33\timport probeinterface as pi\n    34\timport spikeinterface\n    35\tfrom neo.rawio import BlackrockRawIO\n    36\tfrom probeinterface import Probe\n    37\tfrom spikeinterface.core import (\n    38\t    create_sorting_analyzer,\n    39\t    load_sorting_analyzer,\n    40\t    select_segment_sorting,\n    41\t)\n    42\tfrom spikeinterface.core.template_tools import get_template_extremum_channel\n    43\tfrom spikeinterface.extractors import read_blackrock, read_blackrock_sorting\n    44\t\n    45\twarnings.filterwarnings(\n    46\t    \"ignore\", message=\"Detected .* undocumented segments within nev data\"\n    47\t)\n    48\t\n    49\tREPO = Path(__file__).resolve().parent.parent\n    50\tDATA = REPO / \"data\" / \"raw\"\n    51\tBASE = \"Nigel_Anterior_2023-03-17_Baseline_DigitalHeadstage\"\n    52\t\n    53\tNS5 = DATA / f\"{BASE}.ns5\"\n    54\tNEV_AUTO = DATA / f\"{BASE}-01.nev\"\n    55\tNEV_CURATED = DATA / f\"{BASE}-02.nev\"\n    56\tCMP = DATA / \"SN 1025-001496.cmp\"\n    57\t\n    58\tFIG_DIR = REPO / \"figures\" / \"validation\"\n    59\tCACHE_DIR = REPO / \"data\" / \"derived\" / \"nigel_2023-03-17\"\n    60\tANALYZER_CACHE = CACHE_DIR / \"sorting_analyzer_curated.zarr\"\n    61\t\n    62\tUTAH_PITCH_UM = 400.0\n    63\tSPIKE_CHANNEL_NAME_RE = re.compile(r\"^ch(?P<elec>\\d+)#(?P<unit>\\d+)$\")\n    64\tBANK_COLORS = {\"A\": \"#a6cee3\", \"B\": \"#fdbf6f\", \"C\": \"#b2df8a\"}  # soft blue/orange/green\n    65\tSEG_BROADBAND = 1  # session 1: seg[0]=2.36s false-start, seg[1]=180.01s\n    66\tNS5_STREAM_ID = \"5\"\n    67\t\n    68\tWAVE_MS_BEFORE = 1.0\n    69\tWAVE_MS_AFTER = 2.0\n    70\tWAVE_MAX_SPIKES = 500\n    71\t\n    72\t\n    73\tdef banner(title: str) -> None:\n    74\t    print()\n    75\t    print(\"=\" * 72)\n    76\t    print(title)\n    77\t    print(\"=\" * 72)\n    78\t\n    79\t\n    80\t# ---------------------------------------------------------------------------\n    81\t# CMP parsing + probe attach  (mirrors session 1)\n    82\t# ---------------------------------------------------------------------------\n    83\tdef parse_blackrock_cmp(path: Path) -> list[dict]:\n    84\t    rows: list[dict] = []\n    85\t    for ln in path.read_text().splitlines():\n    86\t        s = ln.strip()\n    87\t        if not s or s.startswith(\"//\"):\n    88\t            continue\n    89\t        parts = s.split()\n    90\t        if len(parts) < 4:\n    91\t            continue\n    92\t        if not (parts[0].isdigit() and parts[1].isdigit() and parts[3].isdigit()):\n    93\t            continue\n    94\t        col, row, bank, elec = int(parts[0]), int(parts[1]), parts[2], int(parts[3])\n    95\t        label = parts[4] if len(parts) >= 5 else f\"bank{bank}_elec{elec}\"\n    96\t        electrode_id = (ord(bank.upper()) - ord(\"A\")) * 32 + elec\n    97\t        rows.append(\n    98\t            dict(col=col, row=row, bank=bank, elec=elec, label=label, electrode_id=electrode_id)\n    99\t        )\n   100\t    return rows\n   101\t\n   102\t\n   103\tdef build_probe(cmp_rows: list[dict]) -> Probe:\n   104\t    positions = np.array(\n   105\t        [[r[\"col\"] * UTAH_PITCH_UM, r[\"row\"] * UTAH_PITCH_UM] for r in cmp_rows], dtype=float\n   106\t    )\n   107\t    contact_ids = [str(r[\"electrode_id\"]) for r in cmp_rows]\n   108\t    probe = Probe(ndim=2, si_units=\"um\")\n   109\t    probe.set_contacts(\n   110\t        positions=positions,\n   111\t        shapes=\"circle\",\n   112\t        shape_params={\"radius\": 20.0},\n   113\t        contact_ids=contact_ids,\n   114\t    )\n   115\t    probe.annotate(name=\"Utah-96\", manufacturer=\"blackrock\", serial=\"SN 1025-001496\")\n   116\t    return probe\n   117\t\n   118\t\n   119\tdef attach_probe(rec, probe: Probe, cmp_rows: list[dict]):\n   120\t    rec_chan_ids = [str(c) for c in rec.channel_ids]\n   121\t    chan_index_by_eid = {eid: i for i, eid in enumerate(rec_chan_ids)}\n   122\t    contact_ids = [str(r[\"electrode_id\"]) for r in cmp_rows]\n   123\t    dev = np.array([chan_index_by_eid[cid] for cid in contact_ids], dtype=int)\n   124\t    probe.set_device_channel_indices(dev)\n   125\t    return rec.set_probe(probe, group_mode=\"by_probe\")\n   126\t\n   127\t\n   128\t# ---------------------------------------------------------------------------\n   129\t# Sorting helpers  (mirrors session 1)\n   130\t# ---------------------------------------------------------------------------\n   131\tdef neo_spike_channel_table(nev_path: Path) -> list[dict]:\n   132\t    raw = BlackrockRawIO(filename=str(nev_path.with_suffix(\"\")))\n   133\t    raw.parse_header()\n   134\t    out: list[dict] = []\n   135\t    for ch in raw.header[\"spike_channels\"]:\n   136\t        name = str(ch[\"name\"])\n   137\t        m = SPIKE_CHANNEL_NAME_RE.match(name)\n   138\t        if m:\n   139\t            out.append(\n   140\t                dict(name=name, electrode_id=int(m[\"elec\"]), plexon_unit_id=int(m[\"unit\"]))\n   141\t            )\n   142\t        else:\n   143\t            out.append(dict(name=name, electrode_id=-1, plexon_unit_id=-1))\n   144\t    return out\n   145\t\n   146\t\n   147\tdef load_sorted_sorting(nev_path: Path, sr: float):\n   148\t    \"\"\"Load a Plexon-written .nev as a sorting filtered to U not in {0, 255}.\"\"\"\n   149\t    neo_table = neo_spike_channel_table(nev_path)\n   150\t    sorting = read_blackrock_sorting(file_path=str(nev_path), sampling_frequency=sr)\n   151\t    assert len(neo_table) == sorting.get_num_units(), (\n   152\t        f\"NEO vs SI length mismatch on {nev_path.name}: \"\n   153\t        f\"{len(neo_table)} vs {sorting.get_num_units()}\"\n   154\t    )\n   155\t    sorted_idx = [\n   156\t        i for i, r in enumerate(neo_table) if r[\"plexon_unit_id\"] not in (0, 255)\n   157\t    ]\n   158\t    keep_uids = [sorting.unit_ids[i] for i in sorted_idx]\n   159\t    sorted_sorting = sorting.select_units(unit_ids=keep_uids)\n   160\t    assigned_eid = {sorting.unit_ids[i]: neo_table[i][\"electrode_id\"] for i in sorted_idx}\n   161\t    return sorted_sorting, assigned_eid\n   162\t\n   163\t\n   164\t# ---------------------------------------------------------------------------\n   165\t# Figures\n   166\t# ---------------------------------------------------------------------------\n   167\tdef fig1_channel_mapping(channel_table: list[dict], cmp_rows: list[dict], out_stem: Path):\n   168\t    by_eid = {r[\"electrode_id\"]: r for r in cmp_rows}\n   169\t    fig = plt.figure(figsize=(12, 12))\n   170\t    gs = GridSpec(10, 10, figure=fig, hspace=0.08, wspace=0.08)\n   171\t    for c in channel_table:\n   172\t        cmp_row = by_eid[c[\"electrode_id_from_cmp\"]]\n   173\t        col, row = cmp_row[\"col\"], cmp_row[\"row\"]\n   174\t        ax = fig.add_subplot(gs[9 - row, col])\n   175\t        ax.set_facecolor(BANK_COLORS[cmp_row[\"bank\"]])\n   176\t        ax.set_xticks([])\n   177\t        ax.set_yticks([])\n   178\t        for sp in ax.spines.values():\n   179\t            sp.set_linewidth(0.5)\n   180\t            sp.set_color(\"0.4\")\n   181\t        ax.text(\n   182\t            0.5, 0.5,\n   183\t            f\"eid {c['electrode_id_from_cmp']}\\n\"\n   184\t            f\"cid {c['channel_id']}\\n\"\n   185\t            f\"idx {c['channel_index']}\\n\"\n   186\t            f\"{cmp_row['bank']}/{cmp_row['elec']}\",\n   187\t            ha=\"center\", va=\"center\", fontsize=8, family=\"monospace\",\n   188\t        )\n   189\t    fig.suptitle(\n   190\t        \"Utah-96 channel mapping  (Nigel 2023-03-17 baseline)\\n\"\n   191\t        \"tile fill = bank  (A blue, B orange, C green)   \"\n   192\t        \"eid=electrode id from CMP,  cid=SI channel_id,  idx=SI channel_index\",\n   193\t        fontsize=11,\n   194\t    )\n   195\t    legend_y = 0.04\n\t< truncated lines 196-390 >\n   391\t    nseg = rec.get_num_segments()\n   392\t    print(f\"channels={rec.get_num_channels()}  sr={sr} Hz  segments={nseg}\")\n   393\t    for s in range(nseg):\n   394\t        print(f\"  seg[{s}]  n_samples={rec.get_num_samples(segment_index=s):>10d}  \"\n   395\t              f\"dur={rec.get_num_samples(segment_index=s)/sr:8.2f} s\")\n   396\t\n   397\t    cmp_rows = parse_blackrock_cmp(CMP)\n   398\t    probe = build_probe(cmp_rows)\n   399\t    rec_wp = attach_probe(rec, probe, cmp_rows)\n   400\t    print(f\"CMP rows={len(cmp_rows)}  probe contacts={probe.get_contact_count()}  \"\n   401\t          f\"channel_locations={rec_wp.get_channel_locations().shape}\")\n   402\t\n   403\t    # ---- channel_table ----------------------------------------------------\n   404\t    banner(\"Build channel_table\")\n   405\t    by_eid = {r[\"electrode_id\"]: r for r in cmp_rows}\n   406\t    rec_chan_ids = [str(c) for c in rec_wp.channel_ids]\n   407\t    channel_table = []\n   408\t    locs = rec_wp.get_channel_locations()\n   409\t    for k, cid in enumerate(rec_chan_ids):\n   410\t        eid = int(cid)\n   411\t        cmp_r = by_eid[eid]\n   412\t        channel_table.append(dict(\n   413\t            channel_index=k,\n   414\t            channel_id=cid,\n   415\t            electrode_id_from_cmp=eid,\n   416\t            bank=cmp_r[\"bank\"],\n   417\t            elec_in_bank=cmp_r[\"elec\"],\n   418\t            col=cmp_r[\"col\"],\n   419\t            row=cmp_r[\"row\"],\n   420\t            x_um=float(locs[k, 0]),\n   421\t            y_um=float(locs[k, 1]),\n   422\t            label=cmp_r[\"label\"],\n   423\t        ))\n   424\t    assert len(channel_table) == 96\n   425\t\n   426\t    # ---- report (a) -------------------------------------------------------\n   427\t    banner(\"Report (a)  channel_id / electrode_id / channel_index disagreements\")\n   428\t    disagreements = []\n   429\t    for c in channel_table:\n   430\t        ok_eid = int(c[\"channel_id\"]) == c[\"electrode_id_from_cmp\"]\n   431\t        ok_idx = c[\"channel_index\"] + 1 == int(c[\"channel_id\"])\n   432\t        if not (ok_eid and ok_idx):\n   433\t            disagreements.append(c)\n   434\t    if disagreements:\n   435\t        print(f\"FOUND {len(disagreements)} mismatching rows:\")\n   436\t        for c in disagreements:\n   437\t            print(f\"  idx={c['channel_index']:3d}  cid={c['channel_id']}  \"\n   438\t                  f\"eid={c['electrode_id_from_cmp']}  bank={c['bank']}  elec={c['elec_in_bank']}\")\n   439\t    else:\n   440\t        print(\"0 -- confirms session 1 contiguous mapping (channel_index+1 == channel_id == electrode_id)\")\n   441\t\n   442\t    # ---- Figure 1 ---------------------------------------------------------\n   443\t    banner(\"Figure 1  channel mapping\")\n   444\t    fig1_channel_mapping(channel_table, cmp_rows, FIG_DIR / \"01_channel_mapping\")\n   445\t    print(f\"wrote {FIG_DIR / '01_channel_mapping.png'} and .pdf\")\n   446\t\n   447\t    # ---- sortings + per-electrode counts ---------------------------------\n   448\t    banner(\"Load sortings (auto and curated), build per-electrode counts\")\n   449\t    sort_auto, assigned_auto = load_sorted_sorting(NEV_AUTO, sr)\n   450\t    sort_cur,  assigned_cur  = load_sorted_sorting(NEV_CURATED, sr)\n   451\t    print(f\"auto sorted units: {sort_auto.get_num_units()}   \"\n   452\t          f\"curated sorted units: {sort_cur.get_num_units()}\")\n   453\t\n   454\t    auto_per_elec = Counter(assigned_auto.values())\n   455\t    cur_per_elec = Counter(assigned_cur.values())\n   456\t    print(f\"auto electrodes with >=1 unit:    {len(auto_per_elec)} / 96\")\n   457\t    print(f\"curated electrodes with >=1 unit: {len(cur_per_elec)} / 96\")\n   458\t\n   459\t    # ---- Figure 2 ---------------------------------------------------------\n   460\t    banner(\"Figure 2  units-per-electrode heatmap\")\n   461\t    fig2_units_per_electrode(\n   462\t        auto_per_elec, cur_per_elec, cmp_rows, FIG_DIR / \"02_units_per_electrode.png\"\n   463\t    )\n   464\t    print(f\"wrote {FIG_DIR / '02_units_per_electrode.png'}\")\n   465\t\n   466\t    # ---- SortingAnalyzer build / load ------------------------------------\n   467\t    banner(\"SortingAnalyzer  curated, seg 1 only\")\n   468\t    if args.rebuild_analyzer and ANALYZER_CACHE.exists():\n   469\t        print(f\"--rebuild-analyzer: removing cached {ANALYZER_CACHE}\")\n   470\t        shutil.rmtree(ANALYZER_CACHE)\n   471\t\n   472\t    rec_seg = rec_wp.select_segments([SEG_BROADBAND])\n   473\t    sort_seg = select_segment_sorting(sort_cur, [SEG_BROADBAND])\n   474\t    print(f\"rec_seg  segments={rec_seg.get_num_segments()}  \"\n   475\t          f\"n_samples={rec_seg.get_num_samples()}  dur={rec_seg.get_num_samples()/sr:.2f} s\")\n   476\t    print(f\"sort_seg segments={sort_seg.get_num_segments()}  \"\n   477\t          f\"n_units={sort_seg.get_num_units()}\")\n   478\t\n   479\t    template_runtime: float | str\n   480\t    if ANALYZER_CACHE.exists():\n   481\t        print(f\"loading cached analyzer from {ANALYZER_CACHE}\")\n   482\t        sa = load_sorting_analyzer(ANALYZER_CACHE)\n   483\t        has_tpl = sa.has_extension(\"templates\")\n   484\t        print(f\"has_extension('templates') = {has_tpl}\")\n   485\t        if not has_tpl:\n   486\t            print(\"cache exists but no templates; recomputing via accumulator\")\n   487\t            t0 = time.perf_counter()\n   488\t            if not sa.has_extension(\"random_spikes\"):\n   489\t                sa.compute(\"random_spikes\", method=\"uniform\",\n   490\t                           max_spikes_per_unit=WAVE_MAX_SPIKES, seed=0)\n   491\t            sa.compute(\n   492\t                \"templates\", operators=[\"average\"],\n   493\t                ms_before=WAVE_MS_BEFORE, ms_after=WAVE_MS_AFTER,\n   494\t            )\n   495\t            template_runtime = time.perf_counter() - t0\n   496\t        else:\n   497\t            template_runtime = \"(cached)\"\n   498\t    else:\n   499\t        print(f\"building analyzer (sparse=False, return_scaled=True) -> {ANALYZER_CACHE}\")\n   500\t        # Note: we deliberately skip the 'waveforms' extension. With 217 units x\n   501\t        # 500 spikes x 96 channels x 90 samples x float32 ~= 3.75 GB the shared\n   502\t        # memory buffer overflows on Windows. ComputeTemplates with no\n   503\t        # waveforms-cache falls back to estimate_templates_with_accumulator,\n   504\t        # which streams through the recording once.\n   505\t        t0 = time.perf_counter()\n   506\t        sa = create_sorting_analyzer(\n   507\t            sort_seg, rec_seg,\n   508\t            format=\"zarr\",\n   509\t            folder=str(ANALYZER_CACHE),\n   510\t            sparse=False,\n   511\t            return_scaled=True,\n   512\t            overwrite=False,\n   513\t        )\n   514\t        sa.compute(\"random_spikes\", method=\"uniform\",\n   515\t                   max_spikes_per_unit=WAVE_MAX_SPIKES, seed=0)\n   516\t        sa.compute(\n   517\t            \"templates\", operators=[\"average\"],\n   518\t            ms_before=WAVE_MS_BEFORE, ms_after=WAVE_MS_AFTER,\n   519\t        )\n   520\t        template_runtime = time.perf_counter() - t0\n   521\t\n   522\t    if isinstance(template_runtime, float):\n   523\t        print(f\"template-compute runtime: {template_runtime:.1f} s\")\n   524\t    else:\n   525\t        print(f\"template-compute runtime: {template_runtime}\")\n   526\t\n   527\t    # ---- peak channel per unit -------------------------------------------\n   528\t    banner(\"Peak electrode per unit  vs  assigned electrode\")\n   529\t    peak_id_by_unit = get_template_extremum_channel(\n   530\t        sa, peak_sign=\"neg\", mode=\"peak_to_peak\", outputs=\"id\"\n   531\t    )\n   532\t    # channel_id strings; convert to int for compare with assigned electrode_id\n   533\t    peak_eid_by_unit = {u: int(cid) for u, cid in peak_id_by_unit.items()}\n   534\t    mismatches = [\n   535\t        (u, assigned_cur[u], peak_eid_by_unit[u])\n   536\t        for u in sort_cur.unit_ids\n   537\t        if u in peak_eid_by_unit and peak_eid_by_unit[u] != assigned_cur[u]\n   538\t    ]\n   539\t    print(f\"mismatches: {len(mismatches)} / {sort_cur.get_num_units()}\")\n   540\t    for row in mismatches[:5]:\n   541\t        print(f\"  unit={row[0]}  assigned=elec{row[1]}  peak=elec{row[2]}\")\n   542\t\n   543\t    # ---- Figure 3 ---------------------------------------------------------\n   544\t    banner(\"Figure 3  per-unit dense templates (PDF)\")\n   545\t    channel_index_by_eid = {cid: i for i, cid in enumerate(rec_chan_ids)}\n   546\t    out_pdf = FIG_DIR / \"03_unit_templates_curated.pdf\"\n   547\t    if args.first_n is not None:\n   548\t        out_pdf = FIG_DIR / f\"03_unit_templates_curated_first{args.first_n}.pdf\"\n   549\t\n   550\t    summary = fig3_templates_pdf(\n   551\t        sa=sa,\n   552\t        sort_seg1=sort_seg,\n   553\t        assigned_eid_by_unit=assigned_cur,\n   554\t        peak_eid_by_unit=peak_eid_by_unit,\n   555\t        cmp_rows=cmp_rows,\n   556\t        channel_index_by_eid=channel_index_by_eid,\n   557\t        out_pdf=out_pdf,\n   558\t        first_n=args.first_n,\n   559\t    )\n   560\t    print(f\"wrote {out_pdf}  pages={summary['n_pages']}  \"\n   561\t          f\"zero-spike-in-seg1 units={summary['n_zero_seg1']}  \"\n   562\t          f\"all-nan templates={summary['n_nan_template']}\")\n   563\t\n   564\t    # ---- Final report (a)/(b)/(c) ----------------------------------------\n   565\t    banner(\"Final report  (a) / (b) / (c)\")\n   566\t    print(f\"(a) channel-mapping disagreements:  {len(disagreements)}\")\n   567\t    if disagreements:\n   568\t        for c in disagreements:\n   569\t            print(f\"    idx={c['channel_index']:3d}  cid={c['channel_id']}  \"\n   570\t                  f\"eid={c['electrode_id_from_cmp']}\")\n   571\t    print(f\"(b) peak-vs-assigned mismatches:    \"\n   572\t          f\"{len(mismatches)} / {sort_cur.get_num_units()}\")\n   573\t    for row in mismatches[:5]:\n   574\t        print(f\"    unit={row[0]}  assigned=elec{row[1]}  peak=elec{row[2]}\")\n   575\t    if isinstance(template_runtime, float):\n   576\t        print(f\"(c) template-compute runtime:       {template_runtime:.1f} s\")\n   577\t    else:\n   578\t        print(f\"(c) template-compute runtime:       {template_runtime}\")\n   579\t\n   580\t    return 0\n   581\t\n   582\t\n   583\tif __name__ == \"__main__\":\n   584\t    raise SystemExit(main())\n   585\t",
    "uuid": "1a8adb4c-ed82-4814-a172-a750707340b8"
  }
]
```

> **[thinking]**
>
> I need to check the middle section of the code to see what the figure 2 and figure 3 functions are doing.

Need to see the truncated section with figures 2 and 3.

```json
// tool_use: view
{
  "description": "View the truncated middle section with figures 2 and 3",
  "path": "/mnt/user-data/uploads/scratch_validation_nigel_2023-03-17.py",
  "view_range": [
    195,
    390
  ]
}
```

```json
// tool_result
[
  {
    "type": "text",
    "text": "   195\t    legend_y = 0.04\n   196\t    fig.text(0.5, legend_y, \"row 0 at bottom (CMP convention) ; col 0 at left\", ha=\"center\",\n   197\t             fontsize=9, color=\"0.3\")\n   198\t    fig.savefig(out_stem.with_suffix(\".png\"), dpi=150, bbox_inches=\"tight\")\n   199\t    fig.savefig(out_stem.with_suffix(\".pdf\"), bbox_inches=\"tight\")\n   200\t    plt.close(fig)\n   201\t\n   202\t\n   203\tdef grid_array_from_per_elec(per_elec: Counter, cmp_rows: list[dict]) -> np.ma.MaskedArray:\n   204\t    grid = np.full((10, 10), np.nan)\n   205\t    by_eid = {r[\"electrode_id\"]: r for r in cmp_rows}\n   206\t    for eid, n in per_elec.items():\n   207\t        r = by_eid[eid]\n   208\t        grid[r[\"row\"], r[\"col\"]] = n\n   209\t    # also place zeros at filled but unit-less electrodes so they are not \"missing\"\n   210\t    for r in cmp_rows:\n   211\t        if np.isnan(grid[r[\"row\"], r[\"col\"]]):\n   212\t            grid[r[\"row\"], r[\"col\"]] = 0\n   213\t    return np.ma.array(grid, mask=np.isnan(grid))\n   214\t\n   215\t\n   216\tdef fig2_units_per_electrode(\n   217\t    auto_per_elec: Counter, cur_per_elec: Counter, cmp_rows: list[dict], out: Path\n   218\t):\n   219\t    grid_auto = grid_array_from_per_elec(auto_per_elec, cmp_rows)\n   220\t    grid_cur = grid_array_from_per_elec(cur_per_elec, cmp_rows)\n   221\t    grid_diff = grid_cur - grid_auto\n   222\t\n   223\t    vmax_count = int(max(grid_auto.max(), grid_cur.max()))\n   224\t    vmax_diff = int(max(1, np.abs(grid_diff).max()))\n   225\t\n   226\t    fig, axes = plt.subplots(1, 3, figsize=(18, 6.4))\n   227\t    panels = [\n   228\t        (\"auto-sort (-01.nev)\", grid_auto, \"viridis\", 0, vmax_count),\n   229\t        (\"curated (-02.nev)\", grid_cur, \"viridis\", 0, vmax_count),\n   230\t        (f\"curated - auto  (±{vmax_diff})\", grid_diff, \"RdBu_r\", -vmax_diff, vmax_diff),\n   231\t    ]\n   232\t    for ax, (title, g, cmap_name, vmin, vmax) in zip(axes, panels):\n   233\t        cmap = plt.get_cmap(cmap_name).copy()\n   234\t        cmap.set_bad(\"lightgray\")\n   235\t        im = ax.imshow(g, origin=\"lower\", cmap=cmap, vmin=vmin, vmax=vmax)\n   236\t        ax.set_title(title)\n   237\t        ax.set_xlabel(\"col (x = col * 400 um)\")\n   238\t        ax.set_ylabel(\"row (y = row * 400 um)\")\n   239\t        ax.set_xticks(range(10))\n   240\t        ax.set_yticks(range(10))\n   241\t        for (r, c), v in np.ndenumerate(g.filled(np.nan)):\n   242\t            if np.isnan(v):\n   243\t                continue\n   244\t            txt = f\"{int(v):d}\"\n   245\t            color = \"white\" if (cmap_name == \"viridis\" and v > vmax * 0.55) else \"black\"\n   246\t            ax.text(c, r, txt, ha=\"center\", va=\"center\", fontsize=8, color=color)\n   247\t        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)\n   248\t\n   249\t    fig.suptitle(\n   250\t        f\"Units per electrode  (auto sum={int(grid_auto.sum())}, \"\n   251\t        f\"curated sum={int(grid_cur.sum())})\",\n   252\t        fontsize=12,\n   253\t    )\n   254\t    fig.tight_layout(rect=[0, 0, 1, 0.96])\n   255\t    fig.savefig(out, dpi=150, bbox_inches=\"tight\")\n   256\t    plt.close(fig)\n   257\t\n   258\t\n   259\tdef fig3_templates_pdf(\n   260\t    sa,\n   261\t    sort_seg1,\n   262\t    assigned_eid_by_unit: dict,\n   263\t    peak_eid_by_unit: dict,\n   264\t    cmp_rows: list[dict],\n   265\t    channel_index_by_eid: dict,\n   266\t    out_pdf: Path,\n   267\t    first_n: int | None,\n   268\t) -> dict:\n   269\t    \"\"\"Render multi-page PDF; one page per curated unit. Return summary dict.\"\"\"\n   270\t    templates = sa.get_extension(\"templates\").get_data(operator=\"average\")  # (U, T, C)\n   271\t    sr = sa.sampling_frequency\n   272\t    n_samples = templates.shape[1]\n   273\t    nbefore = int(round(WAVE_MS_BEFORE * sr / 1000.0))\n   274\t    t_ms = (np.arange(n_samples) - nbefore) / sr * 1000.0\n   275\t\n   276\t    unit_ids = list(sort_seg1.unit_ids)\n   277\t    if first_n is not None:\n   278\t        unit_ids = unit_ids[:first_n]\n   279\t\n   280\t    by_eid = {r[\"electrode_id\"]: r for r in cmp_rows}\n   281\t\n   282\t    out_pdf.parent.mkdir(parents=True, exist_ok=True)\n   283\t    n_zero_seg1 = 0\n   284\t    n_nan_template = 0\n   285\t\n   286\t    with PdfPages(out_pdf) as pdf:\n   287\t        for uid in unit_ids:\n   288\t            unit_index = sa.sorting.id_to_index(uid)\n   289\t            tmpl = templates[unit_index]  # (T, C)\n   290\t            assigned = int(assigned_eid_by_unit.get(uid, -1))\n   291\t            peak = peak_eid_by_unit.get(uid)\n   292\t            try:\n   293\t                peak = int(peak)\n   294\t            except (TypeError, ValueError):\n   295\t                peak = -1\n   296\t            n_spikes = len(sort_seg1.get_unit_spike_train(uid, segment_index=0))\n   297\t            if n_spikes == 0:\n   298\t                n_zero_seg1 += 1\n   299\t\n   300\t            finite = np.isfinite(tmpl)\n   301\t            if not finite.any():\n   302\t                n_nan_template += 1\n   303\t                y_abs = 1.0\n   304\t            else:\n   305\t                y_abs = max(1.0, 1.05 * float(np.nanmax(np.abs(tmpl))))\n   306\t\n   307\t            mismatch = assigned != peak\n   308\t            fig = plt.figure(figsize=(11, 11))\n   309\t            gs = GridSpec(10, 10, figure=fig, hspace=0.05, wspace=0.05)\n   310\t\n   311\t            for r in cmp_rows:\n   312\t                eid = r[\"electrode_id\"]\n   313\t                ch_idx = channel_index_by_eid[str(eid)]\n   314\t                ax = fig.add_subplot(gs[9 - r[\"row\"], r[\"col\"]])\n   315\t                wf = tmpl[:, ch_idx]\n   316\t                ax.plot(t_ms, wf, linewidth=0.7, color=\"black\")\n   317\t                ax.axhline(0, color=\"0.7\", linewidth=0.4)\n   318\t                ax.set_xlim(t_ms[0], t_ms[-1])\n   319\t                ax.set_ylim(-y_abs, y_abs)\n   320\t                ax.set_xticks([])\n   321\t                ax.set_yticks([])\n   322\t                # spine + tint highlight\n   323\t                if eid == assigned and eid == peak:\n   324\t                    ax.set_facecolor((1.0, 0.92, 0.85))\n   325\t                    for sp in ax.spines.values():\n   326\t                        sp.set_color(\"darkorange\")\n   327\t                        sp.set_linewidth(2.2)\n   328\t                elif eid == assigned:\n   329\t                    ax.set_facecolor((1.0, 0.88, 0.88))\n   330\t                    for sp in ax.spines.values():\n   331\t                        sp.set_color(\"red\")\n   332\t                        sp.set_linewidth(2.2)\n   333\t                elif eid == peak:\n   334\t                    ax.set_facecolor((0.88, 1.0, 0.88))\n   335\t                    for sp in ax.spines.values():\n   336\t                        sp.set_color(\"green\")\n   337\t                        sp.set_linewidth(2.2)\n   338\t                else:\n   339\t                    for sp in ax.spines.values():\n   340\t                        sp.set_color(\"0.7\")\n   341\t                        sp.set_linewidth(0.4)\n   342\t                ax.text(\n   343\t                    0.02, 0.98, str(eid), transform=ax.transAxes,\n   344\t                    fontsize=6, color=\"0.4\", ha=\"left\", va=\"top\",\n   345\t                )\n   346\t\n   347\t            ttl = (\n   348\t                f\"unit {uid}   assigned=elec{assigned}   peak=elec{peak}   \"\n   349\t                f\"n_spikes_seg1={n_spikes}   amp_max={y_abs/1.05:.1f} uV   \"\n   350\t                f\"{'MISMATCH' if mismatch else 'match'}\"\n   351\t            )\n   352\t            fig.suptitle(ttl, fontsize=10, family=\"monospace\")\n   353\t            fig.text(\n   354\t                0.5, 0.02,\n   355\t                \"red = assigned (Plexon)   green = peak (template extremum)   \"\n   356\t                \"orange = both   y-axis shared across 96 panels\",\n   357\t                ha=\"center\", fontsize=8, color=\"0.3\",\n   358\t            )\n   359\t            pdf.savefig(fig, dpi=110)\n   360\t            plt.close(fig)\n   361\t\n   362\t    return dict(n_pages=len(unit_ids), n_zero_seg1=n_zero_seg1, n_nan_template=n_nan_template)\n   363\t\n   364\t\n   365\t# ---------------------------------------------------------------------------\n   366\t# Main\n   367\t# ---------------------------------------------------------------------------\n   368\tdef main() -> int:\n   369\t    ap = argparse.ArgumentParser()\n   370\t    ap.add_argument(\"--first-n\", type=int, default=None,\n   371\t                    help=\"Cap Figure 3 to first N pages (dev iteration).\")\n   372\t    ap.add_argument(\"--rebuild-analyzer\", action=\"store_true\",\n   373\t                    help=\"Ignore cached SortingAnalyzer zarr; recompute.\")\n   374\t    args = ap.parse_args()\n   375\t\n   376\t    FIG_DIR.mkdir(parents=True, exist_ok=True)\n   377\t    CACHE_DIR.mkdir(parents=True, exist_ok=True)\n   378\t\n   379\t    banner(\"Step 0  versions\")\n   380\t    print(f\"python              {sys.version.split()[0]}\")\n   381\t    print(f\"spikeinterface      {spikeinterface.__version__}\")\n   382\t    print(f\"probeinterface      {pi.__version__}\")\n   383\t    print(f\"neo                 {neo.__version__}\")\n   384\t    print(f\"figures             {FIG_DIR}\")\n   385\t    print(f\"cache               {ANALYZER_CACHE}\")\n   386\t\n   387\t    # ---- setup: recording + probe -----------------------------------------\n   388\t    banner(\"Setup  load .ns5, parse CMP, attach probe\")\n   389\t    rec = read_blackrock(file_path=str(NS5), stream_id=NS5_STREAM_ID)\n   390\t    sr = rec.get_sampling_frequency()\n[585 lines total]",
    "uuid": "bafdb30a-313b-4ff1-94c6-0a0bad39f18e"
  }
]
```

> **[thinking]**
>
> I see the core problem now—the user wants to validate the script through Spyder's variable explorer, but since all the work happens inside `main()`, those local variables disappear once execution finishes. I need to figure out how to restructure the code so the important data is accessible at the module level for inspection. namespace — variables inside `if __name__ == "__main__":` blocks do persist when you run a file in Spyder, but `raise SystemExit(main())` exits before exposing `main()`'s locals like `rec`, `sa`, `templates`, and the various lookup tables. So the session 2 script as written hides everything inside the function scope. The practical fix for validating these scripts is to use Spyder's select-and-run workflow (F9) or convert `main()` into module-level code, rather than rewriting them outright. I should frame the inspection strategy around this split: session 1 is naturally var-explorer-friendly, while session 2 needs cell markers or line-by-line execution to expose its variables.
> 
> Now I'm scanning both scripts for actual code-level issues. Session 1 looks solid — it asserts `n_unmapped == 0` and the contiguous mapping assumption is validated. Session 2's `nbefore` calculation correctly uses the same `WAVE_MS_BEFORE` constant that was used during template creation, so that's consistent.
> 
> The real issue I'm flagging is the hardcoded `NS5_STREAM_ID = "5"` in session 2, which violates the established pattern of resolving stream IDs dynamically by sampling rate rather than hardcoding them. It works for this specific dataset, but it's a portability problem if this code moves into the main source tree. The segment selection via `select_segments([SEG_BROADBAND])` is also a bit indirect compared to session 1's approach, though it's functionally correct. grid_cur - grid_auto` where both are masked arrays with NaN for unused positions, so the subtraction preserves those masks correctly. The grid_array_from_per_elec function handles the distinction properly: positions outside cmp_rows stay NaN, while positions in cmp_rows without units get set to 0, which is the intended behavior.
> 
> There's a potential issue with the mismatch detection though — if a unit's peak_id lookup fails and returns -1, it'll incorrectly flag any assigned unit as a mismatch. The session_plan only shows one such case (unit 297 out of 217), so it didn't manifest in this particular file, but it's a fragility worth noting for robustness.
> 
> For the gain validation, the CLAUDE.md spec says "0.25 µV / count" but the session 1 script just prints the first few gain values without asserting anything. I should check this interactively to make sure the conversion is correct.
> 
> Let me structure a walkthrough that goes section-by-section through both sessions with concrete variable inspections at each checkpoint — the user wants to validate the key functions are working properly, so I'll focus on what to inspect in the variable explorer and what would signal a problem.
> 
> Since the session plans are already confident the code works, I'm not here to discover hidden issues. What I can do is pinpoint exactly which variables to spot-check and flag the real drifts I notice — like the hardcoded `NS5_STREAM_ID` in session 2 that contradicts the dynamic resolution from session 1. There's also a structural issue where `main()` wraps everything in session 2, which makes variable explorer inspection harder. Let me draft this with those specifics in mind.
> 
> For session 1, I'll walk through each checkpoint: versions matching the pyproject pins, the NEO header revealing stream IDs and signal channels, the SI recording object with 96 channels at 30 kHz across 2 segments, the events sanity check, trace slicing, CMP parsing and probe building, and the final sortings filtered to 217 units each. Session 2 needs a different inspection approach since everything lives inside `main()`.
> 
> For session 2, I need to either convert to a cell-marker script, use Spyder's runcell to step through chunks, or refactor briefly to expose key variables like `sa`, `templates`, `channel_table`, `mismatches`, `assigned_cur`, and `peak_eid_by_unit` at the module level. There are two real issues to flag: the hardcoded `NS5_STREAM_ID = "5"` diverges from CLAUDE.md and session 1's dynamic approach, which works here but won't scale, and the mismatch logic treating parse failures (peak == -1) as mismatches needs refinement. Didn't trigger on this file but not robust.
>    - Module structure: `main()` makes variable explorer inspection awkward in Spyder.
> 
> 5. Brief recommendation for session 3 readiness.
> 
> I'm settling on a prose-heavy structure with enumerated sections for each checkpoint rather than a bulleted list, since the user wants section-by-section validation and that's where the substance lies. No visuals needed here—this is a pure planning conversation that works better as a long-form chat response. I'll organize it as workflow setup, then walk through session 1 checkpoints, session 2 checkpoints with the main() workaround, flag the key issues, and close briefly.
> 
> For Spyder 6 specifically, I need to account for how the IDE handles execution: F5 runs the whole file in the current namespace, F9 runs selected lines, and Shift+Enter runs cells if they're marked with `# %%`. That shapes how I'll recommend validating each section—either by adding cell markers and running them individually, or by running the file once to populate the namespace and then calling `main()` from the console, or refactoring to move the main logic to module level. I'll mention the cleanest approach without asking permission, just pointing toward what works best in session 3. I'm realizing the cleanest approach is a minimal three-line modification: have `main()` return its local variables, then update the module's global namespace with those locals after execution. This preserves the script's structure while making all the computed variables accessible for inspection in the REPL, which works seamlessly with Spyder's variable explorer.
> 
> Now I'm drafting the response, keeping in mind the user's preferences for directness—jumping straight into the solution without preamble and ending on substance, plus avoiding em dashes throughout.
> 
> Actually, I need to reconsider how `main()` behaves in Spyder. When you run a script with F5, Spyder's `runfile()` executes it in the current IPython namespace and does set `__name__ == "__main__"`, so the `if __name__ == "__main__":` block fires. The `raise SystemExit(main())` will halt execution, and while Spyder catches the SystemExit exception, the function's local variables get garbage-collected when `main()` returns, so the user only sees module-level variables like `args.first_n` in the variable explorer.
> 
> Since `args` is defined inside `main()`, it won't be accessible for inspection afterward. My recommendation is to either temporarily refactor `main()` for debugging, use cell markers to break up the code, or run selected portions of `main()`'s body directly via F9 after removing the indentation. I'll write up a clean, focused response explaining these options.

Two scripts, two inspection workflows. The session 1 script (`scratch_load_nigel_2023-03-17.py`) is module-level top to bottom, so after F5 every variable persists in the IPython namespace and the Variable Explorer shows everything. The session 2 script (`scratch_validation_nigel_2023-03-17.py`) puts everything inside `main()`, so its locals vaporize when `raise SystemExit(main())` fires. We need a workaround there before inspection is useful.

## Workflow setup

For session 1: open in Spyder, F5. Done. Everything is in the namespace.

For session 2, the smallest non-intrusive change: edit the last two lines.

```python
# at end of main():
    return locals()

# at the bottom:
if __name__ == "__main__":
    _ns = main()
    globals().update(_ns)
```

After F5, every local from `main()` shows in the Variable Explorer (`rec`, `sa`, `templates`, `channel_table`, `assigned_cur`, `peak_eid_by_unit`, `mismatches`, etc.). Revert when you're done. The alternative is `# %%` cell markers, but that requires unwrapping `main()` and changes more lines.

Also use `--first-n 5` the first pass so Figure 3 builds in seconds, not minutes.

## Session 1: load script checkpoints

**Step 0, versions.** After F5, check `spikeinterface.__version__`, `probeinterface.__version__`, `neo.__version__`. They must match `pyproject.toml`: SI is pinned `~=0.102.3`, PI `>=0.2.21`, NEO `>=0.13.0`. A version drift here is the most common silent-failure cause for everything that follows.

**Step 1a, NEO header.** Inspect `hdr` (a dict). The interesting key is `hdr["signal_streams"]`: should show one row at 30 kHz. `hdr["signal_channels"]` should be length 96. `hdr["spike_channels"]` on the base `.nev` is 96 (one row per electrode with U=0, unsorted). `ns5_stream_id` should resolve to `"5"`. The resolution-by-sampling-rate logic is correct and is what session 2 should also be doing (see issues below).

**Step 1b, recording.** Inspect `rec`. The Variable Explorer shows the `BlackrockRecordingExtractor` repr; double-click to expand. Verify:
- `nch == 96`
- `sr == 30000.0`
- `nseg == 2`
- `rec.get_num_samples(0) / sr` ≈ `2.36`, `rec.get_num_samples(1) / sr` ≈ `180.01`
- `gains[:5]` should be `[0.25, 0.25, 0.25, 0.25, 0.25]`. **This is worth asserting.** The script prints but doesn't check, and 0.25 µV/count is the CLAUDE.md-stated convention. A different gain here means either a non-standard nsX config or a SI version returning gains in different units.

**Step 1d, traces slice.** `trace` should be `(30000, 96) float32`. If `trace.dtype` is `int16`, then `return_scaled` defaulting changed between SI versions and you're looking at raw counts not microvolts. Spot-check a value: `trace[:, 0].std()` should be in the tens of microvolts (typical background noise level for cortex), not the thousands (raw int16 counts).

**Step 2a, CMP parsing.** Inspect `cmp_rows` (96-element list of dicts). Spot-check a few: every `electrode_id` in 1..96, every `(col, row)` in 0..9, every `bank` in {A, B, C}. `set(r["electrode_id"] for r in cmp_rows)` should equal `set(range(1, 97))`. Inspect `banks` (Counter): should be 32 A, 32 B, 32 C.

**Step 2b, probe attach.** Inspect `device_channel_indices`: length 96, every entry in 0..95, `sorted(device_channel_indices) == list(range(96))` (a permutation). Then `n_unmapped == 0` is asserted in the script, but you can re-check by hand: `sum(device_channel_indices == -1)`. Inspect `probe_row_by_chan` (dict, 96 entries). Inspect `locs` (shape `(96, 2)`, float). Cross-check one row against the printed table: for `ch=0`, `eid='1'`, the row should be `bank=A, elec=1`, and `(x, y)` should match `col * 400, row * 400`.

**Step 3, sortings.** Inspect `plex["sorting"]` and `cur["sorting"]`. Both should have `get_num_units() == 217`. Inspect `plex["per_elec"]` and `cur["per_elec"]` (Counters of electrode_id → unit count): both should have 96 keys or fewer, all keys in 1..96. The diff print shows `elecs_plex - elecs_cur` and the reverse. The session 2 outcome says the only Figure 2 movement is electrode 65 (+1, curator added) and electrode 26 (−1). You can cross-check by inspecting `(set(plex['per_elec']) ^ set(cur['per_elec']))` plus any electrode where counts differ.

## Session 2: validation script checkpoints

After applying the `return locals()` trick:

**`channel_table`** (list of 96 dicts). The script's "Report (a)" already asserts the contiguous mapping. Spot-check by hand: `all(c['channel_index'] + 1 == int(c['channel_id']) == c['electrode_id_from_cmp'] for c in channel_table)` should be `True`. Inspect a few rows in the Variable Explorer to confirm the four-ID disambiguation matches what Figure 1 shows.

**`rec_seg` and `sort_seg`.** `rec_seg.get_num_segments() == 1`, `rec_seg.get_num_samples() / sr` ≈ `180.01`. `sort_seg.get_num_segments() == 1`, `sort_seg.get_num_units() == 217`. If `sort_seg.get_num_units()` is less than 217 here but was 217 in session 1, some units had all their spikes in `seg[0]` (the 2.36 s false-start) and were dropped by the segment slice. The note `segment_selection.md` flags this exact possibility.

**`sa` (SortingAnalyzer).** `sa.has_extension("random_spikes")` and `sa.has_extension("templates")` both True. `sa.has_extension("waveforms")` should be False (deliberate, per the OOM workaround). Inspect `templates = sa.get_extension("templates").get_data(operator="average")`: shape should be `(217, 90, 96)` for `ms_before=1, ms_after=2, sr=30000` (samples = `(1+2) * 30 = 90`).

**`peak_eid_by_unit`.** 217 entries. Every value should be in 1..96 (it's an electrode_id, not a channel_index). Compare against `assigned_cur` for the same keys: `mismatches` should be a 1-element list of `(297, 90, 89)`. If `len(mismatches) > 1`, walk the cases and check whether `peak_eid_by_unit[u]` ever ended up as `-1` (the parse-failure fallback in the script would mark this as a mismatch even if the peak was just unparseable; see issues below).

**`template_runtime`.** Float around `6.1`. If it's much larger, the accumulator path didn't kick in and shared-memory paging is happening. Confirm by checking `sa.has_extension("waveforms")` is still False.

**`summary` from Figure 3.** `n_pages == 217` (or `first_n`), `n_zero_seg1` and `n_nan_template` ideally both 0. A nonzero `n_zero_seg1` would mean some units fired exclusively in `seg[0]`. A nonzero `n_nan_template` would mean templates failed to estimate for some units (rare; would point at a deeper issue with `random_spikes` for low-spike-count units).

## Issues to flag

**Hardcoded `NS5_STREAM_ID = "5"`** at the top of the session 2 script. CLAUDE.md and the session 1 script both resolve stream id by scanning the NEO header for the 30 kHz signal stream. The hardcoded form works for this one file because the file happens to be on stream `"5"`, but it will silently load the wrong stream (or fail) on any file with a different stream layout. This is a real drift from convention that should not survive the move into `src/`. Worth replacing with the session 1 resolver before session 3 turns this code into modules.

**`mismatch = assigned != peak` in `fig3_templates_pdf`** treats a parse failure (where `peak` defaulted to `-1`) as a mismatch. If `get_template_extremum_channel` ever returns something unparseable for a unit, that unit gets flagged as MISMATCH on its Figure 3 page incorrectly. The Nigel file didn't trigger this (0 parse failures, 1 real mismatch), but the logic is brittle. Cleaner: track `peak_parsed: bool` separately and report parse failures as a third state.

**`main()` encapsulation** makes inspection in Spyder harder than it needs to be for a scratch/validation script. For scratch code where the entire point is variable-explorer-driven inspection, top-level execution (session 1 style) or explicit `# %%` cells beats `main()`. Worth deciding the convention for scratch scripts before session 3, since several more will be written. Promoted modules in `src/` should of course use functions; the rule splits cleanly by directory.

## State going into session 3

The two scripts together establish: probe attach correct (0/96 mismatches), unit assignment correct (1/217 mismatch, adjacent contact, plausible), segment policy correct (drop `seg[0]`, work in `seg[1]`), template extraction efficient (6.1 s, 6.8 MB cache, accumulator path). That's the foundation for the threshold-crossing module, `ElectrodeMetadata` dataclass, and first synthetic test that session 3 builds. Validation work pre-session-3 is done once you have walked the checkpoints above and the stream-id hardcoding is on the session 3 to-do list.

---


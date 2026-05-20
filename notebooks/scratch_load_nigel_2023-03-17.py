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

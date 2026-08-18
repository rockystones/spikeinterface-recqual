"""TDT tank IO for the Oops and Picasso corpus, mirroring the NEV contract.

The Blackrock side of this project reads snippets through
`scratch_rocky_resort.open_nev` / `read_electrode`. Everything downstream --
noise floors, gates, per-unit metrics, longitudinal trends -- is written
against that shape. This module presents a TDT tank the same way so the
analysis code is shared rather than forked.

Four differences from NEV are load-bearing and are handled here, not by the
caller:

1. **NEO wants a block, not a folder.** These tanks store one block per session
   directory with a `<tank>_<block>` file stem, so `TdtRawIO` has to be opened
   in single-block mode by passing the `.tev` *file*. Passing the directory
   raises `IndexError: list index out of range` from an empty segment list.
2. **`wf_left_sweep` is wrong.** NEO reports `NumPoints // 2` = 20 for a
   40-sample snippet. The trough actually sits at sample 8 (measured: 13,405 of
   18,700 snippets in the first Oops session, 4,838 more at 9). Trusting NEO
   would take the "baseline" from samples 0-17, i.e. from across the whole
   spike, and inflate every noise estimate.
3. **The sortcode is an accept flag, not a unit id.** Only codes 0 and 1 occur
   online, and 98% of events carry code 1. TDT's online discriminator says
   "this crossing looks like a spike", it does not say which neuron. Unit
   counts are therefore not available from the online sort -- see
   `docs/notes/tdt_corpus.md`.
4. **Waveforms are float32 volts**, not int16 needing a gain. Scaling is a
   fixed 1e6, and ~0.2% of snippets are NaN-filled and must be dropped.

Offline sorts, where they exist, live in `<block>/sort/<name>/*.SortResult` and
NEO applies them by overwriting the tsq sortcode column. That makes an offline
sort an exact relabelling of the same event list, which is the same fixed-event
regime the NEV variants gave us.

Run from repo root for a self-check on one tank:

    uv run python notebooks/scratch_tdt_io.py

See:
- docs/notes/tdt_corpus.md
"""

from __future__ import annotations

import datetime as dt
import re
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
from neo.rawio import TdtRawIO
from neo.rawio.tdtrawio import read_tbk, tsq_dtype

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import LUIGI, MONKEY_ROOT, OOPS, PICASSO  # noqa: E402

# Where each subject's tanks live. Luigi holds three trees under one root and
# `find_blocks` walks them all; its block directories are named `Block-N` with
# no date, so the tank clock is the only date they have.
TDT_ROOTS = {"Oops": OOPS, "Picasso": PICASSO, "Luigi": LUIGI}


def subject_of(path: Path) -> str | None:
    """Which subject's tree a block belongs to, by root containment."""
    p = Path(path).resolve()
    for name, root in TDT_ROOTS.items():
        try:
            p.relative_to(root.resolve())
        except ValueError:
            continue
        return name
    return None

# Snippet trough position, measured rather than taken from NEO -- see the
# module docstring. Samples 0..NBEFORE-3 are baseline by construction.
NBEFORE = 8
# Snippet waveforms arrive as float32 volts.
V_TO_UV = 1e6
# Store name prefixes. The trailing digit is the array: eNe1/Raw1/pNe1 are all
# array 1. This is a TDT rig convention, not something the tank declares.
SNIPPET_PREFIX = "eNe"
BROADBAND_PREFIX = "Raw"
LFP_PREFIX = "pNe"

# The project's segment policy, restated for TDT. A block shorter than this is
# an aborted record, not a recording.
MIN_DURATION_S = 5.0


def _s(x) -> str:
    """TDT store names come back as numpy bytes; normalise to str."""
    return x.decode() if isinstance(x, (bytes, np.bytes_)) else str(x)


def array_of(store: str) -> int | None:
    """Array number carried by a store name, e.g. ``eNe2`` -> 2."""
    m = re.search(r"(\d+)$", store)
    return int(m.group(1)) if m else None


# %%
# === Discovery ===
def find_blocks(root: Path) -> list[Path]:
    """Every TDT block under ``root``, returned as the path to its `.tev`.

    A block is a directory holding the four mandatory files. The `.tev` is
    returned rather than the directory because that is what `TdtRawIO` needs
    in single-block mode.
    """
    out: list[Path] = []
    for tev in sorted(root.rglob("*.tev")):
        d = tev.parent
        exts = {p.suffix.lower() for p in d.iterdir() if p.is_file()}
        if {".tbk", ".tdx", ".tev", ".tsq"} <= exts:
            out.append(tev)
    return out


def sort_names(block: Path) -> list[str]:
    """Offline sort names available for a block: `<block>/sort/<name>/`."""
    sd = block / "sort"
    if not sd.is_dir():
        return []
    return sorted(
        p.name for p in sd.iterdir()
        if p.is_dir() and any(p.glob("*.SortResult"))
    )


def tank_clock(tsq_path: Path) -> tuple[dt.datetime | None, float]:
    """Block start time and duration straight from the tsq header rows.

    The second row carries the start mark and the last row the stop mark, both
    as Unix epoch seconds. This is the tank's own clock and it is what settles
    the folder-versus-filename date disagreement in the Picasso tree: folder
    `Picasso_2016_01_14-1` holds files stamped `Picasso_2015_01_14`, and the
    clock says 2016-01-14. The folder is right.
    """
    head = np.fromfile(tsq_path, dtype=tsq_dtype, count=2)
    if len(head) < 2:
        return None, float("nan")
    tail = np.fromfile(tsq_path, dtype=tsq_dtype)[-1]
    t0 = float(head[1]["timestamp"])
    t1 = float(tail["timestamp"])
    if not np.isfinite(t0) or t0 <= 0:
        return None, float("nan")
    start = dt.datetime.utcfromtimestamp(t0)
    dur = t1 - t0 if np.isfinite(t1) and t1 > t0 else float("nan")
    return start, dur


def store_table(tbk_path: Path) -> dict[str, dict]:
    """Store declarations from the Tbk, keyed by store name."""
    from neo.rawio.tdtrawio import data_formats_map

    info = read_tbk(tbk_path)
    out: dict[str, dict] = {}
    for row in info:
        name = _s(row["StoreName"])
        fmt = int(row["DataFormat"])
        out[name] = dict(
            n_chan=int(row["NumChan"]),
            fs=float(row["SampleFreq"]),
            n_points=int(row["NumPoints"]),
            ev_type=int(row["TankEvType"]),
            # Carried so callers can tell microvolts from ADC counts without
            # opening the tank -- see `read_stream` and `stream_units`.
            dtype=str(np.dtype(data_formats_map[fmt]))
            if fmt in data_formats_map else None,
        )
    return out


# %%
# === Opening ===
def open_tank(tev: Path, sortname: str = "") -> tuple[TdtRawIO, dict]:
    """Open one block and return ``(io, meta)``.

    Parameters
    ----------
    tev : Path
        Path to the block's `.tev` file.
    sortname : str
        Offline sort to apply, i.e. a directory name under `<block>/sort/`.
        Empty string keeps the online sortcode.

    Returns
    -------
    tuple
        ``(io, meta)``. ``meta`` holds ``sr``, ``nbefore``, ``duration_s``,
        ``start``, ``stores``, ``arrays``, ``streams``, ``sortname``.
    """
    io = TdtRawIO(dirname=str(tev), sortname=sortname)
    io.parse_header()
    stores = store_table(tev.with_suffix(".Tbk"))
    start, dur = tank_clock(tev.with_suffix(".tsq"))

    snip = {k: v for k, v in stores.items() if k.startswith(SNIPPET_PREFIX)}
    # Rates are per store, not per tank. Luigi's 2013 blocks run eNe1-3 at
    # 48828 Hz beside a Raw1 at 24414 and a Raw2 at 48828, so a single tank
    # sampling rate is a fiction -- and CLAUDE.md forbids assuming one.
    sr_by_store = {k: float(v["fs"]) for k, v in stores.items()}
    sr = float(next(iter(snip.values()))["fs"]) if snip else float("nan")
    streams = {_s(n): str(sid) for n, sid, _ in io.header["signal_streams"]}
    arrays = sorted({a for s in snip if (a := array_of(s)) is not None})
    return io, dict(
        tev=tev,
        block=tev.parent.name,
        stem=tev.stem,
        subject=subject_of(tev),
        sr=sr,
        sr_by_store=sr_by_store,
        nbefore=NBEFORE,
        duration_s=dur,
        start=start,
        stores=stores,
        snippet_stores=sorted(snip),
        arrays=arrays,
        streams=streams,
        sortname=sortname,
    )


def channel_index(io: TdtRawIO) -> dict[tuple[str, int], list[tuple[int, int]]]:
    """Map ``(store, channel)`` to the ``(unit_index, sortcode)`` pairs on it.

    NEO explodes a snippet store into one "spike channel" per distinct
    sortcode, so reading a physical electrode means pooling several of them --
    the same shape as pooling Plexon units on a NEV electrode.
    """
    out: dict[tuple[str, int], list[tuple[int, int]]] = defaultdict(list)
    for ui, (store, chan, code) in io.internal_unit_ids.items():
        out[(_s(store), int(chan))].append((int(ui), int(code)))
    return dict(out)


def read_channel(io: TdtRawIO, meta: dict,
                 units: list[tuple[int, int]]) -> dict | None:
    """Read every snippet on one electrode, pooling across its sortcodes.

    Returns
    -------
    dict or None
        ``wf`` (n, n_samples) float32 uV, ``t`` (n,) seconds, ``code`` (n,)
        int16 sortcode. None when the electrode carries no usable event.
    """
    wfs, ts, cs = [], [], []
    for ui, code in units:
        w = io.get_spike_raw_waveforms(0, 0, ui)
        if w is None:
            continue
        w = np.asarray(w)
        if w.shape[0] == 0:
            continue
        w = w.reshape(w.shape[0], -1).astype(np.float32) * V_TO_UV
        t = io.get_spike_timestamps(0, 0, ui)
        t = np.asarray(io.rescale_spike_timestamp(t, dtype="float64"))
        n = min(w.shape[0], t.shape[0])
        if n == 0:
            continue
        w, t = w[:n], t[:n]
        # ~0.2% of TDT snippets come back NaN-filled; they poison every
        # percentile downstream, so drop them here rather than everywhere.
        keep = ~np.isnan(w).any(axis=1)
        if not keep.any():
            continue
        wfs.append(w[keep])
        ts.append(t[keep])
        cs.append(np.full(int(keep.sum()), code, dtype=np.int16))
    if not wfs:
        return None
    order = np.argsort(np.concatenate(ts))
    return dict(
        wf=np.concatenate(wfs)[order],
        t=np.concatenate(ts)[order],
        code=np.concatenate(cs)[order],
    )


def detect_nbefore(io: TdtRawIO, meta: dict, store: str,
                   idx: dict | None = None, n_channels: int = 8) -> int:
    """Where the trough actually sits, measured on a few channels.

    `NBEFORE = 8` holds for Oops, Picasso and Luigi's 2015-16 blocks, but
    Luigi's 2013 tanks sample `eNe*` at 48828 Hz instead of 24414 and their
    trough sits at **9** -- uniformly, on every channel of all 19 blocks
    measured. A constant is therefore a per-vintage assumption dressed up as a
    format fact, so it is measured instead and `NBEFORE` is only the fallback.

    Sampling a handful of channels is enough: the modal trough index is a
    property of the acquisition system's trigger delay, not of the tissue, and
    it was identical across every channel in each block tested.
    """
    idx = idx if idx is not None else channel_index(io)
    keys = [k for k in sorted(idx) if k[0] == store][:n_channels]
    modes: list[int] = []
    for key in keys:
        e = read_channel(io, meta, idx[key])
        if e is None or not len(e["t"]):
            continue
        modes.append(int(np.bincount(np.argmin(e["wf"], axis=1),
                                     minlength=e["wf"].shape[1]).argmax()))
    if not modes:
        return NBEFORE
    return int(np.bincount(modes).argmax())


def read_stream(io: TdtRawIO, meta: dict, stream: str,
                t0: float = 0.0, t1: float | None = None) -> np.ndarray | None:
    """A slice of a continuous stream as (n_samples, n_channels) float32 uV.

    ``Raw*`` is broadband; ``pNe*`` is LFP. A tank may hold either inline in
    the tev or, for the later rigs, in per-channel `.sev` files -- and a tank
    with neither still declares the store in its Tbk, so absence has to be
    caught here rather than assumed from the header.

    **Scaling is per stream, not per corpus, and NEO will not do it for you.**
    `tdtrawio` hardcodes `units = "uV"` and `gain = 1.0` on every stream
    channel. That is correct for Oops and Picasso, whose `Raw*` is float32
    already in microvolts. It is *not* correct for Luigi's 2013 `Raw2`, which
    holds int16 ADC counts -- a blanket 1e6 there produces a 3.3e10 "microvolt"
    trace, i.e. 32767 x 1e6, which is the giveaway.

    So this returns NEO's gain and offset applied honestly, and
    `stream_units()` says what the result actually is. For an integer store the
    values are **ADC counts, not microvolts**: the counts-per-microvolt factor
    comes from the PZ amplifier setting and is not in the tank. Anything
    scale-invariant (sorting, SNR, correlation) is still valid on counts;
    anything reported in microvolts is not.
    """
    names = list(meta["streams"])
    if stream not in names:
        return None
    si = names.index(stream)
    try:
        n = io.get_signal_size(0, 0, si)
    except Exception:  # noqa: BLE001 - missing sev shows up as a shape error
        return None
    if not n:
        return None
    fs = io.get_signal_sampling_rate(si)
    i0 = int(max(0.0, t0) * fs)
    i1 = n if t1 is None else min(n, int(t1 * fs))
    if i1 <= i0:
        return None
    sig = io.get_analogsignal_chunk(
        block_index=0, seg_index=0, i_start=i0, i_stop=i1, stream_index=si
    )
    sid = meta["streams"][stream]
    chans = io.header["signal_channels"]
    sel = chans[chans["stream_id"] == sid]
    gain = np.asarray(sel["gain"], dtype=np.float32)
    offset = np.asarray(sel["offset"], dtype=np.float32)
    scaled = np.asarray(sig, dtype=np.float32) * gain + offset
    unit = str(sel["units"][0]) if len(sel) else "uV"
    return scaled * V_TO_UV if unit.strip().upper() in ("V", "VOLT") else scaled


def stream_units(meta: dict, stream: str) -> str:
    """What :func:`read_stream` actually returns for this store.

    ``"uV"`` when the store holds floating point, ``"adc_counts"`` when it
    holds integers -- see the scaling note in `read_stream`. Callers that
    report microvolts must check this; callers doing scale-invariant work
    (sorting, SNR) need not.
    """
    fmt = meta["stores"].get(stream, {}).get("dtype")
    return "uV" if fmt is None or np.issubdtype(np.dtype(fmt), np.floating) \
        else "adc_counts"


def has_broadband(block: Path) -> bool:
    """Does this block carry the per-channel `.sev` files for `Raw*`?"""
    return any(block.glob("*_Raw*_ch*.sev"))


# %%
# === Self-check ===
def main() -> int:
    blocks = [b for r in TDT_ROOTS.values() for b in find_blocks(r)]
    print(f"blocks found: {len(blocks)}")
    for name, root in TDT_ROOTS.items():
        print(f"  {name:8s} {len(find_blocks(root)):4d}")
    tev = blocks[0]
    io, meta = open_tank(tev)
    print(f"\n{meta['block']}")
    print(f"  start      {meta['start']}   dur {meta['duration_s']:.1f}s")
    print(f"  sr         {meta['sr']:.4f} Hz   nbefore {meta['nbefore']}")
    print(f"  arrays     {meta['arrays']}   snippets {meta['snippet_stores']}")
    print(f"  streams    {meta['streams']}")
    print(f"  sev        {has_broadband(tev.parent)}")
    print(f"  sorts      {sort_names(tev.parent) or '-'}")

    idx = channel_index(io)
    print(f"  electrodes {len(idx)}")
    key = sorted(idx)[0]
    e = read_channel(io, meta, idx[key])
    trough = int(np.bincount(np.argmin(e["wf"], axis=1)).argmax())
    print(f"  {key}: {len(e['t'])} events, trough at sample {trough}, "
          f"|trough| median {np.median(np.abs(e['wf'].min(axis=1))):.1f} uV")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

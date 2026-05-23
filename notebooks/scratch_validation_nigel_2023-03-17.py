"""Validation figures for the Nigel 2023-03-17 baseline DigitalHeadstage session.

Builds three figures to visually verify (a) probe contact, (b) Blackrock
electrode id, (c) SI channel index, and (d) the per-unit electrode assignment
baked into the Plexon `.nev`. CLAUDE.md flags channel-order mismatch as
"silent and ruinous"; these figures are the visual guardrail.

Run from repo root:

    uv run python notebooks/scratch_validation_nigel_2023-03-17.py [--first-n N] [--rebuild-analyzer]

  --first-n N         cap Figure 3 to first N pages (dev iteration)
  --rebuild-analyzer  ignore cached zarr; recompute templates

See:
- docs/session_plans/session02_validation_figures.md
- docs/notes/sorting_analyzer.md
- docs/notes/segment_selection.md
- docs/notes/template_extremum_channel.md
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import time
import warnings
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import neo
import numpy as np
import probeinterface as pi
import spikeinterface
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.gridspec import GridSpec
from neo.rawio import BlackrockRawIO
from probeinterface import Probe
from spikeinterface.core import (
    BaseRecording,
    BaseSorting,
    SortingAnalyzer,
    create_sorting_analyzer,
    load_sorting_analyzer,
    select_segment_sorting,
)
from spikeinterface.core.template_tools import get_template_extremum_channel
from spikeinterface.extractors import read_blackrock, read_blackrock_sorting

warnings.filterwarnings(
    "ignore", message="Detected .* undocumented segments within nev data"
)

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "raw"
BASE = "Nigel_Anterior_2023-03-17_Baseline_DigitalHeadstage"

NS5 = DATA / f"{BASE}.ns5"
NEV_AUTO = DATA / f"{BASE}-01.nev"
NEV_CURATED = DATA / f"{BASE}-02.nev"
CMP = DATA / "SN 1025-001496.cmp"

FIG_DIR = REPO / "figures" / "validation"
CACHE_DIR = REPO / "data" / "derived" / "nigel_2023-03-17"
ANALYZER_CACHE = CACHE_DIR / "sorting_analyzer_curated.zarr"

UTAH_PITCH_UM = 400.0
SPIKE_CHANNEL_NAME_RE = re.compile(r"^ch(?P<elec>\d+)#(?P<unit>\d+)$")
BANK_COLORS = {"A": "#a6cee3", "B": "#fdbf6f", "C": "#b2df8a"}  # soft blue/orange/green
SEG_BROADBAND = 1  # session 1: seg[0]=2.36s false-start, seg[1]=180.01s

# Session 1's dynamic resolver verified that this file's 30 kHz broadband
# stream is id "5". Hard-coded here for brevity; a future session running on
# a different recording should re-verify or copy the resolver from
# scratch_load_nigel_2023-03-17.py.
NS5_STREAM_ID = "5"

WAVE_MS_BEFORE = 1.0
WAVE_MS_AFTER = 2.0
WAVE_MAX_SPIKES = 500


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# === Setup helpers: CMP parsing + probe attach (mirrors session 1) ===
def parse_blackrock_cmp(path: Path) -> list[dict]:
    """Parse a Blackrock per-array .cmp mapfile into per-electrode records.

    Mirror of the parser in scratch_load_nigel_2023-03-17.py - duplicated
    inline per session-2 scope ("do not promote to src/ this session").

    Parameters
    ----------
    path : Path
        Path to the .cmp file.

    Returns
    -------
    list of dict
        One dict per electrode with keys ``col``, ``row``, ``bank``, ``elec``,
        ``label``, ``electrode_id``. See docs/notes/utah_channel_mapping.md.
    """
    rows: list[dict] = []
    for ln in path.read_text().splitlines():
        s = ln.strip()
        if not s or s.startswith("//"):
            continue
        parts = s.split()
        if len(parts) < 4:
            continue
        if not (parts[0].isdigit() and parts[1].isdigit() and parts[3].isdigit()):
            continue
        col, row, bank, elec = int(parts[0]), int(parts[1]), parts[2], int(parts[3])
        label = parts[4] if len(parts) >= 5 else f"bank{bank}_elec{elec}"
        electrode_id = (ord(bank.upper()) - ord("A")) * 32 + elec
        rows.append(
            dict(col=col, row=row, bank=bank, elec=elec, label=label, electrode_id=electrode_id)
        )
    return rows


def build_probe(cmp_rows: list[dict]) -> Probe:
    """Build a ``probeinterface.Probe`` for the Utah-96 from parsed CMP rows.

    Parameters
    ----------
    cmp_rows : list of dict
        Output of :func:`parse_blackrock_cmp`.

    Returns
    -------
    Probe
        A 2D probe with one contact per CMP row, ``contact_ids`` set to the
        Blackrock electrode-id strings (the same strings ``rec.channel_ids``
        exposes). ``device_channel_indices`` is NOT set here - that requires
        the recording and is handled by :func:`attach_probe`.
    """
    positions = np.array(
        [[r["col"] * UTAH_PITCH_UM, r["row"] * UTAH_PITCH_UM] for r in cmp_rows], dtype=float
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
    return probe


def attach_probe(rec: BaseRecording, probe: Probe, cmp_rows: list[dict]) -> BaseRecording:
    """Attach the Utah probe to a recording, mapping contacts by electrode_id.

    Builds ``device_channel_indices`` from the dict
    ``electrode_id -> channel_index`` rather than positionally - some
    Blackrock files have non-contiguous electrode ids (CLAUDE.md gotcha).

    Parameters
    ----------
    rec : BaseRecording
        The probe-less recording from ``read_blackrock``.
    probe : Probe
        From :func:`build_probe`. ``device_channel_indices`` is set as a
        side effect.
    cmp_rows : list of dict
        From :func:`parse_blackrock_cmp`.

    Returns
    -------
    BaseRecording
        The probe-attached recording (single group, ``group_mode="by_probe"``).
    """
    rec_chan_ids = [str(c) for c in rec.channel_ids]
    chan_index_by_eid = {eid: i for i, eid in enumerate(rec_chan_ids)}
    contact_ids = [str(r["electrode_id"]) for r in cmp_rows]
    dev = np.array([chan_index_by_eid[cid] for cid in contact_ids], dtype=int)
    probe.set_device_channel_indices(dev)
    return rec.set_probe(probe, group_mode="by_probe")


# === Setup helpers: sorting parse (mirrors session 1) ===
def neo_spike_channel_table(nev_path: Path) -> list[dict]:
    """Read NEO ``spike_channels`` from a .nev, parsing ``chE#U`` names.

    See docs/notes/blackrock_loading.md for the full mapping.

    Parameters
    ----------
    nev_path : Path
        Path to the .nev file.

    Returns
    -------
    list of dict
        Positional rows (same order as SI's ``BaseSorting.unit_ids``) with
        keys ``name``, ``electrode_id``, ``plexon_unit_id``. Unparsable rows
        get ``-1`` for both id fields so format drift is caught by the
        downstream assert.
    """
    raw = BlackrockRawIO(filename=str(nev_path.with_suffix("")))
    raw.parse_header()
    out: list[dict] = []
    for ch in raw.header["spike_channels"]:
        name = str(ch["name"])
        m = SPIKE_CHANNEL_NAME_RE.match(name)
        if m:
            out.append(
                dict(name=name, electrode_id=int(m["elec"]), plexon_unit_id=int(m["unit"]))
            )
        else:
            out.append(dict(name=name, electrode_id=-1, plexon_unit_id=-1))
    return out


def load_sorted_sorting(
    nev_path: Path, sr: float
) -> tuple[BaseSorting, dict]:
    """Load a Plexon-written .nev as a sorting filtered to ``U not in {0, 255}``.

    Parameters
    ----------
    nev_path : Path
        Path to the Plexon-written .nev.
    sr : float
        Sampling frequency in Hz (must match the broadband recording).

    Returns
    -------
    sorting : BaseSorting
        The filtered sorting (217 units in the Nigel 2023-03-17 baseline).
    assigned_eid : dict
        ``unit_id -> Blackrock electrode_id`` taken from the NEO
        spike-channel name. The unit ids are the SI positional indices,
        not the Plexon unit numbers.
    """
    neo_table = neo_spike_channel_table(nev_path)
    sorting = read_blackrock_sorting(file_path=str(nev_path), sampling_frequency=sr)
    assert len(neo_table) == sorting.get_num_units(), (
        f"NEO vs SI length mismatch on {nev_path.name}: "
        f"{len(neo_table)} vs {sorting.get_num_units()}"
    )
    sorted_idx = [
        i for i, r in enumerate(neo_table) if r["plexon_unit_id"] not in (0, 255)
    ]
    keep_uids = [sorting.unit_ids[i] for i in sorted_idx]
    sorted_sorting = sorting.select_units(unit_ids=keep_uids)
    assigned_eid = {sorting.unit_ids[i]: neo_table[i]["electrode_id"] for i in sorted_idx}
    return sorted_sorting, assigned_eid


# === Figure rendering helpers ===
def fig1_channel_mapping(
    channel_table: list[dict], cmp_rows: list[dict], out_stem: Path
) -> None:
    """Render Figure 1: Utah-96 layout with four-ID disambiguation per tile.

    Each tile shows ``electrode_id`` (from CMP), SI ``channel_id``, SI
    ``channel_index``, and ``bank/elec``. Tile fill is colored by bank.
    Empty grid positions (4 of 100 on this array) are left as figure
    background.

    Parameters
    ----------
    channel_table : list of dict
        One row per recording channel; see the building loop in :func:`main`.
    cmp_rows : list of dict
        From :func:`parse_blackrock_cmp`; provides ``(col, row)`` placement.
    out_stem : Path
        Output path *without* extension; both ``.png`` (150 dpi) and ``.pdf``
        (vector) are written.
    """
    by_eid = {r["electrode_id"]: r for r in cmp_rows}
    fig = plt.figure(figsize=(12, 12))
    gs = GridSpec(10, 10, figure=fig, hspace=0.08, wspace=0.08)
    for c in channel_table:
        cmp_row = by_eid[c["electrode_id_from_cmp"]]
        col, row = cmp_row["col"], cmp_row["row"]
        # Visual row 0 should sit at the bottom (CMP convention); GridSpec
        # is top-down, so place at grid index 9-row.
        ax = fig.add_subplot(gs[9 - row, col])
        ax.set_facecolor(BANK_COLORS[cmp_row["bank"]])
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_linewidth(0.5)
            sp.set_color("0.4")
        ax.text(
            0.5, 0.5,
            f"eid {c['electrode_id_from_cmp']}\n"
            f"cid {c['channel_id']}\n"
            f"idx {c['channel_index']}\n"
            f"{cmp_row['bank']}/{cmp_row['elec']}",
            ha="center", va="center", fontsize=8, family="monospace",
        )
    fig.suptitle(
        "Utah-96 channel mapping  (Nigel 2023-03-17 baseline)\n"
        "tile fill = bank  (A blue, B orange, C green)   "
        "eid=electrode id from CMP,  cid=SI channel_id,  idx=SI channel_index",
        fontsize=11,
    )
    fig.text(
        0.5, 0.04, "row 0 at bottom (CMP convention) ; col 0 at left",
        ha="center", fontsize=9, color="0.3",
    )
    fig.savefig(out_stem.with_suffix(".png"), dpi=150, bbox_inches="tight")
    fig.savefig(out_stem.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def grid_array_from_per_elec(
    per_elec: Counter, cmp_rows: list[dict]
) -> np.ma.MaskedArray:
    """Lay a ``electrode_id -> count`` Counter onto the 10x10 Utah grid.

    Parameters
    ----------
    per_elec : Counter
        Mapping ``electrode_id -> sorted-unit count``.
    cmp_rows : list of dict
        Provides ``(col, row)`` placement. Missing CMP positions (the 4
        unused contacts on this array) end up masked.

    Returns
    -------
    np.ma.MaskedArray
        Shape ``(10, 10)``. ``grid[r, c]`` is the count at ``(col=c, row=r)``;
        positions absent from ``cmp_rows`` are masked.
    """
    grid = np.full((10, 10), np.nan)
    by_eid = {r["electrode_id"]: r for r in cmp_rows}
    for eid, n in per_elec.items():
        r = by_eid[eid]
        grid[r["row"], r["col"]] = n
    # Filled-but-unit-less CMP positions get 0 so only truly absent
    # (missing-contact) cells stay masked.
    for r in cmp_rows:
        if np.isnan(grid[r["row"], r["col"]]):
            grid[r["row"], r["col"]] = 0
    return np.ma.array(grid, mask=np.isnan(grid))


def fig2_units_per_electrode(
    auto_per_elec: Counter,
    cur_per_elec: Counter,
    cmp_rows: list[dict],
    out: Path,
) -> None:
    """Render Figure 2: three-panel units-per-electrode heatmap.

    Panel A: auto-sort counts (viridis). Panel B: curated counts (viridis,
    same vmax). Panel C: ``curated - auto`` (RdBu_r, symmetric).

    Parameters
    ----------
    auto_per_elec, cur_per_elec : Counter
        ``electrode_id -> unit count`` for each sorting.
    cmp_rows : list of dict
        Provides ``(col, row)`` placement.
    out : Path
        Output PNG path. No PDF for this figure (it is a small heatmap).
    """
    grid_auto = grid_array_from_per_elec(auto_per_elec, cmp_rows)
    grid_cur = grid_array_from_per_elec(cur_per_elec, cmp_rows)
    grid_diff = grid_cur - grid_auto

    vmax_count = int(max(grid_auto.max(), grid_cur.max()))
    vmax_diff = int(max(1, np.abs(grid_diff).max()))

    fig, axes = plt.subplots(1, 3, figsize=(18, 6.4))
    panels = [
        ("auto-sort (-01.nev)", grid_auto, "viridis", 0, vmax_count),
        ("curated (-02.nev)", grid_cur, "viridis", 0, vmax_count),
        (f"curated - auto  (±{vmax_diff})", grid_diff, "RdBu_r", -vmax_diff, vmax_diff),
    ]
    for ax, (title, g, cmap_name, vmin, vmax) in zip(axes, panels, strict=True):
        cmap = plt.get_cmap(cmap_name).copy()
        cmap.set_bad("lightgray")
        im = ax.imshow(g, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_title(title)
        ax.set_xlabel("col (x = col * 400 um)")
        ax.set_ylabel("row (y = row * 400 um)")
        ax.set_xticks(range(10))
        ax.set_yticks(range(10))
        for (r, c), v in np.ndenumerate(g.filled(np.nan)):
            if np.isnan(v):
                continue
            txt = f"{int(v):d}"
            color = "white" if (cmap_name == "viridis" and v > vmax * 0.55) else "black"
            ax.text(c, r, txt, ha="center", va="center", fontsize=8, color=color)
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    fig.suptitle(
        f"Units per electrode  (auto sum={int(grid_auto.sum())}, "
        f"curated sum={int(grid_cur.sum())})",
        fontsize=12,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig3_templates_pdf(
    sa: SortingAnalyzer,
    sort_seg1: BaseSorting,
    assigned_eid_by_unit: dict,
    peak_eid_by_unit: dict,
    cmp_rows: list[dict],
    channel_index_by_eid: dict,
    out_pdf: Path,
    first_n: int | None,
) -> dict:
    """Render a multi-page PDF: one page per curated unit, 96 mini-axes per page.

    For each unit, all 96 channels show the unit's mean template at their
    Utah-grid position. Per-page y-axis is shared across all 96 panels.
    Assigned electrode (from Plexon ``chE#U``) is highlighted red; peak
    electrode (from ``get_template_extremum_channel``) is highlighted green;
    when they agree the tile is orange.

    See docs/notes/template_extremum_channel.md.

    Parameters
    ----------
    sa : SortingAnalyzer
        Built with ``sparse=False`` so templates cover all 96 channels.
    sort_seg1 : BaseSorting
        Single-segment sorting matching the analyzer.
    assigned_eid_by_unit : dict
        ``unit_id -> Blackrock electrode_id`` from the NEV ``chE#U`` name.
    peak_eid_by_unit : dict
        ``unit_id -> Blackrock electrode_id`` from the template extremum.
    cmp_rows : list of dict
        Provides ``(col, row)`` placement.
    channel_index_by_eid : dict
        ``electrode_id (str) -> recording channel_index (int)``.
    out_pdf : Path
        Output PDF path.
    first_n : int or None
        If given, only the first N units render (dev iteration).

    Returns
    -------
    dict
        Keys: ``n_pages``, ``n_zero_seg1`` (units with zero spikes in the
        kept segment), ``n_nan_template`` (units whose template is all NaN).
    """
    templates = sa.get_extension("templates").get_data(operator="average")  # (U, T, C)
    sr = sa.sampling_frequency
    n_samples = templates.shape[1]
    nbefore = int(round(WAVE_MS_BEFORE * sr / 1000.0))
    t_ms = (np.arange(n_samples) - nbefore) / sr * 1000.0

    unit_ids = list(sort_seg1.unit_ids)
    if first_n is not None:
        unit_ids = unit_ids[:first_n]

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    n_zero_seg1 = 0
    n_nan_template = 0

    with PdfPages(out_pdf) as pdf:
        for uid in unit_ids:
            unit_index = sa.sorting.id_to_index(uid)
            tmpl = templates[unit_index]  # tmpl: (T, C) template for this unit
            assigned = int(assigned_eid_by_unit.get(uid, -1))
            peak = peak_eid_by_unit.get(uid)
            try:
                peak = int(peak)
            except (TypeError, ValueError):
                peak = -1
            n_spikes = len(sort_seg1.get_unit_spike_train(uid, segment_index=0))
            if n_spikes == 0:
                n_zero_seg1 += 1

            # Per-page y-limit shared across all 96 panels. All-NaN templates
            # (units with zero spikes in this segment) get a placeholder.
            finite = np.isfinite(tmpl)
            if not finite.any():
                n_nan_template += 1
                y_abs = 1.0
            else:
                y_abs = max(1.0, 1.05 * float(np.nanmax(np.abs(tmpl))))

            mismatch = assigned != peak
            fig = plt.figure(figsize=(11, 11))
            gs = GridSpec(10, 10, figure=fig, hspace=0.05, wspace=0.05)

            for r in cmp_rows:
                eid = r["electrode_id"]
                ch_idx = channel_index_by_eid[str(eid)]
                ax = fig.add_subplot(gs[9 - r["row"], r["col"]])
                wf = tmpl[:, ch_idx]
                ax.plot(t_ms, wf, linewidth=0.7, color="black")
                ax.axhline(0, color="0.7", linewidth=0.4)
                ax.set_xlim(t_ms[0], t_ms[-1])
                ax.set_ylim(-y_abs, y_abs)
                ax.set_xticks([])
                ax.set_yticks([])
                # Highlight: red=assigned only, green=peak only, orange=both.
                if eid == assigned and eid == peak:
                    ax.set_facecolor((1.0, 0.92, 0.85))
                    for sp in ax.spines.values():
                        sp.set_color("darkorange")
                        sp.set_linewidth(2.2)
                elif eid == assigned:
                    ax.set_facecolor((1.0, 0.88, 0.88))
                    for sp in ax.spines.values():
                        sp.set_color("red")
                        sp.set_linewidth(2.2)
                elif eid == peak:
                    ax.set_facecolor((0.88, 1.0, 0.88))
                    for sp in ax.spines.values():
                        sp.set_color("green")
                        sp.set_linewidth(2.2)
                else:
                    for sp in ax.spines.values():
                        sp.set_color("0.7")
                        sp.set_linewidth(0.4)
                ax.text(
                    0.02, 0.98, str(eid), transform=ax.transAxes,
                    fontsize=6, color="0.4", ha="left", va="top",
                )

            ttl = (
                f"unit {uid}   assigned=elec{assigned}   peak=elec{peak}   "
                f"n_spikes_seg1={n_spikes}   amp_max={y_abs/1.05:.1f} uV   "
                f"{'MISMATCH' if mismatch else 'match'}"
            )
            fig.suptitle(ttl, fontsize=10, family="monospace")
            fig.text(
                0.5, 0.02,
                "red = assigned (Plexon)   green = peak (template extremum)   "
                "orange = both   y-axis shared across 96 panels",
                ha="center", fontsize=8, color="0.3",
            )
            pdf.savefig(fig, dpi=110)
            plt.close(fig)

    return dict(n_pages=len(unit_ids), n_zero_seg1=n_zero_seg1, n_nan_template=n_nan_template)


# === Main ===
def main() -> int:
    """Build the three validation figures and print the (a)/(b)/(c) report."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--first-n", type=int, default=None,
                    help="Cap Figure 3 to first N pages (dev iteration).")
    ap.add_argument("--rebuild-analyzer", action="store_true",
                    help="Ignore cached SortingAnalyzer zarr; recompute.")
    args = ap.parse_args()

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # === Step 0: print SI / PI / NEO versions ===
    banner("Step 0  versions")
    print(f"python              {sys.version.split()[0]}")
    print(f"spikeinterface      {spikeinterface.__version__}")
    print(f"probeinterface      {pi.__version__}")
    print(f"neo                 {neo.__version__}")
    print(f"figures             {FIG_DIR}")
    print(f"cache               {ANALYZER_CACHE}")

    # === Step 1: load .ns5, parse CMP, attach probe ===
    banner("Setup  load .ns5, parse CMP, attach probe")
    rec = read_blackrock(file_path=str(NS5), stream_id=NS5_STREAM_ID)
    sr = rec.get_sampling_frequency()      # sr: sampling rate in Hz (expected 30000.0)
    nseg = rec.get_num_segments()          # nseg: number of NEO-exposed recording segments
    print(f"channels={rec.get_num_channels()}  sr={sr} Hz  segments={nseg}")
    for s in range(nseg):
        print(f"  seg[{s}]  n_samples={rec.get_num_samples(segment_index=s):>10d}  "
              f"dur={rec.get_num_samples(segment_index=s)/sr:8.2f} s")

    cmp_rows = parse_blackrock_cmp(CMP)
    probe = build_probe(cmp_rows)
    rec_wp = attach_probe(rec, probe, cmp_rows)
    print(f"CMP rows={len(cmp_rows)}  probe contacts={probe.get_contact_count()}  "
          f"channel_locations={rec_wp.get_channel_locations().shape}")

    # === Step 2: build channel_table joining recording channels to CMP rows ===
    banner("Build channel_table")
    by_eid = {r["electrode_id"]: r for r in cmp_rows}
    rec_chan_ids = [str(c) for c in rec_wp.channel_ids]
    channel_table = []
    locs = rec_wp.get_channel_locations()
    for k, cid in enumerate(rec_chan_ids):
        eid = int(cid)
        cmp_r = by_eid[eid]
        channel_table.append(dict(
            channel_index=k,
            channel_id=cid,
            electrode_id_from_cmp=eid,
            bank=cmp_r["bank"],
            elec_in_bank=cmp_r["elec"],
            col=cmp_r["col"],
            row=cmp_r["row"],
            x_um=float(locs[k, 0]),
            y_um=float(locs[k, 1]),
            label=cmp_r["label"],
        ))
    assert len(channel_table) == 96

    # === Step 3: report (a) - channel_id / electrode_id / channel_index disagreements ===
    banner("Report (a)  channel_id / electrode_id / channel_index disagreements")
    disagreements = []
    for c in channel_table:
        ok_eid = int(c["channel_id"]) == c["electrode_id_from_cmp"]
        ok_idx = c["channel_index"] + 1 == int(c["channel_id"])
        if not (ok_eid and ok_idx):
            disagreements.append(c)
    if disagreements:
        print(f"FOUND {len(disagreements)} mismatching rows:")
        for c in disagreements:
            print(f"  idx={c['channel_index']:3d}  cid={c['channel_id']}  "
                  f"eid={c['electrode_id_from_cmp']}  bank={c['bank']}  elec={c['elec_in_bank']}")
    else:
        print("0 -- confirms session 1 contiguous mapping (channel_index+1 == channel_id == electrode_id)")

    # === Step 4: Figure 1 - channel mapping ===
    banner("Figure 1  channel mapping")
    fig1_channel_mapping(channel_table, cmp_rows, FIG_DIR / "01_channel_mapping")
    print(f"wrote {FIG_DIR / '01_channel_mapping.png'} and .pdf")

    # === Step 5: load both sortings and build per-electrode unit counts ===
    banner("Load sortings (auto and curated), build per-electrode counts")
    sort_auto, assigned_auto = load_sorted_sorting(NEV_AUTO, sr)
    sort_cur,  assigned_cur  = load_sorted_sorting(NEV_CURATED, sr)
    print(f"auto sorted units: {sort_auto.get_num_units()}   "
          f"curated sorted units: {sort_cur.get_num_units()}")

    auto_per_elec = Counter(assigned_auto.values())
    cur_per_elec = Counter(assigned_cur.values())
    print(f"auto electrodes with >=1 unit:    {len(auto_per_elec)} / 96")
    print(f"curated electrodes with >=1 unit: {len(cur_per_elec)} / 96")

    # === Step 6: Figure 2 - units-per-electrode heatmap ===
    banner("Figure 2  units-per-electrode heatmap")
    fig2_units_per_electrode(
        auto_per_elec, cur_per_elec, cmp_rows, FIG_DIR / "02_units_per_electrode.png"
    )
    print(f"wrote {FIG_DIR / '02_units_per_electrode.png'}")

    # === Step 7: build or load the SortingAnalyzer (curated, segment 1 only) ===
    banner("SortingAnalyzer  curated, seg 1 only")
    if args.rebuild_analyzer and ANALYZER_CACHE.exists():
        print(f"--rebuild-analyzer: removing cached {ANALYZER_CACHE}")
        shutil.rmtree(ANALYZER_CACHE)

    rec_seg = rec_wp.select_segments([SEG_BROADBAND])
    sort_seg = select_segment_sorting(sort_cur, [SEG_BROADBAND])
    print(f"rec_seg  segments={rec_seg.get_num_segments()}  "
          f"n_samples={rec_seg.get_num_samples()}  dur={rec_seg.get_num_samples()/sr:.2f} s")
    print(f"sort_seg segments={sort_seg.get_num_segments()}  "
          f"n_units={sort_seg.get_num_units()}")

    template_runtime: float | str
    if ANALYZER_CACHE.exists():
        print(f"loading cached analyzer from {ANALYZER_CACHE}")
        sa = load_sorting_analyzer(ANALYZER_CACHE)
        has_tpl = sa.has_extension("templates")
        print(f"has_extension('templates') = {has_tpl}")
        if not has_tpl:
            print("cache exists but no templates; recomputing via accumulator")
            t0 = time.perf_counter()
            if not sa.has_extension("random_spikes"):
                sa.compute("random_spikes", method="uniform",
                           max_spikes_per_unit=WAVE_MAX_SPIKES, seed=0)
            sa.compute(
                "templates", operators=["average"],
                ms_before=WAVE_MS_BEFORE, ms_after=WAVE_MS_AFTER,
            )
            template_runtime = time.perf_counter() - t0
        else:
            template_runtime = "(cached)"
    else:
        print(f"building analyzer (sparse=False, return_scaled=True) -> {ANALYZER_CACHE}")
        # Deliberately skip the 'waveforms' extension. With 217 units x 500
        # spikes x 96 channels x 90 samples x float32 ~= 3.75 GB the shared
        # memory buffer overflows on Windows. ComputeTemplates with no
        # waveforms-cache falls back to estimate_templates_with_accumulator,
        # which streams through the recording once.
        # See docs/notes/sorting_analyzer.md.
        t0 = time.perf_counter()
        sa = create_sorting_analyzer(
            sort_seg, rec_seg,
            format="zarr",
            folder=str(ANALYZER_CACHE),
            sparse=False,
            return_scaled=True,
            overwrite=False,
        )
        sa.compute("random_spikes", method="uniform",
                   max_spikes_per_unit=WAVE_MAX_SPIKES, seed=0)
        sa.compute(
            "templates", operators=["average"],
            ms_before=WAVE_MS_BEFORE, ms_after=WAVE_MS_AFTER,
        )
        template_runtime = time.perf_counter() - t0

    if isinstance(template_runtime, float):
        print(f"template-compute runtime: {template_runtime:.1f} s")
    else:
        print(f"template-compute runtime: {template_runtime}")

    # === Step 8: peak electrode per unit vs assigned electrode ===
    banner("Peak electrode per unit  vs  assigned electrode")
    peak_id_by_unit = get_template_extremum_channel(
        sa, peak_sign="neg", mode="peak_to_peak", outputs="id"
    )
    # channel_id strings -> int for compare with assigned electrode_id
    peak_eid_by_unit = {u: int(cid) for u, cid in peak_id_by_unit.items()}
    mismatches = [
        (u, assigned_cur[u], peak_eid_by_unit[u])
        for u in sort_cur.unit_ids
        if u in peak_eid_by_unit and peak_eid_by_unit[u] != assigned_cur[u]
    ]
    print(f"mismatches: {len(mismatches)} / {sort_cur.get_num_units()}")
    for row in mismatches[:5]:
        print(f"  unit={row[0]}  assigned=elec{row[1]}  peak=elec{row[2]}")

    # === Step 9: Figure 3 - per-unit dense templates PDF ===
    banner("Figure 3  per-unit dense templates (PDF)")
    channel_index_by_eid = {cid: i for i, cid in enumerate(rec_chan_ids)}
    out_pdf = FIG_DIR / "03_unit_templates_curated.pdf"
    if args.first_n is not None:
        out_pdf = FIG_DIR / f"03_unit_templates_curated_first{args.first_n}.pdf"

    summary = fig3_templates_pdf(
        sa=sa,
        sort_seg1=sort_seg,
        assigned_eid_by_unit=assigned_cur,
        peak_eid_by_unit=peak_eid_by_unit,
        cmp_rows=cmp_rows,
        channel_index_by_eid=channel_index_by_eid,
        out_pdf=out_pdf,
        first_n=args.first_n,
    )
    print(f"wrote {out_pdf}  pages={summary['n_pages']}  "
          f"zero-spike-in-seg1 units={summary['n_zero_seg1']}  "
          f"all-nan templates={summary['n_nan_template']}")

    # === Step 10: final report - (a)/(b)/(c) ===
    banner("Final report  (a) / (b) / (c)")
    print(f"(a) channel-mapping disagreements:  {len(disagreements)}")
    if disagreements:
        for c in disagreements:
            print(f"    idx={c['channel_index']:3d}  cid={c['channel_id']}  "
                  f"eid={c['electrode_id_from_cmp']}")
    print(f"(b) peak-vs-assigned mismatches:    "
          f"{len(mismatches)} / {sort_cur.get_num_units()}")
    for row in mismatches[:5]:
        print(f"    unit={row[0]}  assigned=elec{row[1]}  peak=elec{row[2]}")
    if isinstance(template_runtime, float):
        print(f"(c) template-compute runtime:       {template_runtime:.1f} s")
    else:
        print(f"(c) template-compute runtime:       {template_runtime}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

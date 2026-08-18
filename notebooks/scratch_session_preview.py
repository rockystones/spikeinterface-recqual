"""One "session preview" figure per recording: everything about it on one page.

Four panels, following the conventions in the owner's MATLAB
(`Monkey Data/Older code/plot_U01_Utaharray_*.m`) except where noted:

  1  metrics table -- identity, method and parameters, sorting results,
     sorting-based ephys metrics, sorting quality, sorting-free metrics
  2  per-unit waveforms, one axes per electrode, **arranged at the array's
     physical positions** rather than by channel index
  3  units-per-electrode grid at physical positions
  4  peak-to-peak amplitude grid at physical positions

Kept from the MATLAB:

- Unit amplitude is the peak-to-peak of the **mean** waveform, and a channel's
  amplitude is the largest unit on it.
- The shaded band is the full min-to-max envelope of that unit's waveforms at
  each sample -- not a standard deviation.
- `hot` colormap on the grids, values printed in each cell.
- Waveform y range +/-200 uV, from `plot_U01_Utaharray_05042023.m`.

Changed, on instruction:

- **No amplitude exclusion.** The MATLAB dropped units whose mean waveform was
  flatter than 20 uV; every declared unit is drawn and counted here.
- **A fixed y range, never autoscaled.** A big unit may run off the top; a
  small one must not flatten to a line. Clipped envelopes are counted and the
  count is printed.
- **Two kinds of blank look different.** A cell with no electrode wired to it
  is grey with a red X; an electrode that recorded nothing takes value 0 and
  the bottom of the colour scale, because that is a real measurement.
- **A colourblind-safe unit palette** rather than the Spectral ramp, whose
  pale end vanishes on white.
- **Panel 2 is at physical array positions.** The MATLAB laid channels out in
  index order and flagged it: *"The channel index here is for the Blackrock
  recording file channel index, NOT the elec# !!! Remap later."* Its grid code
  fixes this, keeping the earlier attempt commented *"This is the old code
  that mapped the location using elec not the chan, which is WRONG!"* On
  Nigel's 001496 only 2 of 96 contacts have channel_id equal to their elec
  number, so index order misplaces 94 of them.

Run from repo root:

    uv run python notebooks/scratch_session_preview.py                # all
    uv run python notebooks/scratch_session_preview.py --chain -01
    uv run python notebooks/scratch_session_preview.py --stem <stem>

See:
- docs/notes/session_preview.md
- docs/notes/channel_mapping.md
"""

from __future__ import annotations

import argparse
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import Normalize  # noqa: E402
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec  # noqa: E402

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from _paths import MONKEY_ROOT  # noqa: E402
from scratch_cohort_io import array_serial, parse_cmp  # noqa: E402
from scratch_rocky_resort import (  # noqa: E402
    baseline_noise_uv,
    open_nev,
    read_electrode,
)

INV = REPO / "data" / "derived" / "monkey_inventory.parquet"
PROBE_DIR = REPO / "configs" / "probes"
FIG_ROOT = REPO / "figures"

# Unit colours. The MATLAB Color_book was a Spectral ramp, which puts pale
# yellows next to near-white and loses two of its ten on a white background.
# This is Okabe-Ito (colourblind-safe) with its unusable yellow replaced and
# extended to ten, ordered so the first few -- the common case -- are maximally
# separated.
UNIT_COLORS = [
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#009E73",  # bluish green
    "#CC79A7",  # reddish purple
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#7A3B94",  # violet
    "#8C6D31",  # bronze
    "#1B7837",  # dark green
    "#762A83",  # dark purple
]

NOT_A_UNIT = (0, 255)      # 0 unsorted, 255 noise

# Waveform y range, fixed. From the owner's MATLAB (`ylim([-200,200])`, in
# plot_U01_Utaharray_05042023.m). Fixed rather than per-panel on instruction:
# a shared scale keeps panels comparable within and across sessions, and a
# large unit clipping is acceptable where a small one flattening to a line is
# not.
WAVE_YLIM_UV = 200.0

# Grid colour scales, also fixed for cross-session comparability. The MATLAB
# used caxis([0,5]) / caxis([0,6]) for units and caxis([0,600]) for amplitude.
UNITS_CLIM = (0.0, 6.0)
AMP_CLIM = (0.0, 600.0)

# Production Plexon parameters, read from the `.ofb` batch files. Identical in
# every monkey and array folder checked -- Nigel Anterior/Posterior, Fisk
# SN1498/SN1504 -- so this is the pipeline, not one operator's session.
# The `OFS sorting test2023` sweep used ScanStart 1 and ArtifactPercentage 20;
# production uses 10 and 15.
TDIST_PARAMS = ("ScanTDist, 3D, J3; scan 10-30 step 5; "
                "artifact w60 p15%; outliers 1.5")
CHAIN_LABEL = {"": "original (unsorted)", "-01": "Plexon OFS automatic",
               "-02": "manual curation, operator DS",
               "-DS": "manual curation, operator DS",
               "-MA": "manual curation, operator Sidd",
               "-MA-RE": "operator Sidd, redone",
               "-MA-01": "operator Sidd, redone",
               "-MA-02": "operator Sidd, redone",
               "-MADS": "Sidd sorted then DS curated (sequential)",
               "-00": "partial OFS pass, superseded by -01"}


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === Geometry ===
def load_geometry(subject: str, array: str, implant: str) -> pd.DataFrame:
    """The array's own mapfile, as a frame with col/row/channel_id/label."""
    serial = array_serial(subject, array, implant)
    if not serial:
        raise RuntimeError(f"no serial registered for {subject} {implant} {array}")
    hits = sorted(PROBE_DIR.glob(f"*{serial}*.cmp"))
    if not hits:
        raise RuntimeError(f"no .cmp for {serial}")
    d = parse_cmp(hits[0])
    d.attrs["serial"] = serial
    d.attrs["cmp"] = hits[0].name
    return d


# %%
# === Per-electrode unit extraction ===
def session_units(nev: Path) -> tuple[dict, dict]:
    """Per-channel unit waveforms, plus the session's sorting-free numbers.

    Returns ``(by_channel, free)`` where `by_channel[channel_id]` is a list of
    dicts with `unit`, `mean`, `lo`, `hi`, `n`, `p2p`, and `free` holds the
    threshold-crossing metrics that need no labels.
    """
    raw, meta, chan_by_elec = open_nev(nev)
    nbefore, dur = meta["nbefore"], meta["duration_s"]
    by_channel: dict[int, list[dict]] = {}
    noises, counts, amps, snrs = [], [], [], []

    for elec in sorted(chan_by_elec):
        e = read_electrode(raw, meta, chan_by_elec[elec])
        if e is None or not len(e["t"]):
            continue
        wf, pu = e["wf"], e["plexon_unit"]
        noise = baseline_noise_uv(wf, nbefore)
        trough = np.abs(wf.min(axis=1))
        noises.append(noise)
        counts.append(len(wf))
        amps.append(trough)
        if noise > 0:
            snrs.append(float(np.median(trough) / noise))

        units = []
        for u in sorted(set(pu.tolist()) - set(NOT_A_UNIT)):
            sel = pu == u
            if sel.sum() < 2:
                continue
            w = wf[sel]
            mean = w.mean(axis=0)
            units.append(dict(
                unit=int(u), n=int(sel.sum()), mean=mean,
                lo=w.min(axis=0), hi=w.max(axis=0),
                # MATLAB: peak-to-peak of the MEAN waveform, not of the cloud.
                p2p=float(mean.max() - mean.min()),
                noise=noise,
            ))
        by_channel[int(elec)] = units

    allamp = np.concatenate(amps) if amps else np.array([0.0])
    free = dict(
        duration_s=dur, sr=meta["sr"], nbefore=nbefore,
        n_elec_active=len(counts), n_crossings=int(sum(counts)),
        crossing_rate_hz=float(sum(counts) / dur / max(len(counts), 1))
        if dur else np.nan,
        noise_med=float(np.median(noises)) if noises else np.nan,
        noise_p90=float(np.percentile(noises, 90)) if noises else np.nan,
        amp_p50=float(np.percentile(allamp, 50)),
        amp_p90=float(np.percentile(allamp, 90)),
        amp_p99=float(np.percentile(allamp, 99)),
        amp_max=float(allamp.max()),
        peak_snr_med=float(np.median(snrs)) if snrs else np.nan,
    )
    return by_channel, free


# %%
# === Panels ===
def panel_table(ax, meta: dict, geo: pd.DataFrame, by_ch: dict,
                free: dict) -> None:
    """Panel 1: everything numeric about this session, in one block."""
    ax.axis("off")
    n_elec = len(geo)
    # No amplitude exclusion: every declared unit is counted and drawn.
    drawn = by_ch
    n_units = sum(len(v) for v in drawn.values())
    with_units = sum(1 for v in drawn.values() if v)
    p2p = np.array([u["p2p"] for v in drawn.values() for u in v]) \
        if n_units else np.array([np.nan])
    snr = np.array([u["p2p"] / u["noise"] for v in drawn.values() for u in v
                    if u["noise"] > 0]) if n_units else np.array([np.nan])
    rates = np.array([u["n"] / free["duration_s"]
                      for v in drawn.values() for u in v]) \
        if n_units and free["duration_s"] else np.array([np.nan])

    rows = [
        ("SESSION", ""),
        ("  subject / implant", f"{meta['subject']}  {meta['implant']}"),
        ("  array", f"{meta['array']}   SN {geo.attrs['serial']}"),
        ("  date", str(meta["date"])),
        ("  headstage", str(meta.get("headstage") or "-")),
        ("  duration", f"{free['duration_s']:.1f} s   @ {free['sr']:.0f} Hz"),
        ("  mapfile", geo.attrs["cmp"]),
        ("", ""),
        ("METHOD", ""),
        ("  variant", f"{meta['chain'] or '(none)'}  "
                      f"{CHAIN_LABEL.get(meta['chain'], 'unruled')}"),
        ("  detection", "NSP online threshold (fixed at acquisition)"),
        ("  parameters", meta.get("params", TDIST_PARAMS)),
        ("", ""),
        ("SORTING RESULT", ""),
        ("  units declared", f"{n_units}"),
        ("  units / electrode", f"{n_units / n_elec:.3f}"),
        ("  electrodes with units", f"{with_units} / {n_elec}"
                                    f"   ({with_units / n_elec:.0%})"),
        ("", ""),
        ("SORTING-BASED EPHYS", ""),
        ("  unit amplitude p2p  median", f"{np.nanmedian(p2p):.1f} uV"),
        ("                      p99", f"{np.nanpercentile(p2p, 99):.1f} uV"),
        ("                      max", f"{np.nanmax(p2p):.1f} uV"),
        ("  unit SNR  median", f"{np.nanmedian(snr):.2f}"),
        ("  firing rate  median", f"{np.nanmedian(rates):.2f} Hz"),
        ("", ""),
        ("SORTING QUALITY", ""),
        ("  units per active electrode",
         f"{n_units / max(with_units, 1):.2f}"),
        ("", ""),
        ("SORTING-FREE (no labels used)", ""),
        ("  threshold crossings", f"{free['n_crossings']:,}"),
        ("  crossing rate / electrode", f"{free['crossing_rate_hz']:.2f} Hz"),
        ("  noise floor  median", f"{free['noise_med']:.2f} uV"),
        ("               p90", f"{free['noise_p90']:.2f} uV"),
        ("  crossing amp  p50 / p90", f"{free['amp_p50']:.0f} / "
                                      f"{free['amp_p90']:.0f} uV"),
        ("                p99 / max", f"{free['amp_p99']:.0f} / "
                                      f"{free['amp_max']:.0f} uV"),
        ("  peak SNR  median", f"{free['peak_snr_med']:.2f}"),
        ("  electrodes with events", f"{free['n_elec_active']} / {n_elec}"),
    ]
    # Wrap long values onto continuation lines rather than letting them run
    # off the axes -- the parameter string is 60+ characters and was being cut
    # mid-word, which hides exactly the part that distinguishes one sort from
    # another.
    import textwrap

    y = 1.0
    for k, v in rows:
        bold = k and not k.startswith(" ")
        ax.text(0.0, y, k, fontsize=7.6, family="monospace",
                weight="bold" if bold else "normal",
                color="#1a1a1a" if bold else "#333333",
                transform=ax.transAxes, va="top")
        for line in (textwrap.wrap(v, 42) if v else []):
            ax.text(0.60, y, line, fontsize=7.6, family="monospace",
                    transform=ax.transAxes, va="top")
            y -= 0.0228
        if not v:
            y -= 0.0228


def panel_waveforms(fig, spec, geo: pd.DataFrame, by_ch: dict, sr: float,
                    ylim: float = WAVE_YLIM_UV) -> None:
    """Panel 2: one axes per contact, laid out at its physical position.

    Every panel uses the same fixed +/-`ylim`, on instruction: a shared scale
    keeps panels comparable within a session and across sessions, and a large
    unit running off the top is acceptable where a small one collapsing to a
    flat line is not. The count of clipped envelopes is printed so the
    truncation is never silent.
    """
    n_col = int(geo.col.max() - geo.col.min() + 1)
    n_row = int(geo.row.max() - geo.row.min() + 1)
    gs = GridSpecFromSubplotSpec(n_row, n_col, subplot_spec=spec,
                                 hspace=0.62, wspace=0.34)
    c0, r0 = int(geo.col.min()), int(geo.row.min())
    ymax = float(ylim)
    n_clipped = 0

    for r in geo.itertuples():
        # CMP rows count up from the bottom, so invert for a pad-side view.
        gr = (n_row - 1) - (int(r.row) - r0)
        gc = int(r.col) - c0
        ax = fig.add_subplot(gs[gr, gc])
        units = by_ch.get(int(r.channel_id), [])
        for i, u in enumerate(units):
            col = UNIT_COLORS[i % len(UNIT_COLORS)]
            t = np.arange(len(u["mean"])) / sr * 1000.0    # ms
            ax.fill_between(t, u["lo"], u["hi"], color=col, alpha=0.16, lw=0)
            ax.plot(t, u["mean"], color=col, lw=0.9)
            if u["hi"].max() > ymax or u["lo"].min() < -ymax:
                n_clipped += 1
        ax.set_ylim(-ymax, ymax)
        ax.axhline(0, color="#cccccc", lw=0.3, zorder=0)
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_linewidth(0.4)
            s.set_color("#888888" if units else "#dddddd")
        ax.set_title(f"ch{int(r.channel_id)}·{r.label}", fontsize=4.4,
                     pad=1.0, color="#222222" if units else "#aaaaaa")
    fig.text(0.995, 0.5,
             f"all panels: y = +/-{ymax:.0f} uV fixed  "
             f"({n_clipped} unit envelope(s) clipped)",
             rotation=90, va="center", ha="right", fontsize=6.5,
             color="#666666")


def panel_grid(ax, geo: pd.DataFrame, values: dict, title: str,
               clim: tuple[float, float], fmt: str = "{:.0f}") -> None:
    """Panels 3 and 4: a value per contact, at its physical position.

    Two kinds of blank must not look alike, so they do not:

    - **No electrode wired to this cell** -- grey with a red X. Nothing was
      ever going to be recorded there.
    - **An electrode that recorded nothing** -- value 0, so it takes the
      bottom of the colour scale (black) like any other measurement. It is a
      real result about a real contact.

    `clim` is fixed rather than per-session, so the same colour means the same
    number in every figure -- which is the point of generating one per session.
    """
    n_col = int(geo.col.max() - geo.col.min() + 1)
    n_row = int(geo.row.max() - geo.row.min() + 1)
    c0, r0 = int(geo.col.min()), int(geo.row.min())
    grid = np.full((n_row, n_col), np.nan)      # NaN == no electrode here
    for r in geo.itertuples():
        gr = (n_row - 1) - (int(r.row) - r0)
        grid[gr, int(r.col) - c0] = values.get(int(r.channel_id), 0.0)

    vmin, vmax = clim
    cmap = matplotlib.colormaps["hot"].copy()
    cmap.set_bad("#9a9a9a")                     # unwired cells, mid grey
    im = ax.imshow(np.ma.masked_invalid(grid), cmap=cmap,
                   norm=Normalize(vmin, vmax), aspect="equal")
    for i in range(n_row):
        for j in range(n_col):
            v = grid[i, j]
            if not np.isfinite(v):
                ax.plot(j, i, marker="x", ms=9, mew=2.0, color="#cc0000")
                continue
            shade = (np.clip(v, vmin, vmax) - vmin) / max(vmax - vmin, 1e-9)
            ax.text(j, i, fmt.format(v), ha="center", va="center",
                    fontsize=5.4, color="black" if shade > 0.55 else "white")
    ax.set_xticks(range(n_col))
    ax.set_xticklabels(range(c0, c0 + n_col), fontsize=6)
    ax.set_yticks(range(n_row))
    ax.set_yticklabels(range(r0 + n_row - 1, r0 - 1, -1), fontsize=6)
    ax.set_title(title, fontsize=9)
    cb = plt.colorbar(im, ax=ax, fraction=0.045, pad=0.03, extend="max")
    cb.ax.tick_params(labelsize=6)


# %%
# === Assembly ===
def make_preview(meta: dict, out: Path,
                 ylim: float = WAVE_YLIM_UV) -> Path:
    geo = load_geometry(meta["subject"], meta["array"], meta["implant"])
    by_ch, free = session_units(Path(meta["path"]))

    # A contact that recorded nothing gets 0, not NaN: it is a real
    # measurement of an available electrode and must read as the bottom of the
    # colour scale, not as an absent contact.
    n_units = {int(c): len(v) for c, v in by_ch.items()}
    max_amp = {int(c): (max(u["p2p"] for u in v) if v else 0.0)
               for c, v in by_ch.items()}
    for c in geo.channel_id.astype(int):
        n_units.setdefault(int(c), 0)
        max_amp.setdefault(int(c), 0.0)

    fig = plt.figure(figsize=(23, 13.5))
    outer = GridSpec(2, 2, figure=fig, width_ratios=[0.82, 2.0],
                     height_ratios=[1.05, 1.0], wspace=0.10, hspace=0.10,
                     left=0.028, right=0.972, top=0.935, bottom=0.035)
    panel_table(fig.add_subplot(outer[0, 0]), meta, geo, by_ch, free)
    panel_waveforms(fig, outer[:, 1], geo, by_ch, free["sr"], ylim)

    inner = GridSpecFromSubplotSpec(2, 1, subplot_spec=outer[1, 0],
                                    hspace=0.30)
    panel_grid(fig.add_subplot(inner[0, 0]), geo, n_units,
               "3 · units per electrode", UNITS_CLIM, "{:.0f}")
    panel_grid(fig.add_subplot(inner[1, 0]), geo, max_amp,
               "4 · max unit amplitude (uV p2p)", AMP_CLIM, "{:.0f}")

    fig.suptitle(
        f"{meta['subject']} {meta['implant']} {meta['array']}  ·  "
        f"{meta['date']}  ·  {meta['chain'] or 'original'}  "
        f"({CHAIN_LABEL.get(meta['chain'], 'unruled')})   |   "
        f"panel 2 and the grids are at PHYSICAL array positions, "
        f"pad-side view, from {geo.attrs['cmp']}   |   "
        f"grey X = no electrode wired; black = electrode present, no units",
        fontsize=11.5, y=0.975)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=125)
    plt.close(fig)
    return out


def build_worklist(inv: pd.DataFrame, chain: str | None,
                   stem: str | None, include_sweep: bool = False) -> list[dict]:
    """Recordings to render. ``chain=None`` means every variant that exists."""
    nev = inv[(inv.role == "snippets") & inv.excluded.isna()]
    if not include_sweep:
        # The OFS algorithm sweep is eight runs of the same 78 sessions and
        # would multiply the output eightfold for one subject.
        nev = nev[~nev.folder.str.contains("OFS sorting test", na=False)]
    if chain is not None:
        nev = nev[nev.chain == chain]
    if stem:
        nev = nev[nev.stem == stem]
    jobs = []
    for r in nev.itertuples():
        if pd.isna(r.date) or r.array is None:
            continue
        jobs.append(dict(path=str(MONKEY_ROOT / r.rel), stem=r.stem,
                         subject=r.subject, implant=r.implant, array=r.array,
                         date=r.date.date(), chain=r.chain,
                         folder=r.folder, headstage=r.headstage))

    # Tag only the ones that would collide, so the common case keeps a clean
    # filename and the ambiguous case is visible in the name.
    from collections import Counter
    key = Counter((j["subject"], j["stem"], j["chain"]) for j in jobs)
    for j in jobs:
        if key[(j["subject"], j["stem"], j["chain"])] > 1:
            j["tag"] = (Path(j["folder"]).name or "root").replace(" ", "_")
    return jobs


def preview_path(job: dict) -> Path:
    """Output path, disambiguated when two files share a stem and chain.

    Two recordings in different folders can carry the same name and different
    content -- `Nigel_Posterior_2023-03-17...-02.nev` exists in both
    `NEV/Curated/DS Curated` and `NEV/Posterior/sorted` with different md5s.
    Without the suffix one silently overwrites the other and the figure set
    quietly loses a sort.
    """
    tag = f"__{job['tag']}" if job.get("tag") else ""
    return (FIG_ROOT / job["subject"].lower() / "session_preview" /
            f"{job['stem']}{job['chain']}{tag}.png")


def render_one(job: dict) -> str:
    """Worker entry: one figure, errors reported rather than raised."""
    out = preview_path(job)
    try:
        make_preview(job, out)
        return out.name
    except Exception as exc:  # noqa: BLE001
        return f"FAILED {out.name}: {type(exc).__name__}: {exc}"[:140]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", default=None,
                    help="one variant, e.g. -01; default is every variant")
    ap.add_argument("--include-sweep", action="store_true",
                    help="also render the Nigel OFS algorithm sweep")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--stem", default=None)
    ap.add_argument("--force", action="store_true",
                    help="re-render figures that already exist")
    ap.add_argument("--ylim", type=float, default=WAVE_YLIM_UV,
                    help="panel 2 y half-range in uV, fixed for every panel")
    args = ap.parse_args()

    inv = pd.read_parquet(INV)
    jobs = build_worklist(inv, args.chain, args.stem, args.include_sweep)
    banner("Session previews")
    print(f"  recordings to render: {len(jobs)}")
    if not jobs:
        return 1
    print(pd.Series([f"{j['subject']} {j['chain'] or '(original)'}"
                     for j in jobs]).value_counts().to_string())
    tagged = [j for j in jobs if j.get("tag")]
    if tagged:
        print(f"\n  {len(tagged)} recordings share a stem+variant with "
              f"another file and are disambiguated by folder:")
        for j in sorted(tagged, key=lambda x: x["stem"]):
            print(f"      {j['stem']}{j['chain']}  <- {j['folder']}")
    if args.limit and not args.stem:
        df = pd.DataFrame(jobs)
        jobs = (df.sort_values("date").groupby("subject").head(1)
                .head(args.limit).to_dict("records"))

    todo = [j for j in jobs if not preview_path(j).exists() or args.force]
    print(f"\n  already present: {len(jobs) - len(todo)}   "
          f"to render: {len(todo)}")
    if not todo:
        return 0
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for i, msg in enumerate(ex.map(render_one, todo, chunksize=1), 1):
            if i % 25 == 0 or i == len(todo):
                print(f"    [{i}/{len(todo)}] {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

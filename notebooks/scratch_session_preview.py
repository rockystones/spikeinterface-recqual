"""One "session preview" figure per recording: everything about it on one page.

Four panels, following the conventions in the owner's MATLAB
(`Monkey Data/Older code/plot_U01_Utaharray_*.m`) except where noted:

  1  metrics table -- identity, method and parameters, sorting results,
     sorting-based ephys metrics, sorting quality, sorting-free metrics
  2  per-unit waveforms, one axes per electrode, **arranged at the array's
     physical positions** rather than by channel index
  3  units-per-electrode grid at physical positions
  4  peak-to-peak amplitude grid at physical positions

Conventions carried over from the MATLAB, deliberately:

- `Color_book`, the same ten unit colours.
- `Min_P2P_exclusion = 20 uV`: a unit whose *mean* waveform is flatter than
  this is not drawn.
- Unit amplitude is the peak-to-peak of the **mean** waveform, and a channel's
  amplitude is the largest unit on it.
- The shaded band is the full min-to-max envelope of that unit's waveforms at
  each sample -- not a standard deviation.
- `hot` colormap on the grids, absent electrodes in dark grey, values printed.

The one deliberate departure is panel 2's arrangement, which is the point of
this figure. The MATLAB laid channels out in index order and its own comment
says so: *"The channel index here is for the Blackrock recording file channel
index, NOT the elec# !!! Remap later."* Its later grid code fixes this, with
the earlier attempt left in place commented *"This is the old code that mapped
the location using elec not the chan, which is WRONG!"* -- the same
channel-versus-electrode distinction settled in `channel_mapping.md`. Here the
`.cmp` carries both for each contact, so the lookup is direct.

Run from repo root:

    uv run python notebooks/scratch_session_preview.py --limit 2
    uv run python notebooks/scratch_session_preview.py --stem <stem> --chain -01

See:
- docs/notes/session_preview.md
- docs/notes/channel_mapping.md
"""

from __future__ import annotations

import argparse
import sys
import warnings
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

# The MATLAB Color_book, /255. Ten colours because a channel rarely carries
# more than a few units and the palette must stay distinguishable at this size.
COLOR_BOOK = np.array([
    [158, 1, 66], [78, 98, 171], [135, 207, 164], [214, 64, 78],
    [245, 117, 71], [253, 185, 106], [254, 232, 154], [245, 251, 177],
    [203, 233, 157], [70, 158, 180],
]) / 255.0

MIN_P2P_UV = 20.0          # MATLAB Min_P2P_exclusion
NOT_A_UNIT = (0, 255)      # 0 unsorted, 255 noise
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
    drawn = {c: [u for u in us if u["p2p"] >= MIN_P2P_UV]
             for c, us in by_ch.items()}
    n_units = sum(len(v) for v in drawn.values())
    n_declared = sum(len(v) for v in by_ch.values())
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
        ("  parameters", meta.get("params", "Plexon OFS; settings not in file")),
        ("", ""),
        ("SORTING RESULT", ""),
        ("  units declared", f"{n_declared}"),
        (f"  units drawn (p2p>={MIN_P2P_UV:.0f} uV)", f"{n_units}"),
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
        ("  drawn / declared", f"{n_units / max(n_declared, 1):.0%}"),
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
    y = 1.0
    for k, v in rows:
        bold = k and not k.startswith(" ")
        ax.text(0.0, y, k, fontsize=7.6, family="monospace",
                weight="bold" if bold else "normal",
                color="#1a1a1a" if bold else "#333333",
                transform=ax.transAxes, va="top")
        if v:
            ax.text(0.62, y, v, fontsize=7.6, family="monospace",
                    transform=ax.transAxes, va="top")
        y -= 0.0228


def panel_waveforms(fig, spec, geo: pd.DataFrame, by_ch: dict, sr: float,
                    yscale: str = "per-panel") -> None:
    """Panel 2: one axes per contact, laid out at its physical position.

    ``yscale="per-panel"`` matches the MATLAB reference and shows waveform
    *shape* on every electrode, including quiet ones. ``"shared"`` puts every
    panel on one scale so magnitudes are comparable by eye, at the cost of
    flattening small units into a line. Shape and magnitude are separated on
    purpose: panel 4 carries the magnitudes spatially, so panel 2 does not
    have to.
    """
    n_col = int(geo.col.max() - geo.col.min() + 1)
    n_row = int(geo.row.max() - geo.row.min() + 1)
    gs = GridSpecFromSubplotSpec(n_row, n_col, subplot_spec=spec,
                                 hspace=0.62, wspace=0.34)
    c0, r0 = int(geo.col.min()), int(geo.row.min())

    allv = [u["hi"].max() for us in by_ch.values() for u in us] + \
           [u["lo"].min() for us in by_ch.values() for u in us]
    shared_max = max(float(np.nanpercentile(np.abs(allv), 98)), 30.0) \
        if allv else 100.0

    for r in geo.itertuples():
        # CMP rows count up from the bottom, so invert for a pad-side view.
        gr = (n_row - 1) - (int(r.row) - r0)
        gc = int(r.col) - c0
        ax = fig.add_subplot(gs[gr, gc])
        units = [u for u in by_ch.get(int(r.channel_id), [])
                 if u["p2p"] >= MIN_P2P_UV]
        for i, u in enumerate(units):
            col = COLOR_BOOK[i % len(COLOR_BOOK)]
            t = np.arange(len(u["mean"])) / sr * 1000.0    # ms
            ax.fill_between(t, u["lo"], u["hi"], color=col, alpha=0.16, lw=0)
            ax.plot(t, u["mean"], color=col, lw=0.9)

        if yscale == "shared" or not units:
            ymax = shared_max
        else:
            span = max(max(u["hi"].max() for u in units),
                       -min(u["lo"].min() for u in units))
            ymax = float(span) * 1.08
        ax.set_ylim(-ymax, ymax)
        ax.axhline(0, color="#bbbbbb", lw=0.3, zorder=0)
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_linewidth(0.4)
            s.set_color("#888888" if units else "#e0e0e0")
        ax.set_title(f"ch{int(r.channel_id)}·{r.label}", fontsize=4.4,
                     pad=1.0, color="#222222" if units else "#aaaaaa")
        if yscale != "shared" and units:
            # The scale is per-panel, so it has to be readable per panel.
            ax.text(0.97, 0.04, f"{ymax:.0f}", transform=ax.transAxes,
                    fontsize=3.9, color="#777777", ha="right", va="bottom")
    note = (f"all panels share y = +/-{shared_max:.0f} uV"
            if yscale == "shared"
            else "y is per panel; the number in each corner is that panel's "
                 "+/- limit in uV")
    fig.text(0.995, 0.5, note, rotation=90, va="center", ha="right",
             fontsize=6.5, color="#666666")


def panel_grid(ax, geo: pd.DataFrame, values: dict, title: str,
               fmt: str = "{:.0f}") -> None:
    """Panels 3 and 4: a value per contact, at its physical position."""
    n_col = int(geo.col.max() - geo.col.min() + 1)
    n_row = int(geo.row.max() - geo.row.min() + 1)
    c0, r0 = int(geo.col.min()), int(geo.row.min())
    grid = np.full((n_row, n_col), np.nan)
    for r in geo.itertuples():
        gr = (n_row - 1) - (int(r.row) - r0)
        grid[gr, int(r.col) - c0] = values.get(int(r.channel_id), np.nan)

    finite = grid[np.isfinite(grid)]
    vmin, vmax = (float(finite.min()), float(finite.max())) if finite.size \
        else (0.0, 1.0)
    if vmin == vmax:
        vmax = vmin + 1.0
    cmap = matplotlib.colormaps["hot"].copy()
    cmap.set_bad("#3a3a3a")                      # MATLAB's dark-grey NaN
    im = ax.imshow(np.ma.masked_invalid(grid), cmap=cmap,
                   norm=Normalize(vmin, vmax), aspect="equal")
    for i in range(n_row):
        for j in range(n_col):
            v = grid[i, j]
            if not np.isfinite(v):
                continue
            shade = (v - vmin) / (vmax - vmin)
            ax.text(j, i, fmt.format(v), ha="center", va="center",
                    fontsize=5.4, color="black" if shade > 0.55 else "white")
    ax.set_xticks(range(n_col))
    ax.set_xticklabels(range(c0, c0 + n_col), fontsize=6)
    ax.set_yticks(range(n_row))
    ax.set_yticklabels(range(r0 + n_row - 1, r0 - 1, -1), fontsize=6)
    ax.set_title(title, fontsize=9)
    plt.colorbar(im, ax=ax, fraction=0.045, pad=0.03).ax.tick_params(
        labelsize=6)


# %%
# === Assembly ===
def make_preview(meta: dict, out: Path, yscale: str = "per-panel") -> Path:
    geo = load_geometry(meta["subject"], meta["array"], meta["implant"])
    by_ch, free = session_units(Path(meta["path"]))

    drawn = {c: [u for u in us if u["p2p"] >= MIN_P2P_UV]
             for c, us in by_ch.items()}
    n_units = {c: len(v) for c, v in drawn.items()}
    # A channel's amplitude is its largest unit, as in the MATLAB.
    max_amp = {c: (max(u["p2p"] for u in v) if v else np.nan)
               for c, v in drawn.items()}

    fig = plt.figure(figsize=(23, 13.5))
    outer = GridSpec(2, 2, figure=fig, width_ratios=[0.82, 2.0],
                     height_ratios=[1.05, 1.0], wspace=0.10, hspace=0.10,
                     left=0.028, right=0.972, top=0.935, bottom=0.035)
    panel_table(fig.add_subplot(outer[0, 0]), meta, geo, by_ch, free)
    panel_waveforms(fig, outer[:, 1], geo, by_ch, free["sr"], yscale)

    inner = GridSpecFromSubplotSpec(2, 1, subplot_spec=outer[1, 0],
                                    hspace=0.30)
    panel_grid(fig.add_subplot(inner[0, 0]), geo, n_units,
               "3 · units per electrode", "{:.0f}")
    panel_grid(fig.add_subplot(inner[1, 0]), geo, max_amp,
               "4 · max unit amplitude (uV p2p)", "{:.0f}")

    fig.suptitle(
        f"{meta['subject']} {meta['implant']} {meta['array']}  ·  "
        f"{meta['date']}  ·  {meta['chain'] or 'original'}  "
        f"({CHAIN_LABEL.get(meta['chain'], 'unruled')})   |   "
        f"panel 2 and the grids are at PHYSICAL array positions, "
        f"pad-side view, from {geo.attrs['cmp']}",
        fontsize=11.5, y=0.975)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=125)
    plt.close(fig)
    return out


def build_worklist(inv: pd.DataFrame, chain: str,
                   stem: str | None) -> list[dict]:
    nev = inv[(inv.role == "snippets") & (inv.chain == chain)
              & (~inv.folder.str.contains("OFS sorting test", na=False))]
    if stem:
        nev = nev[nev.stem == stem]
    jobs = []
    for r in nev.itertuples():
        if pd.isna(r.date) or r.array is None:
            continue
        jobs.append(dict(path=str(MONKEY_ROOT / r.rel), stem=r.stem,
                         subject=r.subject, implant=r.implant, array=r.array,
                         date=r.date.date(), chain=r.chain,
                         headstage=r.headstage))
    return jobs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", default="-01", help="variant to render")
    ap.add_argument("--limit", type=int, default=2)
    ap.add_argument("--stem", default=None)
    ap.add_argument("--yscale", choices=("per-panel", "shared"),
                    default="per-panel",
                    help="panel 2 y axis; per-panel matches the MATLAB")
    args = ap.parse_args()

    inv = pd.read_parquet(INV)
    jobs = build_worklist(inv, args.chain, args.stem)
    banner("Session previews")
    print(f"  candidates for chain {args.chain!r}: {len(jobs)}")
    if not jobs:
        return 1
    if args.limit and not args.stem:
        # One good session from each of two subjects, so the example shows
        # both a dense array and a sparse one.
        df = pd.DataFrame(jobs)
        pick = (df.sort_values("date").groupby("subject").head(1)
                .head(args.limit))
        jobs = pick.to_dict("records")

    for j in jobs:
        out = (FIG_ROOT / j["subject"].lower() / "session_preview" /
               f"{j['stem']}{j['chain']}.png")
        print(f"  {j['subject']:6s} {j['array']:10s} {j['date']}  -> "
              f"{out.name}")
        make_preview(j, out, args.yscale)
        print(f"      wrote {out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

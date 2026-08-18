"""Session preview figures for the TDT corpus.

Same four panels as `scratch_session_preview.py` -- metrics table, per-channel
waveforms, units grid, amplitude grid -- and the panel drawing code is imported
from there rather than copied, so a change to the layout lands in both.

**One thing is different and it is stamped on every figure.** The Blackrock
previews lay panels 2-4 out at *physical* array positions, read from the
array's `.cmp`. That is not possible here: the CMP maps a Blackrock bank/pin to
an electrode, and how a TDT headstage's channel 1-96 wires onto the same array
is a separate fact the tank does not record. Guessing it would be exactly the
silent, ruinous channel-order mismatch CLAUDE.md warns about.

So these figures lay out **in TDT channel-index order on a 10x10 grid**, and
say so in the title, in the table and in the axis label. Nothing about panel 1
or the waveforms themselves depends on the layout; only the *position* of each
small panel is provisional. When the wiring is known, re-running with a real
mapfile is a one-line change to `channel_grid()`.

For the same reason arrays are named by store number (`eNe1` -> array 1), not
by anatomy. The serials are registered per subject, but which store is the
anterior array is not known, so no figure claims one.

Run from repo root:

    uv run python notebooks/scratch_tdt_preview.py [--subject Oops]
                                                   [--sample 0] [--jobs 3]

Writes `figures/<subject>/tdt_preview/<block>__a<array>__<method>.png`
(gitignored).

See:
- docs/notes/session_preview.md
- docs/notes/tdt_corpus.md
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
warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_cohort_io import array_serial  # noqa: E402
from scratch_rocky_resort import baseline_noise_uv  # noqa: E402
from scratch_session_preview import (  # noqa: E402
    AMP_CLIM,
    CHAIN_LABEL,
    UNITS_CLIM,

    panel_grid,
    panel_table,
    panel_waveforms,
)
from scratch_tdt_io import (  # noqa: E402
    channel_index,
    detect_nbefore,
    open_tank,
    read_channel,
    sort_names,
)

INV = REPO / "data" / "derived" / "tdt_inventory.parquet"
FIG_ROOT = REPO / "figures"

# TDT OpenSorter's outlier bin, and the unsorted code. Neither is a unit.
NOT_A_UNIT = (0, 31)
# Waveform y range for TDT, fixed across figures for comparability but set
# well below the Blackrock previews' +/-200 uV. TDT unit amplitudes here run
# ~40 uV median peak-to-peak against several hundred on Blackrock, so +/-200
# would collapse the typical unit to a flat line -- the one failure mode the
# owner explicitly ruled out. A large unit running off the top is accepted.
TDT_WAVE_YLIM_UV = 75.0
# Grid side for the channel-index layout. 96 channels on a 10x10 leaves four
# cells empty, exactly as a Utah array does -- but which four is arbitrary
# here, so the empties are drawn as "no channel" rather than as vacant pads.
GRID_SIDE = 10

# The imported table helper looks its method label up in this dict. TDT
# methods are not Blackrock suffix chains, so they are registered here rather
# than by duplicating the whole panel.
CHAIN_LABEL.update({
    "online": "TDT online discriminator (accept flag, not a unit id)",
    "": "TDT online discriminator (accept flag, not a unit id)",
})


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === Geometry stand-in ===
def channel_grid(n_channels: int, side: int = GRID_SIDE) -> pd.DataFrame:
    """A `geo`-shaped frame laying channels out in index order.

    Same columns the real mapfile path produces -- `col`, `row`,
    `channel_id`, `label` -- so every panel function works unchanged. `row` is
    counted up from the bottom to match the CMP convention the panels assume.

    This is **not** physical position. It is a deterministic placeholder so the
    figure can be drawn at all, and every caller stamps that on the output.
    """
    rows = []
    for i in range(n_channels):
        ch = i + 1
        r, c = divmod(i, side)
        rows.append(dict(channel_id=ch, col=c, row=side - 1 - r,
                         label=f"idx{ch}"))
    d = pd.DataFrame(rows)
    d.attrs["cmp"] = "CHANNEL-INDEX ORDER (physical map unknown)"
    return d


# %%
# === Per-channel units ===
def tdt_session_units(tev: Path, array: int,
                      sortname: str = "") -> tuple[dict, dict]:
    """Per-channel unit waveforms plus the sorting-free numbers, for one array.

    Mirrors `scratch_session_preview.session_units`, including the shape of
    both return values, so the panels need no TDT-specific branch.

    With `sortname` empty the labels are the online sortcode, which on Oops and
    Picasso is an accept flag rather than a unit id -- at most one "unit" per
    channel. That is a true picture of what the online sorter produced, and the
    figure says which method it is showing.
    """
    io, meta = open_tank(tev, sortname=sortname)
    store = f"eNe{array}"
    idx = channel_index(io)
    nbefore = detect_nbefore(io, meta, store, idx)
    dur = meta["duration_s"]
    sr = meta["sr_by_store"].get(store, meta["sr"])

    by_channel: dict[int, list[dict]] = {}
    noises, counts, amps, snrs = [], [], [], []
    for (st, ch), units in sorted(idx.items()):
        if st != store:
            continue
        e = read_channel(io, meta, units)
        if e is None or not len(e["t"]):
            continue
        wf, code = e["wf"], e["code"]
        noise = baseline_noise_uv(wf, nbefore)
        trough = np.abs(wf.min(axis=1))
        noises.append(noise)
        counts.append(len(wf))
        amps.append(trough)
        if noise > 0:
            snrs.append(float(np.median(trough) / noise))

        out = []
        for u in sorted(set(code.tolist()) - set(NOT_A_UNIT)):
            sel = code == u
            if sel.sum() < 2:
                continue
            w = wf[sel]
            mean = w.mean(axis=0)
            out.append(dict(
                unit=int(u), n=int(sel.sum()), mean=mean,
                lo=w.min(axis=0), hi=w.max(axis=0),
                # Peak-to-peak of the MEAN waveform, matching the MATLAB and
                # the Blackrock previews, not the spread of the cloud.
                p2p=float(mean.max() - mean.min()),
                noise=noise,
            ))
        by_channel[int(ch)] = out

    allamp = np.concatenate(amps) if amps else np.array([0.0])
    free = dict(
        duration_s=dur, sr=sr, nbefore=nbefore,
        n_elec_active=len(counts), n_crossings=int(sum(counts)),
        crossing_rate_hz=float(sum(counts) / dur / max(len(counts), 1))
        if dur and np.isfinite(dur) else np.nan,
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
# === Assembly ===
def make_preview(job: dict, out: Path, ylim: float = TDT_WAVE_YLIM_UV) -> Path:
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec

    tev = Path(job["tev"])
    by_ch, free = tdt_session_units(tev, job["array"], job["sortname"])
    n_chan = max(job.get("n_chan") or 96, max(by_ch, default=0))
    geo = channel_grid(n_chan)
    # The serials are known even though the wiring is not; showing both makes
    # the figure traceable to the subject's arrays without implying which one
    # this store is.
    ant = array_serial(job["subject"], "Anterior", "I1") or "-"
    post = array_serial(job["subject"], "Posterior", "I1") or "-"
    geo.attrs["serial"] = f"{ant} or {post} (store-to-array not yet known)"

    n_units = {int(c): len(v) for c, v in by_ch.items()}
    max_amp = {int(c): (max(u["p2p"] for u in v) if v else 0.0)
               for c, v in by_ch.items()}
    for c in geo.channel_id.astype(int):
        n_units.setdefault(int(c), 0)
        max_amp.setdefault(int(c), 0.0)

    meta = dict(subject=job["subject"], implant="I1",
                array=f"{job['array']} (store eNe{job['array']})",
                date=job["date"], headstage="-",
                chain=job["method"],
                params=job.get("params", "TDT online threshold; "
                                         "40-sample snippets"))
    fig = plt.figure(figsize=(23, 13.5))
    outer = GridSpec(2, 2, figure=fig, width_ratios=[0.82, 2.0],
                     height_ratios=[1.05, 1.0], wspace=0.10, hspace=0.10,
                     left=0.028, right=0.972, top=0.935, bottom=0.035)
    panel_table(fig.add_subplot(outer[0, 0]), meta, geo, by_ch, free)
    panel_waveforms(fig, outer[:, 1], geo, by_ch, free["sr"], ylim)

    inner = GridSpecFromSubplotSpec(2, 1, subplot_spec=outer[1, 0],
                                    hspace=0.30)
    panel_grid(fig.add_subplot(inner[0, 0]), geo, n_units,
               "3 · units per channel (index order)", UNITS_CLIM, "{:.0f}")
    panel_grid(fig.add_subplot(inner[1, 0]), geo, max_amp,
               "4 · max unit amplitude (uV p2p), index order", AMP_CLIM,
               "{:.0f}")

    fig.suptitle(
        f"{job['subject']}  ·  {job['block']}  ·  array {job['array']} "
        f"(eNe{job['array']})  ·  {job['date']}  ·  method: {job['method']}"
        f"   |   WARNING: panel 2 and the grids are in TDT CHANNEL-INDEX "
        f"order, NOT physical array position -- the headstage wiring is not "
        f"recorded in the tank   |   grey X = no channel at this cell; "
        f"black = channel present, no units",
        fontsize=11.5, y=0.975)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=125)
    plt.close(fig)
    return out


def preview_path(job: dict) -> Path:
    return (FIG_ROOT / job["subject"] / "tdt_preview"
            / f"{job['block']}__a{job['array']}__{job['method']}.png")


def render_one(job: dict) -> str:
    out = preview_path(job)
    if out.exists() and not job.get("force"):
        return f"cached {out.name}"
    try:
        make_preview(job, out)
        return f"ok      {out.name}"
    except Exception as exc:  # noqa: BLE001
        return f"FAIL    {job['block']} a{job['array']} " \
               f"{job['method']}: {type(exc).__name__}: {exc}"[:160]


# %%
# === Worklist ===
def build_worklist(inv: pd.DataFrame, subject: str = "",
                   sample: int = 0, force: bool = False) -> list[dict]:
    """One job per (block, array, method).

    Methods are the online sortcode plus every offline sort that covers this
    array -- the same "all the variants" rule the Blackrock previews follow.
    """
    live = inv[inv.live & inv.excluded.isna()]
    if subject:
        live = live[live.subject == subject]
    jobs: list[dict] = []
    for _, r in live.iterrows():
        block = Path(r["path"])
        base = dict(
            tev=str(block / f"{r['stem']}.tev"), path=r["path"],
            subject=r["subject"], block=r["block"], date=r["date"],
            array=int(r["array"]), n_chan=int(r["n_chan_declared"]),
            force=force,
        )
        jobs.append(dict(**base, method="online", sortname=""))
        for name in sort_names(block):
            # A .SortResult covers exactly one store; applying it to the other
            # array would render an all-zero sort as "no units found".
            if any((block / "sort" / name).glob(f"eNe{r['array']}.SortResult")):
                jobs.append(dict(**base, method=name, sortname=name))
    if sample:
        jobs = _spread(jobs, sample)
    return jobs


def _spread(jobs: list[dict], n: int) -> list[dict]:
    """Keep n jobs per subject, spread evenly by date."""
    out: list[dict] = []
    by_subject: dict[str, list[dict]] = {}
    for job in jobs:
        by_subject.setdefault(job["subject"], []).append(job)
    for group in by_subject.values():
        group = sorted(group, key=lambda j: (j["date"] or "", j["block"]))
        if len(group) <= n:
            out.extend(group)
            continue
        idx = np.unique(np.linspace(0, len(group) - 1, n).round().astype(int))
        out.extend(group[i] for i in idx)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    inv = pd.read_parquet(INV)
    jobs = build_worklist(inv, args.subject, args.sample, args.force)
    if args.limit:
        jobs = jobs[:args.limit]
    banner("TDT session previews")
    print(f"  figures to render: {len(jobs)}")
    print(pd.DataFrame(jobs).groupby(["subject", "method"]).size()
          .rename("figures").to_string())
    print("\n  NOTE: laid out in channel-index order, not physical position.")

    ok = fail = 0
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for i, msg in enumerate(ex.map(render_one, jobs, chunksize=1), 1):
            if msg.startswith("FAIL"):
                fail += 1
                print(f"  {msg}")
            else:
                ok += 1
            if i % 25 == 0:
                print(f"    {i}/{len(jobs)}  ok={ok} fail={fail}")
    print(f"\n  rendered {ok}, failed {fail}")
    print(f"  under {FIG_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

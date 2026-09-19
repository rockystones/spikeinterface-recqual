"""ISO-SPLIT (resort) session previews for the outlier candidates.

The standard previews in figures/rocky/outlier_preview/ draw the
Plexon OFS unit labels embedded in the -01 NEV. This script renders a
second page per candidate from the project's OWN resort - the same
pipeline as scratch_rocky_resort.py / units_long.parquet:

  original (unsorted) NEV snippets -> per electrode: baseline-MAD
  noise, trough re-alignment (+/-2 samples), PCA-5, ISO-SPLIT
  (isosplit6), physics gate (SNR>=4, >=50 spikes, peak-trough
  0.15-1.20 ms, trough within +/-0.20 ms).

GATED clusters only are drawn and counted (method 'resort_gated' in
two_array_metrics); the panel-1 table therefore reads lower than the
OFS page on late sessions, which is the point of the comparison. The
full cluster count is in the suptitle; the per-cluster reject audit
lives in figures/rocky/09_gate_audit_*.

Outputs
- figures/rocky/outlier_preview_isosplit/<stem>__isosplit.png
  (same four panels, physical array positions, same fixed scales)
- per-stem MATLAB layer added to data/derived/rocky/outlier_inspect/
  <stem>/: units_iso.parquet + wf_mean_iso/lo/hi.parquet, row-aligned
  exactly like the OFS files. rocky_outlier_inspect.m picks the layer
  with opts.method = 'ofs' (default) or 'isosplit'.

Run: uv run python notebooks/scratch_outlier_isosplit.py [--jobs 4]
"""

from __future__ import annotations

import argparse
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec  # noqa: E402
from sklearn.decomposition import PCA  # noqa: E402

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scratch_outlier_inspect import candidates  # noqa: E402
from scratch_rocky_resort import (  # noqa: E402
    N_PCA, align_on_trough, baseline_noise_uv, cluster_snippets,
    load_snippets, unit_metrics)
from scratch_session_preview import (  # noqa: E402
    AMP_CLIM, UNITS_CLIM, WAVE_YLIM_UV, build_worklist, load_geometry,
    panel_grid, panel_table, panel_waveforms)

REPO = Path(__file__).resolve().parent.parent
DER = REPO / "data" / "derived"
OUT_FIG = REPO / "figures" / "rocky" / "outlier_preview_isosplit"
OUT_DATA = DER / "rocky" / "outlier_inspect"


def isosplit_units(nev: Path) -> tuple[dict, dict, int, int]:
    """Resort one NEV; gated clusters in session_units() shape.

    Returns (by_channel, free, n_clusters_total, n_gated). by_channel
    matches scratch_session_preview.session_units so the same panel
    functions render it; waveform mean/envelope are of the ALIGNED
    snippets (the clusters were formed on aligned waveforms).
    """
    data = load_snippets(nev)
    sr, nbefore, dur = data["sr"], data["nbefore"], data["duration_s"]
    by_channel: dict[int, list[dict]] = {}
    noises, counts, amps, snrs = [], [], [], []
    n_total = n_gated = 0

    for elec, e in sorted(data["by_elec"].items()):
        wf, t = e["wf"], e["t"]
        if not len(t):
            continue
        noise = baseline_noise_uv(wf, nbefore)
        trough = np.abs(wf.min(axis=1))
        noises.append(noise)
        counts.append(len(wf))
        amps.append(trough)
        if noise > 0:
            snrs.append(float(np.median(trough) / noise))

        units = []
        if len(t) >= 50:                      # resort's MIN_SPIKES
            wf_al = align_on_trough(wf, nbefore)
            n_pc = min(N_PCA, wf_al.shape[1], max(2, len(wf_al) - 1))
            feats = PCA(n_components=n_pc,
                        random_state=0).fit_transform(wf_al)
            labels = cluster_snippets(feats)
            for k in np.unique(labels):
                sel = labels == k
                n_total += 1
                m = unit_metrics(wf_al[sel], t[sel], noise, sr,
                                 nbefore, dur)
                if not m["pass_gate"]:
                    continue
                n_gated += 1
                w = wf_al[sel]
                mean = w.mean(axis=0)
                units.append(dict(
                    unit=int(k) + 1, n=int(sel.sum()), mean=mean,
                    lo=w.min(axis=0), hi=w.max(axis=0),
                    p2p=float(mean.max() - mean.min()), noise=noise))
        by_channel[int(elec)] = units

    allamp = np.concatenate(amps) if amps else np.array([0.0])
    free = dict(
        duration_s=dur, sr=sr, nbefore=nbefore,
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
    return by_channel, free, n_total, n_gated


def render_iso(job: dict) -> str:
    """One ISO-SPLIT preview + the MATLAB layer files."""
    stem = job["stem"]
    out = OUT_FIG / f"{stem}__isosplit.png"
    try:
        geo = load_geometry(job["subject"], job["array"],
                            job["implant"])
        by_ch, free, n_total, n_gated = isosplit_units(
            Path(job["path"]))

        # MATLAB layer, row-aligned like the OFS bundle files
        pos = geo.set_index("channel_id")[["col", "row"]]
        rows, means, los, his = [], [], [], []
        for ch, units in sorted(by_ch.items()):
            for u in units:
                rows.append(dict(
                    channel_id=ch,
                    col=int(pos.loc[ch, "col"]) if ch in pos.index
                    else -1,
                    row=int(pos.loc[ch, "row"]) if ch in pos.index
                    else -1,
                    unit=u["unit"], n_spikes=u["n"], p2p_uv=u["p2p"],
                    noise_uv=u["noise"]))
                means.append(u["mean"]); los.append(u["lo"])
                his.append(u["hi"])
        folder = OUT_DATA / stem
        if folder.exists():
            pd.DataFrame(rows).to_parquet(folder / "units_iso.parquet",
                                          index=False)
            n_samp = len(means[0]) if means else 0
            for name, arr in (("wf_mean_iso", means),
                              ("wf_lo_iso", los), ("wf_hi_iso", his)):
                m = (np.asarray(arr, dtype=np.float32) if arr else
                     np.zeros((0, n_samp), np.float32))
                pd.DataFrame(
                    m, columns=[f"s{i:03d}" for i in range(m.shape[1])]
                ).to_parquet(folder / f"{name}.parquet", index=False)

        # figure: same layout as make_preview, resort layer
        n_units = {int(c): len(v) for c, v in by_ch.items()}
        max_amp = {int(c): (max(u["p2p"] for u in v) if v else 0.0)
                   for c, v in by_ch.items()}
        for c in geo.channel_id.astype(int):
            n_units.setdefault(int(c), 0)
            max_amp.setdefault(int(c), 0.0)
        fig = plt.figure(figsize=(23, 13.5))
        outer = GridSpec(2, 2, figure=fig, width_ratios=[0.82, 2.0],
                         height_ratios=[1.05, 1.0], wspace=0.10,
                         hspace=0.10, left=0.028, right=0.972,
                         top=0.935, bottom=0.035)
        panel_table(fig.add_subplot(outer[0, 0]), job, geo, by_ch,
                    free)
        panel_waveforms(fig, outer[:, 1], geo, by_ch, free["sr"],
                        WAVE_YLIM_UV)
        inner = GridSpecFromSubplotSpec(2, 1,
                                        subplot_spec=outer[1, 0],
                                        hspace=0.30)
        panel_grid(fig.add_subplot(inner[0, 0]), geo, n_units,
                   "3 · gated units per electrode", UNITS_CLIM,
                   "{:.0f}")
        panel_grid(fig.add_subplot(inner[1, 0]), geo, max_amp,
                   "4 · max unit amplitude (uV p2p)", AMP_CLIM,
                   "{:.0f}")
        fig.suptitle(
            f"{job['subject']} {job['implant']} {job['array']}  ·  "
            f"{job['date']}  ·  ISO-SPLIT resort, GATED units only "
            f"({n_gated} of {n_total} clusters pass; SNR>=4, >=50 "
            f"spikes, shape)   |   panels at PHYSICAL array positions "
            f"from {geo.attrs['cmp']}", fontsize=11.5, y=0.975)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=125)
        plt.close(fig)
        return f"{out.name}: {n_gated}/{n_total} gated"
    except Exception as exc:  # noqa: BLE001
        return f"FAILED {out.name}: {type(exc).__name__}: {exc}"[:140]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    inv = pd.read_parquet(DER / "monkey_inventory.parquet")
    jobs = []
    for stem in candidates():
        wl = build_worklist(inv, "", stem)   # resort input = original
        if wl:
            jobs.append(wl[0])
        else:
            print(f"  no original NEV for {stem}")
    if not args.force:
        jobs = [j for j in jobs if not
                (OUT_FIG / f"{j['stem']}__isosplit.png").exists()]
    print(f"{len(jobs)} sessions to resort+render")
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for i, msg in enumerate(ex.map(render_iso, jobs,
                                       chunksize=1), 1):
            print(f"  [{i}/{len(jobs)}] {msg}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

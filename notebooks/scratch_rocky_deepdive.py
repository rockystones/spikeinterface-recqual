"""Per-file deep dive: what the units actually look like, by method and over time.

Takes one anterior/posterior pair at each of three timepoints and renders, for
every sorting method plus Plexon:

* an **array overview** -- gate-passing units per electrode on the 10x10 grid,
  one panel per method, both arrays, so over- and under-splitting are visible
  spatially;
* a **channel detail** -- one representative electrode shown four ways
  (waveforms, PCA feature space, amplitude histogram, raster) with each
  cluster annotated by what the noise gate and UnitRefine each decided.

Timepoints were chosen as dates where both arrays have a paired ORIG/OFS file
and both still carry units, so every method has something to be compared on.
The posterior array reaches zero gate-passing units from 2023 onward, which is
why the late timepoint is 2022 rather than the end of the cohort.

Run from repo root:

    uv run python notebooks/scratch_rocky_deepdive.py [--electrode N]

See:
- docs/notes/snippet_sorting.md
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from scratch_rocky_methods import CLUSTERERS, build_row
from scratch_rocky_resort import (
    MIN_SPIKES,
    N_PCA,
    PLEXON_DROP_UNITS,
    align_on_trough,
    baseline_noise_uv,
    open_nev,
    read_electrode,
)
from sklearn.decomposition import PCA

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "derived" / "rocky"
FIG = REPO / "figures" / "rocky" / "deepdive"
INDEX_IN = OUT / "session_index.parquet"

# Both arrays paired, both still carrying units, spanning the implant lifetime.
TIMEPOINTS = [
    ("T1_early", "2017-10-30"),
    ("T2_middle", "2019-01-31"),
    ("T3_late", "2022-12-09"),
]
METHODS = ["isosplit", "gmm_bic", "hdbscan", "kmeans_sil", "ofs"]
SUBSAMPLE = 4000
GRID = 10
CLUSTER_CMAP = plt.get_cmap("tab10")

NOISE_MODEL = "SpikeInterface/UnitRefine_noise_neural_classifier"
TRUSTED = ["numpy.dtype", "sklearn.pipeline.Pipeline"]


def banner(t: str) -> None:
    print()
    print("=" * 72)
    print(t)
    print("=" * 72)


def load_unitrefine():
    """Load the noise/neural classifier, or None if unavailable.

    Returns the pipeline, the integer class meaning 'neural', and the label
    map. The map must be read from the model card: it is
    ``{'0': 'neural', '1': 'noise'}``, i.e. class 1 is noise, and assuming
    otherwise silently inverts every label.
    """
    try:
        from spikeinterface.curation import load_model

        model, info = load_model(repo_id=NOISE_MODEL, trusted=TRUSTED)
        lab = {int(k): v for k, v in info["label_conversion"].items()}
        # sklearn 1.4-era pickle under a 1.8 runtime; restore the attribute
        # SimpleImputer.transform expects (see scratch_rocky_curation.py).
        for _, step in getattr(model, "steps", []):
            if step.__class__.__name__ == "SimpleImputer" and not hasattr(
                step, "_fill_dtype"
            ):
                st = getattr(step, "statistics_", None)
                step._fill_dtype = st.dtype if st is not None else np.dtype("float64")
        return model, lab
    except Exception as e:  # noqa: BLE001
        print(f"  UnitRefine unavailable: {type(e).__name__}: {e}")
        return None, None


def ur_labels(model, lab_map, rows: list[dict]) -> list[str]:
    """Predict UnitRefine noise/neural for a list of metric rows."""
    if model is None or not rows:
        return ["n/a"] * len(rows)
    needed = list(model.feature_names_in_)
    df = pd.DataFrame(rows)
    x = pd.DataFrame(index=df.index)
    for f in needed:
        x[f] = pd.to_numeric(df[f], errors="coerce") if f in df.columns else np.nan
    try:
        return [lab_map.get(int(p), "?") for p in model.predict(x[needed])]
    except Exception:  # noqa: BLE001
        return ["n/a"] * len(rows)


def cluster_electrode(wf: np.ndarray, t: np.ndarray, pu: np.ndarray,
                      nbefore: int) -> dict:
    """Cluster one electrode every way, on an identical spike subsample.

    Returns
    -------
    dict
        ``feats``, ``wf``, ``t``, ``noise``, and ``labels`` mapping method
        name to a per-spike label array.
    """
    noise = baseline_noise_uv(wf, nbefore)
    wf_al = align_on_trough(wf, nbefore)
    n_pc = min(N_PCA, wf_al.shape[1], max(2, len(wf_al) - 1))
    feats_full = PCA(n_components=n_pc, random_state=0).fit_transform(wf_al)
    if len(feats_full) > SUBSAMPLE:
        idx = np.random.default_rng(0).choice(len(feats_full), SUBSAMPLE,
                                              replace=False)
        idx.sort()
    else:
        idx = np.arange(len(feats_full))
    feats, wf_s, t_s, pu_s = feats_full[idx], wf_al[idx], t[idx], pu[idx]

    labels: dict[str, np.ndarray] = {}
    for m, fn in CLUSTERERS.items():
        try:
            labels[m] = fn(feats)
        except Exception:  # noqa: BLE001
            labels[m] = np.ones(len(feats), dtype=int)
    labels["ofs"] = np.where(np.isin(pu_s, list(PLEXON_DROP_UNITS)), -1, pu_s)
    return dict(feats=feats, wf=wf_s, t=t_s, noise=noise, labels=labels)


def analyse_session(path: str, model, lab_map) -> tuple[dict, dict]:
    """Cluster every electrode; return per-method yield maps and per-electrode data.

    Returns
    -------
    summary : dict
        method -> {electrode_id: (n_clusters, n_passing)}
    detail : dict
        electrode_id -> the cluster_electrode() result, kept only for
        electrodes with enough units to be worth plotting.
    """
    raw, meta, cbe = open_nev(Path(path))
    sr, nbefore, dur = meta["sr"], meta["nbefore"], meta["duration_s"]
    summary = {m: {} for m in METHODS}
    detail: dict[int, dict] = {}

    for elec in sorted(cbe):
        e = read_electrode(raw, meta, cbe[elec])
        if e is None or len(e["t"]) < MIN_SPIKES:
            continue
        res = cluster_electrode(e["wf"], e["t"], e["plexon_unit"], nbefore)
        del e["wf"]
        res["meta"] = dict(sr=sr, nbefore=nbefore, duration_s=dur)

        rows_by_method: dict[str, list[dict]] = {}
        for m in METHODS:
            lab = res["labels"][m]
            ks = [k for k in np.unique(lab) if not (m == "ofs" and k == -1)]
            rows = []
            for k in ks:
                if (lab == k).sum() < 3:
                    continue
                r = build_row(res["wf"], res["t"], res["feats"], lab, k,
                              res["noise"], sr, nbefore, dur)
                r["_k"] = int(k)
                rows.append(r)
            urs = ur_labels(model, lab_map, rows)
            for r, u in zip(rows, urs, strict=True):
                r["ur"] = u
            rows_by_method[m] = rows
            summary[m][elec] = (len(rows), sum(1 for r in rows if r["pass_gate"]))
        res["rows"] = rows_by_method

        n_pass_iso = summary["isosplit"].get(elec, (0, 0))[1]
        if n_pass_iso >= 2:
            detail[elec] = res
        else:
            del res
    return summary, detail


def fig_overview(sessions: dict, date: str, out: Path) -> None:
    """Gate-passing units per electrode, every method, both arrays."""
    geo = {}
    for arr in sessions:
        cmp_path = (Path(r"D:\Claude Code\Rocky") / "preimplant" /
                    ("SN 1025-001501.cmp" if arr == "Anterior"
                     else "SN 1025-001497.cmp"))
        g = {}
        for ln in cmp_path.read_text().splitlines():
            p = ln.split()
            if len(p) >= 4 and p[0].isdigit() and p[1].isdigit() and p[3].isdigit():
                eid = (ord(p[2].upper()) - ord("A")) * 32 + int(p[3])
                g[eid] = (int(p[0]), int(p[1]))
        geo[arr] = g

    arrays = list(sessions)
    fig, axes = plt.subplots(len(arrays), len(METHODS),
                             figsize=(3.1 * len(METHODS), 3.4 * len(arrays)),
                             squeeze=False)
    vmax = 1
    for arr in arrays:
        for m in METHODS:
            for _, p in sessions[arr]["summary"][m].items():
                vmax = max(vmax, p[1])

    for ri, arr in enumerate(arrays):
        for ci, m in enumerate(METHODS):
            ax = axes[ri][ci]
            grid = np.full((GRID, GRID), np.nan)
            tot_c = tot_p = 0
            for eid, (nc, npass) in sessions[arr]["summary"][m].items():
                tot_c += nc
                tot_p += npass
                if eid in geo[arr]:
                    col, row = geo[arr][eid]
                    grid[row, col] = npass
            cmap = plt.get_cmap("viridis").copy()
            cmap.set_bad("0.88")
            im = ax.imshow(np.ma.masked_invalid(grid), origin="lower",
                           cmap=cmap, vmin=0, vmax=vmax)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(f"{m}\n{tot_c} clusters -> {tot_p} pass", fontsize=9)
            if ci == 0:
                ax.set_ylabel(arr, fontsize=11)
    fig.colorbar(im, ax=axes, fraction=0.015, pad=0.02,
                 label="gate-passing units on electrode")
    fig.suptitle(f"Array overview  {date}   "
                 "colour = units surviving the noise gate, per electrode",
                 fontsize=13)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_channel(res: dict, elec: int, arr: str, date: str, out: Path) -> None:
    """One electrode, four views per method, with gate and UnitRefine verdicts."""
    feats, wf, t = res["feats"], res["wf"], res["t"]
    sr, nbefore = res["meta"]["sr"], res["meta"]["nbefore"]
    dur = res["meta"]["duration_s"]
    t_ms = (np.arange(wf.shape[1]) - nbefore) / sr * 1000.0
    noise = res["noise"]

    fig, axes = plt.subplots(len(METHODS), 4,
                             figsize=(19, 3.0 * len(METHODS)), squeeze=False)
    for ri, m in enumerate(METHODS):
        lab = res["labels"][m]
        rows = {r["_k"]: r for r in res["rows"][m]}
        ks = sorted(rows)
        a_wf, a_pc, a_hist, a_ras = axes[ri]

        # background: unassigned / Plexon-unsorted spikes
        if m == "ofs":
            bg = lab == -1
            if bg.any():
                a_pc.scatter(feats[bg, 0], feats[bg, 1], s=2, c="0.85",
                             alpha=0.4, zorder=0)

        for ci, k in enumerate(ks):
            sel = lab == k
            n = int(sel.sum())
            if n < 3:
                continue
            r = rows[k]
            colour = CLUSTER_CMAP(ci % 10)
            ok = bool(r["pass_gate"])
            style = "-" if ok else "--"

            a_wf.plot(t_ms, wf[sel].mean(axis=0), style, color=colour, lw=2.0,
                      label=f"u{k} n={n} snr={r['snr']:.1f} "
                            f"{'PASS' if ok else 'rej'}/{r.get('ur', '?')[:3]}")
            a_pc.scatter(feats[sel, 0], feats[sel, 1], s=3,
                         color=colour, alpha=0.35 if ok else 0.15)
            a_hist.hist(np.abs(wf[sel].min(axis=1)), bins=40, histtype="step",
                        lw=1.6 if ok else 1.0, color=colour, ls=style)
            ts = np.sort(t[sel])
            a_ras.plot(ts, np.full(len(ts), ci), "|", color=colour,
                       ms=4, alpha=0.7 if ok else 0.3)

        a_wf.axhspan(-noise, noise, color="0.85", zorder=0)
        a_wf.set_ylabel(f"{m}\nuV", fontsize=10)
        a_wf.legend(fontsize=5.5, loc="lower right", framealpha=0.7)
        a_wf.grid(alpha=0.25)
        a_pc.set_xlabel("PC1", fontsize=8)
        a_pc.set_ylabel("PC2", fontsize=8)
        a_pc.grid(alpha=0.25)
        a_hist.axvline(4 * noise, color="black", ls="--", lw=1.2)
        a_hist.set_xlabel("|trough| uV", fontsize=8)
        a_hist.grid(alpha=0.25)
        a_ras.set_xlim(0, dur)
        a_ras.set_yticks([])
        a_ras.set_xlabel("time (s)", fontsize=8)
        a_ras.grid(alpha=0.25, axis="x")
        if ri == 0:
            a_wf.set_title("mean waveform  (grey band = +/-1 noise sigma)",
                           fontsize=10)
            a_pc.set_title("PCA feature space", fontsize=10)
            a_hist.set_title("amplitude histogram  (dashed = gate)", fontsize=10)
            a_ras.set_title("raster", fontsize=10)

    handles = [
        Line2D([], [], color="black", ls="-", lw=2, label="solid = passes noise gate"),
        Line2D([], [], color="black", ls="--", lw=2, label="dashed = rejected"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, fontsize=9,
               frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle(f"Channel detail  {arr}  {date}  electrode {elec}   "
                 f"noise floor {noise:.1f} uV   "
                 "labels: PASS/rej = gate, then UnitRefine", fontsize=13)
    fig.tight_layout(rect=[0, 0.015, 1, 0.965])
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    """Render overview and channel-detail figures for all three timepoints."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--electrode", type=int, default=None,
                    help="Force a specific electrode for the detail figures.")
    args = ap.parse_args()
    FIG.mkdir(parents=True, exist_ok=True)

    idx = pd.read_parquet(INDEX_IN)
    model, lab_map = load_unitrefine()
    if lab_map:
        print(f"  UnitRefine label map: {lab_map}")

    for tag, date in TIMEPOINTS:
        banner(f"{tag}  {date}")
        sessions = {}
        for arr in ("Anterior", "Posterior"):
            sub = idx[(idx["date"] == date) & (idx["array"] == arr)
                      & (idx["kind"] == "OFS")]
            if not len(sub):
                print(f"  {arr}: no OFS file")
                continue
            print(f"  {arr}: clustering ...", flush=True)
            summary, detail = analyse_session(sub.iloc[0]["path"], model, lab_map)
            sessions[arr] = dict(summary=summary, detail=detail)
            tot = {m: sum(p[1] for p in summary[m].values()) for m in METHODS}
            print(f"    gate-passing per method: {tot}")

        if not sessions:
            continue
        fig_overview(sessions, date, FIG / f"{tag}_overview.png")
        print(f"  wrote {tag}_overview.png")

        for arr, s in sessions.items():
            if not s["detail"]:
                print(f"  {arr}: no electrode with >=2 passing units; "
                      f"skipping channel detail")
                continue
            if args.electrode and args.electrode in s["detail"]:
                elec = args.electrode
            else:
                # the electrode ISO-SPLIT finds most structure on
                elec = max(s["detail"],
                           key=lambda e: s["summary"]["isosplit"][e][1])
            fig_channel(s["detail"][elec], elec, arr, date,
                        FIG / f"{tag}_channel_{arr}.png")
            print(f"  wrote {tag}_channel_{arr}.png  (electrode {elec})")

    print(f"\n  -> {FIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

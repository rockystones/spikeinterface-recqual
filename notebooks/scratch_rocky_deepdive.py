"""Per-file deep dive: what the units actually look like, by method and over time.

Takes one anterior/posterior pair at each of three timepoints and renders, for
every sorting method plus Plexon:

* an **array overview** -- gate-passing units per electrode on the 10x10 grid,
  one panel per method, both arrays, so over- and under-splitting are visible
  spatially;
* a **channel detail** -- one representative electrode shown four ways
  (waveforms, PCA feature space, amplitude histogram, raster) with each
  cluster annotated by what the noise gate and UnitRefine each decided.

Timepoints are dates where both arrays have a sorted file and both still
carry units, so every method has something to be compared on. Rocky's are
pinned, because its posterior array reaches zero gate-passing units from 2023
onward and an automatic "latest" choice would render an empty panel. For any
other subject they are picked automatically: earliest, median and latest date
that both arrays share.

**Any Blackrock subject with a verified channel map.** The clustering and the
gate are subject-agnostic; only the file discovery and the array geometry were
Rocky-shaped. Both now resolve from `inventory_all` and the subject registry.

Run from repo root:

    uv run python notebooks/scratch_rocky_deepdive.py [--subject Nigel] [--electrode N]

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
INV = REPO / "data" / "derived" / "inventory_all.parquet"
PROBE_DIR = REPO / "configs" / "probes"
SUBJECT_DIR = REPO / "configs" / "subjects"

# Rocky's are pinned: both arrays paired, both still carrying units, spanning
# the implant lifetime. Its posterior array is at zero gate-passing units from
# 2023, so an automatic "latest" would render an empty panel.
PINNED_TIMEPOINTS = {
    "Rocky": [("T1_early", "2017-10-30"),
              ("T2_middle", "2019-01-31"),
              ("T3_late", "2022-12-09")],
}
METHODS = ["isosplit", "gmm_bic", "hdbscan", "kmeans_sil", "ofs"]
SUBSAMPLE = 4000
from scratch_cohort_io import array_geometry  # noqa: E402

CLUSTER_CMAP = plt.get_cmap("tab10")

NOISE_MODEL = "SpikeInterface/UnitRefine_noise_neural_classifier"
TRUSTED = ["numpy.dtype", "sklearn.pipeline.Pipeline"]


def banner(t: str) -> None:
    print()
    print("=" * 72)
    print(t)
    print("=" * 72)


# %%
# === UnitRefine models ===
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


# %%
# === Per-electrode clustering ===
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
        method -> {channel_id: (n_clusters, n_passing)}
    detail : dict
        channel_id -> the cluster_electrode() result, kept only for
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


# %%
# === Figures ===
def cmp_for(subject: str, array: str, implant: str = "I1") -> Path | None:
    """The array's mapfile, found by serial rather than by a hardcoded name.

    Restricted to one implant: Rocky's I2 reuses the array labels, and a
    collapsed dict lets it overwrite I1 (docs/notes/serial_resolution.md).
    """
    import json

    reg = json.loads((SUBJECT_DIR / f"{subject.lower()}.json")
                     .read_text(encoding="utf-8"))
    serials = {a: sn for im in reg.get("implants", [])
               if im.get("implant") == implant
               for a, sn in (im.get("arrays") or {}).items() if sn}
    sn = serials.get(array)
    if sn is None:
        # the inventory names some arrays by serial (e.g. "SN1498")
        hit = [v for v in serials.values() if v.endswith(array[-4:])]
        sn = hit[0] if hit else None
    if sn is None:
        return None
    hits = sorted(PROBE_DIR.glob(f"*{sn}*.cmp"))
    return hits[0] if hits else None


def cmp_geometry(path: Path) -> dict[int, tuple[int, int]]:
    """``channel_id -> (col, row)``, with channel_id = (bank - 'A') * 32 + pin."""
    g: dict[int, tuple[int, int]] = {}
    for ln in path.read_text().splitlines():
        f = ln.split()
        if len(f) >= 4 and f[0].isdigit() and f[1].isdigit() and f[3].isdigit():
            eid = (ord(f[2].upper()) - ord("A")) * 32 + int(f[3])
            g[eid] = (int(f[0]), int(f[1]))
    return g


def build_index(subject: str) -> pd.DataFrame:
    """Sorted NEVs for one subject, one per (date, array).

    The `-01` chain is Plexon's automatic output, which carries the unit labels
    the `ofs` method reads. Rocky's own `session_index.parquet` calls the same
    files `kind == "OFS"`; this reaches the rest of the cohort, which never had
    one built.
    """
    inv = pd.read_parquet(INV)
    d = inv[(inv.subject == subject) & (inv.role == "snippets")
            & (inv.chain == "-01")].copy()
    d = d[d.array.notna() & d.date.notna()]
    d["date"] = pd.to_datetime(d.date).dt.strftime("%Y-%m-%d")
    return d.sort_values("path").drop_duplicates(subset=["date", "array"])


def pick_timepoints(idx: pd.DataFrame) -> list[tuple[str, str]]:
    """Earliest, median and latest date that every array shares."""
    per_array = [set(g.date) for _, g in idx.groupby("array")]
    shared = sorted(set.intersection(*per_array)) if per_array else []
    if not shared:
        shared = sorted(idx.date.unique())
    if len(shared) < 3:
        return [(f"T{i + 1}", d) for i, d in enumerate(shared)]
    return [("T1_early", shared[0]),
            ("T2_middle", shared[len(shared) // 2]),
            ("T3_late", shared[-1])]


def fig_overview(sessions: dict, date: str, out: Path, subject: str,
                 grid: int) -> None:
    """Gate-passing units per electrode, every method, both arrays."""
    geo = {}
    for arr in sessions:
        path = cmp_for(subject, arr)
        if path is None:
            continue
        geo[arr] = cmp_geometry(path)

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
            gmap = np.full((grid, grid), np.nan)
            tot_c = tot_p = 0
            for eid, (nc, npass) in sessions[arr]["summary"][m].items():
                tot_c += nc
                tot_p += npass
                if eid in geo.get(arr, {}):
                    col, row = geo[arr][eid]
                    gmap[row, col] = npass
            cmap = plt.get_cmap("viridis").copy()
            cmap.set_bad("0.88")
            im = ax.imshow(np.ma.masked_invalid(gmap), origin="lower",
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


# %%
def main() -> int:
    """Render overview and channel-detail figures for all three timepoints."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="Rocky")
    ap.add_argument("--electrode", type=int, default=None,
                    help="Force a specific electrode for the detail figures.")
    args = ap.parse_args()
    subject = args.subject
    fig_dir = REPO / "figures" / subject.lower() / "deepdive"
    fig_dir.mkdir(parents=True, exist_ok=True)

    rocky_index = REPO / "data" / "derived" / "rocky" / "session_index.parquet"
    if subject == "Rocky" and rocky_index.exists():
        idx = pd.read_parquet(rocky_index)
        idx = idx[idx["kind"] == "OFS"]
    else:
        idx = build_index(subject)
    if not len(idx):
        print(f"  no sorted NEVs for {subject}")
        return 1
    arrays = sorted(idx.array.unique())

    # Grid extent from the array's own mapfile: a Utah-16 is 4x4, and a
    # hardcoded 10x10 would render it as 84 empty cells around a corner block.
    geo0 = array_geometry(subject, arrays[0])
    grid = max(geo0["n_cols"], geo0["n_rows"])

    timepoints = PINNED_TIMEPOINTS.get(subject) or pick_timepoints(idx)
    banner(f"{subject}: {len(idx)} sorted sessions, arrays {arrays}, "
           f"grid {grid}x{grid}")
    print("  timepoints: " + ", ".join(f"{t} {d}" for t, d in timepoints))

    model, lab_map = load_unitrefine()
    if lab_map:
        print(f"  UnitRefine label map: {lab_map}")

    for tag, date in timepoints:
        banner(f"{tag}  {date}")
        sessions = {}
        for arr in arrays:
            sub = idx[(idx["date"] == date) & (idx["array"] == arr)]
            if not len(sub):
                print(f"  {arr}: no sorted file on {date}")
                continue
            print(f"  {arr}: clustering ...", flush=True)
            summary, detail = analyse_session(sub.iloc[0]["path"], model, lab_map)
            sessions[arr] = dict(summary=summary, detail=detail)
            tot = {m: sum(p[1] for p in summary[m].values()) for m in METHODS}
            print(f"    gate-passing per method: {tot}")

        if not sessions:
            continue
        fig_overview(sessions, date, fig_dir / f"{tag}_overview.png",
                     subject, grid)
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
                        fig_dir / f"{tag}_channel_{arr}.png")
            print(f"  wrote {tag}_channel_{arr}.png  (electrode {elec})")

    print(f"\n  -> {fig_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

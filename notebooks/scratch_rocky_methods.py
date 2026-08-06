"""Multi-method snippet sorting, extended metrics, and curation features.

One pass over each NEV produces everything downstream needs:

* **Four clustering methods** on identical PCA features, so differences are
  attributable to the clusterer alone and not to preprocessing:

  | method      | algorithm                     | OFS analogue        |
  |-------------|-------------------------------|---------------------|
  | `isosplit`  | ISO-SPLIT (MountainSort5)     | -- (the new option) |
  | `gmm_bic`   | Gaussian mixture, BIC-selected| Standard / T-Dist EM|
  | `hdbscan`   | density-based                 | Valley Seeking      |
  | `kmeans_sil`| k-means, silhouette-selected  | K-Means             |

  Plexon's own labels are carried through as a fifth method, giving a
  five-way panel for consensus work. Manual sorts can be added later as a
  sixth without re-running anything.

* **Extended per-unit metrics** -- waveform shape (half width, peak-to-valley,
  peak/trough ratio, repolarisation and recovery slopes, peak counts) and
  firing statistics (CV of ISI, burst index, firing range, amplitude CV).

* **UnitRefine feature vectors** so the pretrained classifiers can be applied
  without a SortingAnalyzer. 30 of the 37 features the models expect are
  computable from single-channel snippets; the 7 that are not
  (`drift_ptp/std/mad`, `spread`, `velocity_above/below`, `exp_decay`) require
  continuous multi-channel data and are emitted as NaN for the model's own
  SimpleImputer to fill. That limitation is real and is reported, not hidden.

Run from repo root:

    uv run python notebooks/scratch_rocky_methods.py --all [--n-jobs 8] [--limit N]
    uv run python notebooks/scratch_rocky_methods.py --single <ofs.nev>

See:
- docs/notes/snippet_sorting.md
- docs/session_plans/session05_methods_comparison.md
"""

from __future__ import annotations

import argparse
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scratch_rocky_resort import (  # shared IO and gate, single source of truth
    ISI_REFRACTORY_MS,
    MIN_SPIKES,
    N_PCA,
    PLEXON_DROP_UNITS,
    align_on_trough,
    baseline_noise_uv,
    open_nev,
    read_electrode,
    unit_metrics,
)
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "data" / "derived" / "rocky"
INDEX_IN = OUT_DIR / "session_index.parquet"
SHARD_DIR = OUT_DIR / "method_shards"
METHODS_OUT = OUT_DIR / "methods_long.parquet"

MAX_K = 6              # candidate cluster counts for GMM / k-means
CLUSTER_SUBSAMPLE = 8000   # cap per electrode for the slower clusterers

# The 7 UnitRefine features that single-channel snippet data cannot provide.
UNAVAILABLE_FEATURES = [
    "drift_ptp", "drift_std", "drift_mad",
    "spread", "velocity_above", "velocity_below", "exp_decay",
]


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# === Clustering back-ends ===
def cluster_isosplit(feats: np.ndarray) -> np.ndarray:
    """ISO-SPLIT: non-parametric, auto cluster count (MountainSort5's method)."""
    import isosplit6

    return np.asarray(isosplit6.isosplit6(feats))


def cluster_gmm_bic(feats: np.ndarray, max_k: int = MAX_K) -> np.ndarray:
    """Gaussian mixture with the component count chosen by BIC.

    Closest analogue to Plexon's Standard / T-Distribution E-M, which also
    fits parametric mixtures. Assumes ellipsoidal clusters, which extracellular
    feature clouds only approximately satisfy -- that assumption is exactly
    what the comparison is meant to expose.
    """
    best, best_bic = None, np.inf
    for k in range(1, max_k + 1):
        if k > len(feats):
            break
        try:
            gm = GaussianMixture(n_components=k, covariance_type="full",
                                 random_state=0, reg_covar=1e-4)
            lab = gm.fit_predict(feats)
            bic = gm.bic(feats)
        except Exception:  # noqa: BLE001 - degenerate fits are expected
            continue
        if bic < best_bic:
            best, best_bic = lab, bic
    return (best if best is not None else np.zeros(len(feats), dtype=int)) + 1


def cluster_hdbscan(feats: np.ndarray) -> np.ndarray:
    """Density-based clustering; the analogue of OFS Valley Seeking.

    Like Valley Seeking it can leave ambiguous waveforms unassigned (label
    -1). Those are mapped to their own cluster id so they stay visible as an
    'unsorted' group rather than silently disappearing.
    """
    mcs = max(20, int(0.02 * len(feats)))
    lab = HDBSCAN(min_cluster_size=mcs, min_samples=10).fit_predict(feats)
    return lab + 2  # -1 (noise) -> 1, clusters -> 2..n


def cluster_kmeans_sil(feats: np.ndarray, max_k: int = MAX_K) -> np.ndarray:
    """k-means with k chosen by silhouette score; the analogue of OFS K-Means.

    Assigns every waveform to some cluster, which is the documented weakness
    of K-Means on noisy channels.
    """
    n = len(feats)
    if n < 20:
        return np.ones(n, dtype=int)
    sub = feats if n <= 4000 else feats[
        np.random.default_rng(0).choice(n, 4000, replace=False)
    ]
    best_k, best_s = 1, -np.inf
    for k in range(2, max_k + 1):
        if k >= len(sub):
            break
        try:
            lab = KMeans(n_clusters=k, n_init=4, random_state=0).fit_predict(sub)
            s = silhouette_score(sub, lab)
        except Exception:  # noqa: BLE001
            continue
        if s > best_s:
            best_k, best_s = k, s
    if best_k == 1:
        return np.ones(n, dtype=int)
    return KMeans(n_clusters=best_k, n_init=4, random_state=0).fit_predict(feats) + 1


CLUSTERERS = {
    "isosplit": cluster_isosplit,
    "gmm_bic": cluster_gmm_bic,
    "hdbscan": cluster_hdbscan,
    "kmeans_sil": cluster_kmeans_sil,
}


# === Extended waveform + firing metrics ===
def shape_metrics(tmpl: np.ndarray, sr: float, nbefore: int) -> dict:
    """Waveform shape descriptors from a single-channel mean template.

    Parameters
    ----------
    tmpl : np.ndarray
        Mean waveform in uV, shape ``(n_samples,)``.
    sr : float
        Sampling rate in Hz.
    nbefore : int
        Alignment index.

    Returns
    -------
    dict
        ``half_width_ms``, ``peak_to_valley_ms``, ``peak_trough_ratio``,
        ``repolarization_slope``, ``recovery_slope``,
        ``num_negative_peaks``, ``num_positive_peaks``.
    """
    ms_per_sample = 1000.0 / sr
    trough_i = int(np.argmin(tmpl))
    trough = float(tmpl[trough_i])

    post = tmpl[trough_i:]
    peak_rel = int(np.argmax(post)) if len(post) > 1 else 0
    peak = float(post[peak_rel]) if len(post) > 1 else 0.0

    # Half width: span where the trace is below half the trough depth
    half = trough / 2.0
    below = np.flatnonzero(tmpl <= half)
    half_width = (below[-1] - below[0]) * ms_per_sample if len(below) >= 2 else np.nan

    # Repolarisation slope: trough -> following peak
    repol = ((peak - trough) / (peak_rel * ms_per_sample)) if peak_rel > 0 else np.nan

    # Recovery slope: peak -> end of the window
    tail = tmpl[trough_i + peak_rel:]
    recov = ((float(tail[-1]) - peak) / ((len(tail) - 1) * ms_per_sample)
             if len(tail) > 1 else np.nan)

    # Local extrema counts, thresholded to ignore ripple
    thr = 0.15 * abs(trough) if trough != 0 else 0.0
    d = np.diff(tmpl)
    sign_change = np.diff(np.sign(d))
    n_neg = int(np.sum((sign_change > 0) & (np.abs(tmpl[1:-1]) > thr)))
    n_pos = int(np.sum((sign_change < 0) & (np.abs(tmpl[1:-1]) > thr)))

    return dict(
        half_width_ms=float(half_width) if half_width == half_width else np.nan,
        peak_to_valley_ms=peak_rel * ms_per_sample,
        peak_trough_ratio=(peak / abs(trough)) if trough != 0 else np.nan,
        repolarization_slope=repol,
        recovery_slope=recov,
        num_negative_peaks=n_neg,
        num_positive_peaks=n_pos,
    )


def firing_metrics(t: np.ndarray, amps: np.ndarray, duration_s: float) -> dict:
    """Spike-train statistics from times and per-spike amplitudes.

    Parameters
    ----------
    t : np.ndarray
        Spike times in seconds.
    amps : np.ndarray
        Per-spike |trough| amplitude in uV.
    duration_s : float
        Session duration.

    Returns
    -------
    dict
        ``cv_isi``, ``burst_index``, ``firing_range``, ``amplitude_cv_median``,
        ``amplitude_median``, ``amplitude_cutoff``, ``rp_violations``.
    """
    out = dict(cv_isi=np.nan, burst_index=np.nan, firing_range=np.nan,
               amplitude_cv_median=np.nan, amplitude_median=np.nan,
               amplitude_cutoff=np.nan, rp_violations=0)
    if len(t) < 3:
        return out
    isi = np.diff(np.sort(t))
    isi = isi[isi > 0]
    if len(isi) > 1:
        out["cv_isi"] = float(np.std(isi) / np.mean(isi))
        # Burst index: fraction of ISIs under 10 ms
        out["burst_index"] = float((isi < 0.010).mean())
    out["rp_violations"] = int((isi < ISI_REFRACTORY_MS / 1000.0).sum())

    # Firing range: 95th - 5th percentile of rate across 10 bins
    if duration_s > 0:
        edges = np.linspace(0, duration_s, 11)
        counts = np.histogram(t, bins=edges)[0] / np.diff(edges)
        out["firing_range"] = float(np.percentile(counts, 95) - np.percentile(counts, 5))

    if len(amps):
        med = float(np.median(amps))
        out["amplitude_median"] = med
        # Amplitude CV over 10 temporal chunks
        chunks = np.array_split(amps, min(10, len(amps)))
        cvs = [np.std(c) / np.mean(c) for c in chunks if len(c) > 1 and np.mean(c) > 0]
        if cvs:
            out["amplitude_cv_median"] = float(np.median(cvs))
        # Amplitude cutoff: how much of a Gaussian amplitude distribution is
        # truncated by the detection threshold (missed-spike proxy)
        if len(amps) > 30 and med > 0:
            h, e = np.histogram(amps, bins=30)
            pk = int(np.argmax(h))
            if pk > 0:
                out["amplitude_cutoff"] = float(h[0] / max(1, h[pk]))
    return out


def cluster_quality(feats: np.ndarray, labels: np.ndarray, k: int) -> dict:
    """Isolation metrics for one cluster against the rest of its electrode.

    Parameters
    ----------
    feats : np.ndarray
        ``(n_spikes, n_pca)`` features for the whole electrode.
    labels : np.ndarray
        Cluster assignment per spike.
    k : int
        The cluster of interest.

    Returns
    -------
    dict
        ``isolation_distance``, ``l_ratio``, ``d_prime``, ``silhouette``.
    """
    out = dict(isolation_distance=np.nan, l_ratio=np.nan,
               d_prime=np.nan, silhouette=np.nan)
    inside = labels == k
    n_in = int(inside.sum())
    if n_in < 5 or inside.all():
        return out
    x_in, x_out = feats[inside], feats[~inside]
    mu = x_in.mean(axis=0)
    try:
        cov = np.cov(x_in.T) + np.eye(feats.shape[1]) * 1e-6
        inv = np.linalg.inv(cov)
    except np.linalg.LinAlgError:
        return out
    d_out = np.einsum("ij,jk,ik->i", x_out - mu, inv, x_out - mu)
    if len(d_out) >= n_in:
        out["isolation_distance"] = float(np.sort(d_out)[n_in - 1])
    from scipy.stats import chi2
    out["l_ratio"] = float(np.sum(1.0 - chi2.cdf(d_out, feats.shape[1])) / n_in)
    d_in = np.einsum("ij,jk,ik->i", x_in - mu, inv, x_in - mu)
    pooled = np.sqrt(0.5 * (np.var(d_in) + np.var(d_out)))
    if pooled > 0:
        out["d_prime"] = float(abs(np.mean(d_out) - np.mean(d_in)) / pooled)
    if 1 < len(np.unique(labels)) and len(feats) <= 4000:
        try:
            out["silhouette"] = float(
                silhouette_score(feats, labels, sample_size=min(2000, len(feats)),
                                 random_state=0)
            )
        except Exception:  # noqa: BLE001
            pass
    return out


def build_row(
    wf: np.ndarray, t: np.ndarray, feats: np.ndarray, labels: np.ndarray,
    k: int, noise: float, sr: float, nbefore: int, duration_s: float,
) -> dict:
    """Assemble the full metric row for one cluster."""
    sel = labels == k
    tmpl = wf[sel].mean(axis=0)
    amps = np.abs(wf[sel].min(axis=1))
    row = unit_metrics(wf[sel], t[sel], noise, sr, nbefore, duration_s)
    row.update(shape_metrics(tmpl, sr, nbefore))
    row.update(firing_metrics(t[sel], amps, duration_s))
    row.update(cluster_quality(feats, labels, k))
    for f in UNAVAILABLE_FEATURES:
        row[f] = np.nan  # requires continuous multi-channel data
    return row


# === Per-file driver ===
def process_file(ofs_path: str, meta: dict) -> pd.DataFrame:
    """Cluster every electrode four ways and score Plexon's labels alongside."""
    try:
        raw, nmeta, chan_by_elec = open_nev(Path(ofs_path))
    except Exception as e:  # noqa: BLE001
        return pd.DataFrame([{**meta, "method": "error",
                              "error": f"load: {type(e).__name__}: {e}"}])
    sr, nbefore, dur = nmeta["sr"], nmeta["nbefore"], nmeta["duration_s"]
    rows: list[dict] = []

    for elec in sorted(chan_by_elec):
        e = read_electrode(raw, nmeta, chan_by_elec[elec])
        if e is None or len(e["t"]) < MIN_SPIKES:
            continue
        wf_raw, t, pu = e["wf"], e["t"], e["plexon_unit"]
        noise = baseline_noise_uv(wf_raw, nbefore)
        wf = align_on_trough(wf_raw, nbefore)
        del e["wf"], wf_raw

        n_pc = min(N_PCA, wf.shape[1], max(2, len(wf) - 1))
        feats_full = PCA(n_components=n_pc, random_state=0).fit_transform(wf)

        # Slower clusterers run on a capped subsample; ISO-SPLIT handles the
        # full set and does its own internal subsampling above 20k.
        if len(feats_full) > CLUSTER_SUBSAMPLE:
            idx = np.random.default_rng(0).choice(
                len(feats_full), CLUSTER_SUBSAMPLE, replace=False
            )
            idx.sort()
        else:
            idx = np.arange(len(feats_full))

        for mname, fn in CLUSTERERS.items():
            try:
                if mname == "isosplit":
                    lab, f_use, w_use, t_use = (
                        fn(feats_full), feats_full, wf, t
                    )
                else:
                    lab = fn(feats_full[idx])
                    f_use, w_use, t_use = feats_full[idx], wf[idx], t[idx]
                uniq = np.unique(lab)
                for k in uniq:
                    r = build_row(w_use, t_use, f_use, lab, k,
                                  noise, sr, nbefore, dur)
                    r.update(meta)
                    r.update(dict(method=mname, electrode_id=int(elec),
                                  unit_id=int(k), n_clusters_on_elec=len(uniq)))
                    rows.append(r)
            except Exception as ex:  # noqa: BLE001
                rows.append({**meta, "method": mname, "electrode_id": int(elec),
                             "error": f"{type(ex).__name__}: {ex}"})

        # Plexon's own labels, same metrics, same gate
        keep = [u for u in np.unique(pu) if u not in PLEXON_DROP_UNITS]
        for u in keep:
            sel = pu == u
            if sel.sum() < 3:
                continue
            lab_ofs = np.where(sel, 1, 0)
            r = build_row(wf, t, feats_full, lab_ofs, 1,
                          noise, sr, nbefore, dur)
            r.update(meta)
            r.update(dict(method="ofs", electrode_id=int(elec),
                          unit_id=int(u), n_clusters_on_elec=len(keep)))
            rows.append(r)

        del wf, t, pu, feats_full

    return pd.DataFrame(rows)


def shard_path(meta: dict) -> Path:
    """Per-combo shard path, making the run resumable."""
    return SHARD_DIR / f"{meta['date']}_{meta['array']}.parquet"


def process_shard(ofs_path: str, meta: dict) -> str:
    """Run one combo to its own shard; skip if already present."""
    out = shard_path(meta)
    if out.exists():
        return "skip"
    try:
        df = process_file(ofs_path, meta)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out, engine="pyarrow", index=False)
        return f"ok:{len(df)}"
    except Exception as e:  # noqa: BLE001
        return f"err:{type(e).__name__}: {e}"


def meta_from_row(row: pd.Series) -> dict:
    """Session-identifying fields carried onto every row."""
    return dict(date=row["date"], array=row["array"], serial=row["serial"],
                headstage=row["headstage"], stem=row["stem"])


# === Main ===
def main() -> int:
    """Run the multi-method comparison over one file or the paired cohort."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--single", type=str, default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--n-jobs", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    idx = pd.read_parquet(INDEX_IN)

    if args.single:
        p = Path(args.single)
        r = idx[idx["path"] == str(p)]
        meta = meta_from_row(r.iloc[0]) if len(r) else dict(
            date="?", array="?", serial="?", headstage="?", stem=p.stem)
        banner(f"Multi-method: {p.stem}")
        t0 = time.perf_counter()
        df = process_file(str(p), meta)
        print(f"  runtime {time.perf_counter() - t0:.1f} s   rows {len(df)}")
        if "pass_gate" in df.columns:
            g = df.groupby("method").agg(
                clusters=("unit_id", "size"),
                passing=("pass_gate", "sum"),
                electrodes=("electrode_id", "nunique"),
                median_snr=("snr", "median"),
            )
            print(g.to_string())
        return 0

    if not args.all:
        print("pass --single <path> or --all")
        return 1

    from joblib import Parallel, delayed

    combos = idx.groupby(["date", "array"])["kind"].agg(set)
    paired = combos[combos.apply(lambda s: "ORIG" in s and "OFS" in s)].index
    work = []
    for date, array in paired:
        sub = idx[(idx["date"] == date) & (idx["array"] == array)]
        o, f = sub[sub["kind"] == "ORIG"], sub[sub["kind"] == "OFS"]
        if len(o) and len(f):
            work.append((o.iloc[0], f.iloc[0]))
    if args.limit:
        work = work[: args.limit]

    banner(f"Multi-method run: {len(work)} combos x {len(CLUSTERERS) + 1} methods")
    SHARD_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    stats = Parallel(n_jobs=args.n_jobs, verbose=5)(
        delayed(process_shard)(f["path"], meta_from_row(o)) for o, f in work
    )
    n_err = sum(1 for s in stats if s.startswith("err"))
    if n_err:
        print(f"  ERRORS: {n_err}")
        for s in [s for s in stats if s.startswith("err")][:5]:
            print(f"    {s}")

    shards = sorted(SHARD_DIR.glob("*.parquet"))
    out = pd.concat([pd.read_parquet(s) for s in shards], ignore_index=True)
    out.to_parquet(METHODS_OUT, engine="pyarrow", index=False)

    banner("Done")
    print(f"  runtime {(time.perf_counter() - t0) / 60:.1f} min   shards {len(shards)}")
    print(f"  wrote {METHODS_OUT}  rows={len(out)}")
    if "pass_gate" in out.columns:
        g = out.groupby("method").agg(
            clusters=("unit_id", "size"),
            passing=("pass_gate", "sum"),
            median_snr=("snr", "median"),
        )
        g["pass_frac"] = g["passing"] / g["clusters"]
        print(g.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

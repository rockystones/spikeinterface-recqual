"""A comprehensive waveform catalog: every unit shape, every event class.

Owner request (2026-09-16): a library of ALL waveform archetypes in the
data - real or not, artifact or not, any amplitude. Two parts:

PART A - unit mean waveforms, shape-clustered, EVERY sorting algorithm.
  Sources, all nine provenance stores (Rocky x5, Nigel x2, Fisk x2):
    ofs            human Plexon sort, all events
    isosplit_full  full-data ISO-SPLIT, all events
    gmm_bic / kmeans_sil / hdbscan
                   the subset clusterers, means over the seeded
                   subsample events they actually labeled
                   (subsample.parquet label_* columns)
    mountainsort5 / kilosort4 / spykingcircus2 / tridesclous2
                   modern sorters on the continuous ns5: mean of each
                   unit's stored peak-channel sample waveforms
                   (modern/<sorter>/sample_waveforms.npz, 90 samples at
                   30 kHz, cropped to the shared trigger window)
  Each unit contributes its PLAIN mean waveform (owner's convention, no
  realignment), cropped to the largest window every source supports
  (10 pre + 20 post alignment samples at 30 kHz). Shapes are
  z-normalized (amplitude does not drive the grouping) and k-means-
  clustered (k = 16, seed 0). Cluster ids are arbitrary; the TAXONOMY
  mapping ids to archetype names is the discussion this catalog feeds
  (owner's seed: biphasic-large real, pre-trough-max selection noise,
  tri-peak real).

PART C - merge candidates between clusters: for every cluster pair the
  centroid cross-correlation (zero-lag and best within +-5 samples);
  pairs above MERGE_R are drawn overlaid with their metrics so the
  merge decision is visual + quantified.

PART B - the giant/artifact event classes, raw uV.
  One panel per class of the giants taxonomy (giant_events.klass:
  isolated, local_cluster, scattered_few, artifact, impulse,
  multi_channel, railed), sampling member waveforms from
  giant_wf_shards via gid. These are EVENTS, not units - kept apart
  from Part A on purpose.

Outputs:
  data/derived/rocky/waveform_catalog.parquet   one row per unit:
      subject, store, method, channel_id, unit_id, n, cluster,
      trough_peak_uv, range_uv, snr, pass_gate, edge_max
  figures/rocky/21_waveform_catalog_units.png
  figures/rocky/22_waveform_catalog_giants.png

Run from repo root: uv run python notebooks/scratch_waveform_catalog.py
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
DER = REPO / "data" / "derived"
PROV = DER / "provenance"
FIG = REPO / "figures" / "rocky"
OUT = DER / "rocky" / "waveform_catalog.parquet"
K = 16                      # shape clusters; room for sorter-specific shapes
MIN_SPIKES = 30
PLEXON_DROP = (0, 255)
MODERN = ["mountainsort5", "kilosort4", "spykingcircus2", "tridesclous2"]
MODERN_NBEFORE = 30         # SI template window: 1 ms before = sample 30
SUBSET = ["gmm_bic", "kmeans_sil", "hdbscan"]
MERGE_R = 0.97              # best-lag centroid correlation to propose merge


def collect_units() -> tuple[pd.DataFrame, np.ndarray]:
    """One row + one 30-sample plain mean per unit, all stores/methods."""
    rows, means = [], []
    for store in sorted(PROV.iterdir()):
        if not (store / "meta.json").exists():
            continue
        meta = json.load(open(store / "meta.json"))
        ev = pd.read_parquet(store / "events.parquet")
        wf = np.load(store / "waveforms.npy", mmap_mode="r")
        uf = pd.read_parquet(store / "units_full.parquet")
        uf = uf.set_index(["method", "channel_id", "unit_id"])
        # subset-method metrics live in units_methods, not units_full
        um = pd.read_parquet(store / "units_methods.parquet")
        um = um.set_index(["method", "channel_id", "unit_id"])
        # subset clusterers labeled only the seeded subsample: their unit
        # means are taken over exactly the events each method saw
        sub = pd.read_parquet(store / "subsample.parquet")
        sources = [("ofs", ev, "plexon_unit"),
                   ("isosplit_full", ev, "label_isosplit_full")] + \
                  [(m, sub, f"label_{m}") for m in SUBSET]
        for method, tab, lcol in sources:
            if method == "ofs" and not meta.get("has_ofs"):
                continue
            for (ch, u), g in tab.groupby(["channel_id", lcol]):
                if (method == "ofs" and u in PLEXON_DROP) \
                        or len(g) < MIN_SPIKES:
                    continue
                ridx = (g.index.to_numpy() if tab is ev
                        else g.event_idx.to_numpy())   # sub refs global rows
                tmpl = np.asarray(wf[ridx]).mean(axis=0)
                try:
                    src = uf if method in ("ofs", "isosplit_full") else um
                    m = src.loc[(method, int(ch), int(u))]
                    snr, gate = float(m.snr), bool(m.pass_gate)
                except KeyError:
                    snr, gate = np.nan, False
                rows.append(dict(
                    subject=meta.get("subject", "Rocky"), store=store.name,
                    method=method, channel_id=int(ch), unit_id=int(u),
                    n=len(g), snr=snr, pass_gate=gate,
                    nbefore=int(meta["nbefore"])))
                means.append(tmpl)
        # modern sorters: mean of each unit's stored PEAK-CHANNEL sample
        # waveforms (<=150/unit, 90 samples at 30 kHz, alignment at
        # sample 30); gate/snr not defined for this layer
        for sorter in MODERN:
            npz = store / "modern" / sorter / "sample_waveforms.npz"
            if not npz.exists():
                continue
            with np.load(npz) as z:
                swf, sidx = z["wf"], z["unit_index"]
            uids = np.load(store / "modern" / sorter / "unit_ids.npy")
            for ui in np.unique(sidx):
                w = swf[sidx == ui]
                if len(w) < MIN_SPIKES:
                    continue
                rows.append(dict(
                    subject=meta.get("subject", "Rocky"), store=store.name,
                    method=sorter, channel_id=-1, unit_id=int(uids[ui]),
                    n=len(w), snr=np.nan, pass_gate=False,
                    nbefore=MODERN_NBEFORE))
                means.append(w.mean(axis=0).astype(np.float64))
    t = pd.DataFrame(rows)
    # snippet windows differ per subject (Rocky 30 samples, nbefore 10;
    # Fisk/Nigel 48): crop every mean to the largest window around the
    # trigger that ALL stores can supply, so shapes share a time basis
    pre = int(t.nbefore.min())
    post = int(min(len(m) - r.nbefore for m, r in
                   zip(means, t.itertuples(), strict=True)))
    W = np.vstack([m[r.nbefore - pre: r.nbefore + post]
                   for m, r in zip(means, t.itertuples(), strict=True)])
    print(f"common window: {pre} pre + {post} post trigger samples")
    # shape descriptors computed ON THE COMMON WINDOW so every source is
    # measured identically (edge_max = global max on the first 2 samples,
    # the selection-noise signature)
    ti = W.argmin(axis=1)
    t["range_uv"] = W.max(axis=1) - W.min(axis=1)
    t["trough_peak_uv"] = [float(W[i, ti[i]:].max() - W[i, ti[i]])
                           if ti[i] < W.shape[1] - 1 else 0.0
                           for i in range(len(t))]
    t["edge_max"] = W.argmax(axis=1) <= 1
    return t, W


def main() -> int:
    from sklearn.cluster import KMeans

    t, W = collect_units()
    print(f"{len(t)} units ({t.groupby(['subject','method']).size().to_dict()})")
    # z-normalize each mean so CLUSTERING sees shape, not amplitude
    Z = (W - W.mean(axis=1, keepdims=True)) / \
        (W.std(axis=1, keepdims=True) + 1e-9)
    t["cluster"] = KMeans(n_clusters=K, n_init=10, random_state=0
                          ).fit_predict(Z)
    t.to_parquet(OUT, index=False)

    # order clusters by median trough->peak so the grid reads big -> small
    order = (t.groupby("cluster").trough_peak_uv.median()
             .sort_values(ascending=False).index.tolist())
    short = {"ofs": "ofs", "isosplit_full": "iso", "gmm_bic": "gmm",
             "kmeans_sil": "km", "hdbscan": "hdb", "mountainsort5": "ms5",
             "kilosort4": "ks4", "spykingcircus2": "sc2",
             "tridesclous2": "tdc"}
    fig, axes = plt.subplots(4, 4, figsize=(16, 12))
    for ax, c in zip(axes.ravel(), order, strict=True):
        idx = np.flatnonzero((t.cluster == c).to_numpy())
        pick = idx[np.linspace(0, len(idx) - 1, min(40, len(idx))
                               ).astype(int)]
        for i in pick:
            ax.plot(Z[i], color="0.6", lw=0.4, alpha=0.5)
        ax.plot(Z[idx].mean(axis=0), "k-", lw=2)
        g = t.iloc[idx]
        # top-3 contributing algorithms, so sorter-specific shapes show
        comp = ", ".join(f"{short.get(m, m)} {n}" for m, n in
                         g.method.value_counts().head(3).items())
        ax.set_title(
            f"cluster {c}  (n={len(idx)}, gated {g.pass_gate.mean():.0%})\n"
            f"trough→peak med {g.trough_peak_uv.median():.0f} uV, "
            f"snr med {g.snr.median():.1f}, "
            f"edge-max {g.edge_max.mean():.0%}\n[{comp}]",
            fontsize=7)
        ax.tick_params(labelsize=6)
        ax.grid(alpha=0.2)
    fig.suptitle("PART A - unit mean waveforms, z-normalized, k-means "
                 f"shape clusters ({len(t)} units, 9 sorting chains, "
                 "nine sessions, three subjects)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "21_waveform_catalog_units.png", dpi=150)
    plt.close(fig)
    print(f"wrote {FIG / '21_waveform_catalog_units.png'}")

    # === PART C: merge candidates between shape clusters ================
    def xcorr_best(a: np.ndarray, b: np.ndarray, maxlag: int = 5
                   ) -> tuple[float, int]:
        """Best Pearson r between two centroids over integer lags."""
        best, bl = -1.0, 0
        for L in range(-maxlag, maxlag + 1):
            if L > 0:
                r = np.corrcoef(a[L:], b[: len(b) - L])[0, 1]
            elif L < 0:
                r = np.corrcoef(a[:L], b[-L:])[0, 1]
            else:
                r = np.corrcoef(a, b)[0, 1]
            if r > best:
                best, bl = float(r), L
        return best, bl

    cents = np.vstack([Z[(t.cluster == c).to_numpy()].mean(axis=0)
                       for c in range(K)])
    pairs = []
    for i in range(K):
        for j in range(i + 1, K):
            r0 = float(np.corrcoef(cents[i], cents[j])[0, 1])
            rb, L = xcorr_best(cents[i], cents[j])
            pairs.append(dict(a=i, b=j, r0=r0, r_best=rb, lag=L))
    pt = pd.DataFrame(pairs).sort_values("r_best", ascending=False)
    print("\ntop cluster-pair correlations (merge candidates):")
    print(pt.head(10).round(3).to_string(index=False))
    cand = pt[pt.r_best >= MERGE_R].head(8)

    if len(cand):
        ncol = min(4, len(cand))
        nrow = int(np.ceil(len(cand) / ncol))
        fig, axes = plt.subplots(nrow, ncol,
                                 figsize=(4 * ncol, 3.2 * nrow),
                                 squeeze=False)
        for ax, r in zip(axes.ravel(), cand.itertuples(), strict=False):
            for c, col in ((r.a, "tab:blue"), (r.b, "tab:orange")):
                idx = np.flatnonzero((t.cluster == c).to_numpy())
                for i in idx[np.linspace(0, len(idx) - 1,
                                         min(25, len(idx))).astype(int)]:
                    ax.plot(Z[i], color=col, lw=0.3, alpha=0.25)
                g = t.iloc[idx]
                ax.plot(cents[c], color=col, lw=2.2,
                        label=f"c{c}: n={len(idx)}, "
                              f"gated {g.pass_gate.mean():.0%}, "
                              f"{g.trough_peak_uv.median():.0f} uV")
            ax.set_title(f"c{r.a} vs c{r.b}:  r0={r.r0:.3f}, "
                         f"best r={r.r_best:.3f} @ lag {r.lag:+d}",
                         fontsize=8)
            ax.legend(fontsize=6)
            ax.grid(alpha=0.2)
            ax.tick_params(labelsize=6)
        for ax in axes.ravel()[len(cand):]:
            ax.axis("off")
        fig.suptitle("PART C - merge candidates: cluster-pair centroid "
                     f"cross-correlation >= {MERGE_R}", fontsize=12)
        fig.tight_layout(rect=(0, 0, 1, 0.93))
        fig.savefig(FIG / "23_catalog_merge_candidates.png", dpi=150)
        plt.close(fig)
        print(f"wrote {FIG / '23_catalog_merge_candidates.png'}")

    # === PART B: the giant/artifact classes, raw uV =====================
    ge = pd.read_parquet(DER / "rocky" / "giant_events.parquet")
    classes = ["railed", "artifact", "impulse", "multi_channel",
               "isolated", "local_cluster", "scattered_few"]
    fig, axes = plt.subplots(2, 4, figsize=(15, 6.5))
    rng = np.random.default_rng(0)
    for ax, kl in zip(axes.ravel(), classes, strict=False):
        g = ge[ge.klass == kl]
        # draw up to 8 example events, each fetched from its shard by gid
        drawn = 0
        for r in g.sample(min(40, len(g)), random_state=0).itertuples():
            shard = DER / "rocky" / "giant_wf_shards" / (
                f"{pd.Timestamp(r.date):%Y-%m-%d}_{r.array}.npz")
            if not shard.exists():
                continue
            with np.load(shard) as z:
                hit = np.flatnonzero(z["gid"] == r.gid)
                if not len(hit):
                    continue
                ax.plot(z["wf"][hit[0]], lw=0.8,
                        color=plt.cm.tab10(drawn % 10))
            drawn += 1
            if drawn >= 8:
                break
        ax.set_title(f"{kl}  (class n={len(g):,}, {drawn} shown)",
                     fontsize=9)
        ax.tick_params(labelsize=6)
        ax.grid(alpha=0.2)
        ax.set_ylabel("μV", fontsize=7)
    axes.ravel()[-1].axis("off")
    fig.suptitle("PART B - giant/artifact EVENT classes (raw μV, "
                 "Rocky I1 taxonomy from giant_events.klass)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIG / "22_waveform_catalog_giants.png", dpi=150)
    plt.close(fig)
    print(f"wrote {FIG / '22_waveform_catalog_giants.png'}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

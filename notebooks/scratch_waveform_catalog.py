"""A comprehensive waveform catalog: every unit shape, every event class.

Owner request (2026-09-16): a library of ALL waveform archetypes in the
data - real or not, artifact or not, any amplitude. Two parts:

PART A - unit mean waveforms, shape-clustered.
  Every (channel, unit) with >= 30 snippets in the nine provenance
  stores (Rocky x5, Nigel x2, Fisk x2), BOTH partitions per store: the
  human Plexon sort (method 'ofs') and full-data ISO-SPLIT
  ('isosplit_full'). Each unit contributes its PLAIN mean waveform
  (owner's convention, no realignment). Shapes are z-normalized (so
  amplitude does not drive the grouping) and k-means-clustered
  (k = 12, seed 0); the figure shows each cluster's members, count,
  gate-pass share, and heuristic shape descriptors. Cluster ids are
  arbitrary; the TAXONOMY mapping ids to archetype names is the
  discussion this catalog feeds (owner's seed: biphasic-large real,
  pre-trough-max selection noise, tri-peak real).

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
K = 12                      # shape clusters; enough to separate archetypes
MIN_SPIKES = 30
PLEXON_DROP = (0, 255)


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
        for method, lcol in (("ofs", "plexon_unit"),
                             ("isosplit_full", "label_isosplit_full")):
            if method == "ofs" and not meta.get("has_ofs"):
                continue
            for (ch, u), g in ev.groupby(["channel_id", lcol]):
                if (method == "ofs" and u in PLEXON_DROP) \
                        or len(g) < MIN_SPIKES:
                    continue
                tmpl = np.asarray(wf[g.index.to_numpy()]).mean(axis=0)
                ti = int(np.argmin(tmpl))
                tp = float(tmpl[ti:].max() - tmpl[ti]) if ti < len(tmpl) - 1 \
                    else 0.0
                try:
                    m = uf.loc[(method, int(ch), int(u))]
                    snr, gate = float(m.snr), bool(m.pass_gate)
                except KeyError:
                    snr, gate = np.nan, False
                rows.append(dict(
                    subject=meta.get("subject", "Rocky"), store=store.name,
                    method=method, channel_id=int(ch), unit_id=int(u),
                    n=len(g), trough_peak_uv=tp,
                    range_uv=float(tmpl.max() - tmpl.min()), snr=snr,
                    pass_gate=gate, nbefore=int(meta["nbefore"]),
                    # selection-noise signature: the global max sits on
                    # the first two pre-trigger samples
                    edge_max=bool(np.argmax(tmpl) <= 1)))
                means.append(tmpl)
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
    fig, axes = plt.subplots(3, 4, figsize=(15, 9))
    for ax, c in zip(axes.ravel(), order, strict=True):
        idx = np.flatnonzero((t.cluster == c).to_numpy())
        pick = idx[np.linspace(0, len(idx) - 1, min(40, len(idx))
                               ).astype(int)]
        for i in pick:
            ax.plot(Z[i], color="0.6", lw=0.4, alpha=0.5)
        ax.plot(Z[idx].mean(axis=0), "k-", lw=2)
        g = t.iloc[idx]
        ax.set_title(
            f"cluster {c}  (n={len(idx)}, gated {g.pass_gate.mean():.0%})\n"
            f"trough→peak med {g.trough_peak_uv.median():.0f} uV, "
            f"snr med {g.snr.median():.1f}, edge-max {g.edge_max.mean():.0%}",
            fontsize=8)
        ax.tick_params(labelsize=6)
        ax.grid(alpha=0.2)
    fig.suptitle("PART A - unit mean waveforms, z-normalized, k-means "
                 f"shape clusters (both partitions, {len(t)} units, "
                 "nine sessions, three subjects)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIG / "21_waveform_catalog_units.png", dpi=150)
    plt.close(fig)
    print(f"wrote {FIG / '21_waveform_catalog_units.png'}")

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

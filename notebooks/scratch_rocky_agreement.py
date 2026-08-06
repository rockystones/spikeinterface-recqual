"""Spike-level agreement between snippet sorting methods.

Cluster counts alone cannot establish a consensus baseline: two methods can
report the same number of units while disagreeing about which spikes belong
to them. Because every method here labels an *identical* spike subsample, the
agreement can be measured directly rather than inferred.

Two complementary measures:

* **Adjusted Rand index** on the whole per-electrode partition. Answers "do
  these two methods carve the electrode up the same way", corrected for
  chance agreement.
* **Best-match Jaccard** per gate-passing unit. Answers the question that
  matters operationally -- if method A reports a unit, does method B find
  substantially the same spikes? A unit whose best match is poor is a
  candidate false positive, or a real unit the other method missed.

Plexon OFS is included as a fifth method, so its labels are compared on the
same footing rather than treated as ground truth.

Run from repo root:

    uv run python notebooks/scratch_rocky_agreement.py [--n-sessions 16]

See:
- docs/notes/snippet_sorting.md
"""

from __future__ import annotations

import argparse
import itertools
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scratch_rocky_methods import (
    CLUSTER_SUBSAMPLE,
    CLUSTERERS,
    build_row,
)
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
from sklearn.metrics import adjusted_rand_score

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "data" / "derived" / "rocky"
FIG_DIR = REPO / "figures" / "rocky"
INDEX_IN = OUT_DIR / "session_index.parquet"
AGREE_OUT = OUT_DIR / "method_agreement.parquet"
JACCARD_OUT = OUT_DIR / "method_jaccard.parquet"

METHOD_ORDER = ["isosplit", "gmm_bic", "hdbscan", "kmeans_sil", "ofs"]


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def best_match_jaccard(
    lab_a: np.ndarray, lab_b: np.ndarray, keep_a: set, keep_b: set
) -> list[dict]:
    """For each retained cluster in A, its best Jaccard overlap in B.

    Parameters
    ----------
    lab_a, lab_b : np.ndarray
        Per-spike cluster labels from the two methods, same spikes, same order.
    keep_a, keep_b : set
        Cluster ids in each method that passed the noise gate. Rejected
        clusters are excluded from matching so noise-vs-noise overlap does
        not inflate agreement.

    Returns
    -------
    list of dict
        One row per retained cluster of A, with its best Jaccard against any
        retained cluster of B.
    """
    out = []
    for ka in sorted(keep_a):
        ma = lab_a == ka
        n_a = int(ma.sum())
        if n_a == 0:
            continue
        best, best_k, best_cont, best_nb = 0.0, None, 0.0, 0
        for kb in sorted(keep_b):
            mb = lab_b == kb
            inter = int((ma & mb).sum())
            if inter == 0:
                continue
            j = inter / float((ma | mb).sum())
            if j > best:
                best, best_k = j, int(kb)
            # Containment is tracked separately from Jaccard because the two
            # answer different questions and the methods differ enormously in
            # how many spikes they assign. Plexon leaves most spikes unsorted,
            # so an OFS unit is often a small subset of a large automatic
            # cluster: Jaccard reads near zero (it penalises the size
            # mismatch) while containment correctly reports that every OFS
            # spike was found. Reporting Jaccard alone would say the methods
            # disagree when in fact one is simply more conservative.
            cont = inter / float(n_a)
            if cont > best_cont:
                best_cont, best_nb = cont, int(mb.sum())
        out.append(dict(unit_a=int(ka), n_spikes_a=n_a,
                        best_jaccard=best, matched_b=best_k,
                        best_containment=best_cont, matched_b_size=best_nb))
    return out


def analyse_file(ofs_path: str, meta: dict) -> tuple[list[dict], list[dict]]:
    """Cluster one file every way and measure pairwise agreement."""
    raw, nmeta, chan_by_elec = open_nev(Path(ofs_path))
    sr, nbefore, dur = nmeta["sr"], nmeta["nbefore"], nmeta["duration_s"]
    ari_rows, jac_rows = [], []

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
        if len(feats_full) > CLUSTER_SUBSAMPLE:
            idx = np.random.default_rng(0).choice(
                len(feats_full), CLUSTER_SUBSAMPLE, replace=False)
            idx.sort()
        else:
            idx = np.arange(len(feats_full))
        feats, wf_s, t_s, pu_s = feats_full[idx], wf[idx], t[idx], pu[idx]
        del feats_full, wf

        labels: dict[str, np.ndarray] = {}
        keep: dict[str, set] = {}
        for mname, fn in CLUSTERERS.items():
            try:
                lab = fn(feats)
            except Exception:  # noqa: BLE001
                continue
            labels[mname] = lab
            keep[mname] = {
                int(k) for k in np.unique(lab)
                if build_row(wf_s, t_s, feats, lab, k, noise, sr, nbefore,
                             dur)["pass_gate"]
            }

        # Plexon labels on the same spikes; unsorted/noise ids dropped
        ofs_lab = np.where(np.isin(pu_s, list(PLEXON_DROP_UNITS)), -1, pu_s)
        labels["ofs"] = ofs_lab
        keep["ofs"] = {
            int(u) for u in np.unique(ofs_lab) if u != -1
            and (ofs_lab == u).sum() >= 3
            and build_row(wf_s, t_s, feats, ofs_lab, u, noise, sr, nbefore,
                          dur)["pass_gate"]
        }

        present = [m for m in METHOD_ORDER if m in labels]
        # ARI is symmetric, so unordered pairs suffice.
        for a, b in itertools.combinations(present, 2):
            ari_rows.append({**meta, "electrode_id": int(elec),
                             "method_a": a, "method_b": b,
                             "ari": float(adjusted_rand_score(labels[a], labels[b])),
                             "n_units_a": len(keep[a]), "n_units_b": len(keep[b]),
                             "n_spikes": len(feats)})
        # Containment is NOT symmetric and the asymmetry is the whole point:
        # "are A's spikes inside some B cluster" and the reverse are different
        # questions, and for a conservative method like Plexon only one of them
        # is informative. Ordered pairs are required.
        for a, b in itertools.permutations(present, 2):
            for r in best_match_jaccard(labels[a], labels[b], keep[a], keep[b]):
                jac_rows.append({**meta, "electrode_id": int(elec),
                                 "method_a": a, "method_b": b, **r})

        del wf_s, t_s, pu_s, feats, labels, keep

    return ari_rows, jac_rows


def render(ari: pd.DataFrame, jac: pd.DataFrame, out: Path) -> None:
    """Agreement matrix plus best-match Jaccard distributions."""
    fig, axes = plt.subplots(1, 3, figsize=(19, 5.6))

    methods = [m for m in METHOD_ORDER if m in
               set(ari["method_a"]) | set(ari["method_b"])]
    n = len(methods)
    mat = np.full((n, n), np.nan)
    for i, a in enumerate(methods):
        mat[i, i] = 1.0
        for j, b in enumerate(methods):
            if j <= i:
                continue
            sel = ari[((ari["method_a"] == a) & (ari["method_b"] == b))
                      | ((ari["method_a"] == b) & (ari["method_b"] == a))]
            if len(sel):
                mat[i, j] = mat[j, i] = float(sel["ari"].median())

    im = axes[0].imshow(mat, vmin=0, vmax=1, cmap="viridis")
    axes[0].set_xticks(range(n), methods, rotation=45, ha="right")
    axes[0].set_yticks(range(n), methods)
    for i in range(n):
        for j in range(n):
            if np.isfinite(mat[i, j]):
                axes[0].text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center",
                             color="white" if mat[i, j] < 0.6 else "black",
                             fontsize=9)
    axes[0].set_title("median adjusted Rand index\n(per-electrode partitions)")
    plt.colorbar(im, ax=axes[0], fraction=0.046)

    ref = "isosplit"
    for b in [m for m in methods if m != ref]:
        s = jac[(jac["method_a"] == ref) & (jac["method_b"] == b)]["best_jaccard"]
        if len(s):
            axes[1].hist(s, bins=np.linspace(0, 1, 26), histtype="step",
                         lw=1.6, label=f"{b}  (n={len(s)})", density=True)
    axes[1].set_xlabel("best-match Jaccard against isosplit units")
    axes[1].set_ylabel("density")
    axes[1].set_title("do other methods recover isosplit's units?")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.3)

    frac = []
    for a, b in itertools.permutations(methods, 2):
        s = jac[(jac["method_a"] == a) & (jac["method_b"] == b)]["best_jaccard"]
        if len(s) >= 20:
            frac.append(dict(pair=f"{a}\n vs {b}", frac=float((s >= 0.5).mean())))
    if frac:
        fdf = pd.DataFrame(frac).sort_values("frac")
        axes[2].barh(range(len(fdf)), fdf["frac"], color="steelblue")
        axes[2].set_yticks(range(len(fdf)), fdf["pair"], fontsize=6)
        axes[2].set_xlabel("fraction of units with a good match (Jaccard >= 0.5)")
        axes[2].set_title("reproducibility across methods")
        axes[2].grid(alpha=0.3, axis="x")

    fig.suptitle("Rocky: agreement between snippet sorting methods "
                 "(identical spikes, gate-passing units only)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    """Measure pairwise method agreement over a stratified session sample."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-sessions", type=int, default=16)
    ap.add_argument("--n-jobs", type=int, default=6)
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    idx = pd.read_parquet(INDEX_IN)
    combos = idx.groupby(["date", "array"])["kind"].agg(set)
    paired = combos[combos.apply(lambda s: "ORIG" in s and "OFS" in s)].index
    work = []
    for date, array in paired:
        sub = idx[(idx["date"] == date) & (idx["array"] == array)]
        o, f = sub[sub["kind"] == "ORIG"], sub[sub["kind"] == "OFS"]
        if len(o) and len(f):
            work.append((o.iloc[0], f.iloc[0]))

    # Even spread over year x array, same rationale as the methods run
    cells: dict[tuple, list] = {}
    for o, f in work:
        cells.setdefault((str(o["date"])[:4], o["array"]), []).append((o, f))
    per = max(1, args.n_sessions // max(1, len(cells)))
    picked = []
    for c in sorted(cells):
        items = cells[c]
        picked.extend(items[:: max(1, len(items) // per)][:per])

    banner(f"Agreement over {len(picked)} sessions x {len(METHOD_ORDER)} methods")
    from joblib import Parallel, delayed

    def one(o, f):
        meta = dict(date=o["date"], array=o["array"], headstage=o["headstage"])
        try:
            return analyse_file(f["path"], meta)
        except Exception as e:  # noqa: BLE001
            print(f"  fail {o['date']} {o['array']}: {type(e).__name__}: {e}")
            return [], []

    res = Parallel(n_jobs=args.n_jobs, verbose=5)(
        delayed(one)(o, f) for o, f in picked)
    ari = pd.DataFrame([r for a, _ in res for r in a])
    jac = pd.DataFrame([r for _, b in res for r in b])
    if not len(ari):
        print("no results")
        return 1

    ari.to_parquet(AGREE_OUT, engine="pyarrow", index=False)
    jac.to_parquet(JACCARD_OUT, engine="pyarrow", index=False)

    banner("Pairwise partition agreement (median ARI over electrodes)")
    p = (ari.groupby(["method_a", "method_b"])["ari"]
         .agg(["median", "mean", "size"]).round(3).reset_index())
    print(p.to_string(index=False))

    banner("Unit reproducibility (gate-passing units)")
    print("  jacc_*  = best-match Jaccard, penalises size mismatch")
    print("  cont_*  = best-match containment, |A and B| / |A|")
    print("  A conservative method that under-assigns spikes shows LOW Jaccard")
    print("  but HIGH containment; that is a different finding from disagreement.")
    print()
    q = (jac.groupby(["method_a", "method_b"])
         .agg(jacc_median=("best_jaccard", "median"),
              jacc_good=("best_jaccard", lambda s: float((s >= 0.5).mean())),
              cont_median=("best_containment", "median"),
              cont_good=("best_containment", lambda s: float((s >= 0.8).mean())),
              size_ratio=("matched_b_size", "median"),
              n_a_spikes=("n_spikes_a", "median"),
              n=("best_jaccard", "size"))
         .round(3).reset_index())
    q["size_ratio"] = (q["size_ratio"] / q["n_a_spikes"]).round(2)
    print(q.to_string(index=False))

    banner("Interpretation aids")
    med_all = ari.groupby(["method_a", "method_b"])["ari"].median()
    print(f"  highest agreeing pair : {med_all.idxmax()}  ARI={med_all.max():.3f}")
    print(f"  lowest agreeing pair  : {med_all.idxmin()}  ARI={med_all.min():.3f}")
    ofs_pairs = med_all[[("ofs" in k) for k in med_all.index]]
    if len(ofs_pairs):
        print(f"  median ARI of OFS vs the automatic methods: "
              f"{float(ofs_pairs.median()):.3f}")

    render(ari, jac, FIG_DIR / "14_method_agreement.png")
    print(f"\n  wrote {FIG_DIR / '14_method_agreement.png'}")
    print(f"  wrote {AGREE_OUT.name} ({len(ari)} rows), "
          f"{JACCARD_OUT.name} ({len(jac)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

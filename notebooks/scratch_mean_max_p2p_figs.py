"""Cohort figures for the exact mean-max-P2P metric (nav D-013 / W-017).

Consumes `data/derived/cohort/mean_max_p2p.parquet` written by
`scratch_mean_max_p2p_pass.py` (the exact legacy definition, straight from
the sorted NEVs) and renders the metric as a default longitudinal output
for every Blackrock animal:

- `figures/cohort/mean_max_p2p.png` - 2x3 grid: subjects as columns,
  NaN-fill / zero-fill as rows, one line per (implant, array). Rocky's
  implant labels come from a join (session_index for I1, the inventory for
  the rest) because Anterior/Posterior names are reused across implants
  (docs/notes/serial_resolution.md).
- `figures/rocky/16_mean_max_p2p.png` - regenerated from the exact values,
  with the disqualified units_long approximation overlaid to show the
  session-level size of the (peak - trough) under-read.

Also cross-checks the pass against the validated provenance stores: for
every dumped session, the per-channel max P2P recomputed from the store's
raw waveforms (plain mean, no realignment) must match the shard.

Log y throughout: 2019-05-23 Posterior is a real ~13 mV railed-artifact
day, kept and annotated. Sessions with zero active channels have no
NaN-fill value and drop from the log axis in the zero-fill row.

Run from repo root after the pass completes:

    uv run python notebooks/scratch_mean_max_p2p_figs.py

See docs/notes/longitudinal_metrics.md.
"""

from __future__ import annotations

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
sys.path.insert(0, str(REPO / "notebooks"))

from scratch_cohort_io import banner  # noqa: E402

DER = REPO / "data" / "derived"
TABLE = DER / "cohort" / "mean_max_p2p.parquet"
SHARDS = DER / "cohort" / "mmp2p_shards"
PLEXON_DROP = (0, 255)


# %%
def load_with_implant() -> pd.DataFrame:
    """The exact table plus an implant column resolved per (subject, stem)."""
    from scratch_ns5_resort import INV

    t = pd.read_parquet(TABLE)

    # implant map: Rocky I1 stems from the repaired session_index, everything
    # else from the inventory's snippet rows (chain -01, stems match keys)
    imp: dict[tuple[str, str], str] = {}
    ix = pd.read_parquet(DER / "rocky" / "session_index.parquet")
    for r in ix[ix.kind == "OFS"].itertuples():
        imp[("Rocky", str(r.stem).removesuffix("-01"))] = "I1"
    inv = pd.read_parquet(INV)
    sn = inv[(inv.role == "snippets") & (inv.chain == "-01")]
    for r in sn.itertuples():
        imp.setdefault((str(r.subject), str(r.stem)), str(r.implant))

    t["implant"] = [imp.get((s, st), "?")
                    for s, st in zip(t.subject, t.stem, strict=True)]
    n_unk = int((t.implant == "?").sum())
    if n_unk:
        print(f"  ! {n_unk} sessions with unresolved implant")
    t["date"] = pd.to_datetime(t.date)
    return t.sort_values(["subject", "implant", "array", "date"])


# %%
def crosscheck_stores(t: pd.DataFrame) -> None:
    """Shard vs provenance store on the nine dumped sessions.

    Recomputes the legacy per-channel max P2P from the store's raw
    waveforms (plain mean over each Plexon unit's snippets) and compares
    with the shard on the channels both layers kept.
    """
    for store in sorted((DER / "provenance").iterdir()):
        if not (store / "events.parquet").exists():
            continue
        subject = "Rocky" if store.name.startswith("Rocky") else (
            "Nigel" if store.name.startswith("Nigel") else "Fisk")
        shard_path = SHARDS / f"{subject}__{store.name}.parquet"
        if not shard_path.exists():
            print(f"  {store.name}: no shard (not in worklist)")
            continue
        ev = pd.read_parquet(store / "events.parquet",
                             columns=["channel_id", "plexon_unit"])
        wf = np.load(store / "waveforms.npy", mmap_mode="r")
        best: dict[int, float] = {}      # per-channel max-unit P2P, store side
        for (ch, u), g in ev.groupby(["channel_id", "plexon_unit"]):
            if u in PLEXON_DROP:
                continue
            tmpl = np.asarray(wf[g.index.to_numpy()]).mean(axis=0)
            best[int(ch)] = max(best.get(int(ch), 0.0),
                                float(tmpl.max() - tmpl.min()))
        sh = pd.read_parquet(shard_path).set_index("channel_id")
        common = sorted(set(best) & set(sh.index))
        if not common:
            print(f"  {store.name}: no overlapping channels")
            continue
        diff = max(abs(best[c] - float(sh.loc[c, "max_p2p_uv"]))
                   for c in common)
        print(f"  {store.name}: {len(common)} common channels "
              f"(store {len(best)}, shard {len(sh)})  max|diff| = {diff:g}")


# %%
def fig_cohort(t: pd.DataFrame) -> None:
    """2x3 grid: subject columns, fill-variant rows, log y."""
    subjects = ["Rocky", "Nigel", "Fisk"]
    fig, axes = plt.subplots(2, 3, figsize=(14, 7), sharex="col")
    for j, sub in enumerate(subjects):
        g_sub = t[t.subject == sub]
        for i, (col, ttl) in enumerate([
                ("max_p2p_mean_nan", "NaN-fill (active channels)"),
                ("max_p2p_mean_zero", "zero-fill (all 96)")]):
            ax = axes[i, j]
            for (impl, arr), g in g_sub.groupby(["implant", "array"],
                                                observed=True):
                g = g.sort_values("date")
                lbl = f"{impl} {arr}" if sub == "Rocky" else str(arr)
                ax.plot(g.date, g[col], "-", lw=1.0, ms=2, label=lbl)
            ax.set_yscale("log")
            ax.grid(alpha=0.25)
            if i == 0:
                ax.set_title(sub, fontsize=11)
            if j == 0:
                ax.set_ylabel(f"mean max P2P (uV, log)\n{ttl}", fontsize=8)
            ax.tick_params(axis="x", labelrotation=45, labelsize=7)
            ax.legend(fontsize=6, loc="best")
        # the cohort max is real data, not an outlier to clip
        peak = g_sub.loc[g_sub.max_p2p_mean_nan.idxmax()] if len(g_sub) else None
        if peak is not None and peak.max_p2p_mean_nan > 2000:
            axes[0, j].annotate(f"{peak.date.date()} artifact day",
                                (peak.date, peak.max_p2p_mean_nan),
                                fontsize=7, textcoords="offset points",
                                xytext=(6, -2))
    fig.suptitle("Mean max peak-to-peak amplitude - the legacy headline "
                 "metric, exact from the sorted NEVs (Plexon units)",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = REPO / "figures" / "cohort" / "mean_max_p2p.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  wrote {out}")


def fig_rocky_exact(t: pd.DataFrame) -> None:
    """Regenerate figures/rocky/16 from exact values; overlay the approx."""
    approx = pd.read_parquet(DER / "cohort" / "mean_max_p2p_rocky.parquet")
    approx = approx[approx.method == "ofs"].copy()
    approx["date"] = pd.to_datetime(approx.date)
    ex = t[(t.subject == "Rocky") & (t.implant == "I1")]

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2), sharey=True)
    for ax, col, ttl in zip(
            axes,
            ["max_p2p_mean_nan", "max_p2p_mean_zero"],
            ["NaN-fill (mean over active channels)",
             "zero-fill (inactive channels count as 0)"], strict=True):
        for arr, g in ex.groupby("array", observed=True):
            g = g.sort_values("date")
            ax.plot(g.date, g[col], "-", lw=1.1, label=f"{arr} exact")
        for arr, g in approx.groupby("array", observed=True):
            g = g.sort_values("date")
            ax.plot(g.date, g[col], "--", lw=0.7, alpha=0.55,
                    label=f"{arr} units_long approx")
        ax.set_yscale("log")
        ax.grid(alpha=0.25)
        ax.set_title(ttl, fontsize=10)
        ax.tick_params(axis="x", labelrotation=45, labelsize=7)
        peak = ex.loc[ex[col].idxmax()]
        ax.annotate("2019-05-23 artifact day", (peak.date, peak[col]),
                    fontsize=7, textcoords="offset points", xytext=(6, -2))
    axes[0].set_ylabel("mean max peak-to-peak amplitude (uV, log)")
    axes[0].legend(fontsize=7)
    fig.suptitle("Rocky I1: exact legacy metric from the NEVs, with the "
                 "disqualified (peak - trough) approximation overlaid",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    out = REPO / "figures" / "rocky" / "16_mean_max_p2p.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  wrote {out}")


def main() -> int:
    t = load_with_implant()
    banner("cross-check: pass shards vs provenance stores")
    crosscheck_stores(t)
    banner("summary")
    print(t.groupby(["subject", "implant", "array"], observed=True).agg(
        sessions=("stem", "size"),
        nan_med=("max_p2p_mean_nan", "median"),
        zero_med=("max_p2p_mean_zero", "median"),
        active_med=("n_active", "median")).round(1).to_string())
    banner("figures")
    fig_cohort(t)
    fig_rocky_exact(t)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Mean max peak-to-peak amplitude - the legacy MATLAB metric, made default.

Owner ruling (nav D-013): the legacy layer's headline amplitude metric joins
the default set for every monkey. Definition taken from
`matlab/plot_U01_Utaharray_01062026.m`, not paraphrased:

  line 112:  unit_amp = abs(max(mean_waveform) - min(mean_waveform))
             -- the GLOBAL range of the unit's mean waveform
  line 122:  max_amp(chan) = max over that channel's units (zeros init)
  lines 775/788:  averaged across channels two ways, kept side by side:
             zero-fill  (inactive channels count as 0, denominator = all)
             nan-fill   (inactive channels dropped, mean over active only)

Two jobs here:

1. **Exactness check.** `units_long` carries `trough_uv` and `peak_uv`, but
   `peak_uv` is the post-trough peak, not the global max, so
   (peak - trough) can under-read the legacy P2P when a pre-trough bump is
   the true maximum. The provenance stores hold raw waveforms + Plexon
   labels for five sessions: compute both definitions there and measure the
   gap before trusting the approximation.

2. **Rocky longitudinal now** from `units_long` (ofs = the Plexon input the
   legacy layer consumed, ungated, plus the gated resort as the modern
   counterpart), written to `data/derived/cohort/mean_max_p2p_rocky.parquet`
   with figures. The exact cohort-wide recompute from the NEVs (all
   Blackrock animals) runs separately in `scratch_mean_max_p2p_pass.py`.

Run from repo root:

    uv run python notebooks/scratch_mean_max_p2p.py

See docs/notes/data_inspection.md and docs/notes/longitudinal_metrics.md.
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
sys.path.insert(0, str(REPO / "notebooks"))

from scratch_cohort_io import banner  # noqa: E402

DER = REPO / "data" / "derived"
OUT = DER / "cohort" / "mean_max_p2p_rocky.parquet"
FIG = REPO / "figures" / "rocky"
N_CH = 96                      # zero-fill denominator: the wired array
PLEXON_DROP = (0, 255)


# %%
def exactness_check() -> None:
    """Global-range P2P vs (peak - trough) on the provenance sessions."""
    from scratch_rocky_resort import align_on_trough

    rows = []
    for store in sorted((DER / "provenance").glob("Rocky_*")):
        meta = json.load(open(store / "meta.json"))
        if not meta.get("has_ofs"):
            continue
        ev = pd.read_parquet(store / "events.parquet",
                             columns=["channel_id", "plexon_unit"])
        wf = np.load(store / "waveforms.npy", mmap_mode="r")
        uf = pd.read_parquet(store / "units_full.parquet")
        uf = uf[uf.method == "ofs"].set_index(["channel_id", "unit_id"])
        nbefore = meta["nbefore"]
        for (ch, u), g in ev.groupby(["channel_id", "plexon_unit"]):
            if u in PLEXON_DROP or (ch, u) not in uf.index:
                continue
            w = align_on_trough(np.asarray(wf[g.index.to_numpy()]), nbefore)
            tmpl = w.mean(axis=0)
            exact = float(tmpl.max() - tmpl.min())
            r = uf.loc[(ch, u)]
            approx = float(r.peak_uv - r.trough_uv)
            rows.append(dict(stem=meta["stem"], channel_id=ch, unit_id=u,
                             exact=exact, approx=approx))
    d = pd.DataFrame(rows)
    d["rel_err"] = (d.approx - d.exact) / d.exact
    print(f"  {len(d)} ofs units across {d.stem.nunique()} sessions")
    print(f"  approx == exact on {(d.rel_err.abs() < 1e-9).mean():.1%} "
          f"of units")
    print(f"  rel err: median {d.rel_err.median():+.4%}  "
          f"p01 {d.rel_err.quantile(0.01):+.4%}  "
          f"worst {d.rel_err.min():+.4%}")
    d.to_parquet(DER / "cohort" / "mean_max_p2p_exactness.parquet",
                 index=False)


# %%
def mean_max_p2p(units: pd.DataFrame, n_ch: int = N_CH) -> pd.Series:
    """The legacy statistic for one session's unit table.

    Parameters
    ----------
    units : pandas.DataFrame
        Per-unit rows for one (date, array, method) with ``channel_id``
        and ``p2p_uv``.
    n_ch : int
        Zero-fill denominator (wired electrodes).

    Returns
    -------
    pandas.Series
        ``max_p2p_mean_nan`` (active channels only), ``max_p2p_mean_zero``
        (inactive as 0), ``n_active``.
    """
    per_ch = units.groupby("channel_id").p2p_uv.max()
    return pd.Series(dict(
        max_p2p_mean_nan=float(per_ch.mean()) if len(per_ch) else np.nan,
        max_p2p_mean_zero=float(per_ch.sum() / n_ch),
        n_active=int(len(per_ch))))


def rocky_longitudinal() -> pd.DataFrame:
    """Per session/array/method from units_long (approx P2P; see check)."""
    u = pd.read_parquet(DER / "rocky" / "units_long.parquet")
    u["p2p_uv"] = u.peak_uv - u.trough_uv
    rows = []
    for (d8, arr, meth), g in u.groupby(["date", "array", "method"],
                                        observed=True):
        variants = {"all": g}
        if meth == "resort":
            variants["gated"] = g[g.pass_gate.astype(bool)]
        for tag, gg in variants.items():
            s = mean_max_p2p(gg)
            rows.append(dict(date=str(d8), array=arr,
                             method=meth + ("" if tag == "all" else "_gated"),
                             **s.to_dict()))
    out = pd.DataFrame(rows).sort_values(["array", "method", "date"])
    out.to_parquet(OUT, index=False)
    return out


def fig_rocky(t: pd.DataFrame) -> None:
    """16_mean_max_p2p.png - the legacy metric, both fill variants."""
    t = t.copy()
    t["date"] = pd.to_datetime(t.date)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2), sharey=True)
    for ax, col, ttl in zip(
            axes,
            ["max_p2p_mean_nan", "max_p2p_mean_zero"],
            ["NaN-fill (mean over active channels)",
             "zero-fill (inactive channels count as 0)"], strict=True):
        for (arr, meth), g in t.groupby(["array", "method"], observed=True):
            if meth not in ("ofs", "resort_gated"):
                continue
            g = g.sort_values("date")
            ax.plot(g.date, g[col], "-", lw=1.1,
                    label=f"{arr} {meth}")
        ax.grid(alpha=0.25)
        ax.set_yscale("log")
        ax.set_title(ttl, fontsize=10)
        ax.tick_params(axis="x", labelrotation=45, labelsize=7)
        # the max is real data: 2019-05-23 Posterior is an array-wide ~13 mV
        # artifact day (railed events sorted as units; some pass the gate)
        peak = t.loc[t[col].idxmax()]
        ax.annotate("2019-05-23 artifact day",
                    (peak.date, peak[col]), fontsize=7,
                    textcoords="offset points", xytext=(6, -2))
    axes[0].set_ylabel("mean max peak-to-peak amplitude (uV, log)")
    axes[0].legend(fontsize=7)
    fig.suptitle("The legacy headline metric, Rocky I1 "
                 "(per channel: largest-P2P unit; averaged across channels)",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "16_mean_max_p2p.png", dpi=150)
    plt.close(fig)
    print(f"  wrote {FIG / '16_mean_max_p2p.png'}")


def main() -> int:
    banner("1. Exactness: global-range P2P vs (peak - trough), provenance")
    exactness_check()
    banner("2. Rocky longitudinal from units_long")
    t = rocky_longitudinal()
    print(t.groupby(["array", "method"], observed=True)
           .agg(n=("date", "size"),
                nan_med=("max_p2p_mean_nan", "median"),
                zero_med=("max_p2p_mean_zero", "median"),
                active_med=("n_active", "median")).round(1).to_string())
    fig_rocky(t)
    print(f"\n  wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

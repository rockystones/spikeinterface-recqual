"""Where the global-range amplitude and trough->peak disagree: a gallery.

Owner discussion (2026-09-16): the owner's MATLAB amplitude is
|max - min| of the unit's PLAIN mean waveform (no realignment, no
peak/trough identification) - deliberately simple, assuming sorted units
conform. This script finds, in the provenance stores' raw snippets, the
Plexon units where that definition and the physiological trough->
post-trough-peak excursion diverge most, and draws them side by side:

  green markers = the owner's definition (global max / global min)
  blue markers  = trough and the peak AFTER it (the pipeline's reading)

Classes shown: clean agreement (the assumption holding), pre-trough-max
units (range > trough->peak: the global max is a bump BEFORE the trough
- an overlapping previous spike or double detection in the 1 ms
pre-trigger), and artifact units (both definitions explode together).

Everything is computed on the PLAIN mean, mirroring the owner's code.

    uv run python notebooks/scratch_amp_definition_gallery.py

Output: figures/rocky/20_amp_definition_gallery.png
See docs/notes/longitudinal_metrics.md (the metric's caveat paragraph).
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
PROV = REPO / "data" / "derived" / "provenance"
OUT = REPO / "figures" / "rocky" / "20_amp_definition_gallery.png"
PLEXON_DROP = (0, 255)


def unit_rows() -> pd.DataFrame:
    """Every Plexon unit in the Rocky stores, both amplitude readings."""
    rows = []
    for store in sorted(PROV.glob("Rocky_*")):
        meta = json.load(open(store / "meta.json"))
        if not meta.get("has_ofs"):
            continue
        ev = pd.read_parquet(store / "events.parquet",
                             columns=["channel_id", "plexon_unit"])
        wf = np.load(store / "waveforms.npy", mmap_mode="r")
        for (ch, u), g in ev.groupby(["channel_id", "plexon_unit"]):
            if u in PLEXON_DROP or len(g) < 30:
                continue
            tmpl = np.asarray(wf[g.index.to_numpy()]).mean(axis=0)
            rng = float(tmpl.max() - tmpl.min())          # owner's def
            ti = int(np.argmin(tmpl))                     # trough sample
            post = tmpl[ti:]
            tp = float(post.max() - tmpl[ti]) if len(post) > 1 else 0.0
            rows.append(dict(store=store.name, channel_id=int(ch),
                             unit_id=int(u), n=len(g), rng=rng,
                             trough_peak=tp,
                             infl=rng / tp if tp > 0 else np.inf,
                             nbefore=meta["nbefore"], sr=meta["sr"]))
    return pd.DataFrame(rows)


def draw(ax, store: str, ch: int, u: int, nbefore: int, sr: float,
         label: str) -> None:
    """One unit: faint raw snippets + plain mean with both definitions."""
    ev = pd.read_parquet(PROV / store / "events.parquet",
                         columns=["channel_id", "plexon_unit"])
    wf = np.load(PROV / store / "waveforms.npy", mmap_mode="r")
    idx = ev.index[(ev.channel_id == ch) & (ev.plexon_unit == u)].to_numpy()
    w = np.asarray(wf[idx])
    tmpl = w.mean(axis=0)
    t_ms = (np.arange(len(tmpl)) - nbefore) / sr * 1e3
    sub = w[np.linspace(0, len(w) - 1, min(60, len(w))).astype(int)]
    ax.plot(t_ms, sub.T, color="0.75", lw=0.3, alpha=0.5, zorder=1)
    ax.plot(t_ms, tmpl, "k-", lw=2, zorder=3)
    # owner's definition: global extrema, wherever they fall
    gmax, gmin = int(np.argmax(tmpl)), int(np.argmin(tmpl))
    ax.plot(t_ms[gmax], tmpl[gmax], "^", color="tab:green", ms=9, zorder=4)
    ax.plot(t_ms[gmin], tmpl[gmin], "v", color="tab:green", ms=9, zorder=4)
    # pipeline reading: trough, then the peak AFTER it only
    ti = gmin
    pi = ti + int(np.argmax(tmpl[ti:]))
    ax.plot(t_ms[pi], tmpl[pi], "^", mfc="none", mec="tab:blue", ms=11,
            mew=1.6, zorder=5)
    rng = tmpl[gmax] - tmpl[gmin]
    tp = tmpl[pi] - tmpl[ti]
    ax.set_title(f"{label}\n{store[6:28]} ch{ch} u{u} (n={len(w)})\n"
                 f"range {rng:.0f} uV vs trough→peak {tp:.0f} uV "
                 f"({rng / tp if tp else np.inf:.2f}x)", fontsize=7)
    ax.grid(alpha=0.2)
    ax.tick_params(labelsize=6)


def main() -> int:
    t = unit_rows()
    print(f"{len(t)} Plexon units across {t.store.nunique()} stores")
    ok = t[np.isfinite(t.infl) & (t.trough_peak > 5)]
    print(f"definitions equal (<1% apart) on {(ok.infl < 1.01).mean():.0%}; "
          f"inflation p90 {ok.infl.quantile(0.9):.2f}x, "
          f"max {ok.infl.max():.1f}x")

    picks = []
    # 2 clean units: definitions agree, healthy amplitude
    clean = ok[(ok.infl < 1.005) & (ok.n > 500)].nlargest(2, "rng")
    picks += [(r, "CLEAN: assumption holds") for r in clean.itertuples()]
    # 4 worst pre-trough-max inflations (all turn out to be SMALL units)
    bump = ok[(ok.rng < 1000)].nlargest(4, "infl")
    picks += [(r, "PRE-TROUGH MAX inflates range")
              for r in bump.itertuples()]
    # the 2 worst divergences among units of REAL spike size - the
    # ceiling of the effect where amplitude actually matters
    big = ok[ok.trough_peak > 40].nlargest(2, "infl")
    picks += [(r, "worst case among large units")
              for r in big.itertuples()]

    fig, axes = plt.subplots(2, 4, figsize=(14, 6.5))
    for ax, (r, label) in zip(axes.ravel(), picks, strict=False):
        draw(ax, r.store, r.channel_id, r.unit_id, r.nbefore, r.sr, label)
    for ax in axes.ravel()[len(picks):]:
        ax.axis("off")
    axes[0, 0].set_ylabel("μV")
    axes[1, 0].set_ylabel("μV")
    fig.suptitle("Global range (green extrema) vs trough→post-trough "
                 "peak (blue ring), plain mean waveform, Plexon units",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    plt.close(fig)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

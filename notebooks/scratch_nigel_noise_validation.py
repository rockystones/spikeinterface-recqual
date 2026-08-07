"""Validate the snippet baseline-MAD noise estimate against continuous data.

The whole Rocky analysis rests on one substitution. Those sessions have no
continuous broadband, so the per-electrode noise floor -- and therefore SNR,
and therefore the gate -- is estimated from the pre-trigger samples carried
inside each NEV snippet rather than from a trace. That estimate has never been
checked against the thing it stands in for, because no Rocky session has both.

The Nigel 2023-03-17 session has both: a 1.05 GB `.ns5` and its `.nev`,
recorded simultaneously from the same 96 electrodes. So the substitution can be
measured directly:

    continuous  : bandpass the ns5 into the spike band, MAD per channel
    snippet     : MAD of the pre-trigger samples of that channel's NEV clips

If these agree, every Rocky SNR is defensible. If they disagree, the direction
and size of the bias is itself the correction factor.

Also sweeps how many trailing pre-trigger samples must be discarded: samples
immediately before the threshold crossing already contain the rising phase of
the spike, which biases the noise estimate upward.

Run from repo root:

    uv run python notebooks/scratch_nigel_noise_validation.py

See:
- docs/notes/snippet_noise_floor.md
"""

from __future__ import annotations

import re
import sys
import time
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from spikeinterface.core import get_noise_levels
from spikeinterface.extractors import read_blackrock
from spikeinterface.preprocessing import bandpass_filter, highpass_filter

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_rocky_resort import open_nev, read_electrode  # noqa: E402

RAW = REPO / "data" / "raw"
NS5 = RAW / "Nigel_Anterior_2023-03-17_Baseline_DigitalHeadstage.ns5"
NEV = RAW / "Nigel_Anterior_2023-03-17_Baseline_DigitalHeadstage-01.nev"
FIG_DIR = REPO / "figures" / "validation"
OUT = REPO / "data" / "derived" / "noise_validation_nigel.parquet"

NS5_STREAM_ID = "5"
SEG_BROADBAND = 1          # seg[0] is a 2.36 s operator false start
CHAN_RE = re.compile(r"(\d+)")

# The NSP applies a hardware spike filter before writing NEV snippets. Matching
# it is what makes the two estimates comparable at all; a 300 Hz highpass with
# no upper corner leaves high-frequency content the NEV never saw.
SPIKE_BAND = (250.0, 5000.0)
HP_ONLY = 300.0            # the project's own default, kept for comparison


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def snippet_noise_by_electrode(nev_path: Path, drop_tail: int = 2) -> pd.DataFrame:
    """Baseline-MAD noise per electrode, with a configurable pre-trigger margin.

    Parameters
    ----------
    nev_path : Path
        NEV carrying the snippets.
    drop_tail : int
        Pre-trigger samples discarded from the end of the baseline window. The
        production value is 2.

    Returns
    -------
    pandas.DataFrame
        ``electrode_id``, ``noise_uv``, ``n_spikes``, ``n_baseline_samples``.
    """
    raw, meta, chan_by_elec = open_nev(nev_path)
    nbefore = meta["nbefore"]
    stop = max(1, nbefore - drop_tail)
    rows = []
    for elec in sorted(chan_by_elec):
        e = read_electrode(raw, meta, chan_by_elec[elec])
        if e is None or len(e["t"]) < 20:
            continue
        base = e["wf"][:, :stop]
        med = np.median(base)
        mad = np.median(np.abs(base - med))
        rows.append(dict(
            electrode_id=elec,
            noise_uv=float(mad / 0.6745) if mad > 0 else np.nan,
            n_spikes=int(len(e["t"])),
            n_baseline_samples=int(base.size),
        ))
        del e
    return pd.DataFrame(rows)


def continuous_noise(rec, label: str) -> pd.DataFrame:
    """MAD noise per channel from a continuous recording, in uV."""
    t0 = time.perf_counter()
    mad = get_noise_levels(rec, method="mad", return_scaled=True,
                           force_recompute=True)
    sd = get_noise_levels(rec, method="std", return_scaled=True,
                          force_recompute=True)
    el = time.perf_counter() - t0
    ids = [int(CHAN_RE.search(str(c)).group(1)) for c in rec.channel_ids]
    print(f"  {label:22s} {el:6.1f} s   median MAD {np.median(mad):6.2f} uV"
          f"   median SD {np.median(sd):6.2f} uV")
    return pd.DataFrame({"electrode_id": ids,
                         f"mad_{label}": mad, f"sd_{label}": sd})


def fig_agreement(df: pd.DataFrame, out: Path) -> None:
    """Snippet estimate against the continuous ground truth."""
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2))

    ax = axes[0]
    x, y = df["mad_spikeband"], df["noise_uv"]
    lim = [0, max(x.max(), y.max()) * 1.08]
    ax.plot(lim, lim, "-", color="0.6", lw=1, label="identity")
    ax.plot(x, y, "o", ms=4, alpha=0.75, color="#1f77b4")
    r, _ = pearsonr(x, y)
    rho, _ = spearmanr(x, y)
    ax.set_xlabel("continuous ns5, 250-5000 Hz\nMAD noise (uV)", fontsize=8)
    ax.set_ylabel("snippet pre-trigger baseline\nMAD noise (uV)", fontsize=8)
    ax.set_title(f"per-electrode agreement\nr = {r:.3f}   rho = {rho:.3f}",
                 fontsize=9)
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.legend(fontsize=7)

    ax = axes[1]
    ratio = df["noise_uv"] / df["mad_spikeband"]
    ax.hist(ratio, bins=24, color="#1f77b4", alpha=0.85)
    ax.axvline(1.0, color="0.4", ls=":", lw=1.2)
    ax.axvline(ratio.median(), color="#d62728", lw=1.4,
               label=f"median {ratio.median():.3f}")
    ax.set_xlabel("snippet / continuous", fontsize=8)
    ax.set_ylabel("electrodes", fontsize=8)
    ax.set_title("bias of the substitution", fontsize=9)
    ax.legend(fontsize=7)

    ax = axes[2]
    ax.plot(df["electrode_id"], df["mad_spikeband"], "o", ms=3,
            label="continuous (250-5000 Hz)", color="0.35")
    ax.plot(df["electrode_id"], df["noise_uv"], "o", ms=3,
            label="snippet baseline", color="#1f77b4")
    ax.plot(df["electrode_id"], df["mad_hp300"], "x", ms=3,
            label="continuous (300 Hz HP only)", color="#ff7f0e", alpha=0.6)
    ax.set_xlabel("electrode id", fontsize=8)
    ax.set_ylabel("MAD noise (uV)", fontsize=8)
    ax.set_title("per-electrode noise floor", fontsize=9)
    ax.legend(fontsize=6.5)

    for ax in axes:
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.25, lw=0.5)
    fig.suptitle("Does the snippet baseline-MAD noise estimate reproduce the "
                 "continuous one?  Nigel 2023-03-17, 96 electrodes, same session",
                 fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.9])
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_margin_sweep(sweep: pd.DataFrame, ref: pd.Series, out: Path) -> None:
    """Effect of the pre-trigger margin on the estimate."""
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for d, g in sweep.groupby("drop_tail"):
        m = g.merge(ref.rename("ref").reset_index(), on="electrode_id")
        ax.plot(d, (m["noise_uv"] / m["ref"]).median(), "o", color="#1f77b4",
                ms=6)
        ax.errorbar(d, (m["noise_uv"] / m["ref"]).median(),
                    yerr=[[(m["noise_uv"] / m["ref"]).median()
                           - (m["noise_uv"] / m["ref"]).quantile(0.25)],
                          [(m["noise_uv"] / m["ref"]).quantile(0.75)
                           - (m["noise_uv"] / m["ref"]).median()]],
                    color="#1f77b4", capsize=3, lw=1)
    ax.axhline(1.0, color="0.5", ls=":", lw=1.2)
    ax.set_xlabel("pre-trigger samples discarded before the crossing", fontsize=9)
    ax.set_ylabel("snippet estimate / continuous MAD", fontsize=9)
    ax.set_title("Where the spike's rising phase stops contaminating the baseline",
                 fontsize=9)
    ax.grid(alpha=0.3, lw=0.5)
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    banner("Continuous reference from the ns5")
    rec = read_blackrock(file_path=str(NS5), stream_id=NS5_STREAM_ID)
    rec = rec.select_segments([SEG_BROADBAND])
    sr = rec.get_sampling_frequency()
    print(f"  channels {rec.get_num_channels()}   sr {sr} Hz   "
          f"duration {rec.get_num_samples() / sr:.1f} s")

    # Match the NSP's own spike filter, which is what produced the snippets.
    band = continuous_noise(
        bandpass_filter(rec, freq_min=SPIKE_BAND[0], freq_max=SPIKE_BAND[1]),
        "spikeband")
    hp = continuous_noise(highpass_filter(rec, freq_min=HP_ONLY), "hp300")

    banner("Snippet baseline estimate from the nev")
    t0 = time.perf_counter()
    snip = snippet_noise_by_electrode(NEV, drop_tail=2)
    print(f"  {len(snip)} electrodes in {time.perf_counter() - t0:.1f} s")
    print(f"  median snippet-baseline MAD {snip['noise_uv'].median():.2f} uV")

    df = snip.merge(band, on="electrode_id").merge(hp, on="electrode_id")
    print(f"  matched electrodes {len(df)}")

    banner("Agreement")
    for col, lbl in [("mad_spikeband", "continuous 250-5000 Hz"),
                     ("mad_hp300", "continuous 300 Hz HP"),
                     ("sd_spikeband", "continuous SD 250-5000 Hz")]:
        r, pr = pearsonr(df["noise_uv"], df[col])
        rho, ps = spearmanr(df["noise_uv"], df[col])
        ratio = (df["noise_uv"] / df[col])
        print(f"  vs {lbl:26s} r={r:6.3f} (p={pr:.1e})  rho={rho:6.3f}  "
              f"ratio median={ratio.median():.3f} "
              f"[{ratio.quantile(.1):.3f}, {ratio.quantile(.9):.3f}]")

    banner("Pre-trigger margin sweep")
    sweeps = []
    for d in (0, 1, 2, 3, 4, 5):
        s = snippet_noise_by_electrode(NEV, drop_tail=d)
        s["drop_tail"] = d
        m = s.merge(band, on="electrode_id")
        ratio = (m["noise_uv"] / m["mad_spikeband"]).median()
        print(f"  drop_tail={d}  baseline samples={10 - d:2d}  "
              f"median ratio {ratio:.4f}")
        sweeps.append(s)
    sweep = pd.concat(sweeps, ignore_index=True)

    fig_agreement(df, FIG_DIR / "N1_noise_validation.png")
    fig_margin_sweep(sweep, band.set_index("electrode_id")["mad_spikeband"],
                     FIG_DIR / "N2_pretrigger_margin.png")
    df.to_parquet(OUT, engine="pyarrow", index=False)

    banner("Done")
    print(f"  N1_noise_validation.png, N2_pretrigger_margin.png -> {FIG_DIR}")
    print(f"  {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

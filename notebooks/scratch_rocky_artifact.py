"""Cross-channel artifacts that the per-electrode noise gate cannot see.

The gate in `scratch_rocky_resort.py` judges each cluster on SNR, spike count
and waveform shape -- all properties of a single electrode. A synchronous
artifact appearing on many electrodes at once satisfies every one of those
criteria: it is large, frequent, and roughly spike-shaped. Nothing in a
single-channel view can reject it.

Plexon OFS does not have this blind spot. Its batch log records
`Invalidating artifacts with width 60 ticks, channel percentage 15`, i.e. a
cross-channel artifact pass before sorting. That is the most likely reason it
reports far fewer units than the automatic methods on some electrodes, and on
those events it is right and the automatic methods are wrong.

The `sync_spike_*` features added for the UnitRefine test make the artifacts
directly measurable: they count how often a unit fires at the same sample as
2, 4 or 8 other units anywhere on the array.

Run from repo root:

    uv run python notebooks/scratch_rocky_artifact.py

See:
- docs/notes/snippet_sorting.md
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "derived" / "rocky"
FIG = REPO / "figures" / "rocky" / "evidence"
METHODS_IN = OUT / "methods_long.parquet"

AUTO = ["isosplit", "gmm_bic", "hdbscan", "kmeans_sil"]
# A unit coincident with >=4 other units on this fraction of its spikes is not
# a neuron. Chosen from the bimodality in the data rather than a priori: real
# units sit at sync_spike_4 ~ 0.00, artifacts at ~0.80.
SYNC4_ARTIFACT = 0.20


def banner(t: str) -> None:
    print()
    print("=" * 72)
    print(t)
    print("=" * 72)


def main() -> int:
    """Quantify the artifact contamination and render the evidence figure."""
    FIG.mkdir(parents=True, exist_ok=True)
    m = pd.read_parquet(METHODS_IN)
    m["pass_gate"] = m["pass_gate"].fillna(False).astype(bool)
    auto = m[m["method"].isin(AUTO) & m["pass_gate"]].copy()
    auto = auto[auto["sync_spike_4"].notna() & auto["amplitude_uv"].notna()]
    ofs = m[(m["method"] == "ofs") & m["pass_gate"]].copy()
    ofs = ofs[ofs["sync_spike_4"].notna()]

    banner("Artifact contamination among gate-passing units")
    art = auto["sync_spike_4"] > SYNC4_ARTIFACT
    print(f"  automatic gate-passing units      : {len(auto):,}")
    print(f"  flagged as cross-channel artifact : {int(art.sum()):,} "
          f"({art.mean():.2%})")
    print()
    print("  artifact-flagged units are the LARGEST units in the dataset:")
    print(f"    median amplitude  artifact {auto.loc[art, 'amplitude_uv'].median():8.1f} uV"
          f"   vs clean {auto.loc[~art, 'amplitude_uv'].median():8.1f} uV")
    print(f"    median SNR        artifact {auto.loc[art, 'snr'].median():8.2f}"
          f"      vs clean {auto.loc[~art, 'snr'].median():8.2f}")
    print("    -> they pass the SNR gate precisely because they are huge.")

    if len(ofs):
        oart = ofs["sync_spike_4"] > SYNC4_ARTIFACT
        print()
        print(f"  Plexon gate-passing units         : {len(ofs):,}")
        print(f"    flagged as artifact             : {int(oart.sum()):,} "
              f"({oart.mean():.2%})")
        print("    Plexon runs a cross-channel artifact pass before sorting")
        print("    (batch log: width 60 ticks, channel percentage 15).")

    banner("Effect on the headline statistics")
    for label, sub in (("all gate-passing", auto),
                       ("artifact-free", auto[~art])):
        print(f"  {label:18s} n={len(sub):6,}  "
              f"median SNR {sub['snr'].median():5.2f}  "
              f"median amp {sub['amplitude_uv'].median():6.1f} uV  "
              f"p99 amp {sub['amplitude_uv'].quantile(0.99):8.1f} uV")

    # --- figure ---
    fig, axes = plt.subplots(1, 3, figsize=(17, 5))

    axes[0].scatter(auto.loc[~art, "amplitude_uv"], auto.loc[~art, "sync_spike_4"],
                    s=5, alpha=0.15, color="#1f77b4", label="clean")
    axes[0].scatter(auto.loc[art, "amplitude_uv"], auto.loc[art, "sync_spike_4"],
                    s=8, alpha=0.35, color="#d62728", label="artifact")
    axes[0].axhline(SYNC4_ARTIFACT, color="black", ls="--", lw=1.5)
    axes[0].set_xscale("log")
    axes[0].set_xlabel("unit amplitude (uV, log)")
    axes[0].set_ylabel("sync_spike_4\n(fraction coincident with >=4 units)")
    axes[0].set_title("the largest units are the synchronous ones")
    axes[0].legend(fontsize=9, markerscale=2)
    axes[0].grid(alpha=0.3)

    bins = np.linspace(0, 1, 41)
    axes[1].hist(auto["sync_spike_4"], bins=bins, color="#7f7f7f")
    axes[1].axvline(SYNC4_ARTIFACT, color="black", ls="--", lw=1.5)
    axes[1].set_yscale("log")
    axes[1].set_xlabel("sync_spike_4")
    axes[1].set_ylabel("units (log)")
    axes[1].set_title("bimodal: real units near 0, artifacts near 0.8\n"
                      "the cut is read off the data, not assumed", fontsize=10)

    amp_bins = [0, 100, 200, 400, 800, 1e9]
    labels = ["<100", "100-200", "200-400", "400-800", ">800"]
    auto["amp_bin"] = pd.cut(auto["amplitude_uv"], amp_bins, labels=labels)
    frac = auto.groupby("amp_bin", observed=True)["sync_spike_4"].apply(
        lambda s: float((s > SYNC4_ARTIFACT).mean()))
    cnt = auto.groupby("amp_bin", observed=True).size()
    axes[2].bar(range(len(frac)), frac.values, color="#d62728")
    for i, (f, c) in enumerate(zip(frac.values, cnt.values, strict=True)):
        axes[2].text(i, f + 0.02, f"{f:.0%}\nn={c:,}", ha="center", fontsize=8)
    axes[2].set_xticks(range(len(frac)), frac.index.astype(str))
    axes[2].set_ylim(0, 1.15)
    axes[2].set_xlabel("unit amplitude (uV)")
    axes[2].set_ylabel("fraction flagged as artifact")
    axes[2].set_title("contamination is confined to the largest amplitudes",
                      fontsize=10)
    axes[2].grid(alpha=0.3, axis="y")

    fig.suptitle("E7  A blind spot in the per-electrode gate: cross-channel "
                 "artifacts pass because they are large\n"
                 "Plexon rejects these with an artifact pass the automatic "
                 "methods do not have", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(FIG / "E7_crosschannel_artifacts.png", dpi=150,
                bbox_inches="tight")
    plt.close(fig)
    print(f"\n  wrote {FIG / 'E7_crosschannel_artifacts.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

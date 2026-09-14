"""Direct ISO-SPLIT (snippet resort) vs MountainSort5 (continuous ns5).

The two share a clustering core but see different data: ISO-SPLIT
partitions the NSP's online-thresholded snippets per electrode; MS5
re-detects from the whole continuous stream across the array. This
compares them unit-for-unit on the provenance-store sessions that carry
both layers, the same way the OFS comparison ran (lag-aligned per
I-005, delta_time = 1.0 ms because snippet times are detector stamps,
Hungarian at 0.5, plus graded best-agreement and merge-robust recall).

Two isosplit variants per session: gated (the curated resort layer that
feeds the figures) and all clusters (like-for-like with MS5's uncurated
output).

    uv run python notebooks/scratch_isosplit_vs_ms5.py

Output: data/derived/ns5/consensus/isosplit_vs_ms5.parquet
See docs/notes/consensus_vs_human.md (Q-009 context) and
docs/notes/snippet_sorting.md.
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))

from scratch_consensus_vs_ofs import (  # noqa: E402
    SR,
    compare_pair,
    estimate_lag,
    shift_sorting,
)

PROV = REPO / "data" / "derived" / "provenance"
OUT = REPO / "data" / "derived" / "ns5" / "consensus" / "isosplit_vs_ms5.parquet"


def isosplit_sorting(store: Path, gated_only: bool):
    """The snippet resort as a Sorting: (channel, isosplit label) units."""
    from spikeinterface.core import NumpySorting

    ev = pd.read_parquet(store / "events.parquet",
                         columns=["channel_id", "t_s",
                                  "label_isosplit_full"])
    keep: set[tuple[int, int]] | None = None
    if gated_only:
        uf = pd.read_parquet(store / "units_full.parquet")
        uf = uf[(uf.method == "isosplit_full") & uf.pass_gate.astype(bool)]
        keep = set(zip(uf.channel_id.astype(int), uf.unit_id.astype(int),
                       strict=True))
    frames, labels = [], []
    for (ch, k), g in ev.groupby(["channel_id", "label_isosplit_full"]):
        if keep is not None and (int(ch), int(k)) not in keep:
            continue
        frames.append((g.t_s.to_numpy() * SR).round().astype(np.int64))
        labels.append(np.full(len(g), f"ch{int(ch)}k{int(k)}"))
    if not frames:
        return None
    return NumpySorting.from_times_labels(
        [np.concatenate(frames)], [np.concatenate(labels)],
        sampling_frequency=SR)


def ms5_sorting(store: Path):
    """The stored MountainSort5 trains as a Sorting."""
    from spikeinterface.core import NumpySorting

    d = store / "modern" / "mountainsort5"
    if not (d / "spike_sample_index.npy").exists():
        return None
    samples = np.load(d / "spike_sample_index.npy")
    unit_idx = np.load(d / "spike_unit_index.npy")
    unit_ids = np.load(d / "unit_ids.npy")
    return NumpySorting.from_times_labels(
        [samples.astype(np.int64)],
        [np.array([str(unit_ids[i]) for i in unit_idx])],
        sampling_frequency=SR)


def main() -> int:
    rows = []
    for store in sorted(PROV.iterdir()):
        if not (store / "meta.json").exists():
            continue
        meta = json.load(open(store / "meta.json"))
        ms5 = ms5_sorting(store)
        if ms5 is None:
            print(f"{store.name}: no MS5 trains, skipped")
            continue
        iso_all = isosplit_sorting(store, gated_only=False)
        if iso_all is None:
            continue
        # one lag per session, estimated on the ungated (densest) variant
        lag, peak = estimate_lag(iso_all, [ms5])
        for variant, gated in (("gated", True), ("all", False)):
            iso = iso_all if not gated else isosplit_sorting(store, True)
            if iso is None or not len(iso.unit_ids):
                rows.append(dict(stem=meta["stem"],
                                 subject=meta.get("subject", "Rocky"), variant=variant,
                                 n_iso=0, lag_ms=lag * 1000, lag_peak=peak,
                                 candidate="mountainsort5",
                                 n_cand=len(ms5.unit_ids)))
                continue
            iso_sh = shift_sorting(iso, 0.0)      # iso is the reference
            ms5_sh = shift_sorting(ms5, lag)      # move MS5 onto NEV clock
            r = compare_pair(iso_sh, ms5_sh, "mountainsort5")
            rows.append(dict(stem=meta["stem"], subject=meta.get("subject", "Rocky"),
                             variant=variant, n_iso=len(iso.unit_ids),
                             lag_ms=lag * 1000, lag_peak=peak, **r))
            print(f"{store.name[:46]:46s} {variant:5s} iso {len(iso.unit_ids):3d} "
                  f"ms5 {r['n_cand']:3d}  matched {r['frac_ofs_matched']:.0%}"
                  f"  best_ag p50 {r['best_ag_p50']:.2f}"
                  f"  recall p50 {r['best_recall_p50']:.2f} "
                  f"p90 {r['best_recall_p90']:.2f}  (lag {lag*1000:+.1f} ms)")
    t = pd.DataFrame(rows)
    t.to_parquet(OUT, index=False)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

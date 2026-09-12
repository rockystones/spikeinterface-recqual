"""UnitRefine on a recording-backed SortingAnalyzer: the pilot snippets forbid.

`snippet_sorting.md` established that UnitRefine cannot work on the snippet
cohort -- seven of its features (`drift_*`, `spread`, `velocity_*`,
`exp_decay`) need continuous traces and imputing them saturates the classifier
at 99.98% noise. That was a statement about the *input*, not the classifier.

Four Fisk Medial ns6 stems survive with their sorter outputs and reachable
recordings, so here the analyzer is built properly and every feature is
computed for real. The question: **does UnitRefine become usable on Utah-pitch
data once its features exist?** 400 um pitch is still far from the
Neuropixels geometry it was trained on -- spread and velocity are computable
but nearly degenerate when no template spans neighbouring shanks -- so a
second saturation here would localise the failure to the geometry rather than
the missing features.

Run from repo root (first call downloads the models from HuggingFace):

    uv run python notebooks/scratch_unitrefine_pilot.py

See docs/notes/unitrefine_analyzer.md.
"""

from __future__ import annotations

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

from scratch_cohort_io import banner  # noqa: E402

WORK = REPO / "data" / "derived" / "ns5" / "work"
OUT = REPO / "data" / "derived" / "ns5"
STEMS = ["20240619-090527-Medial", "20230622-131651-Medial"]
# 450 um sparsity radius keeps the centre shank plus its neighbours, so the
# multi-channel features have something to measure at 400 um pitch
RADIUS_UM = 450.0


def pilot_one(stem: str) -> pd.DataFrame:
    """Analyzer, full metric set, UnitRefine labels for one retained sorting."""
    import spikeinterface.core as sc
    from spikeinterface.qualitymetrics import compute_quality_metrics
    from spikeinterface.sorters import read_sorter_folder

    # spykingcircus2 is retained for every pilot stem; mountainsort5 is
    # missing its log for one of them, so SC2 is the common denominator
    folder = WORK / f"{stem}__spykingcircus2"
    sorting = read_sorter_folder(folder, register_recording=False)
    rec = sc.load_extractor(folder / "spikeinterface_recording.json",
                            base_folder=folder)
    print(f"  {stem}: {len(sorting.unit_ids)} units, "
          f"{rec.get_num_channels()} ch, "
          f"{rec.get_total_duration():.0f} s")

    sa = sc.create_sorting_analyzer(
        sorting, rec, sparse=True, method="radius", radius_um=RADIUS_UM)
    sa.compute({
        "random_spikes": dict(max_spikes_per_unit=300),
        "waveforms": {},
        "templates": {},
        "noise_levels": {},
        "spike_amplitudes": {},
        # the classifier needs the PCA metric family (d_prime, nn_*,
        # isolation_distance, l_ratio, silhouette)
        "principal_components": dict(n_components=5,
                                     mode="by_channel_local"),
        "spike_locations": {},
        "unit_locations": {},
        "correlograms": {},
        "template_similarity": {},
    })
    from spikeinterface.postprocessing import compute_template_metrics
    compute_template_metrics(sa, include_multi_channel_metrics=True)
    compute_quality_metrics(sa)

    # SI 0.102.3 exposes the UnitRefine flow as `auto_label_units`, not the
    # `unitrefine_label_units` name CLAUDE.md sketches (a later release).
    # The models are also pickled under sklearn 1.4 while this project pins
    # 1.8, whose SimpleImputer.transform reads a private `_fill_dtype` the old
    # pickle lacks -- the same clash scratch_rocky_curation.py documents -- so
    # the models are loaded and driven manually with that attribute restored.
    from spikeinterface.curation import load_model

    trusted = ["numpy.dtype", "sklearn.pipeline.Pipeline"]
    qm = sa.get_extension("quality_metrics").get_data()
    tm = sa.get_extension("template_metrics").get_data()
    feats = qm.join(tm)

    d = pd.DataFrame(index=feats.index)
    for tag, repo in (("noise", "SpikeInterface/"
                       "UnitRefine_noise_neural_classifier"),
                      ("sua", "SpikeInterface/UnitRefine_sua_mua_classifier")):
        model, info = load_model(repo_id=repo, trusted=trusted)
        for _, step in getattr(model, "steps", []):
            if (step.__class__.__name__ == "SimpleImputer"
                    and not hasattr(step, "_fill_dtype")):
                stats = getattr(step, "statistics_", None)
                step._fill_dtype = (stats.dtype if stats is not None
                                    else np.dtype("float64"))
        lab_map = {int(k): v for k, v in info["label_conversion"].items()}
        need = list(model.feature_names_in_)
        x = feats.reindex(columns=need)
        missing = [c for c in need if feats.get(c) is None
                   or feats[c].isna().all()]
        print(f"    {tag}: {len(need) - len(missing)}/{len(need)} features "
              f"real, missing {missing if missing else 'none'}")
        d[f"{tag}_label"] = pd.Series(model.predict(x),
                                      index=feats.index).map(lab_map)
        d[f"{tag}_prob"] = model.predict_proba(x).max(axis=1)
    d["stem"] = stem
    d = d.reset_index().rename(columns={"index": "unit_id"})
    # carry SNR and rate so the labels can be judged against physics
    d = d.join(qm[["snr", "firing_rate"]].reset_index(drop=True))
    return d


def main() -> int:
    banner("UnitRefine with real features: four-shank-radius analyzers")
    frames = []
    for stem in STEMS:
        try:
            frames.append(pilot_one(stem))
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {stem}: {type(exc).__name__}: {exc}")
    if not frames:
        return 1
    d = pd.concat(frames, ignore_index=True)
    print()
    print(d.head(4).to_string())
    for c in ("noise_label", "sua_label"):
        print(f"\n  {c} counts:")
        print(d.groupby(["stem", c], observed=True).size().to_string())
    d.to_parquet(OUT / "unitrefine_pilot.parquet", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

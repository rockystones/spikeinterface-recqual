"""Preview figures + MATLAB inspection bundles for Rocky's outlier sessions.

The candidate set = the 27 manually-flagged sessions in
rocky/two_array_metrics.parquet (is_outlier, reasons recorded there)
plus the four residual candidates from the waveform-catalog work
(nav REF-003). For each candidate this script:

1. Ensures a session-preview page exists (same generator as
   figures/rocky/session_preview - scratch_session_preview.py, four
   panels at physical array positions) and copies it into
   figures/rocky/outlier_preview/ so the whole candidate set can be
   browsed in one folder. The sorted -01 chain is preferred; the two
   Dec-2018 "amplitude blowup" stems exist only unsorted and fall
   back to the original chain.

2. Exports a per-session MATLAB bundle to
   data/derived/rocky/outlier_inspect/<stem>/ - all parquet/JSON, no
   pickle (MATLAB reads them with parquetread/jsondecode):
     units.parquet     one row per sorted unit: channel_id, col, row,
                       unit, n_spikes, p2p_uv, noise_uv  (row k here
                       is row k of the waveform matrices)
     wf_mean.parquet   units x samples mean waveform, uV
     wf_lo.parquet     per-sample min envelope (same shape)
     wf_hi.parquet     per-sample max envelope
     session.json      stem, chain, date, array, reason, sr, nbefore,
                       sorting-free metrics, geometry (col/row per
                       channel incl. unit-less channels)
   plus a top-level index.json naming every exported session and its
   reason - the MATLAB script reads that to know what exists.

The deciding is done in matlab/rocky_outlier_inspect.m: edit its
sessionsToInspect list, run, and it regenerates the figure as a
native .fig per chosen session and leaves the unit + metric data in
the workspace.

Run: uv run python notebooks/scratch_outlier_inspect.py
"""

from __future__ import annotations

import json
import shutil
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scratch_session_preview import (  # noqa: E402
    build_worklist, load_geometry, preview_path, render_one,
    session_units)

REPO = Path(__file__).resolve().parent.parent
DER = REPO / "data" / "derived"
OUT_FIG = REPO / "figures" / "rocky" / "outlier_preview"
OUT_DATA = DER / "rocky" / "outlier_inspect"

# Residual candidates from the waveform catalog (nav REF-003), on top
# of the 27 is_outlier stems in two_array_metrics.parquet.
RESIDUALS = {
    "Rocky_Anterior_10-31-2017_Baseline":
        "REF-003 residual: 568 uV resort amplitude",
    "Rocky_Posterior_01-31-2020_Baseline_DigitalHeadstage":
        "REF-003 residual: 350 uV amplitude",
    "Rocky_Posterior_2023-01-13_Baseline_DigitalHeadstage":
        "REF-003 residual: late-life subset-method excursion",
    "Rocky_Posterior_2023-08-11_Baseline_DigitalHeadstage":
        "REF-003 residual: late-life subset-method excursion",
}


def candidates() -> dict[str, str]:
    """stem -> reason: the OUTLIERS master dict (covers rulings on
    stems outside the two-array universe), the metric table's flags,
    then the residuals."""
    from scratch_two_array_metrics import OUTLIERS
    t = pd.read_parquet(DER / "rocky" / "two_array_metrics.parquet")
    out = (t[t.is_outlier][["stem", "outlier_reason"]]
           .drop_duplicates().set_index("stem").outlier_reason)
    cand = dict(OUTLIERS)
    cand.update(out)
    cand.update(RESIDUALS)
    return cand


def export_bundle(job: dict, reason: str) -> dict:
    """One session's MATLAB-facing data folder; returns its index row."""
    stem = job["stem"]
    folder = OUT_DATA / stem
    folder.mkdir(parents=True, exist_ok=True)

    by_ch, free = session_units(Path(job["path"]))
    geo = load_geometry(job["subject"], job["array"], job["implant"])
    pos = geo.set_index("channel_id")[["col", "row"]]

    # row-aligned unit table + waveform matrices (row k <-> row k)
    rows, means, los, his = [], [], [], []
    for ch, units in sorted(by_ch.items()):
        for u in units:
            rows.append(dict(
                channel_id=ch,
                col=int(pos.loc[ch, "col"]) if ch in pos.index else -1,
                row=int(pos.loc[ch, "row"]) if ch in pos.index else -1,
                unit=u["unit"], n_spikes=u["n"], p2p_uv=u["p2p"],
                noise_uv=u["noise"]))
            means.append(u["mean"])
            los.append(u["lo"])
            his.append(u["hi"])
    units_df = pd.DataFrame(rows)
    units_df.to_parquet(folder / "units.parquet", index=False)
    n_samp = len(means[0]) if means else 0
    for name, arr in (("wf_mean", means), ("wf_lo", los),
                      ("wf_hi", his)):
        m = np.asarray(arr, dtype=np.float32) if arr else \
            np.zeros((0, n_samp), np.float32)
        pd.DataFrame(m, columns=[f"s{i:03d}" for i in range(m.shape[1])]
                     ).to_parquet(folder / f"{name}.parquet",
                                  index=False)

    meta = dict(stem=stem, chain=job["chain"], date=str(job["date"]),
                array=job["array"], headstage=job.get("headstage"),
                reason=reason, n_units=len(rows),
                n_samples=n_samp, free=free,
                geometry=geo[["channel_id", "col", "row", "label"]]
                .to_dict("records"),
                serial=geo.attrs.get("serial"),
                nev=str(Path(job["path"]).name))
    (folder / "session.json").write_text(json.dumps(meta, indent=1),
                                         encoding="utf-8")
    return dict(stem=stem, chain=job["chain"], date=str(job["date"]),
                array=job["array"], reason=reason, n_units=len(rows))


def main() -> int:
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    inv = pd.read_parquet(DER / "monkey_inventory.parquet")
    cand = candidates()
    print(f"{len(cand)} candidate sessions")

    index = []
    for stem, reason in cand.items():
        jobs = build_worklist(inv, None, stem)
        if not jobs:
            print(f"  MISSING from inventory: {stem}")
            continue
        # prefer the sorted -01 chain, else the original unsorted file
        job = next((j for j in jobs if j["chain"] == "-01"),
                   next((j for j in jobs if j["chain"] == ""), jobs[0]))

        # 1. preview page: render if absent, then copy to the browse dir
        src = preview_path(job)
        if not src.exists():
            print(f"  rendering preview {src.name}")
            print("   ", render_one(job))
        if src.exists():
            shutil.copy2(src, OUT_FIG / src.name)

        # 2. MATLAB bundle (skip if already exported - reruns only add
        #    newly flagged stems; delete a folder to force re-export)
        done = OUT_DATA / stem / "session.json"
        if done.exists():
            meta = json.loads(done.read_text(encoding="utf-8"))
            index.append(dict(stem=stem, chain=meta["chain"],
                              date=meta["date"], array=meta["array"],
                              reason=reason,
                              n_units=meta["n_units"]))
            continue
        index.append(export_bundle(job, reason))
        print(f"  {stem}{job['chain']}: {index[-1]['n_units']} units")

    (OUT_DATA / "index.json").write_text(
        json.dumps(index, indent=1), encoding="utf-8")
    print(f"\n{len(index)} bundles -> {OUT_DATA}")
    print(f"previews -> {OUT_FIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

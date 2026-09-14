"""Materialize the full derivation chain for representative Rocky sessions.

The derived tables keep per-unit metrics but not per-spike assignments
(docs/notes/data_inspection.md, grain caveat). For validation the owner wants
the intermediate steps on disk for a few sessions: which waveform went to
which unit, under which method, and how the unit metrics and the
sorting-free metrics fall out of them.

Everything the original pipelines did is re-run here with the SAME imported
functions and the SAME seeds (random_state=0 throughout scratch_rocky_methods
/ scratch_rocky_resort), so the regenerated assignments are reproductions,
not approximations - and each layer is cross-checked against the stored
tables before it is written.

Per session under data/derived/provenance/<stem>/:

  meta.json                sr, nbefore, gain, duration, gate constants
  events.parquet           one row per snippet: channel, time, sample,
                           plexon (ofs) unit, vmin/vmax/absamp, full-data
                           ISO-SPLIT label (resort-style)
  waveforms.npy            (n_events, 30) float32 uV, row-aligned to events
  electrodes.parquet       per channel: n_events, baseline noise
  subsample.parquet        the seeded 4000-per-electrode subsample the five
                           methods actually clustered: global event_idx,
                           PCA features, one label column per method
  units_methods.parquet    per-unit rows rebuilt with the same build_row
  units_full.parquet       per-unit rows for full-data ISO-SPLIT and ofs
  free_electrode.parquet   sorting-free per-electrode metrics re-derived
                           from events.parquet
  official_*.parquet       the stored rows for this (date, array), copied
                           next to the regenerated ones for comparison
  modern/<sorter>/         (consensus stems only) spike_sample_index.npy,
                           spike_unit_index.npy, unit_ids.npy (plain int64),
                           templates.npy (units x samples x 96 ch, uV),
                           peak_channel_index.npy, sample_waveforms.npz
                           (up to 100 peak-channel snippets per unit)

Run from repo root (30-60 min):

    uv run python notebooks/scratch_provenance_dump.py

MATLAB re-derivation and comparison: matlab/rocky_provenance.m.
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

from scratch_cohort_io import banner  # noqa: E402
from scratch_rocky_methods import CLUSTERERS, CLUSTER_SUBSAMPLE, build_row  # noqa: E402
from scratch_rocky_resort import (  # noqa: E402
    ISI_REFRACTORY_MS,
    MIN_SNR,
    MIN_SPIKES,
    N_PCA,
    PLEXON_DROP_UNITS,
    PT_MS_MAX,
    PT_MS_MIN,
    TROUGH_TOL_MS,
    align_on_trough,
    baseline_noise_uv,
    open_nev,
    read_electrode,
    unit_metrics,
)
from sklearn.decomposition import PCA  # noqa: E402

OUT_ROOT = REPO / "data" / "derived" / "provenance"
DER = REPO / "data" / "derived"

# Era-spanning picks. The three consensus stems also carry the modern
# four-sorter spike trains; the 2018-04-12 session is the giant-event
# gallery session (snippet layers only).
SESSIONS = [
    dict(stem="Rocky_Anterior_02-22-2018_Baseline",
         date="2018-02-22", array="Anterior", implant="I1", consensus=True),
    dict(stem="Rocky_Posterior_04-12-2018_Baseline",
         date="2018-04-12", array="Posterior", implant="I1", consensus=False),
    dict(stem="Rocky_Posterior_2023-09-29_Baseline_DigitalHeadstage",
         date="2023-09-29", array="Posterior", implant="I1", consensus=True),
    dict(stem="Rocky_Anterior_2025-05-02_Baseline_DigitalHeadstage",
         date="2025-05-02", array="Anterior", implant="I2", consensus=True),
    # in the 60-session methods subset: enables the direct regenerated-vs-
    # stored unit-count cross-check the other four dates cannot provide
    dict(stem="Rocky_Anterior_03-22-2018_Baseline",
         date="2018-03-22", array="Anterior", implant="I1", consensus=False),
    # Nigel and Fisk (nav W-018): early-healthy and late pairs, all on
    # consensus stems so the modern spike trains ride along. ev_array is
    # the array label that subject's events_electrode table uses.
    dict(stem="Nigel_Anterior_2023-03-24_Baseline_DigitalHeadstage",
         subject="Nigel", date="2023-03-24", array="Anterior",
         implant="I1", consensus=True),
    dict(stem="Nigel_Posterior_2024-10-01_Baseline_DigitalHeadstage",
         subject="Nigel", date="2024-10-01", array="Posterior",
         implant="I1", consensus=True),
    dict(stem="20230605-132052-Lateral",
         subject="Fisk", date="2023-06-05", array="Lateral",
         ev_array="SN1498", implant="I1", consensus=True),
    dict(stem="20250507-095730-Medial3Min",
         subject="Fisk", date="2025-05-07", array="Medial",
         ev_array="SN1504", implant="I1", consensus=True),
]

SORTERS = ["mountainsort5", "kilosort4", "spykingcircus2", "tridesclous2"]
MAX_SAMPLE_WF = 100          # peak-channel snippets kept per modern unit


BASE_NEV_ROOT = Path(r"C:\MyData\Monkeydata\Rocky\Blackrock")


def nev_path_for(stem: str, implant: str,
                 subject: str = "Rocky") -> tuple[Path, bool]:
    """A readable NEV for one stem, preferring the Plexon -01 chain.

    Returns ``(path, has_ofs)``. The Rocky NEV estate moved from
    D:\\Claude Code\\Rocky to D:\\Claude Code\\Monkey Data\\Rocky around
    2026-09-13 with subfolders restructured (nav I-003, resolved);
    session_index.parquet was remapped by unique basename and re-verified
    886/886. The base-NEV fallback under C:\\MyData remains for resilience:
    those files carry the identical event set (verified in the flow: "the
    Plexon -01 file holds the same events as the original") but no Offline
    Sorter labels, so ``has_ofs`` gates the ofs layers.
    """
    if subject == "Rocky":
        ix = pd.read_parquet(DER / "rocky" / "session_index.parquet")
        hit = ix[(ix.kind == "OFS") & (ix.stem.astype(str) == stem + "-01")]
        if len(hit) and Path(hit.path.iloc[0]).exists():
            return Path(hit.path.iloc[0]), True
    from scratch_ns5_resort import INV, build_worklist
    for j in build_worklist(pd.read_parquet(INV)):
        if j["stem"] == stem and j.get("nev") and Path(j["nev"]).exists():
            return Path(j["nev"]), True          # worklist nevs are -01
    if subject == "Rocky":
        base = BASE_NEV_ROOT / f"{stem}.nev"
        if base.exists():
            return base, False
    raise FileNotFoundError(f"no readable NEV for {stem}")


# %%
# === Layers A-D: snippet estate ==========================================
def dump_snippet_layers(sess: dict, out: Path) -> None:
    """Events + waveforms, seeded five-method subsample, full ISO-SPLIT, ofs."""
    nev, has_ofs = nev_path_for(sess["stem"], sess["implant"],
                                sess.get("subject", "Rocky"))
    raw, nmeta, chan_by_elec = open_nev(nev)
    sr, nbefore, dur = nmeta["sr"], nmeta["nbefore"], nmeta["duration_s"]

    ev_rows, wf_all, elec_rows = [], [], []
    sub_rows, unit_m_rows, unit_f_rows = [], [], []
    offset = 0

    for elec in sorted(chan_by_elec):
        e = read_electrode(raw, nmeta, chan_by_elec[elec])
        if e is None or len(e["t"]) < MIN_SPIKES:
            continue
        wf_raw, t, pu = e["wf"], e["t"], e["plexon_unit"]
        noise = baseline_noise_uv(wf_raw, nbefore)
        wf = align_on_trough(wf_raw, nbefore)
        n = len(t)

        # full-data ISO-SPLIT (the resort-style labels), same PCA as methods
        n_pc = min(N_PCA, wf.shape[1], max(2, n - 1))
        feats_full = PCA(n_components=n_pc, random_state=0).fit_transform(wf)
        lab_full = CLUSTERERS["isosplit"](feats_full)

        vmin = wf_raw.min(axis=1)
        vmax = wf_raw.max(axis=1)
        ev_rows.append(pd.DataFrame(dict(
            event_idx=np.arange(offset, offset + n, dtype=np.int64),
            channel_id=np.full(n, int(elec), dtype=np.int32),
            t_s=t, sample=(t * sr).round().astype(np.int64),
            plexon_unit=pu.astype(np.int32),
            vmin_uv=vmin.astype(np.float32), vmax_uv=vmax.astype(np.float32),
            absamp_uv=np.maximum(np.abs(vmin), vmax).astype(np.float32),
            label_isosplit_full=lab_full.astype(np.int32))))
        wf_all.append(wf_raw.astype(np.float32))
        elec_rows.append(dict(channel_id=int(elec), n_events=n,
                              noise_uv=float(noise)))

        # per-unit rows for the full labels and for Plexon's own labels
        for k in np.unique(lab_full):
            r = unit_metrics(wf[lab_full == k], t[lab_full == k],
                             noise, sr, nbefore, dur)
            unit_f_rows.append({**r, "method": "isosplit_full",
                                "channel_id": int(elec), "unit_id": int(k)})
        if has_ofs:
            for u in np.unique(pu):
                if u in PLEXON_DROP_UNITS:
                    continue
                sel = pu == u
                r = unit_metrics(wf[sel], t[sel], noise, sr, nbefore, dur)
                unit_f_rows.append({**r, "method": "ofs",
                                    "channel_id": int(elec),
                                    "unit_id": int(u)})

        # the seeded subsample the five methods actually saw
        if n > CLUSTER_SUBSAMPLE:
            idx = np.random.default_rng(0).choice(n, CLUSTER_SUBSAMPLE,
                                                  replace=False)
            idx.sort()
        else:
            idx = np.arange(n)
        feats, wf_s, t_s, pu_s = feats_full[idx], wf[idx], t[idx], pu[idx]

        sub = pd.DataFrame(dict(
            channel_id=np.full(len(idx), int(elec), dtype=np.int32),
            event_idx=(idx + offset).astype(np.int64)))
        for c in range(feats.shape[1]):
            sub[f"pc{c + 1}"] = feats[:, c].astype(np.float32)
        for mname, fn in CLUSTERERS.items():
            lab = fn(feats)
            sub[f"label_{mname}"] = lab.astype(np.int32)
            for k in np.unique(lab):
                r = build_row(wf_s, t_s, feats, lab, k, noise, sr, nbefore, dur)
                unit_m_rows.append({**r, "method": mname,
                                    "channel_id": int(elec), "unit_id": int(k),
                                    "n_spikes_electrode": len(idx)})
        # Plexon scored on the same subsample, as in the methods table
        if has_ofs:
            for u in np.unique(pu_s):
                if u in PLEXON_DROP_UNITS or (pu_s == u).sum() < 3:
                    continue
                lab_ofs = np.where(pu_s == u, 1, 0)
                r = build_row(wf_s, t_s, feats, lab_ofs, 1,
                              noise, sr, nbefore, dur)
                unit_m_rows.append({**r, "method": "ofs",
                                    "channel_id": int(elec),
                                    "unit_id": int(u),
                                    "n_spikes_electrode": len(idx)})
        sub_rows.append(sub)
        offset += n

    ev = pd.concat(ev_rows, ignore_index=True)
    ev.to_parquet(out / "events.parquet", index=False)
    np.save(out / "waveforms.npy",
            np.concatenate(wf_all, axis=0).astype(np.float32))
    pd.DataFrame(elec_rows).to_parquet(out / "electrodes.parquet", index=False)
    pd.concat(sub_rows, ignore_index=True).to_parquet(
        out / "subsample.parquet", index=False)
    pd.DataFrame(unit_m_rows).to_parquet(out / "units_methods.parquet",
                                         index=False)
    pd.DataFrame(unit_f_rows).to_parquet(out / "units_full.parquet",
                                         index=False)

    # sorting-free per-electrode metrics, re-derived from the event table
    free = []
    for elec, g in ev.groupby("channel_id"):
        # official events_electrode uses |trough| for the amp percentiles
        # ("comparable with the sorted tables"); absamp = max(|vmin|, vmax)
        # is the giant/artifact amplitude and stays in events.parquet
        a = np.abs(g.vmin_uv.to_numpy())
        noise = next(r["noise_uv"] for r in elec_rows
                     if r["channel_id"] == elec)
        free.append(dict(
            channel_id=int(elec), n_events=len(g),
            crossing_rate_hz=len(g) / dur, noise_uv=noise,
            amp_p50=float(np.percentile(a, 50)),
            amp_p90=float(np.percentile(a, 90)),
            amp_p99=float(np.percentile(a, 99)),
            amp_max=float(a.max()),
            peak_snr=float(np.percentile(a, 99) / noise) if noise > 0
            else np.nan))
    pd.DataFrame(free).to_parquet(out / "free_electrode.parquet", index=False)

    json.dump(dict(
        stem=sess["stem"], subject=sess.get("subject", "Rocky"),
        date=sess["date"], array=sess["array"],
        implant=sess["implant"], nev=str(nev), has_ofs=bool(has_ofs),
        sr=sr, nbefore=int(nbefore),
        duration_s=dur, n_events=int(len(ev)),
        gate=dict(MIN_SPIKES=MIN_SPIKES, MIN_SNR=MIN_SNR,
                  PT_MS_MIN=PT_MS_MIN, PT_MS_MAX=PT_MS_MAX,
                  TROUGH_TOL_MS=TROUGH_TOL_MS,
                  ISI_REFRACTORY_MS=ISI_REFRACTORY_MS),
        n_pca=N_PCA, cluster_subsample=CLUSTER_SUBSAMPLE,
        notes="waveforms.npy rows align with events.parquet; alignment for "
              "metrics used align_on_trough, waveforms.npy is the raw "
              "(pre-alignment) snippet; synchrony columns not refilled here",
    ), open(out / "meta.json", "w"), indent=1)
    print(f"    events {len(ev):,}  electrodes {len(elec_rows)}  "
          f"method-units {len(unit_m_rows)}  full-units {len(unit_f_rows)}")


# %%
# === Cross-checks against the stored tables ==============================
def crosscheck(sess: dict, out: Path) -> None:
    """Copy the official rows next to the regenerated ones and compare."""
    d8 = sess["date"]
    subject = sess.get("subject", "Rocky")
    ev_arr = sess.get("ev_array", sess["array"])

    ml = pd.DataFrame()
    if subject == "Rocky":
        ml = pd.read_parquet(DER / "rocky" / "methods_long.parquet")
        ml = ml[(ml.date.astype(str) == d8) & (ml.array == sess["array"])]
        ml.to_parquet(out / "official_methods_long.parquet", index=False)

    ee_dir = ("rocky_i2" if subject == "Rocky" and sess["implant"] == "I2"
              else subject.lower() if subject != "Rocky" else "rocky")
    ee = pd.read_parquet(DER / ee_dir / "events_electrode.parquet")
    ee = ee[(ee.date.astype(str) == d8) & (ee.array == ev_arr)]
    ee.to_parquet(out / "official_events_electrode.parquet", index=False)

    if subject == "Rocky":
        ss = pd.read_parquet(DER / "rocky" / "session_summary.parquet")
        ss = ss[(ss.date.astype(str) == d8) & (ss.array == sess["array"])]
    else:
        ss = ee.head(0)      # placeholder keeps the MATLAB loader uniform
    ss.to_parquet(out / "official_session_summary.parquet", index=False)

    if len(ml):
        mine = pd.read_parquet(out / "units_methods.parquet")
        a = mine.groupby("method").size()
        b = ml.groupby("method").size()
        cmpdf = pd.DataFrame(dict(regenerated=a, stored=b)).fillna(0).astype(int)
        print("    unit counts per method, regenerated vs stored:")
        print(cmpdf.to_string().replace("\n", "\n    "))
    else:
        print("    (no stored methods_long rows for this date - "
              "not in the 60-session methods subset)")


# %%
# === Layer E: modern pool for consensus stems ============================
def dump_modern(sess: dict, out: Path) -> None:
    """Split spike trains to plain arrays; extract templates from the ns5."""
    import spikeinterface.core as sc
    from scratch_ns5_resort import (FILTER_FREQ_HZ, FILTER_ORDER, INV,
                                    build_worklist, open_recording)
    from spikeinterface.preprocessing import highpass_filter

    job = next((j for j in build_worklist(pd.read_parquet(INV))
                if j["stem"] == sess["stem"]), None)
    if job is None or not Path(job["ns5"]).exists():
        print("    ! recording offline; spike trains split, templates skipped")
        job = None

    for sorter in SORTERS:
        src = DER / "ns5" / "consensus" / "sortings" / sess["stem"] / sorter
        if not src.exists():
            continue
        dst = out / "modern" / sorter
        dst.mkdir(parents=True, exist_ok=True)
        if (dst / "templates.npy").exists():
            print(f"    modern/{sorter}: already extracted, skipped")
            continue
        spikes = np.load(src / "spikes.npy")
        np.save(dst / "spike_sample_index.npy",
                spikes["sample_index"].astype(np.int64))
        np.save(dst / "spike_unit_index.npy",
                spikes["unit_index"].astype(np.int64))
        sorting = sc.load(src)
        np.save(dst / "unit_ids.npy", np.asarray(sorting.unit_ids,
                                                 dtype=np.int64))
        if job is None:
            continue

        rec, _info = open_recording(Path(job["ns5"]), Path(job["cmp"]))
        rec = highpass_filter(rec, freq_min=FILTER_FREQ_HZ,
                              filter_order=FILTER_ORDER)
        sa = sc.create_sorting_analyzer(sorting, rec, sparse=False)
        sa.compute({"random_spikes": dict(max_spikes_per_unit=150),
                    "waveforms": {}, "templates": {}})
        tmpl = sa.get_extension("templates").get_data()      # (u, s, c) uV
        np.save(dst / "templates.npy", tmpl.astype(np.float32))
        peak_ch = np.argmin(tmpl.min(axis=1), axis=1) \
            if tmpl.ndim == 3 else np.zeros(len(sorting.unit_ids), int)
        # peak channel = channel of the deepest trough of each template
        peak_ch = np.array([int(np.unravel_index(np.argmin(tmpl[u]),
                                                 tmpl[u].shape)[1])
                            for u in range(tmpl.shape[0])])
        np.save(dst / "peak_channel_index.npy", peak_ch.astype(np.int64))

        wfx = sa.get_extension("waveforms")
        samples, sidx = [], []
        for ui, uid in enumerate(sorting.unit_ids):
            w = wfx.get_waveforms_one_unit(uid)              # (n, s, c)
            w = w[:MAX_SAMPLE_WF, :, peak_ch[ui]]
            samples.append(w.astype(np.float32))
            sidx.append(np.full(len(w), ui, dtype=np.int32))
        np.savez_compressed(dst / "sample_waveforms.npz",
                            wf=np.concatenate(samples, axis=0),
                            unit_index=np.concatenate(sidx))
        print(f"    modern/{sorter}: {len(sorting.unit_ids)} units, "
              f"templates {tmpl.shape}, samples saved")
        del sa, rec


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--stems", default="", help="comma-separated stems; default all")
    args = ap.parse_args()
    want = {x.strip() for x in args.stems.split(",") if x.strip()}
    todo = [s for s in SESSIONS if not want or s["stem"] in want]
    for sess in todo:
        banner(f"{sess['stem']}  ({sess['implant']}, "
               f"consensus={sess['consensus']})")
        out = OUT_ROOT / sess["stem"]
        out.mkdir(parents=True, exist_ok=True)
        dump_snippet_layers(sess, out)
        crosscheck(sess, out)
        if sess["consensus"]:
            dump_modern(sess, out)
    print("\nprovenance store complete:", OUT_ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

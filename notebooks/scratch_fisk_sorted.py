"""Fisk's sorted layer, and impedance against unit yield per electrode.

`<SN>/Sorted/` holds 73 Plexon `-01` NEVs per array beside the unsorted
originals, so Fisk has a sorting-based layer without re-sorting anything.

This is the version [[fisk_impedance]] asked for. The sorting-free join could
only ask whether a high-impedance electrode crosses threshold less often; this
asks whether it **yields fewer sortable units**, which is the question the
multimodal thread in CLAUDE.md is actually about.

Two things are held to deliberately:

- **Per electrode, within a session.** Impedance varies across the array and so
  does yield; correlating their session medians would throw away the only
  contrast that controls for date, amplifier and threshold.
- **Same-day impedance only**, and pooled on each channel's median across
  dates as well, because a single AutoImpedance reading crosses the 1 MOhm line
  a median of seven times over the series and cannot classify an electrode.

Run from repo root:

    uv run python notebooks/scratch_fisk_sorted.py [--jobs 2]

Writes `data/derived/fisk/sorted_units.parquet` and
`data/derived/fisk/sorted_impedance.parquet`.

See:
- docs/notes/fisk_impedance.md
"""

from __future__ import annotations

import argparse
import re
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from _paths import FISK  # noqa: E402
from scratch_rocky_resort import (  # noqa: E402
    baseline_noise_uv,
    open_nev,
    read_electrode,
)

OUT_DIR = REPO / "data" / "derived" / "fisk"
IMP = OUT_DIR / "impedance.parquet"
UNITS_OUT = OUT_DIR / "sorted_units.parquet"
JOIN_OUT = OUT_DIR / "sorted_impedance.parquet"

ARRAYS = {"SN1498": "Lateral", "SN1504": "Medial"}
# `20230605-132052-001-01.nev` -> date 20230605
DATE_RE = re.compile(r"^(\d{8})-")
NOT_A_UNIT = (0, 255)
SNR_GATE = 4.0


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === One sorted NEV, per electrode ===
def electrode_metrics(job: dict) -> pd.DataFrame:
    """Units, amplitude, SNR and rate for every electrode of one sorted NEV."""
    base = {k: v for k, v in job.items() if k != "nev"}
    try:
        raw, meta, chan_by_elec = open_nev(Path(job["nev"]))
        nbefore, dur = meta["nbefore"], meta["duration_s"]
        rows = []
        for elec in sorted(chan_by_elec):
            e = read_electrode(raw, meta, chan_by_elec[elec])
            if e is None or not len(e["t"]):
                rows.append(dict(**base, channel=int(elec), n_units=0,
                                 n_spikes=0, noise_uv=np.nan,
                                 amp_med=np.nan, snr=np.nan, rate_hz=0.0,
                                 n_gated=0))
                continue
            wf, pu = e["wf"], e["plexon_unit"]
            noise = baseline_noise_uv(wf, nbefore)
            keep = ~np.isin(pu, NOT_A_UNIT)
            units = sorted(set(pu[keep].tolist()))
            amps, gated = [], 0
            for u in units:
                m = pu == u
                a = float(np.median(np.abs(wf[m].min(axis=1))))
                amps.append(a)
                if noise > 0 and a / noise >= SNR_GATE:
                    gated += 1
            rows.append(dict(
                **base, channel=int(elec), n_units=len(units),
                n_spikes=int(keep.sum()), noise_uv=noise,
                amp_med=float(np.median(amps)) if amps else np.nan,
                snr=float(np.median(amps) / noise)
                if amps and noise > 0 else np.nan,
                rate_hz=float(keep.sum() / dur) if dur else np.nan,
                n_gated=gated,
            ))
        return pd.DataFrame(rows)
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame([dict(**base, error=f"{type(exc).__name__}: "
                                                f"{exc}"[:120])])


def build_worklist() -> list[dict]:
    jobs: list[dict] = []
    for serial, anatomy in ARRAYS.items():
        sorted_dir = FISK / serial / "Sorted"
        if not sorted_dir.is_dir():
            continue
        # rglob, not glob: the NEVs sit in `Sorted/Exported/` while the
        # `.wfexp.mat` sit directly in `Sorted/`, so a non-recursive glob
        # finds the folder non-empty and the worklist empty.
        for nev in sorted(sorted_dir.rglob("*.nev")):
            m = DATE_RE.match(nev.name)
            if not m:
                continue
            jobs.append(dict(
                subject="Fisk", array=anatomy, serial=serial,
                session=nev.stem, nev=str(nev),
                date=str(pd.to_datetime(m.group(1), format="%Y%m%d").date()),
            ))
    return jobs


def report(u: pd.DataFrame, j: pd.DataFrame) -> None:
    ok = u[u.get("error").isna()] if "error" in u else u
    banner("1. The sorted layer")
    print(f"  electrode-rows: {len(ok)}   sessions: {ok.session.nunique()}")
    per_sess = ok.groupby(["array", "session", "date"]).agg(
        units=("n_units", "sum"), gated=("n_gated", "sum"),
        elec_with_units=("n_units", lambda s: int((s > 0).sum())),
        amp=("amp_med", "median"), snr=("snr", "median")).reset_index()
    print(per_sess.groupby("array").agg(
        sessions=("session", "size"), units=("units", "median"),
        gated=("gated", "median"), elec=("elec_with_units", "median"),
        amp=("amp", "median"), snr=("snr", "median")).round(2).to_string())

    banner("2. Longitudinal, from the sorted layer")
    for arr, g in per_sess.groupby("array"):
        print(f"  {arr}  n={len(g)}")
        for m in ("units", "gated", "elec_with_units", "amp", "snr"):
            # dropna per metric: one session whose electrodes all lack units
            # gives a NaN median, and `spearmanr` propagates it to the whole
            # correlation. One Lateral session did exactly that and silently
            # voided two trends.
            d = g.dropna(subset=[m])
            if len(d) < 8:
                continue
            r, p = spearmanr(pd.to_datetime(d.date)
                             .map(pd.Timestamp.toordinal), d[m])
            print(f"    {m:16s} rho {r:+.3f}  p={p:.3g}"
                  + ("" if len(d) == len(g) else f"   (n={len(d)})"))

    if not len(j):
        return
    banner("3. Impedance against UNIT YIELD, per electrode")
    print("  The question the sorting-free join could not ask.\n")
    res = []
    for (arr, sess), g in j.groupby(["array", "session"]):
        v = g.dropna(subset=["kohm"])
        if len(v) < 30:
            continue
        row = dict(array=arr, session=sess)
        for m in ("n_units", "n_gated", "snr", "amp_med"):
            vv = v.dropna(subset=[m])
            if len(vv) < 30 or vv[m].nunique() < 3:
                continue
            row[m], _ = spearmanr(vv.kohm, vv[m])
        res.append(row)
    r = pd.DataFrame(res)
    if len(r):
        print(f"  {'metric':12s} {'median rho':>11s} {'IQR':>18s} "
              f"{'sessions':>9s}")
        for m in ("n_units", "n_gated", "snr", "amp_med"):
            if m not in r:
                continue
            s = r[m].dropna()
            if not len(s):
                continue
            print(f"  {m:12s} {s.median():11.3f} "
                  f"{s.quantile(0.25):8.3f}-{s.quantile(0.75):.3f} "
                  f"{len(s):9d}")

    banner("4. Pooled on each channel's median impedance")
    imp = pd.read_parquet(IMP)
    med_i = (imp.groupby(["array", "channel"]).kohm.median()
             .rename("kohm_med").reset_index())
    med_u = (j.groupby(["array", "channel"])
             [["n_units", "n_gated", "snr", "amp_med"]].median().reset_index())
    pool = med_i.merge(med_u, on=["array", "channel"], how="inner")
    for arr, g in pool.groupby("array"):
        print(f"  {arr}  (n = {len(g)} electrodes)")
        for m in ("n_units", "n_gated", "snr", "amp_med"):
            v = g.dropna(subset=["kohm_med", m])
            if len(v) < 20:
                continue
            rho, p = spearmanr(v.kohm_med, v[m])
            print(f"    kohm vs {m:9s} rho {rho:+.3f}  p={p:.3g}")
        print()

    banner("5. High vs low impedance, on unit yield")
    hi, lo = pool[pool.kohm_med >= 1000], pool[pool.kohm_med < 1000]
    print(f"  {'group':20s} {'n':>4s} {'units':>7s} {'gated':>7s} "
          f"{'snr':>7s} {'amp':>7s}")
    for lab, g in (("median >= 1 MOhm", hi), ("median < 1 MOhm", lo)):
        if not len(g):
            continue
        print(f"  {lab:20s} {len(g):4d} {g.n_units.median():7.2f} "
              f"{g.n_gated.median():7.2f} {g.snr.median():7.2f} "
              f"{g.amp_med.median():7.1f}")
    if len(hi) > 5 and len(lo) > 5:
        for m in ("n_units", "n_gated"):
            _, p = mannwhitneyu(hi[m].dropna(), lo[m].dropna())
            print(f"    {m}: p = {p:.3g}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    jobs = build_worklist()
    if args.limit:
        jobs = jobs[:args.limit]
    banner("Fisk sorted layer -- Plexon -01 NEVs")
    print(f"  sessions: {len(jobs)}")

    frames = []
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for i, f in enumerate(ex.map(electrode_metrics, jobs, chunksize=1), 1):
            frames.append(f)
            if i % 20 == 0:
                print(f"    {i}/{len(jobs)}", flush=True)
    u = pd.concat(frames, ignore_index=True)

    imp = pd.read_parquet(IMP)
    imp["day"] = imp.date.dt.strftime("%Y-%m-%d")
    j = u.merge(imp[["array", "day", "channel", "kohm"]],
                left_on=["array", "date", "channel"],
                right_on=["array", "day", "channel"], how="inner")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    u.to_parquet(UNITS_OUT, engine="pyarrow", index=False)
    if len(j):
        j.to_parquet(JOIN_OUT, engine="pyarrow", index=False)
    report(u, j)
    print(f"\n  wrote {UNITS_OUT}  ({len(u)} rows)")
    print(f"  wrote {JOIN_OUT}  ({len(j)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

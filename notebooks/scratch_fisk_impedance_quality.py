"""Does impedance predict recording quality? Fisk, per electrode, same day.

The first test of CLAUDE.md's multimodal premise -- that quality metrics should
be reported against electrode properties rather than against anonymous channel
indices -- now that both sides exist on the same days.

**Per channel, not per session.** A session-level correlation between median
impedance and median noise would be answering a much weaker question and would
be dominated by whatever else changed between dates. The interesting claim is
that *this electrode*, measured at 800 kOhm this morning, has a worse noise
floor and fewer crossings than its neighbour at 300 kOhm in the same recording.
That is a within-session comparison and it controls for date, animal, amplifier
and threshold automatically.

**Same-day only.** [[fisk_impedance]] shows a channel crosses the 1 MOhm line a
median of seven times across the series, so impedance is not stable enough to
carry across a gap; a nearest-date join would be joining to noise.

**Both the reading and the pairing are noisy, and the design says so.** Because
impedance bounces, a single-day correlation understates any real relationship.
So the per-day correlations are reported *and* a pooled version using each
channel's median impedance across all dates, which averages the measurement
noise down. If the relationship is real the pooled version should be stronger.

Run from repo root:

    uv run python notebooks/scratch_fisk_impedance_quality.py [--jobs 2]

Writes `data/derived/fisk/impedance_quality.parquet`.

See:
- docs/notes/fisk_impedance.md
"""

from __future__ import annotations

import argparse
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_cohort_io import PROBE_DIR  # noqa: E402
from scratch_ns5_resort import (  # noqa: E402
    FILTER_FREQ_HZ,
    FILTER_ORDER,
    summarise_error,
)
from scratch_rocky_ns5_free import DETECT_K, REFRACTORY_MS  # noqa: E402

FISK_DIR = REPO / "data" / "derived" / "fisk"
IMP = FISK_DIR / "impedance.parquet"
SESS = FISK_DIR / "fisk_sessions.parquet"
OUT = FISK_DIR / "impedance_quality.parquet"

SLICE_S = 120.0


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === Per-channel quality for one session ===
def channel_quality(job: dict) -> pd.DataFrame:
    """Noise, crossing rate and amplitude for every channel of one .ns6."""
    from spikeinterface.core import get_noise_levels
    from spikeinterface.preprocessing import highpass_filter
    from spikeinterface.sortingcomponents.peak_detection import detect_peaks

    from scratch_ns5_resort import open_recording

    base = {k: v for k, v in job.items() if k not in ("ns6", "cmp")}
    try:
        rec, _ = open_recording(Path(job["ns6"]), Path(job["cmp"]))
        fs = rec.get_sampling_frequency()
        n = min(rec.get_num_frames(), int(SLICE_S * fs))
        rec_f = highpass_filter(rec.frame_slice(0, n),
                                freq_min=FILTER_FREQ_HZ,
                                filter_order=FILTER_ORDER)
        dur = n / fs
        noise_uv = np.asarray(get_noise_levels(
            rec_f, method="mad", return_scaled=True, force_recompute=True))
        noise_raw = np.asarray(get_noise_levels(
            rec_f, method="mad", return_scaled=False, force_recompute=True))
        peaks = detect_peaks(
            rec_f, method="by_channel", peak_sign="neg",
            detect_threshold=DETECT_K, exclude_sweep_ms=REFRACTORY_MS,
            noise_levels=noise_raw, progress_bar=False)
        ch = peaks["channel_index"]
        gain = float(np.median(noise_uv / np.where(noise_raw == 0, np.nan,
                                                   noise_raw)))
        amp_uv = np.abs(peaks["amplitude"].astype(float)) * gain

        # Channel ids are the mapfile's, so the join to impedance is on the
        # electrode the rig numbered, not on a positional index.
        ids = [int(c) for c in rec_f.channel_ids]
        rows = []
        for i, cid in enumerate(ids):
            m = ch == i
            a = amp_uv[m]
            rows.append(dict(
                **base, channel=cid,
                noise_uv=float(noise_uv[i]),
                n_crossings=int(m.sum()),
                rate_hz=float(m.sum() / dur),
                amp_med=float(np.median(a)) if a.size else np.nan,
                snr=float(np.median(a) / noise_uv[i])
                if a.size and noise_uv[i] > 0 else np.nan,
            ))
        return pd.DataFrame(rows)
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame([dict(**base, error=summarise_error(exc))])


# %%
# === Worklist: sessions whose day also has an impedance file ===
def build_worklist() -> list[dict]:
    imp = pd.read_parquet(IMP)
    sess = pd.read_parquet(SESS)
    jobs: list[dict] = []
    for arr, g in sess[sess.has_broadband].groupby("array"):
        days = set(imp[imp.array == arr].date.dt.date)
        for r in g.itertuples():
            if pd.Timestamp(r.date).date() not in days:
                continue
            hits = sorted(PROBE_DIR.glob(f"*{r.serial}*.cmp"))
            ns6 = sorted(Path(r.path).glob("*.ns6"))
            if not hits or not ns6:
                continue
            jobs.append(dict(
                subject="Fisk", array=arr, serial=r.serial,
                session=r.session, date=str(pd.Timestamp(r.date).date()),
                ns6=str(ns6[0]), cmp=str(hits[0]),
            ))
    return jobs


def report(d: pd.DataFrame, imp: pd.DataFrame) -> None:
    ok = d[d.get("error").isna()] if "error" in d else d
    banner("1. Same-day electrode pairs")
    print(f"  rows: {len(ok)}   sessions: {ok.session.nunique()}")
    print(ok.groupby("array").agg(
        sessions=("session", "nunique"), channels=("channel", "nunique"),
        rows=("channel", "size")).to_string())

    banner("2. Per-session correlation, impedance against quality")
    print("  Spearman within each session, so date, amplifier and threshold")
    print("  are all held fixed. One row per session, summarised.\n")
    res = []
    for (arr, sess_id), g in ok.groupby(["array", "session"]):
        if g.kohm.notna().sum() < 30:
            continue
        row = dict(array=arr, session=sess_id)
        for m in ("noise_uv", "rate_hz", "amp_med", "snr"):
            v = g.dropna(subset=["kohm", m])
            if len(v) < 30:
                continue
            row[m], _ = spearmanr(v.kohm, v[m])
        res.append(row)
    r = pd.DataFrame(res)
    if len(r):
        print(f"  {'metric':12s} {'median rho':>11s} {'IQR':>18s} "
              f"{'sessions':>9s} {'|rho|>0.3':>10s}")
        for m in ("noise_uv", "rate_hz", "amp_med", "snr"):
            if m not in r:
                continue
            s = r[m].dropna()
            if not len(s):
                continue
            print(f"  {m:12s} {s.median():11.3f} "
                  f"{s.quantile(0.25):8.3f}-{s.quantile(0.75):.3f} "
                  f"{len(s):9d} {(s.abs() > 0.3).mean():10.0%}")

    banner("3. Pooled, using each channel's median impedance")
    print("  Impedance bounces between dates, so a per-day reading understates")
    print("  any real relationship. Averaging it per channel should sharpen")
    print("  the correlation if the relationship exists.\n")
    med_imp = (imp.groupby(["array", "channel"]).kohm.median()
               .rename("kohm_med").reset_index())
    med_q = (ok.groupby(["array", "channel"])
             [["noise_uv", "rate_hz", "amp_med", "snr"]].median()
             .reset_index())
    j = med_imp.merge(med_q, on=["array", "channel"], how="inner")
    for arr, g in j.groupby("array"):
        print(f"  {arr}  (n = {len(g)} electrodes)")
        for m in ("noise_uv", "rate_hz", "amp_med", "snr"):
            v = g.dropna(subset=["kohm_med", m])
            if len(v) < 20:
                continue
            rho, p = spearmanr(v.kohm_med, v[m])
            print(f"    kohm vs {m:10s} rho {rho:+.3f}  p={p:.3g}")
        print()

    banner("4. The high-impedance electrodes, as a group")
    print("  Split on each channel's MEDIAN impedance, not one reading.\n")
    hi = j[j.kohm_med >= 1000]
    lo = j[j.kohm_med < 1000]
    print(f"  {'group':22s} {'n':>4s} {'noise':>8s} {'rate':>8s} "
          f"{'amp':>8s} {'snr':>7s}")
    for lab, g in (("median >= 1 MOhm", hi), ("median < 1 MOhm", lo)):
        if not len(g):
            continue
        print(f"  {lab:22s} {len(g):4d} {g.noise_uv.median():8.2f} "
              f"{g.rate_hz.median():8.2f} {g.amp_med.median():8.1f} "
              f"{g.snr.median():7.2f}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    jobs = build_worklist()
    if args.limit:
        jobs = jobs[:args.limit]
    banner("Fisk -- impedance against per-electrode quality")
    print(f"  same-day sessions to read: {len(jobs)}")

    frames = []
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for i, f in enumerate(ex.map(channel_quality, jobs, chunksize=1), 1):
            frames.append(f)
            if i % 10 == 0:
                print(f"    {i}/{len(jobs)}", flush=True)
    q = pd.concat(frames, ignore_index=True)

    imp = pd.read_parquet(IMP)
    imp["day"] = imp.date.dt.strftime("%Y-%m-%d")
    d = q.merge(imp[["array", "day", "channel", "kohm", "high_z"]],
                left_on=["array", "date", "channel"],
                right_on=["array", "day", "channel"], how="left")
    FISK_DIR.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, engine="pyarrow", index=False)
    report(d, imp)
    print(f"\n  wrote {OUT}  ({len(d)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

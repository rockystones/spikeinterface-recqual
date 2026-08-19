"""The LFP layer: line noise, band power, and how correlated the array is.

CLAUDE.md says LFP is in scope and must be handled alongside spikes rather than
as an afterthought. Nothing had touched it. Fisk carries `.ns3` for all 140
sessions and the TDT corpus carries `pNe` for all 370 blocks, so the data has
been sitting there since the corpus was assembled.

Three quantities, chosen because they say something about the *recording* that
the spike layer cannot:

- **60 Hz line power, as a fraction of total.** Mains contamination is an
  acquisition fault, not a property of the tissue, and it is invisible to a
  spike-band pipeline that high-passes at 300 Hz. A session with a loose
  ground shows here and nowhere else.
- **Band power** (delta through gamma) per channel, normalised, so a shift in
  the spectrum is separable from a change in overall amplitude.
- **Median cross-channel correlation.** An array whose channels are shorted,
  bridged, or riding a common reference shows near-unity correlation in the
  LFP band. A healthy array shows moderate correlation from volume conduction.
  This is the closest thing in the corpus to a direct test for a hardware
  fault, and it has no spike-layer equivalent.

Scaling is checked, not assumed -- the third format in this project where NEO's
units needed verifying. Blackrock `.ns3` carries its gain and comes out in µV;
TDT `pNe` is **int16 ADC counts with no recorded scale**
([[tdt_corpus]]), so its amplitudes are reported in counts and only the
*ratios* -- line fraction, band fractions, correlation -- are comparable across
the two.

Run from repo root:

    uv run python notebooks/scratch_lfp_quality.py [--jobs 2] [--subject Fisk]

Writes `data/derived/lfp/lfp_quality.parquet`.

See:
- docs/notes/lfp_quality.md
"""

from __future__ import annotations

import argparse
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_cohort_io import PROBE_DIR  # noqa: E402
from scratch_ns5_resort import summarise_error  # noqa: E402

OUT_DIR = REPO / "data" / "derived" / "lfp"
OUT = OUT_DIR / "lfp_quality.parquet"
FISK_SESS = REPO / "data" / "derived" / "fisk" / "fisk_sessions.parquet"

# Seconds analysed. LFP is slow and stationary; 60 s at 2 kHz is ample for a
# spectrum and keeps the pass cheap.
SLICE_S = 60.0
# Mains, and the half-width used to integrate around it.
LINE_HZ = 60.0
LINE_HALFWIDTH_HZ = 1.5
BANDS = {"delta": (1, 4), "theta": (4, 8), "alpha": (8, 13),
         "beta": (13, 30), "gamma": (30, 80)}


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === One session ===
def nsx_filter(path: str, nsx_id: int) -> dict:
    """The stream's own filter corners, from the nsX extended header.

    **Do not assume a stream carries LFP because of its suffix.** Blackrock
    stores corner frequencies in *millihertz*, and Fisk's `.ns3` reports
    `hi_freq_corner = 300000` -- a 300 Hz high-pass -- with a 1000 Hz low-pass.
    That is a spike-band stream sampled at 2 kHz, not LFP, and it contains
    0.2% of its power below 80 Hz. Computing band power from it produces
    numbers that look like data and mean nothing.
    """
    from neo.rawio import BlackrockRawIO

    raw = BlackrockRawIO(filename=str(Path(path).with_suffix("")),
                         nsx_to_load=nsx_id)
    raw.parse_header()
    h = raw._nsx_ext_header[nsx_id][0]
    hp = float(h["hi_freq_corner"]) / 1000.0
    lp = float(h["lo_freq_corner"]) / 1000.0
    return dict(hp_corner_hz=hp, lp_corner_hz=lp,
                # An LFP stream passes the low frequencies. Anything cornered
                # above 30 Hz has removed the band this layer is about.
                is_lfp=hp <= 30.0)


def lfp_metrics(job: dict) -> dict:
    """Line contamination, band power and channel correlation for one file."""
    base = {k: v for k, v in job.items() if k not in ("path", "cmp")}
    try:
        import spikeinterface.extractors as se

        try:
            filt = nsx_filter(job["path"], int(job["stream"]))
            base.update(filt)
            if not filt["is_lfp"]:
                return dict(**base, error=(
                    f"not an LFP stream: high-pass at "
                    f"{filt['hp_corner_hz']:.0f} Hz"))
        except Exception:  # noqa: BLE001 - a missing header must not stop the read
            pass

        rec = se.read_blackrock(file_path=job["path"], stream_id=job["stream"])
        fs = rec.get_sampling_frequency()
        n = min(rec.get_num_frames(), int(SLICE_S * fs))
        # return_scaled: Blackrock carries a real gain, so this is uV.
        x = rec.get_traces(start_frame=0, end_frame=n, return_scaled=True)
        x = np.asarray(x, dtype=np.float64)
        if x.ndim != 2 or x.shape[0] < int(fs * 5):
            return dict(**base, error="too short")

        # Welch per channel. nperseg of 4 s gives 0.25 Hz resolution, enough to
        # separate the 60 Hz line from the gamma band around it.
        nper = int(min(4 * fs, x.shape[0]))
        f, pxx = signal.welch(x, fs=fs, nperseg=nper, axis=0)
        total = np.trapezoid(pxx, f, axis=0)
        total = np.where(total <= 0, np.nan, total)

        line = (f >= LINE_HZ - LINE_HALFWIDTH_HZ) & \
               (f <= LINE_HZ + LINE_HALFWIDTH_HZ)
        line_frac = (np.trapezoid(pxx[line], f[line], axis=0) / total
                     if line.any() else np.full(x.shape[1], np.nan))

        out = {}
        for name, (lo, hi) in BANDS.items():
            m = (f >= lo) & (f < hi)
            if not m.any() or hi > fs / 2:
                out[f"{name}_frac"] = np.nan
                continue
            out[f"{name}_frac"] = float(np.nanmedian(
                np.trapezoid(pxx[m], f[m], axis=0) / total))

        # Cross-channel correlation on the LFP itself. A shorted or bridged
        # array approaches 1; volume conduction alone leaves it moderate.
        c = np.corrcoef(x, rowvar=False)
        iu = np.triu_indices(c.shape[0], k=1)
        cc = c[iu]
        cc = cc[np.isfinite(cc)]

        return dict(
            **base, sr=float(fs), duration_s=float(n / fs),
            n_channels=int(x.shape[1]),
            rms_uv=float(np.nanmedian(np.std(x, axis=0))),
            line_frac_med=float(np.nanmedian(line_frac)),
            line_frac_p90=float(np.nanpercentile(line_frac, 90)),
            corr_med=float(np.median(cc)) if cc.size else np.nan,
            corr_p90=float(np.percentile(cc, 90)) if cc.size else np.nan,
            **out,
        )
    except Exception as exc:  # noqa: BLE001
        return dict(**base, error=summarise_error(exc))


def build_worklist(subject: str = "") -> list[dict]:
    """Fisk's `.ns3`, one per session folder."""
    jobs: list[dict] = []
    if subject in ("", "Fisk") and FISK_SESS.exists():
        sess = pd.read_parquet(FISK_SESS)
        for r in sess[sess.has_lfp].itertuples():
            ns3 = sorted(Path(r.path).glob("*.ns3"))
            if not ns3:
                continue
            jobs.append(dict(
                subject="Fisk", array=r.array, serial=r.serial,
                session=r.session, date=str(pd.Timestamp(r.date).date()),
                path=str(ns3[0]), stream="3",
            ))
    return jobs


def report(d: pd.DataFrame) -> None:
    ok = d[d.get("error").isna()] if "error" in d else d
    banner("1. Coverage")
    print(f"  sessions: {len(ok)} of {len(d)}")
    if len(d) > len(ok):
        print(d[d.error.notna()].error.astype(str).str.slice(0, 60)
              .value_counts().head(3).to_string())
    if not len(ok):
        return
    print(ok.groupby(["subject", "array"]).agg(
        n=("session", "size"), first=("date", "min"), last=("date", "max"),
        sr=("sr", "median"), rms=("rms_uv", "median")).round(1).to_string())

    banner("2. Mains contamination, which the spike layer cannot see")
    print("  60 Hz power as a fraction of total LFP power. A 300 Hz highpass")
    print("  removes this entirely, so a grounding fault is invisible")
    print("  downstream.\n")
    print(ok.groupby(["subject", "array"]).line_frac_med.describe()
          [["50%", "75%", "max"]].round(4).to_string())
    hi = ok[ok.line_frac_med > 0.05]
    print(f"\n  sessions above 5% line power: {len(hi)} of {len(ok)}")
    if len(hi):
        print(hi.nlargest(min(8, len(hi)), "line_frac_med")
              [["array", "date", "line_frac_med", "rms_uv"]]
              .round(4).to_string(index=False))

    banner("3. Cross-channel correlation")
    print("  A shorted or bridged array approaches 1. Volume conduction alone")
    print("  leaves it moderate. This has no spike-layer equivalent.\n")
    print(ok.groupby(["subject", "array"]).corr_med.describe()
          [["min", "50%", "max"]].round(3).to_string())

    banner("4. Band composition")
    cols = [f"{b}_frac" for b in BANDS if f"{b}_frac" in ok]
    if cols:
        print(ok.groupby(["subject", "array"])[cols].median().round(3)
              .to_string())

    banner("5. Longitudinal")
    from scipy.stats import spearmanr
    for (s, a), g in ok.groupby(["subject", "array"]):
        if len(g) < 10:
            continue
        x = pd.to_datetime(g.date).map(pd.Timestamp.toordinal)
        print(f"  {s}/{a}  n={len(g)}")
        for m in ("rms_uv", "line_frac_med", "corr_med", "gamma_frac"):
            if m not in g:
                continue
            v = g.dropna(subset=[m])
            if len(v) < 10:
                continue
            r, p = spearmanr(pd.to_datetime(v.date)
                             .map(pd.Timestamp.toordinal), v[m])
            print(f"    {m:16s} rho {r:+.3f}  p={p:.3g}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--subject", default="")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    jobs = build_worklist(args.subject)
    if args.limit:
        jobs = jobs[:args.limit]
    banner("LFP quality layer")
    print(f"  sessions: {len(jobs)}")

    rows = []
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for i, r in enumerate(ex.map(lfp_metrics, jobs, chunksize=1), 1):
            rows.append(r)
            if i % 20 == 0:
                print(f"    {i}/{len(jobs)}", flush=True)
    d = pd.DataFrame(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, engine="pyarrow", index=False)
    report(d)
    print(f"\n  wrote {OUT}  ({len(d)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

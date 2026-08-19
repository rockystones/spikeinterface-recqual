"""Chase: the Plexon corpus, and the only one with dated events to test against.

20 `.plx` files from 2009-2010, snippet-only, from a Utah array whose history
is written down. Whitford's README gives:

| date | event |
|---|---|
| 2009-02-26 | array implanted |
| 2009-03-17 | first day of brain control |
| 2009-08-24 | **repair surgery** (skin around the pedestal) |
| 2009-08-25 | notes: "many of the units from one and one-half weeks ago are still there" |
| 2009-08-27 | notes: **"sharp decline"** in unit quality |

Every other longitudinal claim in this project is inferred from the data
alone. Here an operator wrote down, at the time, that quality fell on a
specific day -- and there are files on 08-25 and 08-27 bracketing it. That
makes Chase the one place a metric can be checked against an external record
rather than against another metric.

## What the format declares that TDT did not

The Plexon global header is unusually forthcoming, and every value that had to
be measured or guessed for TDT is simply stated:

- `NumPointsPreThr = 8` -- the pre-threshold sample count, so no trough
  hunting. It is still verified against the measured modal trough.
- `ADFrequency = 40000` -- the waveform rate. NEO's `wf_sampling_rate` reads
  **0** for these files, so it must come from the global header instead.
- `Year/Month/Day/Hour/Minute` -- the recording date, which beats parsing it
  out of filenames that use three different conventions.

## Units

NEO's `wf_gain` for Plexon is derived from `SpikeMaxMagnitudeMV`, so
`raw * wf_gain` is in **millivolts**, and microvolts need a further `* 1000`.
`wf_units` is left empty, so nothing warns you. Checked against the physics:
the noise floor comes out at **12.5 uV** under that reading and 12,520 uV under
the volts reading. Extracellular noise is 5-20 uV.

Run from repo root:

    uv run python notebooks/scratch_chase.py [--jobs 1]

Writes `data/derived/chase/chase_sessions.parquet` and
`data/derived/chase/chase_units.parquet`.

See:
- docs/notes/chase_corpus.md
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_rocky_resort import baseline_noise_uv  # noqa: E402

CHASE = Path(r"C:\MyData\Monkeydata\Chase\chase.waveforms")
OUT_DIR = REPO / "data" / "derived" / "chase"
SESSIONS_OUT = OUT_DIR / "chase_sessions.parquet"
UNITS_OUT = OUT_DIR / "chase_units.parquet"

# NEO's Plexon wf_gain lands in millivolts; microvolts need this on top.
MV_TO_UV = 1000.0
# Plexon's unsorted code. 1..N are sorted units, exactly like the NEV.
UNSORTED = 0
# The project's SNR gate, restated so this script stands alone.
SNR_GATE = 4.0

# From the corpus README, which is the point of this subject.
EVENTS = {
    "2009-02-26": "array implanted",
    "2009-03-17": "first day of brain control",
    "2009-08-24": "repair surgery",
    "2009-08-27": 'notes: "sharp decline" in unit quality',
}
DECLINE_DATE = pd.Timestamp("2009-08-27")


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === IO ===
def plx_header(path: Path) -> dict:
    """Global header fields NEO does not expose, read straight from the file."""
    from neo.rawio.plexonrawio import GlobalHeader

    g = np.fromfile(str(path), dtype=GlobalHeader, count=1)[0]
    # WaveformFreq is 0 in these files; ADFrequency is the real rate.
    sr = float(g["WaveformFreq"]) or float(g["ADFrequency"])
    try:
        date = pd.Timestamp(int(g["Year"]), int(g["Month"]), int(g["Day"]),
                            int(g["Hour"]), int(g["Minute"]))
    except Exception:  # noqa: BLE001
        date = pd.NaT
    return dict(version=int(g["Version"]), sr=sr,
                n_points=int(g["NumPointsWave"]),
                nbefore=int(g["NumPointsPreThr"]),
                preamp_gain=int(g["SpikePreAmpGain"]),
                header_date=date)


def session_metrics(job: dict) -> dict:
    """Per-session sorting-free and sorting-based metrics for one .plx."""
    from neo.rawio import PlexonRawIO

    path = Path(job["path"])
    base = {k: v for k, v in job.items() if k != "path"}
    try:
        hdr = plx_header(path)
        io = PlexonRawIO(filename=str(path))
        io.parse_header()
        sc = io.header["spike_channels"]
        dur = float(io.segment_t_stop(0, 0) - io.segment_t_start(0, 0))
        nbefore = hdr["nbefore"]

        by_ch: dict[int, dict] = {}
        units: list[dict] = []
        modal: list[int] = []
        for ui in range(len(sc)):
            ident = sc["id"][ui]
            ident = ident.decode() if isinstance(ident, bytes) else str(ident)
            ch_s, _, unit_s = ident.partition("#")
            ch = int(ch_s.replace("ch", ""))
            code = int(unit_s)
            w = io.get_spike_raw_waveforms(0, 0, ui)
            if w is None:
                continue
            w = np.asarray(w)
            if w.shape[0] == 0:
                continue
            w = w.reshape(w.shape[0], -1).astype(np.float32)
            w = w * float(sc["wf_gain"][ui]) * MV_TO_UV
            amp = np.abs(w.min(axis=1))
            modal.append(int(np.bincount(np.argmin(w, axis=1),
                                         minlength=w.shape[1]).argmax()))
            slot = by_ch.setdefault(ch, dict(wfs=[], n=0))
            slot["wfs"].append(w)
            slot["n"] += w.shape[0]
            if code != UNSORTED:
                mean = w.mean(axis=0)
                units.append(dict(**base, channel=ch, unit=code,
                                  n_spikes=int(w.shape[0]),
                                  rate_hz=float(w.shape[0] / dur) if dur
                                  else np.nan,
                                  amp_med=float(np.median(amp)),
                                  p2p=float(mean.max() - mean.min())))

        noises, counts, amps, snrs = [], [], [], []
        for ch, slot in by_ch.items():
            allw = np.concatenate(slot["wfs"])
            noise = baseline_noise_uv(allw, nbefore)
            a = np.abs(allw.min(axis=1))
            noises.append(noise)
            counts.append(len(a))
            amps.append(a)
            if noise > 0:
                snrs.append(float(np.median(a) / noise))
            slot["noise"] = noise
        for u in units:
            u["noise_uv"] = by_ch[u["channel"]].get("noise", np.nan)
            u["snr"] = (u["amp_med"] / u["noise_uv"]
                        if u["noise_uv"] and u["noise_uv"] > 0 else np.nan)
            u["passes_gate"] = bool(u["snr"] >= SNR_GATE) \
                if np.isfinite(u.get("snr", np.nan)) else False

        if not counts:
            return dict(**base, error="no events"), []
        allamp = np.concatenate(amps)
        n_ch = len(by_ch)
        row = dict(
            **base, duration_s=dur, sr=hdr["sr"], nbefore=nbefore,
            n_points=hdr["n_points"],
            header_date=hdr["header_date"],
            modal_trough=int(np.bincount(modal).argmax()) if modal else -1,
            n_channels=n_ch,
            n_units=len(units),
            units_per_channel=len(units) / n_ch if n_ch else np.nan,
            n_elec_with_units=len({u["channel"] for u in units}),
            noise_med=float(np.median(noises)),
            n_crossings=int(sum(counts)),
            crossing_rate_hz=float(sum(counts) / dur / max(n_ch, 1))
            if dur else np.nan,
            amp_p50=float(np.percentile(allamp, 50)),
            amp_p90=float(np.percentile(allamp, 90)),
            amp_p99=float(np.percentile(allamp, 99)),
            peak_snr_med=float(np.median(snrs)) if snrs else np.nan,
        )
        if units:
            u = pd.DataFrame(units)
            row["unit_amp_med"] = float(u.amp_med.median())
            row["unit_snr_med"] = float(u.snr.median())
            row["unit_rate_med"] = float(u.rate_hz.median())
            row["pass_fraction"] = float(u.passes_gate.mean())
        return row, units
    except Exception as exc:  # noqa: BLE001
        return dict(**base, error=f"{type(exc).__name__}: {exc}"[:140]), []


# %%
# === Report ===
def report(s: pd.DataFrame, u: pd.DataFrame) -> None:
    ok = s[s.get("error").isna()] if "error" in s else s
    banner("1. Sessions")
    print(f"  files: {len(ok)} of {len(s)}")
    cols = ["date", "header_date", "duration_s", "sr", "nbefore",
            "modal_trough", "n_channels", "n_units", "noise_med",
            "amp_p50", "peak_snr_med", "unit_snr_med"]
    print(ok[[c for c in cols if c in ok]].sort_values("date")
          .to_string(index=False))

    banner("2. Does the header agree with the filename?")
    if "header_date" in ok:
        d = ok.dropna(subset=["header_date"]).copy()
        d["fn"] = pd.to_datetime(d.date).dt.date
        d["hd"] = pd.to_datetime(d.header_date).dt.date
        bad = d[d.fn != d.hd]
        print(f"  files where they disagree: {len(bad)} of {len(d)}")
        if len(bad):
            print(bad[["stem", "fn", "hd"]].to_string(index=False))
        print("  The header is written by the acquisition system at record")
        print("  time and is preferred wherever they differ.")

    banner("3. nbefore is declared, not guessed")
    if "nbefore" in ok:
        agree = int((ok.nbefore == ok.modal_trough).sum())
        print(f"  NumPointsPreThr matches the measured modal trough in "
              f"{agree} of {len(ok)} sessions")
        print(f"  declared values: {sorted(ok.nbefore.unique())}   "
              f"measured: {sorted(ok.modal_trough.unique())}")

    banner("4. The documented events")
    for k, v in EVENTS.items():
        print(f"  {k}  {v}")
    print()
    o = ok.copy()
    o["date"] = pd.to_datetime(o["date"])
    o = o.sort_values("date")
    before = o[o.date < DECLINE_DATE]
    after = o[o.date >= DECLINE_DATE]
    print(f"  sessions before 2009-08-27: {len(before)}   on/after: {len(after)}")
    if len(before) >= 3 and len(after) >= 3:
        print(f"\n  {'metric':22s} {'before':>9s} {'after':>9s} "
              f"{'ratio':>7s} {'p':>9s}")
        for m in ("n_units", "units_per_channel", "unit_snr_med",
                  "unit_amp_med", "noise_med", "amp_p50", "peak_snr_med",
                  "crossing_rate_hz", "pass_fraction"):
            if m not in o:
                continue
            a, b = before[m].dropna(), after[m].dropna()
            if len(a) < 3 or len(b) < 3:
                continue
            try:
                _, p = mannwhitneyu(a, b)
            except ValueError:
                p = np.nan
            print(f"  {m:22s} {a.median():9.2f} {b.median():9.2f} "
                  f"{a.median() / b.median() if b.median() else np.nan:7.2f} "
                  f"{p:9.3g}")
        print("\n  The operator recorded a 'sharp decline' on 2009-08-27.")
        print("  Whether these metrics see it is the test.")

    banner("5. Trend across the whole series")
    x = o.date.map(pd.Timestamp.toordinal)
    print(f"  {'metric':22s} {'rho':>7s} {'p':>10s}   n")
    for m in ("n_units", "units_per_channel", "unit_snr_med", "unit_amp_med",
              "noise_med", "amp_p50", "peak_snr_med", "crossing_rate_hz"):
        if m not in o:
            continue
        d = o.dropna(subset=[m])
        if len(d) < 8:
            continue
        rho, p = spearmanr(d.date.map(pd.Timestamp.toordinal), d[m])
        print(f"  {m:22s} {rho:+7.3f} {p:10.3g} {len(d):3d}")


def build_worklist() -> list[dict]:
    return [dict(subject="Chase", path=str(p), stem=p.stem,
                 date=None)
            for p in sorted(CHASE.glob("*.plx"))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    jobs = build_worklist()
    if args.limit:
        jobs = jobs[:args.limit]
    banner("Chase -- Plexon corpus")
    print(f"  files: {len(jobs)}")

    rows, unit_rows = [], []
    if args.jobs > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            for r, us in ex.map(session_metrics, jobs, chunksize=1):
                rows.append(r)
                unit_rows.extend(us)
    else:
        for i, j in enumerate(jobs, 1):
            r, us = session_metrics(j)
            rows.append(r)
            unit_rows.extend(us)
            print(f"    [{i}/{len(jobs)}] {j['stem']}  "
                  f"{'ERROR ' + r['error'] if 'error' in r else ''}",
                  flush=True)
    s = pd.DataFrame(rows)
    # The header date is authoritative; the filenames use three conventions.
    if "header_date" in s:
        s["date"] = pd.to_datetime(s.header_date).dt.strftime("%Y-%m-%d")
    u = pd.DataFrame(unit_rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    s.to_parquet(SESSIONS_OUT, engine="pyarrow", index=False)
    if len(u):
        u.to_parquet(UNITS_OUT, engine="pyarrow", index=False)
    report(s, u)
    print(f"\n  wrote {SESSIONS_OUT}  ({len(s)} rows)")
    print(f"  wrote {UNITS_OUT}  ({len(u)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

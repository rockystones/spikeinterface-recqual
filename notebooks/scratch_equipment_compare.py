"""How does the recording change across acquisition equipment?

Rocky is the only subject recorded on three configurations -- TDT, a Blackrock
analog headstage and a Blackrock digital headstage -- with overlap in time, so
he is the only place this question can be asked without confounding equipment
with animal.

Two comparisons, and they are deliberately not pooled:

**Analog vs digital headstage**, from the broadband. 121 same-day pairs exist
and both members are re-detected from the trace at the same `k * MAD`, which
takes the NSP's own acquisition threshold out of the comparison entirely. That
is the thing S12b could not do: it compared crossing counts the NSP had
already thresholded, and an RMS-relative threshold moves with the noise floor,
so a noisier amplifier appeared to yield *fewer* events.

**TDT vs Blackrock**, from snippets on both sides. There is no fair continuous
comparison to make -- Rocky's TDT tanks are almost all snippet-only -- so both
sides go through `baseline_noise_uv` and the same trough statistic instead.
Mixing a continuous-derived floor with a snippet-derived one would inject the
1.1-1.3x bias from [[snippet_noise_floor]] into the equipment contrast and
look like an equipment effect.

The comparison is date-matched but **not paired**: TDT and Blackrock sessions
on one day are different recordings, so only session-level distributions are
compared, never per-channel values.

Run from repo root:

    uv run python notebooks/scratch_equipment_compare.py [--jobs 3]

Writes `data/derived/equipment/tdt_vs_blackrock.parquet`.

See:
- docs/notes/equipment_comparison.md
- docs/notes/cohort_longitudinal.md
"""

from __future__ import annotations

import argparse
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, wilcoxon

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_rocky_resort import (  # noqa: E402
    baseline_noise_uv,
    open_nev,
    read_electrode,
)
from scratch_tdt_io import (  # noqa: E402
    channel_index,
    detect_nbefore,
    find_blocks,
    open_tank,
    read_channel,
    tank_clock,
)

ROCKY_TDT = Path(r"C:\MyData\Monkeydata\Rocky\Rocky_TDT")
INV = REPO / "data" / "derived" / "newdrop_inventory.parquet"
NS5_FREE = REPO / "data" / "derived" / "rocky_ns5" / "ns5_free.parquet"
OUT_DIR = REPO / "data" / "derived" / "equipment"
OUT = OUT_DIR / "tdt_vs_blackrock.parquet"

METRICS = ("noise_med", "amp_p50", "amp_p90", "peak_snr_med",
           "crossing_rate_hz", "frac_elec_active")


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === Session-level snippet metrics, one function for both formats ===
def snippet_metrics(job: dict) -> dict:
    """Session metrics from snippets, whichever system wrote them.

    The two branches differ only in how the per-channel waveform arrays are
    obtained. Everything after that -- the noise estimator, the trough
    statistic, the aggregation -- is shared, which is what makes the numbers
    comparable across equipment.
    """
    base = {k: v for k, v in job.items() if k != "path"}
    try:
        if job["system"] == "tdt":
            io, meta = open_tank(Path(job["path"]))
            store = job["store"]
            idx = channel_index(io)
            nbefore = detect_nbefore(io, meta, store, idx)
            dur = meta["duration_s"]
            n_declared = meta["stores"].get(store, {}).get("n_chan", 96)
            items = [(ch, read_channel(io, meta, u))
                     for (st, ch), u in sorted(idx.items()) if st == store]
        else:
            raw, meta, chan_by_elec = open_nev(Path(job["path"]))
            nbefore, dur = meta["nbefore"], meta["duration_s"]
            n_declared = 96
            items = [(e, read_electrode(raw, meta, chan_by_elec[e]))
                     for e in sorted(chan_by_elec)]

        noises, counts, amps, snrs = [], [], [], []
        for _, e in items:
            if e is None or not len(e["t"]):
                continue
            wf = e["wf"]
            noise = baseline_noise_uv(wf, nbefore)
            amp = np.abs(wf.min(axis=1))
            noises.append(noise)
            counts.append(len(amp))
            amps.append(amp)
            if noise > 0:
                snrs.append(float(np.median(amp) / noise))
        if not counts:
            return dict(**base, error="no events")
        allamp = np.concatenate(amps)
        return dict(
            **base, duration_s=float(dur),
            noise_med=float(np.median(noises)),
            noise_p90=float(np.percentile(noises, 90)),
            n_crossings=int(sum(counts)),
            crossing_rate_hz=float(sum(counts) / dur / max(len(counts), 1))
            if dur and np.isfinite(dur) else np.nan,
            amp_p50=float(np.percentile(allamp, 50)),
            amp_p90=float(np.percentile(allamp, 90)),
            amp_p99=float(np.percentile(allamp, 99)),
            peak_snr_med=float(np.median(snrs)) if snrs else np.nan,
            n_elec_active=len(counts),
            frac_elec_active=len(counts) / n_declared,
        )
    except Exception as exc:  # noqa: BLE001
        return dict(**base, error=f"{type(exc).__name__}: {exc}"[:140])


# %%
# === Worklist ===
def build_worklist() -> list[dict]:
    """Rocky's TDT blocks and his Blackrock NEVs, as one snippet worklist."""
    jobs: list[dict] = []
    for tev in find_blocks(ROCKY_TDT):
        start, dur = tank_clock(tev.with_suffix(".tsq"))
        if start is None or not np.isfinite(dur) or dur < 60:
            continue
        name = tev.parent.name
        if name.lower().startswith("picasso"):
            # A Picasso-named block sits inside Rocky's tree. Excluded rather
            # than assumed to be misfiled; it is flagged in the corpus note.
            continue
        letter = "A" if "_A" in name else ("B" if "_B" in name else "")
        io_meta_store = "eNe2"      # Rocky's tanks carry one snippet store
        jobs.append(dict(system="tdt", equipment="TDT", subject="Rocky",
                         block=name, path=str(tev), store=io_meta_store,
                         array=f"TDT-{letter or '?'}",
                         date=str(start.date())))

    inv = pd.read_parquet(INV)
    nev = inv[(inv.role == "snippets") & inv.date.notna()
              & (inv.tree == "Blackrock") & (inv.chain == "")].copy()
    nev["d"] = nev.date.dt.strftime("%Y-%m-%d")
    nev = nev[nev.headstage.isin(["Analog", "Digital"])]
    for r in nev.itertuples():
        jobs.append(dict(system="nev", equipment=f"BR-{r.headstage}",
                         subject="Rocky", block=r.stem, path=r.path,
                         store="", array=r.array, date=r.d))
    return jobs


def report(d: pd.DataFrame, ns5: pd.DataFrame | None) -> None:
    ok = d[d.get("error").isna()] if "error" in d else d
    banner("1. What each equipment configuration recorded")
    print(f"  sessions: {len(ok)} of {len(d)}")
    print(ok.groupby("equipment").agg(
        n=("block", "size"), first=("date", "min"), last=("date", "max"),
        noise=("noise_med", "median"), amp=("amp_p50", "median"),
        snr=("peak_snr_med", "median"),
        rate=("crossing_rate_hz", "median"),
        elec=("frac_elec_active", "median")).round(2).to_string())

    banner("2. Overlap window -- the only fair comparison")
    tdt = ok[ok.equipment == "TDT"]
    if not len(tdt):
        return
    lo, hi = tdt.date.min(), tdt.date.max()
    win = ok[(ok.date >= lo) & (ok.date <= hi)]
    print(f"  TDT ran {lo} .. {hi}; restricting every system to that window")
    print(f"  leaves {len(win)} sessions.\n")
    print(win.groupby("equipment").agg(
        n=("block", "size"), noise=("noise_med", "median"),
        amp=("amp_p50", "median"), snr=("peak_snr_med", "median"),
        rate=("crossing_rate_hz", "median")).round(2).to_string())

    banner("3. TDT against each Blackrock headstage, snippets both sides")
    print("  Mann-Whitney, session-level. Not paired: a TDT block and a")
    print("  Blackrock file on one day are different recordings.\n")
    ref = win[win.equipment == "TDT"]
    for eq in ("BR-Analog", "BR-Digital"):
        other = win[win.equipment == eq]
        if len(other) < 8:
            continue
        print(f"  TDT vs {eq}   (n = {len(ref)} vs {len(other)})")
        for m in METRICS:
            a, b = ref[m].dropna(), other[m].dropna()
            if len(a) < 8 or len(b) < 8:
                continue
            try:
                _, p = mannwhitneyu(a, b)
            except ValueError:
                p = np.nan
            print(f"    {m:18s} TDT {a.median():8.2f}   {eq} {b.median():8.2f}"
                  f"   ratio {a.median() / b.median():5.2f}   p={p:.2g}")
        print()

    if ns5 is None or not len(ns5):
        return
    banner("4. Headstage from broadband, re-detected identically")
    print("  The comparison S12b could not make: both members thresholded at")
    print("  the same k*MAD from the trace, so the NSP's RMS-relative")
    print("  acquisition threshold is out of it.\n")
    n = ns5[ns5.get("error").isna()] if "error" in ns5 else ns5
    piv = n.pivot_table(index=["array", "date"], columns="headstage",
                        values=list(METRICS))
    for m in METRICS:
        if (m, "Analog") not in piv or (m, "Digital") not in piv:
            continue
        a, b = piv[(m, "Analog")], piv[(m, "Digital")]
        k = a.notna() & b.notna()
        if k.sum() < 8:
            continue
        try:
            _, p = wilcoxon(a[k], b[k])
        except ValueError:
            p = np.nan
        print(f"  {m:18s} analog {a[k].median():8.2f}  "
              f"digital {b[k].median():8.2f}  "
              f"ratio {a[k].median() / b[k].median():5.2f}  "
              f"p={p:.2g}  n={int(k.sum())}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    jobs = build_worklist()
    if args.limit:
        jobs = jobs[:args.limit]
    banner("Equipment comparison -- Rocky on TDT, analog and digital")
    print(f"  sessions to read: {len(jobs)}")
    print(pd.DataFrame(jobs).groupby("equipment").size()
          .rename("sessions").to_string())

    rows: list[dict] = []
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for i, r in enumerate(ex.map(snippet_metrics, jobs, chunksize=1), 1):
            rows.append(r)
            if i % 25 == 0:
                print(f"    {i}/{len(jobs)}", flush=True)
    d = pd.DataFrame(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, engine="pyarrow", index=False)
    ns5 = pd.read_parquet(NS5_FREE) if NS5_FREE.exists() else None
    report(d, ns5)
    print(f"\n  wrote {OUT}  ({len(d)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

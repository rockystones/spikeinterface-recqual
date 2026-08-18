"""S12b: the headstage contrast with no sorter in the loop, on all 121 pairs.

The first pass (`scratch_headstage_pairs.py`) compared session metrics derived
from the Plexon `-01` sort, which restricted it to **40 of 121** slots -- four
of five analog recordings were never sorted -- and the sorted analog subset
turned out to carry 17% fewer threshold crossings than the unsorted one
(p = 0.023). The cleaner analog sessions were the ones somebody chose to sort.

Every one of the 121 slots has the **original** NEV for both headstages, so
dropping the sorter removes the selection step entirely. What survives without
labels is the threshold-crossing layer of CLAUDE.md's metric stack: per-channel
noise floor, crossing counts and rates, crossing-amplitude distribution, and
peak SNR. None of it depends on anyone's clustering.

This is still not a fixed-event comparison -- two physical recordings have
different crossings -- so only session-level quantities are compared.

Run from repo root:

    uv run python notebooks/scratch_headstage_free.py [--jobs 10]

See:
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
from scipy.stats import spearmanr, wilcoxon

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from _paths import MONKEY_ROOT  # noqa: E402
from scratch_cohort_io import array_geometry  # noqa: E402
from scratch_rocky_resort import (  # noqa: E402
    baseline_noise_uv,
    open_nev,
    read_electrode,
)

INV = REPO / "data" / "derived" / "monkey_inventory.parquet"
OUT_DIR = REPO / "data" / "derived" / "cohort"
FREE_OUT = OUT_DIR / "headstage_free.parquet"
PAIRS_OUT = OUT_DIR / "headstage_free_pairs.parquet"

METRICS = ["noise_med", "noise_p90", "n_crossings", "crossing_rate_hz",
           "amp_p50", "amp_p90", "amp_p99", "amp_max", "peak_snr_med",
           "frac_elec_active", "n_elec_active"]


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === One recording, no labels used ===
def free_metrics(job: dict) -> dict | None:
    """Threshold-crossing metrics for one NEV, ignoring any unit labels.

    Every quantity here is a property of the events the NSP wrote and the
    baseline they sit on. Nothing reads the unit-class byte, so an unsorted
    original and its sorted sibling give identical answers.
    """
    base = {k: v for k, v in job.items() if k != "path"}
    try:
        raw, nmeta, chan_by_elec = open_nev(Path(job["path"]))
    except Exception as exc:  # noqa: BLE001
        return dict(**base, error=f"{type(exc).__name__}: {exc}"[:110])
    dur = nmeta["duration_s"]
    nbefore = nmeta["nbefore"]

    noises: list[float] = []
    counts: list[int] = []
    troughs: list[np.ndarray] = []
    snrs: list[float] = []
    for elec in sorted(chan_by_elec):
        e = read_electrode(raw, nmeta, chan_by_elec[elec])
        if e is None or not len(e["t"]):
            continue
        wf = e["wf"]
        noise = baseline_noise_uv(wf, nbefore)
        # |trough| per event: the crossing amplitude, sign-free.
        amp = np.abs(wf.min(axis=1))
        noises.append(noise)
        counts.append(len(e["t"]))
        troughs.append(amp)
        if noise > 0:
            snrs.append(float(np.median(amp) / noise))
    if not counts:
        return dict(**base, error="no events")

    allamp = np.concatenate(troughs)
    geo = array_geometry(job["subject"], job["array"], job.get("implant"))
    n_elec = geo["n_electrodes"]
    return dict(
        **base,
        noise_med=float(np.median(noises)),
        noise_p90=float(np.percentile(noises, 90)),
        n_crossings=int(sum(counts)),
        crossing_rate_hz=float(sum(counts) / dur / max(len(counts), 1))
        if dur else np.nan,
        amp_p50=float(np.percentile(allamp, 50)),
        amp_p90=float(np.percentile(allamp, 90)),
        amp_p99=float(np.percentile(allamp, 99)),
        amp_max=float(allamp.max()),
        peak_snr_med=float(np.median(snrs)) if snrs else np.nan,
        n_elec_active=len(counts),
        frac_elec_active=len(counts) / n_elec,
        duration_s=float(dur),
        n_electrodes=float(n_elec),
    )


# %%
# === Worklist: originals only, both headstages present ===
def build_pairs_worklist(inv: pd.DataFrame) -> list[dict]:
    """Every (array, date) with an ORIGINAL nev for both headstages."""
    n = inv[(inv.role == "snippets") & (inv.chain == "") & inv.excluded.isna()
            & (inv.subject == "Rocky") & (inv.implant == "I1")].copy()
    n["hs"] = n.headstage.str.lower()
    n = n[n.hs.isin(["analogheadstage", "digitalheadstage"])]
    jobs: list[dict] = []
    for (arr, date), g in n.groupby(["array", "date"]):
        kinds = set(g.hs)
        if not {"analogheadstage", "digitalheadstage"} <= kinds:
            continue
        for r in g.itertuples():
            jobs.append(dict(path=str(MONKEY_ROOT / r.rel), subject=r.subject,
                             implant=r.implant, array=arr, date=date,
                             headstage="analog" if "analog" in r.hs
                             else "digital"))
    return jobs


def pair_up(d: pd.DataFrame) -> pd.DataFrame:
    """Wide table, one row per (array, date), analog beside digital."""
    rows = []
    for (arr, date), g in d.groupby(["array", "date"]):
        a = g[g.headstage == "analog"]
        b = g[g.headstage == "digital"]
        if not len(a) or not len(b):
            continue
        row = dict(array=arr, date=date)
        for m in METRICS + ["duration_s"]:
            row[f"{m}_analog"] = a.iloc[0].get(m, np.nan)
            row[f"{m}_digital"] = b.iloc[0].get(m, np.nan)
        rows.append(row)
    return pd.DataFrame(rows)


def report(d: pd.DataFrame, p: pd.DataFrame) -> None:
    banner("1. Coverage -- no sorter, so no selection step")
    ok = d[d.get("error").isna()] if "error" in d else d
    print(f"  original recordings read : {len(ok)} of {len(d)}")
    print(f"  complete pairs           : {len(p)}   "
          f"(the sorted-only pass managed 40)")
    print(ok.groupby(["array", "headstage"]).size().to_string())

    # Screen on each recording's own noise, as in S09/S10. Baselines are per
    # (array, headstage) because the two amplifiers sit at different floors --
    # a shared baseline would flag most analog sessions by construction.
    base = ok.groupby(["array", "headstage"]).noise_med.transform("median")
    bad = ok[ok.noise_med > 2 * base]
    # Bracket access, never attribute: `row.array` is Series.array.
    drop = set(zip(bad["array"], bad["date"], strict=True))
    mask = [(a, dt) in drop for a, dt in zip(p["array"], p["date"], strict=True)]
    clean = p[~np.array(mask, dtype=bool)]
    print(f"\n  after the acquisition screen on either member: {len(clean)}")

    banner("2. Is analog noisier?  Sorting-free, all pairs")
    print("  Paired Wilcoxon, analog vs digital, same session recorded twice.\n")
    print(f"  {'metric':20s} {'analog':>10s} {'digital':>10s} "
          f"{'ratio':>7s} {'p':>10s}   n")
    out = []
    for m in METRICS:
        a, b = clean[f"{m}_analog"], clean[f"{m}_digital"]
        okm = a.notna() & b.notna()
        if okm.sum() < 8:
            continue
        ma, mb = a[okm].median(), b[okm].median()
        try:
            _, pv = wilcoxon(a[okm], b[okm])
        except ValueError:
            pv = np.nan
        star = ("***" if pv < 1e-3 else "**" if pv < 1e-2
                else "*" if pv < 0.05 else "")
        print(f"  {m:20s} {ma:10.2f} {mb:10.2f} "
              f"{ma / mb if mb else np.nan:7.2f} {pv:10.2g} {int(okm.sum()):4d} {star}")
        out.append(dict(metric=m, analog=ma, digital=mb,
                        ratio=ma / mb if mb else np.nan, p=pv,
                        n=int(okm.sum())))

    banner("3. Scale or quality?")
    print("  If the analog chain simply runs at higher gain, noise and")
    print("  amplitude scale together and peak SNR -- their ratio -- does not.")
    print("  If analog is genuinely worse, peak SNR falls.\n")
    r = {x["metric"]: x for x in out}
    for m in ("noise_med", "amp_p50", "amp_p90", "peak_snr_med"):
        if m in r:
            print(f"    {m:16s} ratio {r[m]['ratio']:.3f}   p={r[m]['p']:.2g}")
    if "peak_snr_med" in r:
        v = r["peak_snr_med"]
        verdict = ("a gain difference: SNR is unchanged"
                   if abs(v["ratio"] - 1) < 0.05 or v["p"] > 0.05
                   else "analog is genuinely worse: SNR falls"
                   if v["ratio"] < 1
                   else "analog reads BETTER on SNR, which needs explaining")
        print(f"\n    -> {verdict}")

    banner("4. Does the headstage change the trend?")
    for arr, g in clean.groupby("array"):
        line = f"  {arr:10s}"
        for m in ("crossing_rate_hz", "noise_med", "amp_p50", "peak_snr_med"):
            x = g.date.map(pd.Timestamp.toordinal)
            ra, _ = spearmanr(x, g[f"{m}_analog"])
            rd, _ = spearmanr(x, g[f"{m}_digital"])
            line += f"  {m}: a{ra:+.2f}/d{rd:+.2f}"
        print(line)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=10)
    args = ap.parse_args()

    inv = pd.read_parquet(INV)
    jobs = build_pairs_worklist(inv)
    banner("S12b -- headstage contrast, sorting-free")
    print(f"  original recordings to read: {len(jobs)}")

    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        res = [r for r in ex.map(free_metrics, jobs, chunksize=2) if r]
    d = pd.DataFrame(res)
    ok = d[d.get("error").isna()] if "error" in d else d
    p = pair_up(ok)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    d.to_parquet(FREE_OUT, engine="pyarrow", index=False)
    p.to_parquet(PAIRS_OUT, engine="pyarrow", index=False)
    report(d, p)
    print(f"\n  wrote {FREE_OUT.relative_to(REPO)}  ({len(d)} rows)")
    print(f"  wrote {PAIRS_OUT.relative_to(REPO)}  ({len(p)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

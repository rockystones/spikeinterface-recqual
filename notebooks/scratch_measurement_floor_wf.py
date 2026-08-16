"""S09, waveform pass: the floor for amplitude, SNR and the gated yield.

The label pass measured how much the *unit count* moves when the operator or
the algorithm changes. That is one of five metrics the longitudinal analysis
reports. This pass computes the rest -- amplitude, SNR, noise floor and the
gate-passing yield -- using the project's own per-unit definitions
(`ofs_metrics_file`), so the spread comes out in the same units as the trends
it has to size.

Two versions of every metric are reported:

    ungated   every unit the sorter or operator declared
    gated     only units passing the project gate (SNR>=4, >=50 spikes,
              shape, alignment)

The longitudinal metrics are gated, so `gated` is the number that matters. The
pair together answers a question neither answers alone: does the gate absorb
operator disagreement, or amplify it?

Run from repo root:

    uv run python notebooks/scratch_measurement_floor_wf.py [--jobs 8]

See:
- docs/notes/measurement_floor.md
"""

from __future__ import annotations

import argparse
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_cohort_io import array_geometry  # noqa: E402
from scratch_measurement_floor import (  # noqa: E402
    operator_sets,
    sweep_sets,
)
from scratch_rocky_resort import ofs_metrics_file  # noqa: E402

INV = REPO / "data" / "derived" / "monkey_inventory.parquet"
OUT_DIR = REPO / "data" / "derived" / "floor"
WF_FILES = OUT_DIR / "wf_files.parquet"
WF_PAIRS = OUT_DIR / "wf_pairs.parquet"

# Metrics whose longitudinal trends this floor is meant to size. Ratios, not
# differences: a 20 uV shift means something different at 40 uV than at 400.
METRICS = ["n_units", "n_elec_with_units", "amp_med", "amp_p99",
           "snr_med", "rate_med", "noise_med"]


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === One file -> session-level metrics, gated and ungated ===
def session_metrics(path: Path, subject: str, array: str | None,
                    implant: str | None = None) -> dict | None:
    """Aggregate one variant's units the way `longitudinal_metrics` does."""
    try:
        df = ofs_metrics_file(path, {})
    except Exception as exc:  # noqa: BLE001 -- one bad file must not kill the run
        # Reported, never silent: an earlier version swallowed these and lost
        # 813 of 1,233 files while still printing a plausible-looking table.
        return dict(path=str(path), error=f"{type(exc).__name__}: {exc}"[:120])
    if not len(df):
        return dict(path=str(path), error="no units after dropping 0/255")
    n_elec = (array_geometry(subject, array, implant)["n_electrodes"]
              if array else np.nan)

    out: dict = dict(path=str(path))
    for tag, sub in (("all", df), ("gated", df[df.pass_gate])):
        if not len(sub):
            out.update({f"{m}_{tag}": np.nan for m in METRICS})
            out[f"pass_fraction_{tag}"] = 0.0
            continue
        out[f"n_units_{tag}"] = float(len(sub))
        out[f"n_elec_with_units_{tag}"] = float(sub.channel_id.nunique())
        out[f"amp_med_{tag}"] = float(sub.amplitude_uv.median())
        out[f"amp_p99_{tag}"] = float(sub.amplitude_uv.quantile(0.99))
        out[f"snr_med_{tag}"] = float(sub.snr.median())
        out[f"rate_med_{tag}"] = float(sub.firing_rate_hz.median())
        out[f"noise_med_{tag}"] = float(sub.noise_uv.median())
        out[f"units_per_electrode_{tag}"] = len(sub) / n_elec
    out["pass_fraction"] = float(df.pass_gate.mean())
    return out


def run_group(group: list[dict]) -> list[dict]:
    """Metrics for every distinct file in one recording's comparison set."""
    seen: dict[Path, dict | None] = {}
    for job in group:
        for side in ("pa", "pb"):
            p = job[side]
            if p not in seen:
                seen[p] = session_metrics(p, job["subject"], job["array"],
                                      job.get("implant"))
    rows = []
    for p, m in seen.items():
        if m is None:
            continue
        j = next(x for x in group if x["pa"] == p or x["pb"] == p)
        variant = j["a"] if j["pa"] == p else j["b"]
        rows.append(dict(stem=j["stem"], subject=j["subject"],
                         array=j["array"], variant=variant, **m))
    return rows


# %%
# === Spread across variants ===
def pair_spreads(files: pd.DataFrame, jobs: list[dict]) -> pd.DataFrame:
    """Relative difference in each metric, for every comparison."""
    by_path = files.set_index("path").to_dict("index")
    rows = []
    for j in jobs:
        a, b = by_path.get(str(j["pa"])), by_path.get(str(j["pb"]))
        if a is None or b is None:
            continue
        row = dict(stem=j["stem"], subject=j["subject"], array=j["array"],
                   kind=j["kind"], a=j["a"], b=j["b"],
                   three_way=j.get("three_way", False))
        for tag in ("all", "gated"):
            for m in METRICS:
                k = f"{m}_{tag}"
                va, vb = a.get(k), b.get(k)
                if va is None or vb is None or not np.isfinite([va, vb]).all():
                    row[f"rel_{k}"] = np.nan
                    continue
                denom = (abs(va) + abs(vb)) / 2
                row[f"rel_{k}"] = abs(vb - va) / denom if denom else np.nan
        row["d_pass_fraction"] = b.get("pass_fraction", np.nan) - a.get(
            "pass_fraction", np.nan)
        rows.append(row)
    return pd.DataFrame(rows)


def report(pairs: pd.DataFrame, files: pd.DataFrame) -> None:
    banner("1. The floor, per metric  (median relative difference)")
    print("  Gated = units passing the project gate, which is what the")
    print("  longitudinal metrics report. Ungated = every declared unit.\n")
    for tag in ("gated", "all"):
        cols = [f"rel_{m}_{tag}" for m in METRICS]
        t = pairs.groupby("kind")[cols].median().round(3)
        t.columns = [c.replace("rel_", "").replace(f"_{tag}", "")
                     for c in t.columns]
        t.insert(0, "n", pairs.groupby("kind").size())
        print(f"  --- {tag} ---")
        print(t.to_string())
        print()

    banner("2. Does the gate absorb operator disagreement, or amplify it?")
    print("  Ratio of gated spread to ungated spread. Below 1 means the gate")
    print("  removes disagreement; above 1 means it concentrates it.\n")
    rows = []
    for kind, g in pairs.groupby("kind"):
        r = {"kind": kind, "n": len(g)}
        for m in METRICS:
            a = g[f"rel_{m}_all"].median()
            b = g[f"rel_{m}_gated"].median()
            r[m] = round(b / a, 2) if a and np.isfinite(a) and a > 0 else np.nan
        rows.append(r)
    print(pd.DataFrame(rows).set_index("kind").to_string())

    banner("3. How hard the gate works, by variant")
    pf = files.groupby("variant").pass_fraction.agg(["size", "median"]).round(3)
    print(pf.sort_values("median").to_string())

    banner("4. The floor next to the longitudinal effects, per metric")
    lm_path = REPO / "data" / "derived" / "rocky" / "longitudinal_metrics.parquet"
    if not lm_path.exists():
        print("  longitudinal_metrics.parquet missing -- skipped")
        return
    lm = pd.read_parquet(lm_path).dropna(subset=["noise_med"])
    # Acquisition screen, as established in S09: never an outcome criterion.
    keep = lm.groupby("array").noise_med.transform("median") * 2
    lm = lm[lm.noise_med <= keep]
    lm["yr"] = lm.date_dt.dt.year
    op = pairs[pairs.kind == "operator"]
    alg = pairs[pairs.kind == "algorithm"]
    print("  Rocky implant 1, acquisition-screened. Change from the array's")
    print("  best year to its last year, against the floor for that metric.\n")
    name = {"n_units": "n_units", "amp_med": "amp_med",
            "amp_p99": "amp_p99", "snr_med": "snr_med"}
    for arr, g in lm.groupby("array"):
        print(f"  {arr}")
        for metric, col in name.items():
            if col not in g.columns:
                continue
            per_yr = g.groupby("yr")[col].median().dropna()
            if len(per_yr) < 2:
                continue
            best, last = per_yr.max(), per_yr.iloc[-1]
            rel = abs(last - best) / ((abs(best) + abs(last)) / 2)
            fo = op[f"rel_{metric}_gated"].median()
            fa = alg[f"rel_{metric}_gated"].median()
            verdict = ("exceeds both" if rel > max(fo, fa)
                       else "within the floor" if rel < min(fo, fa)
                       else "between")
            print(f"    {metric:10s} best {best:8.1f} -> last {last:8.1f}"
                  f"   rel {rel:5.2f}   operator {fo:5.2f}  algorithm {fa:5.2f}"
                  f"   {verdict}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=8)
    args = ap.parse_args()

    inv = pd.read_parquet(INV)
    jobs = operator_sets(inv) + sweep_sets()
    by_stem: dict[tuple, list[dict]] = {}
    for j in jobs:
        by_stem.setdefault((j["subject"], j["stem"]), []).append(j)
    groups = list(by_stem.values())

    banner("S09 waveform pass -- amplitude, SNR and gated yield")
    print(f"  comparisons: {len(jobs)}   recordings: {len(groups)}")

    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        res = list(ex.map(run_group, groups, chunksize=2))
    files = pd.DataFrame([r for chunk in res for r in chunk])
    files = files.drop_duplicates("path")
    failed = files[files.get("error").notna()] if "error" in files else files.iloc[:0]
    files = files[~files.index.isin(failed.index)]
    print(f"  files with metrics: {len(files)}   failed: {len(failed)}")
    if len(failed):
        import collections
        why = collections.Counter(e.split(":")[0] for e in failed.error)
        for k, v in why.most_common():
            print(f"      {v:5d}  {k}")
        print(f"      example: {failed.iloc[0].path[-70:]}")
        print(f"               {failed.iloc[0].error}")

    pairs = pair_spreads(files, jobs)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files.to_parquet(WF_FILES, engine="pyarrow", index=False)
    pairs.to_parquet(WF_PAIRS, engine="pyarrow", index=False)

    report(pairs, files)
    print(f"\n  wrote {WF_FILES.relative_to(REPO)}  ({len(files)} rows)")
    print(f"  wrote {WF_PAIRS.relative_to(REPO)}  ({len(pairs)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""S10: the same longitudinal metrics across subjects, on one axis.

Rocky implant 1 has been analysed; Nigel, Rocky implant 2 and (when its
originals land) Fisk have not. This runs the identical metric definitions over
all of them so the four array-implants can be compared.

Three decisions this makes deliberately:

**One sorting method, not several.** S09 measured the algorithm floor at 0.36
relative difference in unit count -- larger than the operator floor. Mixing
methods across subjects would inject that spread straight into the cross-subject
comparison, so every subject is scored on the Plexon `-01` automatic sort, which
exists for all of them, using the project's own per-unit metrics.

**An acquisition screen before any trend.** Also from S09: a session whose noise
floor runs 4-5x the array's baseline loses ~94% of its units to the SNR gate
while its candidate count is unchanged. That is amplifier state, not electrode
state. Sessions are screened on their own noise floor -- never on their unit
count, which would be circular.

**Implant age, not calendar date.** Four array-implants spanning 2017-2025 are
only comparable from their own age zero.

Run from repo root:

    uv run python notebooks/scratch_cohort_longitudinal.py [--jobs 8]

See:
- docs/notes/cohort_longitudinal.md
- docs/notes/measurement_floor.md
"""

from __future__ import annotations

import argparse
import json
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
from _paths import MONKEY_ROOT  # noqa: E402
from scratch_cohort_io import array_geometry  # noqa: E402
from scratch_rocky_resort import ofs_metrics_file  # noqa: E402

INV = REPO / "data" / "derived" / "monkey_inventory.parquet"
CONFIG_DIR = REPO / "configs" / "subjects"
OUT_DIR = REPO / "data" / "derived" / "cohort"
UNITS_OUT = OUT_DIR / "cohort_units.parquet"
SESSIONS_OUT = OUT_DIR / "cohort_sessions.parquet"
TRENDS_OUT = OUT_DIR / "cohort_trends.parquet"

AUTO_CHAIN = "-01"
NOISE_SCREEN_MULT = 2.0     # a session above this x the array median is out

# Metrics carried through to the trend table.
TREND_METRICS = ["n_units", "units_per_electrode", "elec_coverage",
                 "amp_med", "amp_p99", "snr_med", "rate_med", "noise_med",
                 "pass_fraction"]


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === Session list ===
def surgery_dates() -> dict[tuple[str, str], pd.Timestamp | None]:
    """(subject, implant) -> surgery date, for the implant-age axis."""
    out: dict[tuple[str, str], pd.Timestamp | None] = {}
    for cfg in sorted(CONFIG_DIR.glob("*.json")):
        reg = json.loads(cfg.read_text(encoding="utf-8"))
        for im in reg.get("implants", []):
            sd = im.get("surgery_date")
            out[(reg["subject"], im["implant"])] = (
                pd.Timestamp(sd) if sd else None)
    return out


def build_worklist(inv: pd.DataFrame) -> list[dict]:
    """One job per automatically sorted recording, any subject.

    **Exactly one `-01` per recording.** The Nigel OFS sweep holds eight
    algorithm runs of the same 78 sessions, every one of them chained `-01`.
    Taking them all would count those sessions eight times and mix the
    algorithm spread -- 0.36 relative, the largest term in S09 -- into a
    cross-subject comparison whose whole point is to hold method constant.
    """
    nev = inv[(inv.role == "snippets") & (inv.chain == AUTO_CHAIN)
              & inv.excluded.isna()
              & (~inv.folder.str.contains("OFS sorting test", na=False))]
    jobs: dict[tuple, dict] = {}
    for r in nev.itertuples():
        if pd.isna(r.date) or r.array is None:
            continue
        key = (r.subject, r.implant, r.array, r.date, r.run, r.headstage)
        if key in jobs:
            continue                      # first wins; duplicates are copies
        jobs[key] = dict(path=str(MONKEY_ROOT / r.rel), subject=r.subject,
                         implant=r.implant, array=r.array,
                         date=r.date, headstage=r.headstage or "unknown",
                         run=r.run)
    return list(jobs.values())


# %%
# === Per-session metrics ===
def one_session(job: dict) -> dict | None:
    """Project metrics for one recording's automatic sort."""
    try:
        df = ofs_metrics_file(Path(job["path"]), {})
    except Exception as exc:  # noqa: BLE001
        return dict(**{k: v for k, v in job.items() if k != "path"},
                    error=f"{type(exc).__name__}: {exc}"[:110])
    if not len(df):
        return dict(**{k: v for k, v in job.items() if k != "path"},
                    error="no units")
    geo = array_geometry(job["subject"], job["array"], job["implant"])
    n_elec = geo["n_electrodes"]
    gated = df[df.pass_gate]
    out = {k: v for k, v in job.items() if k != "path"}
    out.update(
        n_candidates=float(len(df)),
        pass_fraction=float(df.pass_gate.mean()),
        # The noise floor is a property of the recording, not of the gate, so
        # it is taken over every candidate -- it is the screening variable and
        # must not be conditioned on the screen's own outcome.
        noise_med=float(df.noise_uv.median()),
        n_electrodes=float(n_elec),
        geometry_source=geo["source"],
    )
    if len(gated):
        out.update(
            n_units=float(len(gated)),
            n_elec_with_units=float(gated.channel_id.nunique()),
            units_per_electrode=len(gated) / n_elec,
            elec_coverage=gated.channel_id.nunique() / n_elec,
            amp_med=float(gated.amplitude_uv.median()),
            amp_p99=float(gated.amplitude_uv.quantile(0.99)),
            snr_med=float(gated.snr.median()),
            rate_med=float(gated.firing_rate_hz.median()),
        )
    else:
        out.update({k: (0.0 if k.startswith(("n_", "units_", "elec_"))
                        else np.nan) for k in TREND_METRICS})
        out["noise_med"] = float(df.noise_uv.median())
    return out


# %%
# === Trends ===
def add_axes(s: pd.DataFrame) -> pd.DataFrame:
    """Attach implant age and the acquisition screen."""
    sd = surgery_dates()
    ages = []
    for r in s.itertuples():
        surgery = sd.get((r.subject, r.implant))
        ages.append((r.date - surgery).days if surgery is not None else np.nan)
    s = s.copy()
    s["implant_age_days"] = ages
    # Only Rocky implant 2 has a recorded surgery date, so a true implant-age
    # axis exists for one of four array-implants. Days-since-first-recording is
    # the honest fallback: it aligns the series at a common origin without
    # pretending to know when each array went in. The offset between the two
    # is unknown per subject, so cross-subject age comparisons stay qualified.
    s["days_since_first"] = (
        s.groupby(["subject", "implant", "array"])
        .date.transform(lambda d: (d - d.min()).dt.days))
    s["age_axis"] = np.where(s.implant_age_days.notna(),
                             "implant_age", "days_since_first")
    # Screen per array-implant: baselines differ between animals and headstages.
    key = ["subject", "implant", "array"]
    s["noise_baseline"] = s.groupby(key).noise_med.transform("median")
    s["high_noise"] = s.noise_med > NOISE_SCREEN_MULT * s.noise_baseline
    return s


def trends(s: pd.DataFrame) -> pd.DataFrame:
    """Spearman rho per array-implant per metric, screened and unscreened."""
    rows = []
    for (sub, imp, arr), g in s.groupby(["subject", "implant", "array"]):
        clean = g[~g.high_noise]
        for m in TREND_METRICS:
            if m not in g.columns:
                continue
            for tag, d in (("all", g), ("screened", clean)):
                # Sort before head/tail. `groupby` preserves *row* order, not
                # date order, so `first`/`last` silently reported the first and
                # last rows of the file. Chase arrives in filename order, whose
                # first entry is its last session, and its amplitude read
                # 65 -> 109 uV against a rho of -0.71. rho itself was always
                # right; only the two summary columns were wrong.
                d = d.dropna(subset=[m, "date"]).sort_values("date")
                if len(d) < 8 or d[m].nunique() < 3:
                    continue
                x = d.date.map(pd.Timestamp.toordinal)
                rho, p = spearmanr(x, d[m])
                rows.append(dict(
                    subject=sub, implant=imp, array=arr, metric=m, scope=tag,
                    n=len(d), rho=round(float(rho), 3), p=float(p),
                    first=float(d[m].head(5).median()),
                    last=float(d[m].tail(5).median()),
                    span_days=int((d.date.max() - d.date.min()).days),
                ))
    return pd.DataFrame(rows)


def report(s: pd.DataFrame, tr: pd.DataFrame) -> None:
    banner("1. Sessions scored, by array-implant")
    t = s.groupby(["subject", "implant", "array"]).agg(
        n=("date", "size"),
        first=("date", "min"), last=("date", "max"),
        high_noise=("high_noise", "sum"),
        geometry=("geometry_source", "first"),
    )
    t["first"] = t["first"].dt.date
    t["last"] = t["last"].dt.date
    print(t.to_string())
    err = s[s.get("error").notna()] if "error" in s else s.iloc[:0]
    if len(err):
        print(f"\n  failed: {len(err)}")
        print(err.error.value_counts().head(5).to_string())

    banner("2. The acquisition screen, per array-implant")
    print("  Sessions whose own noise floor exceeds 2x the array median.")
    print("  Screened on acquisition, never on unit count (S09).\n")
    for (sub, imp, arr), g in s.groupby(["subject", "implant", "array"]):
        hi = g[g.high_noise]
        if not len(g):
            continue
        lo = g[~g.high_noise]
        ratio = (hi.n_units.median() / max(lo.n_units.median(), 1)
                 if len(hi) else np.nan)
        print(f"  {sub:6s} {imp} {arr:10s} baseline "
              f"{g.noise_baseline.iloc[0]:5.1f} uV   dropped {len(hi):3d}/"
              f"{len(g):3d}   units ratio {ratio if len(hi) else float('nan'):.2f}")

    banner("3. Yield trend per array-implant  (units per electrode)")
    y = tr[(tr.metric == "units_per_electrode")].copy()
    for scope in ("all", "screened"):
        d = y[y.scope == scope]
        if not len(d):
            continue
        print(f"  --- {scope} ---")
        print(d[["subject", "implant", "array", "n", "rho", "p", "first",
                 "last", "span_days"]].to_string(index=False))
        print()

    banner("4. Which metrics move, and which do not")
    print("  Screened scope only. Marked * where p < 0.05.\n")
    d = tr[tr.scope == "screened"].copy()
    d["sig"] = np.where(d.p < 0.05, "*", " ")
    piv = d.pivot_table(index="metric",
                        columns=["subject", "implant", "array"],
                        values="rho")
    print(piv.round(2).to_string())
    print("\n  Median unit SNR flat while yield falls is the signature of")
    print("  losing units rather than degrading the survivors.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--subject", default=None, help="limit to one subject")
    args = ap.parse_args()

    inv = pd.read_parquet(INV)
    jobs = build_worklist(inv)
    if args.subject:
        jobs = [j for j in jobs if j["subject"].lower() == args.subject.lower()]

    banner("S10 -- cross-subject longitudinal metrics")
    print(f"  recordings to score: {len(jobs)}")
    print(pd.Series([f"{j['subject']} {j['implant']}"
                     for j in jobs]).value_counts().to_string())

    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        res = [r for r in ex.map(one_session, jobs, chunksize=4) if r]
    s = pd.DataFrame(res)
    s = add_axes(s)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    s.to_parquet(SESSIONS_OUT, engine="pyarrow", index=False)
    tr = trends(s[s.get("error").isna()] if "error" in s else s)
    tr.to_parquet(TRENDS_OUT, engine="pyarrow", index=False)

    report(s, tr)
    print(f"\n  wrote {SESSIONS_OUT.relative_to(REPO)}  ({len(s)} rows)")
    print(f"  wrote {TRENDS_OUT.relative_to(REPO)}  ({len(tr)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

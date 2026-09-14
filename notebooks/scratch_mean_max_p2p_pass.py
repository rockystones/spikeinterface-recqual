"""Exact mean-max-P2P over the Blackrock cohort, from the raw sorted NEVs.

The approximation check in `scratch_mean_max_p2p.py` disqualified
(peak - trough) from units_long: exact for only 26.5% of units, under-reading
to -29% in the tail - and the metric takes the per-channel MAX, so tail
errors land directly in it. This pass computes the legacy definition
verbatim, per session, for Rocky (I1 + I2), Nigel and Fisk:

  per unit     P2P = max(mean(raw sorted snippets)) - min(...)
               -- the plain mean, no realignment, as the legacy layer did
  per channel  max over that channel's Plexon units (0 and 255 dropped)
  per session  mean over active channels (nan variant) and over all 96
               (zero variant), both kept per the legacy plots

Outputs:
  data/derived/cohort/mmp2p_shards/<subject>__<stem>.parquet
      per-channel max P2P - the audit grain
  data/derived/cohort/mean_max_p2p.parquet
      per session/array/subject: both means, n_active, n_units

Resumes from shards. Run in the background from repo root:

    uv run python notebooks/scratch_mean_max_p2p_pass.py

See nav W-017 / D-013; docs/notes/longitudinal_metrics.md.
"""

from __future__ import annotations

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
from scratch_rocky_resort import open_nev, read_electrode  # noqa: E402

DER = REPO / "data" / "derived"
SHARDS = DER / "cohort" / "mmp2p_shards"
OUT = DER / "cohort" / "mean_max_p2p.parquet"
PLEXON_DROP = (0, 255)
N_CH = 96


def worklist() -> list[dict]:
    """Every reachable -01 NEV session for the three Blackrock animals.

    Rocky I1 comes from the repaired session_index (the OFS rows); Rocky I2,
    Nigel and Fisk from the inventory's snippets/-01 rows, resolved the same
    way the ns5 resort resolves them.
    """
    from scratch_ns5_resort import INV, MONKEY_ROOT

    jobs: dict[tuple[str, str], dict] = {}

    ix = pd.read_parquet(DER / "rocky" / "session_index.parquet")
    for r in ix[ix.kind == "OFS"].itertuples():
        stem = str(r.stem).removesuffix("-01")
        jobs[("Rocky", stem)] = dict(
            subject="Rocky", stem=stem, array=str(r.array),
            date=str(pd.Timestamp(r.date).date()), nev=str(r.path))

    inv = pd.read_parquet(INV)
    sn = inv[(inv.role == "snippets") & (inv.chain == "-01")]
    for r in sn.itertuples():
        if r.subject not in ("Nigel", "Fisk", "Rocky"):
            continue
        p = getattr(r, "path", None)
        nev = Path(p) if isinstance(p, str) and p else MONKEY_ROOT / r.rel
        stem = str(r.stem)
        key = (str(r.subject), stem)
        if key in jobs:
            continue
        date = getattr(r, "date", None)
        jobs[key] = dict(
            subject=str(r.subject), stem=stem, array=str(r.array),
            date=str(pd.Timestamp(date).date()) if pd.notna(date) else "",
            nev=str(nev))
    out = [j for j in jobs.values() if Path(j["nev"]).exists()]
    skipped = len(jobs) - len(out)
    print(f"  worklist: {len(out)} reachable sessions "
          f"({skipped} offline skipped)")
    return sorted(out, key=lambda j: (j["subject"], j["stem"]))


def session_channels(nev: Path) -> pd.DataFrame:
    """Per-channel max-unit P2P for one sorted NEV, legacy definition."""
    raw, nmeta, chan_by_elec = open_nev(nev)
    rows = []
    for elec in sorted(chan_by_elec):
        e = read_electrode(raw, nmeta, chan_by_elec[elec])
        if e is None:
            continue
        wf, pu = e["wf"], e["plexon_unit"]
        best, n_units = 0.0, 0
        for u in np.unique(pu):
            if u in PLEXON_DROP:
                continue
            tmpl = wf[pu == u].mean(axis=0)     # plain mean, no realignment
            best = max(best, float(tmpl.max() - tmpl.min()))
            n_units += 1
        if n_units:
            rows.append(dict(channel_id=int(elec), max_p2p_uv=best,
                             n_units=n_units))
    return pd.DataFrame(rows)


def main() -> int:
    SHARDS.mkdir(parents=True, exist_ok=True)
    jobs = worklist()
    banner(f"mean-max-P2P exact pass: {len(jobs)} sessions")
    for i, j in enumerate(jobs, 1):
        shard = SHARDS / f"{j['subject']}__{j['stem']}.parquet"
        if shard.exists():
            continue
        try:
            ch = session_channels(Path(j["nev"]))
        except Exception as exc:  # noqa: BLE001
            print(f"  ! [{i}/{len(jobs)}] {j['stem'][:48]}: "
                  f"{type(exc).__name__}: {exc}", flush=True)
            continue
        for k, v in j.items():
            if k != "nev":
                ch[k] = v
        ch.to_parquet(shard, index=False)
        if i % 25 == 0 or i == len(jobs):
            print(f"  [{i}/{len(jobs)}] {j['subject']} {j['stem'][:44]} "
                  f"active={len(ch)}", flush=True)

    banner("aggregate")
    parts = [pd.read_parquet(p) for p in sorted(SHARDS.glob("*.parquet"))]
    allch = pd.concat(parts, ignore_index=True)
    rows = []
    for (sub, stem), g in allch.groupby(["subject", "stem"], observed=True):
        rows.append(dict(
            subject=sub, stem=stem, array=g["array"].iloc[0],
            date=g["date"].iloc[0],
            max_p2p_mean_nan=float(g.max_p2p_uv.mean()),
            max_p2p_mean_zero=float(g.max_p2p_uv.sum() / N_CH),
            n_active=int(len(g)), n_units=int(g.n_units.sum())))
    out = pd.DataFrame(rows)
    out.to_parquet(OUT, index=False)
    print(out.groupby("subject").agg(
        sessions=("stem", "size"),
        nan_med=("max_p2p_mean_nan", "median"),
        zero_med=("max_p2p_mean_zero", "median")).round(1).to_string())
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

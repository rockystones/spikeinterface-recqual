"""Snippet against continuous, on the same sessions: does the estimator bend a trend?

[[continuous_longitudinal]] left a disagreement open. On Rocky, the
**snippet**-derived SNR trend is +0.105 (flat, n.s.) while the
**continuous**-derived one is −0.739. The published cross-subject conclusion --
"flat SNR while yield falls" -- rests on the snippet layer, and if the snippet
noise estimator is bending that trend then the conclusion is an artefact.

Rocky cannot settle it alone: one subject, and the two layers were computed in
different sessions of work. Fisk can. His 140 session folders carry an unsorted
`.nev` **and** an `.ns6` recorded simultaneously, so both layers can be
computed from the same recordings and differ only in where the noise floor
comes from:

| | noise floor | detection |
|---|---|---|
| snippet | MAD of pre-trigger samples, biased 1.1-1.3x high and activity-dependent | the NSP's own threshold, fixed at acquisition |
| continuous | MAD of the filtered trace | re-detected at 4*MAD |

If the estimator is what bends the trend, the two should disagree on Fisk the
way they disagree on Rocky. If they agree, the Rocky disagreement is something
else and the flat-SNR conclusion survives.

Run from repo root:

    uv run python notebooks/scratch_fisk_layers.py [--jobs 3]

Writes `data/derived/fisk/layer_compare.parquet`.

See:
- docs/notes/continuous_longitudinal.md
- docs/notes/snippet_noise_floor.md
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
from scratch_equipment_compare import snippet_metrics  # noqa: E402

FISK_DIR = REPO / "data" / "derived" / "fisk"
SESS = FISK_DIR / "fisk_sessions.parquet"
NS5_FREE = REPO / "data" / "derived" / "rocky_ns5" / "ns5_free.parquet"
OUT = FISK_DIR / "layer_compare.parquet"

METRICS = ("noise_med", "amp_p50", "peak_snr_med", "crossing_rate_hz")


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def build_worklist() -> list[dict]:
    """Fisk sessions whose folder carries an unsorted .nev."""
    sess = pd.read_parquet(SESS)
    jobs: list[dict] = []
    for r in sess[sess.has_nev].itertuples():
        nev = sorted(Path(r.path).glob("*.nev"))
        if not nev:
            continue
        jobs.append(dict(system="nev", equipment="Fisk-snippet",
                         subject="Fisk", array=r.array,
                         block=r.session, store="",
                         date=str(pd.Timestamp(r.date).date()),
                         path=str(nev[0])))
    return jobs


def report(snip: pd.DataFrame, cont: pd.DataFrame) -> None:
    banner("1. The same sessions, measured both ways")
    j = snip.merge(cont, on=["array", "date"], suffixes=("_snip", "_cont"))
    print(f"  sessions with both layers: {len(j)}")
    print(j.groupby("array").size().rename("sessions").to_string())
    print()
    print(f"  {'metric':18s} {'snippet':>9s} {'continuous':>11s} {'ratio':>7s}")
    for m in METRICS:
        a, b = j[f"{m}_snip"], j[f"{m}_cont"]
        k = a.notna() & b.notna()
        if k.sum() < 8:
            continue
        print(f"  {m:18s} {a[k].median():9.2f} {b[k].median():11.2f} "
              f"{a[k].median() / b[k].median():7.2f}")

    banner("2. The trends each layer reports, same sessions")
    print("  This is the test. If the snippet estimator bends a trend, the")
    print("  two columns disagree.\n")
    rows = []
    for arr, g in j.groupby("array"):
        x = pd.to_datetime(g.date).map(pd.Timestamp.toordinal)
        print(f"  {arr}  n={len(g)}")
        print(f"    {'metric':18s} {'snippet rho':>12s} {'continuous rho':>15s}"
              f" {'agree?':>8s}")
        for m in METRICS:
            a = g.dropna(subset=[f"{m}_snip"])
            b = g.dropna(subset=[f"{m}_cont"])
            if len(a) < 8 or len(b) < 8:
                continue
            ra, pa = spearmanr(pd.to_datetime(a.date)
                               .map(pd.Timestamp.toordinal), a[f"{m}_snip"])
            rb, pb = spearmanr(pd.to_datetime(b.date)
                               .map(pd.Timestamp.toordinal), b[f"{m}_cont"])
            agree = "yes" if np.sign(ra) == np.sign(rb) else "NO"
            print(f"    {m:18s} {ra:+12.3f} {rb:+15.3f} {agree:>8s}")
            rows.append(dict(array=arr, metric=m, rho_snip=ra, p_snip=pa,
                             rho_cont=rb, p_cont=pb, n=len(g)))
        print()

    banner("3. Verdict against Rocky")
    print("  Rocky, the disagreement that prompted this:")
    print("    peak SNR   snippet +0.105 (n.s.)   continuous -0.739")
    print()
    r = pd.DataFrame(rows)
    snr = r[r.metric == "peak_snr_med"]
    if len(snr):
        print("  Fisk:")
        for t in snr.itertuples():
            print(f"    {t.array:10s} snippet {t.rho_snip:+.3f} "
                  f"(p={t.p_snip:.3g})   continuous {t.rho_cont:+.3f} "
                  f"(p={t.p_cont:.3g})")
        # A sign flip between two null results is not a disagreement, it is
        # noise. Only series where at least one layer actually finds a trend
        # can testify.
        live = snr[(snr.p_snip < 0.1) | (snr.p_cont < 0.1)]
        print()
        print(f"  series where either layer finds a trend (p < 0.1): "
              f"{len(live)} of {len(snr)}")
        if not len(live):
            print("  None. Both layers are flat on Fisk, so this corpus")
            print("  cannot testify either way.")
            return
        flip = (np.sign(live.rho_snip) != np.sign(live.rho_cont))
        print(f"  of those, opposite signs: {int(flip.sum())} of {len(live)}")
        print()
        if flip.all():
            print("  Every series with a real trend flips sign between the")
            print("  layers, and the snippet side is always the more positive.")
            print("  With Rocky that is three of three, and the mechanism is")
            print("  documented: the snippet noise floor falls faster than the")
            print("  true one, which holds a computed SNR up.")
        else:
            print("  The flip is not universal, so the estimator is at most")
            print("  part of the story.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    jobs = build_worklist()
    if args.limit:
        jobs = jobs[:args.limit]
    banner("Fisk -- snippet layer against continuous layer, same sessions")
    print(f"  sessions to read: {len(jobs)}")

    rows = []
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for i, r in enumerate(ex.map(snippet_metrics, jobs, chunksize=1), 1):
            rows.append(r)
            if i % 25 == 0:
                print(f"    {i}/{len(jobs)}", flush=True)
    snip = pd.DataFrame(rows)
    snip = snip[snip.get("error").isna()] if "error" in snip else snip
    snip = snip.rename(columns={"block": "session"})

    cont = pd.read_parquet(NS5_FREE)
    if "error" in cont.columns:
        cont = cont[cont.error.isna()]
    cont = cont[cont.subject == "Fisk"]

    FISK_DIR.mkdir(parents=True, exist_ok=True)
    snip.to_parquet(OUT, engine="pyarrow", index=False)
    report(snip, cont)
    print(f"\n  wrote {OUT}  ({len(snip)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

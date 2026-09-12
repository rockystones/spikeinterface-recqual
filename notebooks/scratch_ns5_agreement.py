"""Multi-sorter agreement: the consensus layer the ns5 resort never computed.

The resort (`scratch_ns5_resort.py`) ran the four-sorter pool over 238 stems
but kept only summary rows and each sorter's overlap with the NEV reference --
the spike trains were scratch, since deleted, except for four Fisk Medial
stems (2023-06 .. 2024-08) whose work folders survive with **all four
sorters**. CLAUDE.md's metrics layer 3 wants the agreement *structure* as a
longitudinal metric, so this does two things at the two scales available:

1. **Direct agreement, 4 stems.** `compare_multiple_sorters` over
   MountainSort5, Kilosort4, SpykingCircus2 and Tridesclous2, reporting
   pairwise match fractions and the consensus ladder (units found by >= k
   sorters), across a 14-month span of one array.

2. **Dispersion proxy, all 238 stems.** Without spike trains, sorter
   disagreement is still visible in the summary table: the CV of unit count
   across the four sorters, and the spread of their NEV-recovery fractions.
   Computed per stem and trended over implant age per array. A proxy, not a
   replacement -- it sees how much the sorters disagree, not which units they
   disagree on.

Run from repo root:

    uv run python notebooks/scratch_ns5_agreement.py

See docs/notes/multisorter_agreement.md.
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

WORK = REPO / "data" / "derived" / "ns5" / "work"
OUT = REPO / "data" / "derived" / "ns5"
SORTERS = ["mountainsort5", "kilosort4", "spykingcircus2", "tridesclous2"]


# %%
def load_sorting(stem: str, sorter: str):
    """One retained sorter output, without touching the source recording."""
    from spikeinterface.sorters import read_sorter_folder

    folder = WORK / f"{stem}__{sorter}"
    if not folder.exists():
        return None
    try:
        return read_sorter_folder(folder, register_recording=False)
    except Exception as exc:  # noqa: BLE001
        print(f"    ! {stem}/{sorter}: {type(exc).__name__}: {exc}")
        return None


def direct_agreement(stem: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pairwise agreement and the consensus ladder for one stem."""
    from spikeinterface.comparison import compare_multiple_sorters

    sortings, names = [], []
    for s in SORTERS:
        so = load_sorting(stem, s)
        if so is not None:
            sortings.append(so)
            names.append(s)
    if len(sortings) < 2:
        return pd.DataFrame(), pd.DataFrame()

    comp = compare_multiple_sorters(sortings, name_list=names,
                                    delta_time=0.4, match_score=0.5,
                                    verbose=False)
    pairs = []
    for (a, b), c in comp.comparisons.items():
        # units of a matched to some unit of b at >= match_score, and back
        m12 = c.hungarian_match_12
        m21 = c.hungarian_match_21
        n1, n2 = len(m12), len(m21)
        f1 = float((m12 != -1).mean()) if n1 else np.nan
        f2 = float((m21 != -1).mean()) if n2 else np.nan
        pairs.append(dict(stem=stem, a=str(a), b=str(b), n_a=n1, n_b=n2,
                          frac_a_matched=f1, frac_b_matched=f2))
    ladder = []
    for k in range(2, len(names) + 1):
        agr = comp.get_agreement_sorting(minimum_agreement_count=k)
        ladder.append(dict(stem=stem, min_agreement=k,
                           n_units=int(len(agr.unit_ids))))
    counts = {n: int(len(s.unit_ids)) for n, s in zip(names, sortings,
                                                      strict=True)}
    ladder.insert(0, dict(stem=stem, min_agreement=1,
                          n_units=int(np.sum(list(counts.values())))))
    print(f"  {stem}: " + "  ".join(f"{n}={c}" for n, c in counts.items()))
    return pd.DataFrame(pairs), pd.DataFrame(ladder)


# %%
def dispersion_proxy() -> pd.DataFrame:
    """Per-stem sorter disagreement from the summary table, all 238 stems."""
    d = pd.read_parquet(OUT / "ns5_sorters.parquet")
    ok = d[d.error.isna() & d.n_units.notna()].copy()
    g = (ok.groupby(["subject", "implant", "array", "stem", "date"],
                    observed=True)
           .agg(n_sorters=("sorter", "nunique"),
                units_mean=("n_units", "mean"),
                units_cv=("n_units", lambda s: s.std() / s.mean()
                          if s.mean() else np.nan),
                nev_rec_spread=("frac_nev_recovered",
                                lambda s: s.max() - s.min()))
           .reset_index())
    return g[g.n_sorters == 4]


def main() -> int:
    banner("1. Direct four-sorter agreement on the retained stems")
    stems = sorted({p.name.rsplit("__", 1)[0] for p in WORK.iterdir()})
    full = [s for s in stems
            if all((WORK / f"{s}__{x}").exists() for x in SORTERS)]
    print(f"  {len(full)} stems with all four sorters retained")
    all_pairs, all_ladder = [], []
    for stem in full:
        pairs, ladder = direct_agreement(stem)
        if len(pairs):
            all_pairs.append(pairs)
            all_ladder.append(ladder)
    if all_pairs:
        pairs = pd.concat(all_pairs, ignore_index=True)
        ladder = pd.concat(all_ladder, ignore_index=True)
        print("\n  pairwise fraction matched (mean over stems):")
        sym = pd.concat([
            pairs.rename(columns={"a": "x", "b": "y",
                                  "frac_a_matched": "frac"})[["x", "y",
                                                              "frac"]],
            pairs.rename(columns={"b": "x", "a": "y",
                                  "frac_b_matched": "frac"})[["x", "y",
                                                              "frac"]]])
        print(sym.pivot_table(index="x", columns="y", values="frac")
                 .round(2).to_string())
        print("\n  consensus ladder (units found by >= k sorters):")
        print(ladder.pivot_table(index="stem", columns="min_agreement",
                                 values="n_units").astype(int).to_string())
        pairs.to_parquet(OUT / "agreement_pairs.parquet", index=False)
        ladder.to_parquet(OUT / "agreement_ladder.parquet", index=False)

    banner("2. Dispersion proxy across all resorted stems")
    prox = dispersion_proxy()
    print(f"  {len(prox)} stems with all four sorters")
    print(prox.groupby(["subject", "array"], observed=True)
              .agg(n=("stem", "size"), cv_median=("units_cv", "median"),
                   nev_spread_median=("nev_rec_spread", "median"))
              .round(3).to_string())

    from scipy.stats import spearmanr
    print("\n  does disagreement grow with implant age?")
    for (sub, arr), g in prox.groupby(["subject", "array"], observed=True):
        if len(g) < 15:
            continue
        age = pd.to_datetime(g.date).map(pd.Timestamp.toordinal)
        for col in ("units_cv", "nev_rec_spread"):
            rho, p = spearmanr(age, g[col], nan_policy="omit")
            print(f"    {sub:6s} {arr:10s} {col:15s} rho={rho:+.3f} p={p:.3g}"
                  f"  (n={len(g)})")
    prox.to_parquet(OUT / "agreement_dispersion.parquet", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

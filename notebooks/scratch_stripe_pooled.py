"""Pooling the four striped arrays into one permutation test.

`surface_conditions.md` ran the stripe permutation per array -- five treated
stripes against five untreated, 252 assignments -- and found nothing, with a
detectable-effect bound near 30% on yield. It deliberately did not pool,
because the coatings differ between arrays (TNP-L1 vs TNP on two, EDCNHS-L1
vs bare on two) and the animals disagreed on direction.

This is the pooled variant, run as the sensitivity check it is: **what does
the cohort rule out if the four arrays are allowed to share one L1 term?**
The statistic is the mean across arrays of each array's own normalised
stripe contrast, and the null redraws the 5-of-10 assignment independently
per array, so the array's spatial structure is held fixed exactly as in the
per-array test. Pooling four arrays roughly halves the detectable effect.

Run from repo root:

    uv run python notebooks/scratch_stripe_pooled.py

Results recorded in docs/notes/surface_conditions.md.
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
from scratch_ring_geometry import ring_frame  # noqa: E402

RNG = np.random.default_rng(20260912)
N_DRAWS = 20_000
METRICS = ["n_gated", "rate_hz", "noise_uv", "peak_snr"]
# even CMP columns carry L1 on every array (surface_conditions.md)
TREATED_COLS = frozenset(range(0, 10, 2))


# %%
def stripe_means(method: str = "plexon-01") -> pd.DataFrame:
    """Mean metric per CMP column (stripe), per array.

    Electrodes are first averaged over their sessions, then over the stripe,
    so a stripe mean is a mean of electrode means -- the same construction the
    per-array test used.
    """
    d = pd.read_parquet(REPO / "data" / "derived" / "surface"
                        / "electrode_metrics.parquet")
    d = d[d.method == method].copy()
    d["serial"] = (d.serial.astype(str).str.replace("SN", "", regex=False)
                    .str.strip())
    rows = []
    for (sub, arr, serial), g in d.groupby(["subject", "array", "serial"],
                                           observed=True):
        geo = ring_frame(serial)[["channel_id", "col"]]
        per_elec = (g.groupby("channel_id", observed=True)[METRICS]
                     .mean().reset_index().merge(geo, on="channel_id"))
        for met in METRICS:
            s = per_elec.groupby("col")[met].mean()
            for col, v in s.items():
                rows.append(dict(subject=sub, array=arr, metric=met,
                                 col=int(col), value=float(v)))
    return pd.DataFrame(rows)


def pooled_permutation(sm: pd.DataFrame) -> pd.DataFrame:
    """The pooled test: one shared treated/untreated term across four arrays.

    Per array the contrast is (treated mean - untreated mean) / array mean;
    the pooled statistic is the average of the four. The null redraws each
    array's 5-of-10 stripe assignment independently, which preserves every
    array's own stripe-mean distribution.
    """
    out = []
    for met, g in sm.groupby("metric"):
        arrays = []
        for (_, _), gg in g.groupby(["subject", "array"], observed=True):
            v = gg.set_index("col").value.reindex(range(10))
            base = v.mean()
            if not np.isfinite(base) or base == 0:
                continue
            arrays.append(v.to_numpy() / base)
        arrays = np.array(arrays)                    # (4, 10) normalised
        treated = np.array([c in TREATED_COLS for c in range(10)])

        def contrast(mask: np.ndarray, a: np.ndarray = arrays) -> float:
            return float(np.nanmean(a[:, mask]) - np.nanmean(a[:, ~mask]))

        obs = float(np.mean([contrast(treated[None][0])]))
        # draw independent 5-of-10 masks per array
        null = np.empty(N_DRAWS)
        for k in range(N_DRAWS):
            vals = []
            for a in arrays:
                cols = RNG.choice(10, 5, replace=False)
                m = np.zeros(10, bool)
                m[cols] = True
                vals.append(np.nanmean(a[m]) - np.nanmean(a[~m]))
            null[k] = np.mean(vals)
        p = float(np.mean(np.abs(null) >= abs(obs)))
        # what effect would have reached p<0.05, as % of the array mean
        detectable = float(np.quantile(np.abs(null), 0.95)) * 100
        out.append(dict(metric=met, n_arrays=len(arrays),
                        observed_pct=obs * 100, p_perm=p,
                        null_sd_pct=float(null.std()) * 100,
                        detectable_pct=detectable))
    return pd.DataFrame(out)


def main() -> int:
    banner("Pooled stripe permutation, four arrays as one L1 term")
    sm = stripe_means()
    res = pooled_permutation(sm)
    print(res.round(3).to_string(index=False))
    print("\n  observed = treated-minus-untreated, % of array mean, averaged"
          "\n  over the four arrays; detectable = |effect| needed for p<0.05.")
    res.to_parquet(REPO / "data" / "derived" / "surface"
                   / "stripe_pooled.parquet", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

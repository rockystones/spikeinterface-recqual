"""Sorted-unit yield by concentric ring -- the arm ring_geometry deferred.

`scratch_ring_geometry.py` established the position result on the
sorting-free layer: no consistent geometric effect on ephys, a large
animal-specific one, and a real acquired impedance edge effect. This runs the
same borders/rings machinery on the **sorted layer** -- gated units per
electrode -- which is the quantity the project actually reports
longitudinally, and the one Forrest et al.'s PTPV/SNR findings would matter
for if they transferred.

Sources differ per animal and are kept separate:

- Nigel, Fisk: `data/derived/surface/electrode_metrics.parquet`, per-session
  gated units per channel, 13 sorting methods (`plexon-01` is the one that
  exists for every session and is the primary here).
- Rocky I1: `data/derived/rocky/curation_labels.parquet`, per-date gated
  units per channel across the five snippet methods (`ofs` is the Plexon
  reference).

Same discipline as ring_geometry: electrode surfaces are medians of
per-session values (aggregation rule), the null is the toroidal shift, the
isotropy check is the four-border count, and the bank confound is handled by
the within-bank contrast (bank B holds no border electrode).

Run from repo root:

    uv run python notebooks/scratch_yield_rings.py

Results recorded in docs/notes/ring_geometry.md.
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
from scratch_ring_geometry import (  # noqa: E402
    ARRAYS,
    attach_bank,
    border_signs,
    ring_frame,
    to_grid,
    toroidal_null,
    within_bank_contrast,
)

OUT = REPO / "data" / "derived" / "ring"


# %%
def nigel_fisk_yield(method: str = "plexon-01") -> pd.DataFrame:
    """Per-electrode mean gated yield for the four striped arrays."""
    d = pd.read_parquet(REPO / "data" / "derived" / "surface"
                        / "electrode_metrics.parquet")
    d = d[d.method == method].copy()
    d["serial"] = d.serial.astype(str).str.replace("SN", "", regex=False).str.strip()
    per = (d.groupby(["subject", "array", "serial", "channel_id"],
                     observed=True)
             .agg(value=("n_gated", "mean"), n_sessions=("session", "nunique"))
             .reset_index())
    return per


def rocky_yield(method: str = "ofs") -> pd.DataFrame:
    """Per-electrode mean gated yield for Rocky I1 from the snippet sorts.

    `curation_labels` is one row per unit, so a channel with no units on a
    date is absent -- the zero must be restored from the session grid before
    averaging, or quiet electrodes silently inflate.
    """
    d = pd.read_parquet(REPO / "data" / "derived" / "rocky"
                        / "curation_labels.parquet")
    d = d[d.method == method]
    per_date = (d[d.pass_gate].groupby(["array", "date", "channel_id"],
                                       observed=True)
                  .size().rename("n_gated").reset_index())
    rows = []
    serial = {"Anterior": "1025-001501", "Posterior": "1025-001497"}
    for arr, g in per_date.groupby("array", observed=True):
        dates = d.loc[d.array == arr, "date"].unique()
        geo = ring_frame(serial[arr])
        grid = pd.MultiIndex.from_product(
            [dates, geo.channel_id], names=["date", "channel_id"]).to_frame(
            index=False)
        full = grid.merge(g, on=["date", "channel_id"], how="left").fillna(0)
        per = (full.groupby("channel_id").n_gated.mean()
                   .rename("value").reset_index())
        per["subject"], per["array"], per["serial"] = "Rocky", arr, serial[arr]
        per["n_sessions"] = len(dates)
        rows.append(per)
    return pd.concat(rows, ignore_index=True)


def array_stats(per: pd.DataFrame) -> pd.DataFrame:
    """Toroidal-shift and border-sign statistics per array."""
    rows = []
    for (sub, arr, serial), g in per.groupby(["subject", "array", "serial"],
                                             observed=True):
        geo = ring_frame(serial)
        m = geo.merge(g[["channel_id", "value"]], on="channel_id", how="left")
        grid = to_grid(m.dropna(subset=["value"]))
        obs, p = toroidal_null(grid)
        agree, dev = border_signs(grid)
        rows.append(dict(subject=sub, array=arr, serial=serial,
                         n_elec=int(m.value.notna().sum()),
                         mean_yield=float(np.nanmean(grid)),
                         contrast_pct=obs, p_shift=p, borders_agree=agree))
    return pd.DataFrame(rows)


def ring_profiles(per: pd.DataFrame) -> pd.DataFrame:
    """Mean yield per ring relative to the array mean."""
    rows = []
    for (sub, arr, serial), g in per.groupby(["subject", "array", "serial"],
                                             observed=True):
        geo = ring_frame(serial)
        m = geo.merge(g[["channel_id", "value"]], on="channel_id", how="inner")
        base = m.value.mean()
        for ring, gg in m.groupby("ring"):
            rows.append(dict(subject=sub, array=arr, ring=int(ring),
                             n=len(gg), rel=float(gg.value.mean() / base)
                             if base else np.nan))
    return pd.DataFrame(rows)


def main() -> int:
    banner("1. Yield surfaces")
    nf = nigel_fisk_yield()
    rk = rocky_yield()
    per = pd.concat([nf, rk], ignore_index=True)
    print(per.groupby(["subject", "array"], observed=True)
             .agg(n_elec=("channel_id", "nunique"),
                  sessions=("n_sessions", "max"),
                  mean_yield=("value", "mean")).round(3).to_string())

    banner("2. Border contrast, toroidal null, isotropy")
    st = array_stats(per)
    print(st.round(3).to_string(index=False))
    st.to_parquet(OUT / "yield_array_stats.parquet", index=False)

    banner("3. Ring profiles (value / array mean; ring 5 = border)")
    prof = ring_profiles(per)
    print(prof.pivot_table(index=["subject", "array"], columns="ring",
                           values="rel").round(3).to_string())
    prof.to_parquet(OUT / "yield_ring_profile.parquet", index=False)

    banner("4. Inside a bank (border - interior, gated units/electrode)")
    from scipy.stats import binomtest

    g = per.rename(columns={"value": "v"})
    geo = pd.concat([ring_frame(s) for s in g.serial.unique()],
                    ignore_index=True)
    g = g.merge(geo[["serial", "channel_id", "is_border"]],
                on=["serial", "channel_id"], how="inner")
    wb = within_bank_contrast(attach_bank(g), "v",
                              ["subject", "array", "bank"])
    base = per.groupby(["subject", "array"], observed=True).value.mean()
    wb = wb.merge(base.rename("base"), on=["subject", "array"])
    wb["delta_pct"] = 100.0 * wb.delta / wb.base
    print(wb.pivot_table(index=["subject", "array"], columns="bank",
                         values="delta_pct").round(1).to_string())
    neg = int((wb.delta_pct < 0).sum())
    print(f"\n  {neg}/{len(wb)} negative "
          f"(sign test p = {binomtest(neg, len(wb), 0.5).pvalue:.3g})")
    print("\n  per animal, mean sign:")
    print(wb.assign(sign=np.sign(wb.delta_pct))
            .groupby("subject").sign.mean().round(2).to_string())
    wb.to_parquet(OUT / "yield_within_bank.parquet", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

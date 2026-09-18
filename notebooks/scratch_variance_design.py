"""W-020 Analyses 1+2: sham-contrast resampling and variance components.

Implements the headline of docs/notes/NHP_variance_analysis_brief.md on
the per-channel-per-session max-P2P table (cohort/mmp2p_shards, 708
sessions; the brief's primary metric, exactly).

ANALYSIS 1 - sham contrasts (assumption-free). Within each month-post-
implant bin: (A) within-array half-splits of one array's active
channels; (B) between-array: the two same-implant arrays' mean
difference; (C) between-subject: subject-pooled mean differences among
subjects sharing that month bin. Efficiency = (SD_B/SD_A)^2 etc., with
array/animal-level bootstrap CIs. Variants: realistic (all active
channels) and matched-n (24 per side everywhere).

ANALYSIS 2 - nested variance components by method-of-moments on the
same table: vE (session-to-session within channel), vC~vS (between
channels within array), vD (between arrays within animal), vA (between
animals), each from the appropriate level of means; rho = (vA+vD)/tot
and the design effect 1 + m*rho/(1-rho).

DESIGN DECISIONS (argued in chat 2026-09-17, recorded here):
- No treatment residualization: on THIS cohort every treatment label is
  aliased with an array (whole-array coatings / per-array stripe
  families), so removing condition means would erase vD itself. Instead
  every between-array cell carries a contamination label, and the
  Fisk-only column (its two arrays have IDENTICAL striped treatment)
  is the clean-vD anchor. Rocky pairs (L1 vs uncoated; TNP vs TNP-L1)
  and Nigel (TNP-family vs EDCNHS-family) are labeled contaminated:
  their between-array SD is an UPPER bound on nuisance vD.
- Amplitude is analyzed on log10(uV) primarily (era/subject scale
  differences make raw-uV variance heteroscedastic); raw-uV runs as a
  sensitivity column.
- Active channels only (the metric is conditional on >=1 sorted unit);
  the Rocky manual-examination exclusions (two_array_metrics
  is_outlier) are applied and toggleable.
- month_post = floor(days since surgery / 30.44) from the registry;
  Fisk's registry lacks surgery_date -> anchored at its first session
  (flagged in output).
- "Animal" = subject (Rocky I1+I2 both belong to Rocky); "shank" =
  electrode; m = 96 (48 per condition on striped arrays).

Outputs: results/01_resampling.md + .csv, results/02_variance_components.csv
Run: uv run python notebooks/scratch_variance_design.py
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
DER = REPO / "data" / "derived"
RES = REPO / "results"
RNG = np.random.default_rng(20260917)
B_SPLITS = 2000              # half-splits per array-month cell
N_BOOT = 2000                # outer bootstrap draws for CIs
MATCHED_N = 24               # per-side channels in the matched-n variant
MIN_ACTIVE = 12              # skip cells with fewer active channels
EXCLUDE_OUTLIERS = True
DAYS_PER_MONTH = 30.44

SURGERY = {("Rocky", "I1"): "2017-08-30", ("Rocky", "I2"): "2025-03-26",
           ("Nigel", "I1"): "2023-01-18", ("Fisk", "I1"): None}
# which same-implant array pairs have identical treatment (clean vD)
CLEAN_PAIR = {("Fisk", "I1"): True, ("Nigel", "I1"): False,
              ("Rocky", "I1"): False, ("Rocky", "I2"): False}


def load_table() -> pd.DataFrame:
    """Per (subject, implant, array, month_post, stem, channel) log-amp."""
    shards = sorted((DER / "cohort" / "mmp2p_shards").glob("*.parquet"))
    t = pd.concat([pd.read_parquet(p) for p in shards], ignore_index=True)
    t = t[t.max_p2p_uv > 0].copy()
    t["date"] = pd.to_datetime(t.date)

    # implant: Rocky rows need the I1/I2 split; others are I1
    t["implant"] = "I1"
    t.loc[(t.subject == "Rocky")
          & (t.date >= "2025-03-26"), "implant"] = "I2"

    if EXCLUDE_OUTLIERS:
        tam = DER / "rocky" / "two_array_metrics.parquet"
        bad = set(pd.read_parquet(tam).query("is_outlier").stem)
        n0 = len(t)
        t = t[~t.stem.isin(bad)]
        print(f"outlier exclusion: dropped {n0 - len(t)} channel-rows "
              f"({len(bad)} flagged sessions, Rocky)")

    # month post implant (Fisk anchored at first session - registry gap)
    anchors = {}
    for (sub, imp), d in SURGERY.items():
        anchors[(sub, imp)] = (pd.Timestamp(d) if d else
                               t.loc[t.subject == sub, "date"].min())
    t["month_post"] = [
        int((r.date - anchors[(r.subject, r.implant)]).days
            // DAYS_PER_MONTH)
        for r in t.itertuples()]
    t["logamp"] = np.log10(t.max_p2p_uv)
    t["array_uid"] = t.subject + ":" + t.implant + ":" + t.array
    return t


def cell_values(t: pd.DataFrame, col: str) -> dict:
    """month -> array_uid -> per-channel session-mean values.

    Within a (array, month) cell each channel contributes its MEAN over
    the month's sessions, so a channel is one observation per cell and
    week-to-week noise (vE) does not masquerade as channel spread.
    """
    out: dict = {}
    g = (t.groupby(["month_post", "array_uid", "channel_id"],
                   observed=True)[col].mean().reset_index())
    for (m, a), gg in g.groupby(["month_post", "array_uid"],
                                observed=True):
        if len(gg) >= MIN_ACTIVE:
            out.setdefault(int(m), {})[a] = gg[col].to_numpy()
    return out


def sham_contrasts(cells: dict, matched: bool) -> pd.DataFrame:
    """One row per sham contrast with its design level."""
    rows = []
    for m, arrays in cells.items():
        # A: within-array half splits
        for a, v in arrays.items():
            n = len(v) // 2 if not matched else min(MATCHED_N, len(v) // 2)
            if n < 6:
                continue
            for _ in range(B_SPLITS // 100):
                idx = RNG.permutation(len(v))
                d = v[idx[:n]].mean() - v[idx[n:2 * n]].mean()
                rows.append(dict(design="within", month=m, unit=a, d=d))
        # B: between-array, same implant
        by_impl: dict = {}
        for a in arrays:
            sub, imp, _ = a.split(":")
            by_impl.setdefault((sub, imp), []).append(a)
        for (sub, imp), pair in by_impl.items():
            if len(pair) != 2:
                continue
            v1, v2 = arrays[pair[0]], arrays[pair[1]]
            if matched:
                v1 = RNG.choice(v1, min(MATCHED_N, len(v1)), replace=False)
                v2 = RNG.choice(v2, min(MATCHED_N, len(v2)), replace=False)
            rows.append(dict(design="between_array", month=m,
                             unit=f"{sub}:{imp}",
                             clean=CLEAN_PAIR[(sub, imp)],
                             d=v1.mean() - v2.mean()))
        # C: between-subject (pool arrays per subject in this month)
        by_sub: dict = {}
        for a, v in arrays.items():
            by_sub.setdefault(a.split(":")[0], []).append(v)
        subs = sorted(by_sub)
        for i in range(len(subs)):
            for j in range(i + 1, len(subs)):
                v1 = np.concatenate(by_sub[subs[i]])
                v2 = np.concatenate(by_sub[subs[j]])
                if matched:
                    v1 = RNG.choice(v1, min(MATCHED_N, len(v1)),
                                    replace=False)
                    v2 = RNG.choice(v2, min(MATCHED_N, len(v2)),
                                    replace=False)
                rows.append(dict(design="between_subject", month=m,
                                 unit=f"{subs[i]}|{subs[j]}",
                                 d=v1.mean() - v2.mean()))
    return pd.DataFrame(rows)


def sd_with_ci(d: pd.DataFrame, design: str, clean_only: bool = False
               ) -> tuple[float, float, float, int]:
    """SD of contrasts, bootstrap CI resampling at the unit level."""
    g = d[d.design == design]
    if clean_only and "clean" in g:
        g = g[g.get("clean") == True]  # noqa: E712
    if not len(g):
        return np.nan, np.nan, np.nan, 0
    units = g.unit.unique()
    sd = float(g.d.std(ddof=1))
    boots = []
    for _ in range(N_BOOT):
        pick = RNG.choice(units, len(units), replace=True)
        vals = pd.concat([g[g.unit == u].d for u in pick])
        if len(vals) > 3:
            boots.append(vals.std(ddof=1))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return sd, float(lo), float(hi), len(units)


def variance_components(t: pd.DataFrame, col: str) -> dict:
    """Method-of-moments nested components on channel-month means."""
    # vE: session-to-session within (array, channel, month)
    g = t.groupby(["array_uid", "channel_id", "month_post"],
                  observed=True)[col]
    ve = float(g.var(ddof=1).dropna().mean())
    # channel means within (array, month) -> vC (between-electrode)
    cm = g.mean().reset_index()
    vc_raw = (cm.groupby(["array_uid", "month_post"], observed=True)[col]
              .var(ddof=1).dropna())
    n_sess = float(g.size().mean())
    vC = float(vc_raw.mean()) - ve / n_sess
    # array means within (subject, month) where the pair exists -> vD
    am = (cm.groupby(["array_uid", "month_post"], observed=True)[col]
          .mean().reset_index())
    am[["subject", "implant", "array"]] = am.array_uid.str.split(
        ":", expand=True)
    n_ch = float(cm.groupby(["array_uid", "month_post"],
                            observed=True).size().mean())
    pair_var = (am.groupby(["subject", "implant", "month_post"],
                           observed=True)[col]
                .agg(["var", "size"]))
    pair_var = pair_var[pair_var["size"] == 2]["var"].dropna()
    vD = float(pair_var.mean()) - (vC + ve / n_sess) / n_ch
    # clean-vD variant: Fisk pairs only
    fisk = am[am.subject == "Fisk"]
    fv = (fisk.groupby("month_post", observed=True)[col]
          .agg(["var", "size"]))
    vD_clean = float(fv[fv["size"] == 2]["var"].dropna().mean()) \
        - (vC + ve / n_sess) / n_ch
    # subject means per month -> vA
    sm = (am.groupby(["subject", "month_post"], observed=True)[col]
          .mean().reset_index())
    sm_var = (sm.groupby("month_post", observed=True)[col]
              .agg(["var", "size"]))
    vA = float(sm_var[sm_var["size"] >= 2]["var"].dropna().mean()) \
        - vD / 2 - (vC + ve / n_sess) / (2 * n_ch)
    vA, vD, vD_clean, vC = (max(x, 0.0) for x in (vA, vD, vD_clean, vC))
    tot = vA + vD + vC + ve
    rho = (vA + vD) / tot
    rho_clean = (vA + vD_clean) / (vA + vD_clean + vC + ve)
    return dict(metric=col, vA=vA, vD=vD, vD_clean_fisk=vD_clean, vS=vC,
                vE=ve, rho=rho, rho_clean=rho_clean,
                eff_m48=1 + 48 * rho / (1 - rho),
                eff_m96=1 + 96 * rho / (1 - rho),
                eff_m48_clean=1 + 48 * rho_clean / (1 - rho_clean),
                n_sess_mean=n_sess, n_ch_mean=n_ch)


def main() -> int:
    RES.mkdir(exist_ok=True)
    t = load_table()
    print(f"{len(t)} channel-session rows, "
          f"{t.array_uid.nunique()} arrays, "
          f"{t.subject.nunique()} subjects, months 0-{t.month_post.max()}")

    lines = ["# Analysis 1 - sham-contrast resampling (mmp2p, log10 uV)",
             "", f"seed 20260917; B={B_SPLITS // 100}/cell; "
             f"outliers excluded={EXCLUDE_OUTLIERS}; "
             "Fisk months anchored at first session (registry gap)", ""]
    recs = []
    for col in ("logamp", "max_p2p_uv"):
        cells = cell_values(t, col)
        for matched in (False, True):
            d = sham_contrasts(cells, matched)
            rows = {}
            for des, clean in (("within", False), ("between_array", False),
                               ("between_array", True),
                               ("between_subject", False)):
                key = des + ("_cleanpairs" if clean else "")
                rows[key] = sd_with_ci(d, des, clean)
            sw = rows["within"][0]
            for key, (sd, lo, hi, n) in rows.items():
                eff = (sd / sw) ** 2 if sw else np.nan
                recs.append(dict(metric=col,
                                 variant="matched" if matched else
                                 "realistic", contrast=key, sd=sd,
                                 ci_lo=lo, ci_hi=hi, n_units=n,
                                 efficiency_vs_within=eff))
                lines.append(
                    f"- {col} / "
                    f"{'matched' if matched else 'realistic'} / "
                    f"{key}: SD={sd:.4f} [{lo:.4f},{hi:.4f}] "
                    f"n_units={n}  eff x{eff:.2f}")
            lines.append("")
    rdf = pd.DataFrame(recs)
    rdf.to_csv(RES / "01_resampling.csv", index=False)
    (RES / "01_resampling.md").write_text("\n".join(lines),
                                          encoding="utf-8")
    print("\n".join(lines))

    vcs = pd.DataFrame([variance_components(t, c)
                        for c in ("logamp", "max_p2p_uv")])
    vcs.to_csv(RES / "02_variance_components.csv", index=False)
    print(vcs.round(4).to_string(index=False))
    print(f"\nwrote {RES}/01_resampling.* and 02_variance_components.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

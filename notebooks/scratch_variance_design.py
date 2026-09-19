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

STEP 2 (W-020 order item 2, added 2026-09-17): the same two analyses
repeated for two more metrics.
- yield: per-channel ACTIVITY indicator (>=1 sorted unit that session)
  over the full 708-session universe (cohort/mean_max_p2p.parquet gives
  the attempted sessions; the shards give the active channels; the
  denominator is all 96 Utah sites). Analyzed as a raw proportion, no
  log. This is the brief's per-channel yield at the channel grain.
- crossing_rate: sorting-free clean crossing rate from
  rocky/events_electrode.parquet - Rocky I1 ONLY (the free layer exists
  per-channel only there), so between-subject contrasts and vA are not
  estimable; the within vs between-array comparison still is, and the
  Rocky pair is treatment-contaminated (L1 vs uncoated). log10 Hz.

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


def outlier_stems() -> set:
    """The owner's exclusion set: the OUTLIERS master dict UNION the
    metric table's is_outlier flags.

    The dict is the master (owner rulings live there); the parquet only
    carries flags for stems inside the 332-session two-array universe,
    which misses rulings on stems that exist only in the wider
    405-session NEV corpus (e.g. the Digital 12-06-2018 3.9 mV day,
    ruled excluded 2026-09-19).
    """
    from scratch_two_array_metrics import OUTLIERS
    tam = DER / "rocky" / "two_array_metrics.parquet"
    bad = set(pd.read_parquet(tam).query("is_outlier").stem)
    return bad | set(OUTLIERS)


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
        bad = outlier_stems()
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


def load_yield_table() -> pd.DataFrame:
    """Per (subject, implant, array, month_post, stem, channel) 0/1 active.

    Universe = the 708 attempted sessions x all 96 Utah sites; a channel
    is active when the session's shard carries it with >=1 sorted unit.
    """
    uni = pd.read_parquet(DER / "cohort" / "mean_max_p2p.parquet")
    shards = sorted((DER / "cohort" / "mmp2p_shards").glob("*.parquet"))
    # zero-unit sessions have shards without a channel_id column; they
    # contribute no active pairs but stay in the session universe
    parts = []
    for p in shards:
        s = pd.read_parquet(p)
        if "channel_id" in s.columns and len(s):
            parts.append(s[["stem", "channel_id"]])
    act = pd.concat(parts, ignore_index=True)
    active: set = set(zip(act.stem, act.channel_id))

    # cross-join sessions x channels 1..96 -> binary indicator
    uni = uni[["subject", "stem", "array", "date"]].copy()
    uni["date"] = pd.to_datetime(uni.date)
    t = uni.merge(pd.DataFrame({"channel_id": np.arange(1, 97)}),
                  how="cross")
    t["active"] = [float((s, c) in active)
                   for s, c in zip(t.stem, t.channel_id)]

    t["implant"] = "I1"
    t.loc[(t.subject == "Rocky")
          & (t.date >= "2025-03-26"), "implant"] = "I2"
    if EXCLUDE_OUTLIERS:
        t = t[~t.stem.isin(outlier_stems())]
    anchors = {}
    for (sub, imp), d in SURGERY.items():
        anchors[(sub, imp)] = (pd.Timestamp(d) if d else
                               t.loc[t.subject == sub, "date"].min())
    t["month_post"] = [
        int((r.date - anchors[(r.subject, r.implant)]).days
            // DAYS_PER_MONTH)
        for r in t.itertuples()]
    t["array_uid"] = t.subject + ":" + t.implant + ":" + t.array
    return t


def load_crossing_table() -> pd.DataFrame:
    """Per (channel, stem) sorting-free clean crossing rate - Rocky I1.

    The free layer's per-channel table exists only for Rocky's snippet
    corpus, so this metric has one subject: vA and between-subject
    contrasts are not estimable and are reported as NaN.
    """
    e = pd.read_parquet(DER / "rocky" / "events_electrode.parquet",
                        columns=["date", "array", "stem", "channel_id",
                                 "crossing_rate_clean_hz"])
    t = e[e.crossing_rate_clean_hz > 0].copy()   # log needs positives
    t["date"] = pd.to_datetime(t.date)
    t["subject"], t["implant"] = "Rocky", "I1"
    if EXCLUDE_OUTLIERS:
        t = t[~t.stem.isin(outlier_stems())]
    anchor = pd.Timestamp(SURGERY[("Rocky", "I1")])
    t["month_post"] = ((t.date - anchor).dt.days
                       // DAYS_PER_MONTH).astype(int)
    t["lograte"] = np.log10(t.crossing_rate_clean_hz)
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
    if not boots:
        return sd, np.nan, np.nan, len(units)
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
    vD = (float(pair_var.mean()) - (vC + ve / n_sess) / n_ch
          if len(pair_var) else np.nan)
    # clean-vD variant: Fisk pairs only (NaN when Fisk is absent)
    fisk = am[am.subject == "Fisk"]
    fv = (fisk.groupby("month_post", observed=True)[col]
          .agg(["var", "size"]))
    fv = fv[fv["size"] == 2]["var"].dropna()
    vD_clean = (float(fv.mean()) - (vC + ve / n_sess) / n_ch
                if len(fv) else np.nan)
    # subject means per month -> vA (NaN on single-subject metrics)
    sm = (am.groupby(["subject", "month_post"], observed=True)[col]
          .mean().reset_index())
    sm_var = (sm.groupby("month_post", observed=True)[col]
              .agg(["var", "size"]))
    sm_var = sm_var[sm_var["size"] >= 2]["var"].dropna()
    vA = (float(sm_var.mean()) - np.nan_to_num(vD) / 2
          - (vC + ve / n_sess) / (2 * n_ch)
          if len(sm_var) else np.nan)
    # clip negatives to zero, keep NaN as not-estimable
    vA, vD, vD_clean, vC = (max(x, 0.0) if np.isfinite(x) else x
                            for x in (vA, vD, vD_clean, vC))
    tot = np.nansum([vA, vD, vC, ve])
    rho = (np.nansum([vA, vD]) / tot
           if np.isfinite(vA) or np.isfinite(vD) else np.nan)
    rho_clean = (np.nansum([vA, vD_clean])
                 / np.nansum([vA, vD_clean, vC, ve])
                 if np.isfinite(vD_clean) else np.nan)
    # device-only ratio: the within-animal design question, defined even
    # when vA is not estimable (single-subject metrics)
    rho_device = (vD / (vD + vC + ve) if np.isfinite(vD) else np.nan)
    return dict(metric=col, vA=vA, vD=vD, vD_clean_fisk=vD_clean, vS=vC,
                vE=ve, rho=rho, rho_clean=rho_clean,
                rho_device=rho_device,
                eff_m48=1 + 48 * rho / (1 - rho),
                eff_m96=1 + 96 * rho / (1 - rho),
                eff_m48_clean=1 + 48 * rho_clean / (1 - rho_clean),
                n_sess_mean=n_sess, n_ch_mean=n_ch)


def rho_over_time(tables: dict) -> None:
    """Analysis 3: design SDs and rho in sliding implant-age windows.

    6-month windows stepping by 3. Between-subject exists only where
    subjects overlap in month_post (early windows); late windows are
    Rocky I1 alone, so the between-array line is the survivor there.
    Outputs results/03_rho_over_time.csv + figures/cohort figure.
    """
    win, step = 6, 3               # window width / stride in months
    rows = []
    for label, col in (("mmp2p", "logamp"), ("yield", "active")):
        t = tables[label]
        m_max = int(t.month_post.max())
        for m0 in range(0, m_max - win + 2, step):
            tw = t[(t.month_post >= m0) & (t.month_post < m0 + win)]
            if not len(tw):
                continue
            cells = cell_values(tw, col)
            if not cells:
                continue
            d = sham_contrasts(cells, matched=False)
            base = dict(metric=f"{label}:{col}", win_start=m0,
                        win_end=m0 + win,
                        n_arrays=tw.array_uid.nunique(),
                        n_subjects=tw.subject.nunique())
            sw = np.nan
            for des, clean in (("within", False),
                               ("between_array", False),
                               ("between_array", True),
                               ("between_subject", False)):
                key = des + ("_cleanpairs" if clean else "")
                sd, lo, hi, n = sd_with_ci(d, des, clean)
                if key == "within":
                    sw = sd
                rows.append(dict(base, contrast=key, sd=sd, ci_lo=lo,
                                 ci_hi=hi, n_units=n,
                                 efficiency_vs_within=(sd / sw) ** 2
                                 if sw and np.isfinite(sd) else np.nan))
            # MoM rho on the window (amplitude only; yield's MoM does
            # not transfer cleanly - see R-021)
            if col == "logamp":
                c = variance_components(tw, col)
                rows.append(dict(base, contrast="mom_rho", sd=np.nan,
                                 ci_lo=np.nan, ci_hi=np.nan,
                                 n_units=np.nan,
                                 efficiency_vs_within=c["rho"]))
    r = pd.DataFrame(rows)
    r.to_csv(RES / "03_rho_over_time.csv", index=False)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, (label, col, name) in zip(
            axes, (("mmp2p", "logamp", "log10 amplitude"),
                   ("yield", "active", "channel yield"))):
        g = r[r.metric == f"{label}:{col}"]
        mid = (g.win_start + g.win_end) / 2
        for key, fmt, lab in (("within", "o-", "within-array"),
                              ("between_array", "s-", "between-array"),
                              ("between_subject", "^-",
                               "between-subject")):
            gg = g[g.contrast == key].dropna(subset=["sd"])
            ax.plot((gg.win_start + gg.win_end) / 2, gg.sd, fmt,
                    label=lab, ms=4)
        ax.set_xlabel("months post implant (6-mo window center)")
        ax.set_ylabel(f"sham-contrast SD ({name})")
        ax.set_title(name)
        ax.legend(fontsize=8)
        if label == "mmp2p":
            ax2 = ax.twinx()
            gg = g[g.contrast == "mom_rho"]
            ax2.plot((gg.win_start + gg.win_end) / 2,
                     gg.efficiency_vs_within, "k--", alpha=0.5,
                     label="MoM rho")
            ax2.set_ylabel("rho (MoM)")
            ax2.legend(fontsize=8, loc="upper right")
        _ = mid  # noqa: F841 - kept for debugger inspection
    fig.suptitle("W-020 Analysis 3: design SDs vs implant age "
                 "(late windows are Rocky I1 alone)")
    fig.tight_layout()
    out = REPO / "figures" / "cohort" / "variance_rho_over_time.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    print(f"wrote {RES}/03_rho_over_time.csv and {out}")


def mde_table(rdf: pd.DataFrame) -> None:
    """Analysis 4: minimal detectable effect in natural units.

    The sham-contrast SD IS the null SD of one array-month contrast at
    that design level, so MDE(k) = 2.80 * SD / sqrt(k) at alpha=.05,
    power .80, where k = replicated contrasts (array-month cells for
    within/between-array; animals per arm for between-subject, since
    the sham was a 1-vs-1 subject contrast). Log-scale MDEs are also
    given as fold changes (10**MDE).
    """
    z = 2.80                      # z_{.975} + z_{.80}
    rows = []
    for _, r in rdf[rdf.variant == "realistic"].iterrows():
        if not np.isfinite(r.sd):
            continue
        for k in (1, 2, 4, 8):
            mde = z * r.sd / np.sqrt(k)
            row = dict(metric=r.metric, contrast=r.contrast, k=k,
                       mde=mde)
            if r.metric in ("mmp2p:logamp", "crossing_rate:lograte"):
                row["fold_change"] = 10 ** mde
                row["pct_change"] = (10 ** mde - 1) * 100
            elif r.metric == "yield:active":
                row["pct_points"] = mde * 100
            rows.append(row)
    m = pd.DataFrame(rows)
    m.to_csv(RES / "04_mde.csv", index=False)
    show = m[(m.metric.isin(["mmp2p:logamp", "yield:active"]))
             & (m.contrast.isin(["within", "between_subject"]))]
    print("\nMDE (alpha=.05, power=.80):")
    print(show.round(3).to_string(index=False))
    print(f"wrote {RES}/04_mde.csv")


def main() -> int:
    RES.mkdir(exist_ok=True)
    # metric configs: (label, loader, analysis columns)
    configs = [
        ("mmp2p", load_table, ("logamp", "max_p2p_uv")),
        ("yield", load_yield_table, ("active",)),
        ("crossing_rate", load_crossing_table, ("lograte",)),
    ]

    lines = ["# Analysis 1 - sham-contrast resampling",
             "", f"seed 20260917; B={B_SPLITS // 100}/cell; "
             f"outliers excluded={EXCLUDE_OUTLIERS}; "
             "Fisk months anchored at first session (registry gap).",
             "mmp2p: log10 uV primary, raw uV sensitivity. yield: raw",
             "0/1 activity over all 96 sites, 708-session universe.",
             "crossing_rate: log10 clean Hz, Rocky I1 only (no",
             "between-subject level; the pair is coating-contaminated).",
             ""]
    recs, comps = [], []
    tables: dict = {}                # label -> loaded table, for A3
    for label, loader, cols in configs:
        t = loader()
        tables[label] = t
        print(f"[{label}] {len(t)} channel-session rows, "
              f"{t.array_uid.nunique()} arrays, "
              f"{t.subject.nunique()} subjects, "
              f"months 0-{t.month_post.max()}")
        for col in cols:
            cells = cell_values(t, col)
            for matched in (False, True):
                d = sham_contrasts(cells, matched)
                rows = {}
                for des, clean in (("within", False),
                                   ("between_array", False),
                                   ("between_array", True),
                                   ("between_subject", False)):
                    key = des + ("_cleanpairs" if clean else "")
                    rows[key] = sd_with_ci(d, des, clean)
                sw = rows["within"][0]
                for key, (sd, lo, hi, n) in rows.items():
                    eff = (sd / sw) ** 2 if sw else np.nan
                    recs.append(dict(metric=f"{label}:{col}",
                                     variant="matched" if matched else
                                     "realistic", contrast=key, sd=sd,
                                     ci_lo=lo, ci_hi=hi, n_units=n,
                                     efficiency_vs_within=eff))
                    lines.append(
                        f"- {label}:{col} / "
                        f"{'matched' if matched else 'realistic'} / "
                        f"{key}: SD={sd:.4f} [{lo:.4f},{hi:.4f}] "
                        f"n_units={n}  eff x{eff:.2f}")
                lines.append("")
            c = variance_components(t, col)
            c["metric"] = f"{label}:{col}"
            comps.append(c)

    rdf = pd.DataFrame(recs)
    rdf.to_csv(RES / "01_resampling.csv", index=False)
    (RES / "01_resampling.md").write_text("\n".join(lines),
                                          encoding="utf-8")
    print("\n".join(lines))

    vcs = pd.DataFrame(comps)
    vcs.to_csv(RES / "02_variance_components.csv", index=False)
    print(vcs.round(4).to_string(index=False))
    print(f"\nwrote {RES}/01_resampling.* and 02_variance_components.csv")
    rho_over_time(tables)
    mde_table(rdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

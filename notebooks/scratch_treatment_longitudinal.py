"""Coated against uncoated, paired within animal — the study's actual question.

Every longitudinal result in this project so far has been reported per *array*,
with the surface treatment nowhere in the pipeline. `cohort_definition.md`
established it, so the comparison the cohort was built for can finally run.

**The design is a within-animal pair.** Each generation-1 animal carries one
L1-coated array and one uncoated control, implanted in the same surgery on the
same day, recorded through the same NSP on the same sessions. That holds animal,
surgery date, amplifier and session fixed, which is far stronger than any
between-animal comparison.

**Scope is deliberately narrow.** The treatment label has to reach a session
row, and it only does so unambiguously for four arrays:

| animal | resolvable? | why |
|---|---|---|
| Rocky I1 | **yes** | cohort labels are `Anterior`/`Posterior`, matching the registry |
| Oops | **yes** | `Array1`/`Array2` resolve to `eNe1`/`eNe2`, fixed by explant dates |
| Picasso | **via the legacy sorts** | the modern table has no unit counts for it; `monkey_units_compiled.mat` labels coating per array directly, so no store inference is needed |
| Luigi | **no** | only one array survived past 2013-03, and it entered the legacy compile pre-binned with no session filenames |
| Nigel, Fisk | n/a | generation 2, striped *within* an array — no uncoated array exists |
| Rocky I2 | separate | generation 3, TNP vs TNP-L1, only 10 sessions per array |

So the analysis rests on **Rocky I1** from the modern pipeline (both arrays
alive 2017-2023, the best case in the corpus) and on **Oops and Picasso** from
the legacy sorts.

**The three animals arrange treatment differently**, and that turns out to
matter more than the treatment: Oops and Picasso put the coating under opposite
pedestals, Rocky puts it on the opposite cortex from both. Together they
deconfound treatment, pedestal and cortical site -- which is what W5 tests, and
it is the result that matters here. See docs/notes/treatment_effect.md.

    W1_paired      yield per treatment over each implant's life
    W2_ratio       the within-session coated/uncoated ratio
    W3_tenmonth    the legacy claim, re-tested on its own window
    W4_metrics     noise, amplitude, SNR and pass fraction by treatment
    W5_three_axis  coating, pedestal or cortex? only one agrees across animals

Run from repo root:

    uv run python notebooks/scratch_treatment_longitudinal.py

See:
- docs/notes/cohort_definition.md
- docs/notes/treatment_effect.md
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))

COHORT = REPO / "data" / "derived" / "cohort" / "cohort_sessions.parquet"
SUBJECTS = REPO / "configs" / "subjects"
FIG = REPO / "figures" / "treatment"

# Cohort array label -> (implant, registry array name). Only the entries this
# project can defend. Picasso and Luigi are deliberately absent: see the module
# docstring and cohort_definition.md.
RESOLVE = {
    ("Rocky", "Anterior"): ("I1", "Anterior"),
    ("Rocky", "Posterior"): ("I1", "Posterior"),
    # Oops: Array1 is eNe1, which survives to 2017-02 with the anterior
    # pedestal; Array2 is eNe2, gone after 2016-12 with the posterior.
    ("Oops", "Array1"): ("I1", "Anterior"),
    ("Oops", "Array2"): ("I1", "Posterior"),
}
# Rocky reuses Anterior/Posterior across two implants with different arrays and
# coatings; everything before this date is implant 1.
ROCKY_I2_FROM = pd.Timestamp("2025-04-04")

TREAT_COLOR = {"L1": "#d62728", "uncoated": "#1f77b4"}
METRICS = ["units_per_electrode", "pass_fraction", "noise_med", "amp_med",
           "snr_med", "elec_coverage"]


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
def registry() -> pd.DataFrame:
    """One row per (subject, implant, array): serial, treatment, surgery date."""
    rows = []
    for f in sorted(SUBJECTS.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for im in d.get("implants", []):
            for name, info in (im.get("array_detail") or {}).items():
                rows.append(dict(
                    subject=d["subject"], implant=im.get("implant"),
                    reg_array=name, serial=info["serial"],
                    treatment=info["treatment"],
                    pedestal=info.get("pedestal"), cortex=info.get("cortex"),
                    surgery=im.get("surgery_date")))
    r = pd.DataFrame(rows)
    r["surgery"] = pd.to_datetime(r.surgery, errors="coerce")
    return r


def load() -> pd.DataFrame:
    """Cohort sessions with treatment attached, for the resolvable arrays only.

    `days` is measured from the surgery date, not from the first recording, so
    two animals implanted years apart are on a comparable axis.
    """
    c = pd.read_parquet(COHORT)
    c["date"] = pd.to_datetime(c.date)
    reg = registry()

    keep = []
    for (subj, arr), g in c.groupby(["subject", "array"]):
        hit = RESOLVE.get((subj, arr))
        if hit is None:
            continue
        implant, reg_array = hit
        g = g.copy()
        # Rocky's labels are reused across implants; keep implant 1 only
        if subj == "Rocky":
            g = g[g.date < ROCKY_I2_FROM]
        g["implant"] = implant
        g["reg_array"] = reg_array
        keep.append(g)
    if not keep:
        return pd.DataFrame()
    d = pd.concat(keep, ignore_index=True).merge(
        reg, on=["subject", "implant", "reg_array"], how="left")
    d["days"] = (d.date - d.surgery).dt.days
    d["months"] = d.days / 30.44
    return d.dropna(subset=["treatment", "days"])


# %%
def fig_paired(d: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Yield over each implant's life, one line per treatment.

    The two arrays share every session, so any difference between the lines is
    the treatment or the cortical site -- not the day, the animal or the rig.
    """
    animals = sorted(d.subject.unique())
    fig, axes = plt.subplots(1, len(animals), figsize=(6.2 * len(animals), 4.4),
                             squeeze=False)
    for ax, subj in zip(axes[0], animals, strict=True):
        g = d[d.subject == subj]
        for treat, gg in g.groupby("treatment"):
            gg = gg.sort_values("months")
            ax.plot(gg.months, gg.units_per_electrode, "o", ms=4, alpha=0.55,
                    color=TREAT_COLOR.get(treat, "0.4"), label=treat)
            # rolling median, so the eye follows the level not the scatter
            if len(gg) >= 7:
                rm = gg.set_index("months").units_per_electrode.rolling(
                    7, center=True, min_periods=3).median()
                ax.plot(rm.index, rm.to_numpy(), lw=2.2,
                        color=TREAT_COLOR.get(treat, "0.4"))
        ax.set_xlabel("months after implant")
        ax.set_ylabel("units per electrode")
        ax.set_title(f"{subj}  ({g.date.min():%Y-%m} to {g.date.max():%Y-%m})",
                     fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.25)
    fig.suptitle("L1-coated against uncoated, paired within animal",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)

    return d.groupby(["subject", "treatment"]).agg(
        sessions=("date", "size"), first=("date", "min"), last=("date", "max"),
        months=("months", "max"),
        upe=("units_per_electrode", "median"),
        pass_frac=("pass_fraction", "median"),
        noise=("noise_med", "median")).round(3).reset_index()


# %%
def paired_ratio(d: pd.DataFrame) -> pd.DataFrame:
    """Coated / uncoated on the *same session*, which is the honest statistic.

    Pairing inside the session holds the day, the animal and the amplifier
    fixed, exactly as the aggregation rule in CLAUDE.md requires. Sessions
    where only one array recorded are dropped rather than compared against a
    different day.
    """
    piv = d.pivot_table(index=["subject", "date", "months"],
                        columns="treatment", values=METRICS, aggfunc="first")
    out = []
    for m in METRICS:
        if (m, "L1") not in piv or (m, "uncoated") not in piv:
            continue
        sub = piv[[(m, "L1"), (m, "uncoated")]].dropna()
        sub.columns = ["L1", "uncoated"]
        sub = sub.reset_index()
        sub["metric"] = m
        sub["ratio"] = sub.L1 / sub.uncoated.replace(0, np.nan)
        out.append(sub)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def fig_ratio(r: pd.DataFrame, out: Path) -> pd.DataFrame:
    """The paired ratio over time, and its distribution."""
    from scipy.stats import wilcoxon

    y = r[r.metric == "units_per_electrode"].dropna(subset=["ratio"])
    animals = sorted(y.subject.unique())
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))

    ax = axes[0]
    for subj in animals:
        g = y[y.subject == subj].sort_values("months")
        ax.plot(g.months, g.ratio, "o", ms=4, alpha=0.6, label=subj)
        if len(g) >= 7:
            rm = g.set_index("months").ratio.rolling(
                7, center=True, min_periods=3).median()
            ax.plot(rm.index, rm.to_numpy(), lw=2.2)
    ax.axhline(1.0, color="k", ls="--", lw=1.2)
    ax.set_yscale("log")
    ax.set_xlabel("months after implant")
    ax.set_ylabel("coated / uncoated, same session")
    ax.set_title("above 1 favours the coating", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    ax = axes[1]
    rows = []
    for i, subj in enumerate(animals, start=1):
        v = y[y.subject == subj].ratio.dropna()
        v = v[np.isfinite(v)]
        if not len(v):
            continue
        rng = np.random.default_rng(5)
        ax.scatter(rng.normal(i, 0.06, len(v)), v, s=16, alpha=0.5)
        ax.plot([i - 0.28, i + 0.28], [v.median()] * 2, color="k", lw=2)
        g = y[y.subject == subj].dropna(subset=["L1", "uncoated"])
        p = wilcoxon(g.L1, g.uncoated)[1] if len(g) >= 6 else np.nan
        ax.text(i + 0.32, v.median(), f"{v.median():.2f}x", fontsize=9,
                va="center")
        rows.append(dict(subject=subj, n=len(g), ratio=float(v.median()),
                         L1=float(g.L1.median()),
                         uncoated=float(g.uncoated.median()), p=p))
    ax.axhline(1.0, color="k", ls="--", lw=1.2)
    ax.set_yscale("log")
    ax.set_xticks(range(1, len(animals) + 1))
    ax.set_xticklabels(animals, fontsize=9)
    ax.set_ylabel("coated / uncoated, same session")
    ax.set_title("paired within session; dashed line = no effect", fontsize=10)
    ax.grid(alpha=0.25, axis="y")

    fig.suptitle("The within-session treatment ratio", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return pd.DataFrame(rows)


# %%
def fig_tenmonth(d: pd.DataFrame, r: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Re-test the legacy claim on the window it was made in.

    The U01 aims state: *"L1 coating showed significantly improved single unit
    recording yield of a Blackrock array in primate motor cortex over the
    course of 10 months."* That is a testable claim with a stated window, and
    this corpus is larger than the one it was made on.
    """
    from scipy.stats import wilcoxon

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))
    y = r[r.metric == "units_per_electrode"].dropna(subset=["L1", "uncoated"])

    ax = axes[0]
    rows = []
    for label, lo, hi in (("0-10 months", 0, 10), ("10+ months", 10, 1e6)):
        w = y[(y.months >= lo) & (y.months < hi)]
        for subj, g in w.groupby("subject"):
            if len(g) < 6:
                continue
            p = wilcoxon(g.L1, g.uncoated)[1]
            rows.append(dict(window=label, subject=subj, n=len(g),
                             L1=g.L1.median(), uncoated=g.uncoated.median(),
                             ratio=(g.L1 / g.uncoated.replace(0, np.nan)).median(),
                             p=p))
    t = pd.DataFrame(rows)
    if len(t):
        idx = np.arange(len(t))
        ax.bar(idx, t.ratio, color=["#d62728" if w.startswith("0-10") else "#7f7f7f"
                                    for w in t.window])
        ax.axhline(1.0, color="k", ls="--", lw=1.2)
        ax.set_xticks(idx)
        ax.set_xticklabels([f"{r.subject}\n{r.window}\nn={r.n}"
                            for r in t.itertuples()], fontsize=8)
        ax.set_ylabel("coated / uncoated")
        ax.set_title("the claim's own window, and after it", fontsize=10)
        ax.grid(alpha=0.25, axis="y")

    ax = axes[1]
    for subj, g in y.groupby("subject"):
        g = g.sort_values("months")
        ax.plot(g.months, np.log2(g.ratio.replace(0, np.nan)), "o", ms=4,
                alpha=0.55, label=subj)
    ax.axhline(0, color="k", ls="--", lw=1.2)
    ax.axvline(10, color="#d62728", ls=":", lw=1.6)
    ax.text(10.3, ax.get_ylim()[1] * 0.85, "10 months", fontsize=8,
            color="#d62728")
    ax.set_xlabel("months after implant")
    ax.set_ylabel("log2(coated / uncoated)")
    ax.set_title("does any advantage appear, or fade?", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    fig.suptitle("Re-testing the published L1 yield claim", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return t


# %%
def fig_metrics(r: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Every metric, paired within session, so one number cannot carry it."""
    from scipy.stats import wilcoxon

    present = [m for m in METRICS if m in set(r.metric)]
    fig, axes = plt.subplots(1, len(present), figsize=(2.9 * len(present), 4.2),
                             squeeze=False)
    rows = []
    for ax, m in zip(axes[0], present, strict=True):
        g = r[r.metric == m].dropna(subset=["L1", "uncoated"])
        subs = sorted(g.subject.unique())
        for i, subj in enumerate(subs, start=1):
            s = g[g.subject == subj]
            v = (s.L1 / s.uncoated.replace(0, np.nan)).replace(
                [np.inf, -np.inf], np.nan).dropna()
            if not len(v):
                continue
            rng = np.random.default_rng(9)
            ax.scatter(rng.normal(i, 0.06, len(v)), v, s=12, alpha=0.45)
            ax.plot([i - 0.3, i + 0.3], [v.median()] * 2, color="k", lw=2)
            p = wilcoxon(s.L1, s.uncoated)[1] if len(s) >= 6 else np.nan
            rows.append(dict(metric=m, subject=subj, n=len(s),
                             ratio=float(v.median()), p=p))
        ax.axhline(1.0, color="k", ls="--", lw=1)
        ax.set_yscale("log")
        ax.set_xticks(range(1, len(subs) + 1))
        ax.set_xticklabels(subs, fontsize=8, rotation=20, ha="right")
        ax.set_title(m.replace("_", " "), fontsize=9)
        ax.grid(alpha=0.25, axis="y")
    axes[0][0].set_ylabel("coated / uncoated, same session")
    fig.suptitle("Treatment ratio across every cohort metric", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return pd.DataFrame(rows)



# %%
# --- the legacy sorts, which are the only paired unit counts for Oops/Picasso
LEGACY_MAT = Path(r"D:\Claude Code\Monkey Data\Legacy\L1MonkeyData\ephys"
                  r"\monkey_units_compiled.mat")
LEGACY_OUT = REPO / "data" / "derived" / "cohort" / "legacy_sorts_paired.parquet"

# `loc` A/B are the pedestals -- seven sources agree, see cohort_definition.md.
PEDESTAL = {"A": "anterior", "B": "posterior"}
CORTEX = {("Oops", "A"): "lateral", ("Oops", "B"): "medial",
          ("Picasso", "A"): "medial", ("Picasso", "B"): "lateral"}


def legacy_sorts() -> pd.DataFrame:
    """Per-session unit counts per array from `monkey_units_compiled.mat`.

    The modern cohort table has almost no unit counts for Oops and Picasso --
    their sorts are legacy OpenSorter output that never carried yield into the
    pipeline (5 and 1 non-null rows of 61 and 84). The legacy `.mat` does, and
    it labels the **coating per array** directly, so no store-to-array
    inference is needed for this arm at all.
    """
    import re

    import scipy.io as sio

    if not LEGACY_MAT.exists():
        return pd.DataFrame()
    u = sio.loadmat(LEGACY_MAT, squeeze_me=True,
                    struct_as_record=False)["unitsort"]

    def dates_of(fnames) -> pd.DatetimeIndex:
        out = []
        for x in fnames:
            m = re.search(r"(20\d\d)[_.](\d{1,2})[_.](\d{1,3})", str(x))
            if m:
                y, mo, dd = m.groups()
                dd = dd[:2] if len(dd) == 3 else dd      # a '_010' typo
                try:
                    out.append(pd.Timestamp(int(y), int(mo), int(dd)))
                    continue
                except ValueError:
                    pass
            out.append(pd.NaT)
        return pd.DatetimeIndex(out)

    rows = []
    for animal in u._fieldnames:
        a = getattr(u, animal)
        for loc in a._fieldnames:
            st = getattr(a, loc)
            us = st.unitsum
            fn = [str(x) for x in np.atleast_1d(getattr(st, "fnames", []))]
            if not fn:
                continue                      # Luigi entered pre-binned
            d = dates_of(fn)
            # Nunit is (2, n): row 0 is per-electrode counts, row 1 the total
            nu = np.atleast_2d(us.Nunit)
            units = (np.asarray([int(x) for x in nu[1]])
                     if nu.shape[0] > 1 else np.full(len(d), np.nan))
            yld = np.asarray(np.atleast_1d(getattr(us, "yield")),
                             dtype=float).ravel()
            ms = np.asarray(np.atleast_1d(us.maxsigM), dtype=float).ravel()
            for i, dd in enumerate(d):
                rows.append(dict(
                    animal=animal, loc=loc, coating=str(st.coating), date=dd,
                    pedestal=PEDESTAL.get(loc),
                    cortex=CORTEX.get((animal, loc)),
                    units=units[i] if i < len(units) else np.nan,
                    yield_pct=yld[i] if i < yld.size else np.nan,
                    maxsig=ms[i] if i < ms.size else np.nan))
    return pd.DataFrame(rows).dropna(subset=["date"])


def three_axis(df: pd.DataFrame, modern: pd.DataFrame) -> pd.DataFrame:
    """The same paired data, contrasted three ways.

    Oops and Picasso have **opposite** coating-to-pedestal assignments, which
    is what makes this possible: a design that deconfounds treatment from
    position. If the effect is the coating, `coated/uncoated` should agree
    between them. If it is the position, `anterior/posterior` should.
    """
    from scipy.stats import wilcoxon

    rows = []
    for animal, g in df.groupby("animal"):
        for met in ("units", "yield_pct"):
            for axis, hi, lo in (("coating", "coated", "uncoated"),
                                 ("pedestal", "anterior", "posterior"),
                                 ("cortex", "medial", "lateral")):
                piv = g.pivot_table(index="date", columns=axis,
                                    values=met).dropna()
                if len(piv) < 6 or hi not in piv or lo not in piv:
                    continue
                ratio = (piv[hi] / piv[lo].replace(0, np.nan)).replace(
                    [np.inf, -np.inf], np.nan).dropna()
                rows.append(dict(animal=animal, source="legacy sorts",
                                 metric=met, axis=axis,
                                 contrast=f"{hi}/{lo}", n=len(piv),
                                 ratio=float(ratio.median()),
                                 p=float(wilcoxon(piv[hi], piv[lo])[1])))

    # Rocky comes from the modern pipeline, so it is kept as a separate source
    if len(modern):
        rk = modern[modern.subject == "Rocky"].copy()
        rk["pedestal"] = rk.reg_array.str.lower()
        rk["cortex"] = rk.cortex
        for met, col in (("units", "units_per_electrode"),
                         ("yield_pct", "elec_coverage")):
            for axis, hi, lo in (("treatment", "L1", "uncoated"),
                                 ("pedestal", "anterior", "posterior"),
                                 ("cortex", "medial", "lateral")):
                piv = rk.pivot_table(index="date", columns=axis,
                                     values=col).dropna()
                if len(piv) < 6 or hi not in piv or lo not in piv:
                    continue
                ratio = (piv[hi] / piv[lo].replace(0, np.nan)).replace(
                    [np.inf, -np.inf], np.nan).dropna()
                lbl = "coated/uncoated" if axis == "treatment" else f"{hi}/{lo}"
                rows.append(dict(animal="Rocky", source="modern pipeline",
                                 metric=met, axis=axis, contrast=lbl,
                                 n=len(piv), ratio=float(ratio.median()),
                                 p=float(wilcoxon(piv[hi], piv[lo])[1])))
    return pd.DataFrame(rows)


def fig_three_axis(t: pd.DataFrame, out: Path) -> None:
    """One panel per metric; a consistent axis is one where the bars agree."""
    mets = [m for m in ("units", "yield_pct") if m in set(t.metric)]
    fig, axes = plt.subplots(1, len(mets), figsize=(6.6 * len(mets), 4.6),
                             squeeze=False)
    order = ["coated/uncoated", "anterior/posterior", "medial/lateral"]
    colr = {"coated/uncoated": "#d62728", "anterior/posterior": "#2ca02c",
            "medial/lateral": "#7f7f7f"}
    for ax, met in zip(axes[0], mets, strict=True):
        g = t[t.metric == met]
        animals = sorted(g.animal.unique())
        idx = np.arange(len(animals))
        w = 0.26
        for k, contrast in enumerate(order):
            vals = [g[(g.animal == a) & (g.contrast == contrast)].ratio.median()
                    for a in animals]
            ax.bar(idx + (k - 1) * w, vals, w, color=colr[contrast],
                   label=contrast)
        ax.axhline(1.0, color="k", ls="--", lw=1.2)
        ax.set_xticks(idx)
        ax.set_xticklabels(animals, fontsize=9)
        ax.set_yscale("log")
        ax.set_ylabel("ratio, paired within session")
        ax.set_title(met.replace("_", " "), fontsize=10)
        ax.grid(alpha=0.25, axis="y")
    axes[0][0].legend(fontsize=8)
    fig.suptitle("The same paired data, three ways of naming the contrast \u2014 "
                 "only position agrees across animals", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    d = load()
    if not len(d):
        print("no resolvable treatment sessions")
        return 1

    banner("1. What resolves, and what it covers")
    cov = fig_paired(d, FIG / "W1_paired.png")
    print(cov.to_string(index=False))

    banner("2. The within-session ratio")
    r = paired_ratio(d)
    tab = fig_ratio(r, FIG / "W2_ratio.png")
    print(tab.round(4).to_string(index=False))

    banner("3. The legacy 10-month claim")
    t = fig_tenmonth(d, r, FIG / "W3_tenmonth.png")
    print(t.round(4).to_string(index=False))

    banner("4. Every metric")
    m = fig_metrics(r, FIG / "W4_metrics.png")
    print(m.round(4).to_string(index=False))

    banner("5. The legacy sorts: the only paired yield for Oops and Picasso")
    lg = legacy_sorts()
    if len(lg):
        LEGACY_OUT.parent.mkdir(parents=True, exist_ok=True)
        lg.to_parquet(LEGACY_OUT, index=False)
        print(lg.groupby(["animal", "loc", "pedestal", "cortex", "coating"])
              .agg(n=("date", "size"), first=("date", "min"),
                   last=("date", "max"), units=("units", "median"),
                   yld=("yield_pct", "median")).round(1).to_string())

    banner("6. Coating, pedestal or cortex? The three-axis test")
    t = three_axis(lg, d)
    if len(t):
        fig_three_axis(t, FIG / "W5_three_axis.png")
        for met, g in t.groupby("metric"):
            print(f"\n--- {met} ---")
            print(g.pivot_table(index="contrast", columns="animal",
                                values="ratio").round(3).to_string())
        t.to_csv(REPO / "data" / "derived" / "cohort" /
                 "treatment_three_axis.csv", index=False)

    print("\n  wrote 5 figures to figures/treatment/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

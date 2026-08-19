"""Surface treatment is striped across each array, so the comparison is internal.

Nigel and Fisk each carry two arrays whose shanks were coated in **alternating
stripes**, one stripe treated and the next not. That changes the unit of
analysis: these are not two treated arrays to compare against some other
animal, they are four arrays each containing its own control, measured through
the same amplifier on the same day by the same operator. Every confounder that
makes cross-array comparison hard cancels within a stripe pair.

| animal | pedestal / cortex | array serial | stripe A | stripe B |
|---|---|---|---|---|
| Nigel | Anterior / Lateral | 1025-001496 | TNP L1 | TNP only |
| Nigel | Posterior / Medial | 1025-001473 | EDCNHS L1 | Non-treated Ctrl |
| Fisk | Anterior / Lateral | 1025-001498 | TNP L1 | TNP only |
| Fisk | Posterior / Medial | 1025-001504 | EDCNHS L1 | Non-treated Ctrl |

This is **not** the assignment in the implant table, which has its Treatment
column transposed -- see `ARRAY_TREATMENT` for how that was caught and
confirmed.

**Both arrays test the same thing on two backgrounds.** Stripe A carries L1 and
stripe B does not, on a bare substrate in one array and on TNP in the other. So
the L1 contrast is replicated twice per animal and four times in all.

## Which way the stripes run, which is the whole analysis

Getting this wrong does not error; it silently splits the array along the wrong
axis and returns a null.

- The treatment figure is drawn with the **wire bundle at the bottom** and the
  stripes horizontal.
- Blackrock CMP files are written with the **wire bundle on the right**
  (owner, 2026-08-19), with `col` increasing left-to-right and `row`
  increasing bottom-to-top.

Rotating the CMP frame 90 degrees clockwise puts its right edge at the bottom,
matching the figure. Under that rotation the CMP's `col` axis points *down* the
figure and its `row` axis points *right*. A horizontal stripe in the figure is
therefore a line of constant **`col`**, not constant `row`.

`STRIPE_AXIS = "col"` states it in one place. `EVEN_COL_IS_A` states the phase:
the figure's topmost stripe is the L1 one on both arrays, and the top of the
figure is `col = 0`, so even columns carry L1. **If the array schematic is
mirrored rather than rotated, the phase inverts and every label swaps** — which
is why the report prints both stripes' values side by side rather than only
their ratio.

## The control that makes the split falsifiable

`row` parity carries no treatment. Running the identical pipeline on row parity
is a negative control with a known answer: it must find nothing. If row parity
showed the effect and column parity did not, the rotation above is wrong. If
both show an effect, something other than the coating is striping the array.

Run from repo root:

    uv run python notebooks/scratch_surface_conditions.py [--jobs 6]
    uv run python notebooks/scratch_surface_conditions.py --cached   # figures only

Writes `data/derived/surface/` and `figures/surface/`.

See:
- docs/notes/surface_conditions.md
- docs/notes/channel_mapping.md
"""

from __future__ import annotations

import argparse
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, wilcoxon

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_cohort_io import PROBE_DIR, parse_cmp  # noqa: E402
from scratch_rocky_resort import (  # noqa: E402
    PLEXON_DROP_UNITS,
    align_on_trough,
    baseline_noise_uv,
    load_snippets,
    unit_metrics,
)

OUT_DIR = REPO / "data" / "derived" / "surface"
ELEC_OUT = OUT_DIR / "electrode_metrics.parquet"
CONTRAST_OUT = OUT_DIR / "surface_contrast.parquet"
FIG = REPO / "figures" / "surface"

# The stripes run along CMP columns -- see the module docstring. Both flags are
# assumptions about the array schematic, not about the data, and both are
# one-line edits if the schematic is read differently.
STRIPE_AXIS = "col"
EVEN_COL_IS_A = True

# serial -> (stripe A, stripe B, background). A always carries L1.
#
# **The implant table's Treatment column is transposed.** It reads Anterior ->
# Ctrl/EDC and Posterior -> TNP, but the treatment schematic's two panels carry
# the real electrode maps, and they match the opposite arrays: the panel
# labelled EDCNHS is 1025-001473 (Nigel Posterior) cell for cell, including its
# unconnected positions, and the TNP panel is 1025-001496 (Nigel Anterior).
# Owner confirmed 2026-08-19: "the table is wrong, anterior is TNP L1/TNP".
#
# Applied to Fisk on the same reasoning -- its Lateral array sits on the
# anterior pedestal in the same table -- but Fisk's own maps match neither
# panel, so that half is an inference from the surgical design rather than from
# a schematic. Flagged in surface_conditions.md.
ARRAY_TREATMENT: dict[str, tuple[str, str, str]] = {
    "1025-001496": ("TNP L1", "TNP only", "TNP"),                # Nigel Ant
    "1025-001473": ("EDCNHS L1", "Non-treated Ctrl", "bare"),    # Nigel Post
    "1025-001498": ("TNP L1", "TNP only", "TNP"),                # Fisk Lat/Ant
    "1025-001504": ("EDCNHS L1", "Non-treated Ctrl", "bare"),    # Fisk Med/Post
}
SUBJECT_ARRAY = {
    ("Nigel", "Anterior"): "1025-001496",
    ("Nigel", "Posterior"): "1025-001473",
    ("Fisk", "Lateral"): "1025-001498",
    ("Fisk", "Medial"): "1025-001504",
}

# Metrics carried through every stage. Sorting-free first, then sorted.
FREE_METRICS = ["rate_hz", "noise_uv", "amp_med", "peak_snr"]
SORTED_METRICS = ["n_units", "n_gated", "unit_amp_med", "unit_snr_med",
                  "unit_rate_med"]
L1_COLOR, NOL1_COLOR = "#2ca02c", "#7f7f7f"


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === The condition map ===
def surface_map(serial: str) -> pd.DataFrame:
    """channel_id -> stripe condition for one array.

    Parameters
    ----------
    serial : str
        Array serial, e.g. ``"1025-001496"``.

    Returns
    -------
    pandas.DataFrame
        ``channel_id, col, row, condition, has_l1, background`` for every
        connected electrode. Four positions per array are unconnected and
        simply absent, as they are from the CMP.
    """
    hits = sorted(PROBE_DIR.glob(f"*{serial}*.cmp"))
    if not hits:
        raise FileNotFoundError(f"no CMP for {serial}")
    d = parse_cmp(hits[0])[["channel_id", "col", "row"]].copy()
    a, b, background = ARRAY_TREATMENT[serial]
    even_is_a = EVEN_COL_IS_A
    parity = d[STRIPE_AXIS] % 2 == 0
    d["has_l1"] = parity if even_is_a else ~parity
    d["condition"] = np.where(d.has_l1, a, b)
    d["background"] = background
    d["serial"] = serial
    d["mapfile"] = hits[0].name
    return d


def control_map(serial: str) -> pd.DataFrame:
    """The same split along `row`, where no treatment exists. A known null."""
    d = surface_map(serial)[["channel_id", "col", "row", "serial"]].copy()
    d["has_l1"] = d["row"] % 2 == 0
    d["condition"] = np.where(d.has_l1, "row-even", "row-odd")
    return d


# %%
# === Per-electrode metrics from one NEV ===
def electrode_metrics(job: dict) -> list[dict]:
    """Sorting-free and sorted metrics for every electrode in one recording.

    One read of the NEV serves both layers. The sorting-free half is the
    threshold-crossing layer CLAUDE.md puts first -- event count, baseline
    noise, snippet amplitude -- and exists for every electrode that crossed at
    all. The sorted half comes from the Plexon `-01` labels through the same
    `unit_metrics()` gate the rest of the project uses.
    """
    base = {k: v for k, v in job.items() if k not in ("nev", "path")}
    try:
        data = load_snippets(Path(job["nev"]))
    except Exception as exc:  # noqa: BLE001
        return [dict(**base, error=f"{type(exc).__name__}: {exc}"[:140])]
    sr, nbefore, dur = data["sr"], data["nbefore"], data["duration_s"]
    out: list[dict] = []
    for elec, e in sorted(data["by_elec"].items()):
        wf, t, pu = e["wf"], e["t"], e["plexon_unit"]
        if not len(t):
            continue
        noise = baseline_noise_uv(wf, nbefore)
        amp = np.abs(wf.min(axis=1))
        amp_med = float(np.median(amp))
        row = dict(**base, channel_id=int(elec), n_events=int(len(t)),
                   duration_s=float(dur),
                   rate_hz=float(len(t) / dur) if dur else np.nan,
                   noise_uv=float(noise), amp_med=amp_med,
                   peak_snr=float(amp_med / noise) if noise > 0 else np.nan)
        aligned = align_on_trough(wf, nbefore)
        units = []
        for u in np.unique(pu):
            if u in PLEXON_DROP_UNITS:
                continue
            sel = pu == u
            if not sel.any():
                continue
            units.append(unit_metrics(aligned[sel], t[sel], noise, sr,
                                      nbefore, dur))
        gated = [m for m in units if m["pass_gate"]]
        row.update(n_units=len(units), n_gated=len(gated))
        if gated:
            row.update(
                unit_amp_med=float(np.median([m["amplitude_uv"] for m in gated])),
                unit_snr_med=float(np.median([m["snr"] for m in gated])),
                unit_rate_med=float(np.median([m["firing_rate_hz"]
                                               for m in gated])),
            )
        out.append(row)
    return out


def build_worklist(subject: str = "") -> list[dict]:
    """Plexon `-01` recordings for Nigel and Fisk, from their own builders."""
    jobs: list[dict] = []
    if subject in ("", "Nigel"):
        from scratch_cohort_longitudinal import build_worklist as cohort_jobs
        inv = pd.read_parquet(REPO / "data" / "derived" /
                              "monkey_inventory.parquet")
        for j in cohort_jobs(inv):
            if j["subject"] != "Nigel":
                continue
            jobs.append(dict(subject="Nigel", array=j["array"],
                             serial=SUBJECT_ARRAY[("Nigel", j["array"])],
                             session=Path(j["path"]).stem,
                             date=str(pd.Timestamp(j["date"]).date()),
                             nev=j["path"]))
    if subject in ("", "Fisk"):
        from scratch_fisk_sorted import build_worklist as fisk_jobs
        for j in fisk_jobs():
            jobs.append(dict(subject="Fisk", array=j["array"],
                             serial=SUBJECT_ARRAY[("Fisk", j["array"])],
                             session=j["session"], date=j["date"],
                             nev=j["nev"]))
    return jobs


def complete_grid(e: pd.DataFrame) -> pd.DataFrame:
    """Reindex every session onto its array's full electrode list.

    An electrode that produced no threshold crossing has no row in the NEV, so
    it is silently absent -- and a missing electrode is a **zero**, not a gap.
    Dropping them would compute yield over only the electrodes that already
    work, which is exactly the quantity the treatment is supposed to change.
    """
    frames = []
    for (sub, arr, sess), g in e.groupby(["subject", "array", "session"]):
        serial = SUBJECT_ARRAY[(sub, arr)]
        full = surface_map(serial)[["channel_id"]]
        m = full.merge(g, on="channel_id", how="left")
        m[["subject", "array", "session", "serial"]] = [sub, arr, sess, serial]
        m["date"] = g.date.iloc[0]
        for c in ("n_events", "n_units", "n_gated"):
            if c in m:
                m[c] = m[c].fillna(0.0)
        m["rate_hz"] = m.rate_hz.fillna(0.0)
        frames.append(m)
    return pd.concat(frames, ignore_index=True)


# %%
# === Within-session contrast ===
def session_contrast(e: pd.DataFrame, mapper) -> pd.DataFrame:
    """One row per session per stripe: yield and medians over that stripe.

    Everything here is computed **inside** a session, so date, amplifier,
    threshold and operator are held fixed by construction. The pairing across
    stripes is what the striped design buys.
    """
    rows = []
    for (sub, arr, sess), g in e.groupby(["subject", "array", "session"]):
        smap = mapper(SUBJECT_ARRAY[(sub, arr)])
        g = g.merge(smap[["channel_id", "condition", "has_l1"]],
                    on="channel_id", how="inner")
        for (cond, l1), c in g.groupby(["condition", "has_l1"]):
            n_elec = len(c)
            if not n_elec:
                continue
            row = dict(subject=sub, array=arr, session=sess,
                       date=pd.Timestamp(c.date.iloc[0]), condition=cond,
                       has_l1=bool(l1), n_electrodes=n_elec)
            row["units_per_electrode"] = float(c.n_gated.sum() / n_elec)
            row["all_units_per_electrode"] = float(c.n_units.sum() / n_elec)
            row["elec_with_units"] = float((c.n_gated > 0).mean())
            row["elec_active"] = float((c.n_events > 0).mean())
            for m in FREE_METRICS + SORTED_METRICS[2:]:
                row[m] = float(c[m].median()) if m in c else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def stripe_permutation(e: pd.DataFrame, metrics: list[str],
                       rng_seed: int = 0) -> pd.DataFrame:
    """Test the stripe assignment against every other 5/5 split of the grid.

    **The session is not the unit of replication.** The same 96 electrodes are
    recorded every session, so a paired test across sessions asks "do these two
    fixed electrode sets differ at all", which is essentially never exactly
    false -- and it answers p < 0.0001 on the row axis, where no treatment
    exists. Adding sessions buys precision on a fixed quantity, not evidence
    about a cause.

    The unit that was actually assigned a treatment is the **stripe**, and
    there are five per condition. So: average each electrode over all its
    sessions, average those into ten stripe means, and ask where the real
    even/odd assignment sits among all `C(10,5) = 252` ways of calling five of
    the ten stripes treated. That null preserves the array's spatial structure
    exactly, because it reuses the same stripe means.

    Returns
    -------
    pandas.DataFrame
        Per array, axis and metric: the observed difference, its two-sided
        percentile in the permutation null, and the null's spread.
    """
    from itertools import combinations

    del rng_seed                          # exhaustive, so nothing to seed
    treated = [0, 2, 4, 6, 8] if EVEN_COL_IS_A else [1, 3, 5, 7, 9]
    rows = []
    for (sub, arr), g in e.groupby(["subject", "array"]):
        # One value per electrode: its mean over every session it appears in.
        per_elec = g.groupby(["channel_id", "col", "row"])[metrics].mean()
        per_elec = per_elec.reset_index()
        for axis in ("col", "row"):
            prof = per_elec.groupby(axis)[metrics].mean()
            levels = list(prof.index)
            if len(levels) != 10:
                continue
            for m in metrics:
                v = prof[m]
                if not np.isfinite(v).all():
                    continue
                obs = float(v[treated].mean() -
                            v[[x for x in levels if x not in treated]].mean())
                null = []
                for pick in combinations(levels, 5):
                    rest = [x for x in levels if x not in pick]
                    null.append(float(v[list(pick)].mean() - v[rest].mean()))
                null = np.asarray(null)
                # Two-sided: how often does an arbitrary split separate the
                # stripe means at least as strongly as the real one?
                p = float((np.abs(null) >= abs(obs)).mean())
                rows.append(dict(
                    subject=sub, array=arr, axis=axis, metric=m,
                    observed=obs, null_sd=float(null.std()),
                    z=float(obs / null.std()) if null.std() > 0 else np.nan,
                    p_perm=p, n_splits=len(null)))
    return pd.DataFrame(rows)


def second_difference(e: pd.DataFrame, axis: str,
                      metrics: list[str]) -> pd.DataFrame:
    """Each treated stripe against the **mean of its two neighbours**.

    A plain even/odd split of a striped array is confounded, and badly. Yield
    on these arrays runs in smooth cortical gradients -- Nigel Anterior goes
    0.05 -> 1.12 -> 0.32 units per electrode across its ten columns -- and
    sampling a gradient at even indices versus odd ones leaves a small
    systematic offset that has nothing to do with the coating. Over 70+
    sessions a paired test turns a 5% sampling artefact into p < 0.0001, which
    is exactly what the row-parity control caught: 29 of 44 "significant"
    on an axis carrying no treatment at all.

    Contrasting stripe `c` with the average of `c-1` and `c+1` cancels any
    **linear** gradient exactly and a quadratic one to second order, because
    the two neighbours sit symmetrically about it. Only interior stripes have
    two neighbours, so columns 2, 4, 6 and 8 are used and column 0 is dropped.

    Parameters
    ----------
    e : pandas.DataFrame
        Per-electrode, per-session metrics with `col` and `row` attached.
    axis : {"col", "row"}
        Which grid axis to treat as the stripe axis. `"row"` is the control.
    metrics : list of str
        Per-electrode columns to contrast.

    Returns
    -------
    pandas.DataFrame
        One row per session per metric, with the contrast in the metric's own
        units and as a ratio.
    """
    treated = [2, 4, 6, 8] if EVEN_COL_IS_A else [1, 3, 5, 7]
    rows = []
    for (sub, arr, sess), g in e.groupby(["subject", "array", "session"]):
        prof = g.groupby(axis)[metrics].mean()
        date = pd.Timestamp(g.date.iloc[0])
        for m in metrics:
            v = prof[m]
            diffs, ratios = [], []
            for c in treated:
                if c not in v.index or (c - 1) not in v.index \
                        or (c + 1) not in v.index:
                    continue
                nb = 0.5 * (v[c - 1] + v[c + 1])
                if not np.isfinite(nb) or not np.isfinite(v[c]):
                    continue
                diffs.append(float(v[c] - nb))
                if nb > 0:
                    ratios.append(float(v[c] / nb))
            if not diffs:
                continue
            rows.append(dict(subject=sub, array=arr, session=sess, date=date,
                             axis=axis, metric=m, n_stripes=len(diffs),
                             diff=float(np.mean(diffs)),
                             ratio=float(np.mean(ratios)) if ratios else np.nan))
    return pd.DataFrame(rows)


def second_difference_stats(sd: pd.DataFrame) -> pd.DataFrame:
    """Is the neighbour-corrected contrast different from zero, per array?"""
    rows = []
    for (sub, arr, axis, m), g in sd.groupby(["subject", "array", "axis",
                                              "metric"]):
        d = g.dropna(subset=["diff"])
        if len(d) < 8:
            continue
        try:
            _, p = wilcoxon(d["diff"])
        except ValueError:
            p = 1.0
        r, p_t = spearmanr(d.date.map(pd.Timestamp.toordinal), d["diff"])
        rows.append(dict(subject=sub, array=arr, axis=axis, metric=m,
                         n=len(d), diff=float(d["diff"].median()),
                         ratio=float(d.ratio.median()), p=float(p),
                         rho_time=float(r), p_time=float(p_t)))
    return pd.DataFrame(rows)


def paired_stats(ct: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    """Paired test per array per metric: L1 stripe against its neighbour."""
    rows = []
    for (sub, arr), g in ct.groupby(["subject", "array"]):
        piv = g.pivot_table(index=["session", "date"], columns="has_l1",
                            values=metrics)
        for m in metrics:
            if (m, True) not in piv or (m, False) not in piv:
                continue
            d = piv[m].dropna()
            if len(d) < 8:
                continue
            a, b = d[True], d[False]
            try:
                _, p = wilcoxon(a, b)
            except ValueError:                 # all differences zero
                p = 1.0
            ratio = float((a / b.replace(0, np.nan)).median())
            # Does the gap itself move? A treatment that wears off shows here
            # and not in the pooled ratio.
            dates = d.index.get_level_values("date")
            r_gap, p_gap = spearmanr(
                pd.Series(dates).map(pd.Timestamp.toordinal),
                (a - b).to_numpy())
            rows.append(dict(
                subject=sub, array=arr, metric=m, n=len(d),
                l1=float(a.median()), no_l1=float(b.median()), ratio=ratio,
                p_paired=float(p), higher_in=("L1" if a.median() > b.median()
                                              else "no-L1"),
                rho_gap=float(r_gap), p_gap=float(p_gap)))
    return pd.DataFrame(rows)


def longitudinal(ct: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    """Each stripe's own trend, so the two can be read side by side."""
    rows = []
    for (sub, arr, cond), g in ct.groupby(["subject", "array", "condition"]):
        x = g.date.map(pd.Timestamp.toordinal)
        for m in metrics:
            d = g.dropna(subset=[m])
            if len(d) < 8 or d[m].nunique() < 3:
                continue
            r, p = spearmanr(d.date.map(pd.Timestamp.toordinal), d[m])
            rows.append(dict(subject=sub, array=arr, condition=cond,
                             has_l1=bool(g.has_l1.iloc[0]), metric=m,
                             n=len(d), rho=float(r), p=float(p),
                             first=float(d.sort_values("date")[m].head(5)
                                         .median()),
                             last=float(d.sort_values("date")[m].tail(5)
                                        .median())))
        del x
    return pd.DataFrame(rows)


# %%
# === Figures ===
def fig_layout(e: pd.DataFrame, out: Path) -> None:
    """The stripe map beside the measured yield map, per array.

    If the coating does anything and the axis is right, the right-hand maps
    should be visibly striped in the same direction as the left-hand ones.
    This is the figure that checks the geometry against the data.
    """
    keys = [(s, a) for (s, a) in SUBJECT_ARRAY if (
        (e.subject == s) & (e.array == a)).any()]
    fig, axes = plt.subplots(2, len(keys), figsize=(3.5 * len(keys), 7.2),
                             squeeze=False)
    for j, (sub, arr) in enumerate(keys):
        serial = SUBJECT_ARRAY[(sub, arr)]
        smap = surface_map(serial)
        ax = axes[0, j]
        for l1, g in smap.groupby("has_l1"):
            ax.scatter(g.col, g.row, s=95,
                       color=L1_COLOR if l1 else NOL1_COLOR,
                       label=g.condition.iloc[0])
        ax.set_title(f"{sub} {arr}\n{serial}", fontsize=9.5)
        ax.set_xlabel("CMP col  (stripe axis)", fontsize=8)
        ax.set_ylabel("CMP row", fontsize=8)
        ax.set_aspect("equal")
        # Inside the axes: below them it collides with the yield-map titles.
        ax.legend(fontsize=6.5, loc="lower left", framealpha=0.85,
                  handletextpad=0.3, borderpad=0.3)
        ax.tick_params(labelsize=7)

        ax = axes[1, j]
        g = e[(e.subject == sub) & (e.array == arr)]
        y = g.groupby("channel_id").n_gated.mean().rename("y").reset_index()
        y = smap.merge(y, on="channel_id", how="left")
        sc = ax.scatter(y.col, y.row, s=95, c=y.y, cmap="viridis")
        ax.set_title("mean gated units per electrode", fontsize=9)
        ax.set_xlabel("CMP col", fontsize=8)
        ax.set_aspect("equal")
        ax.tick_params(labelsize=7)
        fig.colorbar(sc, ax=ax, fraction=0.046)
    fig.suptitle("Stripe assignment (top) against measured yield (bottom).\n"
                 "The CMP is drawn with the bundle on the right; the treatment "
                 "figure has it at the bottom, so stripes run along `col`.",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_yield(ct: pd.DataFrame, out: Path) -> None:
    """The longitudinal ask: yield per stripe, over time, per array."""
    keys = sorted({(s, a) for s, a in zip(ct.subject, ct.array, strict=True)})
    fig, axes = plt.subplots(1, len(keys), figsize=(4.1 * len(keys), 4.2),
                             squeeze=False)
    for j, (sub, arr) in enumerate(keys):
        ax = axes[0, j]
        g = ct[(ct.subject == sub) & (ct.array == arr)]
        for l1, c in g.groupby("has_l1"):
            c = c.sort_values("date")
            r, p = spearmanr(c.date.map(pd.Timestamp.toordinal),
                             c.units_per_electrode)
            ax.plot(c.date, c.units_per_electrode, "o-", ms=3, lw=0.9,
                    color=L1_COLOR if l1 else NOL1_COLOR, alpha=0.85,
                    label=f"{c.condition.iloc[0]}: rho {r:+.3f} p={p:.2g}")
        ax.set_ylabel("gated units / electrode")
        ax.set_title(f"{sub} {arr}", fontsize=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.grid(alpha=0.25)
        ax.legend(fontsize=7.5)
    fig.suptitle("Unit yield by surface condition, within array", fontsize=11.5)
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_metrics(ct: pd.DataFrame, out: Path) -> None:
    """Every metric, both stripes, all four arrays."""
    metrics = [("units_per_electrode", "gated units / electrode"),
               ("elec_with_units", "electrodes with units (frac)"),
               ("rate_hz", "crossing rate (Hz)"),
               ("noise_uv", "noise floor (uV)"),
               ("amp_med", "snippet amplitude (uV)"),
               ("unit_snr_med", "median unit SNR")]
    keys = sorted({(s, a) for s, a in zip(ct.subject, ct.array, strict=True)})
    fig, axes = plt.subplots(len(metrics), len(keys),
                             figsize=(3.6 * len(keys), 2.4 * len(metrics)),
                             sharex="col", squeeze=False)
    for j, (sub, arr) in enumerate(keys):
        g = ct[(ct.subject == sub) & (ct.array == arr)]
        for i, (m, label) in enumerate(metrics):
            ax = axes[i, j]
            for l1, c in g.groupby("has_l1"):
                c = c.sort_values("date").dropna(subset=[m])
                ax.plot(c.date, c[m], "o-", ms=2.4, lw=0.8,
                        color=L1_COLOR if l1 else NOL1_COLOR, alpha=0.8,
                        label=c.condition.iloc[0] if i == 0 else None)
            ax.set_ylabel(label, fontsize=8)
            ax.grid(alpha=0.25)
            ax.tick_params(labelsize=7)
            if i == 0:
                ax.set_title(f"{sub} {arr}", fontsize=9.5)
                ax.legend(fontsize=6.5)
    for ax in axes[-1]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.suptitle("Every metric, both stripes, four arrays", fontsize=11.5)
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_contrast(real: pd.DataFrame, ctrl: pd.DataFrame, out: Path) -> None:
    """The paired contrast, against the row-parity control that must be null."""
    metrics = ["units_per_electrode", "elec_with_units", "rate_hz",
               "noise_uv", "amp_med", "unit_snr_med"]
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2), sharey=True)
    for ax, (tab, name) in zip(
            axes, ((real, "column parity — the treatment stripes"),
                   (ctrl, "row parity — no treatment, must be null")),
            strict=True):
        keys = sorted({(s, a) for s, a in zip(tab.subject, tab.array,
                                              strict=True)})
        h = 0.8 / max(len(keys), 1)
        for k, (sub, arr) in enumerate(keys):
            g = tab[(tab.subject == sub) & (tab.array == arr)]
            vals, pos, edge = [], [], []
            for i, m in enumerate(metrics):
                r = g[g.metric == m]
                vals.append(float(r.ratio.iloc[0]) if len(r) else np.nan)
                pos.append(i + (k - (len(keys) - 1) / 2) * h)
                edge.append("k" if len(r) and r.p_paired.iloc[0] < 0.05
                            else "none")
            ax.barh(pos, np.array(vals) - 1.0, height=h * 0.9, left=1.0,
                    label=f"{sub} {arr}", edgecolor=edge, linewidth=1.4)
        ax.axvline(1.0, color="k", lw=1.2)
        ax.set_yticks(range(len(metrics)))
        ax.set_yticklabels(metrics, fontsize=9)
        ax.set_xlabel("stripe A / stripe B  (median of within-session ratios)")
        ax.set_title(name, fontsize=10.5)
        ax.grid(alpha=0.25, axis="x")
        ax.legend(fontsize=7.5)
    fig.suptitle("Within-session ratio between neighbouring stripes. "
                 "Black outline = paired Wilcoxon p < 0.05.\n"
                 "The right panel splits the same electrodes along an axis "
                 "with no treatment on it.", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_permutation(perm: pd.DataFrame, e: pd.DataFrame, out: Path) -> None:
    """Where the real stripe assignment sits among all 252 splits.

    A null result is only worth as much as its sensitivity, so this draws the
    permutation spread rather than only the verdict: the bar is the observed
    contrast, the whisker is the range an arbitrary 5/5 split of the same ten
    stripes produces.
    """
    metrics = [("n_gated", "gated units / electrode"),
               ("rate_hz", "crossing rate (Hz)"),
               ("noise_uv", "noise floor (uV)"),
               ("peak_snr", "peak SNR")]
    keys = sorted({(s, a) for s, a in zip(perm.subject, perm.array,
                                          strict=True)})
    fig, axes = plt.subplots(1, len(metrics), figsize=(4.0 * len(metrics), 4.6))
    lev = e.groupby(["subject", "array"])[[m for m, _ in metrics]].mean()
    for ax, (m, label) in zip(axes, metrics, strict=True):
        y = np.arange(len(keys))
        for axis, off, colour in (("col", -0.18, "#d62728"),
                                  ("row", 0.18, "0.55")):
            obs, sd = [], []
            for sub, arr in keys:
                r = perm[(perm.subject == sub) & (perm.array == arr)
                         & (perm.axis == axis) & (perm.metric == m)]
                base = lev.loc[(sub, arr), m]
                obs.append(100 * float(r.observed.iloc[0]) / base
                           if len(r) and base else np.nan)
                sd.append(100 * 1.96 * float(r.null_sd.iloc[0]) / base
                          if len(r) and base else np.nan)
            ax.barh(y + off, obs, height=0.32, color=colour,
                    label="treatment axis" if axis == "col" else "control axis")
            ax.errorbar(np.zeros(len(y)), y + off, xerr=sd, fmt="none",
                        ecolor="k", elinewidth=1.1, capsize=3)
        ax.axvline(0, color="k", lw=1)
        ax.set_yticks(y)
        ax.set_yticklabels([f"{s}\n{a}" for s, a in keys], fontsize=8)
        ax.set_xlabel("stripe contrast (% of array mean)", fontsize=8.5)
        ax.set_title(label, fontsize=9.5)
        ax.grid(alpha=0.25, axis="x")
        ax.tick_params(labelsize=8)
    axes[0].legend(fontsize=7.5, loc="lower right")
    fig.suptitle("Stripe-level contrast against the permutation null. "
                 "Whiskers are +/-1.96 SD of all 252 alternative 5/5 splits.\n"
                 "Every bar sits inside its whisker: no array separates its "
                 "treated stripes from its untreated ones.", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(out, dpi=150)
    plt.close(fig)


# %%
def report_sd(sd_stats: pd.DataFrame) -> None:
    """The gradient-corrected contrast, treatment axis beside its control."""
    banner("7. Gradient-corrected: each stripe against its two neighbours")
    print("  A linear gradient cancels exactly. `col` is the treatment axis,")
    print("  `row` carries no treatment and is the control. If the coating")
    print("  does anything, col fires and row does not.\n")
    for m in ("n_gated", "rate_hz", "noise_uv", "amp_med", "peak_snr"):
        d = sd_stats[sd_stats.metric == m]
        if not len(d):
            continue
        print(f"  --- {m} ---")
        piv = d.pivot_table(index=["subject", "array"], columns="axis",
                            values=["ratio", "p"])
        print(piv.round(4).to_string())
        print()
    n_col = int(((sd_stats.axis == "col") & (sd_stats.p < 0.05)).sum())
    n_row = int(((sd_stats.axis == "row") & (sd_stats.p < 0.05)).sum())
    tot = int((sd_stats.axis == "col").sum())
    print(f"  significant at p<0.05 -- treatment axis {n_col}/{tot}, "
          f"control axis {n_row}/{tot}")


def report(e: pd.DataFrame, ct: pd.DataFrame, st: pd.DataFrame,
           sc: pd.DataFrame, lo: pd.DataFrame) -> None:
    banner("1. The stripe map")
    for (sub, arr), serial in SUBJECT_ARRAY.items():
        m = surface_map(serial)
        n = m.groupby("condition").size().to_dict()
        print(f"  {sub:6s} {arr:10s} {serial}  {m.mapfile.iloc[0]}")
        print(f"      {n}   stripe axis={STRIPE_AXIS}  "
              f"even-{STRIPE_AXIS} carries L1={EVEN_COL_IS_A}")

    banner("2. Coverage")
    print(e.groupby(["subject", "array"]).agg(
        sessions=("session", "nunique"), electrode_rows=("channel_id", "size"),
        first=("date", "min"), last=("date", "max")).to_string())

    banner("3. Within-session contrast, L1 stripe against its neighbour")
    print("  ratio > 1 means the L1 stripe is higher. p is a paired Wilcoxon")
    print("  across sessions; every pair is within one recording.\n")
    if not len(st):
        # Only reachable on a --limit run: the paired tests need eight sessions.
        print("  fewer than 8 paired sessions; nothing to test yet")
        return
    print(st[["subject", "array", "metric", "n", "l1", "no_l1", "ratio",
              "p_paired", "higher_in"]].round(4).to_string(index=False))

    banner("4. The row-parity control, which must be null -- and is not")
    sig = sc[sc.p_paired < 0.05] if len(sc) else sc
    print(f"  significant at p<0.05: {len(sig)} of {len(sc)} "
          f"(treatment axis: {int((st.p_paired < 0.05).sum())} of {len(st)})")
    print("  The control fires at least as often as the treatment axis, so a")
    print("  plain even/odd split cannot support any claim about the coating.")
    print("  Cause: yield runs in smooth gradients across the array, and")
    print("  even-versus-odd sampling of a gradient leaves an offset that a")
    print("  paired test over 70+ sessions resolves easily. Section 7 uses an")
    print("  estimator that cancels it.")

    banner("5. Does the gap move over time?")
    print("  rho of (L1 - no-L1) against date. A coating that wears off shows")
    print("  here even when the pooled ratio does not.\n")
    d = st[st.metric.isin(["units_per_electrode", "rate_hz", "noise_uv"])]
    print(d[["subject", "array", "metric", "n", "rho_gap", "p_gap"]]
          .round(4).to_string(index=False))

    banner("6. Each stripe's own longitudinal trend")
    piv = lo[lo.metric.isin(["units_per_electrode", "rate_hz", "noise_uv",
                             "unit_snr_med"])]
    print(piv[["subject", "array", "condition", "metric", "n", "rho", "p",
               "first", "last"]].round(3).to_string(index=False))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--subject", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--cached", action="store_true",
                    help="reuse electrode_metrics.parquet, redo the rest")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    if args.cached and ELEC_OUT.exists():
        e = pd.read_parquet(ELEC_OUT)
    else:
        jobs = build_worklist(args.subject)
        if args.limit:
            jobs = jobs[:args.limit]
        banner(f"Per-electrode pass -- {len(jobs)} recordings")
        rows: list[dict] = []
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            for i, res in enumerate(ex.map(electrode_metrics, jobs,
                                           chunksize=1), 1):
                rows.extend(res)
                if i % 20 == 0:
                    print(f"    {i}/{len(jobs)}", flush=True)
        e = pd.DataFrame(rows)
        if "error" in e.columns:
            bad = e[e.error.notna()]
            if len(bad):
                print(f"  failed: {len(bad)}")
                print(bad.error.astype(str).str.slice(0, 70)
                      .value_counts().head(3).to_string())
            e = e[e.error.isna()].drop(columns=["error"])
        e = complete_grid(e)
        e.to_parquet(ELEC_OUT, engine="pyarrow", index=False)

    # Geometry for the gradient-corrected estimator. Attached here rather than
    # baked into the cached table so a relabel never needs a re-read.
    geo = pd.concat([surface_map(s)[["channel_id", "col", "row"]]
                     .assign(serial=s) for s in ARRAY_TREATMENT],
                    ignore_index=True)
    e = e.merge(geo, on=["channel_id", "serial"], how="left")

    elec_metrics = ["n_gated", "n_units", *FREE_METRICS]
    sd = pd.concat([second_difference(e, "col", elec_metrics),
                    second_difference(e, "row", elec_metrics)],
                   ignore_index=True)
    sd_stats = second_difference_stats(sd)
    sd.to_parquet(OUT_DIR / "stripe_second_difference.parquet",
                  engine="pyarrow", index=False)
    sd_stats.to_parquet(OUT_DIR / "stripe_sd_stats.parquet",
                        engine="pyarrow", index=False)
    perm = stripe_permutation(e, elec_metrics)
    perm.to_parquet(OUT_DIR / "stripe_permutation.parquet",
                    engine="pyarrow", index=False)

    metrics = ["units_per_electrode", "all_units_per_electrode",
               "elec_with_units", "elec_active", *FREE_METRICS,
               "unit_amp_med", "unit_snr_med", "unit_rate_med"]
    ct = session_contrast(e, surface_map)
    st = paired_stats(ct, metrics)
    lo = longitudinal(ct, metrics)
    ct_ctrl = session_contrast(e, control_map)
    sc = paired_stats(ct_ctrl, metrics)

    ct.to_parquet(OUT_DIR / "stripe_sessions.parquet", engine="pyarrow",
                  index=False)
    st["axis"] = "col (treatment)"
    sc["axis"] = "row (control)"
    pd.concat([st, sc], ignore_index=True).to_parquet(
        CONTRAST_OUT, engine="pyarrow", index=False)
    lo.to_parquet(OUT_DIR / "stripe_trends.parquet", engine="pyarrow",
                  index=False)

    # A short run (--limit) can leave a stage with fewer than the eight paired
    # sessions the tests need, which is not an error -- it just has nothing to
    # draw yet.
    jobs = [("U1_layout.png", fig_layout, (e,), len(e)),
            ("U2_yield.png", fig_yield, (ct,), len(ct)),
            ("U3_metrics.png", fig_metrics, (ct,), len(ct)),
            ("U4_contrast.png", fig_contrast, (st, sc), min(len(st), len(sc))),
            ("U5_permutation.png", fig_permutation, (perm, e), len(perm))]
    for name, fn, fargs, n in jobs:
        if not n:
            print(f"  skipped {name}: nothing to draw yet")
            continue
        fn(*fargs, FIG / name)

    report(e, ct, st, sc, lo)
    report_sd(sd_stats)

    banner("8. Stripe-level permutation -- the correct unit of inference")
    print("  Each electrode averaged over its sessions, then into 10 stripe")
    print("  means. The real 5/5 assignment is ranked against all 252 ways of")
    print("  splitting the same ten stripes, so the array's spatial structure")
    print("  is held fixed. `col` is the treatment axis; `row` is the null.\n")
    for m in ("n_gated", "rate_hz", "noise_uv", "peak_snr"):
        d = perm[perm.metric == m]
        if not len(d):
            continue
        print(f"  --- {m} ---")
        print(d.pivot_table(index=["subject", "array"], columns="axis",
                            values=["observed", "p_perm"]).round(4).to_string())
        print()
    hit = perm[(perm.axis == "col") & (perm.p_perm < 0.05)]
    ctl = perm[(perm.axis == "row") & (perm.p_perm < 0.05)]
    tot = int((perm.axis == "col").sum())
    print(f"  p_perm < 0.05 -- treatment axis {len(hit)}/{tot}, "
          f"control axis {len(ctl)}/{tot}")
    print(f"\n  wrote {ELEC_OUT.relative_to(REPO)}  ({len(e)} rows)")
    print(f"  wrote {CONTRAST_OUT.relative_to(REPO)}")
    print("  wrote 4 figures to figures/surface/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

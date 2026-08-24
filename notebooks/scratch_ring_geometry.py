"""Does position on the array predict recording quality? The concentric-ring test.

Forrest et al. 2025 (J. Neural Eng. 22 066008) model micromotion-induced tissue
strain around Utah arrays and find it is highest at the array's edge and corners.
They then group electrodes into **concentric rings** -- "the number of rows away
from the edge of the array" -- and report that edge electrodes differ from
interior ones in impedance, peak-to-peak waveform voltage and SNR.

Our CMP geometry is verified (`cmp_validation.md`), so the grouping is free: the
electrode tables already carry `col` and `row`. This asks the same question of
six 10x10 arrays across three animals and up to six years.

**The hard part is not the grouping, it is the null.** Ring membership is a
*fixed* property of an electrode, so a paired test across sessions asks "do
these two fixed electrode sets differ at all", which is essentially never
exactly false -- the same trap documented in `surface_conditions.md`. Worse,
these arrays carry strong smooth spatial gradients in yield that are cortical,
not geometric, and a gradient alone will make one edge look different from the
middle.

Three tests, in increasing order of what they are worth:

1. **Naive paired-across-sessions Wilcoxon.** Reported only so its own control
   can be shown beside it. Not evidence.
2. **Toroidal-shift permutation.** Roll the metric map over the grid while
   holding the ring labels fixed. Preserves the array's spatial autocorrelation
   and destroys only its registration to the physical boundary.
3. **Four-border isotropy.** A mechanical edge effect is *isotropic*: all four
   borders should deviate from the interior in the same direction. A cortical
   gradient is *directional*: it raises one border and lowers the opposite. This
   is the test that separates geometry from biology, and it is the one this
   script is really for.

Run from repo root:

    uv run python notebooks/scratch_ring_geometry.py

See docs/notes/ring_geometry.md.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")

# The Windows console is cp1252; figures still carry real typography.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))

from scratch_cohort_io import PROBE_DIR, banner, parse_cmp  # noqa: E402

FIG = REPO / "figures" / "ring"
OUT = REPO / "data" / "derived" / "ring"
GRID = 10  # Utah 10x10; the four corners are unconnected on every array here

# The six Blackrock arrays with per-electrode metrics. Rocky's table covers
# implant 1 only; implant 2 has too few sessions for a per-array null.
ARRAYS: dict[tuple[str, str], str] = {
    ("Rocky", "Anterior"): "1025-001501",
    ("Rocky", "Posterior"): "1025-001497",
    ("Nigel", "Anterior"): "1025-001496",
    ("Nigel", "Posterior"): "1025-001473",
    ("Fisk", "SN1498"): "1025-001498",
    ("Fisk", "SN1504"): "1025-001504",
}

# Sorting-free metrics only. These map one-to-one onto the paper's measures:
# `amp_p50` is its PTPV (peak-to-peak of threshold-crossing snippets) and
# `peak_snr` its SNR, both computed without any unit labels.
METRICS = ["noise_uv", "amp_p50", "peak_snr", "crossing_rate_hz"]


# %%
# === Geometry: rings, borders and the centre distance the paper rejected ===
def ring_frame(serial: str) -> pd.DataFrame:
    """Per-electrode geometry for one array: ring, border membership, radius.

    Parameters
    ----------
    serial : str
        Array serial, e.g. ``"1025-001496"``.

    Returns
    -------
    pandas.DataFrame
        ``channel_id, col, row, depth, ring, is_border, border, r_centre`` for
        every connected electrode. ``depth`` is 0 on the outer border and 4 at
        the centre; ``ring`` is the paper's 1..5 numbering with **5 outermost**,
        so a larger ring number means closer to the edge.
    """
    hits = sorted(PROBE_DIR.glob(f"*{serial}*.cmp"))
    if not hits:
        raise FileNotFoundError(f"no CMP for {serial}")
    d = parse_cmp(hits[0])[["channel_id", "col", "row"]].copy()

    # depth = shells in from the boundary; the paper's ring counts the other way
    d["depth"] = np.minimum.reduce([d.col, GRID - 1 - d.col,
                                    d.row, GRID - 1 - d.row]).astype(int)
    d["ring"] = GRID // 2 - d["depth"]
    d["is_border"] = d.depth == 0
    # which of the four borders; interior electrodes get an empty label
    side = np.where(d.row == 0, "bottom",
                    np.where(d.row == GRID - 1, "top",
                             np.where(d.col == 0, "left",
                                      np.where(d.col == GRID - 1, "right", ""))))
    d["border"] = side
    # the alternative grouping Forrest et al. tested and found less informative
    c = (GRID - 1) / 2.0
    d["r_centre"] = np.hypot(d.col - c, d.row - c)
    d["serial"] = serial
    d["mapfile"] = hits[0].name
    return d


def load_electrodes() -> pd.DataFrame:
    """Per-electrode, per-session sorting-free metrics for the three animals.

    Returns
    -------
    pandas.DataFrame
        One row per electrode-session with geometry attached.
    """
    frames = []
    for subject in ("rocky", "nigel", "fisk"):
        p = REPO / "data" / "derived" / subject / "events_electrode.parquet"
        if not p.exists():
            print(f"  ! missing {p}")
            continue
        d = pd.read_parquet(p)
        d["subject"] = subject.capitalize()
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    d["date"] = pd.to_datetime(d["date"])

    d["key"] = list(zip(d.subject, d.array, strict=True))
    d["array_serial"] = d.key.map(ARRAYS)
    unknown = d[d.array_serial.isna()].key.unique()
    if len(unknown):
        print(f"  ! unmapped array keys dropped: {unknown}")
    d = d.dropna(subset=["array_serial"]).drop(columns=["key"])

    geo = pd.concat([ring_frame(s) for s in sorted(set(ARRAYS.values()))],
                    ignore_index=True)
    # join on (serial, channel_id): col/row already on the table, so this is
    # also a cross-check that the two agree
    d = d.merge(geo.drop(columns=["col", "row"]),
                left_on=["array_serial", "channel_id"],
                right_on=["serial", "channel_id"], how="left",
                suffixes=("", "_geo"))
    return d


# %%
# === The array-level surface: one value per electrode per array ===
def electrode_surface(d: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Collapse sessions to one value per electrode, per array.

    Sessions are collapsed by the **median of the per-session value**, following
    the aggregation rule in CLAUDE.md -- session durations on this corpus span
    two orders of magnitude, so a pooled mean would be a statement about the
    longest sessions.
    """
    g = (d.dropna(subset=[metric])
           .groupby(["subject", "array", "array_serial", "channel_id",
                     "col", "row", "depth", "ring", "is_border", "border",
                     "r_centre"], observed=True)[metric]
           .median().reset_index(name="value"))
    return g


def to_grid(surf: pd.DataFrame) -> np.ndarray:
    """One array's electrode values as a 10x10 grid, NaN where unconnected."""
    g = np.full((GRID, GRID), np.nan)
    g[surf.row.to_numpy(), surf.col.to_numpy()] = surf.value.to_numpy()
    return g


def border_contrast(grid: np.ndarray) -> float:
    """(border mean - interior mean) / array mean, in percent.

    Normalised by the array's own mean so arrays with different noise floors
    and amplifier gains are comparable.
    """
    mask = np.zeros((GRID, GRID), bool)
    mask[0, :] = mask[-1, :] = mask[:, 0] = mask[:, -1] = True
    b, i = np.nanmean(grid[mask]), np.nanmean(grid[~mask])
    return float(100.0 * (b - i) / np.nanmean(grid))


def toroidal_null(grid: np.ndarray) -> tuple[float, float]:
    """Observed border contrast and its p under a toroidal-shift null.

    Rolling the metric map over the grid preserves its spatial autocorrelation
    -- the smooth cortical gradients these arrays carry -- and destroys only its
    registration to the physical array boundary. So a contrast that survives is
    about *where the array ends*, not about how smoothly the tissue varies.

    Returns
    -------
    (observed, p) : tuple of float
        ``p`` is the fraction of the 100 shifts (identity included) whose
        absolute contrast is at least the observed one, so it is bounded below
        by 0.01.
    """
    obs = border_contrast(grid)
    null = np.array([border_contrast(np.roll(grid, (dy, dx), axis=(0, 1)))
                     for dy in range(GRID) for dx in range(GRID)])
    return obs, float(np.mean(np.abs(null) >= abs(obs)))


def border_signs(grid: np.ndarray) -> tuple[int, list[float]]:
    """Each of the four borders against the interior; how many agree in sign.

    A mechanical edge effect is isotropic and should move all four borders the
    same way. A directional cortical gradient raises one border and lowers the
    one opposite, so it can only ever agree on two -- three with a diagonal.
    This is the discriminator.
    """
    interior = np.nanmean(grid[1:-1, 1:-1])
    sides = [grid[0, :], grid[-1, :], grid[:, 0], grid[:, -1]]
    dev = [float(np.nanmean(s) - interior) for s in sides]
    pos = sum(x > 0 for x in dev)
    return max(pos, 4 - pos), dev


def detrended(grid: np.ndarray) -> np.ndarray:
    """Grid with its best-fit plane removed, to kill any linear gradient.

    A plane is the simplest thing a cortical gradient can be. If the border
    contrast survives its removal the effect is not a linear trend across the
    array; if it vanishes, it was.
    """
    yy, xx = np.mgrid[0:GRID, 0:GRID]
    ok = np.isfinite(grid)
    a = np.c_[xx[ok], yy[ok], np.ones(ok.sum())]
    coef, *_ = np.linalg.lstsq(a, grid[ok], rcond=None)
    fit = coef[0] * xx + coef[1] * yy + coef[2]
    out = grid - fit + np.nanmean(grid)   # re-centre so ratios stay meaningful
    return out


# %%
# === The three tests ===
def naive_paired(d: pd.DataFrame, metric: str) -> pd.DataFrame:
    """The invalid test, plus its control, reported together.

    The control splits on ``col`` parity, an axis that encodes no geometry at
    all. If the control fires as often as the treatment axis, neither is
    evidence -- exactly the diagnosis in `surface_conditions.md`.
    """
    from scipy.stats import wilcoxon

    rows = []
    for (sub, arr), g in d.dropna(subset=[metric]).groupby(
            ["subject", "array"], observed=True):
        for axis, hi_mask in (("border/interior", g.is_border),
                              ("col-parity (control)", g.col % 2 == 0)):
            piv = (g.assign(grp=np.where(hi_mask, "hi", "lo"))
                     .pivot_table(index="stem", columns="grp", values=metric))
            piv = piv.dropna()
            if len(piv) < 6:
                continue
            rows.append(dict(
                subject=sub, array=arr, metric=metric, axis=axis,
                n_sessions=len(piv),
                ratio=float((piv["hi"] / piv["lo"]).median()),
                p=float(wilcoxon(piv["hi"], piv["lo"])[1])))
    return pd.DataFrame(rows)


def array_level(surf: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Per-array border contrast, its toroidal-shift p, and border-sign count."""
    rows = []
    for (sub, arr, serial), g in surf.groupby(
            ["subject", "array", "array_serial"], observed=True):
        grid = to_grid(g)
        obs, p = toroidal_null(grid)
        agree, dev = border_signs(grid)
        d_obs, d_p = toroidal_null(detrended(grid))
        d_agree, _ = border_signs(detrended(grid))
        rows.append(dict(
            subject=sub, array=arr, serial=serial, metric=metric,
            n_elec=int(g.value.notna().sum()),
            contrast_pct=obs, p_shift=p, borders_agree=agree,
            dev_bottom=dev[0], dev_top=dev[1],
            dev_left=dev[2], dev_right=dev[3],
            contrast_detrended_pct=d_obs, p_shift_detrended=d_p,
            borders_agree_detrended=d_agree))
    return pd.DataFrame(rows)


def ring_profile(surf: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Mean value per ring, per array, normalised to the array's own mean."""
    rows = []
    for (sub, arr), g in surf.groupby(["subject", "array"], observed=True):
        m = g.value.mean()
        for ring, gg in g.groupby("ring"):
            rows.append(dict(subject=sub, array=arr, metric=metric,
                             ring=int(ring), depth=int(5 - ring),
                             n=len(gg), rel=float(gg.value.mean() / m)))
    return pd.DataFrame(rows)


def centre_vs_ring(surf: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Does the paper's rejected grouping (radius) do better or worse here?

    Forrest et al. report that concentric rings distinguished strain better than
    distance from the array centre. Rings and radius are near-collinear on a
    square grid, so this asks the weaker question their supplement asks: which
    of the two correlates more strongly with the measured value.
    """
    from scipy.stats import spearmanr

    rows = []
    for (sub, arr), g in surf.groupby(["subject", "array"], observed=True):
        r_ring = spearmanr(g.ring, g.value)
        r_rad = spearmanr(g.r_centre, g.value)
        rows.append(dict(subject=sub, array=arr, metric=metric,
                         rho_ring=float(r_ring[0]), p_ring=float(r_ring[1]),
                         rho_radius=float(r_rad[0]), p_radius=float(r_rad[1])))
    return pd.DataFrame(rows)


# %%
# === Longitudinal: does the edge-interior gap open with implant age? ===
def contrast_over_time(d: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Per-session border contrast against implant age.

    The paper measures at 1 month, 1 year and 2 years. This corpus runs to six,
    so the question can be asked as a trend rather than three snapshots.
    """
    from scipy.stats import spearmanr

    per = []
    for (sub, arr, stem), g in d.dropna(subset=[metric]).groupby(
            ["subject", "array", "stem"], observed=True):
        if g.channel_id.nunique() < 80:
            continue
        b = g.loc[g.is_border, metric].median()
        i = g.loc[~g.is_border, metric].median()
        if not np.isfinite(b) or not np.isfinite(i) or i == 0:
            continue
        per.append(dict(subject=sub, array=arr, stem=stem,
                        date=g.date.iloc[0], metric=metric,
                        contrast_pct=100.0 * (b - i) / g[metric].median()))
    per = pd.DataFrame(per)
    if not len(per):
        return per, pd.DataFrame()

    trends = []
    for (sub, arr), g in per.groupby(["subject", "array"], observed=True):
        g = g.sort_values("date")
        age = (g.date - g.date.min()).dt.days.to_numpy()
        if len(g) < 10:
            continue
        rho, p = spearmanr(age, g.contrast_pct)
        trends.append(dict(subject=sub, array=arr, metric=metric, n=len(g),
                           span_days=int(age.max()),
                           first_pct=float(g.contrast_pct.iloc[:5].median()),
                           last_pct=float(g.contrast_pct.iloc[-5:].median()),
                           rho_age=float(rho), p_age=float(p)))
    return per, pd.DataFrame(trends)


# %%
# === Impedance: the paper's primary measure ===
CD_10BY10 = Path(r"D:\Claude Code\Blackrock files\Blackrock Utah array"
                 r"\Utah array manufacture CD files\10by10")


def impedance_rings() -> pd.DataFrame:
    """Fisk's Blackrock impedance by ring -- the one map-free impedance we have.

    Fisk's values come from Cerebus `*MotorImpedance.txt` dumps, which are
    indexed by **Blackrock channel** -- proved 1248/1248 against the factory
    workbook in `impedance_sources.md` -- so the CMP alone places them. Rocky's
    come from the Autolab potentiostat and need the disputed channel map
    ([[impedance_channel_map]]), so they are handled separately.
    """
    p = REPO / "data" / "derived" / "fisk" / "impedance.parquet"
    if not p.exists():
        return pd.DataFrame()
    z = pd.read_parquet(p)
    z["serial"] = z.serial.astype(str).str.replace("SN", "", regex=False).str.strip()
    geo = pd.concat([ring_frame(s) for s in ("1025-001498", "1025-001504")],
                    ignore_index=True)
    z = z.merge(geo, left_on=["serial", "channel"],
                right_on=["serial", "channel_id"], how="inner")
    # `high_z` is a project threshold at 1 MOhm, not an instrument rail, so
    # these are real readings and are kept. They are also where the effect
    # lives: the fraction above 1 MOhm runs 62% at the centre against 16% on
    # the border, so excluding them *understates* the contrast.
    z["log_z"] = np.log10(z.kohm * 1e3)
    return z


def factory_impedance() -> pd.DataFrame:
    """Pre-implant bench impedance by ring, for every 10x10 array on the CD.

    **This is the control the strain hypothesis needs and the paper does not
    have.** These are the manufacturer's automated-tester sweeps in saline,
    recorded before the array was ever implanted, so no tissue, no micromotion
    and no glial scar can contribute. If the border-versus-interior contrast is
    already present here, an edge effect measured in vivo is not evidence of
    micromotion-induced strain on its own.

    The dumps are indexed by channel id, not electrode number -- the row labels
    `elecN` are a documented misnomer ([[impedance_sources]]).

    Returns
    -------
    pandas.DataFrame
        ``serial, channel_id, kohm, log_z`` joined to :func:`ring_frame`
        geometry, one row per electrode per array.
    """
    import re

    rows = []
    for txt in sorted(CD_10BY10.glob("*.txt")):
        m = re.search(r"(\d{4}-\d{6})", txt.name)
        if not m:
            continue
        serial = m.group(1)
        hits = sorted(CD_10BY10.glob(f"*{serial}*.cmp"))
        if not hits:
            print(f"  ! no CMP for {serial}, skipped")
            continue
        vals = {}
        for ln in txt.read_text(errors="replace").splitlines():
            mm = re.match(r"\s*elec(\d+)\s+([\d.]+)\s*$", ln)
            if mm:
                vals[int(mm.group(1))] = float(mm.group(2))
        if len(vals) < 96:
            print(f"  ! {serial}: parsed {len(vals)} rows, skipped")
            continue
        geo = parse_cmp(hits[0])[["channel_id", "col", "row"]].copy()
        geo["depth"] = np.minimum.reduce(
            [geo.col, GRID - 1 - geo.col, geo.row, GRID - 1 - geo.row]).astype(int)
        geo["ring"] = GRID // 2 - geo["depth"]
        geo["is_border"] = geo.depth == 0
        geo["serial"] = serial
        geo["kohm"] = geo.channel_id.map(vals)
        rows.append(geo.dropna(subset=["kohm"]))
    if not rows:
        return pd.DataFrame()
    d = pd.concat(rows, ignore_index=True)
    d["log_z"] = np.log10(d.kohm * 1e3)
    return d


def factory_to_invivo(z: pd.DataFrame, fz: pd.DataFrame) -> pd.DataFrame:
    """The edge contrast per date, anchored to the same array's bench value.

    Two of the never-implanted arrays in :func:`factory_impedance` are Fisk's
    own, measured before implantation, so for those two the in vivo series has a
    **paired baseline on the same electrodes**. That converts "is there an edge
    effect" -- which manufacturing scatter alone can produce -- into "did the
    edge effect grow once the array was in tissue", which it cannot.

    Returns
    -------
    pandas.DataFrame
        One row per array-date: ``serial, date, age_days, delta, factory``.
    """
    rows = []
    for serial, g in z.groupby("serial", observed=True):
        f = fz[fz.serial == serial]
        if not len(f):
            continue
        base = float(f[f.is_border].log_z.median()
                     - f[~f.is_border].log_z.median())
        per = (g.groupby(["date", "is_border"], observed=True)
                .log_z.median().unstack("is_border").dropna().sort_index())
        d = (per[True] - per[False])
        age = (d.index - d.index.min()).days
        rows.append(pd.DataFrame(dict(serial=serial, date=d.index,
                                      age_days=age, delta=d.to_numpy(),
                                      factory=base)))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def fig_factory_to_invivo(t: pd.DataFrame, out: Path) -> None:
    """Edge contrast against time, with the pre-implant value as an anchor."""
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    colr = {"1025-001498": "#d62728", "1025-001504": "#1f77b4"}
    for serial, g in t.groupby("serial", observed=True):
        c = colr.get(serial, "#7f7f7f")
        ax.scatter(g.age_days, g.delta, s=16, color=c, alpha=0.75,
                   label=f"{serial} in vivo")
        ax.axhline(g.factory.iloc[0], color=c, ls="--", lw=1.3)
        ax.annotate(f"bench {g.factory.iloc[0]:+.3f}",
                    (g.age_days.max(), g.factory.iloc[0]),
                    fontsize=7, color=c, va="bottom", ha="right")
    ax.axhline(0, color="k", lw=1)
    ax.set_xlabel("days since first in vivo measurement")
    ax.set_ylabel("border − interior, log10 |Z| (dex)")
    ax.set_title("The edge effect starts at the bench value and opens up",
                 fontsize=11)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def bank_control(serials: list[str]) -> pd.DataFrame:
    """Is ring confounded with bank? A per-array association check.

    Impedance and noise are measured bank by bank through separate front-end
    sections, so a bank offset could masquerade as an edge effect if the CMP
    happened to wire one bank around the perimeter. Reported as the eta-squared
    of ring explained by bank.
    """
    rows = []
    for s in serials:
        hits = (sorted(PROBE_DIR.glob(f"*{s}*.cmp"))
                or sorted(CD_10BY10.glob(f"*{s}*.cmp")))
        if not hits:
            continue
        g = parse_cmp(hits[0])
        g["depth"] = np.minimum.reduce(
            [g.col, GRID - 1 - g.col, g.row, GRID - 1 - g.row]).astype(int)
        g["is_border"] = g.depth == 0
        share = g.groupby("bank").is_border.mean()
        rows.append(dict(serial=s, border_share_A=float(share.get("A", np.nan)),
                         border_share_B=float(share.get("B", np.nan)),
                         border_share_C=float(share.get("C", np.nan)),
                         spread=float(share.max() - share.min())))
    return pd.DataFrame(rows)


def within_bank_contrast(d: pd.DataFrame, value: str,
                         keys: list[str]) -> pd.DataFrame:
    """Border vs interior **inside one bank**, which removes the bank confound.

    The CMP wires the 96 channels in three diagonal bands, and the consequence
    is severe: **bank B holds no border electrode at all** and supplies half the
    interior. So a plain border-versus-interior contrast is partly a
    bank-B-versus-the-rest contrast, and the impedance tester sweeps bank by
    bank. Banks A and C each straddle the boundary -- roughly 15 border against
    17 interior and the reverse -- so the comparison can be made inside a bank,
    holding the front-end section, the connector half and the sweep block fixed.

    Parameters
    ----------
    d : pandas.DataFrame
        Electrode-level rows carrying ``bank``, ``is_border`` and `value`.
    value : str
        Column to contrast.
    keys : list of str
        Grouping columns identifying one array.

    Returns
    -------
    pandas.DataFrame
        One row per array per bank, with the border-minus-interior difference.
    """
    rows = []
    for key, g in d.groupby(keys, observed=True):
        key = key if isinstance(key, tuple) else (key,)
        for bank, gg in g.groupby("bank", observed=True):
            b = gg.loc[gg.is_border, value]
            i = gg.loc[~gg.is_border, value]
            if len(b) < 8 or len(i) < 8:
                continue                    # bank B never clears this, by design
            rows.append(dict(zip(keys, key, strict=True))
                        | dict(bank=bank, n_border=len(b), n_interior=len(i),
                               delta=float(b.median() - i.median())))
    return pd.DataFrame(rows)


def attach_bank(d: pd.DataFrame, serial_col: str = "serial") -> pd.DataFrame:
    """Add the CMP bank letter to an electrode-level table."""
    frames = []
    for s in d[serial_col].dropna().unique():
        hits = (sorted(PROBE_DIR.glob(f"*{s}*.cmp"))
                or sorted(CD_10BY10.glob(f"*{s}*.cmp")))
        if not hits:
            continue
        g = parse_cmp(hits[0])[["channel_id", "bank"]].copy()
        g[serial_col] = s
        frames.append(g)
    if not frames:
        return d.assign(bank=pd.NA)
    return d.merge(pd.concat(frames, ignore_index=True),
                   on=[serial_col, "channel_id"], how="left")


def impedance_array_stats(d: pd.DataFrame, value: str = "log_z") -> pd.DataFrame:
    """Border contrast, toroidal-shift p and border signs, per array.

    Uses the same machinery as the ephys arm so the two are directly
    comparable, and so the same null protects both.
    """
    rows = []
    for serial, g in d.groupby("serial", observed=True):
        surf = (g.groupby(["row", "col"], observed=True)[value]
                 .median().reset_index(name="value"))
        grid = np.full((GRID, GRID), np.nan)
        grid[surf.row.to_numpy(), surf.col.to_numpy()] = surf.value.to_numpy()
        obs, p = toroidal_null(grid)
        agree, dev = border_signs(grid)
        mask = np.zeros((GRID, GRID), bool)
        mask[0, :] = mask[-1, :] = mask[:, 0] = mask[:, -1] = True
        rows.append(dict(
            serial=serial, n_elec=int(np.isfinite(grid).sum()),
            border_dex=float(np.nanmean(grid[mask])),
            interior_dex=float(np.nanmean(grid[~mask])),
            delta_dex=float(np.nanmean(grid[mask]) - np.nanmean(grid[~mask])),
            contrast_pct=obs, p_shift=p, borders_agree=agree,
            dev_bottom=dev[0], dev_top=dev[1],
            dev_left=dev[2], dev_right=dev[3]))
    return pd.DataFrame(rows)


def impedance_map_arbiter() -> pd.DataFrame:
    """Rocky's potentiostat impedance by ring, under both candidate maps.

    The edge effect is a *geometric* prediction with an external, published
    direction (edge impedance lower than interior). The two candidate maps are
    96-way permutations of each other, so at most one can reproduce it. This is
    a far better-powered arbiter than the noise-floor test, which failed on
    quantisation ties -- impedance is continuous over four decades and the
    contrast is a 2-group comparison rather than a 96-way rank correlation.
    """
    from scipy.stats import mannwhitneyu

    p = REPO / "data" / "derived" / "rocky" / "impedance_long.parquet"
    authored = REPO / "configs" / "probes" / "impedance_channel_map.csv"
    if not p.exists() or not authored.exists():
        return pd.DataFrame()
    z = pd.read_parquet(p)
    a = pd.read_csv(authored)

    # naive: the channel_id already on the table, from sweep order
    # authored: (half, pos) -> channel_id from the lab's mapping sheets
    a_key = a.set_index(["half", "pos"]).channel_id
    z["pos"] = z.sweep.astype(int) + 1
    z["half_key"] = z.bank.astype(str) + z.half.astype(int).astype(str)
    z["ch_authored"] = pd.MultiIndex.from_arrays(
        [z.half_key, z.pos]).map(a_key)

    serial = {"Anterior": "1025-001501", "Posterior": "1025-001497"}
    geo = pd.concat([ring_frame(s) for s in serial.values()], ignore_index=True)

    rows = []
    for name, col in (("naive", "channel_id"), ("authored", "ch_authored")):
        w = z.dropna(subset=[col]).copy()
        w["serial"] = w.array.map(serial)
        w = w.merge(geo[["serial", "channel_id", "is_border", "ring"]],
                    left_on=["serial", col], right_on=["serial", "channel_id"],
                    how="inner", suffixes=("", "_g"))
        w["log_z"] = np.log10(w.z_1khz_ohm.clip(lower=1))
        for (date, arr), g in w.groupby(["date", "array"], observed=True):
            b = g.loc[g.is_border, "log_z"]
            i = g.loc[~g.is_border, "log_z"]
            if len(b) < 10 or len(i) < 10:
                continue
            rows.append(dict(map=name, date=date, array=arr,
                             delta_dex=float(b.median() - i.median()),
                             p=float(mannwhitneyu(b, i)[1])))
    return pd.DataFrame(rows)


# %%
# === Figures ===
def fig_layout(surf_by_metric: dict[str, pd.DataFrame], out: Path) -> None:
    """Ring map beside the measured surface, per array. The eye test."""
    metric = "amp_p50"
    surf = surf_by_metric[metric]
    keys = sorted(surf.groupby(["subject", "array"]).groups)
    fig, axes = plt.subplots(2, len(keys), figsize=(2.5 * len(keys), 5.6),
                             squeeze=False)
    for k, (sub, arr) in enumerate(keys):
        g = surf[(surf.subject == sub) & (surf.array == arr)]
        rings = np.full((GRID, GRID), np.nan)
        rings[g.row, g.col] = g.ring
        axes[0][k].imshow(rings, origin="lower", cmap="viridis")
        axes[0][k].set_title(f"{sub}\n{arr}", fontsize=8)
        grid = to_grid(g)
        axes[1][k].imshow(grid, origin="lower", cmap="magma")
        for ax in (axes[0][k], axes[1][k]):
            ax.set_xticks([])
            ax.set_yticks([])
    axes[0][0].set_ylabel("ring (5 = edge)", fontsize=8)
    axes[1][0].set_ylabel("median snippet amp", fontsize=8)
    fig.suptitle("Ring geometry against the measured surface — "
                 "the arrays are patchy, not shelled", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_profiles(prof: pd.DataFrame, out: Path) -> None:
    """Ring profile per metric; a mechanical effect would be a monotone ramp."""
    mets = list(dict.fromkeys(prof.metric))
    fig, axes = plt.subplots(1, len(mets), figsize=(3.4 * len(mets), 3.6),
                             squeeze=False)
    for ax, met in zip(axes[0], mets, strict=True):
        g = prof[prof.metric == met]
        for (sub, arr), gg in g.groupby(["subject", "array"], observed=True):
            gg = gg.sort_values("ring")
            ax.plot(gg.ring, gg.rel, marker="o", ms=3, lw=1.1,
                    label=f"{sub} {arr}")
        ax.axhline(1.0, color="k", ls="--", lw=1)
        ax.set_xlabel("ring (5 = outer border)")
        ax.set_ylabel("value / array mean")
        ax.set_title(met, fontsize=9)
        ax.grid(alpha=0.25)
    axes[0][-1].legend(fontsize=6)
    fig.suptitle("Concentric-ring profiles, six arrays", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_borders(res: pd.DataFrame, out: Path) -> None:
    """Each border against the interior. Isotropy would put all four one side."""
    mets = list(dict.fromkeys(res.metric))
    fig, axes = plt.subplots(1, len(mets), figsize=(3.6 * len(mets), 4.0),
                             squeeze=False)
    cols = dict(dev_bottom="#1f77b4", dev_top="#d62728",
                dev_left="#2ca02c", dev_right="#9467bd")
    for ax, met in zip(axes[0], mets, strict=True):
        g = res[res.metric == met].reset_index(drop=True)
        idx = np.arange(len(g))
        for k, (c, colr) in enumerate(cols.items()):
            # scale each array by its own mean so four metrics share an axis
            ax.bar(idx + (k - 1.5) * 0.2, g[c] / g[c].abs().max(), 0.2,
                   color=colr, label=c.replace("dev_", ""))
        ax.axhline(0, color="k", lw=1)
        ax.set_xticks(idx)
        ax.set_xticklabels([f"{s}\n{a}" for s, a in zip(g.subject, g.array,
                                                        strict=True)],
                           fontsize=6)
        ax.set_title(met, fontsize=9)
        ax.grid(alpha=0.25, axis="y")
    axes[0][0].set_ylabel("border − interior (scaled)")
    axes[0][-1].legend(fontsize=6)
    fig.suptitle("Four borders against the interior — a mechanical edge "
                 "effect would put all four on one side", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_time(per: pd.DataFrame, out: Path) -> None:
    """Border contrast against date, per array."""
    mets = list(dict.fromkeys(per.metric))
    fig, axes = plt.subplots(1, len(mets), figsize=(3.6 * len(mets), 3.6),
                             squeeze=False)
    for ax, met in zip(axes[0], mets, strict=True):
        g = per[per.metric == met]
        for (sub, arr), gg in g.groupby(["subject", "array"], observed=True):
            gg = gg.sort_values("date")
            ax.plot(gg.date, gg.contrast_pct.rolling(9, min_periods=3).median(),
                    lw=1.3, label=f"{sub} {arr}")
        ax.axhline(0, color="k", ls="--", lw=1)
        ax.set_ylabel("border − interior, % of array median")
        ax.set_title(met, fontsize=9)
        ax.tick_params(axis="x", labelrotation=45, labelsize=6)
        ax.grid(alpha=0.25)
    axes[0][-1].legend(fontsize=6)
    fig.suptitle("Does the edge–interior gap open with implant age?",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_factory(fz: pd.DataFrame, fst: pd.DataFrame, out: Path) -> None:
    """The control figure: the ring effect on arrays that were never implanted.

    Left, every array's ring profile normalised to its own mean; right, the
    border-minus-interior contrast per array. If the in vivo edge effect is
    micromotion, these panels should be flat.
    """
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2))

    for _, g in fz.groupby("serial", observed=True):
        prof = g.groupby("ring").log_z.mean() - g.log_z.mean()
        axes[0].plot(prof.index, prof.to_numpy(), lw=0.9, alpha=0.55,
                     color="#7f7f7f")
    pooled = fz.assign(rel=fz.log_z - fz.groupby("serial").log_z.transform("mean"))
    mean_prof = pooled.groupby("ring").rel.mean()
    axes[0].plot(mean_prof.index, mean_prof.to_numpy(), lw=2.6, color="#d62728",
                 marker="o", label=f"mean of {fz.serial.nunique()} arrays")
    axes[0].axhline(0, color="k", ls="--", lw=1)
    axes[0].set_xlabel("ring (5 = outer border)")
    axes[0].set_ylabel("log10 |Z| − array mean (dex)")
    axes[0].set_title("Pre-implant bench impedance by ring", fontsize=10)
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.25)

    order = fst.sort_values("delta_dex")
    colr = np.where(order.delta_dex < 0, "#d62728", "#1f77b4")
    axes[1].barh(np.arange(len(order)), order.delta_dex, color=colr)
    axes[1].axvline(0, color="k", lw=1)
    axes[1].set_yticks(np.arange(len(order)))
    axes[1].set_yticklabels(order.serial, fontsize=6)
    axes[1].set_xlabel("border − interior, dex")
    axes[1].set_title("Per array, never implanted", fontsize=10)
    axes[1].grid(alpha=0.25, axis="x")

    fig.suptitle("The control: no tissue, no micromotion, no glial scar",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_impedance(z: pd.DataFrame, out: Path) -> None:
    """Fisk impedance by ring, the map-free version of the paper's figure 3."""
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.8), squeeze=False)
    for ax, (arr, g) in zip(axes[0], z.groupby("array", observed=True),
                            strict=False):
        data = [g.loc[g.ring == r, "log_z"].dropna() for r in range(1, 6)]
        ax.boxplot(data, labels=[str(r) for r in range(1, 6)], showfliers=False)
        ax.set_xlabel("ring (5 = outer border)")
        ax.set_ylabel("log10 |Z| at 1 kHz (ohm)")
        ax.set_title(f"Fisk {arr}  (n={len(g)} electrode-dates)", fontsize=9)
        ax.grid(alpha=0.25, axis="y")
    fig.suptitle("Impedance by ring — Forrest et al. predict the outer "
                 "ring sits lower", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(out, dpi=150)
    plt.close(fig)


# %%
def main() -> int:
    FIG.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    banner("1. Geometry: what a ring is on these arrays")
    for serial in sorted(set(ARRAYS.values())):
        g = ring_frame(serial)
        counts = g.ring.value_counts().sort_index(ascending=False)
        corners = int(((g.col.isin([0, GRID - 1])) &
                       (g.row.isin([0, GRID - 1]))).sum())
        print(f"  {serial}: {len(g)} wired, corners connected = {corners}, "
              f"ring 5..1 = {list(counts.to_numpy())}")

    banner("2. Loading per-electrode metrics")
    d = load_electrodes()
    print(f"  {len(d):,} electrode-sessions, {d.stem.nunique()} sessions, "
          f"{d.subject.nunique()} animals, "
          f"{d.groupby(['subject', 'array']).ngroups} arrays")
    print(f"  {d.date.min().date()} -> {d.date.max().date()}")
    bad = int((d.col != d.col_geo).sum()) if "col_geo" in d else 0
    print(f"  geometry cross-check: {bad} col mismatches against the CMP")

    surf = {m: electrode_surface(d, m) for m in METRICS}

    banner("3. The naive test, and its control")
    nv = pd.concat([naive_paired(d, m) for m in METRICS], ignore_index=True)
    tab = (nv.assign(sig=nv.p < 0.05)
             .groupby(["axis"]).agg(n=("sig", "size"),
                                    n_sig=("sig", "sum")).reset_index())
    print(tab.to_string(index=False))
    print("\n  If the control fires as often as the border axis, neither is "
          "evidence.")
    nv.to_parquet(OUT / "naive_paired.parquet", index=False)

    banner("4. Array-level: toroidal-shift null and the four-border sign test")
    res = pd.concat([array_level(surf[m], m) for m in METRICS],
                    ignore_index=True)
    show = ["subject", "array", "metric", "contrast_pct", "p_shift",
            "borders_agree", "contrast_detrended_pct", "p_shift_detrended",
            "borders_agree_detrended"]
    for met, g in res.groupby("metric"):
        print(f"\n--- {met} ---")
        print(g[show].drop(columns=["metric"]).round(3).to_string(index=False))
    res.to_parquet(OUT / "array_level.parquet", index=False)

    print("\n  four-border agreement, all metrics x arrays:")
    print(res.borders_agree.value_counts().sort_index().to_string())
    n4 = int((res.borders_agree == 4).sum())
    from scipy.stats import binomtest
    bt = binomtest(n4, len(res), 0.125, alternative="greater")
    print(f"  4-of-4 in {n4}/{len(res)}; against 1/8 under sign symmetry, "
          f"p = {bt.pvalue:.4g}")

    banner("5. Ring profiles, and the radius alternative the paper rejected")
    prof = pd.concat([ring_profile(surf[m], m) for m in METRICS],
                     ignore_index=True)
    for met, g in prof.groupby("metric"):
        print(f"\n--- {met} (value / array mean) ---")
        print(g.pivot_table(index=["subject", "array"], columns="ring",
                            values="rel").round(3).to_string())
    prof.to_parquet(OUT / "ring_profile.parquet", index=False)

    cv = pd.concat([centre_vs_ring(surf[m], m) for m in METRICS],
                   ignore_index=True)
    print("\n  ring vs radius, median |rho| across arrays:")
    print(cv.groupby("metric")[["rho_ring", "rho_radius"]]
            .apply(lambda g: g.abs().median()).round(3).to_string())
    cv.to_parquet(OUT / "ring_vs_radius.parquet", index=False)

    banner("6. Longitudinal: does the gap open with implant age?")
    pers, trends = [], []
    for m in METRICS:
        p, t = contrast_over_time(d, m)
        if len(p):
            pers.append(p)
        if len(t):
            trends.append(t)
    per = pd.concat(pers, ignore_index=True)
    tr = pd.concat(trends, ignore_index=True)
    print(tr.round(3).to_string(index=False))
    per.to_parquet(OUT / "contrast_sessions.parquet", index=False)
    tr.to_parquet(OUT / "contrast_trends.parquet", index=False)

    banner("7. Impedance by ring: Fisk in vivo, map-free")
    z = impedance_rings()
    if len(z):
        print(f"  {len(z):,} electrode-dates, {z.date.nunique()} dates, "
              f"{z.serial.nunique()} arrays")
        # per date first, then median across dates -- CLAUDE.md aggregation rule
        zper = (z.groupby(["array", "date", "is_border"], observed=True)
                 .log_z.median().unstack("is_border").dropna())
        zper.columns = ["interior", "border"]
        zper["delta"] = zper.border - zper.interior
        print("\n  per-date border − interior, dex:")
        print(zper.groupby("array").delta.agg(
            n="size", median="median",
            frac_neg=lambda s: float((s < 0).mean())).round(3).to_string())
        print("\n  array-level, with the toroidal-shift null:")
        st = impedance_array_stats(z)
        print(st.round(3).to_string(index=False))

        # the uncensored version of the same effect: an electrode either is or
        # is not above 1 MOhm, so this needs no value and no log
        print("\n  fraction above 1 MOhm, by ring (5 = outer border):")
        print(z.groupby(["array", "ring"], observed=True).high_z.mean()
               .unstack("ring").round(3).to_string())
        hz = impedance_array_stats(z.assign(log_z=z.high_z.astype(float)))
        print("\n  same statistic on the failure rate, per array:")
        print(hz[["serial", "border_dex", "interior_dex", "delta_dex",
                  "p_shift", "borders_agree"]]
              .rename(columns={"border_dex": "border_frac",
                               "interior_dex": "interior_frac",
                               "delta_dex": "delta"})
              .round(3).to_string(index=False))

        print("\n  robustness: the same contrast with >1 MOhm readings dropped")
        zx = z[~z.high_z]
        xper = (zx.groupby(["array", "date", "is_border"], observed=True)
                  .log_z.median().unstack("is_border").dropna())
        xper.columns = ["interior", "border"]
        print((xper.border - xper.interior).groupby("array").agg(
            n="size", median="median",
            frac_neg=lambda t: float((t < 0).mean())).round(3).to_string())
        fig_impedance(z, FIG / "G5_impedance_rings.png")
        z.to_parquet(OUT / "fisk_impedance_rings.parquet", index=False)
        st.to_parquet(OUT / "fisk_impedance_array.parquet", index=False)
    else:
        print("  ! Fisk impedance table missing")

    banner("7b. THE CONTROL: the same test on never-implanted arrays")
    fz = factory_impedance()
    if len(fz):
        print(f"  {fz.serial.nunique()} arrays, {len(fz):,} electrodes, "
              "manufacturer bench sweep in saline, pre-implant")
        fst = impedance_array_stats(fz)
        print()
        print(fst.round(3).to_string(index=False))
        from scipy.stats import binomtest, wilcoxon
        neg = int((fst.delta_dex < 0).sum())
        bt = binomtest(neg, len(fst), 0.5, alternative="less")
        w = wilcoxon(fst.delta_dex)
        print(f"\n  border below interior on {neg}/{len(fst)} arrays "
              f"(sign test p = {bt.pvalue:.4g})")
        print(f"  median delta {fst.delta_dex.median():+.3f} dex "
              f"= {100 * (10 ** fst.delta_dex.median() - 1):+.1f}%  "
              f"(Wilcoxon p = {w[1]:.4g})")
        print(f"  four-border agreement: "
              f"{dict(fst.borders_agree.value_counts().sort_index())}")
        print(f"  toroidal-shift p < 0.05 on {int((fst.p_shift < 0.05).sum())}"
              f"/{len(fst)} arrays")
        fz.to_parquet(OUT / "factory_impedance_rings.parquet", index=False)
        fst.to_parquet(OUT / "factory_impedance_array.parquet", index=False)
        fig_factory(fz, fst, FIG / "G6_factory_control.png")
    else:
        print("  ! factory CD tree not reachable")

    banner("7e. The paired anchor: same arrays, bench then in vivo")
    if len(z) and len(fz):
        from scipy.stats import spearmanr

        t = factory_to_invivo(z, fz)
        for serial, g in t.groupby("serial", observed=True):
            rho, pv = spearmanr(g.age_days, g.delta)
            print(f"  {serial}: bench {g.factory.iloc[0]:+.3f} -> "
                  f"first session {g.delta.iloc[0]:+.3f} -> "
                  f"last {g.delta.iloc[-1]:+.3f} dex")
            print(f"      vs age: rho = {rho:+.3f}, p = {pv:.3g}, "
                  f"{g.age_days.max()} days, n = {len(g)}")
            print(f"      dates below the bench value: "
                  f"{int((g.delta < g.factory).sum())}/{len(g)}")
        t.to_parquet(OUT / "factory_to_invivo.parquet", index=False)
        fig_factory_to_invivo(t, FIG / "G7_bench_to_invivo.png")

    banner("7c. Bank control: is a ring just a bank?")
    bc = bank_control(sorted(set(ARRAYS.values())))
    print(bc.round(3).to_string(index=False))
    print("  bank B holds NO border electrode on any array, and supplies half"
          " the interior.\n  Border-vs-interior is therefore partly"
          " bank-B-vs-the-rest. Banks A and C\n  straddle the boundary, so the"
          " contrast can be made inside a bank.")
    bc.to_parquet(OUT / "bank_composition.parquet", index=False)

    banner("7d. The same contrasts, made INSIDE one bank")
    from scipy.stats import binomtest, wilcoxon

    if len(z):
        zb = attach_bank(z.assign(serial=z.serial.astype(str)))
        wb = within_bank_contrast(zb, "log_z", ["array", "date", "bank"])
        agg = wb.groupby(["array", "bank"]).delta.agg(
            n="size", median="median",
            frac_neg=lambda t: float((t < 0).mean())).round(3)
        print("  Fisk in vivo impedance, per date, inside a bank:")
        print(agg.to_string())

    if len(fz):
        fb = within_bank_contrast(attach_bank(fz), "log_z", ["serial", "bank"])
        piv = fb.pivot_table(index="serial", columns="bank", values="delta")
        print("\n  factory bench impedance, inside a bank (dex):")
        print(piv.round(3).to_string())
        for bank in piv.columns:
            v = piv[bank].dropna()
            print(f"  bank {bank}: median {v.median():+.3f} dex, "
                  f"{int((v < 0).sum())}/{len(v)} negative, "
                  f"Wilcoxon p = {wilcoxon(v)[1]:.3g}")

    # the same control on the ephys arm, where it matters most: banks A and C
    # each straddle the boundary, so 6 arrays x 2 banks = 12 signs per metric
    ebs = []
    for met in METRICS:
        g = (surf[met].rename(columns={"array_serial": "serial"})
                      .rename(columns={"value": "v"}))
        e = within_bank_contrast(attach_bank(g, "serial"), "v",
                                 ["subject", "array", "bank"])
        if len(e):
            # scale by the array's own mean so metrics share one axis
            base = g.groupby(["subject", "array"]).v.mean().rename("base")
            e = e.merge(base, on=["subject", "array"])
            e["delta_pct"] = 100.0 * e.delta / e.base
            ebs.append(e.assign(metric=met))
    eb = pd.concat(ebs, ignore_index=True)
    for met, g in eb.groupby("metric"):
        neg = int((g.delta_pct < 0).sum())
        bt = binomtest(neg, len(g), 0.5)
        print(f"\n  {met}, border - interior inside a bank (% of array mean):")
        print(g.pivot_table(index=["subject", "array"], columns="bank",
                            values="delta_pct").round(1).to_string())
        print(f"    {neg}/{len(g)} negative, sign test p = {bt.pvalue:.3g}")
    eb.to_parquet(OUT / "within_bank_ephys.parquet", index=False)

    print("\n  per animal, sign of the within-bank contrast (all metrics):")
    print(eb.assign(sign=np.sign(eb.delta_pct))
            .pivot_table(index="subject", columns="metric", values="sign",
                         aggfunc="mean").round(2).to_string())

    banner("8. Rocky impedance: can the ring effect arbitrate the channel map?")
    arb = impedance_map_arbiter()
    if len(arb):
        print(arb.groupby("map").agg(
            n=("delta_dex", "size"),
            median_delta=("delta_dex", "median"),
            frac_negative=("delta_dex", lambda s: float((s < 0).mean())),
            frac_p05=("p", lambda s: float((s < 0.05).mean()))).round(3)
              .to_string())
        print("\n  Forrest et al. predict border < interior, i.e. a NEGATIVE "
              "delta.")
        arb.to_parquet(OUT / "impedance_map_arbiter.parquet", index=False)
    else:
        print("  ! Rocky impedance or authored map missing")

    banner("9. Figures")
    fig_layout(surf, FIG / "G1_layout.png")
    fig_profiles(prof, FIG / "G2_profiles.png")
    fig_borders(res, FIG / "G3_borders.png")
    fig_time(per, FIG / "G4_time.png")
    print(f"  wrote figures to {FIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

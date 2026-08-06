"""Longitudinal sanity check on the Rocky impedance sessions.

The impedance sweeps were nominally collected with one protocol and one
connection method across seven years. This script looks for sessions where
that was not true -- a wrong connector, a partially seated headstage, a
reference/ground problem, or a different tester configuration.

**No electrode ordering is required.** Every diagnostic here is either a
property of the session's distribution as a whole or a comparison of the
session against its own neighbours in time, so a scrambled within-file
electrode order cannot affect any of it. Ordering is deferred (see
docs/notes/impedance_parsing.md).

Five independent flags, each catching a different failure mode:

1. **Level shift** -- median 1 kHz impedance far from the array's local
   trend. Catches a whole-session gain or connection change.
2. **Dispersion collapse or explosion** -- the spread across the 96
   electrodes changing abruptly. A collapse suggests the tester measured
   something common to all channels (e.g. an unseated connector reading its
   own input impedance); an explosion suggests intermittent contact.
3. **Open/short fraction** -- proportion of electrodes outside a physically
   plausible window. A jump means many channels were not actually connected.
4. **Sweep-shape anomaly** -- an electrode-electrode impedance spectrum is
   monotonically decreasing with frequency. Sessions where that shape breaks
   were not measuring an electrode-electrolyte interface.
5. **Phase anomaly** -- at 1 kHz a Utah electrode is capacitive, so -phase
   sits well away from 0 and 90 deg. Values near either rail indicate a
   resistive or open connection rather than an electrode.

Run from repo root:

    uv run python notebooks/scratch_rocky_impedance_qc.py

See:
- docs/notes/impedance_parsing.md
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
ROCKY = Path(r"D:\Claude Code\Rocky")
OUT_DIR = REPO / "data" / "derived" / "rocky"
FIG_DIR = REPO / "figures" / "rocky"
QC_OUT = OUT_DIR / "impedance_qc.parquet"

N_FREQ_PER_SWEEP = 19
ELECTRODES_PER_FILE = 16
TARGET_HZ = 1000.0

# Physically plausible window for a chronic Utah electrode at 1 kHz.
# Below: short / broken trace. Above: open circuit or disconnected.
Z_SHORT_OHM = 20e3
Z_OPEN_OHM = 20e6

ROLL_WINDOW = 7        # sessions in the local baseline
LEVEL_FLAG = 2.0       # x deviation from local median
DISPERSION_FLAG = 2.5  # x deviation in robust CV
OPEN_SHORT_FLAG = 0.25  # fraction of electrodes out of range
MONOTONIC_FLAG = 0.70  # min fraction of sweeps that must decrease with frequency
PHASE_LO, PHASE_HI = 10.0, 80.0   # deg; outside this is not a capacitive interface
CROSS_ARRAY_FLAG = 1.7   # Anterior/Posterior median ratio implying one array is off


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def folder_date(name: str) -> str | None:
    """Parse the three date conventions used by impedance folders."""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", name)
    if m:
        return "{}-{}-{}".format(*m.groups())
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", name)
    if m:
        mo, d, y = m.groups()
        return f"{y}-{mo}-{d}"
    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", name.strip())
    if m:
        return "{}-{}-{}".format(*m.groups())
    return None


def parse_file(path: Path) -> pd.DataFrame:
    """Read one impedance .txt into per-sweep rows.

    Reads raw rather than via ``pd.read_csv``: field counts are inconsistent
    across rows in some files, and the header line repeats between sweeps.
    """
    recs = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        p = raw.split("\t")
        if len(p) < 3:
            continue
        try:
            recs.append((float(p[0]), float(p[1]), float(p[2])))
        except ValueError:
            continue
    df = pd.DataFrame(recs, columns=["freq_hz", "phase_deg", "z_ohm"])
    if not len(df):
        return df
    df["sweep"] = np.arange(len(df)) // N_FREQ_PER_SWEEP
    return df


def collect() -> pd.DataFrame:
    """Build a per-(date, array, sweep) table with the diagnostics each needs."""
    fname_re = re.compile(r"^(Anterior|Posterior)_([ABC])([12])$")
    rows = []
    for txt in ROCKY.rglob("*.txt"):
        d = folder_date(txt.parent.name)
        if d is None:
            continue
        m = fname_re.match(txt.stem)
        if not m:
            continue
        array, bank, half = m.group(1), m.group(2), int(m.group(3))
        df = parse_file(txt)
        if not len(df):
            continue
        for sweep, g in df.groupby("sweep"):
            if sweep >= ELECTRODES_PER_FILE or len(g) < 5:
                continue
            g = g.sort_values("freq_hz")
            i = (g["freq_hz"] - TARGET_HZ).abs().idxmin()
            # Is |Z| monotonically decreasing with frequency, as an
            # electrode-electrolyte interface must be?
            z_desc = g.sort_values("freq_hz", ascending=False)["z_ohm"].to_numpy()
            mono = float(np.mean(np.diff(z_desc) > 0)) if len(z_desc) > 2 else np.nan
            rows.append(dict(
                date=d, array=array, bank=bank, half=half, sweep=int(sweep),
                z_1khz=float(g.loc[i, "z_ohm"]),
                phase_1khz=float(g.loc[i, "phase_deg"]),
                mono_frac=mono,
                n_freq=len(g),
                source=txt.name,
            ))
    return pd.DataFrame(rows)


def session_stats(raw: pd.DataFrame) -> pd.DataFrame:
    """Collapse sweeps to one row per (date, array) with QC statistics."""
    out = []
    for (d, a), g in raw.groupby(["date", "array"]):
        z = g["z_1khz"].to_numpy()
        z = z[np.isfinite(z) & (z > 0)]
        if not len(z):
            continue
        med = float(np.median(z))
        q25, q75 = np.percentile(z, [25, 75])
        out.append(dict(
            date=d, array=a,
            n_sweeps=len(g),
            z_median=med,
            z_iqr=float(q75 - q25),
            # Robust CV: IQR normalised by median, immune to outliers
            z_rcv=float((q75 - q25) / med) if med > 0 else np.nan,
            frac_short=float((z < Z_SHORT_OHM).mean()),
            frac_open=float((z > Z_OPEN_OHM).mean()),
            phase_median=float(np.median(g["phase_1khz"])),
            mono_frac_median=float(np.median(g["mono_frac"].dropna()))
            if g["mono_frac"].notna().any() else np.nan,
        ))
    df = pd.DataFrame(out)
    df["date_dt"] = pd.to_datetime(df["date"])
    return df.sort_values(["array", "date_dt"]).reset_index(drop=True)


def add_flags(s: pd.DataFrame) -> pd.DataFrame:
    """Attach the five QC flags, comparing each session to its own neighbours."""
    parts = []
    for _, g in s.groupby("array"):
        g = g.sort_values("date_dt").copy()
        base_med = g["z_median"].rolling(ROLL_WINDOW, center=True, min_periods=3).median()
        base_rcv = g["z_rcv"].rolling(ROLL_WINDOW, center=True, min_periods=3).median()
        g["level_ratio"] = g["z_median"] / base_med
        g["rcv_ratio"] = g["z_rcv"] / base_rcv

        g["flag_level"] = (g["level_ratio"] > LEVEL_FLAG) | (g["level_ratio"] < 1 / LEVEL_FLAG)
        g["flag_dispersion"] = (
            (g["rcv_ratio"] > DISPERSION_FLAG) | (g["rcv_ratio"] < 1 / DISPERSION_FLAG)
        )
        g["flag_open_short"] = (g["frac_short"] + g["frac_open"]) > OPEN_SHORT_FLAG
        g["flag_sweep_shape"] = g["mono_frac_median"] < MONOTONIC_FLAG
        g["flag_phase"] = (g["phase_median"] < PHASE_LO) | (g["phase_median"] > PHASE_HI)
        parts.append(g)
    out = pd.concat(parts, ignore_index=True)

    # Cross-array agreement separates the two failure modes, and is the single
    # most diagnostic column here. The two arrays are independent electrodes in
    # independent tissue: their impedances have no reason to track each other
    # except through the shared measurement rig.
    #
    #   both arrays shift together  -> rig / protocol / tester configuration
    #   one array shifts alone      -> that array's connector or cable
    piv = out.pivot_table(index="date", columns="array", values="z_median")
    if {"Anterior", "Posterior"} <= set(piv.columns):
        piv = piv.dropna()
        ratio = (piv["Anterior"] / piv["Posterior"]).rename("cross_array_ratio")
        out = out.merge(ratio, left_on="date", right_index=True, how="left")
        # An array-specific fault drives this ratio away from 1
        out["flag_array_mismatch"] = (
            (out["cross_array_ratio"] > CROSS_ARRAY_FLAG)
            | (out["cross_array_ratio"] < 1 / CROSS_ARRAY_FLAG)
        )
    else:
        out["cross_array_ratio"] = np.nan
        out["flag_array_mismatch"] = False

    flag_cols = [c for c in out.columns if c.startswith("flag_")]
    out["n_flags"] = out[flag_cols].sum(axis=1)

    # Label the likely cause rather than leaving the reader to infer it
    def classify(r: pd.Series) -> str:
        if r["flag_array_mismatch"]:
            return "single-array connection"
        if r["flag_level"] and not r["flag_array_mismatch"]:
            return "rig/protocol level shift (both arrays)"
        if r["flag_dispersion"]:
            return "dispersion anomaly"
        if r["flag_sweep_shape"] or r["flag_phase"]:
            return "not an electrode interface"
        if r["flag_open_short"]:
            return "many channels out of range"
        return ""

    out["likely_cause"] = out.apply(classify, axis=1)
    return out


def render(s: pd.DataFrame, out_png: Path) -> None:
    """Four-panel QC overview with flagged sessions marked."""
    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
    colors = {"Anterior": "#1f77b4", "Posterior": "#d62728"}
    panels = [
        ("z_median", "median |Z| at 1 kHz (Ohm)", True),
        ("z_rcv", "robust CV  (IQR / median)", False),
        ("phase_median", "median -phase at 1 kHz (deg)", False),
        ("mono_frac_median", "fraction of sweep decreasing\nwith frequency", False),
    ]
    for ax, (col, lbl, logy) in zip(axes, panels, strict=True):
        for arr, g in s.groupby("array"):
            g = g.sort_values("date_dt")
            ax.plot(g["date_dt"], g[col], "-o", ms=4, lw=1.0,
                    color=colors.get(arr, "0.4"), label=arr, alpha=0.85)
            bad = g[g["n_flags"] > 0]
            ax.scatter(bad["date_dt"], bad[col], s=110, facecolors="none",
                       edgecolors="black", linewidths=1.6, zorder=5)
        if logy:
            ax.set_yscale("log")
        ax.set_ylabel(lbl)
        ax.grid(alpha=0.3)
    axes[2].axhspan(PHASE_LO, PHASE_HI, color="green", alpha=0.06)
    axes[3].axhline(MONOTONIC_FLAG, color="0.5", ls=":")
    axes[0].legend(fontsize=9)
    axes[3].set_xlabel("impedance session date")
    axes[3].xaxis.set_major_locator(mdates.YearLocator())
    axes[3].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("Rocky impedance QC -- black rings mark sessions with >=1 flag\n"
                 "(ordering-independent: all diagnostics are session-level)",
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    """Run the impedance QC sweep and report suspect sessions."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    banner("Step 1  parse all impedance sweeps")
    raw = collect()
    print(f"  sweeps parsed: {len(raw)}")
    print(f"  sessions: {raw.groupby(['date', 'array']).ngroups}  "
          f"dates: {raw['date'].nunique()}")

    banner("Step 2  per-session statistics")
    s = session_stats(raw)
    print(f"  sessions: {len(s)}")
    print(f"  sweeps per session: min={s['n_sweeps'].min()} "
          f"median={int(s['n_sweeps'].median())} max={s['n_sweeps'].max()}")
    incomplete = s[s["n_sweeps"] < 96]
    if len(incomplete):
        print(f"  INCOMPLETE sessions (<96 electrodes): {len(incomplete)}")
        print(incomplete[["date", "array", "n_sweeps"]].to_string(index=False))

    banner("Step 3  flags")
    s = add_flags(s)
    for c in [c for c in s.columns if c.startswith("flag_")]:
        print(f"  {c:20s} {int(s[c].sum()):3d} session(s)")
    print(f"  {'ANY FLAG':20s} {int((s['n_flags'] > 0).sum()):3d} of {len(s)}")

    banner("Step 4  suspect sessions, worst first")
    bad = s[s["n_flags"] > 0].sort_values(["n_flags", "level_ratio"], ascending=[False, False])
    if len(bad):
        cols = ["date", "array", "n_sweeps", "z_median", "z_rcv", "phase_median",
                "level_ratio", "cross_array_ratio", "n_flags", "likely_cause"]
        show = bad[cols].copy()
        show["z_median"] = (show["z_median"] / 1e3).round(0)
        for c in ("z_rcv", "phase_median", "level_ratio", "cross_array_ratio"):
            show[c] = show[c].round(2)
        show = show.rename(columns={"z_median": "z_med_kOhm"})
        print(show.to_string(index=False))
        print()
        print("  reasons per session:")
        for _, r in bad.iterrows():
            why = [c.replace("flag_", "") for c in s.columns
                   if c.startswith("flag_") and bool(r[c])]
            print(f"    {r['date']}  {r['array']:9s}  {', '.join(why)}")

        banner("Step 4b  grouped by likely cause")
        for cause, g in bad.groupby("likely_cause"):
            dates = sorted(g["date"].unique())
            print(f"  {cause}  ({len(g)} session-array, {len(dates)} dates)")
            print(f"    {', '.join(dates)}")
    else:
        print("  none")

    banner("Step 5  write + figure")
    s.to_parquet(QC_OUT, engine="pyarrow", index=False)
    print(f"  wrote {QC_OUT}  rows={len(s)}")
    render(s, FIG_DIR / "10_impedance_qc.png")
    print(f"  wrote {FIG_DIR / '10_impedance_qc.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

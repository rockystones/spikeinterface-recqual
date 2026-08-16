"""Parse Rocky longitudinal impedance sweeps and join them to the unit metrics.

Each `<date>/{Anterior,Posterior}_{A,B,C}{1,2}.txt` holds 16 consecutive EIS
sweeps -- one per contact, 19 frequencies each (1 MHz down to 1 Hz) -- with
the column header row *repeated between sweeps*. Six files cover one array's
96 channels. Measured on an external potentiostat, not through the Blackrock
headstage; the two impedance families are separated in
docs/notes/impedance_sources.md.

Two things this script refuses to assume:

1. **Sweep ordering within a file.** The files carry no contact labels, only a
   bank letter and a 1/2 half. Because a bank and pin are *connector*
   coordinates, the quantity indexed is a channel id, not an electrode id --
   but which sweep is which pin is still undocumented, so it is tested
   empirically against unit yield rather than trusted.
2. **That impedance was measured on recording days.** It was not -- impedance
   exists for 36 dates, and only 5 of 182 recording dates have a same-day
   measurement. The join is nearest-date within a tolerance, and the coverage
   it achieves is reported rather than hidden.

Run from repo root:

    uv run python notebooks/scratch_rocky_impedance.py [--tol-days 14]

See:
- docs/notes/impedance_parsing.md
- docs/session_plans/session04_rocky_resort.md
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
from _paths import ROCKY  # noqa: E402

OUT_DIR = REPO / "data" / "derived" / "rocky"
INDEX_IN = OUT_DIR / "session_index.parquet"
UNITS_IN = OUT_DIR / "units_long.parquet"
IMPEDANCE_OUT = OUT_DIR / "impedance_long.parquet"

N_FREQ_PER_SWEEP = 19       # 1 MHz .. 1 Hz
# A bank is 32 pins; the operator split each into two files, so a `{Bank}{Half}`
# file holds half a bank. Derived rather than written as 16 so a different bank
# size or split would not silently mis-index. See docs/notes/channel_mapping.md.
PINS_PER_BANK = 32
PINS_PER_HALF = PINS_PER_BANK // 2
TARGET_HZ = 1000.0          # standard electrode-impedance readout


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


# %%
# === Parsing ===
def parse_impedance_file(path: Path) -> pd.DataFrame:
    """Parse one impedance .txt into tidy per-sweep rows.

    The file concatenates 16 sweeps, re-emitting the column header between
    each. Those repeated headers are dropped, then rows are chunked into
    sweeps of ``N_FREQ_PER_SWEEP``.

    Parameters
    ----------
    path : Path
        Path to a ``{Anterior,Posterior}_{A,B,C}{1,2}.txt`` file.

    Returns
    -------
    pandas.DataFrame
        Columns ``sweep``, ``freq_hz``, ``z_ohm``, ``phase_deg``.
    """
    # Read raw rather than via pd.read_csv: field counts are inconsistent
    # across rows in some files (observed 6 vs 9 in Anterior_C2.txt), which
    # trips the C parser. Only the first three columns are ever needed.
    recs: list[tuple[float, float, float]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = raw.split("\t")
        if len(parts) < 3:
            continue
        try:
            freq = float(parts[0])
            phase = float(parts[1])
            z = float(parts[2])
        except ValueError:
            continue  # header row, repeated between sweeps
        recs.append((freq, phase, z))
    df = pd.DataFrame(recs, columns=["freq_hz", "phase_deg", "z_ohm"])
    df = df.dropna(subset=["freq_hz", "z_ohm"]).reset_index(drop=True)

    df["sweep"] = np.arange(len(df)) // N_FREQ_PER_SWEEP
    return df[["sweep", "freq_hz", "z_ohm", "phase_deg"]]


def channel_id_from(bank: str, half: int, sweep: int) -> int:
    """Map (bank letter, file half, sweep index) to a **channel id**.

    This returns a channel id, not an electrode id. The distinction was settled
    after this parser was first written: `channel id` indexes the recording
    file, `electrode id` indexes the physical shank, and the two differ. The
    filename here names a *bank and half* -- connector coordinates -- so the
    quantity it yields is necessarily channel space:

        channel_id = (bank - 'A') * 32 + (half - 1) * 16 + sweep + 1

    which is the verified `(bank - 'A') * PINS_PER_BANK + pin` rule with the pin
    taken as the sweep's position within the half. To reach an electrode, route
    through the CMP.

    **The sweep-to-pin order within a file remains unverified** -- that a file
    covers a known set of 16 pins does not fix which sweep is which. See
    docs/notes/impedance_parsing.md.

    Parameters
    ----------
    bank : str
        ``A``, ``B`` or ``C``.
    half : int
        1 or 2, from the filename suffix.
    sweep : int
        0-based sweep index within the file.

    Returns
    -------
    int
        Channel id, 1-based.
    """
    bank_base = (ord(bank.upper()) - ord("A")) * PINS_PER_BANK
    return bank_base + (half - 1) * PINS_PER_HALF + sweep + 1


def build_impedance_table(root: Path) -> pd.DataFrame:
    """Walk the cohort and build the long-format impedance table.

    Parameters
    ----------
    root : Path
        Rocky dataset root.

    Returns
    -------
    pandas.DataFrame
        One row per (date, array, channel_id) at ``TARGET_HZ``, plus the
        full sweep retained as ``z_1khz_ohm`` alongside 10 Hz and 10 kHz
        reference points.
    """
    import re

    ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
    US = re.compile(r"(\d{2})-(\d{2})-(\d{4})")
    COMPACT = re.compile(r"^(\d{4})(\d{2})(\d{2})$")

    def folder_date(name: str) -> str | None:
        m = ISO.search(name)
        if m:
            return "{}-{}-{}".format(*m.groups())
        m = US.search(name)
        if m:
            mo, d, y = m.groups()
            return f"{y}-{mo}-{d}"
        m = COMPACT.match(name.strip())
        if m:
            return "{}-{}-{}".format(*m.groups())
        return None

    fname_re = re.compile(r"^(Anterior|Posterior)_([ABC])([12])$")
    rows: list[dict] = []
    for txt in root.rglob("*.txt"):
        d = folder_date(txt.parent.name)
        if d is None:
            continue
        m = fname_re.match(txt.stem)
        if not m:
            continue
        array, bank, half = m.group(1), m.group(2), int(m.group(3))
        try:
            sw = parse_impedance_file(txt)
        except Exception as e:  # noqa: BLE001
            print(f"    parse failed {txt.name}: {type(e).__name__}: {e}")
            continue
        for sweep, g in sw.groupby("sweep"):
            if sweep >= PINS_PER_HALF:
                continue  # trailing partial sweep, if any
            cid = channel_id_from(bank, half, int(sweep))

            def at(hz: float, g: pd.DataFrame = g) -> float:
                # g bound as a default arg so the closure captures this
                # iteration's frame, not the loop variable (ruff B023).
                i = (g["freq_hz"] - hz).abs().idxmin()
                return float(g.loc[i, "z_ohm"])

            rows.append(dict(
                date=d, array=array, bank=bank, half=half, sweep=int(sweep),
                channel_id=cid,
                z_1khz_ohm=at(TARGET_HZ),
                z_10hz_ohm=at(10.0),
                z_10khz_ohm=at(10_000.0),
                n_freq=len(g),
                source=str(txt),
            ))
    return pd.DataFrame(rows)


# %%
# === Ordering verification ===
def verify_ordering(imp: pd.DataFrame, units: pd.DataFrame, tol_days: int) -> None:
    """Test the assumed electrode ordering against unit yield.

    A correct mapping should show a negative association between 1 kHz
    impedance and unit yield: dead or very high impedance electrodes should
    carry fewer units. A scrambled mapping should show none. Comparing the
    two is the available evidence, since the files carry no electrode labels.

    Parameters
    ----------
    imp : pandas.DataFrame
        Output of :func:`build_impedance_table`.
    units : pandas.DataFrame
        Long-format unit metrics from the re-sort.
    tol_days : int
        Nearest-date join tolerance.
    """
    res = units[(units.get("method") == "resort")]
    if "pass_gate" not in res.columns or not len(res):
        print("  no re-sort rows available; skipping verification")
        return
    yield_df = (
        res[res["pass_gate"].fillna(False)]
        .groupby(["date", "array", "channel_id"])
        .size().rename("n_units").reset_index()
    )
    joined = nearest_date_join(yield_df, imp, tol_days)
    joined = joined.dropna(subset=["z_1khz_ohm", "n_units"])
    if len(joined) < 50:
        print(f"  only {len(joined)} joined rows; verification inconclusive")
        return

    rho, p = spearmanr(joined["z_1khz_ohm"], joined["n_units"])
    rng = np.random.default_rng(0)
    null = []
    for _ in range(200):
        shuffled = joined["z_1khz_ohm"].to_numpy().copy()
        rng.shuffle(shuffled)
        null.append(spearmanr(shuffled, joined["n_units"])[0])
    null = np.abs(np.array(null))

    print(f"  joined electrode-sessions : {len(joined)}")
    print(f"  Spearman rho (Z_1kHz vs n_units) : {rho:+.4f}  (p={p:.2e})")
    print(f"  |rho| vs shuffled null    : null p95={np.percentile(null, 95):.4f}")
    if abs(rho) > np.percentile(null, 95):
        print("  -> assumed ordering produces a real association; mapping is "
              "consistent with the data")
    else:
        print("  -> NO association beyond chance. The assumed A1->1..16 ordering "
              "is NOT supported; treat the impedance join as unverified.")


def nearest_date_join(
    left: pd.DataFrame, imp: pd.DataFrame, tol_days: int
) -> pd.DataFrame:
    """Join impedance to sessions by nearest measurement date within a tolerance.

    Impedance was measured on its own schedule (36 dates), not on recording
    days, so an exact join would discard almost everything.

    Parameters
    ----------
    left : pandas.DataFrame
        Must have ``date``, ``array``, ``channel_id``.
    imp : pandas.DataFrame
        Impedance table.
    tol_days : int
        Maximum allowed separation.

    Returns
    -------
    pandas.DataFrame
        ``left`` with impedance columns and ``imp_date``/``imp_gap_days``.
    """
    left = left.copy()
    left["_d"] = pd.to_datetime(left["date"])
    imp = imp.copy()
    imp["_d"] = pd.to_datetime(imp["date"])

    out = []
    for (array, eid), grp in left.groupby(["array", "channel_id"], sort=False):
        cand = imp[(imp["array"] == array) & (imp["channel_id"] == eid)]
        if not len(cand):
            continue
        g = grp.sort_values("_d")
        c = cand.sort_values("_d")
        m = pd.merge_asof(
            g, c[["_d", "z_1khz_ohm", "z_10hz_ohm", "z_10khz_ohm"]],
            on="_d", direction="nearest",
            tolerance=pd.Timedelta(days=tol_days),
        )
        m["imp_gap_days"] = np.nan
        out.append(m)
    if not out:
        return left.assign(z_1khz_ohm=np.nan)
    return pd.concat(out, ignore_index=True)


# %%
# === Main ===
def main() -> int:
    """Parse impedance, verify ordering, write the long table."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--tol-days", type=int, default=14,
                    help="Nearest-date join tolerance (default 14).")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    banner("Step 1  parse impedance sweeps")
    imp = build_impedance_table(ROCKY)
    print(f"  rows: {len(imp)}")
    if not len(imp):
        print("  nothing parsed; aborting")
        return 1
    print(f"  dates: {imp['date'].nunique()}   arrays: {sorted(imp['array'].unique())}")
    print(f"  electrodes per (date,array): "
          f"{imp.groupby(['date', 'array'])['channel_id'].nunique().describe()[['min', '50%', 'max']].to_dict()}")
    bad = imp[imp["n_freq"] != N_FREQ_PER_SWEEP]
    print(f"  sweeps with != {N_FREQ_PER_SWEEP} frequencies: {len(bad)}")
    print()
    print("  Z at 1 kHz (ohm) distribution:")
    z = imp["z_1khz_ohm"]
    for q in (1, 10, 50, 90, 99):
        print(f"    p{q:2d}: {np.percentile(z.dropna(), q):12,.0f}")

    banner("Step 2  verify assumed electrode ordering")
    if UNITS_IN.exists():
        units = pd.read_parquet(UNITS_IN)
        verify_ordering(imp, units, args.tol_days)
    else:
        print(f"  {UNITS_IN} not present yet; re-run after the re-sort finishes")

    banner("Step 3  write")
    imp.to_parquet(IMPEDANCE_OUT, engine="pyarrow", index=False)
    print(f"  wrote {IMPEDANCE_OUT}  "
          f"({IMPEDANCE_OUT.stat().st_size / 1024:.1f} KB)  rows={len(imp)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

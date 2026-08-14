"""The one authoritative channel map, hardware pin to data-file channel.

Four different numbers can refer to "a channel" in this project, three of them
called something like *electrode*, and two pieces of software use the same word
for different things. This module builds a single table carrying all of them
under unambiguous names, and verifies it against the recordings.

Vocabulary, following LB-0023 Rev 8 section "Channel ID, Electrode ID, and
channel index" and the mapfile KB article:

``bank`` + ``pin``
    Where the electrode is physically wired into the amplifier. The CMP column
    named ``elec`` is the **pin**, 1-32 within its bank -- not an electrode
    number. Banks are lettered A-H.

``channel_id``
    Blackrock's *Channel ID*: the order in which the hardware samples the
    banks and pins, ``(bank_index) * 32 + pin``. **This is the number that
    appears in NEV and NSx files.** Verified below against the NEV's own
    Physical Connector and Connector Pin header fields.

``electrode_num``
    Blackrock's *Electrode ID*: the array electrode, carried in the CMP
    ``label`` column as ``elecNN``. The spec is explicit that "Channel ID 1 is
    not necessarily equivalent to Electrode ID 1" -- on Rocky's arrays only 2
    of 96 coincide.

``col`` / ``row``
    Position in the 10x10 grid, 0-based, **row counting from the bottom**.
    Which four cells are vacant is a per-array build property.

Two collisions to keep in mind:

- **neo** exposes the NEV's channel identifier as ``electrode_id`` and renders
  it ``chNN``. That field is a *Channel ID* in Blackrock's terms. This project
  inherited the name, so ``electrode_id`` in existing derived tables means
  ``channel_id`` here. It is emitted as an alias for continuity.
- The factory impedance ``.txt`` heads its rows ``elec1..elec128``, but those
  are **pins**, not electrodes: rows 1-32 are exactly the CMP's bank-A labels,
  33-64 bank B. Reading them as electrode numbers scrambles the array.

Run from repo root:

    uv run python notebooks/scratch_channel_map.py

See:
- docs/notes/channel_mapping.md
"""

from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
from scratch_cohort_io import (  # noqa: E402
    parse_cmp,
    read_pad_map,
    vacant_cells,
    verify_against_padmap,
)

PROBE_DIR = REPO / "configs" / "probes"
OUT = REPO / "data" / "derived" / "channel_map.parquet"

PITCH_UM = 400.0          # Utah inter-electrode spacing
PINS_PER_BANK = 32

# Recordings used to verify the derived Channel ID against the NEV's own
# Physical Connector / Connector Pin fields.
NEV_CHECKS = [
    ("Rocky I1 2018", r"D:\Claude Code\Rocky\Rocky all nev\Anterior\Sorted"
                      r"\Sorted NEV\Rocky_Anterior_04-26-2018_Baseline_DigitalHeadstage-01.nev"),
    ("Rocky I1 2023", r"D:\Claude Code\Rocky\Rocky all nev\Anterior\Sorted"
                      r"\Sorted NEV\Rocky_Anterior_2023-07-27_Baseline_DigitalHeadstage-01.nev"),
    ("Nigel 2023", str(REPO / "data" / "raw"
                       / "Nigel_Anterior_2023-03-17_Baseline_DigitalHeadstage-01.nev")),
]


def banner(t: str) -> None:
    print()
    print("=" * 76)
    print(t)
    print("=" * 76)


# %%
# === The map ===
def channel_id(bank: str, pin: int) -> int:
    """Blackrock Channel ID from amplifier bank and pin.

    "Channel ID order is defined by the sequential sampling of banks in order
    ... and pins in order within each bank" (LB-0023 Rev 8). Bank A pins 1-32
    are channels 1-32, bank B 33-64, bank C 65-96.
    """
    return (ord(bank.upper()) - ord("A")) * PINS_PER_BANK + int(pin)


def build_map(cmp_path: Path, xlsm_path: Path | None = None) -> pd.DataFrame:
    """Canonical per-electrode table for one array.

    Returns
    -------
    pandas.DataFrame
        One row per electrode with ``channel_id``, ``bank``, ``pin``,
        ``electrode_num``, ``electrode_label``, ``col``, ``row``, ``x_um``,
        ``y_um``, plus ``electrode_id`` as a deprecated alias of ``channel_id``
        for continuity with tables written before the naming was settled.
    """
    c = parse_cmp(cmp_path)
    m = pd.DataFrame({
        "channel_id": [channel_id(b, e) for b, e in zip(c.bank, c.elec, strict=True)],
        "bank": c.bank,
        "pin": c.elec.astype(int),
        "electrode_label": c.label,
        "electrode_num": c.label.str.extract(r"(\d+)", expand=False).astype("Int64"),
        "col": c.col.astype(int),
        "row": c.row.astype(int),
    })
    # Physical position. Row counts from the bottom, so y increases with row.
    m["x_um"] = m.col * PITCH_UM
    m["y_um"] = m.row * PITCH_UM
    m["electrode_id"] = m.channel_id          # deprecated alias, see docstring
    m["serial"] = re.search(r"(\d{4}-\d{6})", cmp_path.name).group(1)

    # Carried as a column, not in .attrs: DataFrame.attrs does not survive
    # sort_values, so an attrs-based flag silently reads "unknown" downstream.
    agreement = "no workbook"
    if xlsm_path is not None and xlsm_path.exists():
        pad = read_pad_map(xlsm_path)
        agreement = ("no pad grid" if pad is None
                     else ("exact" if not verify_against_padmap(c, pad)
                           else "MISMATCH"))
    m["pad_agreement"] = agreement
    return m.sort_values("channel_id").reset_index(drop=True)


def read_factory_impedance(txt_path: Path) -> pd.DataFrame:
    """Factory impedance, indexed by **pin**, despite the ``elecN`` header.

    Rows 1-96 are channels 1-96 (banks A-C); rows above that are unused bank-D
    pins on a 128-channel front end and read in the kilohm range.
    """
    rows = []
    for ln in txt_path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\s*elec(\d+)\s+(<=\s*)?(\d+)", ln)
        if m:
            rows.append(dict(channel_id=int(m.group(1)),
                             z_ohm=int(m.group(3)),
                             at_limit=bool(m.group(2))))
    return pd.DataFrame(rows)


# %%
# === Verification ===
def verify_against_nev(tag: str, nev_path: Path) -> dict | None:
    """Check the derived Channel ID against the NEV's own bank/pin fields."""
    if not nev_path.exists():
        return None
    from neo.rawio import BlackrockRawIO

    raw = BlackrockRawIO(filename=str(nev_path.with_suffix("")))
    raw.parse_header()
    ext = next((v for k, v in raw.__dict__.items() if "ext_header" in k), None)
    key = next((k for k in ext if b"NEUEVWAV" in k), None)
    if key is None:
        return None
    h = ext[key]
    df = pd.DataFrame({n: h[n] for n in
                       ("electrode_id", "physical_connector", "connector_pin")})
    df = df[df.electrode_id <= 96]
    derived = (df.physical_connector - 1) * PINS_PER_BANK + df.connector_pin
    return dict(tag=tag, n=len(df), agree=int((derived == df.electrode_id).sum()),
                banks=sorted(int(x) for x in df.physical_connector.unique()))


def main() -> int:
    banner("Verifying Channel ID against the NEV's own header fields")
    print("  NEUEVWAV stores Physical Connector (bank 1-4) and Connector Pin")
    print("  (1-32) beside the channel identifier, so the formula is testable.")
    for tag, p in NEV_CHECKS:
        r = verify_against_nev(tag, Path(p))
        if r is None:
            print(f"  {tag:16s} SKIP (not staged)")
            continue
        banks = ", ".join(chr(64 + b) for b in r["banks"])
        print(f"  {tag:16s} {r['agree']}/{r['n']} channels satisfy "
              f"channel_id == (bank-1)*32 + pin   banks present: {banks}")

    banner("Building the map for every array with a CMP")
    frames = []
    for cmp_path in sorted(PROBE_DIR.glob("*.cmp")):
        serial = re.search(r"(\d{4}-\d{6})", cmp_path.name).group(1)
        xl = next(iter(PROBE_DIR.glob(f"*{serial}.xlsm")), None)
        m = build_map(cmp_path, xl)
        txt = next(iter(PROBE_DIR.glob(f"*{serial}.txt")), None)
        if txt is not None:
            z = read_factory_impedance(txt)
            m = m.merge(z[z.channel_id <= 96], on="channel_id", how="left")
        frames.append(m)
        same = int((m.channel_id == m.electrode_num).sum())
        print(f"\n  {serial}  pad map: {m.pad_agreement.iloc[0]}")
        print(f"     channel_id == electrode_num for {same}/{len(m)} electrodes")
        print(f"     vacant cells {vacant_cells(parse_cmp(cmp_path))}")
        print(f"     bank A -> channels {m[m.bank == 'A'].channel_id.min()}"
              f"-{m[m.bank == 'A'].channel_id.max()}, "
              f"B -> {m[m.bank == 'B'].channel_id.min()}"
              f"-{m[m.bank == 'B'].channel_id.max()}, "
              f"C -> {m[m.bank == 'C'].channel_id.min()}"
              f"-{m[m.bank == 'C'].channel_id.max()}")
        if "z_ohm" in m:
            print(f"     factory impedance joined by channel_id: "
                  f"median {m.z_ohm.median():.0f} ohm, "
                  f"{int(m.z_ohm.isna().sum())} missing")

    allmap = pd.concat(frames, ignore_index=True)

    banner("Worked example: how one number becomes another")
    ex = allmap[allmap.serial == "1025-001501"].nsmallest(6, "channel_id")
    print(ex[["serial", "channel_id", "bank", "pin", "electrode_label",
              "electrode_num", "col", "row"]].to_string(index=False))
    print("\n  Read the first row as: the electrode Blackrock calls elec78 is")
    print("  wired to bank A pin 1, therefore appears in the NEV as ch1, and")
    print("  sits at grid column 2, row 9 (row counted from the bottom).")

    banner("The trap, stated plainly")
    n_agree = int((allmap.channel_id == allmap.electrode_num).sum())
    print(f"  channel_id equals electrode_num for {n_agree} of {len(allmap)} "
          f"rows across all arrays.")
    print("  Treating the CMP 'elec' column as an electrode number, or the")
    print("  impedance file's 'elecN' rows as electrode numbers, silently")
    print("  permutes the array.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    allmap.to_parquet(OUT, engine="pyarrow", index=False)
    for serial, g in allmap.groupby("serial"):
        g.to_csv(PROBE_DIR / f"channel_map_{serial}.csv", index=False)
    banner("Written")
    print(f"  {OUT.relative_to(REPO)}  ({len(allmap)} rows)")
    for p in sorted(PROBE_DIR.glob("channel_map_*.csv")):
        print(f"  {p.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

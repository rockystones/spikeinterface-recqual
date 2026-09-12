"""Extend Rocky's impedance record and let the bench arbitrate the channel map.

Four jobs, all runnable without the map decision -- and two of them bear
directly on it:

1. **Ingest the missing era.** `Patrick/monkey_array/Rocky/postimplant/` holds
   36 dated folders; 16 of them (2019-06 .. 2021-07) were never ingested --
   exactly the 2019-2021 gap in `impedance_long.parquet`. These files use a
   **45-point frequency ladder**, not the 19-point one, so the fixed-length
   sweep chunking in `scratch_rocky_impedance.py` would shred them silently.
   Sweeps are chunked here by frequency reset instead, and validated.

2. **The bench arbiter.** `Rocky/preimplant/` holds potentiostat sweeps of both
   arrays taken before implantation. The factory workbook holds the same
   arrays' impedance indexed by **channel id, proven 1248/1248**
   ([[impedance_sources]]). Both candidate maps assign the same 16 channels to
   each file half, so the between-half signal is shared -- the discriminating
   signal is the **within-half ordering**, 16 values per half, 12 halves.
   Whichever ordering correlates with the factory values is the real one.

3. **The open/short test.** 11 array-dates carry electrodes the potentiostat
   read as open (>20 MOhm) or short (<20 kOhm). A genuinely open electrode
   records no spikes, so the flagged sweep's channel -- under the true map --
   should sit at an extreme of its session's ephys distribution.

4. **The extended border arbiter.** The ring analysis's border-vs-interior
   contrast ([[ring_geometry]]) re-run over the full 52-date record.

Run from repo root:

    uv run python notebooks/scratch_impedance_extended.py

See docs/notes/impedance_channel_map.md (updated with these results).
"""

from __future__ import annotations

import re
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

PATRICK = Path(r"D:\Claude Code\Monkey Data\Legacy\Patrick\monkey_array\Rocky")
OUT_DIR = REPO / "data" / "derived" / "rocky"
FULL_OUT = OUT_DIR / "impedance_long_full.parquet"
BENCH_OUT = OUT_DIR / "impedance_bench.parquet"
AUTHORED = REPO / "configs" / "probes" / "impedance_channel_map.csv"

SERIALS = {"Anterior": "1025-001501", "Posterior": "1025-001497"}
TARGET_HZ = 1000.0
Z_SHORT_OHM = 20e3          # thresholds from scratch_rocky_impedance_qc.py
Z_OPEN_OHM = 20e6


# %%
# === Parsing: sweep chunking that survives a changed frequency ladder ===
def parse_sweeps(path: Path) -> pd.DataFrame:
    """Parse one potentiostat dump into per-sweep rows, chunked by freq reset.

    The 2017-2018 and 2022-2024 eras used a 19-point ladder and the 2019-2021
    era a 45-point one, so chunking by a fixed length is wrong for half the
    corpus. Within a sweep the ladder is strictly descending; a new sweep is
    wherever frequency rises again.

    Parameters
    ----------
    path : Path
        A ``*_{A,B,C}{1,2}.txt`` dump, 16 concatenated sweeps.

    Returns
    -------
    pandas.DataFrame
        ``sweep, freq_hz, z_ohm, phase_deg`` plus per-file validation fields.
    """
    recs: list[tuple[int, float, float, float]] = []
    sweep = -1                            # headers delimit sweeps
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = raw.split("\t")
        if len(parts) < 3:
            continue
        try:
            row = (float(parts[0]), float(parts[1]), float(parts[2]))
        except ValueError:
            # the instrument re-emits the column header before every sweep;
            # that line is the one reliable sweep delimiter across all three
            # frequency-ladder eras (19, 45, 75 points)
            if "Frequency" in parts[0]:
                sweep += 1
            continue
        recs.append((max(sweep, 0), *row))
    d = pd.DataFrame(recs, columns=["sweep", "freq_hz", "phase_deg", "z_ohm"])
    if not len(d):
        return d
    # a file with 32 headers is the half measured twice; the second pass
    # supersedes the first, like the explicit *_2 rerun files
    n_sweeps = d.sweep.nunique()
    if n_sweeps == 32:
        d = d[d.sweep >= 16].copy()
        d["sweep"] -= 16
    return d


def at_hz(g: pd.DataFrame, hz: float) -> float:
    """The sweep's |Z| at the ladder point nearest ``hz``."""
    i = (g.freq_hz - hz).abs().idxmin()
    return float(g.loc[i, "z_ohm"])


def ingest_tree(root: Path, label: str) -> pd.DataFrame:
    """All chronic dumps under one tree, one row per (date, array, sweep)."""
    compact = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
    us = re.compile(r"(\d{2})-(\d{2})-(\d{4})")
    fname = re.compile(r"^(Anterior|Posterior)_([ABC])([12])(_2)?$")

    rows = []
    for txt in sorted(root.rglob("*.txt")):
        m = fname.match(txt.stem)
        if not m:
            continue
        folder = txt.parent.name
        mm = compact.match(folder)
        date = ("{}-{}-{}".format(*mm.groups()) if mm else None)
        if date is None:
            mm = us.search(folder)
            if mm:
                mo, dd, yy = mm.groups()
                date = f"{yy}-{mo}-{dd}"
        if date is None:
            continue
        array, bank, half, rerun = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        sw = parse_sweeps(txt)
        n_sweeps = sw.sweep.nunique()
        if n_sweeps != 16:
            print(f"    ! {txt.parent.name}/{txt.name}: {n_sweeps} sweeps, skipped")
            continue
        for sweep, g in sw.groupby("sweep"):
            rows.append(dict(
                date=date, array=array, bank=bank, half=half, sweep=int(sweep),
                channel_id=(ord(bank) - 65) * 32 + (half - 1) * 16 + sweep + 1,
                z_1khz_ohm=at_hz(g, TARGET_HZ), z_10hz_ohm=at_hz(g, 10.0),
                z_10khz_ohm=at_hz(g, 10_000.0), n_freq=len(g),
                rerun=bool(rerun), tree=label, source=str(txt)))
    return pd.DataFrame(rows)


# %%
# === The candidate maps as (bank, half, sweep) -> channel_id ===
# Both primary candidates permute only within a bank half. The reversed
# variants exist because several bench halves anticorrelate strongly with the
# factory record, which is the signature of a within-half order flip rather
# than of noise.
def candidate_channels(d: pd.DataFrame) -> pd.DataFrame:
    """The four candidate channel assignments for every sweep row.

    Returns
    -------
    pandas.DataFrame
        ``ch_naive, ch_naive_rev, ch_authored, ch_authored_rev`` aligned to
        ``d``'s index. naive: sweep order equals pin order within the half.
        authored: the lab's mapping sheets. *_rev: the same with the 16
        positions reversed.
    """
    a = pd.read_csv(AUTHORED)
    key = a.set_index(["half", "pos"]).channel_id
    half_lbl = d.bank.astype(str) + d.half.astype(int).astype(str)
    pos_fwd = d.sweep.astype(int) + 1
    pos_rev = 16 - d.sweep.astype(int)
    base = (d.bank.map(lambda s: ord(s) - 65) * 32
            + (d.half.astype(int) - 1) * 16)
    out = pd.DataFrame(index=d.index)
    out["ch_naive"] = base + pos_fwd
    out["ch_naive_rev"] = base + pos_rev
    out["ch_authored"] = pd.MultiIndex.from_arrays(
        [half_lbl, pos_fwd]).map(key).to_numpy()
    out["ch_authored_rev"] = pd.MultiIndex.from_arrays(
        [half_lbl, pos_rev]).map(key).to_numpy()
    return out


CANDIDATES = ["ch_naive", "ch_naive_rev", "ch_authored", "ch_authored_rev"]


# %%
# === Job 2: the bench arbiter ===
def bench_table() -> pd.DataFrame:
    """Pre-implant potentiostat sweeps for both Rocky arrays, per sweep."""
    fname = re.compile(r"^(L1|ctrl)_([ABC])([12])(_2)?$")
    arrays = {"L1": "Anterior", "ctrl": "Posterior"}   # coat_1501 / ctrl_1497
    rows = []
    for txt in sorted((PATRICK / "preimplant").rglob("*.txt")):
        m = fname.match(txt.stem)
        if not m:
            continue
        cond, bank, half, rerun = m.groups()
        sw = parse_sweeps(txt)
        if sw.sweep.nunique() != 16:
            print(f"    ! bench {txt.name}: {sw.sweep.nunique()} sweeps, skipped")
            continue
        for sweep, g in sw.groupby("sweep"):
            rows.append(dict(
                array=arrays[cond], bank=bank, half=int(half), sweep=int(sweep),
                z_1khz_ohm=at_hz(g, TARGET_HZ), n_freq=len(g),
                rerun=bool(rerun), source=txt.name))
    b = pd.DataFrame(rows)
    # a rerun half supersedes its first take
    b = (b.sort_values("rerun")
           .drop_duplicates(["array", "bank", "half", "sweep"], keep="last")
           .reset_index(drop=True))
    return pd.concat([b, candidate_channels(b)], axis=1)


def arbiter_bench_vs_factory(b: pd.DataFrame) -> pd.DataFrame:
    """Within-half Spearman of bench |Z| against factory |Z|, per map.

    Both maps agree on *which* 16 channels a file half covers, so any
    between-half signal is shared; only the ordering inside a half separates
    them. Twelve halves x two arrays gives twelve paired correlations.
    """
    from scipy.stats import spearmanr

    fac = pd.read_parquet(REPO / "data" / "derived" / "channel_map.parquet")
    fac = fac[~fac.at_limit]              # rails carry no ordering information
    fz = fac.set_index(["serial", "channel_id"]).z_ohm

    rows = []
    for (array, bank, half), g in b.groupby(["array", "bank", "half"]):
        serial = SERIALS[array]
        for col in CANDIDATES:
            idx = pd.MultiIndex.from_arrays(
                [np.repeat(serial, len(g)), g[col].astype(int)])
            f = pd.Series(idx.map(fz).to_numpy(), index=g.index)
            ok = f.notna() & np.isfinite(g.z_1khz_ohm)
            if ok.sum() < 8:
                continue
            rho, p = spearmanr(np.log10(g.z_1khz_ohm[ok]), np.log10(f[ok]))
            # extremes carry the identifiable signal a rank test dilutes: does
            # the bench half's highest-|Z| sweep land on the factory half's
            # highest-|Z| channel?
            gi = g[ok]
            fi = f[ok]
            hit_max = bool(gi.loc[gi.z_1khz_ohm.idxmax(), col]
                           == gi.loc[fi.idxmax(), col])
            hit_min = bool(gi.loc[gi.z_1khz_ohm.idxmin(), col]
                           == gi.loc[fi.idxmin(), col])
            rows.append(dict(array=array, bank=bank, half=half,
                             map=col.removeprefix("ch_"),
                             n=int(ok.sum()), rho=float(rho), p=float(p),
                             argmax_match=hit_max, argmin_match=hit_min))
    return pd.DataFrame(rows)


# %%
# === Job 3: open/short electrodes against ephys ===
def open_short_test(full: pd.DataFrame) -> pd.DataFrame:
    """Where do the potentiostat's open/short sweeps land in ephys, per map?

    For every flagged sweep, find the nearest ephys session of that array
    within 45 days and report the flagged channel's within-session percentile
    of crossing rate and noise. Under the true map an open electrode should
    sit at the quiet extreme; under a wrong map it should sit anywhere.
    """
    ev = pd.read_parquet(REPO / "data" / "derived" / "rocky"
                         / "events_electrode.parquet")
    ev["date"] = pd.to_datetime(ev["date"])

    flagged = full[(full.z_1khz_ohm > Z_OPEN_OHM)
                   | (full.z_1khz_ohm < Z_SHORT_OHM)].copy()
    flagged["kind"] = np.where(flagged.z_1khz_ohm > Z_OPEN_OHM, "open", "short")
    flagged["date"] = pd.to_datetime(flagged.date)

    rows = []
    # itertuples would rename the `array` column anyway (Series.array is a
    # pandas accessor), so index explicitly throughout
    for _, r in flagged.iterrows():
        sess = ev[ev["array"] == r["array"]]
        gap = (sess.date - r["date"]).abs()
        if not len(gap) or gap.min() > pd.Timedelta(days=45):
            continue
        day = sess[sess.date == sess.loc[gap.idxmin(), "date"]]
        for col in CANDIDATES:
            name, ch = col.removeprefix("ch_"), r[col]
            hit = day[day.channel_id == ch]
            if not len(hit):
                continue
            rows.append(dict(
                imp_date=r["date"].date().isoformat(),
                ephys_date=day.date.iloc[0].date().isoformat(),
                gap_days=int(gap.min().days), array=r["array"], kind=r["kind"],
                map=name, channel_id=int(ch),
                z_1khz_ohm=float(r["z_1khz_ohm"]),
                pct_rate=float((day.crossing_rate_hz
                                < hit.crossing_rate_hz.iloc[0]).mean()),
                pct_noise=float((day.noise_uv < hit.noise_uv.iloc[0]).mean()),
                pct_amp=float((day.amp_p99 < hit.amp_p99.iloc[0]).mean())))
    return pd.DataFrame(rows)


# %%
# === Job 4: the border arbiter over the full record ===
def border_arbiter(full: pd.DataFrame) -> pd.DataFrame:
    """Border-vs-interior contrast per array-date, under both maps."""
    from scipy.stats import mannwhitneyu

    geo = pd.concat([ring_frame(s) for s in SERIALS.values()],
                    ignore_index=True)
    rows = []
    for col in CANDIDATES:
        name = col.removeprefix("ch_")
        w = full.dropna(subset=[col]).copy()
        w["serial"] = w.array.map(SERIALS)
        w = w.merge(geo[["serial", "channel_id", "is_border"]],
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
def main() -> int:
    banner("1. Ingest: the Patrick tree against the already-ingested record")
    old = pd.read_parquet(OUT_DIR / "impedance_long.parquet")
    old["tree"] = "rocky_drive"
    old["rerun"] = False
    new = ingest_tree(PATRICK / "postimplant", "patrick")
    print(f"  patrick tree: {len(new)} sweep-rows, "
          f"{new.date.nunique()} dates, ladders {sorted(new.n_freq.unique())}")

    have = set(old.date.astype(str))
    add = new[~new.date.isin(have)].copy()
    print(f"  new dates not in impedance_long: {add.date.nunique()}")
    print("  " + " ".join(sorted(add.date.unique())))

    full = pd.concat([old, add.drop(columns=["rerun"])
                      .reindex(columns=old.columns, fill_value=None)],
                     ignore_index=True)
    full = pd.concat([full, candidate_channels(full)], axis=1)
    full = full.sort_values(["date", "array", "bank", "half", "sweep"])
    full.to_parquet(FULL_OUT, index=False)
    print(f"\n  full record: {full.date.nunique()} dates "
          f"{full.date.min()} -> {full.date.max()}, {len(full)} sweep-rows")
    print(f"  wrote {FULL_OUT.name}")

    banner("2. The bench arbiter: pre-implant sweeps vs the factory workbook")
    b = bench_table()
    print(f"  bench sweeps: {len(b)} across "
          f"{b.groupby('array').size().to_dict()}")
    arb = arbiter_bench_vs_factory(b)
    piv = arb.pivot_table(index=["array", "bank", "half"], columns="map",
                          values="rho")
    print("\n  within-half Spearman rho, bench log|Z| vs factory log|Z|:")
    print(piv.round(3).to_string())
    from scipy.stats import binomtest, wilcoxon
    for name in piv.columns:
        g = arb[arb["map"] == name]
        v = g.rho
        amax, amin = int(g.argmax_match.sum()), int(g.argmin_match.sum())
        # a wrong permutation matches an extreme with probability 1/16
        pa = binomtest(amax, len(g), 1 / 16, alternative="greater").pvalue
        print(f"  {name:13s} median rho {v.median():+.3f}   rho>0: "
              f"{int((v > 0).sum())}/{len(v)}  Wilcoxon p={wilcoxon(v)[1]:.2g}"
              f"   argmax match {amax}/{len(g)} (p={pa:.3g})"
              f"   argmin match {amin}/{len(g)}")
    b.to_parquet(BENCH_OUT, index=False)
    arb.to_parquet(OUT_DIR / "impedance_bench_arbiter.parquet", index=False)

    banner("3. Open/short electrodes against ephys, both maps")
    os_t = open_short_test(full)
    if len(os_t):
        print(f"  {len(os_t)} flagged-sweep x map rows with ephys within 45 d")
        summary = (os_t.groupby(["kind", "map"])
                   .agg(n=("pct_rate", "size"),
                        med_pct_rate=("pct_rate", "median"),
                        med_pct_noise=("pct_noise", "median"),
                        med_pct_amp=("pct_amp", "median")).round(3))
        print(summary.to_string())
        print("\n  an OPEN electrode under the true map should sit near "
              "percentile 0 for rate\n  (records nothing) -- under a wrong "
              "map, near 0.5.")
        os_t.to_parquet(OUT_DIR / "impedance_open_short_test.parquet",
                        index=False)
    else:
        print("  no flagged sweeps within 45 days of ephys")

    banner("4. Border arbiter over the full 52-date record")
    arb2 = border_arbiter(full)
    print(arb2.groupby("map").agg(
        n=("delta_dex", "size"), median_delta=("delta_dex", "median"),
        frac_negative=("delta_dex", lambda s: float((s < 0).mean())),
        frac_p05=("p", lambda s: float((s < 0.05).mean()))).round(3)
        .to_string())
    arb2.to_parquet(OUT_DIR / "impedance_map_arbiter_full.parquet",
                    index=False)

    banner("5. Rocky's edge time course, bench-anchored (authored map)")
    # near-identical under all four candidates (the half-level component is
    # shared), so one map suffices for the trend
    from scipy.stats import spearmanr

    geo = pd.concat([ring_frame(s) for s in SERIALS.values()],
                    ignore_index=True)
    bb = b.copy()
    bb["serial"] = bb["array"].map(SERIALS)
    bb = bb.merge(geo[["serial", "channel_id", "is_border"]],
                  left_on=["serial", "ch_authored"],
                  right_on=["serial", "channel_id"], how="inner")
    bb["log_z"] = np.log10(bb.z_1khz_ohm.clip(lower=1))
    for arr, g in bb.groupby("array", observed=True):
        bench = g.loc[g.is_border, "log_z"].median() \
            - g.loc[~g.is_border, "log_z"].median()
        t = (arb2[(arb2["map"] == "authored") & (arb2["array"] == arr)]
             .sort_values("date"))
        age = pd.to_datetime(t.date).map(pd.Timestamp.toordinal).to_numpy()
        rho, p = spearmanr(age, t.delta_dex)
        print(f"  {arr}: bench {bench:+.3f} dex -> chronic median "
              f"{t.delta_dex.median():+.3f} over {len(t)} dates "
              f"({t.date.min()} .. {t.date.max()})")
        print(f"      trend vs date: rho = {rho:+.3f}, p = {p:.3g};  "
              f"dates below bench: {int((t.delta_dex < bench).sum())}/{len(t)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

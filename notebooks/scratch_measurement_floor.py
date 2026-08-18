"""S09: how much the answer moves when you change the operator or the algorithm.

A longitudinal claim is only interpretable against the amount the measurement
itself moves. This measures that, exactly, using the fact that sorting never
re-detects: every variant of a recording labels the *same* list of spikes
(697/697 verified, see docs/notes/monkey_corpus.md), so comparing two sorts is a
confusion between two labellings rather than a matching problem.

Four sources of spread, all on fixed event sets:

    operator identity   DS vs Sidd on the same recording        30 sessions
    human vs automatic  each operator vs OFS `-01`              30 sessions
    operator vs self    Sidd's `-MA` vs his own redo             7 recordings
    algorithm choice    Nigel OFS sweep, 8 algorithms x 78      624 files

This is the label-only pass: unit counts, noise decisions and partition
agreement, read straight from the spike packets. Waveform-derived metrics
(amplitude, SNR) are the second pass -- they need the same reads plus alignment,
and are only worth paying for once the cheap answer is in.

Run from repo root:

    uv run python notebooks/scratch_measurement_floor.py [--jobs 8]

See:
- docs/analysis_plan.md
- docs/notes/measurement_floor.md
"""

from __future__ import annotations

import argparse
import itertools
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

REPO = Path(__file__).resolve().parent.parent
import sys  # noqa: E402

sys.path.insert(0, str(REPO / "notebooks"))
from _paths import MONKEY_ROOT  # noqa: E402
from scratch_monkey_variants import read_packets  # noqa: E402

INV = REPO / "data" / "derived" / "monkey_inventory.parquet"
OUT_DIR = REPO / "data" / "derived" / "floor"
FILES_OUT = OUT_DIR / "variant_files.parquet"
PAIRS_OUT = OUT_DIR / "variant_pairs.parquet"

NOT_A_UNIT = (0, 255)        # 0 unsorted, 255 noise -- neither is a unit
DS_CHAINS = ("-02", "-DS")
MA_CHAINS = ("-MA", "-MA-01", "-MA-02", "-MA-RE")
AUTO_CHAIN = "-01"

OFS_SWEEP_DIR = MONKEY_ROOT / "Nigel" / "OFS sorting test2023"
OFS_ALGOS = ["ScanEM-J3", "ScanEM-PSF", "ScanKmean-J3", "ScanKmean-PSF",
             "ScanValley-J3", "ScanValley-PSF", "TDIST-EM-3D-J3",
             "TDIST-EM-3D-PSF"]


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === One file, reduced to what a comparison needs ===
def label_file(path: Path) -> dict | None:
    """Per-file labelling summary, plus the arrays a pairwise test needs.

    Returns the electrode and unit-class arrays in packet order. Because every
    variant of a recording shares the packet order, two files can be compared
    element-wise with no alignment step.
    """
    try:
        ts, eid, cls = read_packets(path)
    except (OSError, ValueError, NotImplementedError):
        return None
    keep = ~np.isin(cls, NOT_A_UNIT)
    # A unit is a (electrode, class) pair: class ids restart on each electrode.
    units = {(int(e), int(c)) for e, c in zip(eid[keep], cls[keep], strict=True)}
    return dict(
        n_spikes=int(len(ts)), n_kept=int(keep.sum()),
        n_noise=int((cls == 255).sum()), n_unsorted=int((cls == 0).sum()),
        n_units=len(units), n_elec=int(len(np.unique(eid))),
        n_elec_with_units=len({e for e, _ in units}),
        keep_frac=float(keep.mean()),
        noise_frac=float((cls == 255).mean()),
        _ts=ts, _eid=eid, _cls=cls,
    )


def compare(a: dict, b: dict) -> dict:
    """Exact agreement between two labellings of one spike list.

    Decomposed deliberately: whether a spike is a unit at all is a different
    decision from how the kept spikes are partitioned, and operators can agree
    on one while disagreeing on the other.

    Returns
    -------
    dict
        ``keep_agree`` -- fraction of spikes both treat the same way
        (unit vs not-a-unit). ``ari_kept`` -- adjusted Rand index over spikes
        *both* keep, so it measures partitioning alone. ``jaccard_kept`` --
        overlap of the two kept sets. Unit-count deltas alongside.
    """
    if len(a["_ts"]) != len(b["_ts"]):
        return dict(comparable=False)
    # Same recording is asserted, not assumed: identical timestamps AND
    # electrodes in the same order is what makes element-wise comparison valid.
    if not (np.array_equal(a["_ts"], b["_ts"])
            and np.array_equal(a["_eid"], b["_eid"])):
        return dict(comparable=False)

    ka = ~np.isin(a["_cls"], NOT_A_UNIT)
    kb = ~np.isin(b["_cls"], NOT_A_UNIT)
    both = ka & kb
    union = ka | kb
    # Globally unique labels: class ids restart per electrode, so a raw class
    # comparison would merge unit 1 of every electrode into one cluster.
    la = a["_eid"].astype(np.int64) * 1000 + a["_cls"]
    lb = b["_eid"].astype(np.int64) * 1000 + b["_cls"]
    return dict(
        comparable=True,
        n_spikes=int(len(ka)),
        keep_agree=float((ka == kb).mean()),
        jaccard_kept=float(both.sum() / union.sum()) if union.sum() else np.nan,
        n_both_kept=int(both.sum()),
        ari_kept=(float(adjusted_rand_score(la[both], lb[both]))
                  if both.sum() > 1 else np.nan),
        units_a=a["n_units"], units_b=b["n_units"],
        d_units=b["n_units"] - a["n_units"],
        noise_a=a["n_noise"], noise_b=b["n_noise"],
        d_noise=b["n_noise"] - a["n_noise"],
    )


# %%
# === Building the comparison sets ===
def operator_sets(inv: pd.DataFrame) -> list[dict]:
    """Every operator comparison the corpus supports, tagged by scope.

    ``three_way`` marks the recordings that carry the automatic sort *and*
    both operators. Only within that subset are the four comparisons measured
    on identical input; the wider auto-vs-human sets draw on different (and
    mostly different-subject) recordings and must not be read side by side
    with the operator set without saying so.
    """
    nev = inv[(inv.role == "snippets") & inv.excluded.isna()]
    jobs: list[dict] = []
    for stem, g in nev.groupby("stem"):
        by_chain = {r.chain: MONKEY_ROOT / r.rel for r in g.itertuples()}
        ds = next((by_chain[c] for c in DS_CHAINS if c in by_chain), None)
        ma = next((by_chain[c] for c in MA_CHAINS if c in by_chain), None)
        auto = by_chain.get(AUTO_CHAIN)
        # Bracket access, not attribute: `row.array` is Series.array, the
        # backing ExtensionArray, not the column named "array".
        row = g.iloc[0]
        three_way = ds is not None and ma is not None and auto is not None
        base = dict(stem=stem, subject=row["subject"], implant=row["implant"],
                    array=row["array"], three_way=three_way,
                    date=(row["date"].date() if pd.notna(row["date"])
                          else None))
        if ds is not None and ma is not None:
            jobs.append(dict(**base, kind="operator", a="DS", b="Sidd",
                             pa=ds, pb=ma))
        if auto is not None and ds is not None:
            jobs.append(dict(**base, kind="auto_vs_DS", a="auto", b="DS",
                             pa=auto, pb=ds))
        if auto is not None and ma is not None:
            jobs.append(dict(**base, kind="auto_vs_Sidd", a="auto", b="Sidd",
                             pa=auto, pb=ma))
        # Sidd against his own redo: the within-operator movement.
        redo = [by_chain[c] for c in ("-MA-RE", "-MA-02", "-MA-01")
                if c in by_chain]
        if "-MA" in by_chain and redo:
            jobs.append(dict(**base, kind="self_Sidd", a="Sidd", b="Sidd_redo",
                             pa=by_chain["-MA"], pb=redo[0]))
    return jobs


def sweep_sets() -> list[dict]:
    """Every algorithm pair on each session of the Nigel OFS sweep."""
    by_session: dict[str, dict[str, Path]] = {}
    for algo in OFS_ALGOS:
        for p in (OFS_SWEEP_DIR / algo).rglob("*.nev"):
            by_session.setdefault(p.name, {})[algo] = p
    jobs = []
    for name, algos in sorted(by_session.items()):
        for x, y in itertools.combinations(sorted(algos), 2):
            jobs.append(dict(stem=name.replace("-01.nev", ""), subject="Nigel",
                             implant="I1",
                             array=("Anterior" if "Anterior" in name
                                    else "Posterior"),
                             date=None, three_way=False, kind="algorithm",
                             a=x, b=y, pa=algos[x], pb=algos[y]))
    return jobs


def run_group(group: list[dict]) -> list[dict]:
    """All comparisons for one recording, loading each variant exactly once.

    The sweep asks for 28 pairs per session across 8 files; done pairwise that
    reads every file seven times. These are ~25 MB each and there are 624 of
    them, so the difference is roughly 130 GB of reads against 33 GB.
    """
    cache: dict[Path, dict | None] = {}

    def get(p: Path) -> dict | None:
        if p not in cache:
            cache[p] = label_file(p)
        return cache[p]

    out: list[dict] = []
    for job in group:
        a, b = get(job["pa"]), get(job["pb"])
        if a is None or b is None:
            continue
        row = {k: v for k, v in job.items() if k not in ("pa", "pb")}
        row.update(compare(a, b))
        out.append(row)
    # Per-file summaries fall out of the same reads; emit them here rather
    # than paying for a second pass over the corpus.
    files = []
    for p, d in cache.items():
        if d is None:
            continue
        files.append(dict(path=str(p),
                          **{k: v for k, v in d.items()
                             if not k.startswith("_")}))
    return [dict(_pairs=out, _files=files)]


def group_jobs(jobs: list[dict]) -> list[list[dict]]:
    """Bundle comparisons that share a recording, so a worker reads it once."""
    by_stem: dict[tuple, list[dict]] = {}
    for j in jobs:
        by_stem.setdefault((j["subject"], j["stem"]), []).append(j)
    return list(by_stem.values())


# %%
# === Reporting ===
def report(pairs: pd.DataFrame) -> None:
    ok = pairs[pairs.comparable]
    banner("1. Do the variants describe the same spikes?")
    print(f"  comparisons attempted : {len(pairs)}")
    print(f"  element-wise comparable: {len(ok)}  "
          f"({len(ok) / max(len(pairs), 1):.1%})")
    bad = pairs[~pairs.comparable]
    if len(bad):
        print(f"  NOT comparable: {len(bad)} -- listed below, excluded")
        for r in bad.head(8).itertuples():
            print(f"      {r.kind:14s} {r.stem[:46]}")

    def table(df: pd.DataFrame) -> pd.DataFrame:
        return df.groupby("kind").agg(
            n=("ari_kept", "size"),
            keep_agree_med=("keep_agree", "median"),
            ari_med=("ari_kept", "median"),
            ari_p10=("ari_kept", lambda s: s.quantile(0.10)),
            units_a_med=("units_a", "median"),
            units_b_med=("units_b", "median"),
            d_units_med=("d_units", "median"),
            d_units_iqr=("d_units", lambda s: s.quantile(.75) - s.quantile(.25)),
            d_noise_med=("d_noise", "median"),
        ).round(3)

    banner("2. The measurement floor, by source of variation")
    print("  keep_agree : fraction of spikes both treat the same way")
    print("               (assigned to a unit vs discarded)")
    print("  ari_kept   : partition agreement over spikes BOTH keep")
    print("  d_units    : b minus a, so sign is meaningful\n")
    print(table(ok).to_string())

    matched = ok[ok.three_way & (ok.kind != "algorithm")]
    if len(matched):
        banner("2b. Matched subset -- identical input, so directly comparable")
        print("  Only recordings carrying the automatic sort AND both operators."
              "\n  The table above pools wider sets that differ in subject and"
              "\n  era, which is fine per row and misleading across rows.\n")
        print(table(matched).to_string())
        print(f"\n  recordings in the matched subset: "
              f"{matched.stem.nunique()}")
        print(matched.groupby(["subject", "array"], dropna=False)
              .stem.nunique().to_string())

    banner("3. Relative spread -- the number a longitudinal claim is sized by")
    rel = ok.copy()
    denom = rel[["units_a", "units_b"]].mean(axis=1).replace(0, np.nan)
    rel["rel_d_units"] = (rel.units_b - rel.units_a).abs() / denom
    r = rel.groupby("kind").rel_d_units.describe(
        percentiles=[0.5, 0.9])[["count", "50%", "90%", "max"]].round(3)
    r.columns = ["n", "median", "p90", "max"]
    print("  |unit count difference| as a fraction of the mean of the two:")
    print(r.to_string())

    banner("4. Systematic or random? -- decides whether the floor even bites")
    print("  A consistent offset (one operator always calls more units) cancels")
    print("  out of a trend computed within a single operator, and only breaks")
    print("  comparisons that cross operators. Random disagreement does not")
    print("  cancel and inflates every trend's error bar.\n")
    for kind, g in ok.groupby("kind"):
        d = g.d_units.dropna()
        if len(d) < 5:
            continue
        same_sign = max((d > 0).mean(), (d < 0).mean())
        # A consistent multiplicative offset shows up as a tight ratio.
        ratio = (g.units_b / g.units_a.replace(0, np.nan)).dropna()
        print(f"  {kind:14s} n={len(d):5d}  same sign: {same_sign:5.1%}"
              f"   ratio b/a median {ratio.median():.2f}"
              f"  IQR {ratio.quantile(.25):.2f}-{ratio.quantile(.75):.2f}")
    print("\n  same sign near 100% with a tight ratio = systematic offset.")
    print("  near 50% = the direction itself is unpredictable.")

    if "algorithm" in set(ok.kind):
        banner("4b. Which OFS algorithms disagree most")
        al = ok[ok.kind == "algorithm"].copy()
        al["pair"] = al.a + "  vs  " + al.b
        t = al.groupby("pair").agg(
            n=("ari_kept", "size"), ari_med=("ari_kept", "median"),
            d_units_med=("d_units", "median")).round(3)
        print(t.sort_values("ari_med").to_string())

    floor = dict(ok.assign(rel=(ok.units_b - ok.units_a).abs()
                           / ok[["units_a", "units_b"]].mean(axis=1)
                           .replace(0, np.nan))
                 .groupby("kind").rel.median())
    longitudinal_context(floor)


def longitudinal_context(floor: dict[str, float]) -> None:
    """Size the observed Rocky trend against the floor -- and against a third
    source of variation that turns out to dwarf both.

    Deliberately *not* a first-vs-last comparison. The anterior series is not
    monotone, so endpoints are the one summary guaranteed to mislead: its first
    four sessions sit near 150 units and the 2017 median is 11.
    """
    from scipy.stats import spearmanr

    lm_path = REPO / "data" / "derived" / "rocky" / "longitudinal_metrics.parquet"
    if not lm_path.exists():
        print("\n  longitudinal_metrics.parquet not found -- section skipped")
        return
    lm = pd.read_parquet(lm_path).dropna(subset=["n_units", "noise_med"])
    lm["yr"] = lm.date_dt.dt.year

    banner("5. What the series actually looks like")
    print("  Median units per session, by year. Anterior is not a decline --")
    print("  it rises to 2019 and falls after, so endpoint summaries lie.\n")
    t = lm.pivot_table(index="yr", columns="array", values="n_units",
                       aggfunc="median")
    n = lm.pivot_table(index="yr", columns="array", values="n_units",
                       aggfunc="size")
    for y in t.index:
        cells = "   ".join(
            f"{a} {t.loc[y, a]:5.0f} (n={n.loc[y, a]:3.0f})"
            for a in t.columns if pd.notna(t.loc[y, a]))
        print(f"    {y}   {cells}")

    banner("6. A third source of variation, larger than either of the above")
    print("  Some sessions have a noise floor 4-5x the array's baseline. The")
    print("  candidate count is unchanged in those sessions -- the events are")
    print("  still detected -- but the SNR gate then rejects nearly all of")
    print("  them, so `n_units` collapses and recovers. That is the")
    print("  acquisition state, not the electrode.\n")
    rows = []
    for arr, g in lm.groupby("array"):
        base = g.noise_med.median()
        hi = g[g.noise_med > 2 * base]
        lo = g[g.noise_med <= 2 * base]
        ratio = hi.n_units.median() / max(lo.n_units.median(), 1)
        print(f"  {arr:10s} baseline {base:5.1f} uV | high-noise sessions "
              f"{len(hi):3d}/{len(g):3d} ({len(hi) / len(g):4.0%})")
        print(f"    {'':10s} median units  normal {lo.n_units.median():5.0f}"
              f"   high-noise {hi.n_units.median():5.0f}   ratio {ratio:.2f}")
        rows.append((arr, 1 - ratio))
    worst = max(r for _, r in rows)
    print(f"\n  Relative effect of a high-noise session: up to {worst:.2f}")
    for k in ("self_Sidd", "operator", "algorithm"):
        if k in floor:
            print(f"    vs {k:10s} floor {floor[k]:.2f}"
                  f"   -> {worst / floor[k]:4.1f}x larger")

    banner("7. Does the trend survive excluding them?")
    print("  The exclusion is on an ACQUISITION criterion -- the session's own")
    print("  noise floor -- not on the outcome. Dropping sessions because they")
    print("  had few units would be circular; dropping them because the")
    print("  amplifier was noisy is not.\n")
    for arr, g in lm.groupby("array"):
        base = g.noise_med.median()
        clean = g[g.noise_med <= 2 * base]
        ra, pa = spearmanr(g.date_dt.map(pd.Timestamp.toordinal), g.n_units)
        rc, pc = spearmanr(clean.date_dt.map(pd.Timestamp.toordinal),
                           clean.n_units)
        # An era exclusion is the incumbent explanation; show whether the
        # acquisition screen is doing anything beyond re-deriving it.
        g18 = g[g.date_dt.dt.year > 2017]
        c18 = g18[g18.noise_med <= 2 * base]
        r18, p18 = spearmanr(g18.date_dt.map(pd.Timestamp.toordinal),
                             g18.n_units)
        rb, pb = spearmanr(c18.date_dt.map(pd.Timestamp.toordinal),
                           c18.n_units)
        print(f"  {arr:10s} rho all           {ra:+.3f}  p={pa:.2g}  "
              f"(n={len(g)})")
        print(f"  {'':10s} rho noise-screened {rc:+.3f}  p={pc:.2g}  "
              f"(n={len(clean)})   dropped {len(g) - len(clean)}")
        print(f"  {'':10s} rho excl 2017     {r18:+.3f}  p={p18:.2g}  "
              f"(n={len(g18)})")
        print(f"  {'':10s} rho both          {rb:+.3f}  p={pb:.2g}  "
              f"(n={len(c18)})")
        in2017 = int((g[g.noise_med > 2 * base].date_dt.dt.year == 2017).sum())
        print(f"  {'':10s} -> {in2017} of {len(g) - len(clean)} dropped "
              f"sessions are 2017, so the screen largely re-derives the known"
              f"\n  {'':10s}    era confound -- but keeps 2017's good sessions"
              f" and catches later ones.")

    print("\n  CAVEAT: the operator floor is measured on Fisk and Rocky implant")
    print("  2 (2023-2025) and the algorithm floor on Nigel; the trend is Rocky")
    print("  implant 1 (2017-2023). That the spread transfers across that gap")
    print("  in protocol and hardware is an assumption, not a finding.")



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--sweep-limit", type=int, default=0,
                    help="cap sweep sessions (0 = all)")
    args = ap.parse_args()

    inv = pd.read_parquet(INV)
    jobs = operator_sets(inv)
    sweep = sweep_sets()
    if args.sweep_limit:
        keep = sorted({j["stem"] for j in sweep})[: args.sweep_limit]
        sweep = [j for j in sweep if j["stem"] in keep]
    jobs += sweep

    banner("S09 -- the measurement floor")
    counts = pd.Series([j["kind"] for j in jobs]).value_counts()
    print(f"  comparisons to run: {len(jobs)}")
    print(counts.to_string())

    groups = group_jobs(jobs)
    print(f"  bundled into {len(groups)} recordings "
          f"(each variant read once, not once per pair)")
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        res = list(ex.map(run_group, groups, chunksize=1))

    pair_rows = [r for chunk in res for out in chunk for r in out["_pairs"]]
    file_rows_ = [r for chunk in res for out in chunk for r in out["_files"]]
    pairs = pd.DataFrame(pair_rows)
    files = pd.DataFrame(file_rows_).drop_duplicates("path")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pairs.to_parquet(PAIRS_OUT, engine="pyarrow", index=False)
    files.to_parquet(FILES_OUT, engine="pyarrow", index=False)

    report(pairs)
    print(f"\n  wrote {PAIRS_OUT.relative_to(REPO)}  ({len(pairs)} rows)")
    print(f"  wrote {FILES_OUT.relative_to(REPO)}  ({len(files)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

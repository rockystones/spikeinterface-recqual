"""Q1: does multi-sorter consensus match the human (Plexon OFS) sorting?

For every stem whose four sorter outputs were kept
(`ns5/consensus/sortings/<stem>/`), build the human reference sorting from
the session's canonical sorted NEV (Plexon unit labels at NEV sample
times, units 0/255 dropped) and compare, at the same delta_time=0.4 ms /
match_score=0.5 the agreement graph uses:

  - each individual sorter        vs OFS
  - consensus-of-k (k = 2..4)     vs OFS   (get_agreement_sorting)

Per candidate: how many human units it recovers (frac_ofs_matched), how
much of what it reports the human also saw (frac_cand_matched - the
precision side), unit counts, and the mean agreement of matched pairs.

Two measurement facts this script had to absorb (nav I-005):
  - The NEV's online detector stamps events a FIXED few ms after the
    continuous stream (measured -2.6 ms on the probe stem, sharp at
    0.4 ms tolerance once corrected). The lag is estimated per stem by
    scanning the pooled OFS-vs-sorter match over +-10 ms and applied to
    the OFS frames; the shard records lag_ms and the post-alignment
    pooled match against its chance floor.
  - OFS comparisons run at delta_time=1.0 ms (detector stamp vs template
    peak jitter); the sorter-vs-sorter consensus graph stays at 0.4 ms.
  - The resort's stored frac_nev_recovered is pooled at 1 ms and sits AT
    its own chance column (median excess -0.004) - it is not used here.

Caveats carried into the table rather than hidden:
  - OFS sorts the online-thresholded snippets; the sorters see the whole
    continuous stream. A consensus unit missing from OFS is not
    necessarily false - frac_cand_matched is a precision *proxy*.

Resumes from shards; rerun as the consensus expansion adds stems.

    uv run python notebooks/scratch_consensus_vs_ofs.py

Outputs: ns5/consensus/ofs_match_shards/<stem>.parquet,
         ns5/consensus/ofs_match.parquet
See docs/notes/consensus_vs_human.md; nav Q-0xx / W-0xx per ledger.
"""

from __future__ import annotations

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

from scratch_rocky_resort import open_nev, read_electrode  # noqa: E402

CONS = REPO / "data" / "derived" / "ns5" / "consensus"
SHARDS = CONS / "ofs_match_shards"
OUT = CONS / "ofs_match.parquet"
SUMMARY = REPO / "data" / "derived" / "ns5" / "ns5_sorters.parquet"
SORTERS = ["mountainsort5", "kilosort4", "spykingcircus2", "tridesclous2"]
PLEXON_DROP = (0, 255)
SR = 30000.0                      # Blackrock clock, NEV and ns5/ns6 alike


def ofs_sorting(stem: str, implant: str, subject: str):
    """The human reference: Plexon labels at NEV sample times, or None."""
    from spikeinterface.core import NumpySorting

    from scratch_provenance_dump import nev_path_for

    try:
        nev, _ = nev_path_for(stem, implant, subject)
    except FileNotFoundError:
        return None, 0
    raw, nmeta, chan_by_elec = open_nev(nev)
    frames, labels = [], []
    for elec in sorted(chan_by_elec):
        e = read_electrode(raw, nmeta, chan_by_elec[elec])
        if e is None:
            continue
        t, pu = e["t"], e["plexon_unit"]
        for u in np.unique(pu):
            if u in PLEXON_DROP:
                continue
            tt = t[pu == u]
            frames.append((tt * SR).round().astype(np.int64))
            labels.append(np.full(len(tt), f"ch{int(elec)}u{int(u)}"))
    if not frames:
        return None, 0
    so = NumpySorting.from_times_labels(
        [np.concatenate(frames)], [np.concatenate(labels)],
        sampling_frequency=SR)
    return so, len(labels)


def coarse_lag(a_s: np.ndarray, b_s: np.ndarray, bin_s: float = 0.001
               ) -> float:
    """FFT cross-correlation peak (s): lag to add to b so it meets a."""
    nb = int(max(a_s.max(), b_s.max()) / bin_s) + 2000
    ha = np.bincount((a_s / bin_s).astype(int), minlength=nb).astype(float)
    hb = np.bincount((b_s / bin_s).astype(int), minlength=nb).astype(float)
    n = 1 << int(np.ceil(np.log2(nb * 2)))
    cc = np.fft.irfft(np.fft.rfft(ha, n) * np.conj(np.fft.rfft(hb, n)), n)
    lags = np.arange(n)
    lags[lags > n // 2] -= n
    return float(lags[int(np.argmax(cc))]) * bin_s


def top_trains_s(so, k: int) -> list[np.ndarray]:
    """The k largest units' spike trains, in seconds."""
    tr = [so.get_unit_spike_train(u, segment_index=0)
          for u in so.unit_ids]
    tr.sort(key=len, reverse=True)
    return [t / SR for t in tr[:k]]


def estimate_lag(ofs, sortings) -> tuple[float, float]:
    """Clock lag (s) to ADD to sorter times so they meet the OFS stamps.

    Multi-segment sessions carry SECONDS of offset (the NEV clock spans
    dropped segments; Rocky 2018-11-09 measured -3.54 s), single-segment
    ones a few ms of DSP delay (I-005). Dense pooled trains saturate any
    single correlation, so several coarse candidates are generated -
    pooled top units, plus sparse top-5-vs-top-5 per sorter - each
    refined on a 0.1 ms grid, and the best fine 0.4 ms match wins. No
    gate: zeroing a real lag destroys the comparison, while a spurious
    lag on unrelated trains leaves them as unmatched as they were.
    """
    from scratch_ns5_resort import match_rate

    ofs_s = np.sort(np.concatenate(top_trains_s(ofs, 20)))
    cand_pool = np.sort(np.concatenate(
        sum((top_trains_s(s, 8) for s in sortings), [])))
    cands = {0.0, coarse_lag(ofs_s, cand_pool)}
    ofs_sparse = np.sort(np.concatenate(top_trains_s(ofs, 5)))
    for s in sortings:
        sp = np.sort(np.concatenate(top_trains_s(s, 5)))
        if len(sp):
            cands.add(coarse_lag(ofs_sparse, sp))
    best = (0.0, 0.0)
    for L0 in cands:
        for L in np.arange(L0 - 0.002, L0 + 0.002, 0.0001):
            v = match_rate(ofs_s, cand_pool + L, 0.0004)
            if v > best[1]:
                best = (float(L), float(v))
    return best


def shift_sorting(so, lag_s: float):
    """The sorting with lag_s added to every spike time."""
    from spikeinterface.core import NumpySorting

    if abs(lag_s) < 1e-9:
        return so
    dshift = int(round(lag_s * SR))
    frames, labels = [], []
    for u in so.unit_ids:
        f = so.get_unit_spike_train(u, segment_index=0) + dshift
        f = f[f >= 0]
        frames.append(f)
        labels.append(np.full(len(f), str(u)))
    return NumpySorting.from_times_labels(
        [np.concatenate(frames)], [np.concatenate(labels)],
        sampling_frequency=SR)


def compare_pair(ofs, cand, name: str) -> dict:
    """OFS-referenced match numbers for one candidate sorting."""
    from spikeinterface.comparison import compare_two_sorters

    n_cand = int(len(cand.unit_ids))
    if n_cand == 0:
        return dict(candidate=name, n_cand=0, frac_ofs_matched=0.0,
                    frac_cand_matched=np.nan, mean_match_agreement=np.nan)
    # 1.0 ms: the online detector stamp and a sorter's template peak
    # jitter against each other by more than the 0.4 ms consensus window
    c = compare_two_sorters(ofs, cand, sorting1_name="ofs",
                            sorting2_name=name, delta_time=1.0,
                            match_score=0.5)
    m12 = c.hungarian_match_12          # ofs unit -> candidate unit or -1
    m21 = c.hungarian_match_21
    ag = c.agreement_scores             # DataFrame ofs x candidate
    matched = m12[m12 != -1]
    scores = [float(ag.loc[u, v]) for u, v in matched.items()]
    best = ag.values.max(axis=1)        # graded: each ofs unit's best score
    # merge-robust recall: of each OFS unit's spikes, the share found in
    # its single best-coinciding candidate unit (a candidate that merges
    # two human units still scores ~1 for both)
    cnt = c.match_event_count           # DataFrame ofs x candidate
    n_u = np.array([len(ofs.get_unit_spike_train(u, segment_index=0))
                    for u in cnt.index], dtype=float)
    recall = cnt.values.max(axis=1) / np.maximum(n_u, 1)
    return dict(
        candidate=name, n_cand=n_cand,
        frac_ofs_matched=float((m12 != -1).mean()),
        frac_cand_matched=float((m21 != -1).mean()),
        mean_match_agreement=float(np.mean(scores)) if scores else np.nan,
        best_ag_p50=float(np.percentile(best, 50)),
        best_ag_p90=float(np.percentile(best, 90)),
        best_recall_p50=float(np.percentile(recall, 50)),
        best_recall_p90=float(np.percentile(recall, 90)))


def spike_recovery(ofs, cand, tol_s: float = 0.001) -> tuple[float, float]:
    """Median per-OFS-unit spike recovery by the candidate's pooled train.

    Split/merge-robust detection statistic: did the automatic pool FIND
    the spikes the human kept, regardless of unit boundaries. Returns
    (median recovery, Poisson chance floor for the pooled rate).
    """
    from scratch_ns5_resort import match_rate

    if not len(cand.unit_ids):
        return 0.0, 0.0
    cand_all = np.sort(np.concatenate(
        [cand.get_unit_spike_train(u, segment_index=0)
         for u in cand.unit_ids])) / SR
    dur = float(cand_all[-1]) if len(cand_all) else 1.0
    chance = 1.0 - float(np.exp(-len(cand_all) / dur * 2 * tol_s))
    per = [match_rate(ofs.get_unit_spike_train(u, segment_index=0) / SR,
                      cand_all, tol_s) for u in ofs.unit_ids]
    return float(np.median(per)), chance


def main() -> int:
    from spikeinterface import load_extractor
    from spikeinterface.comparison import compare_multiple_sorters

    SHARDS.mkdir(parents=True, exist_ok=True)
    summ = pd.read_parquet(SUMMARY)
    meta_by_stem = (summ.groupby("stem")
                    .agg(subject=("subject", "first"),
                         implant=("implant", "first"),
                         array=("array", "first"), date=("date", "first"),
                         nev_align_med=("frac_nev_recovered", "median"))
                    .to_dict("index"))

    stems = sorted(p.name for p in (CONS / "sortings").iterdir()
                   if p.is_dir())
    print(f"{len(stems)} stems with kept sortings")
    for i, stem in enumerate(stems, 1):
        shard = SHARDS / f"{stem}.parquet"
        if shard.exists():
            continue
        meta = meta_by_stem.get(stem)
        if meta is None:
            print(f"  ! {stem}: not in summary, skipped")
            continue
        sortings, names = [], []
        for s in SORTERS:
            d = CONS / "sortings" / stem / s
            if d.exists():
                try:
                    sortings.append(load_extractor(d))
                    names.append(s)
                except Exception as exc:  # noqa: BLE001
                    print(f"  ! {stem}/{s}: {type(exc).__name__}")
        if len(sortings) < 2:
            continue
        ofs, n_ofs = ofs_sorting(stem, str(meta["implant"]),
                                 str(meta["subject"]))
        if ofs is None:
            print(f"  [{i}] {stem[:48]}: no Plexon labels, skipped")
            continue

        # per-stem clock lag (I-005): align OFS onto the sorter clock
        lag, peak = estimate_lag(ofs, sortings)
        ofs = shift_sorting(ofs, -lag)

        comp4 = compare_multiple_sorters(sortings, name_list=names,
                                         delta_time=0.4, match_score=0.5,
                                         verbose=False)
        cands = {n: s for n, s in zip(names, sortings, strict=True)}
        for k in range(2, len(names) + 1):
            cands[f"consensus{k}"] = comp4.get_agreement_sorting(
                minimum_agreement_count=k)

        rows = []
        for name, cand in cands.items():
            try:
                r = compare_pair(ofs, cand, name)
                rec, rec_chance = spike_recovery(ofs, cand)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! {stem}/{name}: {type(exc).__name__}: {exc}")
                continue
            rows.append(dict(stem=stem, **meta, n_ofs=n_ofs,
                             n_sorters=len(names), lag_ms=lag * 1000,
                             lag_peak=peak,
                             spike_rec_med=rec, spike_rec_chance=rec_chance,
                             **r))
        if rows:
            pd.DataFrame(rows).to_parquet(shard, index=False)
            r3 = next((r for r in rows if r["candidate"] == "consensus3"),
                      None)
            print(f"  [{i}/{len(stems)}] {stem[:44]} ofs={n_ofs} "
                  f"cons3: {r3['n_cand'] if r3 else '-'} units, "
                  f"recovers {r3['frac_ofs_matched']:.0%}" if r3 else
                  f"  [{i}/{len(stems)}] {stem[:44]} ofs={n_ofs}",
                  flush=True)

    parts = [pd.read_parquet(p) for p in sorted(SHARDS.glob("*.parquet"))]
    if not parts:
        print("nothing to aggregate")
        return 0
    t = pd.concat(parts, ignore_index=True)
    t.to_parquet(OUT, index=False)
    print(f"\n{t.stem.nunique()} stems -> {OUT}")
    print(t.groupby(["subject", "candidate"], observed=True)
           .agg(stems=("stem", "nunique"),
                unit_match_med=("frac_ofs_matched", "median"),
                best_ag_med=("best_ag_p50", "median"),
                best_recall_med=("best_recall_p50", "median"),
                spike_rec_med=("spike_rec_med", "median"),
                rec_chance=("spike_rec_chance", "median"),
                n_med=("n_cand", "median")).round(2).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

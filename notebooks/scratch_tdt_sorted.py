"""The legacy TDT offline sorts: what they contain and how they behaved.

Three subjects, three vintages of the same workflow:

| subject | sorts | name | era |
|---|---|---|---|
| Luigi | 144 | `baySort` | 2013 |
| Oops | 5 | `<date>_A` / `_B` | 2015 |
| Picasso | 4 | `kmsort`, `20160513A` | 2015-16 |

Two facts about the mechanism make the comparison against the online sortcode
exact rather than approximate:

- NEO applies an offline sort by overwriting `tsq["sortcode"][1:-1]`, so the
  events are identical and only their labels move -- the same fixed-event
  regime the Blackrock NEV variants gave us.
- A `.SortResult` targets exactly the store its filename names, and **zeroes
  every other store**. `eNe2.SortResult` therefore destroys eNe1's online
  codes, and any comparison must be restricted to the named store. Missing
  this would read the zeroed array as "the offline sorter rejected everything".

Codes: offline, 1..N are units and **31 is the outlier bin**, TDT's analogue
of Plexon's 255. Online, Oops and Picasso emit only 0 and 1 -- an accept flag,
not a unit id -- while Luigi's 2013 rig emitted up to 5 distinct codes and did
carry unit structure.

**No measurement floor is computable here.** A floor needs the same store
sorted twice, and no block has that: `Oops_2015_09_04-1` carries two sorts but
they cover *different* arrays. This script therefore reports what the legacy
sorts contain, not how far two of them would disagree.

Corrupt inputs are expected and are labelled rather than skipped silently: a
`.SortResult` whose payload does not match the tsq length cannot be applied,
and the estate census already flagged at least one truncated tank.

Run from repo root:

    uv run python notebooks/scratch_tdt_sorted.py [--jobs 6] [--no-waveforms]

Writes `data/derived/tdt/offline_sorts.parquet` (per channel),
`data/derived/tdt/offline_sort_units.parquet` (per unit) and
`data/derived/tdt/offline_sort_status.parquet` (one row per SortResult,
including the rejected ones).

See:
- docs/notes/tdt_corpus.md
- docs/notes/measurement_floor.md
"""

from __future__ import annotations

import argparse
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from neo.rawio.tdtrawio import EVTYPE_SNIP, tsq_dtype
from sklearn.metrics import adjusted_rand_score

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))

from scratch_rocky_resort import baseline_noise_uv  # noqa: E402
from scratch_tdt_io import array_of, channel_index, open_tank, read_channel  # noqa: E402

INV = REPO / "data" / "derived" / "tdt_inventory.parquet"
OUT_DIR = REPO / "data" / "derived" / "tdt"
OUT_CH = OUT_DIR / "offline_sorts.parquet"
OUT_UNITS = OUT_DIR / "offline_sort_units.parquet"
OUT_STATUS = OUT_DIR / "offline_sort_status.parquet"

# TDT OpenSorter's outlier bin. Events carrying it are detected but assigned to
# no unit, exactly like Plexon's 255.
OUTLIER_CODE = 31
# The project's SNR gate, restated so this script stands alone.
SNR_GATE = 4.0


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


# %%
# === Label-level comparison, straight from the tsq ===
def label_pass(job: dict) -> tuple[list[dict], list[dict]]:
    """Per-channel online-vs-offline label counts for every sort on a block.

    Reads only the tsq index, so it never touches the tev and costs a fraction
    of a second per block even for Luigi's 4 GB tanks.

    Returns ``(channel_rows, status_rows)``. Every `.SortResult` produces a
    status row whether or not it could be applied, so a corrupt file is
    visible in the output rather than absent from it.
    """
    block = Path(job["path"])
    base = dict(subject=job["subject"], block=block.name, date=job["date"])
    try:
        tev = next(block.glob("*.tev"))
        tsq = np.fromfile(tev.with_suffix(".tsq"), dtype=tsq_dtype)
    except Exception as exc:  # noqa: BLE001
        return [], [dict(**base, sort=None, status="unreadable tank",
                         detail=f"{type(exc).__name__}: {exc}"[:120])]
    if tsq.size < 3:
        return [], [dict(**base, sort=None, status="truncated tank",
                         detail=f"tsq holds {tsq.size} records")]

    body = tsq[1:-1]
    is_snip = body["evtype"] == EVTYPE_SNIP
    online = body["sortcode"].astype(np.int16)

    rows: list[dict] = []
    status: list[dict] = []
    for sr in sorted(block.glob("sort/*/*.SortResult")):
        raw = np.fromfile(sr, "int8")
        offline = raw[1024:]
        st = dict(**base, sort=sr.parent.name, file=sr.name,
                  bytes=int(raw.size), expected=int(body.size))
        if offline.size != body.size:
            status.append(dict(**st, status="corrupt",
                               detail=f"payload {offline.size} != tsq body "
                                      f"{body.size}"))
            continue
        # The store this sort actually covers; every other store is zeroed.
        store = sr.name.split(".")[0]
        sel = is_snip & (body["evname"] == store.encode())
        if not sel.any():
            status.append(dict(**st, status="store absent",
                               detail=f"{store} has no events in this tank"))
            continue
        chans = body["channel"][sel]
        on, off = online[sel], offline[sel].astype(np.int16)
        for ch in np.unique(chans):
            m = chans == ch
            o, f = on[m], off[m]
            # "Kept" means assigned to a unit: online anything above 0,
            # offline anything that is neither 0 nor the outlier bin.
            keep_on = o > 0
            keep_off = (f != 0) & (f != OUTLIER_CODE)
            both = keep_on & keep_off
            rows.append(dict(
                **base, sort=sr.parent.name, store=store,
                array=array_of(store), channel=int(ch), n_events=int(m.sum()),
                n_units_offline=int(np.unique(f[keep_off]).size),
                n_units_online=int(np.unique(o[keep_on]).size),
                frac_keep_online=float(keep_on.mean()),
                frac_keep_offline=float(keep_off.mean()),
                frac_outlier_offline=float((f == OUTLIER_CODE).mean()),
                keep_agree=float((keep_on == keep_off).mean()),
                # ARI is only meaningful when both sides partition into more
                # than one class. Oops and Picasso online have a single kept
                # class, so their ARI is 0 by construction, not by
                # disagreement; NaN says "not applicable" instead.
                ari_kept=float(adjusted_rand_score(o[both], f[both]))
                if both.sum() > 1 and np.unique(o[both]).size > 1
                and np.unique(f[both]).size > 1 else np.nan,
            ))
        status.append(dict(**st, status="ok", store=store,
                           channels=int(np.unique(chans).size),
                           events=int(sel.sum())))
    if not status:
        status.append(dict(**base, sort=None, status="no SortResult"))
    return rows, status


# %%
# === Waveform-level metrics under the offline labels ===
def unit_metrics(job: dict) -> list[dict]:
    """Amplitude, SNR and rate for each offline unit on each channel.

    This is the only sorting-based metric layer the TDT corpus has without
    re-sorting the broadband, so it is worth the tev read.
    """
    block, sortname, store = Path(job["path"]), job["sort"], job["store"]
    base = dict(subject=job["subject"], block=block.name, date=job["date"],
                sort=sortname, store=store, array=array_of(store))
    try:
        tev = next(block.glob("*.tev"))
        io, meta = open_tank(tev, sortname=sortname)
        idx = channel_index(io)
    except Exception as exc:  # noqa: BLE001
        return [dict(**base, error=f"{type(exc).__name__}: {exc}"[:140])]
    dur = meta["duration_s"]
    out: list[dict] = []
    for (st, ch), units in sorted(idx.items()):
        if st != store:
            continue
        try:
            e = read_channel(io, meta, units)
        except Exception:  # noqa: BLE001 - one bad channel must not kill a block
            continue
        if e is None or not len(e["t"]):
            continue
        noise = baseline_noise_uv(e["wf"], meta["nbefore"])
        for code in np.unique(e["code"]):
            if code in (0, OUTLIER_CODE):
                continue
            m = e["code"] == code
            amp = np.abs(e["wf"][m].min(axis=1))
            med = float(np.median(amp))
            out.append(dict(
                **base, channel=int(ch), unit=int(code),
                n_spikes=int(m.sum()),
                rate_hz=float(m.sum() / dur) if dur and np.isfinite(dur)
                else np.nan,
                amp_med=med, amp_p99=float(np.percentile(amp, 99)),
                noise_uv=noise, snr=med / noise if noise > 0 else np.nan,
                passes_gate=bool(noise > 0 and med / noise >= SNR_GATE),
            ))
    return out


def report(ch: pd.DataFrame, un: pd.DataFrame, st: pd.DataFrame) -> None:
    banner("1. Every SortResult found, including the ones that failed")
    print(st.status.value_counts().rename("files").to_string())
    bad = st[st.status != "ok"]
    if len(bad):
        print("\n  rejected:")
        cols = [c for c in ("subject", "block", "sort", "file", "status",
                            "detail") if c in bad.columns]
        print(bad[cols].head(20).to_string(index=False))
    good = st[st.status == "ok"]
    print("\n  usable sorts by subject and sort name:")
    print(good.groupby(["subject", "sort"]).size()
          .rename("files").head(12).to_string())
    print(f"  distinct sort names per subject: "
          f"{good.groupby('subject')['sort'].nunique().to_dict()}")

    banner("2. Units per channel that the legacy sorter declared")
    piv = ch.pivot_table(index="subject", columns="n_units_offline",
                         values="channel", aggfunc="size", fill_value=0)
    print(piv.to_string())
    print("\n  mean units/channel by subject:")
    print(ch.groupby("subject").n_units_offline.mean().round(2).to_string())
    print("\n  Oops and Picasso sit at ~2.0 because those sorts were")
    print("  configured for a fixed two units per channel; that is a property")
    print("  of the sort setup, not of the tissue.")

    banner("3. Online accept flag vs offline inclusion")
    print("  Both are decisions about whether an event belongs to a neuron.\n")
    print(f"  {'subject':10s} {'keep online':>12s} {'keep offline':>13s} "
          f"{'outlier':>9s} {'agree':>8s} {'ARI':>8s}")
    for subj, g in ch.groupby("subject"):
        ari = g.ari_kept.dropna()
        print(f"  {subj:10s} {g.frac_keep_online.median():12.3f} "
              f"{g.frac_keep_offline.median():13.3f} "
              f"{g.frac_outlier_offline.median():9.4f} "
              f"{g.keep_agree.median():8.3f} "
              f"{(f'{ari.median():.3f}' if len(ari) else 'n/a'):>8s}")
    print("\n  ARI is n/a wherever the online side has a single kept class:")
    print("  with nothing to partition, a zero would mean 'not applicable',")
    print("  not 'total disagreement'.")

    if not len(un):
        return
    u = un[un.get("error").isna()] if "error" in un else un
    banner("4. Per-unit metrics under the legacy labels")
    print(f"  units: {len(u)}   passing the SNR >= {SNR_GATE:.0f} gate: "
          f"{int(u.passes_gate.sum())} ({u.passes_gate.mean():.1%})\n")
    print(u.groupby("subject").agg(
        units=("unit", "size"), blocks=("block", "nunique"),
        pass_frac=("passes_gate", "mean"), amp_med=("amp_med", "median"),
        snr_med=("snr", "median"), rate=("rate_hz", "median"),
        noise=("noise_uv", "median")).round(3).to_string())

    banner("5. The project's SNR gate was tuned on Blackrock")
    print("  Blackrock units sit near SNR 5-7 and pass at 27%; these sit near")
    print("  the numbers above. A gate carried across acquisition systems")
    print("  without re-tuning changes what fraction of a corpus survives.\n")
    for subj, g in u.groupby("subject"):
        q = g.snr.quantile([0.25, 0.5, 0.75]).round(2).tolist()
        print(f"  {subj:10s} SNR quartiles {q}   pass {g.passes_gate.mean():.1%}")

    banner("6. Gated units per electrode, against the Blackrock cohort")
    per = u[u.passes_gate].groupby(["subject", "block", "array"]).size()
    allc = u.groupby(["subject", "block", "array"]).channel.nunique()
    dens = (per / allc).dropna()
    print(dens.groupby(level=0).describe().round(2).to_string())
    print("\n  Blackrock Rocky I1 sat near 0.4-1.5 gated units per electrode")
    print("  across its life, so these are low by comparison -- driven by the")
    print("  gate, not by the sorter (see section 5).")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--no-waveforms", action="store_true",
                    help="label pass only; skips every tev read")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    inv = pd.read_parquet(INV)
    have = inv[inv.n_sorts > 0].drop_duplicates("block")
    jobs = [dict(path=r["path"], subject=r["subject"], date=r["date"])
            for _, r in have.iterrows()]
    if args.limit:
        jobs = jobs[:args.limit]
    banner("Legacy TDT offline sorts -- Luigi, Oops and Picasso")
    print(f"  blocks with at least one offline sort: {len(jobs)}")
    print(have.groupby("subject").block.nunique().to_string())

    ch_rows: list[dict] = []
    st_rows: list[dict] = []
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for rows, status in ex.map(label_pass, jobs, chunksize=2):
            ch_rows.extend(rows)
            st_rows.extend(status)
    ch = pd.DataFrame(ch_rows)
    st = pd.DataFrame(st_rows)

    un = pd.DataFrame()
    if not args.no_waveforms and len(ch):
        by_path = {Path(j["path"]).name: j for j in jobs}
        wf_jobs = [dict(**by_path[b], sort=s, store=t)
                   for (b, s, t) in ch.groupby(
                       ["block", "sort", "store"]).groups]
        print(f"\n  waveform passes to run: {len(wf_jobs)}")
        un_rows: list[dict] = []
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            for i, out in enumerate(ex.map(unit_metrics, wf_jobs,
                                           chunksize=1), 1):
                un_rows.extend(out)
                if i % 20 == 0:
                    print(f"    {i}/{len(wf_jobs)}")
        un = pd.DataFrame(un_rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ch.to_parquet(OUT_CH, engine="pyarrow", index=False)
    st.to_parquet(OUT_STATUS, engine="pyarrow", index=False)
    if len(un):
        un.to_parquet(OUT_UNITS, engine="pyarrow", index=False)
    report(ch, un, st)
    print(f"\n  wrote {OUT_CH.relative_to(REPO)}  ({len(ch)} rows)")
    print(f"  wrote {OUT_STATUS.relative_to(REPO)}  ({len(st)} rows)")
    if len(un):
        print(f"  wrote {OUT_UNITS.relative_to(REPO)}  ({len(un)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

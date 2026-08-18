# Session 09 — porting the analysis to the TDT corpus

**Ask.** Three new subjects arrived on a second acquisition system — Oops and
Picasso under `Monkey Data/`, Luigi on `C:\MyData\Monkeydata\Luigi` — with the
instruction to run the same analysis the Blackrock subjects got. Two follow-on
asks landed mid-session: register the array serials the operator supplied, and
summarise the legacy TDT sorts and compare them against the modern sorters.

## Plan

1. **IO layer** (`scratch_tdt_io.py`) presenting a tank in the same shape as
   `open_nev` / `read_electrode`, so the metric code is shared not forked.
2. **Inventory** (`scratch_tdt_inventory.py`) — one row per (block, array),
   dates reconciled across folder / stem / tank clock.
3. **Sorting-free layer** (`scratch_tdt_free.py`) on every block, plus a
   broadband cross-check where `.sev` exists.
4. **Legacy sorts** (`scratch_tdt_sorted.py`) — what the 153 offline sorts
   contain, with corrupt files labelled rather than skipped.
5. **Longitudinal** (`scratch_tdt_longitudinal.py`) stacked against the
   Blackrock free layer.
6. **Docs + configs**: `docs/notes/tdt_corpus.md`, subject JSONs.

## Outcome

**Built.** All six. 370 blocks inventoried (825 block×array rows, 0 errors);
251 Oops/Picasso free-metric rows with 0 failures; 154 legacy `.SortResult`
files parsed, **none corrupt**; 14,748 per-channel legacy-sort rows.

**What the corpus turned out to be.** The plan assumed TDT would be Blackrock
with different headers. It is not:

- **The online sortcode is an accept flag, not a unit id** for Oops and
  Picasso — codes 0 and 1 only. The sorting-based metric layer that carried
  S10 does not exist for them without re-sorting broadband. Luigi's 2013 rig
  is the exception, with five codes and real partition structure.
- **No measurement floor is computable.** A floor needs one store sorted
  twice; no block has that. `Oops_2015_09_04-1` has two sorts on *different*
  arrays.
- **Rates are per store**, not per tank — Luigi 2013 runs `Raw1` at 24414 Hz
  beside `Raw2` at 48828 Hz.
- **A declared store is not an acquiring store.** Luigi declares three arrays
  and acquires on one; Picasso switches arrays for 2017.

**Two silent-corruption traps found and closed.** NEO reports
`wf_left_sweep = 20` for these snippets; the trough is at sample 8, so the
"baseline" would have spanned the whole spike and inflated every noise
estimate. And snippets are float32 volts while `read_tdt` broadband is already
µV — a ×1e6 asymmetry, cross-checked on the same events.

**The snippet noise estimator validated on a second corpus.** 88 blocks with
both estimates: ratio 1.133 (10–90%: 1.045–1.265) against the single Nigel
NEV session's 1.305. More useful than the level, the **trend** replicates —
Oops array 1 gives rho −0.623 from snippets and −0.638 from continuous. The
estimator is biased high but is a faithful longitudinal instrument, which
matters because it is all that most Blackrock sessions have.

**The legacy sorts split into two kinds.** Luigi's `baySort` discovers a
variable unit count (0–9 per channel, mean 0.25, and it rejects most channels
outright). Oops's and Picasso's sorts assign a fixed 2 units to essentially
every channel — 913 of 929 — so their unit counts describe the sort
configuration, not the tissue.

**The SNR ≥ 4 gate does not transfer across acquisition systems.** It passes
27% of Blackrock units and 15.9% of TDT ones, because TDT's online threshold
sits lower: peak SNR runs ~3.2–3.4 here against 5–7 on Blackrock.

**Diverged from the plan.** The date question needed a ruling, not a column:
the tank clock is UTC, the folder is the session date, and ten blocks carry
stem typos. Two Luigi blocks disagree by 5 and 15 days, which no timezone
explains, and are flagged unresolved.

**Deferred.** Luigi's free-metric and waveform passes — a single Luigi block
holds 1.7–3.0 GB resident and takes minutes, so those run at 2–3 workers, not
6. The legacy-vs-modern sorter comparison has only 6 blocks with both a legacy
sort and `.sev`; whether Luigi's 2013 tanks expose readable broadband inline
decides if that becomes ~150.

**New uncertainty.** Which store is which anatomy. Serials are registered;
`eNe1` still cannot be called Anterior, so everything is reported by array
number and `tdt_stores` in the subject JSONs holds nulls.

## SpikeInterface / NEO functions introduced

- `neo.rawio.TdtRawIO(dirname=<tev path>, sortname=...)` — single-block mode;
  `sortname` applies an offline sort by overwriting the tsq sortcode column.
- `neo.rawio.tdtrawio.read_tbk` — the store declaration table.
- `neo.rawio.tdtrawio.tsq_dtype` — the tank event index, read directly so a
  whole-corpus census never memory-maps a tev.
- `spikeinterface.extractors.read_tdt(folder_path=<tev path>, stream_name=...)`
  — chosen over reading `.sev` by hand because it yields a real recording
  object that `bandpass_filter` and `get_noise_levels` accept unchanged.

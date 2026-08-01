# HANDOFF — recqual

Everything load-bearing for picking this project up cold, on a new machine, with no access to the originating chat session.

Written at the point of migration from a Windows 11 workstation to a Linux VM, after sessions 1–3.

- **Repo**: https://github.com/rockystones/spikeinterface-recqual (public)
- **Package name**: `recqual` (nothing in `src/` yet — see [Status](#status))
- **Raw narrative record**: [`session_archive/session_transcript.md`](session_archive/session_transcript.md)
- **Project rules**: [`../CLAUDE.md`](../CLAUDE.md) — read this first, it is the contract

---

## 1. What this project is

A longitudinal recording-quality assessment pipeline for chronically implanted extracellular arrays, built on SpikeInterface.

- **Acquisition**: Blackrock / Ripple Neuro (nsX format)
- **Probes**: Utah arrays (16, 96 ch), NeuroNexus linear / multi-shank (16, 64 ch). Sparse geometries, **not** Neuropixels-class.
- **Goal**: track recording quality per electrode across months, so array degradation is measurable rather than anecdotal.
- **Metric stack** (CLAUDE.md defines three layers, each usable standalone):
  1. **Threshold-crossing, no sorter** — ✅ built (session 3)
  2. **Per-sorter quality metrics** — ⬜ not started
  3. **Multi-sorter consensus / agreement structure** — ⬜ not started

The multi-sorter agreement structure is the intended headline output. It is deliberately *not* collapsed into a single consensus sorting.

---

## 2. Status

| Session | Delivered | Commit |
|---|---|---|
| 1 | Data loads; Utah-96 probe attaches; both Plexon `.nev` files parse to `BaseSorting` | `71381cf` |
| 2 | Three validation figures; cached `SortingAnalyzer` with dense templates | `f661783` |
| 3 | Layer 1 threshold-crossing metric + parquet + cross-validation figure | `7329ae3` |

Nine commits total on `main`. Working tree was clean at handoff; local and `origin` in sync.

**Nothing is in `src/recqual/` yet.** All three sessions are scratch-first under `notebooks/`. Promotion to `src/` plus Tier 1 tests is deliberately deferred — the API is still finding its shape. See [`notes/testing_policy.md`](notes/testing_policy.md).

---

## 3. VM migration — do this in order

### 3.1 What git carries (≈1 MB, 26 files)

Clone gets you: `CLAUDE.md`, `pyproject.toml`, `uv.lock`, `.python-version`, three `notebooks/*.py`, all of `docs/`, and three PNG/PDF figures. That is the entire intellectual content.

### 3.2 What git does NOT carry

`.gitignore` excludes `.venv/`, `data/`, and the two large derived PDFs. You must supply `data/raw/` out of band (scp / rsync / bucket). Everything else regenerates.

**`data/raw/` transfer manifest** — 1,161,957,803 bytes total across 6 files:

| SHA256 (first 16) | Bytes | File |
|---|---:|---|
| `EEEF4BCFB925848E` | 1,050,433,868 | `Nigel_Anterior_2023-03-17_Baseline_DigitalHeadstage.ns5` |
| `EB7C383894C6348F` | 35,133,980 | `…-01.nev` (Plexon auto-sort) |
| `C5BD96F14A175987` | 35,133,980 | `…-02.nev` (manually curated) |
| `663DC3BFE851B37B` | 35,133,980 | `….nev` (raw acquisition) |
| `29A20465596C3978` | 6,119,728 | `….ccf` (Central config; unused so far) |
| `23F70602203C1940` | 2,267 | `SN 1025-001496.cmp` ← **small but critical**, the probe map |

Hashes truncated to 16 hex chars (64 bits — ample for detecting transfer corruption). Regenerate full ones with `sha256sum data/raw/*`.

> The `.cmp` is only 2 KB and easy to forget. Without it nothing works: it is the sole source of Utah electrode geometry. Do not lose it.

**`data/derived/` is fully regenerable** — do not bother transferring it:
- `sorting_analyzer_curated.zarr` (6.8 MB) ← rebuilt by the session-2 script
- `threshold_crossings.parquet` (23 KB) ← rebuilt by the session-3 script

### 3.3 Environment rebuild

```bash
git clone https://github.com/rockystones/spikeinterface-recqual.git
cd spikeinterface-recqual
uv python install 3.11
uv sync
```

`uv lock --check` passes as of commit `4b0783b`, so the lock resolves cleanly. Expected versions:

| Package | Locked |
|---|---|
| python | 3.11 (`.python-version`) |
| spikeinterface | 0.102.3 |
| probeinterface | 0.3.2 |
| neo | 0.14.4 |
| numpy | 2.4.5 |
| scipy | 1.17.1 |
| pandas | 3.0.3 |
| matplotlib | 3.10.9 |
| zarr | 2.18.7 |
| pyarrow | 24.0.0 |
| mountainsort5 | 0.5.8 |
| h5py | 3.16.0 |

⚠️ **Reproducibility caveat**: sessions 1–3 ran on the originating Windows venv, which matched these versions **except `mountainsort5` was never installed there**. A fresh `uv sync` will install it. No session-1–3 result depends on mountainsort5, so published numbers stand — but be aware the VM environment is a strict superset, not an exact clone.

### 3.4 Run order to reproduce everything

```bash
uv run python notebooks/scratch_load_nigel_2023-03-17.py            # ~30 s, stdout only
uv run python notebooks/scratch_validation_nigel_2023-03-17.py      # ~3 min first run (builds zarr cache)
uv run python notebooks/scratch_threshold_crossing_nigel_2023-03-17.py  # ~53 s
```

All three take paths from `REPO = Path(__file__).resolve().parent.parent` — **no absolute paths are baked in**, so they are OS-portable as written.

---

## 4. Windows → Linux behavioural deltas

These are the things that will actually change. Read before debugging anything that "used to work".

### 4.1 The SharedMemory workaround may no longer be needed

Session 2 hit `OSError [WinError 1450] Insufficient system resources` when `sa.compute("waveforms")` tried to allocate a **3.75 GB** `multiprocessing.shared_memory` buffer (217 units × 500 spikes × 96 ch × 90 samples × float32).

The workaround: **skip the `waveforms` extension entirely**, letting `ComputeTemplates` fall through to `estimate_templates_with_accumulator`, which streams the recording once.

On Linux this limit is governed by `/dev/shm` (typically 50% of RAM), so with ≥16 GB RAM the waveforms path will probably succeed. **Keep the accumulator anyway** — it was also *faster* (6.1 s for 217 units) and uses orders of magnitude less memory. Only reach for the waveforms extension when you genuinely need per-spike data (PCA, amplitude scatter), and if you do, prefer `format="binary_folder"` so it memmaps instead of using shared memory. Full detail in [`notes/sorting_analyzer.md`](notes/sorting_analyzer.md).

### 4.2 Headless matplotlib

The scripts call `savefig` and never `show`, but on a VM with no `$DISPLAY` set `MPLBACKEND=Agg` to be safe:

```bash
export MPLBACKEND=Agg
```

### 4.3 Line endings

Git repeatedly warned `LF will be replaced by CRLF` on Windows. Those warnings vanish on Linux. Consider normalising once, on the VM, to stop the two platforms fighting:

```bash
printf '* text=auto eol=lf\n' > .gitattributes
```

### 4.4 Tooling that gets simpler

- `.venv\Scripts\python.exe` → `.venv/bin/python`
- `uv run` works normally (on Windows it was briefly broken by invalid SI extras; fixed in `4b0783b`)
- PowerShell here-string quoting pain for commit messages → just use `git commit -m` or `-F`
- Docker for sorters (Kilosort4 etc.) is far easier: `nvidia-container-toolkit` + SI's `run_sorter(..., docker_image=...)`. This is the intended sorter path — Kilosort is deliberately **not** a Python dependency.

---

## 5. Dataset constants (hard-won — do not re-derive)

Demo session: `Nigel_Anterior_2023-03-17_Baseline_DigitalHeadstage`

| Fact | Value | Where verified |
|---|---|---|
| Broadband stream id | `"5"` | resolved dynamically by 30 kHz match in session 1 |
| Channels | 96 | asserted |
| Sampling rate | 30000.0 Hz | read from recording, never hardcoded |
| `gain_to_uV` | 0.25 µV/count, uniform | asserted in session 3 |
| Segments | **2** — `seg[0]`=2.36 s, `seg[1]`=180.01 s | session 1 |
| Segment policy | drop `seg[0]`; all analysis on `seg[1]` | [`notes/segment_handling.md`](notes/segment_handling.md) |
| Sorted units | **217** in *both* `-01.nev` and `-02.nev` | session 1 |
| Plexon unit-class ids | `0`=unsorted, `1..N`=sorted, `255`=noise | filter `{0,255}` |
| NEO spike-channel name | `chE#U` (electrode E, unit U); regex `^ch(\d+)#(\d+)$` | session 1 |
| Electrode id formula | `(bank − 'A') × 32 + elec` | [`notes/utah_channel_mapping.md`](notes/utah_channel_mapping.md) |
| Channel mapping | `channel_index + 1 == int(channel_id) == electrode_id` | 0/96 disagreements, session 2 |
| Utah pitch | 400 µm, 10×10 grid | — |
| Unused grid positions | `(0,0) (0,1) (1,1) (3,9)` — **not** the four corners | session 2 figure 1 |
| Curated-vs-auto diff | +1 unit on elec 65, −1 on elec 26 (nets to 0) | session 2 figure 2 |
| Peak≠assigned electrode | **1 / 217** — unit 297, assigned elec90, peak elec89 (adjacent) | session 2 figure 3 |

**Session 3 Layer 1 results** (300 Hz HP order-3, no CMR, `seg[1]`):

- `mad_uv`: median 12.8, IQR [12.0, 13.6], range [10.4, 15.6]
- `sd_over_mad`: median 1.07, max 1.84 → **no channel** above the 2.5 heavy-tail flag
- Crossing rate (median): 76 / 31 / 13 Hz at k = 3 / 4 / 5
- Tier 2 invariant `n_peaks(k=3) ≥ k=4 ≥ k=5`: **96/96** channels
- Cross-validation vs curated unit count: Spearman ρ = +0.42 / +0.37 / +0.38 (k=3/4/5); Pearson r = +0.48 / +0.51 / +0.52

**Timing anchors for scaling to a full cohort (~60 sessions × 96 ch):**

| Operation | Cost |
|---|---|
| Dense templates, 217 units, 180 s | 6.1 s (≈0.034 s/unit) |
| Layer 1 end-to-end, 96 ch, 180 s | 52.8 s (≈0.55 s/channel) |
| — of which `detect_peaks` × 3 thresholds | 46.7 s ← **dominates; first target for parallelism** |

`detect_peaks` ran with no parallelisation. `job_kwargs={"n_jobs": -1}` on a multi-core VM is the obvious first win.

---

## 6. Design decisions worth honouring

Each has a note; the note explains the alternative considered and why it lost.

| Decision | Note |
|---|---|
| `SortingAnalyzer`, never `WaveformExtractor` | [`notes/sorting_analyzer.md`](notes/sorting_analyzer.md) |
| Drop segments < 5 s at the IO layer; never concatenate | [`notes/segment_handling.md`](notes/segment_handling.md) |
| `select_segment_sorting()` is a free function — `BaseSorting` has **no** `select_segments` method | [`notes/segment_selection.md`](notes/segment_selection.md) |
| Probe geometry from the `.cmp`, matched by electrode id (never positionally) | [`notes/utah_channel_mapping.md`](notes/utah_channel_mapping.md) |
| 300 Hz HP order 3; **no CMR at Layer 1** | [`notes/spike_band_filter.md`](notes/spike_band_filter.md) |
| Threshold crossing = local minima below −k·MAD, 1.0 ms refractory | [`notes/threshold_crossing.md`](notes/threshold_crossing.md) |
| Peak-channel assignment via `get_template_extremum_channel` | [`notes/template_extremum_channel.md`](notes/template_extremum_channel.md) |
| Blackrock IO conventions, stream ids, gain | [`notes/blackrock_loading.md`](notes/blackrock_loading.md) |
| Test tiers; why no tests yet | [`notes/testing_policy.md`](notes/testing_policy.md) |

**Why no CMR at Layer 1** is the decision most likely to be second-guessed: Layer 1 deliberately characterises the *raw* noise floor so that CMR can later be quantified as a separate Δ-MAD measurement rather than silently folded into the baseline. Revisit at Layer 2, not before.

---

## 7. Gotchas

1. **`get_noise_levels` caches on the recording object** and does not reliably key on `method`/`return_scaled`. Always pass `force_recompute=True` when you need MAD *and* SD, or scaled *and* raw, from the same recording.
2. **`detect_peaks` units**: the `by_channel` detector compares **raw** traces against `noise_levels × detect_threshold`. Noise levels handed to it must be `return_scaled=False`. Returned per-peak `amplitude` is likewise raw — multiply by `gain_to_uV` for µV. Getting this backwards silently produces a 4× wrong threshold.
3. **`detect_peaks` defaults to `method='locally_exclusive'`**, not `by_channel`. Always pass it explicitly.
4. **Never let NEO auto-discover `.nev` files.** Three `.nev` files share one base name (`.nev`, `-01.nev`, `-02.nev`); auto-discovery picks arbitrarily. Always construct `BlackrockRawIO` per explicit path.
5. **Blackrock electrode ids can be non-contiguous** in other files even though they are contiguous here. The identity `channel_index + 1 == channel_id` is a *property of this recording*, re-asserted per file — never an assumption.
6. **`figures/validation/01_channel_mapping.pdf` re-renders as "modified"** on every run: matplotlib embeds a creation timestamp, so the bytes change while content does not. Harmless. If it becomes annoying, gitignore the PDF and keep the PNG.
7. `return_scaled` vs `return_in_uV` parameter naming has shifted across SI versions. This is why the SI pin matters.

---

## 8. Verifying the VM is correct

Run the three scripts in order (§3.4). The VM is good if:

- [ ] Session 1 prints `channels 96`, `sampling_rate 30000.0 Hz`, 2 segments (2.36 s / 180.01 s), `unmapped contacts: 0`, and **217** sorted units for both `.nev` files
- [ ] Session 2 reports `0` channel-mapping disagreements and `1 / 217` peak-vs-assigned mismatches (unit 297)
- [ ] Session 2 writes a 217-page PDF and a 6.8 MB zarr cache
- [ ] Session 3 reports Tier 2 invariant `96 / 96` and Spearman ρ positive at all three k
- [ ] `uv run python -m ruff check notebooks/` is clean

Any deviation in the **217 / 0 / 1 / 96-of-96** numbers means something is wrong with the data transfer or the environment, not with the analysis.

---

## 9. Suggested next steps

Roughly in dependency order. One task per session; `/clear` between unrelated tasks (CLAUDE.md rule).

1. **Parallelise `detect_peaks`** — pass `job_kwargs={"n_jobs": -1}`. Should cut Layer 1 from 53 s to single digits and is the prerequisite for cohort-scale runs.
2. **Promote Layer 1 to `src/recqual/quality/`** with Tier 1 synthetic-data tests per [`notes/testing_policy.md`](notes/testing_policy.md). The API has now stabilised across one full session, which was the stated bar.
3. **Build `ElectrodeMetadata`** (`src/recqual/io/electrode_metadata.py`). CLAUDE.md is emphatic that all metrics report against this, not anonymous channel indices, and that its schema must not be quietly redesigned. Impedance is the first multimodal field.
4. **Layer 2**: run the sorter pool (MountainSort5, Tridesclous2, Kilosort4 with `do_correction=False`) via Docker, then `compute_quality_metrics`.
5. **Layer 3**: `compare_multiple_sorters` agreement matrix, reported as longitudinal structure — explicitly *not* collapsed to one consensus sorting.
6. **Scale to the cohort**: apply Layer 1 across all sessions, aggregate to long-format Parquet for cross-session trends.
7. **Quantify CMR** as the deferred Δ-MAD measurement (§6).

Two loose ends worth closing early: add a root `README.md` (the repo has none, and `pyproject.toml` references one), and pick a `LICENSE` (pyproject declares MIT but no license file exists).

---

## 10. Security note

This repo is public. At migration it was audited against 11 credential patterns (GitHub classic/fine-grained/OAuth PATs, Anthropic, OpenAI, AWS, Slack, private-key blocks, bearer headers, URLs with inline credentials) across **all tracked files and the full session transcript**. Clean.

The GitHub token is held by **Windows Credential Manager** (`credential.helper = manager`) and has never been written to the repo, the transcript, or any config file under version control. The remote is plain HTTPS with no embedded credentials.

On the VM, authenticate with a **fresh** credential — `gh auth login`, or SSH keys, or a git credential helper. Do not copy the Windows token across; rotate it if it ever touched a shell history or a file.

The archived transcript was sanitised before commit: local Windows user paths redacted to `C:\Users\<user>`, e-mail addresses redacted (GitHub noreply addresses exempted — already public in commit metadata), base64 figure payloads stripped, progress-bar spam collapsed, oversized tool payloads truncated. The exporter ([`session_archive/export_transcript.py`](session_archive/export_transcript.py)) re-scans its own output and exits non-zero if any pattern survives. It resolves the local account name at runtime rather than hardcoding it, so the sanitiser does not itself leak the identifier it removes.

### Known false positive

A **case-insensitive** grep for AWS keys will match `akIAgLRHAFUcUUrIK664` around line 8838 of the transcript archive. This is **not a credential**. It is a fragment of base64-encoded PNG data (one of the validation figures, read inline during session 2) that happens to contain the letters `akia`. Genuine AWS access keys are uppercase `AKIA` followed by exactly 16 uppercase alphanumerics, so GitHub's own secret scanning does not flag it. It survives in the archive only because the audit that identified it is itself part of the recorded session. Left in place deliberately, as scrubbing it would make that audit narrative incoherent.

# Running the sorters at corpus scale, and the six ways it goes wrong

`scratch_ns5_resort.py` over 626 sessions. The algorithms are the easy part;
everything below is what actually cost time, and none of it is in
SpikeInterface's documentation because none of it is SpikeInterface's fault.

## 1. Partial runs overwriting whole-corpus artifacts

Three separate instances of one mistake, each found only by accident:

| artifact | what a scoped run did |
|---|---|
| session shard | `--sorters kilosort4` replaced a shard holding three CPU sorters with one KS4 row |
| `ns5_sorters.parquet` | rebuilt from the run's own frames, so a 2-session run left a 2-session corpus summary |
| `cohort_sessions.parquet` | `--part tdt` dropped every extension subject, deleting Chase |

The shard case destroyed real results: the two sessions where Kilosort4 first
succeeded lost their MountainSort5, Tridesclous2 and SpykingCircus2 rows, which
is why no session in the corpus carried all four sorters until it was repaired.

**The rule:** anything written at the end of a run must merge with what is
already on disk, or be rebuilt from the per-item files rather than from the
current run's memory. Treat every "write the aggregate at the end" line as
guilty until checked.

## 2. Worker pools that outlive their child

SpykingCircus2 and Tridesclous2 spawn joblib pools. Those workers **survive the
child that started them even on a clean exit**, and `Process.terminate()` kills
only the child. Eighteen were found holding **30 GB of commit** — most of the
way to the ceiling — with no failure recorded anywhere, because the sorter had
succeeded.

Reaping them dropped commit from 72% to 43% instantly.

`_reap_descendants()` now sweeps after every child. It matches on the dead
child's PID rather than asking psutil for its children: by the time `join()`
returns the child is gone and has no children to report, while Windows leaves
orphans carrying the stale `ppid`. Matching on that specific PID rather than on
"any parentless python" keeps it from touching unrelated work.

## 3. MountainSort5's memory scales with events, not with file size

The clearest single limit found. On `20230622-131651-Medial`:

| | value |
|---|---|
| NEV events in 180 s | **464,636** (2.05× the corpus median; bigger than 112 of 128 sessions) |
| MountainSort5 | **cannot complete** — committed 58 → 61 → 65 GB and climbing, twice |
| Tridesclous2 | 198 units, 206 s |
| SpykingCircus2 | 264 units, 228 s |
| Kilosort4 | 249 units, 182 s |

A ~1 GB file, and MountainSort5 needs more than 65 GB for it while the other
three finish in under four minutes. Typical sessions cost it ~10 GB. **Judge
the cost by event density, not by megabytes** — Fisk's Medial array runs
`peak/noise` around 16 against ~6 on quiet sessions, and every memory event in
this corpus landed on a Medial session.

## 3b. Kilosort4's spatial defaults are Neuropixels geometry — and there is no one-line fix

A Utah array is a 10×10 grid at **400 µm in both axes** (confirmed off the
probe: x = 0, 400 … 3600). Kilosort4's relevant defaults are

| param | default | meaning here |
|---|---|---|
| `dmin` | auto | correctly picks up 400 from the y pitch |
| `dminx` | **32** | Neuropixels horizontal spacing |
| `max_channel_distance` | **32** | no channel is within 32 µm of any other |

Three Fisk sessions die on

```
ValueError: `get_data_cpu` never found suitable channels in `clustering_qr.run`.
dmin, dminx, and xcenter are: (400.0, 32, 1796.3)
```

with the GPU at 33% and a 0.98 GB peak — never a memory problem.

**Setting `dminx` from the probe was tried and reverted.** Two controlled
re-runs, same data, only that parameter changed:

| session | `dminx=32` | `dminx=400` |
|---|---|---|
| `20230906-122625-Medial3min` | 171 units, **1.51×** the other three sorters | **108 units, ratio 0.96** — the over-count is gone |
| `20240724-102500-Medial3Min` | 141 units | **session fails outright** |

And the three original failures **still fail** at `dminx=400`, so `dminx` was
never their cause. `max_channel_distance` is still at 32 and `xcenter` lands
between columns (1804 against columns at 1600 and 2000), so more than one
parameter is involved.

Left at Kilosort4's defaults, so every KS4 row in the corpus is at least
mutually comparable. `KS4_DMINX_FROM_PROBE` turns the experiment back on.

**What this actually establishes.** Not that the over-splitting is an artefact,
and not that it is real — that one session's 1.51× collapses to 0.96× on a
single spatial parameter, while another session stops running at all. So:

> **Kilosort4's unit counts on a 400 µm Utah array are not a property of the
> sorter.** One parameter moves them 37% and decides whether a session
> completes. Every four-sorter spread in this note — 1.65× on Fisk, 2.43× on
> Nigel, 2.44× on Rocky — is conditional on `dminx=32` and should not be quoted
> as a Kilosort4 characteristic without a proper parameter sweep.

CLAUDE.md's "Kilosort4 over-splits on sparse arrays" gotcha is *unresolved*
rather than confirmed or refuted. A sweep over `dminx` and
`max_channel_distance` against a fixed reference — Plexon's own sort, or
agreement with the other three — is what would settle it.

One useful by-product: re-running a session reproduced 141 units exactly, so
Kilosort4 is deterministic here and a parameter sweep would be measuring the
parameter rather than run-to-run noise.

## 4. A hung job looks exactly like an idle one

MountainSort5 finished a session, SpykingCircus2 started, printed `Recording
too large to be preloaded in RAM...` and stopped. Two hours later: parent at
274 s CPU unchanged, child at **2 s CPU over 34 minutes**, 49 threads, 8 MB
resident.

**Memory monitoring cannot see this.** At the moment of the stall the machine
read 2.2 GB free, 53% commit, python holding 0.01 GB — indistinguishable from
healthy idle. What caught it was a check on **shard-file mtime**: no new shard
in 120 minutes while python is alive.

Any watch on a long job needs a liveness signal from the job's own output, not
from its resource use. The per-sorter timeout eventually fired and recorded
`TIMEOUT after 3600s` cleanly, so the design worked — the monitor just could
not have told anyone for an hour.

## 5. Commit, not free RAM, is the number that matters

Free physical RAM routinely falls under 1 GB during a normal MountainSort5 pass
and recovers. Alerting on it fires roughly 250 times across a corpus run and
means nothing.

Commit against the current pagefile is the freeze signal, and it must be read
as a **fraction of the current total** — a reboot resized the pagefile from
108.8 GB to 95 GB and later grew it to 103.6 GB, so any hardcoded ceiling is
wrong within a day.

The dangerous shape is a process with a large *commit* and a small working set:
one held 47.8 GB committed against 1.4 GB resident, which no working-set-based
check would notice.

Automate the intervention. The 15-minute guard is too slow for something that
moved 87% → 96% inside two minutes; a 60-second watch with an auto-kill at 96%
caught it. 96% is where a failed commit stops being the job's problem and
becomes the machine's.

## 6. Purging scratch deletes the evidence

Failure rows read `child exited N; see <stem>__<sorter>` — naming the work
folder. `purge_work()` then deleted it, so the message pointed at nothing. Two
Kilosort4 failures were recorded and their logs destroyed in the same pass.

Scratch is now kept whenever any sorter on the session failed.

## What the corpus run cost

512 jobs on Fisk, 5 errors. Four of the five are one array:

| sorter | ok | median units | median s |
|---|---|---|---|
| tridesclous2 | 128/128 | 94 | 151 |
| mountainsort5 | 127/128 | 117 | 262 |
| spykingcircus2 | 127/128 | 132 | 167 |
| kilosort4 | **125/128** | 157 | 158 |

Kilosort4 now runs everywhere once the working-directory fix landed
([[kilosort4_gpu]]): `C:` went from **0 of 43 to 38 of 43**, and the corpus
carries **221 four-sorter sessions**.

That makes the per-subject comparison real, and it separates cleanly.
`fig_subject()` in `scratch_ns5_figures.py` is the reproducible version
(`figures/sorters/M5_subject.png`); the ratio is **paired inside the session**
— `kilosort4 ÷ mean(other three)` per session, then the median over sessions —
because the alternative, dividing the two subject-level medians, compares
sessions that are not comparable and reads 0.03 to 0.13 higher.

| subject | sessions | span | spread | KS4 ÷ others | IQR |
|---|---|---|---|---|---|
| Fisk | 124 | 2023-06 → 2025-05 | 1.65 | **1.33** | 1.25–1.42 |
| Nigel | 40 | 2023-01 → 2024-10 | 2.43 | **2.04** | 1.87–2.17 |
| Rocky **I1** | 37 | 2018-02 → 2023-10 | 2.54 | **2.16** | — |
| Rocky **I2** | 20 | 2025-04 → 2025-06 | 2.39 | **1.80** | — |

**Rocky must be split by implant.** It carries two, and the array labels
`Anterior`/`Posterior` are reused across both while the serials and the
coatings change ([[cohort_definition]]). Pooled, Rocky reads 1.98 on 57
sessions; that is an average of two populations differing at **p = 4.2e-07**,
not a property of the animal. Splitting also sharpens the picture — Rocky I1
at 2.16 sits beside Nigel at 2.04, against Fisk at 1.33.

Nigel and Rocky I1 agree at ~2.1 against Fisk's 1.33, so the animal, not the
sorter, sets the size of the over-split. **Rocky's number moved from 1.73 to
1.98 when its history was included** — the earlier figure came from the 20
sessions that happened to sit on `D:`, which were exactly implant 2. A subset
selected by an unrelated bug is not a random subset, and here the bug had
selected an entire implant.

The right panel of M5 answers the obvious follow-up: the ratio does not drift
across an implant's life. Each animal holds its own offset from 2018 to 2025,
which rules out the over-split being a function of how degraded the array is.

Every number here remains conditional on `dminx = 32` (§3b).

## Related

[[kilosort4_gpu]] for the CUDA and drive fixes, [[robustness]] for what the
sorter spread means once measured, [[ns5_plan]] for the design.

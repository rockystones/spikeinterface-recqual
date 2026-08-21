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
> completes. The 1.65× and 2.30×/2.56× four-sorter spreads reported from this
> corpus are conditional on `dminx=32` and should not be quoted as a KS4
> characteristic without a proper parameter sweep.

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

Kilosort4 runs at 98% on Fisk against ~3% on Nigel and Rocky, whose attempts
predate the `work_root` drive fix ([[kilosort4_gpu]]) and died before reaching
the GPU. Until those are re-run, the four-sorter spread is 123 Fisk sessions
against one session each from Nigel and Rocky, and **no per-subject claim about
Kilosort4 over-splitting is supported yet**.

## Related

[[kilosort4_gpu]] for the CUDA and drive fixes, [[robustness]] for what the
sorter spread means once measured, [[ns5_plan]] for the design.

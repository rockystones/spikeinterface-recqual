# Kilosort4 on a Blackwell GPU

Kilosort4 produced **zero results in 76 attempts** across this project before
the cause was identified. It is not a sorter problem, a driver problem or a
Docker problem.

## The error, and what it actually means

```
RuntimeError: CUDA error: no kernel image is available for execution on the device
```

PyTorch says it plainly when asked directly:

```
NVIDIA GeForce RTX 5060 Laptop GPU with CUDA capability sm_120 is not
compatible with the current PyTorch installation.
The current PyTorch install supports CUDA capabilities
  sm_50 sm_60 sm_70 sm_75 sm_80 sm_86 sm_37 sm_90
```

| | value |
|---|---|
| stock image torch | **2.7.1+cu118**, built against CUDA 11.8 |
| its compiled architectures | sm_50 … **sm_90** (stops at Hopper) |
| this GPU | **sm_120** (Blackwell) |
| host driver | 595.79, CUDA 13.2 |

A PyTorch wheel carries machine code only for the architectures it was compiled
for. `sm_120` is absent, and so is any `compute_120` PTX entry, so there is no
JIT fallback either.

**What is not wrong.** `docker run --gpus all` reaches the GPU and enumerates
it correctly, so the driver, NVIDIA Container Toolkit and GPU passthrough are
all working. And it is not a torch *version* problem: 2.7.1 supports sm_120 —
but only in its **cu128** build. The image shipped the cu118 flavour.

## The fix

`docker/Dockerfile.ks4-cu128` derives from the stock image and replaces only
the wheel:

```dockerfile
FROM spikeinterface/kilosort4-base:latest
RUN pip install --force-reinstall --no-cache-dir \
        torch --index-url https://download.pytorch.org/whl/cu128
```

The build asserts `sm_120 in torch.cuda.get_arch_list()`, so a stale or wrong
wheel fails at build time rather than one session into a corpus run.

`scratch_ns5_resort.CUSTOM_IMAGE` maps `kilosort4 -> ks4:cu128`, and
`sorter_kwargs` uses it in place of `docker_image=True` **only if the image is
present locally** — otherwise it falls back to SpikeInterface's default, so the
code still runs on a machine that has not built it.

## Diagnosing this class of failure elsewhere

The general check, for any containerised GPU sorter:

```bash
docker run --rm --gpus all <image> python -c \
  "import torch; print(torch.__version__, torch.version.cuda); \
   print(torch.cuda.get_arch_list()); print(torch.cuda.get_device_capability())"
```

If the device capability is absent from the arch list and no matching
`compute_*` PTX entry exists, no amount of re-running will help. The
alternatives are a rebuilt wheel, `torch_device="cpu"` (works, far too slow for
96 channels), or dropping the sorter and saying so.

## Three layered faults, each hidden by the one before

The CUDA error was the first of three. Each only became visible once the
previous was fixed, and the failure *moved deeper* each time — which is how you
can tell a fix worked even before it succeeds.

| # | error | where it failed |
|---|---|---|
| 1 | `CUDA error: no kernel image is available` | before any computation |
| 2 | `ValueError: too many values to unpack (expected 16)` | the SI ↔ Kilosort API boundary |
| 3 | `Numba needs NumPy 2.4 or less. Got NumPy 2.5` | import time, **self-inflicted** |
| — | `Found array with 0 sample(s) ... TruncatedSVD` | deep inside KS4's clustering |

**(2) is worth knowing beyond Kilosort.** SI 0.102.3 unpacks exactly 16 values
from `get_run_parameters(ops)` and its newest version guard is `4.0.34`; the
image shipped 4.1.7. `check_sorter_version()` guards only the **lower** bound
(`>= 4.0.16`), so a too-new sorter passes the check and dies later with an
error that looks like a data problem. Any containerised sorter here can hit
this as its image drifts forward.

**(3) was mine.** `pip install --force-reinstall torch` reinstalls the whole
dependency tree, not just torch, and bumped NumPy past what the image's numba
accepts. Pinning `numpy<2.5` alongside the torch pin fixes it.

The last row is not a fault. Kilosort4 reaching `TruncatedSVD` with zero
samples means it loaded, preprocessed and ran detection, and found no spikes —
on `Nigel_Anterior_2023-01-24`, the session the owner confirmed is mostly noise
from a global connection issue, and where MountainSort5 also returns 0 units.
**KS4 raises where MountainSort5 returns zero**, so a dead session produces an
error row rather than a legitimate zero. Do not count those as environment
failures.

## It works

The first two Kilosort4 results in this project:

| session | units | spikes |
|---|---|---|
| `Nigel_Posterior_2023-01-24` | **248** | 427,274 |
| `Rocky_Anterior_2025-06-05` | **276** | 731,089 |

Both numbers looked like CLAUDE.md's recorded gotcha — *"Kilosort4 over-splits
on sparse arrays"* — showing up on first contact, and at the time that is what
they were taken for.

**That reading is now qualified.** On 221 four-sorter sessions the effect is
real but strongly subject-dependent (Fisk 1.33×, Nigel 2.04×, Rocky 1.98×), and
every one of those numbers is conditional on `dminx = 32`, Kilosort4's
Neuropixels horizontal-spacing default. Changing that one parameter moves a
session's count 37% and can stop it running altogether. See
[`sorter_operations`](sorter_operations.md); the gotcha is **unresolved**, not
confirmed.

## Resolved: the process must sit on the recording's drive

**Corrected twice.** The first diagnosis was "recording and output on different
drives"; the second was "Kilosort4 cannot read a recording on `C:`". Both were
wrong, and neither was a Docker problem.

The container run **succeeds**. `spikeinterface_log.json` for a "failed"
session reads `error: false`, and the sorter folder holds a finished
`in_container_sorting`. The failure is on the way back.

`container_tools.path_to_unix` strips the drive letter, so
`C:\MyData\...` is written into `spikeinterface_recording.json` as
`/MyData/...`. That is correct *inside* the container, where SI binds the
folder at exactly that path. But `read_sorter_folder()` re-reads that JSON
**on the host**, and on Windows a leading-slash path resolves against the
**current drive**:

| process CWD | `/MyData/...` resolves to | `/Claude Code/...` resolves to |
|---|---|---|
| `D:\…` (the repo) | `D:\MyData\…` — missing | `D:\Claude Code\…` — **found** |
| `C:\…` | `C:\MyData\…` — **found** | `C:\Claude Code\…` — missing |

That is the whole effect. With the repo on `D:`, every `D:` recording resolved
and every `C:` one did not — **185 of 195 against 0 of 43**, which looked like
a drive capability and was really a working-directory coincidence.

**The fix is two lines**: `run_sorter_guarded` chdirs to the recording's drive
around the `read_sorter_folder()` call and restores afterwards. The first
`Rocky_Anterior_01-10-2019` run after it returned **275 units, 649,362 spikes**
on a session that had failed every previous attempt.

Nothing had to be staged or copied. `docker run -v "C:\MyData\…:/probe"` was
always able to list all 431 `.ns5`, which is why the mount tests kept coming
back clean while the runs kept failing.

## The work folder still follows the recording's drive

Kept, but for a different reason than it was written for. Scratch on the
recording's drive keeps a `recording.dat` copy per sorter — about 70 GB across
one corpus pass — off a drive that is short of space. It has nothing to do with
Kilosort4, and putting the scratch on `C:` beside the recording never helped.

## Perspective

Kilosort4 is the only sorter in this project's pool that needs a GPU. The other
three completed **325 successful jobs on CPU** while this was broken, and they
agree with each other to within 1.43x on unit counts. Adding KS4 adds a fourth
opinion to the comparison; it was never blocking the pipeline.

## Related

[[robustness]] Q1 for the cross-sorter comparison KS4 is absent from,
[[ns5_plan]] for the re-sorting design.

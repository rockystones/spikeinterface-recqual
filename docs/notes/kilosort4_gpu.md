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

## Perspective

Kilosort4 is the only sorter in this project's pool that needs a GPU. The other
three completed **325 successful jobs on CPU** while this was broken, and they
agree with each other to within 1.43x on unit counts. Adding KS4 adds a fourth
opinion to the comparison; it was never blocking the pipeline.

## Related

[[robustness]] Q1 for the cross-sorter comparison KS4 is absent from,
[[ns5_plan]] for the re-sorting design.

#!/usr/bin/env bash
# Runtime verification for ks4:cu128.
#
# Must run WITH --gpus, which is exactly why it is not a build step: `docker
# build` has no GPU, CUDA cannot initialise, and `torch.cuda.get_arch_list()`
# returns [] -- an assert there fails a perfectly good image.
set -euo pipefail
IMAGE="${1:-ks4:cu128}"
docker run --rm --gpus all "$IMAGE" python -c '
import torch
print("torch      :", torch.__version__, "| built for CUDA", torch.version.cuda)
print("available  :", torch.cuda.is_available())
archs = torch.cuda.get_arch_list()
print("arch list  :", archs)
cap = torch.cuda.get_device_capability()
sm = "sm_%d%d" % cap
print("device     :", torch.cuda.get_device_name(0), cap, sm)
assert sm in archs, "%s missing from %s -- this is the original bug" % (sm, archs)
# Importing cleanly is not the test. The previous fix imported fine and still
# died at the first kernel launch, so actually launch one.
x = torch.randn(4096, 4096, device="cuda")
torch.cuda.synchronize()
print("matmul mean:", round(float((x @ x.T).mean()), 4))
print("PASS")
'

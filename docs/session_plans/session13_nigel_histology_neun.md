# Session 13: Nigel peri-implant histology - NEUN spatial pipeline

## Plan

Stand up an analysis pipeline for the confocal IF sections around Nigel's
lateral TNP Utah array (`D:\Claude Code\Histology data\MonkeyUtahArray`):
decode the slide/slice/depth tables, detect and identify shank holes across
the 375-1800 um depth ladder despite tissue distortion and the oblique
slicing plane, segment NEUN (C3) with the lab's Cellpose settings, and
produce NEUN density vs distance-from-shank profiles per depth with NRRC as
control.

## Outcome

- Built `MonkeyUtahArray/analysis/` (scripts 00-06 + README): inventory,
  tissue/hole detection, per-section lattice fit + trusted-link depth chain
  giving every hole a global (i,j) shank identity, cpsam segmentation,
  density profiles, per-shank tip-depth model.
- 18 NRRT sections chained with zero broken links (frac-dev <= 0.14,
  basis rotation <= 2.8 deg); hole counts fall 74 -> 7 across depth as the
  oblique plane exits the shanks; median hole radius tapers 65 -> 20 um.
- Cellpose validation: fresh cpsam matches the lab's curated GUI seg on
  NRRT_A8_SB at 99.2%/99.6% (8329 vs 8299 cells).
- Main result (all 15 NRRT sections + 2 NRRC): every depth shows a NEUN
  deficit at 0-25 um from the hole edge recovering by ~75-100 um, and the
  near(0-50)/plateau(100-200) ratio rises near-monotonically with depth,
  0.41 (375 um) -> ~0.65 (1000-1300) -> 0.84 (1800, below most tips):
  peri-shank neuronal loss is worst near the pad/surface.
- NRRT_A8_SA is dim/diffuse in NEUN in both acquisitions (flagged; its
  within-section ratio is still in-trend).
- Diverged from plan: none major; GPU cellpose impossible because Windows
  App Control blocks CUDA torch DLLs (and scipy.signal `_spline`) - CPU
  torch used (~6.4 min/section), numpy-FFT xcorr replaces fftconvolve.
- New uncertainty: wire-bundle-side rows (j>=8) damaged in many sections -
  tip estimates there biased; A4 slide is a PIEZO1 panel mislabeled as NEUN.
- Deferred: 12-bit OIR intensity extraction, IBA1/GFAP channels, absolute
  (i,j) -> CMP electrode mapping, per-shank NEUN profiles, 3D visualization.
- SI functions used: none (pure image analysis session; no SpikeInterface
  calls).

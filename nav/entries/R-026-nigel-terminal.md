---
id: R-026
type: result
status: current
title: Nigel terminal session analyzed end to end - 6 gated units remain on the TNP array; sorter outputs are method artifacts at this signal level
created: 2026-09-25
actor: agent
basis: recorded
parent: P-03
informs: [Q-006, R-016]
source: [notebooks/scratch_nigel_terminal.py, data/derived/nigel_terminal, figures/nigel/terminal_overview.png, docs/notes/nigel_terminal.md]
---
Owner asked (2026-09-25) whether the terminal recordings
(Monkey Data/Nigel/Terminal recordings, recorded 2025-09-25) were
analyzed. File-level layers already covered them (inventory, 4
previews, exact mmp2p on the manual sort: 48 units / 34 active
channels / 61.7 uV, stripe pass, cohort row). Added now:

- CONTINUOUS-DATA CONSENSUS: the NS5 lives only as NPMK openNSx v7.3
  .mat exports (74-82 s, 96 array ch of 254, gain 0.25 uV/ct);
  scratch_nigel_terminal.py rebuilds SI recordings from them (band
  from the embedded extended header - the terminal export is
  BROADBAND, 0.3 Hz corner, unlike the 250-Hz-high-passed regular
  Nigel ns5 corpus) and runs the full pool (MS5/TDC2/SC2 native, KS4
  in ks4:cu128 with pypi SI install + dminx=400).
- RESULT: unit counts are pure method artifacts at this signal
  level - MS5 10-14, KS4 42-47, TDC2 91-141, SC2 143-218 per file,
  with 0-15 units matching between ANY pair at 0.5 agreement, and
  manual-vs-KS4 matching 0 of 47-vs-47. Nothing here resembles the
  healthy-era structure (R-016: consensus tracks human counts).
- GATE AUTOPSY: of the 47 scoreable manually sorted units, 6 pass
  the physics gate; 34 fail SNR>=4, the rest spike-count/shape. The
  honest terminal yield of the TNP array is ~6 isolatable units on a
  96-channel array (noise floor 8.0 uV, normal), against 34 channels
  carrying SOMETHING sortable by hand.
- Only the Anterior/TNP array was recorded (all files map to SN1496
  geometry), consistent with the owner's report that the Ctrl-family
  array had failed - its last recorded sessions are late-2024, and
  the context figure shows both trajectories
  (figures/nigel/terminal_overview.png).
- Discrepancy noted: the cohort-layer row reads 0 gated units for
  the same file (different gate implementation); the per-unit audit
  (6/47) is the auditable number - manual_gate_audit.parquet.

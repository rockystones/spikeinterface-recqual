---
id: A-003
type: aim
status: active
title: A pipeline a new student can run end to end, MATLAB-consumable
created: 2026-05-20
actor: agent
basis: recorded
scope: src/recqual package + parallel MATLAB layer; nothing promoted from notebooks yet
source: [docs/roadmap.md, CLAUDE.md]
---
Success criterion: `src/recqual` modules with Tier-1 tests, phase tutorials,
and NPY/JSON/Parquet outputs a MATLAB layer consumes without pickle.
Approach: scratch-first, promote at phase boundaries. Nothing is promoted yet
(W-007, W-008); every analysis so far lives in notebooks/scratch_*.py.

---
id: I-001
type: issue
status: resolved
title: 431 Rocky I1 sessions carried I2 serials (collapsed lookup key)
created: 2026-09-12
owner: agent
basis: recorded
closed: 2026-09-12
source: [docs/notes/serial_resolution.md]
---
Four scripts collapsed serials across implants; ns5_free/ns5_sorters labels and
the sorters' CMP geometry were wrong for Rocky I1. Values unaffected
(geometry-free metrics); position-dependent readings of those sorts remain
untrustworthy until re-run. Fixed by D-005; tables repaired.

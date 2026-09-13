---
id: D-005
type: decision
status: accepted
title: Resolve array serials by (subject, implant, array), never (subject, array)
created: 2026-09-12
owner: agent
basis: recorded
resolves: [I-001]
evidence: [docs/notes/serial_resolution.md]
source: [CLAUDE.md, docs/notes/serial_resolution.md]
---
Context: Rocky's two implants reuse the Anterior/Posterior labels; a collapsed
key let I2 overwrite I1 (I-001).
Options: keep collapsed key and special-case Rocky; key by implant everywhere.
Choice: implant in the key, taken from the session row; helpers fixed at four
sites, tables repaired.
Consequences: any future subject with reimplants is safe by construction.

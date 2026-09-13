---
id: D-006
type: decision
status: accepted
title: Blackrock impedance joins recordings on channel_id (proven 1248/1248)
created: 2026-08-22
owner: agent
basis: recorded
evidence: [docs/notes/impedance_sources.md]
source: [docs/notes/impedance_sources.md]
---
Context: the factory workbook's rows are headed elec1..128, a misnomer.
Options: join on electrode number; join on channel id.
Choice: channel id - proved exactly (1,248/1,248 positions across 13 arrays);
joining on electrode number yields a complete, plausible, permuted table.
Consequences: Fisk's Cerebus impedance is map-free; only the potentiostat
chain needs D-011.

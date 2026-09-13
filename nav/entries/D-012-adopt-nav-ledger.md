---
id: D-012
type: decision
status: accepted
title: The nav ledger is the project's navigation system; NAV.html supersedes the dashboards
created: 2026-09-13
actor: agent
basis: recorded
decided_by: human
pinned: true
summary: Cross-session memory lives in nav/entries; STATE.md is the orientation page; generated files are never hand-edited
informs: [I-002, W-011]
source: [nav/PILOT-HANDOFF.md, "D:/Claude Code/nav-kit/NAV-TEST-A-steady-state.md"]
---
Context: the pilot (2026-09-12) showed the hand-built dashboards freeze and
drift while docs/notes stay current; the owner directed running Test A.
Options: keep hand-curated dashboards; adopt the ledger with generated views.
Choice: schema v0.2 ledger in nav/entries, nav.py generating STATE.md /
DELTA.md / NAV.html, hooks printing the brief at session start and closing
out before compaction. session_map.html and recqual_flow.html move to
nav/legacy as records.
Consequences: file-as-you-go becomes part of normal work (CLAUDE.md
snippet); telemetry runs for the steady-state test window.

---
id: D-010
type: decision
status: accepted
title: Min_P2P_exclusion = 20 uV is not applied anywhere unless explicitly requested
created: 2026-08-15
owner: agent
basis: inferred
source: [chat 2026-08 (standing instruction; not recorded in repo files)]
---
Context: a legacy exclusion threshold exists in the MATLAB layer's history.
Options: apply it for comparability; never apply it silently.
Choice: standing instruction from the owner - never apply unless explicitly
asked. Basis is inferred because the instruction lives only in chat; created
date approximate.
Consequences: all yield/amplitude tables are unfiltered by P2P.

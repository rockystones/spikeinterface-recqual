---
id: R-012
type: result
status: current
title: The Rocky derivation chain is deterministic and MATLAB-validated end to end
created: 2026-09-13
actor: agent
basis: recorded
reviewed: 2026-09-13
verdict: works
parent: P-03
evidence: [REF-002]
source: [docs/notes/data_inspection.md, matlab/rocky_provenance.m]
---
What ran: five sessions' chains regenerated with the original seeded
functions; every metric re-derived independently in MATLAB.
Outcome: regeneration deterministic (identical counts on re-run); stored
methods_long matched exactly on the in-subset session (343/192/159/206/120
units per method); MATLAB max|diff| = 0 on all unit metrics, 100% gate
agreement, free layer equal to stored events_electrode.
Interpretation: figures trace to raw waveforms with no unexplained steps;
the one definitional split found (|trough| vs max(|vmin|,vmax) amplitude)
is documented in data_inspection.md.

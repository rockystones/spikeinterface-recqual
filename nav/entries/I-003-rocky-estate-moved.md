---
id: I-003
type: issue
status: resolved
title: Rocky NEV estate moved; session_index paths went stale
created: 2026-09-13
actor: agent
basis: recorded
closed: 2026-09-13
summary: Owner reorganized D:\Claude Code\Rocky into Monkey Data\Rocky; index remapped by basename, 886/886 verified
evidence: [data/derived/rocky/session_index.parquet]
source: [notebooks/scratch_provenance_dump.py, "chat 2026-09-13 (owner: 'I might have reorganized the data')"]
---
Found when the provenance dump could not open the I1 Plexon -01 NEVs. The
whole `D:\Claude Code\Rocky` staging tree moved to
`D:\Claude Code\Monkey Data\Rocky` with subfolders restructured: `Original
NEV` up one level, `Analog to be sorted`/`Analog`/`Part2` dissolved into
`Original NEV`, chronic impedance dates now under `postimplant/`, bench
under `preimplant/`, and new `Sorted/Manual` + `Sorted/Scan` trees (~35k
files - likely OFS per-unit exports, relevant to W-012).

Resolved by remapping `session_index.parquet` by unique NEV basename
against a walk of the new tree (835 files, zero name collisions) and
verifying all 886 rows exist on disk; backup kept as `.parquet.bak2`. Any
other table storing absolute `D:\Claude Code\Rocky\` paths (e.g. old
impedance `source` strings) is provenance text, not a live pointer.

---
id: I-006
type: issue
status: open
title: Host nonpaged-pool leak under sustained sorting I/O starves the machine
created: 2026-09-16
actor: agent
basis: recorded
parent: P-03
informs: [W-019]
source: ["perf counters 2026-09-15/16", notebooks/scratch_ns5_consensus.py]
---
Measured twice during W-019: the Windows NONPAGED kernel pool grows
under sustained sorting I/O and never shrinks - 22.8 GB after ~2 nights
(0.1 GB available), reset to 0.9 GB by a reboot, regrown to 7.6 GB
within ~12 h of resumed sorting. It survives killing every sorter
process and container, so a kernel driver holds it (Docker/WSL storage,
NTFS filter, or AV filter are the usual suspects; naming the tag needs
an elevated poolmon/fltmc, not available from this session).

Secondary effect: a sorter LAUNCHED into a starved machine balloons and
thrashes - SC2 reached ~11 GB and 5 h on a stem the original resort
cleared in 152 s with normal output. The stem was innocent.

Mitigations in place: scratch_ns5_consensus.py now refuses to start a
stem below 3 GB available and exits cleanly for a resume-from-shards.
For the owner: reboot between long sorting campaigns; to name the
culprit driver run poolmon (WDK) or `fltmc filters` from an elevated
shell during a leak episode; consider Defender real-time exclusions for
the bulk-read data folders if WdFilter turns out to hold the tag.

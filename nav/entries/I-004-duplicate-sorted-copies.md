---
id: I-004
type: issue
status: resolved
title: Duplicate sorted NEV copies let stem lookups pick a test-vintage sort
created: 2026-09-14
actor: agent
basis: recorded
parent: P-03
informs: [R-013, W-017, REF-002]
source: [notebooks/scratch_ns5_resort.py, notebooks/scratch_mean_max_p2p_pass.py, notebooks/scratch_provenance_dump.py]
---
Surfaced by the W-017 cross-check (pass shards vs provenance stores):
Nigel_Anterior_2023-03-24 disagreed by up to 37.8 uV per channel while
every other overlapping session matched at 0.

Cause: the same session's sorted NEV exists in multiple copies with
identical events but different Plexon labels - Nigel's
"OFS sorting test2023\Scan*/TDIST*" algorithm-comparison folders (7-8
copies per session) and "Curated" exports, Fisk's "DS vs Sidd" curation
folders. Any resolver that takes the first inventory row per stem can
silently land on a test vintage. Measured blast radius: the provenance
dump built the Nigel_Anterior_2023-03-24 store from TDIST-EM-3D-PSF, and
the mean-max-P2P pass resolved exactly 1 of 708 stems
(Nigel_Anterior_2023-01-24) to ScanEM-J3; all other picks were canonical.

Second facet, same root (stem-based NEV resolution): the dump's
ns5-worklist fallback resolved Fisk's region-token stems
(20230605-132052-Lateral) to the UNSORTED Recordings NEV and asserted
has_ofs=True - both Fisk stores were built without any Plexon layer
while claiming one (their "53/165 units" were isosplit-only). The
sorted exports live under Fisk\SN<serial>\Sorted\Exported with
run-numbered stems (...-001-01.nev).

Fix: `noncanonical_nev_score()` in scratch_ns5_resort.py ranks paths
containing "OFS sorting test" / "Curated" / "DS vs Sidd" behind the
production sorted file; the pass worklist and the dump's nev_path_for
select by that score; nev_path_for additionally matches Fisk region
stems to inventory stems by YYYYMMDD-HHMMSS prefix; and meta.json
has_ofs is now what the file's labels showed, never what the resolver
claimed. Recomputed from canonical files: the 2023-01-24 shard, the
Nigel 2023-03-24 store (isosplit layer unchanged - R-013 numbers stand;
ofs layer now the production sort), and both Fisk stores (redumped with
their true Plexon layer, revalidated).

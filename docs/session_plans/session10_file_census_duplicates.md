# Session 10 — E: drive file-census duplicate review

## Plan

Review the qc.py census of the E: MonkeyEphys drive
(`D:\Claude Code\Monkey Data\census_E_drive_202608180018.sqlite`, all files
quickXorHash'd) and identify duplicates.

## Outcome

- 841.1 GiB of 5.3 TiB (15.9%) is exact duplicate content: 17,089 groups, 39,327 files.
- Verified a 7-folder cleanup set freeing 656.7 GiB (mirrors of the `*_TDT` masters:
  `004_Picasso\Picasso`, `003_Oops\Old Sorting`, `003_Oops\Oops_baseline_data`,
  `002_Luigi\L1tanks`, `002_Luigi\Luigi`, `to_batista`, `Old compiled`), with a
  166-file rescue list (unique .Tdx indexes + 5 compiled .mat).
- New uncertainty → data-integrity bugs, not just copies: three Oops sessions
  (2016_01_22, 2016_01_29 A/B) and one Rocky session (2018-06-28 Raw2A) have all
  96 Raw2 channel .sev files byte-identical; `003_Oops\MAT_TO_MDA` wrote eNe1==eNe2
  for ~16 sessions (2016_01_22→03_29). Flagged in memory; affected sessions must be
  excluded or re-exported before longitudinal use.
- Outputs next to the census DB: `census_duplicates_report.md`,
  `census_duplicate_files.csv`, `census_duplicate_trees.csv`,
  `census_cleanup_rescue_list.csv`. Artifact:
  https://claude.ai/code/artifact/eb8242d4-dad1-4525-95e2-2a5ba8437aed
- Deferred: nothing deleted; cross-drive comparison of the local D: working copies
  against E: would need a hashed census of D:.
- SI functions used or introduced: none (pure census/SQLite analysis session).

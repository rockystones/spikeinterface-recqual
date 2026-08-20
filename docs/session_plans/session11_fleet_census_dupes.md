# Session 11 — seven-drive fleet census duplicate review

## Plan

Review the new census databases in `D:\Claude Code\Monkey Data`
(`census_D_E_F_H_I_J_L_drive_202608141350.sqlite`, all 1.96M files hashed;
`census_L_drive_202608062020.sqlite`, metadata-only, superseded) and identify
duplicates beyond the session-10 Seagate audit.

## Outcome

- Fleet: 15.67 TiB / 1,964,386 files on 7 drives. 2,440.9 GiB (15.2%) exact duplicate
  content = 1,378.1 GiB intra-drive + 1,062.8 GiB cross-drive. Seagate-internal
  841.1 GiB reproduces session 10 exactly.
- Drive letters proved unstable across censuses (Seagate = L: here, E: on 08-18);
  all reporting keyed to label/serial. The current machine's D: is in no census.
- New dupes: F-Backup4TB 318 GiB internal (Neuropixels L10x copies — but
  `Backup\Kilosort\L101_221212` is the fleet's only copy of that session, so no
  wholesale delete); DATASSD↔Seagate 567.6 GiB; D↔F backup mirror 206.8 GiB +
  `Backup20251105` third copies; autolab ×3; ICE tanks renamed blocks; Matlab
  images ×2-3.
- Sharper inverse finding: 92.5% of distinct content (12.3 TiB) is single-copy;
  I-ANALYZER holds ~1.7 TiB of monkey ephys nowhere else; the Seagate archive is
  86% single-copy.
- New integrity flag: DATASSD copy of Picasso_2015_11_17-1 has 62 identical Raw1
  channels (archive copy clean). Seven VDIs (~2.7 TiB) verified all-unique.
- Outputs: `census_fleet_dupes_report.md` + 3 CSVs next to the census DB; artifact
  https://claude.ai/code/artifact/43837014-28d2-4417-b3f2-7a4d49ac2f9b
- Deferred: verified safe-delete set for F:'s duplicated subtrees (needs a
  keep-side decision); backup plan for the exposed single-copy drives.
- SI functions used or introduced: none (SQLite/census analysis session).

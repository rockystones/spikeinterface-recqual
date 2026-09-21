---
id: D-016
type: decision
status: accepted
title: Owner outlier rulings - six flagged sessions restored as normal data
created: 2026-09-21
actor: human
decided_by: human
basis: recorded
parent: P-03
informs: [REF-003]
source: ["chat 2026-09-21", notebooks/scratch_two_array_metrics.py]
---
After inspecting the outlier previews (OFS + ISO-SPLIT pages, W-021),
the owner ruled these six sessions NORMAL and they were removed from
the OUTLIERS master dict:

  Rocky_Anterior_09-22-2017        Rocky_Anterior_09-28-2017
  Rocky_Posterior_09-21-2017       Rocky_Posterior_10-19-2017
  Rocky_Posterior_10-30-2017_Baseline
  Rocky_Posterior_2022-08-26_Baseline_DigitalHeadstage

Consistent with the ISO-SPLIT evidence: these five 2017 stems gate
cleanly (65-93% of clusters pass, e.g. 152/162 on Anterior 09-22)
unlike the rest of the 2017 block (0-5%), and the 2022-08-26 session
resorts at 67/169.

Standing exclusions (22 stems) unchanged, including the Digital
12-06-2018 truncated-export day (D-014-era ruling 2026-09-19) and the
Dec-2018 Analog stems - though after the D-015 rebuild the Analog
stems no longer appear in the 332-corpus at all (their combos carry
the Digital lineage), so those two dict entries are documentary.

Applied downstream 2026-09-21: two_array_metrics + figure sets,
variance pipeline exclusion set, outlier-inspection candidate list.

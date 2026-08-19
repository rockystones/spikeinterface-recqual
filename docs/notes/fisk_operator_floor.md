# The operator floor on Fisk, and a drift S09 could not see

14 matched pairs: the same seven session dates curated by both DS and Sidd, on
**both** arrays, 2023-12-13 to 2024-04-03.

`notebooks/scratch_fisk_operators.py` → `data/derived/fisk/operator_pairs.parquet`.

S09's 30 operator pairs were opportunistic — whatever happened to exist — so an
operator difference and a session difference were partly confounded. Here every
date contributes one DS file and one Sidd file per array, so the comparison is
within-session by construction. `label_file` and `compare` are imported from
S09 rather than reimplemented, so the numbers are on one scale with the
published floor.

## The floor, matched

| | S09, 30 pairs | **Fisk, 14 matched** |
|---|---|---|
| relative unit-count difference | 0.25 | **0.353** |
| Sidd / DS unit ratio | 0.79 (IQR 0.72–0.97) | **0.700** (IQR 0.63–0.78) |
| keep agreement | 0.935 | 0.963 |
| ARI on spikes both keep | 0.995 | **0.998** |

The decomposition S09 reported holds and sharpens: **the operators partition
the kept spikes almost identically (ARI 0.998) and disagree about inclusion**.
Sidd keeps fewer units than DS in **14 of 14 pairs** — perfectly systematic,
against 80% same-sign in S09.

## Two things the matched design exposes

### The gap is array-specific

| array | Sidd / DS |
|---|---|
| Lateral | 0.784 |
| Medial | **0.633** |

Mann-Whitney **p = 0.0006**. The two operators diverge half again as much on
Medial as on Lateral. An operator floor quoted as one number for a subject is
therefore averaging over a real per-array difference.

### The gap drifts — and this is the part that matters

| array | rho(date, Sidd/DS) | p |
|---|---|---|
| Lateral | −0.714 | 0.071 |
| Medial | −0.786 | 0.036 |

The ratio falls on both arrays over four months: the operators grow further
apart. And the consequence shows up directly in the trends each one would
report from the same seven recordings:

| array | DS unit count | Sidd unit count |
|---|---|---|
| Lateral | rho **+0.821** (p = 0.023) | +0.429 (p = 0.34) |
| Medial | +0.018 (p = 0.97) | rho **−0.782** (p = 0.038) |

**On Medial, Sidd's unit count declines significantly while DS's is flat. On
Lateral, DS's rises significantly while Sidd's is flat.** Same array, same
sessions, same events — opposite conclusions about what the array is doing.

## What this revises

[[measurement_floor]] concluded that the operator difference is "largely but
not wholly systematic (80%, ratio IQR 0.72–0.97)" and therefore that **"a
longitudinal series sorted throughout by one operator is mostly protected."**

The first half is confirmed and strengthened — 14 of 14 here. The second half
is weaker than it looked. A *constant* offset cancels out of a within-operator
trend; a *drifting* offset does not. These pairs show the offset drifting over
four months, and the two operators consequently report different trends on the
same recordings.

So the protection holds for the **level** and not for the **slope**. Holding
the operator fixed removes a step; it does not guarantee that the trend you
measure is the trend another curator would have measured.

## Limits, which are real

- **Seven dates per array, four months.** A rank correlation on seven points is
  noisy, and the p-values above are nominal — four trend tests are reported and
  none is corrected. Treat the drift as a flag for a larger test, not as a
  settled effect.
- The window is short relative to the multi-year series the floor is used to
  qualify.
- Both operators curated the same automatic starting point, so this bounds
  curation disagreement, not sorting disagreement.

**What would settle it**: the same matched design over a longer span. Fisk has
71 and 69 sessions across two years and only seven are double-curated. If more
can be curated by both hands — ideally spread across the full range rather than
clustered in one quarter — the drift becomes testable rather than suggestive.

## Figures

`notebooks/scratch_fisk_figures.py` → `figures/fisk/operator/`.

| figure | what it shows |
|---|---|
| `O1_floor` | all 14 pairs as individual slopes, the ratio split by array, and keep-agreement against ARI |
| `O2_drift` | the ratio falling on both arrays, and each operator's own trend on the same seven recordings |

`O2` is the one worth looking at. The middle and right panels are the same
seven sessions scored twice: on Lateral the two curves rise together and only
DS's reaches significance, on Medial they separate and only Sidd's declines.
The divergence is visible in a way the rho table is not.

## Related

[[measurement_floor]] for the floor this extends and partly revises,
[[fisk_impedance]] for the rest of this drop, [[robustness]] for where the
floor feeds the longitudinal conclusions.

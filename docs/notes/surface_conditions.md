# Striped surface treatments on Nigel and Fisk, and why the obvious test lies

Nigel's and Fisk's four arrays were coated in **alternating stripes**, one
stripe treated and the next not. That is a much better design than treating
whole arrays: each array contains its own control, recorded through the same
amplifier on the same day by the same operator, so every confounder that makes
cross-array comparison hard cancels within a stripe pair.

`notebooks/scratch_surface_conditions.py` → `data/derived/surface/`,
`figures/surface/`. 302 recordings, 28,992 electrode-sessions.

| animal | pedestal / cortex | serial | stripe A (even CMP col) | stripe B |
|---|---|---|---|---|
| Nigel | Anterior / Lateral | 1025-001496 | TNP L1 | TNP only |
| Nigel | Posterior / Medial | 1025-001473 | EDCNHS L1 | Non-treated Ctrl |
| Fisk | Lateral / Anterior | 1025-001498 | TNP L1 | TNP only |
| Fisk | Medial / Posterior | 1025-001504 | EDCNHS L1 | Non-treated Ctrl |

Stripe A carries L1 on both arrays, on TNP in one and on a bare substrate in
the other, so the L1 contrast is replicated twice per animal.

## Which way the stripes run

Getting this wrong does not error. It splits the array along the wrong axis and
returns a null that looks like a result.

- The treatment schematic is drawn with the **wire bundle at the bottom** and
  the stripes horizontal.
- Blackrock CMPs are written with the **wire bundle on the right** (owner,
  2026-08-19), `col` left-to-right and `row` bottom-to-top.

So the schematic is the CMP rotated 90° clockwise, and a horizontal stripe in
the schematic is a line of constant **`col`**. Splitting on `row` — the obvious
reading of "alternating rows" — would have been perpendicular to the treatment.
Phase: the schematic's first stripe carries L1 and maps to `col = 0`, so even
columns are treated. That splits Nigel's arrays 48/48 and Fisk's 49/47 and
47/49, the imbalance coming from where each array's four unconnected shanks
fall.

## The implant table is transposed

The treatment schematic's two panels carry **real electrode maps**, not a
generic template, and they identify their arrays exactly — including the
unconnected positions, which differ per array:

| | top row (CMP r9) | bottom row (CMP r0) |
|---|---|---|
| panel labelled EDCNHS | `89 88 78 68 58 48 38 28 18 ·` | `· 79 69 59 49 39 29 19 9 ·` |
| **1025-001473** = Nigel Posterior | identical | identical |
| panel labelled TNP | `89 88 78 · 58 48 38 28 18 68` | `· · 69 59 49 39 29 19 9 79` |
| **1025-001496** = Nigel Anterior | identical | identical |

The implant table assigns Ctrl/EDC to the *anterior* pedestal and TNP to the
posterior — the opposite. Owner confirmed 2026-08-19: **the table is wrong,
anterior is TNP**. Fisk is carried across on the same reasoning, since its
Lateral array sits on the anterior pedestal in the same table; Fisk's own maps
match neither panel, so that half is an inference from the surgical design and
not from a schematic.

## The obvious test is invalid, and its control proves it

Split each session's electrodes by stripe, take a paired Wilcoxon across
sessions. On the treatment axis, **23 of 44 array-metrics reach p < 0.05**,
several at p < 0.0001, with effects like "the L1 stripe crosses threshold at
0.68× the rate of its neighbour".

Run the identical pipeline on **row** parity, which carries no treatment:
**29 of 44**. The control fires *more often than the treatment axis*.

Two things are wrong, and only the second one matters.

**Spatial gradients.** Yield runs in smooth gradients across these arrays —
Nigel Anterior goes 0.05 → 1.12 → 0.32 gated units per electrode across its ten
columns. Sampling a gradient at even indices versus odd ones leaves a small
systematic offset that has nothing to do with any coating.

**The session is not the unit of replication.** This is the real problem. The
same 96 electrodes are recorded every session, so a paired test across sessions
asks *"do these two fixed electrode sets differ at all?"* — which is essentially
never exactly false. More sessions buy precision on a fixed quantity, not
evidence about a cause. With 73 sessions, a 5% difference between two fixed
groups lands at p < 0.0001 whether or not anything was ever applied to them.

Correcting only the first — contrasting each stripe with the mean of its two
neighbours, which cancels any linear gradient exactly — leaves the problem
untouched: **18 of 24 on the treatment axis, 18 of 24 on the control**. The
gradient was never the main term.

## The valid test, and what it says

The unit that was assigned a treatment is the **stripe**, and there are five per
condition. Average each electrode over all its sessions, average those into ten
stripe means, and ask where the real even/odd assignment ranks among all
`C(10,5) = 252` ways of calling five of those ten stripes treated. The null
reuses the same stripe means, so the array's spatial structure is held fixed by
construction.

| | treatment axis (`col`) | control axis (`row`) |
|---|---|---|
| p_perm < 0.05 | **0 of 24** | **0 of 24** |

The control now behaves, which is what makes the null trustworthy.

**No array separates its treated stripes from its untreated ones**, on gated
unit yield, crossing rate, noise floor or peak SNR.

## How large an effect would have been seen

A null is worth only its sensitivity. Observed contrasts against the spread of
the permutation null, as a percentage of each array's own mean:

| array | yield observed | detectable at 95% | noise observed | detectable |
|---|---|---|---|---|
| Nigel Anterior | **−0.3%** | 69% | +0.2% | 7% |
| Nigel Posterior | −8.5% | 34% | +0.9% | 5% |
| Fisk Lateral | −13.3% | 29% | +9.0% | 14% |
| Fisk Medial | −8.9% | 28% | +1.9% | 15% |

So this design can rule out a **large** effect on yield — roughly 30% or more
on three arrays — and cannot rule out a modest one. The noise floor is much
better constrained, at 5–15%, because it varies far less between stripes.

Yield is nominally *lower* on the L1 stripe on all four arrays. A sign test on
four arrays gives p = 0.125, the magnitudes range from 0.3% to 13%, and the
gradient-corrected estimator does not agree on direction — Fisk gives 0.90 and
0.91 while Nigel gives 1.12 and 1.19. **Treat the direction as unresolved.**

## The longitudinal answer: both stripes decline together

The question was what each surface condition does over time. Gated units per
electrode, per stripe:

| array | stripe A (L1) | stripe B |
|---|---|---|
| Nigel Anterior | TNP L1 **−0.560** | TNP only **−0.683** |
| Nigel Posterior | EDCNHS L1 **−0.806** | Non-treated **−0.784** |
| Fisk Lateral | TNP L1 **−0.394** | TNP only **−0.259** |
| Fisk Medial | EDCNHS L1 **−0.379** | Non-treated **−0.452** |

All eight decline, all eight significantly, and the treated stripe declines
faster than its control on two arrays and slower on two. **The decline reported
across this cohort is not slowed by any of these coatings at a rate this design
can resolve.** Nigel Posterior reaches zero yield on both stripes.

`U1_layout.png` makes the same point without statistics: the stripe maps are
cleanly striped and the measured yield maps are patchy and gradient-shaped,
with no stripe visible in them.

## What would change this

- **More arrays, not more sessions.** The binding constraint is five stripes
  per condition. Sessions are already saturated at 73–79.
- **Pooling the four arrays** into one permutation would roughly halve the
  detectable effect, at the cost of assuming the coatings act alike across
  animals and substrates. Not done here; the direction disagreement between
  animals argues against pooling.
- **Confirmation of Fisk's assignment** from its own schematic, which would
  turn two of the four arrays from inferred to verified.

## Related

[[channel_mapping]] for the channel-id rule this depends on,
[[utah_channel_mapping]] for the CMP parser and per-array unconnected
positions, [[cohort_longitudinal]] for the whole-array decline these stripes
sit inside, [[measurement_floor]] for the operator floor that bounds any
yield claim.

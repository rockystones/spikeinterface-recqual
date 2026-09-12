# Resolving an array serial: always key by (subject, implant, array)

Rocky carries two implants whose arrays **reuse the labels** `Anterior` and
`Posterior`. Any lookup built as `(subject, array) → serial` — or worse,
`array → serial` — iterates the registry's implants in order and lets **I2
silently overwrite I1**.

That bug shipped four times. In `scratch_rocky_ns5_free.py` and
`scratch_ns5_resort.py` it labelled **431 Rocky I1 sessions (2017–2023) with
the I2 serials `1025-004377`/`1025-004419`** in `ns5_free.parquet` and 163 rows
of `ns5_sorters.parquet`; the same collapsed dict existed latent in
`scratch_giants_cohort.py` and `scratch_rocky_deepdive.py`. All four are fixed
(2026-09-12) and the tables' `serial` columns repaired to `1025-001501` /
`1025-001497`.

**What the mislabel did and did not touch.** The free-layer *values* are safe:
session-level noise, crossing and amplitude metrics never use geometry. The
`serial` label and the **CMP handed to the sorters** were wrong — Rocky's I1
`.ns5` sorts ran with I2's probe geometry, i.e. a permuted channel→position
assignment and slightly different unconnected corners. At 400 µm pitch no
template spans neighbouring shanks, so unit counts and amplitudes are
essentially unaffected, but any *position-dependent* reading of those sorter
outputs (which shank a unit sat on) is untrustworthy until re-run.

**The rule.** Resolve serials with the implant in the key, and take the implant
from the session row (`cohort_index` / inventory carry it), never from "the
subject's arrays". `scratch_cohort_io.array_serials(subject, implant=...)` does
it correctly; the fixed helpers now require or default the implant explicitly.

Related: [[cmp_validation]] for why the CMP identity matters,
[[cohort_definition]] for the implant history that makes the labels collide.

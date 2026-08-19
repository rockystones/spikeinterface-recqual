# How much does the acquisition equipment change the recording?

Rocky was recorded on three configurations with overlap in time — TDT, a
Blackrock **analog** headstage and a Blackrock **digital** headstage — so he is
the only place this can be asked without confounding equipment with animal,
array age or implant.

**Short answer: equipment sets the scale, not the quality.** Noise floor and
amplitude move together by 1.2–1.4× across configurations and their ratio does
not. Peak SNR spans 2.93 → 3.14 across all three, a 7% range.

`notebooks/scratch_equipment_compare.py`, `scratch_rocky_ns5_free.py`.

## Two comparisons, kept apart on purpose

They use different measurement paths and **must not be pooled**:

- **Analog vs digital** comes from the **broadband**, with both members of a
  same-day pair re-detected at the same `k·MAD`. That removes the NSP's own
  acquisition threshold from the comparison — the thing that made S12b's
  crossing counts misleading.
- **TDT vs Blackrock** comes from **snippets on both sides**. Rocky's TDT tanks
  are almost all snippet-only, so there is no fair continuous comparison to
  make. Mixing a continuous-derived noise floor with a snippet-derived one
  would inject the 1.1–1.3× bias from [[snippet_noise_floor]] into the
  equipment contrast and read as an equipment effect.

The visible consequence is that snippet-derived SNR runs ~3.0 and
continuous-derived SNR ~4.7 on the same animal. That gap is the estimator, not
the hardware, which is exactly why the two tables are separate.

TDT vs Blackrock is date-matched but **not paired**: a TDT block and a
Blackrock file on one day are different recordings, so only session-level
distributions are compared.

## Analog vs digital headstage — broadband, 108 same-day pairs

Both re-detected identically, so nothing here depends on what the NSP chose to
save.

| metric | analog | digital | ratio | p |
|---|---|---|---|---|
| noise floor | 10.13 µV | 7.81 µV | **1.30** | 2.4e−19 |
| crossing amplitude p50 | 60.18 µV | 48.50 µV | **1.24** | 1.9e−19 |
| crossing amplitude p90 | 131.89 µV | 100.92 µV | 1.31 | 1.8e−17 |
| **peak SNR** | 4.66 | 4.75 | **0.98** | 0.064 |
| crossing rate | 26.59 Hz | 30.10 Hz | 0.88 | **0.86** |
| electrodes active | 1.00 | 1.00 | 1.00 | 0.16 |

**A gain difference.** Noise and amplitude scale together and SNR does not
move. This confirms S12b — which found 1.25× noise, 1.33× amplitude, SNR 0.98
— from a completely independent measurement path.

**And it settles the crossing-rate question S12b left open.** S12b found the
analog headstage yielding ~20% *fewer* crossings and argued that was the
RMS-relative acquisition threshold rising with the noise floor, not fewer
neurons. Re-detect both sides at the same `k·MAD` and the difference vanishes:
0.88 at **p = 0.86**. The prediction held.

## All three, in the window where they overlap

TDT ran 2018-05-31 to 2019-01-17. Restricting every system to that window
leaves 192 sessions and removes array age from the contrast. Snippets on all
three sides.

| | n | noise | amp p50 | **SNR** | rate |
|---|---|---|---|---|---|
| BR-Analog | 66 | 12.23 | 58.00 | **2.93** | 14.00 |
| BR-Digital | 66 | 9.73 | 45.62 | **3.05** | 20.89 |
| TDT | 60 | 12.06 | 62.50 | **3.14** | 19.88 |

**TDT sits on top of the Blackrock analog headstage**, and differs from digital
by about the same factor analog does:

| | vs BR-Analog | p | vs BR-Digital | p |
|---|---|---|---|---|
| noise | **0.99** | 0.60 | 1.24 | 1.1e−05 |
| amplitude p50 | 1.08 | 0.39 | 1.37 | 3.2e−07 |
| amplitude p90 | 1.23 | 5.8e−12 | 1.47 | 1.2e−16 |
| peak SNR | 1.07 | 1.7e−05 | **1.03** | 0.069 |
| crossing rate | 1.42 | 8.1e−11 | **0.95** | 0.36 |

Read the noise row against the headstage table: analog/digital is 1.30 from
broadband and TDT/digital is 1.24 from snippets, while TDT/analog is 0.99.
**The three configurations fall into two gain regimes** — TDT and the analog
headstage in one, the digital headstage about 25% lower in both noise and
signal — and SNR is flat across the boundary.

**Crossing rate is a threshold setting, not a yield.** TDT records 1.42× the
analog rate and 0.95× the digital rate, each under its own online threshold.
Nothing about the tissue changed between two sessions on one day; what changed
is where each system put its trigger. Any longitudinal series that crosses an
equipment change will show a step in crossing rate that is pure instrument.

The one small real difference: TDT's peak SNR is 7% above analog (p = 1.7e−05)
and indistinguishable from digital (p = 0.069). Significant, and an order of
magnitude smaller than the gain differences around it.

## What this means for the longitudinal work

1. **SNR is the metric to carry across an equipment change.** It is the only
   one here that is stable, and it is stable across a change of amplifier
   *and* of acquisition system.
2. **Never compare absolute noise or amplitude across configurations.** A
   1.24–1.30× step will appear at the changeover and look like the array
   improving or degrading.
3. **Never compare crossing rate across configurations at all.** It reflects
   each system's threshold, and the S12b result shows the threshold moves with
   the noise floor.
4. **Record which equipment produced each session** and treat a changeover the
   way S09 treats a change of operator: a step to be controlled for, not
   biology.

## Limits

- **One animal.** Rocky is the only subject with the overlap; nothing here
  says the 1.25× gain ratio is the same on another rig or another implant.
- **TDT vs Blackrock is unpaired**, so it carries session-to-session variance
  the headstage comparison does not.
- **66 of 431 broadband sessions are missing** from the analog/digital table:
  they failed with `MemoryError` when the pass was competing with the sorters.
  The failures are scheduling artefacts, not data faults, and are queued to
  re-run; 108 pairs is already well past what the test needs.

## Related

[[cohort_longitudinal]] for the trends this constrains, [[snippet_noise_floor]]
for why the two comparisons use different measurement paths,
[[threshold_crossing]] for the detection contract the broadband side follows.

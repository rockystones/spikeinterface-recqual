# Noise floor from snippet data

How the per-electrode noise floor is obtained when there is no continuous trace, and how well it works. This is the load-bearing estimate in the whole Rocky analysis: SNR, the gate, and every downstream unit count depend on it.

## The method

A Blackrock NEV snippet is `(n_spikes, n_samples)` int16 with `wf_left_sweep = 10` — ten samples recorded *before* the threshold crossing. Those pre-trigger samples precede the detected event by construction, so their spread estimates the electrode's noise:

```python
stop = max(1, nbefore - 2)          # drop the two samples nearest the crossing
base = wf[:, :stop]                 # (n_spikes, 8) in uV
noise_uv = median(|base - median(base)|) / 0.6745
```

Pooled across every snippet on the electrode, not per snippet: eight samples is far too few for a single-snippet estimate. MAD rather than SD because the pool still contains occasional contaminated windows. The `/0.6745` converts MAD to a Gaussian-equivalent sigma so it is comparable with `get_noise_levels(method="mad")`.

The last two pre-trigger samples are dropped because on a fast-rising spike they already contain part of the depolarisation.

**No alternative was considered, because there is none.** With no continuous data, the pre-trigger window is the only sample of non-event signal the file contains.

## Validation against continuous data — and the bias it exposes

The Rocky cohort has no `.ns5`, so the substitution was never checked there. The Nigel 2023-03-17 session has both a 1.05 GB `.ns5` and its `.nev` from the same 96 electrodes, which makes the check possible: bandpass the `.ns5` to the spike band (250–5000 Hz, matching the NSP's own hardware filter) and take `get_noise_levels(method="mad")` per channel, then compare.

`notebooks/scratch_nigel_noise_validation.py`, figure `figures/validation/N1_noise_validation.png`.

| | median |
|---|---|
| continuous MAD, 250–5000 Hz | 13.33 µV |
| continuous MAD, 300 Hz highpass only | 14.68 µV |
| snippet pre-trigger MAD | 17.42 µV |
| **ratio snippet / continuous** | **1.305** (10–90 %: 1.005–1.927) |
| Pearson r | **−0.445** (p = 5.5e-6) |

Two problems, not one. The estimate is biased **high** by ~30 %, and it is **anti-correlated** with the quantity it estimates.

## Why: the pre-trigger window is never clean

The bias tracks how many events the electrode recorded:

| event-count quartile | median events | true noise | snippet estimate | ratio |
|---|---|---|---|---|
| Q1 fewest | 3 271 | 12.90 µV | 20.02 µV | **1.562** |
| Q2 | 4 172 | 13.23 | 19.37 | 1.454 |
| Q3 | 5 129 | 13.20 | 16.86 | 1.213 |
| Q4 most | 7 974 | 14.99 | 15.38 | **1.019** |

`rho(ratio, n_events) = −0.75`. On an electrode with plenty of real spikes the estimate is accurate to 2 %; on a quiet one it is 56 % high.

The mechanism is selection. A threshold crossing on a quiet electrode *is* a noise excursion, and in a band cornered at 250 Hz an excursion stays correlated for ~4 ms — twelve times the 0.33 ms pre-trigger window. The whole window therefore sits inside the excursion that triggered it. Dropping trailing samples cannot help, which is exactly what the margin sweep shows: the estimate is unchanged from `drop_tail = 1` through `5`.

## Twenty-one alternatives, none better

Three rounds were tested against the continuous ground truth:

- **Low quantiles of the per-snippet baseline SD** (q05/q10/q25) fix the sign (r rises to +0.45) but collapse the scale to 0.23–0.38× — an 8-sample SD is too short for an order statistic.
- **Restricting to large-trough snippets** (top 25 %, top 10 %, or a two-pass 4σ rule) makes it *worse*, ratio 1.66 → 2.29. This refutes the obvious hypothesis: a big spike's pre-trigger window contains its own rising phase, so spike-triggered snippets are contaminated too, just differently.
- **The post-trigger tail** (last 4–8 samples) weakens the activity dependence a lot (rho −0.75 → −0.17) but is uniformly ~1.79× high, because for a real spike the tail is in repolarisation.
- **Per-snippet centring**, geometric and elementwise combinations of the two windows: no improvement.

Contamination arrives from both ends of the snippet and there is no clean subset. Kept the production estimator; recorded the bias.

## What this means for the results

- **SNR is systematically underestimated**, most on low-activity electrodes. The `SNR >= 4` gate is therefore conservative and rejects some real units.
- The bias is worst exactly where an array is failing (few crossings), so **a declining array's decline is, if anything, exaggerated**. The direction is safe for the posterior-failure conclusion and unsafe for any claim that a decline was mild.
- Absolute SNR values are not comparable with SNR from a continuous pipeline. Rankings within a session are, since the bias varies slowly across electrodes.
- Do not apply the 1.305 factor as a correction. It is one session, one animal, one headstage.

**The real fix is continuous data.** With `.ns5` the noise floor is measured rather than inferred and this entire failure mode disappears — see [`ns5_plan.md`](ns5_plan.md).

## Related

[[snippet_sorting]] for how the estimate feeds the gate, [[threshold_crossing]] for the continuous-data equivalent, [[giant_events]] for what the amplitude tail looks like once SNR is available.

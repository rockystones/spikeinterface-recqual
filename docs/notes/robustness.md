# How much can a longitudinal conclusion be trusted?

Four questions, answered from what S09–S12 measured. `scratch_robustness.py`
re-cuts the existing tables; nothing here re-reads a NEV.

Short version: **the sorting-free layer is the more trustworthy longitudinal
instrument, the physics gate is the only curation layer that works on this data,
and the sorter parameters have not been validated at all.**

---

## Q1 — Are the sorter parameters right for a 400 µm pitch?

**No evidence that they are, and two pieces of evidence that they are not.**
This is the weakest link in everything below.

Every sorter ran on SpikeInterface defaults except two documented deviations —
MountainSort5 `scheme="2"` and Kilosort4 `do_correction=False`, both from
CLAUDE.md. Those defaults are tuned for high-density probes, where a spike lands
on several neighbouring channels. A Utah array is the opposite regime.

**MountainSort5's own log says so.** At `scheme2_phase1_detect_channel_radius =
200 µm` against a 400 µm pitch, the adjacency it built was:

```
[[0], [1], [2], [3], ... [95]]
```

Every channel is its own neighbourhood. Each of the 96 channels is sorted in
isolation, and every spatial parameter in the sorter is inert. That is not
necessarily wrong for this probe — it may be exactly right — but it means the
defaults are doing something quite different from what they were tuned to do,
and nobody has checked which setting is best.

**The sorters disagree far more than their algorithms do.** On one session with
good signal (`Nigel_Posterior_2023-01-24`, peak/noise 14.4):

| sorter | units | spikes | NSP events recovered |
|---|---|---|---|
| mountainsort5 | 242 | 148,312 | 0.85 |
| spykingcircus2 | 116 | 77,859 | 0.62 |
| **tridesclous2** | **7** | 3,811 | **0.06** |

A 35× spread in unit count. S09 put the *algorithm* floor — different clustering
of the same events — at 0.17 relative. This is two orders of magnitude beyond
that, so at least one of these three is badly parameterised for this geometry.
It is not yet known which.

**What would settle it.** The same machinery S09 used for algorithms, pointed at
parameters: sweep `detect_threshold` and the channel-radius parameters per
sorter over a stratified session subset, and score against (a) the NSP's own
threshold crossings as a partial anchor and (b) agreement between sorters. There
is no ground truth, so "best" is not directly observable — but "how much does it
matter, and where is the sorter insensitive" is, exactly as for the operator
floor.

**Until then, treat cross-sorter unit counts as uncalibrated.** Within-sorter
longitudinal trends are unaffected, because the parameter is held constant.

---

## Q2 — Does post-sorting curation help?

**The physics gate: yes, measurably. UnitRefine: it does not work here at all.**

### The gate roughly halves method-dependence

Ratio of gated spread to ungated spread, from S09's waveform pass. Below 1 means
the gate removes disagreement about who did the sorting:

| source of variation | unit count | amplitude | SNR |
|---|---|---|---|
| operator vs self | 0.33 | 0.12 | 0.49 |
| auto vs Sidd | 0.45 | 0.30 | 0.31 |
| algorithm choice | 0.49 | 0.50 | 0.37 |
| operator identity | 0.64 | 0.52 | 0.83 |
| **auto vs DS** | **1.46** | 0.22 | 0.21 |

Gating cuts the spread roughly in half across the board — a real benefit, and
the main argument for keeping it. The exception is **automatic versus DS**,
where gating makes the count disagreement *worse*. DS curates close to what OFS
proposed (both pass the gate at ~39–40%), so the gate is re-deciding units the
two had already agreed on.

It passes **17,365 of 65,051 units — 27%**.

### UnitRefine is not usable on this data

**99.98% of units are labelled noise** (65,040 of 65,051), and `p(neural)` has
median 0.224 and never exceeds 0.604. That is not a statement about the units.

**Seven of the classifier's input features cannot be computed here:**
`drift_ptp`, `drift_std`, `drift_mad`, `spread`, `velocity_above`,
`velocity_below`, `exp_decay`.

Every one is spatial or drift-based, and there are two independent reasons none
is available:

1. **Snippet data has no continuous trace**, so drift cannot be measured.
2. **At 400 µm pitch a spike appears on one channel.** `spread`, `velocity_*`
   and `exp_decay` describe how a waveform decays across neighbours. With no
   neighbours they are undefined **even given continuous data** — so `.ns5`
   would fix reason 1 and not reason 2.

The imputer fills the gaps and the classifier decides on a mutilated feature
vector, landing everything on one side.

**This contradicts CLAUDE.md's stated default curation policy.** UnitRefine is
named as the default and cited as validated on Utah arrays (Jain et al. 2025);
that validation cannot have been on single-channel-per-spike input. **The
`ur_*` columns in `curation_labels.parquet` should not be used**, and the
physics gate is the only working curation layer on this project's geometry.

---

## Q3 — How robust is the sorting-based layer?

Three separate exposures, and they differ by orders of magnitude.

**Clustering choice is a modest term.** Relative spread in the answer, gated:

| | unit count | amplitude | SNR |
|---|---|---|---|
| operator identity | 0.161 | 0.017 | 0.015 |
| algorithm choice | 0.173 | 0.032 | 0.029 |

**Sorter choice is a large one** — 35× on the single session measured (Q1).
Different clusterings of a fixed event set are close; different *detectors* are
not.

**Analysis choices move the trend more than either.** Under S09's 18
gate/method/cohort variants, Rocky's trend `rho` ranges:

| array | metric | rho range | sign stable? |
|---|---|---|---|
| Posterior | elec_coverage | −0.77 → +0.39 (**1.17**) | no |
| Anterior | elec_coverage | −0.63 → +0.29 (0.91) | no |
| Posterior | amp_med | −0.80 → +0.10 (0.90) | no |
| Anterior | n_units | −0.72 → +0.05 (0.77) | no |
| Posterior | n_units | −0.78 → −0.30 (0.48) | **yes** |
| Anterior | amp_med | −0.80 → −0.39 (0.42) | **yes** |

Only 5 of 12 array × metric combinations keep a stable sign across the sweep.

**Replication across animals is the strongest evidence available**, since there
is no ground truth. Across 8 array-implants, screened:

| metric | median rho | rho sd | significant | same sign |
|---|---|---|---|---|
| **electrode coverage** | −0.68 | **0.25** | **8/8** | **8/8** |
| pass fraction | −0.29 | 0.27 | 5/8 | 8/8 |
| units per electrode | −0.53 | 0.31 | 6/8 | 7/8 |
| median SNR | +0.09 | 0.32 | 3/8 | 5/8 |
| amplitude p99 | −0.23 | 0.35 | 4/8 | 6/8 |
| median amplitude | −0.30 | 0.50 | 5/8 | 6/8 |

**Electrode coverage is the most reliable sorting-based longitudinal metric** —
it declines in all eight arrays, significantly in all eight, with the lowest
variance. Unit count is close behind. Median amplitude is the least reliable,
which matters because it is a natural thing to reach for.

---

## Q4 — How robust is the sorting-free layer, and how do the two compare?

The two layers agree on direction wherever both have a direction, and their
agreement on *magnitude* varies a lot:

| quantity | free rho | sorted rho | correlation |
|---|---|---|---|
| noise floor | −0.74 | −0.66 | **0.93** |
| typical amplitude | −0.71 | −0.53 | **0.80** |
| amplitude tail | −0.59 | −0.17 | 0.44 |
| electrode coverage | −0.01 | −0.40 | 0.42 |
| event rate | −0.24 | −0.30 | 0.41 |
| SNR | −0.21 | −0.02 | 0.39 |

**Noise floor and typical amplitude are the same measurement twice** (0.93,
0.80). For those, sorting adds nothing and costs robustness — measure them
without a sorter.

The other four decouple. That is not a failure: the sorted versions count
*neurons* while the free versions count *threshold crossings*, and those are
genuinely different quantities. Electrode coverage is the clearest case — the
free version is flat (−0.01) because electrodes keep crossing threshold long
after they stop yielding sortable units. **The sorted version is measuring
something the free version cannot see.**

### What each layer is exposed to

```
sorting-free    NSP online threshold, noise estimate, amplifier
sorting-based   ALL of the above, PLUS sorter choice, clustering algorithm,
                operator, curation threshold
```

The free layer's exposures are a **strict subset**, so it cannot be less robust.
Its own confounds are real and measured, though:

- **The online threshold is RMS-relative, not absolute.** S12b showed the
  noisier analog headstage yields **20% fewer** crossings on the same session —
  the opposite of what a fixed-µV threshold would give. So a drifting noise
  floor moves the crossing rate without any change in neurons.
- **The snippet noise estimate is 1.305× high** and anti-correlated with the
  true floor ([`snippet_noise_floor`](snippet_noise_floor.md)).
- **The amplifier matters**: analog reads 1.25× noisier and 1.33× larger.

## What to actually do

1. **Use the sorting-free layer as the primary longitudinal instrument** for
   noise floor and amplitude. It measures the same thing with fewer exposures.
2. **Use electrode coverage (sorted) as the primary yield metric.** It is the
   only one that declined significantly in all eight arrays.
3. **Hold the sorter and its parameters fixed** across a longitudinal series,
   and never compare absolute unit counts across sorters until Q1 is settled.
4. **Do not use the UnitRefine labels.** Use the physics gate.
5. **Screen on acquisition quality before fitting any trend** — the noise-floor
   screen from S09, which is a pre-outcome criterion.

## Related

[[measurement_floor]] for the per-metric floors, [[cohort_longitudinal]] for the
trends being sized, [[snippet_noise_floor]] for the free layer's noise bias,
[[validation_guide]] for how to re-run any of it.

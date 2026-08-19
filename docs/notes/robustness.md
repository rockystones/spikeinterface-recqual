# How much can a longitudinal conclusion be trusted?

Four questions, answered from what S09–S12 measured. `scratch_robustness.py`
re-cuts the existing tables; nothing here re-reads a NEV.

Short version: **the sorting-free layer is the more trustworthy longitudinal
instrument, the physics gate is the only curation layer that works on this data,
and the sorter parameters have not been validated at all.**

---

## Q1 — Are the sorter parameters right for a 400 µm pitch?

**No evidence that they are.** This is the weakest link in everything below.
An earlier version of this note also offered evidence that they are *wrong*;
that evidence was an artefact of a broken dependency and is retracted below.

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

**The sorters disagree, but far less than I first reported.** Across the 30
sessions of S11 completed so far:

| sorter | n | units (median) | spikes (median) | runtime |
|---|---|---|---|---|
| mountainsort5 | 29 | 142 | 157,923 | 373 s |
| spykingcircus2 | 28 | 110 | 393,063 | 163 s |
| tridesclous2 | 27 | 103 | 451,793 | 161 s |

**Kilosort4 is absent from every comparison in this project, and it is not a
sampling accident.** 76 attempts, zero results. The container reaches the GPU
and dies inside torch with `CUDA error: no kernel image is available for
execution on the device` -- a PyTorch build with no kernels for the card's
compute capability. The GPU here is an RTX 5060 Laptop at **compute 12.0**
(Blackwell) and the KS4 image ships a torch compiled for older architectures.

Re-running cannot fix it, so KS4 is now excluded from the default pool rather
than failing 49 more times. CLAUDE.md's sorter policy names it as one of four;
on this hardware the pool is **three**. The fix is either a KS4 image built
with `sm_120` support or `torch_device="cpu"`, which works and is far too slow
for a 96-channel corpus.

Per session, the **unit-count** spread between sorters is median **1.44x**, p90
2.09x, max 5.18x. Against S09's algorithm floor of 0.17 relative that is a real
and larger term, but it is nothing like the 35x this note previously claimed.

### Retraction

An earlier version of this note reported Tridesclous2 finding **7 units** where
MountainSort5 found 242, called it a 35x spread, and concluded that at least one
sorter was badly parameterised for a 400 um pitch.

**That was wrong, and the cause was my environment, not the sorters.**
SpikeInterface 0.102.3 calls `np.in1d`, which NumPy removed in 2.0; under numpy
2.4 both Tridesclous2 and SpykingCircus2 died partway through clustering and
returned whatever they had. With the shim in place TDC2 returns 103 units, in
line with the others.

The **conclusion** of Q1 is unchanged -- nothing here validates the parameters,
and MountainSort5's adjacency at 400 um is still `[[0], [1], ... [95]]`, every
channel its own neighbourhood. But the evidence I offered *against* the
parameters has evaporated, and a 1.44x median spread is the sort of difference
one expects between sorters that genuinely disagree rather than one that has
crashed.

**A second thing worth knowing about the sorters is more interesting than the
unit counts.** They agree far better on *how many neurons* there are (1.44x)
than on *how much of the record is neural*: 158k, 393k and 452k spikes is a
**2.9x** spread on the same recordings. MountainSort5 assigns roughly a third
as many spikes to a similar number of units.

### The NEV-agreement columns are not usable yet

`frac_nev_recovered` and `frac_sorter_in_nev` in `ns5_sorters.parquet` read
0.87-0.995, which looks like near-perfect agreement with the NSP's own
threshold crossings. **It is an artefact.** The matcher pools every channel
before asking "is there a NEV event within 1 ms", and at this corpus's density
-- ~400,000 events over 180 s -- that is 2,222 Hz pooled, so 4.4 events fall
inside any +/-1 ms window and the chance match rate is **0.988**. The observed
values are indistinguishable from it.

Matching has to be **per channel** (96x lower density, chance ~4.5%). The saved
sorter folders make that recomputable without re-running anything, and it is
the outstanding piece of S11: *how much the online threshold discarded* is the
one question this session exists to answer, and it is not answered yet.

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

### The gate does not transfer across acquisition systems

The TDT corpus gives the first chance to apply this gate to data from another
rig. It passes **12.9% of Oops's legacy units and 20.6% of Picasso's**, against
27% on Blackrock — not because those arrays are worse, but because TDT's online
threshold sits lower. Peak SNR runs ~3.2–3.4 there against 5–7 here, so a
threshold fixed at 4 lands in the middle of the TDT distribution
(Oops IQR 3.12–3.68) instead of in its tail.

Two consequences. **Gated unit counts are not comparable across acquisition
systems** — 0.23–0.29 gated units per electrode on TDT against 0.4–1.5 on
Blackrock Rocky I1 is a gate artefact, not a yield difference. And because the
gate sits mid-distribution on TDT, small changes to it move the survivor count
a lot there, where on Blackrock it is comparatively stable.

**Do not re-tune the gate to equalise pass rates.** A threshold chosen to make
two corpora agree is no longer a physics criterion. Report SNR distributions,
or fix the gate per system and never compare the counts.
See [[tdt_legacy_sorts]].

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

**Sorter choice is a larger one** — median **1.44×** in unit count across 30
sessions, p90 2.09× (Q1), and **2.9×** in the number of spikes assigned.
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

> **Two qualifications from the continuous layer**, now that 559 sessions of
> real broadband exist ([[continuous_longitudinal]]).
>
> **Electrode coverage is a snippet-layer metric and does not survive the
> move.** Re-detected from the trace at 4·MAD it takes two distinct values
> across Rocky's 431 sessions, 0.99 and 1.00 — every channel crosses in every
> session. What made it informative was the NSP's own threshold being
> selective; a fixed multiple of each channel's noise removes exactly that.
> Never compute it from continuous data, and never compare the two.
>
> **The flat-SNR result does not reproduce on Rocky's broadband.** Continuous
> peak SNR falls with rho −0.739 / −0.719 where the snippet layer gave +0.105,
> non-significant. The continuous effect is only **12% over five years** — the
> rho is large because the decline is monotone, not because it is big — and a
> 12% effect sits well inside what the snippet estimator's activity-dependent
> bias could erase. Which layer is right is unsettled; until it is, **"flat SNR
> replicates across three animals and eight arrays" should lose the word
> robust**.

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
  true floor ([`snippet_noise_floor`](snippet_noise_floor.md)) — but the
  **trend** it reports is sound, which is what this section needs. The TDT
  corpus supplies 88 block-arrays carrying both a snippet store and continuous
  broadband, and the two agree closely on direction and strength: Oops array 1
  gives rho −0.623 from snippets against −0.638 from the continuous MAD, array
  2 −0.505 against −0.544. The bias is ~1.13× there and behaves like a
  near-constant offset within a series rather than something that grows. So a
  snippet-derived *level* is not comparable across systems, while a
  snippet-derived *trend* is trustworthy — which matters because most Blackrock
  sessions in this project have no continuous trace at all.
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
[[validation_guide]] for how to re-run any of it, [[tdt_corpus]] and
[[tdt_legacy_sorts]] for the second acquisition system these conclusions were
tested against.

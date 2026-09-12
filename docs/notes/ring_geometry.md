# Position on the array: the concentric-ring test

Forrest et al. 2025 (*J. Neural Eng.* **22** 066008) build a finite-element model
of micromotion-induced tissue strain around a Utah array, find strain highest at
the corners and edges, then group electrodes into **concentric rings** — "the
number of rows away from the edge of the array" — and correlate ring with
measured performance. They report that edge electrodes have **lower impedance**
than interior ones (human motor 10×10 and macaque V4 8×8, at 1 month, 1 year and
2 years), and in human motor arrays **lower peak-to-peak waveform voltage and
SNR** at 1 and 2 years.

Our CMP geometry is verified ([[cmp_validation]]) and the electrode tables
already carry `col` and `row`, so the grouping is free. This asks the same
question of **six implanted 10×10 arrays, three animals, 630 sessions, 59,297
electrode-sessions, 2017–2025** — plus two things the paper does not have: **19
never-implanted arrays** measured on the manufacturer's bench, and **a paired
bench baseline for two of the implanted arrays**.

`notebooks/scratch_ring_geometry.py` → `data/derived/ring/`, `figures/ring/`.

**Answer in one line: the impedance edge effect is real and grows in tissue; the
ephys edge effect is large, animal-specific, and cancels across animals.**

## Ring convention

`depth = min(col, 9−col, row, 9−row)` is shells in from the boundary;
`ring = 5 − depth` follows the paper, so **ring 5 is the outer border** and ring 1
the four centre electrodes. Every array here is 96 of 100, with the unconnected
positions differing per array — the paper's corner group barely exists for us
(0–3 corners wired per array), so corners are not analysed separately.

## Two traps, and the second one is not obvious

**The session is not the unit of replication.** Ring membership is a *fixed*
property of an electrode, so a paired Wilcoxon across sessions asks "do these
two fixed electrode sets differ at all", which is essentially never exactly
false. Run on the border/interior axis it fires on **21 of 24** array-metrics.
Run on a `col`-parity control that encodes no geometry whatsoever it fires on
**20 of 24**. Neither number is evidence. This is the same diagnosis as
[[surface_conditions]], and the same control catches it.

**Bank B holds no border electrode.** The Blackrock CMP wires the 96 channels in
three diagonal bands, and the consequence is exact and severe:

| | bank A | bank B | bank C |
|---|---|---|---|
| border electrodes | 15 | **0** | 17 |
| interior electrodes | 17 | **32** | 15 |

So *border versus interior* is partly *bank-B versus everything else* — and the
impedance tester sweeps bank by bank, through separate front-end sections. Any
per-bank offset is indistinguishable from an edge effect. Banks A and C each
straddle the boundary, so the honest contrast is made **inside one bank**, which
holds the front-end section and the sweep block fixed. Every headline number
below survives that.

The valid tests used here are: a **toroidal-shift permutation** (roll the metric
map over the grid with the ring labels fixed — preserves the array's spatial
autocorrelation, destroys only its registration to the physical boundary), a
**four-border isotropy count** (a mechanical edge effect is isotropic and must
move all four borders the same way; a directional cortical gradient raises one
border and lowers the opposite, so it can reach 3 of 4 at most), and the
**within-bank contrast** above.

## Ephys: no cohort-level effect, and a large animal-level one

Border minus interior **inside a bank**, as a percentage of each array's mean.
Six arrays × two straddling banks = twelve signs per metric:

| metric | negative | sign test |
|---|---|---|
| median snippet amplitude (the paper's PTPV) | 8 / 12 | p = 0.39 |
| crossing rate | 7 / 12 | p = 0.77 |
| noise floor | 6 / 12 | p = 1.0 |
| peak SNR | 6 / 12 | p = 1.0 |

Nothing. But the twelve signs are not scattered — they are **sorted by animal**:

| animal | amplitude | crossing rate | noise | peak SNR |
|---|---|---|---|---|
| **Nigel** | −1.0 | −1.0 | −1.0 | −0.5 |
| **Rocky** | +0.5 | +0.5 | +0.75 | +0.5 |
| Fisk | −0.5 | 0.0 | 0.0 | 0.0 |

(mean sign over that animal's arrays × banks; ±1 means every cell agreed.)

The magnitudes are not small. Nigel Posterior's border crosses threshold at
**−47%** of its interior inside bank A; Rocky Posterior's at **+97%**. Both
animals' two arrays agree with themselves and disagree with each other, across
all four metrics and both banks.

**Six arrays share one geometry. A geometric cause cannot produce opposite signs
in two animals.** This is the same argument as [[treatment_effect]]'s three-axis
test: a shared cause must give a shared sign, and where the sign tracks the
animal rather than the manipulation, the animal is the better explanation.

Longitudinally the same split holds. Fisk's border–interior gap in noise and
crossing rate **widens** with implant age (ρ = +0.40 to +0.56) while Rocky's
**narrows** (ρ = −0.23 to −0.43).

## Impedance: the edge effect is real, and it is acquired

Fisk is the one animal with **map-free** impedance: Cerebus `MotorImpedance.txt`
dumps indexed by Blackrock channel, which [[impedance_sources]] proves 1248/1248
against the factory workbook. Rocky's come from the Autolab potentiostat and
depend on the unsettled [[impedance_channel_map]].

Per date, median border minus median interior, over 81 array-dates:

| array | median Δ | dates negative |
|---|---|---|
| Fisk Lateral `1025-001498` | **−0.306 dex** (−51%) | **41 / 41** |
| Fisk Medial `1025-001504` | **−0.251 dex** (−44%) | **40 / 40** |

Survives the within-bank control (bank A −0.09 and −0.19; bank C −0.01 and
−0.14), four borders agree on the Lateral array, toroidal-shift p = 0.02.

The uncensored form of the same effect is starker. The fraction of electrodes
above 1 MΩ, by ring:

| array | ring 1 (centre) | 2 | 3 | 4 | ring 5 (border) |
|---|---|---|---|---|---|
| Lateral | **0.854** | 0.604 | 0.455 | 0.542 | **0.158** |
| Medial | 0.375 | 0.438 | 0.295 | 0.220 | **0.164** |

Note this runs *against* the analysis: excluding the >1 MΩ readings as a
robustness check shrinks the contrast to −0.098 and −0.180, because the readings
excluded are disproportionately interior. The effect is not a censoring artifact.

### The control the paper does not have

Nineteen 10×10 arrays have the manufacturer's automated-tester sweep in saline,
taken **before implantation** — no tissue, no micromotion, no glial scar. The
same statistic on those:

- median Δ **+0.009 dex**, border below interior on **7 / 19** arrays, Wilcoxon
  p = 0.47
- within-bank: bank A p = 0.89, bank C p = 0.98
- toroidal-shift p < 0.05 on 4 / 19

**No edge effect at manufacture.** Individual arrays scatter ±0.15 dex, which
matters for the next step.

### The paired anchor

Two of those 19 are Fisk's own arrays, so for them the in vivo series has a
baseline **on the same electrodes**:

| array | bench | first session | last session | vs age |
|---|---|---|---|---|
| `1025-001498` | −0.086 | **−0.084** | **−0.493** | ρ = −0.76, p = 7.3e-09 |
| `1025-001504` | −0.113 | **−0.041** | **−0.272** | ρ = −0.17, p = 0.29 |

Both arrays start in vivo **at their own bench value** and open away from it —
40/41 and 39/40 later dates sit below the bench line. `1025-001498` keeps
widening across the year; `1025-001504` does most of its widening inside three
months and then plateaus (−0.226 → −0.252 → −0.272 across <3 mo, 3–12 mo, 1–2 y).

That is the argument in its strongest form: these two arrays each had a small
edge offset at manufacture, well inside the scatter of the other 17, and time in
tissue roughly tripled it. **This replicates Forrest et al.'s impedance finding
and adds the pre-implant control that separates it from manufacturing.**

## The dissociation, and why it is not a contradiction

Impedance shows the edge effect; spontaneous ephys does not. Forrest et al. see
the same split in their own NHP data — their macaque V4 arrays show the
impedance correlation but **no** PTPV correlation, and their evoked MUA SNR
correlates with strain in the *positive* direction, opposite to their human
motor arrays. Our cohort is NHP, and matches their NHP result rather than their
human one.

The plainest reading: whatever the edge does to the electrode–tissue interface
is measurable in impedance, and does not propagate to how many spikes that
electrode records. Impedance and yield are only loosely coupled on this corpus
anyway — the same conclusion [[fisk_impedance]] reaches from the other direction.

## Ring against radius

Forrest et al. report that concentric rings distinguished strain better than
distance from the array centre. On our measured data the two are
indistinguishable — median |ρ| across arrays:

| metric | ring | radius |
|---|---|---|
| amplitude | 0.218 | 0.217 |
| crossing rate | 0.228 | 0.246 |
| noise | 0.192 | 0.200 |
| peak SNR | 0.145 | 0.133 |

On a square grid the two are near-collinear, so this is a weak test and does not
contradict their supplementary finding, which was about modelled strain rather
than measured performance.

## Implant 2 flips the sign inside the same animal

Rocky's second implant (surgery 2025-03-26; 20 sessions at one to two months
post-implant, `scratch_rocky_i2_events.py`) shows a **large negative** border
contrast on every metric — border below interior by 26–38% on amplitude, SNR
and crossing rate, all sixteen within-bank cells negative, four-border
agreement 4/4 on six of eight array-metrics, toroidal-shift p down to 0.01 on
the Posterior. **Implant 1, in the same animal, ran the other way** (+16 to
+55%, border better).

Same animal, same rig, same 10×10 geometry, opposite signs. The earlier
reading — "the sign is an animal-level property" — was too generous: it is an
**implant-level** property, and the deconfound is now within-animal. Whatever
sets the sign (insertion mechanics, perimeter trauma, cortical placement), it
is decided per implantation, not by the array's geometry and not by the
animal. Note I1's own early sessions did not start strongly negative
(first-months contrasts ≈ 0 to +28%), so this is not a simple
young-versus-old-implant trajectory either — two insertions simply differ.

## The sorted layer says the same thing

The deferred yield arm is run (`scratch_yield_rings.py`, 2026-09-12): gated
units per electrode, Nigel/Fisk from `plexon-01` and Rocky I1 from the `ofs`
snippet sorts, zeros restored for unit-less channels before averaging.
Within-bank border contrast: **7/12 negative, sign test p = 0.77** — cohort
null — while the per-animal signs repeat the free layer exactly: Nigel −1.0
(−49% and −86% inside banks A/C on the Anterior), Rocky +0.75 (to +37%), Fisk
mixed. The position result is therefore consistent across the sorting-free and
sorted layers.

## Rocky corroborates the acquired impedance edge effect

Rocky's chronic potentiostat record now spans 52 dates over seven years with a
pre-implant bench measurement of both arrays
(`scratch_impedance_extended.py`). Under the authored map the border−interior
contrast **widens with time from its bench value** — Posterior ρ = −0.73,
p = 1.2e-09; Anterior ρ = −0.36, p = 0.0095 — a second animal, on a second
instrument chain, showing the Fisk pattern. Magnitudes (median −0.04 to −0.05
dex) sit far below Fisk's −0.25 to −0.31, as expected if the within-half
channel ordering is partly scrambled: a wrong permutation dilutes a real
border effect but cannot manufacture a time trend.

## The arbiter idea did not survive the fuller record

The first pass here read the border contrast as leaning authored. Extended to
52 dates with reversed candidates added, all four orderings give the negative
contrast (the bank-half component is shared between them), so the border
effect **cannot** separate the maps — and the bench-vs-factory and open/short
tests came back null too. Details, and the retirement of the open/short idea:
[[impedance_channel_map]].

## What this does and does not say

**Does not say** the geometry is irrelevant. Six arrays is a small design for a
cohort-level sign test, and a real geometric term could sit under a larger
animal-level term.

**Does say** that on this corpus an edge/interior contrast in ephys cannot be
attributed to array geometry, because the same geometry gives opposite signs in
two animals; and that reporting one animal's ring profile as a geometric finding
would have been wrong in a way that only the second animal reveals.

**Does say** that the impedance edge effect is real, is not manufacturing, and
develops over months in tissue — on two arrays in one animal.

## Related

[[cmp_validation]] and [[channel_mapping]] for the geometry this rests on,
[[surface_conditions]] for the fixed-electrode-split trap and its control,
[[treatment_effect]] for the same shared-cause-shared-sign argument,
[[impedance_sources]] for why Fisk's impedance is map-free and Rocky's is not,
[[impedance_channel_map]] for the open map decision this bears on,
[[fisk_impedance]] for the impedance-to-yield coupling.

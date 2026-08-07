# What the raw ns5 data unlocks

Recorded 2026-08-07: most of the raw `.ns5` for this project exists and further analysis on it is planned. That changes what is possible, because almost every compromise in the current pipeline traces to one missing input.

## What the snippet-only path cannot do, and continuous data can

| limitation | why it exists | what `.ns5` gives |
|---|---|---|
| No sorter from CLAUDE.md's pool runs | MountainSort5, Kilosort4, Tridesclous2 and SpykingCircus2 all detect spikes *from traces*; snippets give them nothing to detect | The whole pool, and therefore the multi-sorter consensus the project is actually built around |
| Noise floor biased ~30 % high and anti-correlated with the truth | the pre-trigger window sits inside the excursion that triggered it — see [[snippet_noise_floor]] | Direct measurement via `get_noise_levels`; the failure mode disappears |
| Only events the NSP chose to keep | the online threshold is invisible and moved between eras (2017 sits 2.3× above 2018) | Re-detection at a *known, constant* threshold across all six years, which is the single biggest fix available to the longitudinal comparison |
| No UnitRefine or Bombcell | both need a `SortingAnalyzer` backed by a recording | Curation becomes available; UnitRefine's 7 unavailable features (`drift_ptp/std/mad`, `spread`, `velocity_above/below`, `exp_decay`) are exactly the ones that made it fail here |
| No LFP | `.ns5` is broadband, `.ns3` is LFP | LFP is in scope per CLAUDE.md and has no snippet equivalent at all |
| Cross-channel artifacts inferred from coincidence | only event times are available | Artifacts visible directly as simultaneous deflections across the array |
| Giant events unverifiable | a 30-sample clip is all there is | The full trace around anterior electrode 61's 2.5 mV spikes and the 90/93 axonal pair — see [[giant_events]] |

## The highest-value first job

**Re-detect the whole cohort at a fixed threshold.** The strongest confound in the longitudinal result is not the sorter or the gate — the sensitivity sweep shows those move the anterior trend by less than cohort composition does. It is that the NSP's own online threshold changed between eras, so 2017 and 2023 are not measuring the same thing. Continuous data removes that confound outright, and it is the only thing that can.

Order of work, once files are staged:

1. Re-detect at a fixed `k × MAD` on the same sessions already analysed, and compare yield against the snippet result. The difference *is* the threshold drift.
2. Validate the snippet noise estimate on more than one session — the current bias figure rests on Nigel 2023-03-17 alone.
3. Run the sorter pool on a handful of sessions per era and check whether the per-electrode ISO-SPLIT result holds up. At 400 µm pitch it should, but that has never been tested against a multi-channel sorter on this data.
4. Pull the raw traces around the 51 recurring giant sites and the 288 axon-like sites.

## What does not need redoing

The event-level artifact/impulse/rail taxonomy, the CMP channel mapping, the impedance QC, and the segment-selection workaround are all independent of the data regime and carry over unchanged.

## Related

[[snippet_sorting]], [[snippet_noise_floor]], [[giant_events]], [[longitudinal_metrics]], [[threshold_crossing]], [[blackrock_loading]].

# Session 10 — three new corpora, and four conclusions revised

**Ask.** Process Chase (Plexon) and the second Rocky drop the way the other
subjects were processed; answer how the recording changes across acquisition
equipment; render TDT session previews; process the new Fisk drop; and manage
machine load so the box stays usable.

## Outcome

**Corpora added.** Chase (19 Plexon sessions, 2009–10), Rocky's broadband (431
`.ns5`, 2017–2023), Fisk's second drop (140 sessions with `.nev` + `.ns3` +
`.ns6`, 81 AutoImpedance files, a DS/Sidd pair set). The continuous layer went
from 67 candidate sessions to **559, all of which now have metrics**.

**Four published conclusions changed.**

1. **"Flat SNR while yield falls" — the SNR half is an artefact.** Fisk carries
   `.nev` and `.ns6` from the same recordings, so the layers differ only in the
   noise floor. In every series where either layer finds a trend they flip
   sign, snippet always more positive: Rocky ±0.10 against −0.74/−0.72, Fisk
   Medial +0.219 against −0.249. The yield half stands, being label-derived.
2. **Electrode coverage does not survive the move to continuous data** — two
   distinct values across 431 sessions. It is a snippet-layer metric.
3. **The operator offset drifts.** 14 matched Fisk pairs, systematic in 14 of
   14, but widening, so DS and Sidd report *opposite* trends on the same Medial
   sessions. Holding the operator fixed protects the level, not the slope.
4. **The analog headstage degrades.** Noise ratio against a same-day digital
   control goes 1.25 → 2.07 and 1.33 → 3.88. The "1.30× gain difference" was an
   era-average over a moving target.

**Equipment answered.** Three configurations fall into two gain regimes — TDT
and the analog headstage together, digital ~25% lower in noise *and* signal —
with SNR flat across the boundary at 2.93/3.05/3.14. Crossing rate is a
threshold setting, not a yield.

**Impedance.** Predicts unit yield weakly and array-specifically (median rho
−0.277 per session; −0.440 pooled on Medial, −0.197 on Lateral). One reading
cannot classify an electrode: the median channel crosses 1 MΩ seven times over
41 dates. Electrodes above 1 MΩ record at 95% of the good group's SNR.

**Chase** has the only externally documented event in the project — an
operator's "sharp decline" note on 2009-08-27. It is **not visible** as a step
(−1.45 SD on unit count after detrending, unremarkable in 19 sessions). A
before/after split looked like confirmation and was just a monotone series cut
near its middle; the report now says so instead of quoting the p-values.

**Kilosort4 has never run here.** 76 attempts, 0 results: RTX 5060 at compute
12.0 against an image built for older architectures. Dropped from the default
pool; CLAUDE.md's four-sorter policy is three on this hardware.

**Diverged from the plan.** The TDT channel map could not be inferred from
same-day Blackrock. The method works — 0.448 recovery of a known identity map —
but the signature is transient, and against a calibrated ceiling of 0.19–0.22
the TDT pairings scored 0.021. Previews stay in channel-index order.

**Machine.** A restart cleared a 124/127 GB commit charge. The cause was found
later: **`TaskStop` does not reap `ProcessPoolExecutor` workers**, so every
stopped job left its children running. Purging two recovered 17.6 GB. The
monitor now detects orphans by dead parent PID rather than by idle time, which
would never have caught busy orphans. 70 GB of regenerable sorter scratch was
also freed.

**Deferred.** Luigi's 319 previews (~26 h, running); the 50-session sort (11/49
when last checked); Fisk's `.ns3` LFP, untouched for all 140 sessions.

**Recurring bug class worth naming.** Three separate single-NaN-kills-the-
aggregate failures: `np.median` over a ratio with one NaN voided every
amplitude in ten sessions; `spearmanr` with one NaN session voided two whole
trends; and NEO's snippet overread put foreign bytes in every waveform. Each
was silent and each produced plausible output.

## SpikeInterface / NEO functions introduced

- `neo.rawio.PlexonRawIO` — Chase; `wf_gain` derives from `SpikeMaxMagnitudeMV`
  so `raw * gain` is millivolts, and `wf_units` is left empty.
- `neo.rawio.plexonrawio.GlobalHeader` — read directly for `NumPointsPreThr`,
  `ADFrequency` and the recording date, none of which NEO exposes.
- `spikeinterface.sortingcomponents.peak_detection.detect_peaks` with
  `method="by_channel"` — the continuous threshold-crossing layer.
- `scipy.optimize.linear_sum_assignment` — the channel-map assignment.

# The session preview figure

One page per recording per method. `notebooks/scratch_session_preview.py` →
`figures/<subject>/session_preview/<stem><chain>.png`.

Built to the conventions in the owner's MATLAB
(`Monkey Data/Older code/plot_U01_Utaharray_*.m`), with one deliberate change.

## Four panels

| panel | content |
|---|---|
| 1 | metrics table — identity, method and parameters, sorting result, sorting-based ephys, sorting quality, sorting-free metrics |
| 2 | per-unit waveforms, one axes per contact, **at physical array positions** |
| 3 | units-per-electrode grid, physical positions |
| 4 | max unit amplitude (µV peak-to-peak), physical positions |

## The change: physical positions, not channel index

The MATLAB laid panel 2 out as `subplot(10, 10, chan_indx)` — channel index
order — and says so in its own comment:

> *"The channel index here is for the Blackrock recording file channel index,
> NOT the elec# !!! Remap later."*

Its grid code does the remap, and keeps the earlier attempt commented out as a
warning:

> *"This is the old code that mapped the location using elec not the chan,
> which is WRONG!"*

That is exactly the channel-versus-electrode distinction settled in
[`channel_mapping`](channel_mapping.md). The MATLAB needed a hardcoded
`Blackrock_elec_to_channel_map` table to do it; here the `.cmp` carries `col`,
`row`, `channel_id` and the `elecN` label on the same row, so the lookup is
direct and comes from the array's own build record.

**It matters more than it sounds.** On Nigel's `SN 1025-001496`, only **2 of 96**
contacts have `channel_id == elec` number. Laying panel 2 out by channel index
puts 94 of 96 waveforms in the wrong place.

Verified three ways:

| array | vacant cells | checked against |
|---|---|---|
| Nigel Anterior `001496` | `(0,0) (0,1) (1,0) (3,9)` | `channel_mapping.md`, **and the owner's `cmpfile.mat`** |
| Nigel Posterior `001473` | `(0,0) (0,1) (9,0) (9,9)` | **the owner's `cmpfile.mat`** |
| Rocky I2 Anterior `004377` | `(0,0) (8,9) (9,8) (9,9)` | `cmp_validation.md` — the rewired array |

**The owner's own MATLAB mapping is correct.** `Older code/cmpfile.mat` holds
`CMP1496` and `CMP1473` as 10x10 matrices of elec numbers. Reconstructing the
same matrices from the official `.cmp` files reproduces them at **100 of 100
cells for both arrays**, once the row axis is flipped — which is the documented
convention, CMP rows counting up from the bottom while MATLAB prints row 1 at
the top.

`004377` is the array whose broken shanks were rewired at manufacture, so its
vacant cells are *not* the symmetric corners. The preview places them correctly,
which is a working check that the layout is coming from the mapfile rather than
from an assumption.

## Kept from the MATLAB

- **Unit amplitude is peak-to-peak of the mean waveform**, and a channel's
  amplitude is its largest unit. Not the peak-to-peak of the waveform cloud.
- **The shaded band is the full min-to-max envelope** at each sample, not a
  standard deviation or percentile.
- **`hot` colormap** on the grids, values printed in each cell.
- **Waveform y range ±200 µV**, from `plot_U01_Utaharray_05042023.m:209`.
- Unit classes 0 (unsorted) and 255 (noise) are excluded.

## Changed, on instruction

**No amplitude exclusion.** The MATLAB's `Min_P2P_exclusion = 20 µV` dropped
units whose *mean* waveform was flatter than 20 µV. Every declared unit is now
drawn and counted. On Nigel 2023-02-03 `-01` this is the difference between 210
and 211 units; on Rocky implant 2 it is 176 versus 194, because that array
carries more small units.

**A fixed y range, never autoscaled.** A large unit running off the top is
acceptable; a small one collapsing to a flat line is not. The number of clipped
envelopes is printed on the figure so the truncation is never silent.

**Two kinds of blank look different.** This was previously one grey, which
conflated two quite different facts:

| | appearance | meaning |
|---|---|---|
| no electrode wired to this cell | grey with a **red X** | nothing was ever going to be recorded |
| electrode present, recorded nothing | value **0**, black | a real measurement of a real contact |

**Fixed colour scales** — units 0–6, amplitude 0–600 µV, following the MATLAB's
`caxis` choices. The same colour means the same number in every figure, which
is the point of generating one per session.

**A colourblind-safe unit palette** (Okabe-Ito, extended to ten) rather than the
Spectral ramp, whose pale end is invisible on white.

**Rows drawn with CMP row 0 at the bottom**, so the layout reads as the
pad-side view the factory grids use.

## Sorting parameters, read from the batch files

Panel 1 reports the actual production parameters, parsed from the `.ofb` files:

```
SortType ScanTDist · SortDim 3 · ScanStat J3
ScanStart 10 · ScanEnd 30 · ScanStep 5
ArtifactWidth 60 · ArtifactPercentage 15 · OutlierThreshold 1.5
```

**Identical in every monkey and array folder checked** — Nigel Anterior and
Posterior, Fisk SN1498 and SN1504 — so this is the pipeline rather than one
operator's session. The `OFS sorting test2023` sweep used `ScanStart 1` and
`ArtifactPercentage 20`, so the sweep is not the production setting.

## Coverage

**1,799 figures** — every variant of every recording, excluding the Nigel OFS
algorithm sweep (eight runs of the same 78 sessions, `--include-sweep` to add
them):

| variant | n |
|---|---|
| original | 730 |
| `-01` | 697 |
| `-MA` | 228 |
| `-02` | 96 |
| everything else | 48 |

Gitignored — regenerable, and ~2 MB each.

## Reading it

The Rocky implant-2 example shows what the arrangement buys: its dead
electrodes form a contiguous block in the bottom-right of the array, obvious in
panels 3 and 4 and invisible in any channel-ordered view.

## Related

[[channel_mapping]] for the channel/electrode vocabulary and the verified chain,
[[cmp_validation]] for per-array geometry checks including the rewired
`004377`, [[measurement_floor]] for what the metrics in panel 1 are worth.

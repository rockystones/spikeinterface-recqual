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

Verified against the recorded geometry:

| array | vacant cells | matches |
|---|---|---|
| Nigel Anterior `001496` | `(0,0) (0,1) (1,0) (3,9)` | `channel_mapping.md` |
| Rocky I2 Anterior `004377` | `(0,0) (8,9) (9,8) (9,9)` | `cmp_validation.md` — the rewired array |

`004377` is the array whose broken shanks were rewired at manufacture, so its
vacant cells are *not* the symmetric corners. The preview places them correctly,
which is a working check that the layout is coming from the mapfile rather than
from an assumption.

## Conventions kept from the MATLAB

- **`Color_book`** — the same ten unit colours, in the same order.
- **`Min_P2P_exclusion = 20 µV`** — a unit whose *mean* waveform is flatter
  than this is not drawn. The table reports both declared and drawn counts so
  the cut is visible rather than silent.
- **Unit amplitude is peak-to-peak of the mean waveform**, and a channel's
  amplitude is its largest unit. Not the peak-to-peak of the waveform cloud.
- **The shaded band is the full min-to-max envelope** at each sample, not a
  standard deviation or percentile.
- **`hot` colormap**, absent contacts in dark grey, values printed in each cell.
- Unit classes 0 (unsorted) and 255 (noise) are excluded.

## Choices that are mine

**Panel 2 autoscales per panel by default** (`--yscale per-panel`), matching the
reference figure, with each panel's ± limit printed small in its corner. A
shared scale is available (`--yscale shared`) but flattens a 30 µV channel into
a line next to a 400 µV one. Shape and magnitude are deliberately split: panel 2
carries shape, panel 4 carries magnitude spatially.

**Rows are drawn with CMP row 0 at the bottom**, so the layout reads as the
pad-side view the factory grids use.

**A contact with no units still gets an empty framed panel**, greyed. A *vacant*
CMP cell gets no panel at all. The two are different facts and should not look
the same.

## Reading it

The Rocky implant-2 example shows what the arrangement buys: its dead
electrodes form a contiguous block in the bottom-right of the array, obvious in
panels 3 and 4 and invisible in any channel-ordered view.

## Related

[[channel_mapping]] for the channel/electrode vocabulary and the verified chain,
[[cmp_validation]] for per-array geometry checks including the rewired
`004377`, [[measurement_floor]] for what the metrics in panel 1 are worth.

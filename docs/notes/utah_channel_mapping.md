# Utah channel mapping

> **The authoritative definition of every channel number lives in [`channel_mapping.md`](channel_mapping.md)**, verified against Blackrock's documentation and against the NEV headers. This note covers the CMP parser and the probeinterface attachment.

Parsing a Blackrock per-array CMP file into a `probeinterface.Probe`, and the ID disambiguation needed to verify channel ordering against the recording.

## CMP file format

One row per connected electrode, whitespace-separated:

```
col  row  bank  elec  label
```

Blackrock's own definitions of the five columns [3]:

- `col`, `row`: position in Central's Spike Panel, **`0` = left** and **`0` = bottom**. On a Utah array this is also the physical grid position.
- `bank`: the channel's bank, lettered **A–H** [3]. A 96-channel Utah array uses A, B and C. The Front-End Amplifier has four banks [1].
- `elec`: 1..32, *"the channel's Pin in its given Bank"* [3]. **Despite the column name this is not an electrode number** — see [`channel_mapping.md`](channel_mapping.md).
- `label`: the electrode name, typically `elecNN`. **This is the electrode id.**

The header lines and any line starting with `//` are ignored. Lines that don't have `digit digit non-digit digit` in the first 4 columns are skipped (catches the leading descriptive line in Blackrock-issued CMPs).

## How many electrodes, and which

A Utah array carries **100 electrodes, of which 96 are connected** to the pedestal connector [5]. The four unconnected shanks are physically present but wired to nothing, so they never appear in the CMP.

**Which four are unconnected varies per array**, and Blackrock says so: *"arrays are often highly customized and the exact channel mappings vary from device to device. Please refer to the mapping datasheet included with your array"* [4]. Usually it is the four corners. Observed here:

| array | unconnected positions |
|---|---|
| Rocky `1025-001501`, `1025-001497`, `1025-004419` | `(0,0) (0,9) (9,0) (9,9)` |
| Rocky `1025-004377` | `(0,0) (8,9) (9,8) (9,9)` |
| Nigel `1025-001496` | `(0,0) (0,1) (1,0) (3,9)` |

Read positions from the array's own CMP. Never assume a pattern, and never reuse another array's map — see [`cmp_validation.md`](cmp_validation.md).

## Channel id

```python
channel_id = (ord(bank.upper()) - ord("A")) * 32 + elec   # A1..A32 -> 1..32, B -> 33..64, C -> 65..96
```

This is the integer that appears in the NEV and NSx files and in NEO spike-channel names like `chN#U`. It is the join key between the CMP, the recording, and Plexon's unit assignment. Blackrock states the same rule directly: *"pins 1-32 on Bank A will be channels 1-32 in Central, pins 1-32 on Bank B will be channels 33-64 in Central, and pins 1-32 on bank C will be channels 65-96 in Central"* [4].

## Probe build

```python
positions = [[r["col"] * 400.0, r["row"] * 400.0] for r in cmp_rows]   # 400 um electrode pitch [6]
probe.set_contacts(positions=positions, shapes="circle",
                   shape_params={"radius": 20.0},
                   contact_ids=[str(r["channel_id"]) for r in cmp_rows])
```

`contact_ids` are strings (PI convention). Set them from `channel_id` so the recording's channel-id strings (also derived from the same number) can be joined by equality.

## Attaching to a recording: `device_channel_indices`

For each probe contact `i`, `device_channel_indices[i]` must equal the recording channel index carrying that channel id. Build by dict lookup, never positionally:

```python
chan_index_by_id = {rec.channel_ids[i]: i for i in range(rec.get_num_channels())}
device_channel_indices = [chan_index_by_id[cid] for cid in probe.contact_ids]
probe.set_device_channel_indices(device_channel_indices)
rec_with_probe = rec.set_probe(probe, group_mode="by_probe")
```

**Assert zero unmapped contacts** before continuing. CLAUDE.md: channel-order mismatch is "silent and ruinous".

## The identities of one contact

A given physical contact has five identities in this project. Figure 1 in [session 02](../session_plans/session02_validation_figures.md) prints them per tile.

| name | source | type | example |
|---|---|---|---|
| `electrode_id` | the CMP `label` number, `elecNN` | `int` | `78` |
| `channel_id` | `(bank − 'A') * 32 + elec` | `int` | `1` |
| `si_channel_id` | SI `rec.channel_ids[i]` | `str` | `"1"` |
| `channel_index` | positional index into `rec.channel_ids` | `int` | `0` |
| `bank` / `pin` | CMP `bank` and `elec` | `str`/`int` | `A` / `1` |

In the Nigel 2023-03-17 file the recording-side relationship is the simplest possible — `channel_index + 1 == int(si_channel_id) == channel_id`. **Do not generalize**: CLAUDE.md's gotcha is that NSP firmware can write nsX files with non-contiguous channel ids. The validation script asserts the identity per file, and Figure 1 makes any deviation visible.

`electrode_id` is *not* in that chain and agrees with `channel_id` for only 8 of 384 electrodes across Rocky's four arrays.

## probeinterface used

- `Probe(ndim=2, si_units="um")`, `set_contacts`, `set_device_channel_indices`, `annotate`. The catalog probe (`get_probe`) was not used: building positions directly from the CMP is simpler than reconciling catalog coordinates against per-array unconnected-position patterns.
- `recording.set_probe(probe, group_mode="by_probe")` returns a probe-attached recording. `group_mode="by_probe"` puts all 96 channels into a single SI group, matching the [CLAUDE.md probe table](../../CLAUDE.md) (Utah arrays are single-group).

## Sources

1. *Cerebus Neural Signal Processing System Instructions for Use*, Rev 21.0, LB-0028, 2026-03 — Front-End Amplifier banks, p25.
3. *How to interpret and use mapfiles*, Blackrock support KB — column definitions.
4. *Blackrock Research Arrays IFU*, Rev 5.00, LB-0514, 2020 — bank→Central channels and per-device variation, p11.
5. *NeuroPort Electrode IFU*, Rev 3.00, LB-0612, 2022 — 100 electrodes, 96 connected, p8.
6. *Utah Array product specifications*, Blackrock Neurotech — "Electrode Pitch 400 um". <https://blackrockneurotech.com/products/utah-array/>

Numbering matches [`channel_mapping.md`](channel_mapping.md), which carries the full list.

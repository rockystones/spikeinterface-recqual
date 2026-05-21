# Utah channel mapping

Parsing a Blackrock per-array CMP file into a `probeinterface.Probe`, and the four-ID disambiguation needed to verify channel ordering against the recording.

## CMP file format

One row per electrode, whitespace-separated:

```
col  row  bank  elec  label
```

- `col`, `row`: integer position on the 10×10 grid. Row 0 is at the bottom, col 0 is at the left.
- `bank`: `A`, `B`, or `C`. The Cerebus NSP wires 32 contacts per bank.
- `elec`: 1..32, the Blackrock electrode number **within the bank**.
- `label`: free text (often `elecN`).

The header lines and any line starting with `//` are ignored. Lines that don't have `digit digit non-digit digit` in the first 4 columns are skipped (catches the leading descriptive line in Blackrock-issued CMPs).

The 96-electrode Utah array has **4 of the 100 grid positions unused**. In the Nigel array (SN 1025-001496) those are `(0,0)`, `(0,1)`, `(1,1)`, `(3,9)` — not all four corners, which is why we read positions from the CMP rather than assuming a standard pattern.

## Blackrock electrode ID

```python
electrode_id = (ord(bank.upper()) - ord("A")) * 32 + elec   # A1..A32 -> 1..32, B1..B32 -> 33..64, C1..C32 -> 65..96
```

This is the integer that appears in the NEV `signal_channels["id"]` field and in NEO spike-channel names like `chE#U`. It is the join key between the CMP, the recording, and Plexon's unit assignment.

## Probe build

```python
positions = [[r["col"] * 400.0, r["row"] * 400.0] for r in cmp_rows]   # Utah pitch is 400 um
probe.set_contacts(positions=positions, shapes="circle",
                   shape_params={"radius": 20.0},
                   contact_ids=[str(r["electrode_id"]) for r in cmp_rows])
```

`contact_ids` are strings (PI convention). Set them from `electrode_id` so the recording's `channel_id` strings (also derived from `electrode_id`) can be joined by equality.

## Attaching to a recording: `device_channel_indices`

For each probe contact `i`, `device_channel_indices[i]` must equal the recording channel index that has the matching electrode ID. Build by dict lookup, never positionally:

```python
chan_index_by_eid = {rec.channel_ids[i]: i for i in range(rec.get_num_channels())}
device_channel_indices = [chan_index_by_eid[cid] for cid in probe.contact_ids]
probe.set_device_channel_indices(device_channel_indices)
rec_with_probe = rec.set_probe(probe, group_mode="by_probe")
```

**Assert zero unmapped contacts** before continuing. CLAUDE.md: channel-order mismatch is "silent and ruinous".

## The four-ID disambiguation

A given physical contact has four identities in this project; Figure 1 in [session 02](../session_plans/session02_validation_figures.md) prints all four per tile:

| ID                  | Source                                        | Type     | Example |
|---------------------|-----------------------------------------------|----------|---------|
| `electrode_id`      | `(bank - 'A') * 32 + elec` from the CMP       | `int`    | `5`     |
| `channel_id`        | SI `rec.channel_ids[i]` (from NEV header)     | `str`    | `"5"`   |
| `channel_index`     | positional index into `rec.channel_ids`       | `int`    | `4`     |
| `bank` / `elec`     | CMP physical labeling                          | `str`/`int` | `A` / `5` |

In the Nigel 2023-03-17 file the relationship is the simplest possible — `channel_index + 1 == int(channel_id) == electrode_id`. **Do not generalize.** CLAUDE.md gotcha: Blackrock NSP firmware can write nsX files with non-contiguous electrode IDs. The validation script asserts this identity per file, and Figure 1 makes any deviation immediately visible.

## probeinterface used

- `Probe(ndim=2, si_units="um")`, `set_contacts`, `set_device_channel_indices`, `annotate`. The catalog probe (`get_probe`) was not used: building positions directly from the CMP is simpler than reconciling catalog coordinates against per-array missing-position patterns.
- `recording.set_probe(probe, group_mode="by_probe")` returns a probe-attached recording. `group_mode="by_probe"` puts all 96 channels into a single SI group, matching the [CLAUDE.md probe table](../../CLAUDE.md) (Utah arrays are single-group).

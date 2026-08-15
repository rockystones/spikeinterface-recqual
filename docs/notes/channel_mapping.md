# Channel mapping, hardware pin to data file

The one place this project settles what "channel" means. Six names below can refer to one physical contact, two of them contain the word *electrode*, and two pieces of software use the same word for different things. Getting it wrong silently permutes the array: every unit lands on a real channel, nothing errors, and every spatial conclusion is wrong.

Every claim below is either quoted from Blackrock documentation — cited inline and listed at the end — or measured on this project's own data and marked as such.

## The vocabulary

Settled 2026-08-14, matching Blackrock's own usage: **channel id indexes recording files, electrode id indexes physical shanks.**

| name | what it is | where it comes from |
|---|---|---|
| **`channel_id`** | index in the recording file. Blackrock's **Channel ID**: hardware sampling order, `(bank_index) × 32 + pin` | **the number in NEV and NSx files** |
| **`electrode_id`** | the physical shank. Blackrock's **Electrode ID** | CMP `label` column, `elecNN` |
| **`bank` + `pin`** | the amplifier connector position the shank is wired to | CMP columns `bank` and — misleadingly named — `elec` |
| **`col` / `row`** | position in Central's Spike Panel, 0-based, **row from the bottom**; on a Utah array this is also the physical layout, but the *origin is not guaranteed* [10] | CMP `col`, `row` |
| **`channel_index`** | 0-based position in a recording's channel list | SpikeInterface / NSx ordering |
| **`si_channel_id`** | SpikeInterface's channel-id *string* | `recording.channel_ids` |

Before this was settled the project used `electrode_id` for what is now `channel_id`, inheriting the name from neo. Values were always correct; only the name was wrong. `notebooks/scratch_rename_channel_id.py` migrated all 12 affected derived tables by renaming columns — no recomputation, and the longitudinal results reproduce exactly (posterior yield rho −0.644, anterior amplitude rho −0.736).

The CMP column named `elec` is **not** an electrode number. Blackrock defines it as *"the channel's Pin in its given Bank, numbered 1-32"* [3]. The electrode number lives in `label`.

## The rule

```
channel_id = (ord(bank) - ord('A')) * 32 + pin
```

Bank A pins 1–32 → channels 1–32, bank B → 33–64, bank C → 65–96.

**The rule is independent of array size.** Verified across 57 manufacturer mapfiles plus a 256-channel map [10]: 16-channel rodent arrays use bank A pins 1–16 only (channels 1–16, with 17–32 simply absent); 96-channel arrays use banks A–C; 256-channel arrays use banks **A–H** and satisfy the same formula for 256 of 256 rows. Only the number of banks changes.

Two independent statements of this. The file spec derives it: *"Channel ID order is defined by the sequential sampling of banks in order … and pins in order within each bank"* [2]. The arrays IFU states the result: *"pins 1-32 on Bank A will be channels 1-32 in Central, pins 1-32 on Bank B will be channels 33-64 in Central, and pins 1-32 on bank C will be channels 65-96 in Central"* [4].

Note the IFU's qualifier — *"by default (i.e., bank A on ICS connected to bank A of the amplifier …)"*. An adapter that crosses banks breaks it, and the same document warns that map files *"assume analog configurations"* and to confirm compatibility for custom adapters or digital headstages [4].

And the warning that makes all of this matter: *"Since electrodes are not wired to pins and banks in electrode order, Channel ID 1 is not necessarily equivalent to Electrode ID 1"* [2].

On Rocky's four arrays, `channel_id == electrode_id` for **8 of 384** electrodes. The two numbering systems agree essentially nowhere.

## The hardware the numbers come from

The amplifier side: *"The Front-End Amplifier has four 34-pin banks. Each bank consists of 32 channels, a bank reference pin, and a ground pin"* [1]. So a bank carries 32 signals plus a reference and a ground — 32 is the number that propagates downstream.

The array side: a CerePort assembly is *"the electrode array, the wire bundle, two reference wires, and the pedestal connector"* [4], and *"connector pins are associated into banks because most devices in the field process data in 32 channel banks/increments"* [4]. Electrode pitch is **400 µm** [6].

The connector between them is the **NeuroPort Plug**, which carries the contacts (fuzz-button pins originally, filament film later) on the head-stage housing of the patient cable and aligns onto the pedestal's LGA pads [7]. The *Pedestal Cap with Viton O-Ring* is a different object — the accessory that protects the pedestal when nothing is connected [4]. A digital headstage such as the CerePlex E instead mounts on the pedestal and digitises at the recording site [9].

## Verified, not assumed

The NEV's `NEUEVWAV` extended header stores **Physical Connector** (*"Front-End Bank A, B, C, D are 1, 2, 3, 4"*) and **Connector Pin** (*"1-32 on bank A, B, C, D"*) beside the channel identifier [2] — so the formula is testable against real recordings rather than trusted.

| recording | result |
|---|---|
| Rocky I1 2018-04-26 | **96/96** channels satisfy `id == (connector−1)×32 + pin`, banks A B C |
| Rocky I1 2023-07-27 | **96/96**, banks A B C |
| Nigel 2023-03-17 | **96/96**, banks A B C |

Digitization factor is 250 nV/LSB in all three, matching the 0.25 µV/count `wf_gain` the project reads from the header.

Geometry is verified separately against each array's factory pad-side location grid: **exact at 96/96 positions for all four Rocky arrays** — see [`cmp_validation.md`](cmp_validation.md).

`notebooks/scratch_channel_map.py` runs both checks and writes `data/derived/channel_map.parquet` plus one CSV per array in `configs/probes/`.

## Worked example

`SN 1025-001501`, first six channels:

| channel_id | bank | pin | electrode_label | electrode_id | col | row |
|---|---|---|---|---|---|---|
| 1 | A | 1 | elec78 | 78 | 2 | 9 |
| 2 | A | 2 | elec88 | 88 | 1 | 9 |
| 3 | A | 3 | elec68 | 68 | 3 | 9 |
| 4 | A | 4 | elec58 | 58 | 4 | 9 |
| 5 | A | 5 | elec56 | 56 | 4 | 7 |
| 6 | A | 6 | elec48 | 48 | 5 | 9 |

Read row 1 as: the electrode Blackrock calls **elec78** is wired to **bank A pin 1**, therefore appears in the NEV as **ch1**, and sits at grid **column 2, row 9** counting rows from the bottom.

## Two collisions that bite

**neo calls the Channel ID `electrode_id`.** `BlackrockRawIO` exposes the NEV's channel identifier under that name and renders channels `chNN`. In Blackrock's vocabulary — and in this project's, as of 2026-08-14 — that field is a *Channel ID*. It is read under neo's name and renamed on the way out, in one place, with a comment saying why. Anything reading NEV headers directly must do the same.

**The impedance `.txt` heads its rows `elec1..elec128`, but those are pins.** The factory workbook proves it directly: it prints the same array twice on one sheet, as *Electrode numbering viewing from pad side* and *Electrode Impedance viewing from pad side*, so each grid position gives an electrode number and its impedance together with no indexing assumption. Looking each electrode up in the `.cmp` and asking which table row carries its impedance:

| hypothesis | positions matched |
|---|---|
| row *N* = **channel id** | **1,248 / 1,248 — 100.00 %** |
| row *N* = electrode number | 31 / 1,248 — 2.48 %, i.e. chance |

13 arrays × 96 positions [10]. Rows above the channel count are unused pins on a larger front end and read in the kilohm range against ~100–1000 Ω for a real electrode.

This resolves the impedance join for the whole cohort: **index the file by `channel_id`, not by electrode number.** Joining it as electrode numbers scrambles the array while producing a full, plausible-looking table. See [`impedance_sources`](impedance_sources.md), which also parks the separate potentiostat EIS dataset — same array, different instrument, ordering not yet established.

## Which electrodes go unconnected varies per array

A Utah array has **100 electrodes, of which 96 are connected** to the pedestal connector [5]. The other four shanks exist physically but are wired to nothing and never appear in the map file.

*Which* four varies, and Blackrock documents the variation: *"arrays are often highly customized and the exact channel mappings vary from device to device. Please refer to the mapping datasheet included with your array"* [4]. In this lab's experience the substitution is how a shank broken during manufacture is compensated, by wiring a surviving one elsewhere to still reach 96 [8].

**It varies more than "usually the corners" suggests.** Across the 21 96-channel arrays in the manufacturer collection the symmetric-corner set appears in only **6** — 29 % — and the other 15 each differ [10]. 16-channel arrays have no unconnected positions at all. See [`array_catalog`](array_catalog.md).

| array | unconnected positions |
|---|---|
| Rocky 1025-001501, 001497, 004419 | `(0,0) (0,9) (9,0) (9,9)` |
| Rocky 1025-004377 | `(0,0) (8,9) (9,8) (9,9)` |
| Nigel 1025-001496 | `(0,0) (0,1) (1,0) (3,9)` |

Session 2 established this and wrote it into [`utah_channel_mapping`](utah_channel_mapping.md); session S07 then introduced a validator that assumed the symmetric corners, flagged the rewired array as corrupt, and "repaired" it onto positions that carry no connected electrode. Read positions from the array's own CMP. Never from a canonical layout, never from a sibling.

The 2026-08-15 audit also corrected Nigel's list, which had carried `(1,1)` since session 2 where its CMP says `(1,0)`.

## Rules

- Take `channel_id` from `bank` and `pin`; never treat CMP `elec` as an electrode number.
- Join Blackrock 1 kHz impedance files by `channel_id`. The potentiostat EIS data is a different instrument with an unsettled ordering — see [`impedance_sources`](impedance_sources.md).
- Take geometry from the array's own CMP, verified against its own pad map.
- Never share a channel map between arrays, even of the same model and lot.
- When reporting a channel, say which number it is.

## Sources

1. *Cerebus Neural Signal Processing System Instructions for Use*, Rev 21.0, **LB-0028**, 2026-03 — Front-End Amplifier banks §7.4 p25; Hardware Configuration §9.2 p36; Spike Panel §9.3 p65.
2. *TOC File Formats (File Spec 3.0) Specifications*, Rev 7.0, **LB-0110**, 2025-04 — "Channel ID, Electrode ID, and channel index" p26; NEUEVWAV extended header p11; NSx extended header p23. The same section appears in **LB-0023** Rev 8.
3. *How to interpret and use mapfiles*, Blackrock support KB — CMP column definitions; default sequential numbering by bank. <https://support.blackrockneurotech.com/portal/en/kb/articles/how-to-interpret-and-use-mapfiles>
4. *Blackrock Research Arrays IFU*, Rev 5.00, **LB-0514**, 2020 — map files assume analog configurations p3; CerePort assembly p6; banks and the electrode 33 ↔ pin B-01 example p8; bank→Central channels and per-device variation p11.
5. *NeuroPort Electrode IFU*, Rev 3.00, **LB-0612**, 2022 — "Number of Electrodes 100 (96 connected to percutaneous connector)" p8; pad-side datasheet layout p15.
6. *Utah Array product specifications*, Blackrock Neurotech — "Electrode Pitch 400 um". <https://blackrockneurotech.com/products/utah-array/>
7. *Filament Film NeuroPort Plug User's Manual*, **LB-0266** Rev DRAFT 1.00 — the plug carries the contacts onto the pedestal LGA; "care not to bend the internal ICS 96 pins" p3.
8. This project's own verification — see the section above and `notebooks/scratch_channel_map.py`.
10. Cross-validation of 57 manufacturer mapfiles and a 256-channel map — [`array_catalog`](array_catalog.md), `notebooks/scratch_array_catalog.py`.
9. *CerePlex E IFU*, Rev 5.00, **LB-0545**, 2021-04 — digital headstage interfacing a CerePort pedestal, digitising at the recording site p4.

## Related

[[utah_channel_mapping]] for the CMP parser and probeinterface attachment, [[cmp_validation]] for geometry validation, [[blackrock_loading]] for the file layer, [[impedance_parsing]] for the chronic measurement files.

# Channel mapping, hardware pin to data file

The one place this project settles what "channel" means. Four numbers can refer to a channel, three of them are called something like *electrode*, and two pieces of software use the same word for different things. Getting it wrong silently permutes the array: every unit lands on a real channel, nothing errors, and every spatial conclusion is wrong.

Sources: Blackrock **LB-0023 Rev 8**, section *"Channel ID, Electrode ID, and channel index"*; the KB article [*How to interpret and use mapfiles*](https://support.blackrockneurotech.com/portal/en/kb/articles/how-to-interpret-and-use-mapfiles); and empirical verification against the recordings themselves.

## The four numbers

| name here | what it is | where it comes from |
|---|---|---|
| **`bank` + `pin`** | the amplifier connector position the electrode is wired to | CMP columns `bank` and — misleadingly named — `elec` |
| **`channel_id`** | Blackrock's **Channel ID**: hardware sampling order, `(bank_index) × 32 + pin` | **this is the number in NEV and NSx files** |
| **`electrode_num`** | Blackrock's **Electrode ID**: the array electrode | CMP `label` column, `elecNN` |
| **`col` / `row`** | position on the 10×10 grid, 0-based, **row from the bottom** | CMP `col`, `row` |

The CMP column named `elec` is **not** an electrode number. The KB article defines it as *"the channel's Pin in its given Bank, numbered 1-32"*. The electrode number lives in `label`.

## The rule

```
channel_id = (ord(bank) - ord('A')) * 32 + pin
```

Bank A pins 1–32 → channels 1–32, bank B → 33–64, bank C → 65–96. LB-0023: *"Channel ID order is defined by the sequential sampling of banks in order … and pins in order within each bank."*

And the warning that makes all of this matter, from the same section: *"Since electrodes are not wired to pins and banks in electrode order, Channel ID 1 is not necessarily equivalent to Electrode ID 1."*

On Rocky's four arrays, `channel_id == electrode_num` for **8 of 384** electrodes. The two numbering systems agree essentially nowhere.

## Verified, not assumed

The NEV's `NEUEVWAV` extended header stores **Physical Connector** (*"Front-End Bank A, B, C, D are 1, 2, 3, 4"*) and **Connector Pin** (*"1-32 on bank A, B, C, D"*) beside the channel identifier — so the formula is testable against real recordings rather than trusted.

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

| channel_id | bank | pin | electrode_label | electrode_num | col | row |
|---|---|---|---|---|---|---|
| 1 | A | 1 | elec78 | 78 | 2 | 9 |
| 2 | A | 2 | elec88 | 88 | 1 | 9 |
| 3 | A | 3 | elec68 | 68 | 3 | 9 |
| 4 | A | 4 | elec58 | 58 | 4 | 9 |
| 5 | A | 5 | elec56 | 56 | 4 | 7 |
| 6 | A | 6 | elec48 | 48 | 5 | 9 |

Read row 1 as: the electrode Blackrock calls **elec78** is wired to **bank A pin 1**, therefore appears in the NEV as **ch1**, and sits at grid **column 2, row 9** counting rows from the bottom.

## Two collisions that bite

**neo calls the Channel ID `electrode_id`.** `BlackrockRawIO` exposes the NEV's channel identifier under that name and renders channels `chNN`. In Blackrock's vocabulary that field is a *Channel ID*, not an Electrode ID. This project inherited the name, so **`electrode_id` in every derived table written before this note means `channel_id`**. The values are correct; only the name is misleading. `build_map()` emits `electrode_id` as an explicit alias so old and new tables join, and new work should use `channel_id`.

**The impedance `.txt` heads its rows `elec1..elec128`, but those are pins.** Rows 1–32 are exactly the CMP's bank-A labels and 33–64 its bank-B labels; the alternative reading is impossible, because bank A's electrode numbers span 2–88 non-contiguously. Rows above 96 are unused bank-D pins on a 128-channel front end and read in the kilohm range against ~100–1000 Ω for a real electrode.

This resolves the impedance join for the whole cohort: **index the file by `channel_id`, not by electrode number.** Joining it as electrode numbers scrambles the array while producing a full, plausible-looking table.

## Which grid cells are empty varies per array

A Utah-96 populates 96 of 100 cells. *Which* four are vacant is a build property: shanks that break during manufacture are replaced by rewiring surviving shanks from elsewhere.

| array | vacant cells |
|---|---|
| Rocky 1025-001501, 001497, 004419 | `(0,0) (0,9) (9,0) (9,9)` |
| Rocky 1025-004377 | `(0,0) (8,9) (9,8) (9,9)` |
| Nigel 1025-001496 | `(0,0) (0,1) (1,1) (3,9)` |

Session 2 established this and wrote it into [`utah_channel_mapping`](utah_channel_mapping.md); session S07 then introduced a validator that assumed the symmetric corners, flagged the rewired array as corrupt, and "repaired" it onto cells holding no electrode. Read positions from the array's own CMP. Never from a canonical layout, never from a sibling.

## Rules

- Take `channel_id` from `bank` and `pin`; never treat CMP `elec` as an electrode number.
- Join impedance files by `channel_id`.
- Take geometry from the array's own CMP, verified against its own pad map.
- Never share a channel map between arrays, even of the same model and lot.
- When reporting a channel, say which number it is.

## Related

[[utah_channel_mapping]] for the CMP parser and probeinterface attachment, [[cmp_validation]] for geometry validation, [[blackrock_loading]] for the file layer, [[impedance_parsing]] for the chronic measurement files.

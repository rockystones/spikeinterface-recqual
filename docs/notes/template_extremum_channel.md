# `get_template_extremum_channel`

`spikeinterface.core.template_tools.get_template_extremum_channel(templates_or_sorting_analyzer, peak_sign="neg", mode="extremum", outputs="id")`

Returns a dict `{unit_id: channel_id_or_index}` mapping each unit to the channel where its template peak is largest. The "where does this unit sit on the probe?" function.

## Inputs and parameters

- First positional argument: a `Templates` object or a `SortingAnalyzer` with the `templates` extension computed (`sa.has_extension("templates")` must be true).
- **`peak_sign`**: `"neg"` (default), `"pos"`, or `"both"`. Extracellular action potentials are dominantly negative-going at the soma, so `"neg"` is the right default for spike sorting outputs. `"both"` falls back to absolute amplitude — useful when units could be either polarity (e.g. axonal recordings) but slower and slightly noisier.
- **`mode`**:
  - `"extremum"` — peak value (min for `peak_sign="neg"`, max for `"pos"`).
  - `"at_index"` — value sampled at `nbefore` (the alignment index). Less robust to template jitter.
  - `"peak_to_peak"` — full range across the template window. Robust to small phase shifts and to units with both positive and negative components. **Session 2 uses this.**
- **`outputs`**: `"id"` returns the SI `channel_id` (string in this project — Blackrock electrode IDs are strings like `"5"`); `"index"` returns the positional channel index (`int`).

## How session 2 uses it

```python
peak_id_by_unit = get_template_extremum_channel(
    sa, peak_sign="neg", mode="peak_to_peak", outputs="id"
)
peak_eid_by_unit = {u: int(cid) for u, cid in peak_id_by_unit.items()}
```

Then compared against the **assigned** electrode from the Plexon `chE#U` name. Found 1/217 mismatches (unit 297, assigned elec90, peak elec89 — adjacent contact). The function is the spatial cross-check on the unit-to-electrode assignment baked into the NEV file.

## Returns

A `dict` keyed by `unit_id`. **Order is not guaranteed**; iterate by `sorting.unit_ids` if you need a stable order matching the sorting object.

## Alternative considered

Computing the peak channel by hand: `np.argmax(np.ptp(templates, axis=1))` per unit, indexed into `sa.channel_ids`. Equivalent for the `peak_to_peak` case but loses the `peak_sign` polarity semantics. The SI helper also handles sparsity correctly (returns the peak within the unit's sparse mask, not the global recording channel) — relevant for any future sparse-analyzer work even if session 2 ran with `sparse=False`.

---
id: W-021
type: work
status: active
title: Outlier inspection kit - previews, MATLAB .fig regeneration and workspace bundles for Rocky's flagged sessions
created: 2026-09-19
actor: agent
basis: recorded
parent: P-03
informs: [REF-003]
gate: human
source: [notebooks/scratch_outlier_inspect.py, matlab/rocky_outlier_inspect.m, data/derived/rocky/outlier_inspect]
---
Owner asked (2026-09-19) for the session-preview treatment applied to
Rocky's potential outliers, plus a decide-and-inspect feature: pick
sessions, get native .fig figures and the unit/metric data in the
MATLAB workspace.

Built: scratch_outlier_inspect.py takes the 27 is_outlier stems from
two_array_metrics plus the 4 REF-003 residual candidates, ensures the
standard 4-panel preview page exists for each (sorted -01 chain
preferred; the two Dec-2018 amplitude-blowup stems exist only
unsorted), copies them into figures/rocky/outlier_preview/, and
exports per-stem MATLAB bundles (units.parquet + wf_mean/lo/hi
parquet matrices row-aligned to it + session.json with free metrics
and geometry; index.json as the menu). All parquet/JSON per the
no-pickle rule.

matlab/rocky_outlier_inspect.m is the deciding surface: edit
sessionsToInspect (stems or 'all'), run; per session it draws the
waveforms-at-physical-positions panel plus the units/amplitude grids
(fixed scales matching the Python preview), saves <stem>.fig, and
leaves M (units table, waveform matrices, free metrics, geometry,
two_array_metrics slice) plus idx in the workspace. Provenance-style
data dictionary in the header.

Gate: the actual include/exclude rulings on these 31 sessions are
the owner's; they feed back into the OUTLIERS dict of
scratch_two_array_metrics.py.

# Inspecting variables and derived tables

How to work through this project's scripts the way a MATLAB variable explorer works: step a cell, look at what came out, check it is what you meant.

## Do not install Spyder into the project venv

Spyder depends on PyQt5, whose `pyqt5-qt5` wheel does not exist for `win_amd64`. That is the exact dependency that made `uv sync` unresolvable and took three attempts to diagnose (see [`session_state.md`](session_state.md)). Installing Spyder here would re-break the environment.

Install Spyder separately, and put only `spyder-kernels` — pure Python, no Qt — into the project env:

```bash
uv pip install spyder-kernels
uv run python -m spyder_kernels.console --matplotlib=inline
```

It prints a connection-file path. In Spyder: **Consoles → Connect to an existing kernel**, point at that JSON. Spyder 6 needs spyder-kernels 3.x; Spyder 5.5 needs 2.5.x.

VS Code's Jupyter extension is the zero-install alternative and needs none of this.

## Cell markers

Every script in `notebooks/` carries `# %%` immediately above each column-0 `# === Section ===` header and above `def main(`, so it runs cell-by-cell with results landing in the global namespace. The markers were added mechanically in one pass — 100 comment lines, zero statements touched, verified by re-running and diffing output.

The analysis logic still lives inside `main()`. The helpers around it are pure functions returning real objects, so the usual move is to import and drive them directly rather than run the script:

```python
import sys; sys.path.insert(0, "notebooks")
from scratch_rocky_events import event_stats_session, coincidence_counts
```

## Derived tables

`notebooks/explore.py` loads every parquet under `data/derived/` into one namespace. All 20 tables together are ~30 MB, so there is no reason to query lazily.

```python
from explore import load_all, describe_all, describe, peek
describe_all()                  # shape, memory, date span, scope caveat
globals().update(load_all())    # units_long, events_electrode, ... in scope
describe(units_long)            # per-column dtype/nulls/distinct/min/median/max
```

`describe_all()` prints which tables are **not** full-cohort — `methods_long`, `curation_labels`, `method_agreement`, `method_jaccard` are stratified subsets and must not be pooled with the rest.

## Related

[[session_state]] for the environment constraints, [[coding_conventions]] for the naming rules that make a variable explorer readable.

"""Load every derived table into one namespace for interactive inspection.

Written for a variable-explorer workflow: run one line, get every parquet in
`data/derived/` as a named DataFrame sitting alongside your script variables,
then double-click them in Spyder's Variable Explorer (or VS Code's Data
Viewer). Everything the project produces fits in memory -- 18 tables, ~30 MB
total, the largest being `methods_long` at 11 MB -- so there is no reason to
query lazily.

Typical use, from the repo root::

    import sys; sys.path.insert(0, "notebooks")
    from explore import load_all, describe_all, describe, peek

    describe_all()              # what exists, how big, what it spans
    globals().update(load_all())  # units_long, events_electrode, ... in scope
    describe(units_long)        # per-column summary, MATLAB-style

To attach Spyder to this project's interpreter without installing Qt into the
venv (PyQt5 has no win_amd64 wheel and breaks `uv sync`)::

    uv pip install spyder-kernels
    uv run python -m spyder_kernels.console --matplotlib=inline

then Consoles -> Connect to an existing kernel, and point at the printed JSON.

See docs/notes/session_state.md for which tables are full-cohort and which are
stratified subsets -- they must not be pooled.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
DERIVED = REPO / "data" / "derived"

# Tables whose scope differs from the full 332-session cohort. Pooling these
# with the full-cohort tables silently double- or under-counts; the warning is
# printed by describe_all() so it cannot be missed during exploration.
SUBSET_SCOPE = {
    "methods_long": "60-session stratified subset, 5 methods, 4000 spikes/electrode",
    "curation_labels": "derived from methods_long, so the same 60-session subset",
    "method_agreement": "12-session subset",
    "method_jaccard": "12-session subset",
}


def table_paths() -> dict[str, Path]:
    """Map a short name to every parquet under ``data/derived``.

    Names are the file stem; if two directories hold the same stem the parent
    directory is prefixed so nothing is silently shadowed.
    """
    found: dict[str, list[Path]] = {}
    for p in sorted(DERIVED.rglob("*.parquet")):
        found.setdefault(p.stem, []).append(p)
    out: dict[str, Path] = {}
    for stem, paths in found.items():
        if len(paths) == 1:
            out[stem] = paths[0]
        else:
            for p in paths:
                out[f"{p.parent.name}_{stem}"] = p
    return out


def load_all(exclude_shards: bool = True) -> dict[str, pd.DataFrame]:
    """Read every derived parquet into a dict of DataFrames.

    Parameters
    ----------
    exclude_shards : bool
        Skip the per-session shard directories, which are intermediate outputs
        already concatenated into the top-level tables.

    Returns
    -------
    dict
        ``name -> DataFrame``. Pass to ``globals().update(...)`` to get them as
        plain variables in the Variable Explorer.
    """
    out = {}
    for name, p in table_paths().items():
        if exclude_shards and "shards" in p.parent.name:
            continue
        out[name] = pd.read_parquet(p)
    return out


def _span(df: pd.DataFrame) -> str:
    """Date range of a table, if it carries a date column."""
    if "date" not in df.columns:
        return ""
    s = df["date"].dropna()
    return f"{s.min()} .. {s.max()}" if len(s) else ""


def describe_all(exclude_shards: bool = True) -> pd.DataFrame:
    """One row per derived table: shape, memory, date span, scope caveat.

    Returns the frame as well as printing it, so it can be inspected in the
    Variable Explorer like anything else.
    """
    rows = []
    for name, p in table_paths().items():
        if exclude_shards and "shards" in p.parent.name:
            continue
        df = pd.read_parquet(p)
        rows.append(dict(
            table=name,
            rows=len(df),
            cols=df.shape[1],
            mb=round(df.memory_usage(deep=True).sum() / 1e6, 1),
            span=_span(df),
            scope=SUBSET_SCOPE.get(name, "full cohort"),
        ))
    out = pd.DataFrame(rows).sort_values("rows", ascending=False)
    with pd.option_context("display.width", 200, "display.max_colwidth", 60):
        print(out.to_string(index=False))
    subs = [r for r in rows if r["scope"] != "full cohort"]
    if subs:
        print(f"\n  {len(subs)} tables are NOT the full cohort -- do not pool "
              f"them with the rest (see docs/notes/session_state.md).")
    return out


def describe(df: pd.DataFrame, max_rows: int = 60) -> pd.DataFrame:
    """Per-column summary of a DataFrame, in the shape MATLAB's explorer gives.

    Parameters
    ----------
    df : pandas.DataFrame
        Any table.
    max_rows : int
        Cap on columns reported, so a 58-column table stays readable.

    Returns
    -------
    pandas.DataFrame
        dtype, non-null count, distinct count, and min/median/max for numeric
        columns; the two most common values for everything else.
    """
    rows = []
    for c in df.columns[:max_rows]:
        s = df[c]
        rec = dict(column=c, dtype=str(s.dtype), non_null=int(s.notna().sum()),
                   nulls=int(s.isna().sum()), distinct=int(s.nunique(dropna=True)))
        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            v = s.dropna().to_numpy()
            if len(v):
                rec |= dict(min=float(np.min(v)), median=float(np.median(v)),
                            max=float(np.max(v)))
        else:
            top = s.value_counts().head(2)
            rec["common"] = ", ".join(f"{k}({v})" for k, v in top.items())
        rows.append(rec)
    out = pd.DataFrame(rows)
    with pd.option_context("display.width", 220, "display.max_colwidth", 44,
                           "display.float_format", lambda x: f"{x:,.3f}"):
        print(out.to_string(index=False))
    if df.shape[1] > max_rows:
        print(f"\n  ... {df.shape[1] - max_rows} more columns "
              f"(raise max_rows to see them)")
    return out


def peek(name: str, n: int = 8) -> pd.DataFrame:
    """Load one table by name and print its head, without loading the rest."""
    paths = table_paths()
    if name not in paths:
        close = [k for k in paths if name in k]
        raise KeyError(f"no table {name!r}; did you mean {close or list(paths)[:6]}?")
    df = pd.read_parquet(paths[name])
    print(f"{name}: {df.shape[0]:,} x {df.shape[1]}   {paths[name]}")
    with pd.option_context("display.width", 220, "display.max_columns", 40):
        print(df.head(n).to_string())
    return df


if __name__ == "__main__":
    describe_all()

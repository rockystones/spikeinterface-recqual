"""A place to leave intermediates so they can be inspected after a run.

The MATLAB habit this replaces is assigning to the base workspace from inside a
function. Python has no base workspace, so scripts stash into a module-level
dict instead and it is read from an interactive session afterwards:

    from _probe import probe
    probe(noise=noise, wf=wf, elec=elec)        # anywhere

    from _probe import STASH
    STASH["wf"].shape

**It does not cross a process boundary.** Every long analysis in this project
runs under `ProcessPoolExecutor`, and a worker's `STASH` dies with the worker.
To inspect inside a parallel step, call the per-item function directly in your
own session -- all of them are importable and take plain arguments. See
docs/notes/validation_guide.md.

Left in production code deliberately: `probe()` costs a dict write when unused,
and stripping the calls out again is how a debugging aid stops being available
the next time it is needed.
"""

from __future__ import annotations

from typing import Any

# name -> most recent value. Deliberately last-write-wins: a loop leaves the
# final iteration, which is what you want when checking that a loop terminated
# on the value you expected.
STASH: dict[str, Any] = {}

# name -> every value seen, for the cases where the trajectory matters.
HISTORY: dict[str, list[Any]] = {}
_RECORD_HISTORY = False


def probe(**values: Any) -> None:
    """Stash values under their keyword names. Returns nothing."""
    STASH.update(values)
    if _RECORD_HISTORY:
        for k, v in values.items():
            HISTORY.setdefault(k, []).append(v)


def record_history(on: bool = True) -> None:
    """Keep every probed value, not just the last.

    Off by default: a per-spike probe inside a 2.4 M-event session would hold
    the whole recording in memory, which is the failure mode that exhausted RAM
    on this cohort before.
    """
    global _RECORD_HISTORY
    _RECORD_HISTORY = on


def clear() -> None:
    """Empty both stores."""
    STASH.clear()
    HISTORY.clear()


def summary() -> str:
    """One line per stashed name: type, and shape or length where it has one."""
    if not STASH:
        return "(nothing stashed)"
    lines = []
    for k in sorted(STASH):
        v = STASH[k]
        shape = getattr(v, "shape", None)
        size = shape if shape is not None else (
            len(v) if hasattr(v, "__len__") else "")
        lines.append(f"  {k:24s} {type(v).__name__:16s} {size}")
    return "\n".join(lines)

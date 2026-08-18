"""Data roots, in one place so a reorganisation is a one-line change.

`D:\\Claude Code\\Rocky` was merged into `D:\\Claude Code\\Monkey Data\\Rocky` on
2026-08-15 and ten scratch scripts held that path as a literal. They now import
from here.

Usage from a script in `notebooks/`:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _paths import ROCKY, MONKEY_ROOT
"""

from __future__ import annotations

from pathlib import Path

# Everything staged locally for analysis.
MONKEY_ROOT = Path(r"D:\Claude Code\Monkey Data")

# Per-subject trees. Rocky's two implants are separate trees, which is the only
# reason the implant is knowable from the path alone.
ROCKY = MONKEY_ROOT / "Rocky"               # implant 1, 2017-2024
ROCKY_NEW = MONKEY_ROOT / "Rocky New"       # implant 2, 2025
NIGEL = MONKEY_ROOT / "Nigel"
FISK = MONKEY_ROOT / "Fisk"

# TDT-era subjects. Oops and Picasso sit beside the Blackrock trees; Luigi is
# on a separate volume and was not moved, because at 276 GB it is larger than
# the rest of the local corpus combined.
OOPS = MONKEY_ROOT / "Oops"
PICASSO = MONKEY_ROOT / "Picasso"
LUIGI = Path(r"C:\MyData\Monkeydata\Luigi")

# Array mapfiles, factory workbooks and pre-implant impedance for Rocky I1.
ROCKY_PREIMPLANT = ROCKY / "preimplant"
# Chronic potentiostat EIS, per-date folders of {Array}_{Bank}{Half}.txt.
ROCKY_POSTIMPLANT = ROCKY / "postimplant"

# Manufacturer CD collection: 57 arrays, cross-validated in array_catalog.md.
BLACKROCK_FILES = Path(r"D:\Claude Code\Blackrock files")
UTAH_CD_ROOT = (BLACKROCK_FILES / "Blackrock Utah array"
                / "Utah array manufacture CD files")


def require(p: Path) -> Path:
    """Fail loudly at import time rather than with an empty result set later.

    A moved data root otherwise shows up as "0 sessions found", which reads as
    a filter bug and costs far more to diagnose than a missing directory.
    """
    if not p.exists():
        raise FileNotFoundError(f"data root not found: {p}")
    return p

#!/usr/bin/env python3
"""NAV pilot validator. stdlib + PyYAML. Run from repo root: python nav/check.py"""
import sys, re, json, collections, pathlib

try:
    import yaml
except ImportError:
    sys.exit("PyYAML missing: pip install pyyaml")

ENTRIES = pathlib.Path(__file__).resolve().parent / "entries"
TYPES = {"aim", "phase", "work", "decision", "result", "issue", "question", "other"}
STATUS = {
    "aim": {"active", "done", "abandoned"},
    "phase": {"proposed", "active", "done", "abandoned"},
    "work": {"proposed", "active", "blocked", "done", "parked", "abandoned"},
    "decision": {"proposed", "accepted", "rejected", "superseded"},
    "result": {"current", "superseded"},
    "issue": {"open", "active", "resolved", "wontfix"},
    "question": {"open", "answered", "parked", "withdrawn"},
    "other": set(),
}
CORE = {
    "id", "type", "status", "title", "created", "owner", "basis",
    "summary", "parent", "depends_on", "supersedes", "resolves", "evidence",
    "source", "tags", "updated", "closed",
    "order", "hill", "prediction", "credence", "falsifier", "verdict",
}
LINK_FIELDS = ["parent", "depends_on", "supersedes", "resolves", "evidence"]
OPEN = {"proposed", "active", "open", "blocked"}


def load(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return None, text
    return (yaml.safe_load(m.group(1)) or {}), m.group(2)


entries, errors = {}, []
for p in sorted(ENTRIES.glob("*.md")):
    fm, body = load(p)
    if fm is None:
        errors.append(f"{p.name}: no frontmatter")
        continue
    eid = fm.get("id")
    if not eid:
        errors.append(f"{p.name}: missing id")
        continue
    if eid in entries:
        errors.append(f"{p.name}: duplicate id {eid}")
    entries[eid] = (fm, body, p.name)

by_type, by_status = collections.Counter(), collections.Counter()
xfields, other_types = collections.Counter(), collections.Counter()
basis, owner = collections.Counter(), collections.Counter()
dangling, no_source = [], []

for eid, (fm, body, name) in entries.items():
    t, s = fm.get("type"), fm.get("status")
    if t not in TYPES:
        errors.append(f"{eid}: unknown type {t!r}")
    elif t != "other" and s not in STATUS[t]:
        errors.append(f"{eid}: status {s!r} not allowed for {t}")
    by_type[t] += 1
    by_status[f"{t}/{s}"] += 1
    basis[fm.get("basis")] += 1
    owner[fm.get("owner")] += 1
    if t == "other":
        other_types[fm.get("x_proposed_type")] += 1
    for k in fm:
        if k.startswith("x_"):
            xfields[k] += 1
        elif k not in CORE:
            errors.append(f"{eid}: unknown field {k!r} (use an x_ prefix)")
    for f in LINK_FIELDS:
        v = fm.get(f)
        if v is None:
            continue
        for target in (v if isinstance(v, list) else [v]):
            if isinstance(target, str) and re.match(r"^[A-Z]+-\d+$", target) and target not in entries:
                dangling.append(f"{eid}.{f} -> {target}")
    if not fm.get("source"):
        no_source.append(eid)
    if not body.strip():
        errors.append(f"{eid}: empty body")

pending = sorted(
    e for e, (fm, _, _) in entries.items()
    if fm.get("owner") == "human" and (fm.get("status") in OPEN or fm.get("type") == "result")
)

report = {
    "n_entries": len(entries),
    "by_type": dict(by_type),
    "by_status": dict(by_status),
    "basis": dict(basis),
    "owner": dict(owner),
    "x_fields": dict(xfields),
    "other_proposed_types": dict(other_types),
    "pending_from_human": pending,
    "entries_without_source": no_source,
    "dangling_links": dangling,
    "errors": errors,
}
print(json.dumps(report, indent=2, default=str))
sys.exit(1 if errors else 0)

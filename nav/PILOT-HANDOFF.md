# NAV pilot handoff (schema v0.1)

For a Claude Code session running inside one project repository. To run: copy this file to `nav/PILOT-HANDOFF.md` in the repo and instruct the session to execute it end to end.

## Purpose

Test whether a small, topic-agnostic ledger schema can represent this project's navigational state (goal, plan, strategy, what was done, what worked and didn't, what is next and what is waiting on the human) well enough that a reader holding only the generated `STATE.md` could make the project's live decisions. You are a pilot site, not a builder: instantiate the schema on this project exactly as written, record where it fits and where it strains, and write one report. Stone will compare reports across projects of different kinds and revise the schema. Where the schema fails is more valuable to him than where it fits, so record strain honestly.

## 0. Ground rules

1. Work on a branch named `nav-pilot`. Create only the `nav/` folder. Do not edit, move, or delete any other file. Commit at the end.
2. Do not build tooling. No HTML, no generator, no dependency beyond PyYAML for `nav/check.py` (Appendix A).
3. Do not adapt the schema silently. Extensions go only through `x_` fields and `type: other` (Section 3.6). Every extension is data for the report.
4. Do not invent history. Every entry carries `basis: recorded` (explicit in project files, logs, commits, issues, chats saved in the repo) or `basis: inferred` (reconstructed from code, structure, or context). If you cannot tell whether something was decided, file a `question`, never a `decision`.
5. Budget: one session. Cap at 60 entries using the sampling rule in Section 3.7 and report what you omitted.
6. Every ambiguity you resolve by judgment goes in the report. The ambiguities are half the point of the pilot.
7. Work through the phases in order. Write `nav/INVENTORY.md` (Phase 1) before writing any entry, in the project's own vocabulary, not the schema's.

## 1. Phase 0: orient

Read, in this order, whatever exists: `README`, `CLAUDE.md`, `docs/` and any plan, roadmap, or design files, memory and session-log files (`MEMORY.md`, `HANDOFF.md`, `sessions/`, `memory/`), open TODO lists, `gh issue list` if the repo uses issues, `git log --oneline -200`, and any existing navigation or dashboard HTML (`git ls-files '*.html'`; the file that lays out the project's directions, decisions, or steps is the "legacy HTML"; there may be none). Write nothing yet.

## 2. Phase 1: blind inventory, native vocabulary

Write `nav/INVENTORY.md`: every trackable thing the project has, in the project's own words. Do not use the schema's type names in this file. One table, columns:

`item | native kind | where recorded | last touched | mapping`

`native kind` is the word the project itself uses (milestone, session card, hypothesis, bug, invariant, TODO, finding, pin, cap, deliverable, reading, routine, and so on). Include things that are only implied, such as an obviously pending choice nobody wrote down, and mark them `implied` in `where recorded`. Leave `mapping` empty for now; Phase 2 fills it. Completeness over polish; 30 to 120 rows is typical.

## 3. Schema v0.1

### 3.1 Entry files

`nav/entries/<ID>-<slug>.md`, one entry per file, YAML frontmatter plus a Markdown body. One file per entry so that parallel sessions never conflict on a shared ledger file.

IDs: type prefix plus zero-padded number, one global sequence per prefix (`A-001`, `P-01`, `W-031`, `D-014`, `R-031`, `I-007`, `Q-007`, `X-001`). Never renumber, never reuse. A `result` is never edited after the fact; a newer result supersedes it (the one permitted metadata edit on a result is `owner`, see 3.4).

### 3.2 Types

| type | prefix | what it is |
|---|---|---|
| aim | A | The outcome the project exists to produce. One to three per project. Success criterion and the approach (the strategy in one paragraph) in the body. |
| phase | P | A stage of the roadmap. Ordered. Contains work. Keep to eight or fewer. |
| work | W | A unit of planned or executing work that takes at least one session or that someone waits on: an experiment, a build item, a session card, a document to write. "Things to try" are work with status `proposed`; `parked` when not committed for the foreseeable future, with a wake trigger in the body. |
| decision | D | A choice among options that constrains future work. Includes constraints, invariants, pins, and budget caps: a decision with no live alternative is still a decision. `proposed` means awaiting the human. |
| result | R | An immutable record of something that happened: an experiment ran, a measurement was taken, an external finding arrived. Carries a verdict. |
| issue | I | Something wrong or blocking whose resolution is action. |
| question | Q | Something unknown whose resolution is knowledge. When it carries a prediction it is a hypothesis; use the `prediction`, `credence`, and `falsifier` fields. |
| other | X | Does not fit any of the above. Requires `x_proposed_type` (Section 3.6). |

Boundary rules:

- result versus decision: a result reports what happened; a decision commits what will happen. "Config 2 fails at 1k notes" is a result; "drop config 2" is a decision that cites it via `evidence`.
- issue versus question: if resolving it is fixing, it is an issue; if resolving it is finding out, it is a question.
- phase versus work: if others wait on its sub-steps individually, it is a phase or a parent work item with child work items.
- Not an entry: micro-steps, individual commands, bugs fixed within one session, anything you would never point at later by id. These stay in logs and commits and are referenced from entries through `source`. This boundary is the tree-versus-forest line; the report asks how decidable it was.

### 3.3 Statuses, per type

| type | allowed statuses |
|---|---|
| aim | active, done, abandoned |
| phase | proposed, active, done, abandoned |
| work | proposed, active, blocked, done, parked, abandoned |
| decision | proposed, accepted, rejected, superseded |
| result | current, superseded |
| issue | open, active, resolved, wontfix |
| question | open, answered, parked, withdrawn |

### 3.4 Fields

Required on every entry: `id`, `type`, `status`, `title`, `created` (YYYY-MM-DD, the date the item entered the project per the record; if unknown, the pilot date, and say so in the body), `owner`, `basis`.

- `owner`: who must act for this entry to progress: `human`, `agent`, or `external`. The pending-from-human queue is every entry with `owner: human` that is not closed. For a `result`, `owner: human` means it awaits the human's review; flip it to `agent` once reviewed.
- `basis`: `recorded` or `inferred` (ground rule 4).

Optional on any type:

- `summary`: one line.
- `parent`: single id, containment (work in phase, phase in aim, sub-work in work). A work item's phase is its nearest ancestor of type phase.
- `depends_on`: list of ids that must be done, decided, or answered first.
- `supersedes`: list of ids this entry replaces.
- `resolves`: list of ids this entry closes (a result or decision closing a question, issue, or work item).
- `evidence`: list of ids, repo paths, or URLs supporting this entry.
- `source`: list of repo paths, session ids, chat references, or URLs saying where this entry came from (provenance).
- `tags`: list.
- `updated`, `closed`: dates.

Type-specific:

- phase: `order` (integer).
- work: `hill`, one of `uphill`, `crest`, `downhill`, on active work only. Uphill means still figuring out how; downhill means known work remaining.
- question: `prediction` (one line), `credence` (0 to 1), `falsifier` (one line).
- result: `verdict`, one of `works`, `fails`, `inconclusive`, `measured` (a neutral measurement that is neither success nor failure).

Do not store derived fields. The future builder derives `blocks` from `depends_on`, children from `parent`, and an "unblocks count" for ranking the human queue.

### 3.5 Body conventions

- decision: Context, Options, Choice, Consequences, as four short paragraphs or headers.
- result: What ran, Outcome (with numbers), Interpretation.
- work: what done looks like; for parked work, the wake trigger.
- aim: success criterion, then the approach.
- Others free. Keep bodies short; link out through `source`.

### 3.6 Extension protocol

- A field the schema lacks: add it with an `x_` prefix (`x_cost_usd`, `x_cadence`, `x_severity`). Use each `x_` name consistently within the repo.
- A type the schema lacks: `type: other`, prefix `X`, plus `x_proposed_type: <name>` and a one-line definition in the body.
- A status the schema lacks: use the nearest allowed status and add `x_status_wanted: <name>`.

`check.py` counts all of these; the report explains each one.

### 3.7 Sampling rule

If the project has more than 60 candidate entries: include all aims, phases, open questions, open issues, proposed decisions, and active or blocked work; then the ten most recent results and the ten most recent accepted decisions; then parked work up to the cap. Report the number omitted per type.

### 3.8 Examples

```markdown
---
id: D-014
type: decision
status: accepted
title: SQLite over DuckDB for the catalog store
created: 2026-06-03
owner: agent
basis: recorded
supersedes: [D-009]
resolves: [Q-004]
evidence: [R-022]
source: [docs/design.md#storage, sessions/S07.md]
---
Context: the catalog needs single-writer access from a watcher plus ad hoc analytics.
Options: SQLite; DuckDB; both.
Choice: SQLite as system of record; DuckDB attached read-only for analytics.
Consequences: analytics never writes; D-009 (DuckDB primary) superseded.
```

```markdown
---
id: W-031
type: work
status: active
title: Run config 2 against the 1k-note slice
created: 2026-09-02
owner: agent
basis: recorded
parent: P-03
depends_on: [D-014]
hill: downhill
source: [sessions/S12.md]
---
Done looks like: pass-rate table for the 28-query battery at n = 50/100/150/168 with telemetry, committed under results/.
```

```markdown
---
id: R-031
type: result
status: current
title: Config 2 pass rate drops two bins between 100 and 150 notes
created: 2026-09-05
owner: human
basis: recorded
resolves: [W-031]
verdict: fails
source: [results/config2-run1.md]
---
What ran: W-031 as specified.
Outcome: 21/28 to 15/28 between checkpoints 100 and 150; index at 48% of context.
Interpretation: break criterion met; config 2 does not hold at 1k. Drop-or-tune is an open decision.
```

```markdown
---
id: Q-007
type: question
status: open
title: How much anchor fidelity is lost between character-span and heading-level addressing?
created: 2026-08-20
owner: agent
basis: recorded
parent: P-03
prediction: median loss under 5% of anchors on the 168-note slice
credence: 0.6
falsifier: loss above 15% at any checkpoint
source: [docs/design.md#anchors]
---
Gates D-011 (client architecture, proposed). Answered by a measurement result carrying `resolves: [Q-007]`.
```

## 4. Phase 2: instantiate

1. Map every `INVENTORY.md` row to the schema and fill its `mapping` column with one of: an entry id; `LOSSY: <what was lost>` when it maps but drops something; `NONE: <why>` when it does not map (these become `type: other` entries or are deliberately excluded under the not-an-entry rule, and you say which).
2. Write the entries.
3. Write `nav/check.py` from Appendix A. Run `python nav/check.py` from the repo root, fix errors (dangling links, disallowed statuses, unknown fields), and paste the final JSON into the report.

## 5. Phase 3: STATE.md and DELTA.md by hand, from entries only

Close the project documents. Using `nav/entries/` only, write `nav/STATE.md` with the template below. If a section cannot be filled from entries alone, leave the placeholder and record in the report what you would have needed. Then answer the six navigation questions (Section 8, part 3) from `STATE.md` alone.

```markdown
# STATE: <project>, generated <date> from nav/entries (by hand, pilot)

## Aim
<A-001 one line; success criterion; approach in one sentence>

## Pending from the human, ranked by what each unblocks
1. <id> (<type>, <status>): <title>. Unblocks: <ids>
...

## Phase and position
Current phase: <P-xx title>. Phases: <P-01 done, P-02 done, P-03 active, P-04 proposed>
Active work: <W-xx uphill; W-yy downhill; W-zz blocked on I-nn>

## Accepted decisions, latest first (max 10)
<D-xx: title>

## What worked and what didn't, latest first (max 10)
<R-xx (verdict): title>

## Open questions and issues
<Q-xx open (owner): title> / <I-xx open, blocks W-yy: title>

## Parked
<W-xx parked: title. Wake trigger: ...>

## Next action
<one line>
```

`DELTA.md`: pick an anchor date, in this order of preference: the last commit date of the legacy HTML; else the last commit authored by Stone; else skip and say so. List entries whose `created` (or `closed`) date is after the anchor, grouped: new, status changed, closed, and still waiting on the human since before the anchor. Finally run `git tag -f last-review` on your final pilot commit so the next session has an anchor for its own delta.

## 6. Phase 4: legacy HTML diff (skip if there is none)

Copy the legacy HTML to `nav/legacy/`. Inventory what it encodes, in its own vocabulary. Then diff in both directions: encoded there but not representable in the schema; representable in the schema but absent there; stale in the HTML relative to the repo, with dates.

## 7. Phase 5, optional but recommended: cold read

If Stone allows it, a fresh Claude Code session with no other context reads only `nav/STATE.md` and answers the six navigation questions plus "what would you do next and why". This session then scores those answers against the repo. Save both as `nav/COLD-READ.md`.

## 8. Report: nav/PILOT-REPORT.md

Fixed structure so reports are comparable across projects. Keep it under 300 lines plus the appendix. Label claims `recorded`, `inferred`, or `judgment`.

```markdown
# NAV pilot report: <project>, <date>

## 0. Project profile
- Repo, file count, commit count, age, active or dormant.
- Primary class (pick one, note secondary): build | research inquiry | learning program | content production | recurring routine | decision framework | mixed.
- Where the project tracks state today (docs, memory files, issues, chats, legacy HTML) and how stale each is.
- Pilot effort: wall time, sessions, approximate tokens.

## 1. Inventory summary (Phase 1)
- Row count; native kinds and their counts.

## 2. Mapping outcome (Phase 2)
- check.py JSON, verbatim.
- Coverage: rows total / mapped cleanly / LOSSY / NONE, with the LOSSY and NONE rows listed.
- Extension fields used: x_ name | count | why | should it be core? (yes/no, one line)
- Proposed types (type: other): name | count | definition | nearest core type and why it was not good enough
- Statuses wanted: name | type | count | why
- Ambiguities resolved by judgment: item | candidate types | rule applied
- Relations you could not express with parent / depends_on / supersedes / resolves / evidence / source.
- Granularity: what you treated as one entry; the hard cases, counted.
- Sampling: omitted per type, if the cap applied.

## 3. STATE.md self-test (Phase 3)
For each of the six questions: answerable from STATE.md alone? yes / partial / no, plus what was missing.
1. What is the goal and what counts as success?
2. What is the plan: phases, what is next?
3. What is the strategy: the load-bearing approach decisions and why?
4. What has been done?
5. What worked and what didn't?
6. What is waiting on the human right now, and what does each item unblock?
Also: contradictions found between the project's existing documents and the entries (staleness surfaced by the exercise).

## 4. Legacy HTML diff (Phase 4)
- HTML had, schema cannot represent: ...
- Schema represents, HTML lacked: ...
- Stale in HTML relative to repo: ...

## 5. Cold read (Phase 5, if run)
- Score per question; the wrong or missing answers and what in STATE.md caused them.

## 6. Checks
Score each pass / partial / fail with one line of evidence. A "recurring gap" is one that appears in three or more inventory rows.
- C1 Types: pass = no recurring gap; partial = one; fail = two or more.
- C2 Statuses: same rule on x_status_wanted.
- C3 Links: pass = every relation needed was expressible.
- C4 STATE.md from entries alone: pass = all six questions answerable; partial = four or five; fail = three or fewer.
- C5 Idea folding: were "things to try" fully represented as work proposed/parked? What was lost, if anything?
- C6 Owner queue: does check.py's pending_from_human list match what the human actually needs to act on? List false positives and false negatives.
- C7 Granularity: was the one-entry rule decidable? Hard cases as a fraction of rows.
- C8 Legacy loss: did the schema lose anything the legacy HTML had?

## 7. Recommended schema changes, ranked, at most five
Each with the evidence rows that motivate it.

## Appendix: entry index
id | type | status | owner | basis | title
```

Hand back to Stone: `nav/PILOT-REPORT.md` and the contents of `nav/legacy/`. The entries stay in the repo on the `nav-pilot` branch.

## Appendix A: nav/check.py

```python
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
```

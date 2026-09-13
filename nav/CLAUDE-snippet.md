## Navigation ledger (nav/)

This repo keeps a navigation ledger in `nav/entries/` (schema nav/v0.2, spec in the nav-kit checkout).
It is the cross-session memory of the project; the context window is not.

- **Start**: read `nav/STATE.md` and `nav/DELTA.md` (the SessionStart hook prints them). Treat them as the
  current position; if the code or docs disagree with them, the ledger is stale and the fix is an entry.
- **File as you go.** The moment a decision is made, a result lands, a question opens, a problem appears, or
  a task is planned or parked, write its entry then (one file, `nav/entries/<ID>-<slug>.md`). Do not batch
  entries for the end of the session; compaction and context loss happen without warning.
- **Granularity**: an entry is anything someone will later wait on or cite by id. Micro-steps stay in commits
  and logs, referenced from entries through `source`. If another entry cites it, it is an entry.
- **Never invent history**: `basis: recorded` only for what a file, commit, log, or the human said;
  otherwise `basis: inferred`. Unsure whether something was decided: file a question, not a decision.
- **Authority**: `actor` is who does it; `gate: human` when your work needs the human's go; decisions the
  human made carry `decided_by: human`; a result the human has not seen has no `reviewed` date.
- **Being wrong is an entry.** A result that turns out invalid gets `status: retracted`, superseded by the
  corrected result whose body says what was wrong and why. Outdated but valid at the time: `superseded`.
- **Foundational decisions** (why the project is built this way) carry `pinned: true`.
- **Links**: `depends_on` (all must close first), `resolves` (closing this closes those), `informs`
  (influence without gating), `supersedes`, `evidence`, `parent` (containment). Cross-repo: `repo:ID`.
  A link target must exist; create a one-line stub entry rather than drop the link.
- **Subagents never write entries.** They return candidate entries in their report; this session files them.
- **Close-out** (also run by the PreCompact and SessionEnd hooks): `python NAV_KIT/nav.py closeout .`
  which validates, regenerates STATE.md / DELTA.md / NAV.html / state.json, and commits `nav/`.
  Never hand-edit generated files. Anything navigational that lives only in out-of-repo memory
  (`~/.claude/projects/...`) must be mirrored into an entry before the session ends.
- **Telemetry** (during the steady-state test): before starting the close-out, note the session cost and
  time; after it, append one line to `nav/TELEMETRY.md`: date, session id, close-out tokens, close-out
  minutes, session total tokens, entries added, entries changed, links added, check errors.

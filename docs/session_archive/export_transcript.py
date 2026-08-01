"""Render a Claude Code session JSONL transcript to sanitized Markdown.

Strips base64 image payloads, collapses tqdm progress spam, truncates giant
tool payloads, and redacts local-machine identifiers before the result is
committed to a PUBLIC repository.

Usage:
    python export_transcript.py <input.jsonl> <output.md>
"""

from __future__ import annotations

import getpass
import json
import os
import re
import sys
from pathlib import Path

# The local account name is resolved at runtime, never written into this file
# -- otherwise the sanitizer would itself leak the identifier it exists to
# remove.
LOCAL_USER: str = (
    os.environ.get("USERNAME") or os.environ.get("USER") or getpass.getuser() or ""
)

# Home-directory paths appear in several escaping styles depending on context:
# plain shell output, JSON-escaped inside a tool_use payload (doubled
# separators), forward-slash form, and git-bash form. Anchoring on the
# "Users<sep>" prefix catches every style in one rule, and the capture group
# preserves whichever separator was used.
USER_PATH_RE = r"(?i)(users[\\/]{{1,2}}){}"

# Redact e-mail addresses generically. GitHub noreply addresses are exempt:
# they are already public in the commit metadata and carry no private info.
EMAIL_RE = (
    r"\b[A-Za-z0-9._%+\-]+@(?!users\.noreply\.github\.com)"
    r"[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)


def build_redactions(user: str) -> list[tuple[str, str]]:
    """Assemble the (pattern, replacement) list for a given local account name."""
    rules: list[tuple[str, str]] = []
    if user:
        rules.append((USER_PATH_RE.format(re.escape(user)), r"\1<user>"))
    rules.append((EMAIL_RE, "<redacted-email>"))
    return rules


REDACTIONS: list[tuple[str, str]] = build_redactions(LOCAL_USER)

# Secret patterns re-checked against the FINAL output as a self-audit.
SECRET_PATTERNS: dict[str, str] = {
    "GitHub classic PAT": r"ghp_[A-Za-z0-9]{16,}",
    "GitHub fine PAT": r"github_pat_[A-Za-z0-9_]{20,}",
    "GitHub oauth/app": r"gh[ousr]_[A-Za-z0-9]{16,}",
    "Anthropic key": r"sk-ant-[A-Za-z0-9\-_]{20,}",
    "OpenAI key": r"sk-[A-Za-z0-9]{32,}",
    "AWS access key": r"AKIA[0-9A-Z]{16}",
    "Slack token": r"xox[baprs]-[A-Za-z0-9\-]{10,}",
    "Private key block": r"BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY",
    "URL with creds": r"https://[^/\s:\"]+:[^@/\s\"]+@",
    # Populated at runtime from LOCAL_USER / EMAIL_RE; see build_audit_patterns.
}


def build_audit_patterns(user: str) -> dict[str, str]:
    """SECRET_PATTERNS plus the runtime-derived local-identifier checks."""
    pats = dict(SECRET_PATTERNS)
    if user:
        pats["Local username"] = USER_PATH_RE.format(re.escape(user))
    pats["Personal email"] = EMAIL_RE
    return pats

# tqdm / progress-bar lines: "  42%|####2     | 76/181 [00:06<00:08, 11.76it/s]"
PROGRESS_RE = re.compile(r"^\s*\S.*?\d+%\|[#\s|]*\|\s*\d+/\d+\s*\[")
# Long base64 runs (inline images, zarr blobs). 200+ chars of base64 alphabet.
BASE64_RE = re.compile(r"[A-Za-z0-9+/]{200,}={0,2}")

MAX_TOOL_INPUT = 2500
MAX_TOOL_RESULT = 4000
MAX_THINKING = 6000

# Meta record types carrying no conversational content.
SKIP_TYPES = {"ai-title", "last-prompt", "queue-operation", "mode", "custom-title"}


def redact(s: str) -> str:
    """Apply all REDACTIONS to a string."""
    for pat, repl in REDACTIONS:
        s = re.sub(pat, repl, s)
    return s


def strip_base64(s: str) -> str:
    """Replace long base64 runs (inline images) with a size placeholder."""
    return BASE64_RE.sub(
        lambda m: f"<<base64 payload stripped: {len(m.group(0))} chars>>", s
    )


def collapse_progress(s: str) -> str:
    """Collapse consecutive tqdm progress-bar lines into a single marker."""
    out: list[str] = []
    run = 0
    for line in s.splitlines():
        if PROGRESS_RE.match(line):
            run += 1
            continue
        if run:
            out.append(f"    [... {run} progress-bar lines collapsed ...]")
            run = 0
        out.append(line)
    if run:
        out.append(f"    [... {run} progress-bar lines collapsed ...]")
    return "\n".join(out)


def clean(s: str, limit: int) -> str:
    """Strip base64, collapse progress spam, truncate, redact."""
    s = strip_base64(s)
    s = collapse_progress(s)
    if len(s) > limit:
        s = s[:limit] + f"\n... [truncated, {len(s) - limit} more chars] ..."
    return redact(s)


def block_text(block: dict) -> str:
    """Extract renderable text from a tool_result content block."""
    c = block.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts = []
        for sub in c:
            if isinstance(sub, dict):
                if sub.get("type") == "text":
                    parts.append(sub.get("text", ""))
                elif sub.get("type") == "image":
                    parts.append("<<image result omitted>>")
            else:
                parts.append(str(sub))
        return "\n".join(parts)
    return "" if c is None else str(c)


def render(records: list[dict]) -> str:
    """Render parsed JSONL records to Markdown."""
    out: list[str] = []
    turn = 0

    for rec in records:
        rtype = rec.get("type")
        if rtype in SKIP_TYPES:
            continue

        if rtype == "system":
            lvl = rec.get("level", "info")
            slug = rec.get("slug", "")
            if rec.get("error"):
                out.append(f"> **system ({lvl})** {redact(str(slug))}\n")
            continue

        if rtype == "attachment":
            continue

        msg = rec.get("message") or {}
        content = msg.get("content")
        role = msg.get("role", rtype)

        # Plain-string content (rare)
        if isinstance(content, str):
            if role == "user":
                turn += 1
                out.append(f"\n---\n\n## Turn {turn} — User\n")
                out.append(clean(content, 8000) + "\n")
            else:
                out.append(clean(content, 8000) + "\n")
            continue

        if not isinstance(content, list):
            continue

        # A user record carrying ANY tool_result is a tool response, not a new
        # human turn. Such records often also carry a text block holding an
        # injected <system-reminder>; matching on "all blocks are tool_result"
        # would misclassify those as fresh human turns and inflate the count.
        is_tool_response = role == "user" and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content
        )

        if role == "user" and not is_tool_response:
            turn += 1
            out.append(f"\n---\n\n## Turn {turn} — User\n")

        # Render this record's blocks into a buffer first, so an assistant
        # record that produced nothing renderable does not leave an orphan
        # "### Assistant" header behind.
        chunk: list[str] = []
        out, real_out = chunk, out

        for block in content:
            if not isinstance(block, dict):
                out.append(clean(str(block), 4000) + "\n")
                continue
            btype = block.get("type")

            if btype == "text":
                txt = block.get("text", "").strip()
                if txt:
                    out.append(clean(txt, 12000) + "\n")

            elif btype == "thinking":
                th = (block.get("thinking") or "").strip()
                if th:
                    out.append("<details><summary>💭 reasoning</summary>\n")
                    out.append("\n```text")
                    out.append(clean(th, MAX_THINKING))
                    out.append("```\n")
                    out.append("</details>\n")

            elif btype == "tool_use":
                name = block.get("name", "?")
                inp = block.get("input", {})
                try:
                    rendered = json.dumps(inp, indent=2, ensure_ascii=False)
                except Exception:
                    rendered = str(inp)
                out.append(f"**🔧 {name}**\n")
                out.append("```json")
                out.append(clean(rendered, MAX_TOOL_INPUT))
                out.append("```\n")

            elif btype == "tool_result":
                body = block_text(block).strip()
                err = block.get("is_error")
                label = "⚠️ result (error)" if err else "result"
                if body:
                    out.append(f"<details><summary>{label}</summary>\n")
                    out.append("\n```text")
                    out.append(clean(body, MAX_TOOL_RESULT))
                    out.append("```\n")
                    out.append("</details>\n")

            elif btype == "image":
                out.append("*(image omitted from archive)*\n")

        # Restore the real output list and flush the buffer behind a role
        # header, only if the record actually rendered something.
        out, chunk = real_out, out
        if chunk:
            if role == "assistant":
                out.append("\n### Assistant\n")
            out.extend(chunk)

    return "\n".join(out)


def main() -> int:
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])

    records = []
    for line in src.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    body = render(records)

    header = (
        "# Session archive — recqual (SpikeInterface recording-quality pipeline)\n\n"
        "Full Claude Code session transcript covering sessions 1-3 of this project,\n"
        "exported for handoff. See [`docs/HANDOFF.md`](HANDOFF.md) for the distilled\n"
        "load-bearing facts; this file is the raw narrative record.\n\n"
        "**Sanitization applied before commit** (this repo is public):\n\n"
        "- Local Windows user paths redacted to `C:\\Users\\<user>`\n"
        "- Base64 payloads (inline figure images) stripped\n"
        "- tqdm progress-bar spam collapsed\n"
        "- Oversized tool payloads truncated\n"
        "- No credentials present: the GitHub token lives in Windows Credential\n"
        "  Manager, never in the repo or the transcript\n\n"
        "---\n"
    )

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(header + body, encoding="utf-8")

    # --- self-audit: re-scan the FINAL rendered output ---
    final = dst.read_text(encoding="utf-8")
    print(f"records parsed : {len(records)}")
    print(f"output written : {dst}")
    print(f"output size    : {len(final) / 1024:.1f} KB")
    print()
    print("=== SELF-AUDIT of rendered output ===")
    clean_run = True
    for name, pat in build_audit_patterns(LOCAL_USER).items():
        hits = re.findall(pat, final)
        if hits:
            clean_run = False
            print(f"  HIT  {name:20s} {len(hits)} match(es)")
        else:
            print(f"  ok   {name:20s} clean")
    print()
    print("AUDIT PASSED" if clean_run else "AUDIT FAILED - do not commit")
    return 0 if clean_run else 1


if __name__ == "__main__":
    raise SystemExit(main())

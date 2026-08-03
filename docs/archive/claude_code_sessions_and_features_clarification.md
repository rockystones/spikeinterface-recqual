# Claude code sessions and features clarification

*Exported 2026-08-03T03:58:42.504Z*  
*URL: https://claude.ai/chat/0342d113-4ec0-4fc6-a848-5fe7a0b0ae24*  
*Mode: active • messages: 2 of 3 in tree*

---

## 🧑 Human

*2026-05-23T21:45:19.319886Z*

Please clarify some key Claude code functions and concepts for me in this chat. 1. The sessions. Does the "sessions 1,2,x,..." necessarily mean clicking the "new session" button in Claude code? 2. What are the session types, local, remote control vs cloud? Which type allows me to access from the mobile app and give instructions and approvals? 3. Do I need to configure any skills? 4. Currently I am primarily using the Claude app Claude Code tab. Anything that this approach doesn't have but exist in the Claude code terminal?

---

## 🤖 Claude

*2026-05-24T02:49:49.440167Z*

 

> **[thinking]**
>
> The user is asking about Claude Code specifics. Per my instructions, I need to search the documentation for current information about Claude Code features.

Let me pull current documentation before answering, since Claude Code details change frequently.

```json
// tool_use: web_fetch
{
  "url": "https://docs.claude.com/en/docs/claude-code/overview",
  "html_extraction_method": "markdown",
  "text_content_token_limit": 3000
}
```

```json
// tool_result
[
  {
    "type": "text",
    "text": "{\"error_type\": \"PERMISSIONS_ERROR\", \"error_message\": \"This URL cannot be fetched because it was not provided by the user nor did it appear in any search/fetch results\"}",
    "uuid": "73363194-b5a9-46a4-8f7f-77a472297a76"
  }
]
```

```json
// tool_use: web_search
{
  "query": "Claude Code sessions remote background mobile app 2025"
}
```

```json
// tool_result
[
  {
    "type": "knowledge",
    "title": "Anthropic’s Remote Control Brings Claude Code to Mobile Devices",
    "url": "https://winbuzzer.com/2026/02/28/anthropic-remote-control-claude-code-mobile-access-xcxwbn/",
    "metadata": {
      "type": "webpage_metadata",
      "site_domain": "winbuzzer.com",
      "favicon_url": "https://www.google.com/s2/favicons?sz=64&domain=winbuzzer.com",
      "site_name": "WinBuzzer"
    },
    "is_missing": false
  },
  {
    "type": "knowledge",
    "title": "Remote Control extends Claude Code to the mobile app - Techzine Global",
    "url": "https://www.techzine.eu/news/devops/139101/remote-control-extends-claude-code-to-the-mobile-app/",
    "metadata": {
      "type": "webpage_metadata",
      "site_domain": "techzine.eu",
      "favicon_url": "https://www.google.com/s2/favicons?sz=64&domain=techzine.eu",
      "site_name": "Techzine Global"
    },
    "is_missing": false
  },
  {
    "type": "knowledge",
    "title": "Anthropic just released a mobile version of Claude Code called Remote Control | VentureBeat",
    "url": "https://venturebeat.com/orchestration/anthropic-just-released-a-mobile-version-of-claude-code-called-remote",
    "metadata": {
      "type": "webpage_metadata",
      "site_domain": "venturebeat.com",
      "favicon_url": "https://www.google.com/s2/favicons?sz=64&domain=venturebeat.com",
      "site_name": "VentureBeat"
    },
    "is_missing": false
  },
  {
    "type": "knowledge",
    "title": "Claude Code Remote Control: Manage AI Coding Sessions From Any Device | by Flora Nanda | Data Science Collective | Medium",
    "url": "https://medium.com/data-science-collective/claude-code-remote-control-manage-ai-coding-sessions-from-any-device-2480b0907d90",
    "metadata": {
      "type": "webpage_metadata",
      "site_domain": "medium.com",
      "favicon_url": "https://www.google.com/s2/favicons?sz=64&domain=medium.com",
      "site_name": "Medium"
    },
    "is_missing": false
  },
  {
    "type": "knowledge",
    "title": "Continue local sessions from any device with Remote Control - Claude Code Docs",
    "url": "https://code.claude.com/docs/en/remote-control",
    "metadata": {
      "type": "webpage_metadata",
      "site_domain": "claude.com",
      "favicon_url": "https://www.google.com/s2/favicons?sz=64&domain=claude.com",
      "site_name": "Claude"
    },
    "is_missing": false
  },
  {
    "type": "knowledge",
    "title": "Anthropic reveals Remote Control, a mobile version of Claude Code to keep you productive on the move",
    "url": "https://www.techradar.com/pro/anthropic-reveals-remote-control-a-mobile-version-of-claude-code-to-keep-you-productive-on-the-move",
    "metadata": {
      "type": "webpage_metadata",
      "site_domain": "techradar.com",
      "favicon_url": "https://www.google.com/s2/favicons?sz=64&domain=techradar.com",
      "site_name": "techradar"
    },
    "is_missing": false
  },
  {
    "type": "knowledge",
    "title": "Code with Claude 2025",
    "url": "https://www.anthropic.com/events/code-with-claude-2025",
    "metadata": {
      "type": "webpage_metadata",
      "site_domain": "anthropic.com",
      "favicon_url": "https://www.google.com/s2/favicons?sz=64&domain=anthropic.com",
      "site_name": "anthropic"
    },
    "is_missing": false
  }
]
```

```json
// tool_use: web_fetch
{
  "url": "https://code.claude.com/docs/en/remote-control",
  "html_extraction_method": "markdown",
  "text_content_token_limit": 3000
}
```

```json
// tool_result
[
  {
    "type": "knowledge",
    "title": "",
    "url": "https://code.claude.com/docs/en/remote-control",
    "metadata": {
      "type": "webpage_metadata",
      "site_domain": "claude.com",
      "favicon_url": "https://www.google.com/s2/favicons?sz=64&domain=claude.com",
      "site_name": "claude"
    },
    "is_missing": false
  }
]
```

```json
// tool_use: web_fetch
{
  "html_extraction_method": "markdown",
  "text_content_token_limit": 2000,
  "url": "https://code.claude.com/docs/en/claude-code-on-the-web"
}
```

```json
// tool_result
[
  {
    "type": "text",
    "text": "{\"error_type\": \"PERMISSIONS_ERROR\", \"error_message\": \"This URL cannot be fetched because it was not provided by the user nor did it appear in any search/fetch results\"}",
    "uuid": "ec3aa4dd-ac47-430c-bede-a4af169752e2"
  }
]
```

```json
// tool_use: web_search
{
  "query": "Claude Code \"on the web\" vs terminal differences skills MCP 2025 2026"
}
```

```json
// tool_result
[
  {
    "type": "knowledge",
    "title": "Codex vs. Claude Code: Which is best? [2026] | Zapier",
    "url": "https://zapier.com/blog/codex-vs-claude-code/",
    "metadata": {
      "type": "webpage_metadata",
      "site_domain": "zapier.com",
      "favicon_url": "https://www.google.com/s2/favicons?sz=64&domain=zapier.com",
      "site_name": "Zapier"
    },
    "is_missing": false
  },
  {
    "type": "knowledge",
    "title": "Claude Code Documentation: 2026 Working Guide - Petronella Cybersecurity News",
    "url": "https://petronellatech.com/blog/claude-code-cli-guide-ai-powered-development",
    "metadata": {
      "type": "webpage_metadata",
      "site_domain": "petronellatech.com",
      "favicon_url": "https://www.google.com/s2/favicons?sz=64&domain=petronellatech.com",
      "site_name": "Petronellatech"
    },
    "is_missing": false
  },
  {
    "type": "knowledge",
    "title": "Claude Code Skills vs MCP vs Plugins: Complete Guide 2026",
    "url": "https://www.morphllm.com/claude-code-skills-mcp-plugins",
    "metadata": {
      "type": "webpage_metadata",
      "site_domain": "morphllm.com",
      "favicon_url": "https://www.google.com/s2/favicons?sz=64&domain=morphllm.com",
      "site_name": "Morph"
    },
    "is_missing": false
  },
  {
    "type": "knowledge",
    "title": "Claude Code Skills vs Sub-Agents vs MCP: When to Use What",
    "url": "https://k21academy.com/claude/claude-code-skills-vs-sub-agents-vs-mcp/",
    "metadata": {
      "type": "webpage_metadata",
      "site_domain": "k21academy.com",
      "favicon_url": "https://www.google.com/s2/favicons?sz=64&domain=k21academy.com",
      "site_name": "K21 Academy"
    },
    "is_missing": false
  },
  {
    "type": "knowledge",
    "title": "Claude Code Skills vs MCP Servers — What to Use, How to Install, and the Best Ones in 2026 - DEV Community",
    "url": "https://dev.to/williamwangai/claude-code-skills-vs-mcp-servers-what-to-use-how-to-install-and-the-best-ones-in-2026-548k",
    "metadata": {
      "type": "webpage_metadata",
      "site_domain": "dev.to",
      "favicon_url": "https://www.google.com/s2/favicons?sz=64&domain=dev.to",
      "site_name": "DEV Community"
    },
    "is_missing": false
  },
  {
    "type": "knowledge",
    "title": "Claude Skills vs. MCP: A Technical Comparison for AI Workflows | IntuitionLabs",
    "url": "https://intuitionlabs.ai/articles/claude-skills-vs-mcp",
    "metadata": {
      "type": "webpage_metadata",
      "site_domain": "intuitionlabs.ai",
      "favicon_url": "https://www.google.com/s2/favicons?sz=64&domain=intuitionlabs.ai",
      "site_name": "IntuitionLabs"
    },
    "is_missing": false
  },
  {
    "type": "knowledge",
    "title": "Claude Code vs Codex CLI 2026: Which Terminal AI Coding Agent Wins? | NxCode",
    "url": "https://www.nxcode.io/resources/news/claude-code-vs-codex-cli-terminal-coding-comparison-2026",
    "metadata": {
      "type": "webpage_metadata",
      "site_domain": "nxcode.io",
      "favicon_url": "https://www.google.com/s2/favicons?sz=64&domain=nxcode.io",
      "site_name": "Nxcode"
    },
    "is_missing": false
  },
  {
    "type": "knowledge",
    "title": "2026 01 10 what are claude skills",
    "url": "https://glama.ai/blog/2026-01-10-what-are-claude-skills",
    "metadata": {
      "type": "webpage_metadata",
      "site_domain": "glama.ai",
      "favicon_url": "https://www.google.com/s2/favicons?sz=64&domain=glama.ai",
      "site_name": "glama"
    },
    "is_missing": false
  }
]
```

> **[thinking]**
>
> Good, I have enough information now. Let me address the four questions clearly.
> 
> 1. Sessions in Claude Code - do they require clicking "new session"?
> 2. Session types (local, remote control, cloud/web) and which allows mobile access
> 3. Skills - do they need configuring?
> 4. Claude Code app (mobile Claude Code tab) vs terminal differences
> 
> Let me answer these clearly and concisely.

Addressing each question directly.

**1. What "sessions" means in the roadmap vs Claude Code sessions**

The sessions numbered S1, S2, etc. in your roadmap are not Claude Code sessions in any technical sense. They are planning units representing a discrete chunk of work. A single roadmap session might correspond to one or several Claude Code invocations, or you might restart Claude Code mid-work and it's still the same roadmap session. "New session" in the roadmap means "new bounded work objective," not a button click. In Claude Code itself, a session is just a single continuous conversation with the agent; it ends when you exit the process or start a new one with `claude`.

**2. Session types and mobile access**

There are two distinct execution modes, and a bridge between them.

*Claude Code on the web* runs on Anthropic-managed cloud infrastructure. Sessions run on cloud infrastructure and are accessible from browser, mobile app, or desktop app, but have no local environment access. This is what you get when you go to claude.ai/code without running anything locally first.

*Local CLI session* runs on your machine. Full access to your filesystem, environment variables, MCP servers, CLAUDE.md, the repo. This is what `claude` in your terminal gives you.

*Remote Control* is the bridge. A local Claude Code session continues to run on your machine during Remote Control. The user's entire local environment remains available: file system, MCP servers, tools, and project configuration. Conversations automatically sync across all connected devices. To activate it: run `claude --remote-control` when starting a session, or type `/rc` inside an existing session. The terminal displays a QR code that, when scanned, opens a synchronized session in the Claude mobile app. In the Claude mobile app, tap Code in the navigation to reach the session list.

For your workflow, this means: start the session on your desktop in the repo directory, enable remote control, then pick it up from your phone for approvals and instructions while Claude keeps running locally. Remote Control is available on all plans, but on Team and Enterprise it is off by default until an admin enables the Remote Control toggle in Claude Code admin settings. Since you're using an Enterprise account context, check whether your admin has that toggled on.

**3. Skills**

Skills are Markdown files (.md) that you drop into `.claude/commands/` in your project. They teach Claude Code how to perform specific tasks, with no server, no API, no dependencies. They are not a prerequisite for basic Claude Code use. For your current work, CLAUDE.md serves a related function: it is the authoritative policy file Claude Code reads at the start of every session to know the project conventions, which is a more direct and already-active mechanism than setting up Skills. Skills become relevant when you want reusable procedural shortcuts (e.g., a "run the test suite and summarize failures" command). Nothing to configure now unless you want them.

The distinction from MCP: MCP connects Claude Code to external tools or services (GitHub, databases, etc.) via a running server process. Skills are lightweight Markdown instructions for recurring workflows within the repo. For `recqual` you will eventually want MCP if you want Claude Code to interact with GitHub issues or similar, but neither Skills nor MCP are needed to run the pipeline sessions.

**4. Claude Code app (the Code tab in the Claude mobile/desktop app) vs terminal**

The main differences:

The terminal CLI is the full-featured surface. It supports all slash commands, hooks, plan mode, `/rc`, custom MCP server configs, reading `.claude/` project files, and the complete `CLAUDE.md` flow. It is where you run sessions S1 onward.

The web surface and CLI surface share the same skills, MCP servers, and session history, so a session you start on your laptop can be resumed on your phone. So the gap has narrowed considerably.

The practical limitation of the app's Code tab for your purposes: without Remote Control active on a local session, the app surface runs on cloud infrastructure and does not see your local repo, your installed Python environment, your MATLAB scripts, or your data files. It cannot run `pytest`, call `spikeinterface`, or write to `docs/session_plans/`. For actual implementation sessions, the terminal (or VS Code extension connected to the local repo) is the right surface. The app Code tab is most useful as a remote window into an active local session via Remote Control, or for quick questions that don't require local execution.

---


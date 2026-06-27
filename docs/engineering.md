# Engineering Highlights

Every design decision in AIBA answers one question: *how do we make autonomous web agents safe, fast, and affordable for a single user on a single machine?*

---

## Model Choice: Gemini

AIBA runs exclusively on Google Gemini models.

| Factor | Why Gemini wins |
|---|---|
| **1M token context window** | Web pages are long. Snapshots are longer. A 1M window means the agent can hold dozens of pages, screenshots, and tool outputs in context without truncation. |
| **Native vision** | Gemini reads images natively — no separate vision model, no format conversion. `browser_take_screenshot` → `read_image` is a single hop. |
| **Cost** | Gemini Flash models are among the cheapest per-token LLMs with vision. Sub-agents make many calls — cost matters. |
| **Built-in search grounding** | `WEB_SEARCH_ENGINE=native` injects Google Search results directly into the model's context. No separate search API, no tool round-trips. |

---

## Pydantic AI v2: Deterministic by Design

AIBA is built on **pydantic-ai >= 2.0.0** — a framework designed for production agents, not prototypes.

```python
agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    capabilities=[...],
    retries=AgentRetries(tools=1, output=1),
)
```

| Property | What it means for AIBA |
|---|---|
| **Structured output** | Every tool return is typed. No parsing ambiguity. |
| **Deterministic retries** | `AgentRetries(tools=1, output=1)` — one retry on tool failure, one on output validation. Predictable, not infinite. |
| **Capability injection** | Guardrails, tool schemas, and system prompt reinjection are capabilities — composable, testable, togglable. |
| **UsageLimits** | Request caps, tool call caps, and token budgets enforced at framework level. Not advisory — hard stops. |
| **No hidden state** | Agent configuration is explicit in code. Model, tools, capabilities — all visible in `Agent(...)`. |

The framework itself enforces budget discipline. The agent can't overspend even if it wants to.

---

## Session History: Aggressive Truncation

Every REPL turn trims conversation history before the next call. This isn't a nice-to-have — it's a cost and latency multiplier.

### Two-stage pipeline

**Stage 1 — Strip tool noise** (`_filter_tool_parts`):

Tool-call payloads and tool-return outputs (YAML, JSON, HTML from Playwright snapshots) are stripped. Their content is already synthesized in the agent's text response. Keeping them would re-consume tokens for no informational gain.

**Stage 2 — Trim to 20 messages** (`trim_history`):

The filtered history is capped at `MAX_HISTORY_MESSAGES = 20`, aligned to a user-message boundary so Gemini's strict turn ordering isn't broken. The system prompt is always preserved as message 0.

```
Raw history → strip tool noise → keep last 20 user/model messages → send
```

Without this, a single browser-heavy investigation could carry 200+ messages of snapshot YAML into every subsequent turn, multiplying token costs with every interaction.


---

## Web Artifacts: Files First, Read Later

Web pages and snapshots are never passed inline. They're saved to disk first, then read with line caps.

### The problem

A `browser_navigate` to a job listing page can return 15,000 lines of accessibility YAML. Sending that directly to the model would consume 50K+ tokens in one shot — and most of it is nav bars, footers, and boilerplate.

### The solution

Every Playwright MCP tool that produces content saves to `.playwright-mcp/` and returns only a **file path**, not the content. The agent uses `read_and_filter_file` to pull what it needs:

```python
def read_and_filter_file(
    file_path: str,
    start_line: int | None = None,
    end_line: int | None = 300,  # ← default cap
    search_string: str | None = None,
    search_regex: str | None = None,
) -> str:
```

| Design choice | Effect |
|---|---|
| **Default 300-line cap** | Even without filters, the agent can't accidentally read 15K lines |
| **Regex + substring filters** | Agent extracts exactly what it needs — emails, names, prices |
| **Line-numbered output** | Agent can re-read specific ranges with `start_line`/`end_line` |

This is the single biggest token saver in AIBA. A 15,000-line snapshot costs nothing to save, and only the filtered subset costs tokens to read.

---

## Guardrails: Shields On by Default

Four capability wrappers from `pydantic-ai-shields` protect against cost overruns, dangerous tool use, prompt injection, and secret leakage. All active by default.

| Shield | Purpose |
|---|---|
| `CostTracking` | Hard USD budget cap — kills the run, not your wallet |
| `ToolGuard` | Human-in-the-loop approval for tools like `send_email` |
| `InputGuard` | Blocks prompt injection and homoglyph attacks |
| `SecretRedaction` | Redacts API keys/tokens from sub-agent output |

See [Guardrails](security/guardrails.md) for full details.

---

## Folder Sandboxing: No Escape from Allowed Paths

Agents can only access files within designated folders. There is no general filesystem access.

| Folder | Purpose | Tools that access it |
|---|---|---|
| `data/` | CSV files | `read_csv`, `append_csv` |
| `.playwright-mcp/` | Browser snapshots, screenshots | `read_and_filter_file`, `read_image` |
| `static/` | Email attachments | `send_email` |
| `sessions/` | Saved conversations | `/save`, `/load` |

Every tool validates that the requested file is within its allowed directory. Path traversal attacks (`../../etc/passwd`) are rejected:

```python
if "/" in filename or "\\" in filename or filename.startswith(".."):
    return f"ERROR: '{filename}' is not a valid filename."
```

The agent can't create files outside these folders either — `append_csv` only writes to pre-existing CSVs with matching headers. It never creates new files.

---

## Flat Files: No Database, No Migrations, No Overhead

AIBA stores everything as flat files on disk. No SQLite, no Postgres, no ORM.

| Data | Format | Location |
|---|---|---|
| Conversation history | JSON | `sessions/*.json` |
| Beat state | JSON | `data/beat_state.json` |
| Beat run logs | JSON + Markdown | `logs/beats/<name>/` |
| Task tracking (CSV) | CSV | `data/*.csv` |
| Browser cookies | JSON | `.playwright-mcp/cookies.json` |

### Why this works

AIBA is **single-user software**. There's no concurrent access, no replication, no sharding. A JSON file is:

- **Human-readable** — open `sessions/*.json` and see every message
- **Zero-dependency** — Python's `json` module, nothing to install
- **Instant to debug** — `cat data/beat_state.json` beats `SELECT * FROM ...`

Atomic writes use the `.tmp` → rename pattern to prevent corruption.

---

## Playwright MCP: One Browser, Many Agents

A single Chromium instance serves all sub-agents. There's no browser-per-worker model.

```
┌─────────────────────────────┐
│  Playwright MCP (npx)       │
│  ┌───────────────────────┐  │
│  │  Chromium (--isolated)│  │
│  │  Shared across all    │  │
│  │  sub-agent calls      │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
         │
    ┌────┴────┬────────┬────────┐
  Worker 1  Worker 2  Worker 3  ...
```

The `--isolated` flag gives each sub-agent its own browser context (separate cookies, localStorage, session) while sharing the single Chromium process. This means:

- **Memory**: 1 browser process, not N × 500MB
- **Startup**: The transport is deferred (`defer_loading=True`) — Playwright doesn't start until the first browser tool is actually called, saving resources when the agent only does web search. And keeps running till all the tasks are done
- **Cookie isolation**: `--storage-state` keeps each worker's context isolated at runtime

---

## AIBA-beats: Zero Resources When Idle

AIBA-beats has no built-in scheduler. No daemon, no polling loop, no background process.

The user configures their OS scheduler (cron, launchd, Task Scheduler) to run `python main.py beat run --all` at their desired interval. Between runs, AIBA-beats consumes exactly zero CPU, zero memory, and zero network.

| Approach | CPU idle | Memory idle | Complexity |
|---|---|---|---|
| Built-in scheduler | > 0 (polling loop) | > 0 (process alive) | High (watchdog, crash recovery) |
| OS cron | 0 | 0 | Low (one crontab line) |

State persists in `data/beat_state.json` — each run reads it, executes due beats, and writes it back. If a run crashes, the next cron tick picks up where it left off. No lost state, no stale locks.

---

## TUI: Built for DX

The terminal UI is deliberately minimal. No ncurses, no Textual framework, and built for developer experience.

| Choice | Rationale |
|---|---|
| **Raw ANSI codes** | Zero dependencies for color. Works in any terminal, over SSH, in tmux. |
| **Rich only for markdown** | Agent output (tables, code blocks, headings) uses Rich. Setup screens don't — keep them fast. |
| **Line-by-line input** | `input()` with teal `▸` prompt. No TUI framework to fight. |
| **4–5 step wizard** | Mode → Template → Effort → Sub-agents → Notes. Linear, predictable. |
| **Session resume** | First screen asks if you want to pick up where you left off. Cached in `sessions/`. |

The TUI is designed for the terminal power user — someone who lives in zsh, tmux, and vim. It's fast, keyboard-driven, and doesn't try to be a web app. See [TUI](ui/tui.md) for the full walkthrough.

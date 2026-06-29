# Changelog

All notable changes to AIBA will be documented in this file.

## [1.0.0] — 2026-06-29

### Initial Release — Autonomous Internet Browsing Agent

First public release of AIBA, a multi-agent research engine that turns your
terminal into a command center for autonomous internet exploration.

---

### Core Architecture

- **Main Orchestrator Agent** (`src/agents/main_agent.py`)
  - Swarm-mode orchestrator powered by Google Gemini (configurable model).
  - Built-in tools: `send_email` (SMTP with attachment support), `spawn_sub_agents`
    (parallel sub-agent fleet), `read_csv`, `append_csv`, `todo`.
  - Guardrails: Cost tracking, tool guard, input guard (optional via settings).
  - Phased orchestration: plan → dispatch → ingest/pivot → synthesize.
  - ReinjectSystemPrompt for long-running multi-turn sessions.

- **Sub-Agent** (`src/agents/sub_agent.py`)
  - Deep web reconnaissance agent with full browser automation capabilities.
  - Tools: `read_image` (visual intelligence via Gemini vision), `read_and_filter_file`
    (precision extraction with regex, line ranges, substring search).
  - DuckDuckGo web search integration (configurable backend).
  - Web Fetch for static page assessment.
  - Playwright MCP integration for interactive browser automation (deferred loading).
  - Secret Redaction and Input Guard (optional).
  - Three effort modes: Quick, Balanced, Max.

### Prompt & Effort System

- **Effort Modes** (`src/prompts/effort.py`)
  - `QUICK` — minimal tool calls, short responses, fast turnaround.
  - `BALANCED` — thorough cross-verification, 2–3 waves, pragmatic depth.
  - `MAX` — exhaustive deep-dive, 4–8 waves, maximum tokens and quality.
  - Per-mode temperature, token budgets, and instruction variants.

- **Prompt Templates** (`src/prompts/templates.py`)
  - General Browsing, Job Search, OSINT, and Custom template modes.
  - Template-specific orchestrator and sub-agent system prompts.
  - Model configuration helpers for Gemini model selection.

### Interactive REPL

- **REPL Loop** (`src/services/repl.py`)
  - Slash commands: `/agent`, `/swarm`, `/save`, `/load`, `/list`, `/clear`,
    `/history`, `/mode`, `/template`, `/help`, `/quit`.
  - Session persistence to `~/.aiba/sessions/`.
  - Rich-format output (Markdown rendering, live status).
  - Continuous conversation — refine, pivot, drill deeper after results.

- **Setup Screens** (`src/services/screens.py`)
  - 7 interactive screens: session picker, mode selector, template picker,
    effort config, sub-agent count, prompt input, confirm/launch.
  - Colored terminal UI with keyboard navigation.

### Scheduled Beats

- **Beat Engine** (`src/services/beats.py`)
  - YAML-based beat configuration (`beats.yaml`).
  - Cron-scheduled autonomous runs — AIBA wakes up, does the work, emails results.
  - Per-beat: template, mode, effort, sub-agent count, headless toggle.
  - Beat state tracking (last run, enabled/disabled).
  - Automatic summary email after each beat run.

- **Beat CLI** (`src/services/beat_cli.py`)
  - `list`, `run`, `status` commands for managing beats from the terminal.

### Session Management

- **Session System** (`src/services/session.py`)
  - Save/load/list complete conversation histories.
  - Settings metadata stored alongside messages.
  - Intelligent history trimming (preserves system prompt + recent context).
  - Tool-part filtering for clean replay.

### Common Tools

- **Shared Tool Library** (`src/tools/common_tools.py`)
  - `read_csv` — parse structured data from CSV files.
  - `append_csv` — append rows to CSV files.
  - `todo` — task tracking (add/update/complete/reorder) for orchestrator.

### Configuration

- **Settings** (`src/utils/settings.py`)
  - Environment-variable-driven via `pydantic-settings`.
  - Gemini API key, model selection (main/sub), web search engine, timeouts,
    cost budgets, guardrails, Playwright headless mode, Logfire observability.
  - Range validation on all numeric fields.

### Rendering & Output

- **Rich Rendering** (`src/services/rendering.py`)
  - Markdown-to-Rich conversion for terminal display.
  - Tool-call result formatting.
  - Structured output tables.

### Test Suite — 257 tests, 100% coverage

- **Agent Tests** — `test_main_agent.py` (18 tests), `test_sub_agent.py` (41 tests)
  - pydantic-ai `TestModel` mocking for all LLM interactions.
  - `capture_run_messages()` for message introspection.
  - Tool-level unit tests (send_email, read_image, read_and_filter_file).
  - Orchestration tests (spawn_sub_agents: success, timeout, exception).

- **Service Tests** — `test_repl.py` (17), `test_screens.py` (50), `test_session.py` (24),
  `test_beats.py` (42), `test_beat_cli.py` (6), `test_rendering.py` (12)
  - Full slash-command coverage for REPL.
  - All 7 setup screens with input-sequence simulation.
  - Session save/load/list/trim with mixed message types.
  - Beat scheduling, state management, and CLI commands.

- **Tool/Prompt Tests** — `test_common_tools.py` (27), `test_effort_configs.py` (8),
  `test_prompt_models.py` (6), `test_settings.py` (10)

- **QA Tooling** — ruff (zero lint errors), pyright (strict mode, zero errors),
  pytest-cov (100% line coverage across 962 statements).

### Documentation & Community

- Custom logo and branding.
- MkDocs Material documentation site with custom subdomain.
- AIBA Public License (APL).
- CI/CD via GitHub Actions for docs and main branch merge deployment.

---

### Technical Stack

| Category | Technology |
|---|---|
| LLM Framework | pydantic-ai ≥ 2.0 |
| Model Provider | Google Gemini (via pydantic-ai Google provider) |
| Browser Automation | Playwright MCP (fastmcp transports) |
| Settings | pydantic-settings |
| Scheduling | croniter |
| Terminal UI | Rich |
| Testing | pytest, pytest-cov, pytest-asyncio |
| Linting | ruff, pyright (strict) |
| Documentation | MkDocs Material |
| Package Manager | uv |
| Runtime | Python ≥ 3.13 |

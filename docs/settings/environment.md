# Environment & Settings

All configuration lives in a single `.env` file at the project root. AIBA uses **pydantic-settings** to load it — every variable has a type, a default, and optional validation constraints.

No JSON configs. No YAML. No CLI flags for settings. Just `.env`.

---

### Covers: [Quick Reference](#quick-reference), [LLM](#llm), [Orchestration](#orchestration), [Browser](#browser), [Web Search](#web-search), [Email](#email), [User Profile](#user-profile), and [How Settings Load](#how-settings-load)

---

## Quick Reference

| Variable | Type | Default | Required | Category |
|---|---|---|---|---|
| `GEMINI_API_KEY` | `str` | `""` | **Yes** | LLM |
| `GEMINI_MAIN_MODEL` | `str` | `gemini-3.5-flash` | No | LLM |
| `GEMINI_SUB_MODEL` | `str` | `gemini-3.1-flash-lite` | No | LLM |
| `LOGFIRE_ENABLED` | `bool` | `false` | No | Observability |
| `LOGFIRE_TOKEN` | `str` | `""` | No | Observability |
| `MAX_CONCURRENT_SUB_AGENTS` | `int` | `5` | No | Orchestration |
| `REQUEST_TIMEOUT_SECONDS` | `int` | `60` | No | Orchestration |
| `PLAYWRIGHT_HEADLESS` | `bool` | `true` | No | Browser |
| `WEB_SEARCH_ENGINE` | `str` | `duckduckgo` | No | Web Search |
| `SMTP_HOST` | `str` | `smtp.gmail.com` | No | Email |
| `SMTP_PORT` | `int` | `587` | No | Email |
| `SMTP_USERNAME` | `str` | `""` | No | Email |
| `SMTP_PASSWORD` | `str` | `""` | No | Email |
| `SENDER_EMAIL` | `str` | `""` | No | Email |
| `USER_PROFILE` | `str` | `""` | No | User Profile |
| `GUARDRAILS_ENABLED` | `bool` | `true` | No | Guardrails |
| `COST_BUDGET_USD` | `float` | `1.0` | No | Guardrails |
| `REQUIRE_APPROVAL_FOR` | `list[str]` | `[]` | No | Guardrails |

---

## LLM

The only required variable. Everything else can stay at defaults.

```
GEMINI_API_KEY=AIza...
```

Get a key from [Google AI Studio](https://aistudio.google.com/). The free tier includes generous quotas.

```
GEMINI_MAIN_MODEL=gemini-3.5-flash
GEMINI_SUB_MODEL=gemini-3.1-flash-lite
```

The main model powers the orchestrator. The sub-model powers every worker agent. They serve different roles and have different demands:

| Model | Used by | Needs |
|---|---|---|
| Main model | Orchestrator (planning, synthesis, tool orchestration) | Reasoning depth, large context |
| Sub-model | Workers (web browsing, data extraction) | Speed, cost efficiency |

You can use the same model for both — set them to identical values. But the split optimises cost since sub-agents make many more API calls and benefit from a lighter model.

---

## Orchestration

```
MAX_CONCURRENT_SUB_AGENTS=5
REQUEST_TIMEOUT_SECONDS=60
```

`MAX_CONCURRENT_SUB_AGENTS` caps how many sub-agents run in parallel during swarm mode. Range `1–50`. Higher values increase throughput but multiply API costs linearly.

`REQUEST_TIMEOUT_SECONDS` is the per-request wall clock limit. If a sub-agent hangs on a slow page or an API call stalls, it's killed after this timeout and an error is returned to the orchestrator. Minimum `10`.

---

## Observability

```
LOGFIRE_ENABLED=false
LOGFIRE_TOKEN=
```

When enabled, AIBA instruments itself with [Logfire](https://logfire.pydantic.dev/) — Pydantic's observability platform. This provides:

- Structured logging of every agent invocation
- Tool call tracing with timing
- Cost and token usage dashboards
- System metrics (CPU, memory)

Set `LOGFIRE_ENABLED=true` and provide a `LOGFIRE_TOKEN` to activate. Tokens are free for low-volume usage.

---

## Browser

```
PLAYWRIGHT_HEADLESS=true
```

Controls whether Playwright's Chromium runs in headless mode. Set to `false` to watch the browser work — useful for debugging anti-bot walls or visual verification. Headless is faster and required for headless servers.

---

## Web Search

```
WEB_SEARCH_ENGINE=duckduckgo
```

Two backends are available:

| Value | Backend | Cost | Notes |
|---|---|---|---|
| `duckduckgo` | DuckDuckGo Instant Answer API | Free, no quota | Default. Good for most research. |
| `native` | Gemini's built-in Google Search | Free up to 5,000 prompts/month, then $14/1K queries | Higher quality results, especially for recent/real-time data. |

The `native` backend uses Gemini's Grounding feature — search results are injected directly into the model's context rather than fetched as a separate tool call. This makes it faster and more accurate, but it counts against your Gemini usage.

---

## Email

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@email.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SENDER_EMAIL=your@email.com
```

SMTP configuration for the `send_email` tool on the main agent. Designed for Gmail by default:

- `SMTP_PORT=587` uses STARTTLS
- `SMTP_PASSWORD` should be a [Gmail App Password](https://support.google.com/accounts/answer/185833), not your account password

All five fields must be set for `send_email` to work. If unset, calling `send_email` will return an SMTP error.

---

## User Profile

```
USER_PROFILE=I am a full-stack engineer with 5 years of Python and React experience...
```

Freeform text describing your skills, experience, and background. Templates like `job_search` inject this into the system prompt so results are tailored to you. Not used by the agent directly — it's a template variable.

If left empty, AIBA warns at startup that templates may lack context.

---

## Guardrails

```
GUARDRAILS_ENABLED=true
COST_BUDGET_USD=1.0
REQUIRE_APPROVAL_FOR=[]
```

| Variable | Purpose |
|---|---|
| `GUARDRAILS_ENABLED` | Master switch — `false` strips all guardrails |
| `COST_BUDGET_USD` | Hard USD cap per agent run |
| `REQUIRE_APPROVAL_FOR` | Comma-separated tool names needing human approval |

Full details in [Guardrails](../security/guardrails.md).

---

## How Settings Load

At import time, `AibaSettings()` reads `.env` from the project root:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class AibaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    max_concurrent_sub_agents: int = Field(default=5, ge=1, le=50, ...)
    ...
```

Key behaviors:

- **Case-insensitive** — `gemini_api_key` and `GEMINI_API_KEY` are equivalent
- **Validated at load** — invalid values (e.g. `MAX_CONCURRENT_SUB_AGENTS=0`) raise a `ValidationError` before the REPL starts
- **Single instance** — `AibaSettings()` is called once per module, and every module that imports it gets the same instance
- **No hot-reload** — changing `.env` while the REPL is running has no effect. Restart to pick up new values

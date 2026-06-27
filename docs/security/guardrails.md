# Guardrails

AIBA has two independent layers of run-time protection:

1. **pydantic-ai-shields** — four capability wrappers that intercept agent calls for safety checks. Toggled by `GUARDRAILS_ENABLED` in `.env`.
2. **UsageLimits** — pydantic-ai's native resource enforcement. Request caps, tool-call caps, and token budgets. Always active, set per effort mode.

---

### Covers: [Overview](#overview), [CostTracking](#costtracking), [ToolGuard](#toolguard), [InputGuard](#inputguard), [SecretRedaction](#secretredaction), [UsageLimits](#usagelimits), and [Configuration](#configuration)

---

## Overview

Guardrails are pydantic-ai **capabilities** — wrappers that intercept agent invocations at the framework level. They are injected once at agent creation time and apply to every subsequent call.

There is one master switch: `GUARDRAILS_ENABLED` in `.env`. When `false`, no guardrails are loaded — the agents run bare.

### Who gets what

| Guardrail | Main Agent | Sub-Agent | Purpose |
|---|---|---|---|
| `CostTracking` | Yes | No | Kill the orchestrator when the USD budget is exceeded |
| `ToolGuard` | Yes | No | Require human approval before executing dangerous tools |
| `InputGuard` | Yes | Yes | Inspect and sanitize user input before it reaches the model |
| `SecretRedaction` | No | Yes | Redact secrets from sub-agent output |

The main agent (orchestrator) owns cost and approval concerns — it's the one running the overall operation. The sub-agent (web worker) gets `SecretRedaction` because it browses external pages that may accidentally contain API keys or tokens in their source.

---

## CostTracking

Enforces a hard USD budget per agent run. Configured via `COST_BUDGET_USD` (default `1.0`).

When the agent's accumulated API cost exceeds the budget, pydantic-ai raises a `UsageLimitExceeded` exception. AIBA catches this and displays a resource-limit warning in the terminal.

```python
CostTracking(budget_usd=_settings.cost_budget_usd)
```

The cost counter is per-run, not cumulative across sessions. Each new REPL turn or beat execution starts with a fresh budget. AIBA provides no rollover or monthly tracking — that belongs to your provider's billing dashboard.

---

## ToolGuard

Requires human approval before executing specific tools. Configured via `REQUIRE_APPROVAL_FOR` — a comma-separated list of tool names in `.env`.

```python
ToolGuard(require_approval=_settings.require_approval_for)
```

Example configuration:

```
REQUIRE_APPROVAL_FOR=["send_email"]
```

When a guarded tool is invoked, the agent pauses and prompts in the terminal:

```
  ⚠  Agent wants to call 'send_email'
  Recipient: user@example.com
  Subject: AIBA Research Results

  Approve? [y/N]:
```

Declining the approval returns a rejection to the agent, which can then adapt its plan.

Any tool can be guarded — `spawn_sub_agents`, `append_csv`, or custom tools. The list is empty by default (`[]`), meaning no tools require approval.

---

## InputGuard

Inspects user input before it reaches the language model. Both agents run it.

```python
InputGuard()
```

InputGuard screens for:

- Prompt injection attempts (e.g. `ignore previous instructions`)
- Excessively long inputs that could blow context windows
- Unicode homoglyph attacks and obfuscation patterns

These checks happen client-side — the input never leaves your machine if it fails inspection.

---

## SecretRedaction

Redacts secrets from sub-agent output before it's returned to the orchestrator. The sub-agent browses external web pages, and a page's source may contain hardcoded API keys, tokens, or credentials that the model inadvertently echoes.

```python
SecretRedaction()
```

`SecretRedaction` scans output for patterns matching common secret formats:

| Pattern | Example |
|---|---|
| GitHub tokens | `ghp_xxxxxxxxxxxxxxxxxxxx` |
| AWS keys | `AKIAIOSFODNN7EXAMPLE` |
| Generic API keys | `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| JWT tokens | `eyJhbGciOiJIUzI1NiJ9...` |

It does **not** prevent the sub-agent from seeing secrets — it only redacts them from the text that flows back to the orchestrator and into conversation history.

---

## UsageLimits

Separate from the pydantic-ai-shields capabilities, every effort mode enforces hard resource caps through pydantic-ai's native `UsageLimits`. These are not opt-in — they are always active and determined by the effort mode selected at startup.

### Per-mode limits

| Mode | `request_limit` | `tool_calls_limit` | `total_tokens_limit` |
|---|---|---|---|
| **quick** | 15 | 20 | 100,000 |
| **balanced** | 25 | 40 | 300,000 |
| **max** | 50 | 100 | 500,000 |

All three caps apply to every agent invocation — the main orchestrator, each sub-agent spawned in a swarm, and the single sub-agent in agent mode.

When any limit is hit, pydantic-ai raises `UsageLimitExceeded` — the same exception `CostTracking` uses. AIBA catches it uniformly and displays a resource-limit warning.

### Where they're set

UsageLimits are hardcoded in `src/prompts/effort.py` and flow into every agent call:

```python
EFFORT_CONFIGS: dict[EffortMode, EffortConfig] = {
    EffortMode.QUICK: {
        "usage_limits": UsageLimits(
            request_limit=15,
            tool_calls_limit=20,
            total_tokens_limit=100_000,
        ),
        ...
    },
    ...
}
```

The config is unpacked at call time in the REPL, `run_agent()`, `run_sub_agent()`, and `spawn_sub_agents()`:

```python
result = agent_fn(
    user_input,
    usage_limits=config["usage_limits"],
    ...
)
```

There is no `.env` variable for UsageLimits — they are deliberately tied to effort mode. If you need tighter or looser caps, change the effort mode.

---

## Configuration

All guardrail settings live in `.env`:

```
GUARDRAILS_ENABLED=true
COST_BUDGET_USD=1.0
REQUIRE_APPROVAL_FOR=[]
```

| Variable | Type | Default | Effect |
|---|---|---|---|
| `GUARDRAILS_ENABLED` | `bool` | `true` | Master switch — `false` strips all guardrails from both agents |
| `COST_BUDGET_USD` | `float` | `1.0` | Maximum USD per run for `CostTracking` |
| `REQUIRE_APPROVAL_FOR` | `list[str]` | `[]` | Tool names that require human approval via `ToolGuard` |

Guardrails are injected at agent creation time in `main_agent.py` and `sub_agent.py`. They cannot be toggled mid-session without restarting the REPL.

### Wiring

**Main agent** (`src/agents/main_agent.py`):

```python
capabilities=[
    ReinjectSystemPrompt(),
    IncludeToolReturnSchemas(),
    *(
        [
            CostTracking(budget_usd=_settings.cost_budget_usd),
            ToolGuard(require_approval=_settings.require_approval_for),
            InputGuard(),
        ]
        if _settings.guardrails_enabled
        else []
    ),
],
```

**Sub-agent** (`src/agents/sub_agent.py`):

```python
capabilities=[
    _web_search_cap,
    WebFetch(local=True),
    playwright_cap,
    ReinjectSystemPrompt(),
    IncludeToolReturnSchemas(tools=lambda ctx, td: bool(td.return_schema)),
    *([SecretRedaction(), InputGuard()] if _settings.guardrails_enabled else []),
],
```
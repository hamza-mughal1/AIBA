# AIBA-beats

AIBA-beats is an autonomous scheduling engine for AIBA. You define a beat (a task), schedule it at a repeating interval, and it runs at each interval — autonomously.

It logs each run, summarizes the results, and notifies you through email.

---

### Three subcommands control beats: [list](cli.md#list), [run](cli.md#run), and [schedule](cli.md#schedule)

---

## How Beats Work

```
beats.yaml                  cron / launchd / Task Scheduler
    │                              │
    │  defines schedule,           │  polls every 5 minutes:
    │  template, effort,           │  uv run python main.py beat run --all
    │  mode, etc.                  │
    │                              ▼
    │                       AIBA checks each beat:
    │                       • Is it due? (cron check)
    │                       • If yes → fire agent
    │                       • Log result to logs/
    │                       • Send email (if configured)
    │                       • Update state
    ▼
  Done. Waits for next poll.
```

Beats never run themselves. An external scheduler — cron, launchd, or Task Scheduler — polls `beat run --all` on a cadence (typically every 5 minutes). AIBA checks each beat's cron expression against its last run time, fires the ones that are due, logs the result, and optionally sends an email summary.

---

## Beats vs. Manual Runs

| Dimension | Manual Run | Beat |
|---|---|---|
| **Trigger** | You type at a terminal | Cron expression triggers automatically |
| **Interaction** | Full REPL — back-and-forth | One-shot — fires, reports, exits |
| **Browser** | Headless or headed (your choice) | Always headless |
| **CSV access** | All CSV files available | Restricted to `allowed_csvs` per beat |
| **Email** | Main agent has the email tool | Configurable per beat — summary on completion |
| **Logs** | Session files or none | Structured JSON logs per run + rolling summary |

---

## Anatomy of a Beat

Each beat lives under `beats:` in `beats.yaml`:

```yaml
beats:
  daily_hackernews_ai_summary:
    name: "Daily HackerNews AI Summary"
    schedule: "*/5 * * * *"
    template: default
    effort: quick
    mode: agent
    sub_agents: 1
    prompt_extra: "Check the top HackerNews posts and summarize..."
    budget_override_usd: 0.25
    headless: true
    notify_email: "you@example.com"
    allowed_csvs:
      - hn_posts.csv
```

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Unique identifier — used in logs and state tracking |
| `schedule` | Yes | Cron expression — `0 9 * * *`, `*/30 * * * *`, etc. |
| `template` | Yes | Template name — `default`, `job_search`, `osint`, or a custom one |
| `effort` | No | `quick`, `balanced`, or `max`. Defaults to `balanced` |
| `mode` | No | `agent` or `swarm`. Defaults to `agent` |
| `sub_agents` | No | Max parallel sub-agents (swarm mode). Range 1–50. Defaults to 5 |
| `prompt_extra` | No | Additional instructions appended to the template-generated prompt |
| `budget_override_usd` | No | Override the global cost budget for this specific beat |
| `headless` | No | Beats always run headless. Defaults to `true` |
| `notify_email` | No | Email address for run summary (SMTP must be configured) |
| `allowed_csvs` | No | CSV files the agent may read and append to. Must pre-exist with header rows |

---

## Next: Beat CLI

The `beat` subcommand is how you list, run, and configure beats from the terminal. See [CLI](cli.md).

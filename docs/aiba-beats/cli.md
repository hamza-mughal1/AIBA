# Beat CLI

The CLI entry point for beats is `python main.py beat <subcommand>`. No REPL, no setup screens — runs and exits.

---

### Four subcommands: [list](#list), [run](#run), [schedule](#schedule), and [help](#help)

---

## `list`

Show every beat defined in `beats.yaml` with its configuration.

```bash
uv run python main.py beat list
```

```
──────────────────────────────────────────────────────────────────────────────
  Beats
──────────────────────────────────────────────────────────────────────────────

  daily_hackernews_ai_summary
  Schedule:   */5 * * * *
  Mode:       agent
  Template:   default
  Effort:     quick
  Sub-agents: 1
  Extra:      Check the top HackerNews posts and summarize...
  CSVs:       hn_posts.csv
  Notify:     you@example.com
```

If no beats are configured, it tells you to edit `beats.yaml`.

---

## `run`

Fire beats. Two modes: target a single beat by name, or run all due beats.

### Single beat

```bash
uv run python main.py beat run <name>
```

Runs the named beat immediately — schedule ignored. Result renders inline. Use this to test a beat before wiring it to cron.

```
✓ daily_hackernews_ai_summary: success
```

### All due beats

```bash
uv run python main.py beat run --all
```

Checks every beat's cron schedule against its last run. Fires the ones that are due, skips the rest. This is the command your OS scheduler calls.

```
✓ daily_hackernews_ai_summary: Top HackerNews AI posts from the last 24 hours...
○ weekly_competitor_check: Not due yet. Last run: 2026-06-27T09:00:00
```

Status indicators:

| Icon | Meaning |
|---|---|
| `✓` | Success — agent completed and produced output |
| `✗` | Error — something failed (errors printed below) |
| `○` | Skipped — not due yet |

---

## `schedule`

Prints OS-specific instructions for wiring beats to your system scheduler.

```bash
uv run python main.py beat schedule
```

The output varies by platform — cron line for Linux, crontab + launchd options for macOS, Task Scheduler steps for Windows. Copy the line, paste it into your scheduler, and beats go live.

---

## `help`

Prints a list of all available `beat` subcommands and their usage.

```bash
uv run python main.py beat --help
```

```
usage: main.py beat [-h] {list,run,schedule} ...

positional arguments:
  {list,run,schedule}
    list        Show all configured beats
    run         Run a beat by name, or --all for all due
    schedule    Print OS scheduler setup instructions

optional arguments:
  -h, --help    Show this help message
```

---

## Next: Scheduling

The `schedule` subcommand gives you the exact line to paste. To understand the scheduling model and how to verify beats are running — see [Scheduling](scheduling.md).

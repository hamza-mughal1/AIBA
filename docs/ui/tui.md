# TUI

AIBA runs entirely in the terminal. There is no web UI, no desktop window, no browser dashboard. Everything — the setup wizard, the REPL, the agent output — renders through a thin rendering layer built on ANSI escape codes and Rich.

---

### Covers: [The Rendering Layer](#the-rendering-layer), [Setup Screens](#setup-screens), [The REPL](#the-repl), and [The Launch Flow](#the-launch-flow)

---

## The Rendering Layer

All terminal output flows through `src/services/rendering.py`. It has two jobs: color and markdown.

### ANSI color palette

A dictionary called `C` holds the color tokens. Every screen, the REPL, and `main.py` reference `C` for consistent styling:

| Token | ANSI code | Usage |
|---|---|---|
| `bold` | `\033[1m` | Headings, emphasised labels |
| `dim` | `\033[2m` | Secondary text, descriptions |
| `purple` | `\033[38;5;99m` | The launch banner ("∞ AIBA") |
| `teal` | `\033[38;5;44m` | Interactive prompts (`▸`), selected values |
| `green` | `\033[38;5;42m` | Success badges, the logo |
| `yellow` | `\033[38;5;221m` | Warnings, usage-limit alerts |
| `red` | `\033[38;5;203m` | Errors, invalid input markers (`✗`) |
| `reset` | `\033[0m` | Reset to terminal default |

The palette uses 256-color codes rather than 16-color ANSI names (e.g. `\033[31m` for red). This keeps the look consistent across different terminal themes — OS color schemes don't override AIBA's intended appearance.

### Rich markdown rendering

Agent output is markdown. AIBA uses [Rich](https://rich.readthedocs.io/) to render it to the terminal:

```python
from rich.console import Console
from rich.markdown import Markdown

_console = Console(highlight=False)

def render_markdown(text: str) -> None:
    md = Markdown(text, code_theme="monokai")
    _console.print(md)
```

What this gets you:

| Feature | Example |
|---|---|
| **Headings** | H1–H6 rendered with weight and color |
| **Tables** | Pipe tables drawn with box-drawing characters |
| **Code blocks** | Syntax-highlighted with the Monokai theme |
| **Inline code** | Backtick-wrapped text rendered in a contrasting background |
| **Lists** | Ordered and unordered, with proper indentation |
| **Blockquotes** | Indented with a vertical bar |

Rich is only used for agent output. The setup screens and REPL prompts use raw ANSI codes — no Rich overhead.

### Utility helpers

Two small functions complement the palette:

```python
def hr(char: str = "─", color: str = "dim") -> str:
    """Horizontal rule spanning the terminal width."""

def badge(label: str, value: str) -> str:
    """Dim label followed by teal value, e.g. 'Mode: AGENT'."""
```

The horizontal rule adapts to the terminal width via `shutil.get_terminal_size()`. It is used extensively in the setup screens and REPL to separate sections.

---

## Setup Screens

When you run `python main.py` (without `beat`), AIBA walks you through a 4–5 step wizard. Each step is a function in `src/services/screens.py`.

### Step 1 — Mode

```
∞  A I B A   Autonomous Internet Browsing Agent
────────────────────────────────────────────────

  Step 1 — Select Mode

  [1]  Agent   Single autonomous agent, full internet access
               Best for focused tasks, single-domain research.

  [2]  Swarm   Orchestrated fleet of parallel sub-agents
               Best for large-scale research, multi-hop mining.

  ▸  Enter 1 or 2:
```

Choices map directly to what gets launched:

| Choice | What runs | How |
|---|---|---|
| `1` — Agent | Sub-agent directly | `run_sub_agent(prompt)` |
| `2` — Swarm | Main orchestrator + parallel sub-agents | `run_agent(prompt)` |

### Step 2 — Template

Lists every registered template with its description. The template's system prompt shapes the agent's behavior for the entire session.

Templates are configured in `src/prompts/templates/` and registered at startup. See [Templates](../core-concepts/templates.md) for the full catalog.

### Step 3 — Effort

```
  Step 3 — Effort Level

  [1]  quick     Fast & cheap — minimal tool calls, short responses.
  [2]  balanced  Thorough & pragmatic — cross-check 2–3 sources.
  [3]  max       Exhaustive deep-dive — maximum tools, maximum tokens.
```

Effort controls temperature, token budgets, and instruction depth. `max` mode also enables Gemini thinking. See [Effort](../core-concepts/effort.md).

### Step 4 — Sub-Agent Pool (Swarm only)

Appears only in Swarm mode. Sets `max_concurrent_sub_agents` (range 1–50). The default comes from `.env`.

### Step 5 — Extra Notes

Freeform text appended to the template-generated prompt. Press Enter on an empty line (or Ctrl+D) to skip. Useful for adding URLs, specific constraints, or follow-up context.

### Launch Summary

After all steps, a summary block displays before execution:

```
═══════════════════════════════════════════════
  Launch Summary
═══════════════════════════════════════════════
  Mode:        SWARM
  Sub-agents:  8
  Prompt:      Find all software engineering jobs posted in the last 24 hours…
═══════════════════════════════════════════════
```

---

## The REPL

After the first result renders, the session drops into an interactive REPL loop. The REPL is already documented in detail at [REPL](../usage/repl.md).

In the context of the TUI:

- The REPL uses the same `C` palette and `hr()` helper as the setup screens
- User input is read via `input()` with a teal `▸` prompt
- Each agent response passes through `render_markdown()` before display
- Commands (`/exit`, `/save`, `/clear`, `/history`, `/help`) are parsed before agent invocation

---

## The Launch Flow

Putting it all together, here is the full path from `python main.py` to a running REPL:

```
python main.py
    │
    ├── /beat argument? ──> beat_cli() ──> exit (no TUI)
    │
    └── No argument ──> screens.session()
            │
            ├── Resume saved session? ──Y──> load history ──> REPL
            │
            └── N ──> screens.mode()
                   ──> screens.template()
                   ──> screens.effort()
                   ──> screens.sub_agents()  (swarm only)
                   ──> screens.prompt()
                   ──> screens.confirm()
                   ──> run_sub_agent() or run_agent()
                   ──> first result renders
                   ──> repl.run() > interactive loop
```

The beat path (`python main.py beat ...`) bypasses the TUI entirely. It uses `argparse` in `beat_cli.py` and runs directly. See [beats CLI](../aiba-beats/cli.md).

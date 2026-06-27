<p align="center">
  <img src="docs/assets/aiba_logo.png" alt="AIBA Logo" width="320" />
</p>

# AIBA — Autonomous Internet Browsing Agent

**You define the goal. It handles the rest.**

AIBA is a multi-agent research engine that turns your terminal into a command center for autonomous internet exploration. It thinks, plans, discovers, distributes, searches, verifies, and synthesizes — autonomously.

---

## What It Does

- **Swarm intelligence** — breaks complex objectives into smaller tasks, executes them in parallel across up to 50 browser-equipped sub-agents, and weaves the results back into a single synthesized report.
- **Two modes** — Agent mode (one focused agent, deep research) or Swarm mode (orchestrator + fleet, breadth and scale).
- **Scheduled beats** — configure it once, and AIBA wakes up on a schedule, does the work, and emails you the report. You don't even need to be there.
- **REPL interface** — the conversation stays open after results. Refine, pivot, drill deeper, save your session, pick it up later.

_The scope of what it can do is tied to your imagination._

---

## How It Works

1. Pick a **mode** (Agent or Swarm) and a **template** (general browsing, job search, OSINT, custom).
2. Describe your goal.
3. AIBA plans an approach, spawns browser agents, executes, adapts, and delivers.
4. The conversation stays open. Keep going, or save it for later.

Built on **Google Gemini** (brains), **Playwright** (browser), **pydantic-ai** (type-safe tool calling), and **logfire** (observability). Licensed under [APL](LICENSE) — free for personal use, modifications welcome, no commercial use without permission.

---

## Setup & Run

### Prerequisites

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** — package manager
- **Node.js 18+ & npm 8+** — required by Playwright MCP
- **A [Gemini API key](https://aistudio.google.com/apikey)**

### 1. Clone and install

```bash
git clone https://github.com/hamza-mughal1/AIBA
cd AIBA
uv sync
```

### 2. Install the browser

```bash
uv run playwright install chromium
```

### 3. Configure

```bash
cp .env.example .env
```

Open `.env` and set the one required field:

```env
GEMINI_API_KEY=AIza...your-key-here
```

Everything else ships with sensible defaults. Tweak them later when you need them.

### 4. Run

```bash
uv run python main.py
```

You'll walk through mode selection, template choice, and effort level. After that, AIBA takes the wheel.

---

## Dive Deeper

This README scratches the surface. For the full picture — modes, templates, effort levels, beat scheduling, guardrails, session persistence, troubleshooting, and the engineering behind it — **read the docs**.

[View the documentation →](https://hamza-mughal1.github.io/AIBA/)


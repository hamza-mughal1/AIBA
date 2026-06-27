# Getting Started

Before anything, make sure you have these.

## Prerequisites

| Requirement | Why |
|---|---|
| **Python 3.13+** | The runtime. If you're on an older version, AIBA won't start. |
| **[uv](https://docs.astral.sh/uv/)** | Package manager. Installs everything in one shot — no virtualenv wrangling. |
| **Node.js & npm** | Playwright MCP needs **Node 18+** and **npm 8+** behind the scenes. npm comes with Node, so one install covers both. |
| **A Gemini API key** | Agents use gemini models to run because they also have vision capabilities |

!!! tip
    Don't have a Gemini key yet? Head to [aistudio.google.com/apikey](https://aistudio.google.com/apikey), click "Create API Key", and paste it into your `.env` file in step 4. The free tier gives you plenty to get started.

---

## Install AIBA

Clone the repository and install dependencies.

```bash
git clone https://github.com/hamza-mughal1/AIBA
cd AIBA
uv sync
```

`uv sync` reads `pyproject.toml` and installs every dependency you need.

---

## Install the Browser

```bash
uv run playwright install chromium
```

Downloads a Chromium engine required by Playwright MCP.

---

## Wire Up Your Environment

```bash
cp .env.example .env
```

Open `.env` and fill in the two fields that matter right now:

```ini
# Required — paste your Gemini API key
GEMINI_API_KEY=AIza...your-key-here
```

The rest can wait. Sensible defaults ship out of the box — tweak them once you know what you want.

!!! warning
    SMTP variables 

    ```ini
    SMTP_HOST
    SMTP_PORT
    SMTP_USERNAME
    SMTP_PASSWORD
    SENDER_EMAIL
    ```

    are required when using email service through the agent's email tool or AIBA-beats email notification. 
    
    _But don't worry for right now, put them later when needed._
---

## Run It

```bash
uv run python main.py
```

You'll walk through a few quick choices:

1. **Mode** — Agent (single focused agent) or Swarm (orchestrator + parallel sub-agents). Start with Agent.
2. **Template** — Pick `default` for general browsing, or `job_search` if you're hunting.
3. **Effort** — Quick, Balanced, or Max. Balanced is your daily driver.


```bash
──────────────────────────────────────────────────────────────────────────────
∞  A I B A   Autonomous Internet Browsing Agent
──────────────────────────────────────────────────────────────────────────────

  Step 1 — Select Mode

  [1]  Agent   Single autonomous agent, full internet access
          Best for focused tasks, single-domain research.

  [2]  Swarm   Orchestrated fleet of parallel sub-agents
          Best for large-scale research, multi-hop mining.

  ▸  Enter 1 or 2: 1

──────────────────────────────────────────────────────────────────────────────
  Step 2 — Select Template

  [1]  default
      General-purpose AI assistant with full internet access. Good for
      research, browsing, QA testing, and open-ended exploration.

  [2]  job_search
      LinkedIn job discovery with direct contact extraction. Derives role
      titles from your profile, searches LinkedIn Jobs, and hunts for
      recruiter emails per verified job posting.

  [3]  osint
      Deep open-source intelligence investigation. Maps a person or
      company's digital footprint across social media, public records,
      news archives, and corporate databases. Produces a structured
      intelligence dossier.

  ▸  Enter 1–3: 1

──────────────────────────────────────────────────────────────────────────────
  Step 3 — Effort Level

  [1]  quick
      Fast & cheap — minimal tool calls, short responses. Good for quick lookups.

  [2]  balanced
      Thorough & pragmatic — cross-check 2–3 sources. Good default.

  [3]  max
      Exhaustive deep-dive — maximum tools, maximum tokens, maximum quality.

  ▸  Enter 1–3: 1
```


Then the prompt appears. Type your goal. Press enter.


```bash
──────────────────────────────────────────────────────────────────────────────
  Step 4 of 4 — Extra Notes

  The template already generated a detailed prompt.
  Add any extra context, URLs, or notes below (optional).
  (Ctrl+D or empty line to skip)

do something...


══════════════════════════════════════════════════════════════════════════════
  Launch Summary
══════════════════════════════════════════════════════════════════════════════
  Mode:  AGENT
  Prompt:  do something...
══════════════════════════════════════════════════════════════════════════════

```

That's it. AIBA takes the wheel.

---

## What Next?

Dive deeper into how AIBA works — [Agent vs Swarm mode](core-concepts/modes.md), scheduling with Beats, or the full configuration reference. Each section unpacks one piece of the puzzle.

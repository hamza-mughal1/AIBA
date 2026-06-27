# REPL

AIBA doesn't just run once and exit. After the initial launch it drops you into a REPL — a read-eval-print loop where you and the agent have a continuous conversation. You type. It responds. You type again.

Every message carries forward. The agent remembers what you've discussed, builds on previous findings, and refines as you go.

---

### Six slash commands are available: `/exit`, `/clear`, `/history`, `/save`, and `/help`

---

## Commands

| Command | What it does |
|---|---|
| `/exit`, `/quit` | Ends the session and returns to the terminal |
| `/clear` | Resets the conversation history but preserves the system prompt — the agent keeps its instructions, just forgets the chat |
| `/history` | Prints the number of messages currently held in context |
| `/save <name>` | Saves the full conversation to `sessions/<name>.json` |
| `/help` | Prints the command reference |

### `/save`

Pass a name — any name. AIBA writes the current history and session settings (mode, effort, template) to a JSON file in the `sessions/` directory.

```
▸  /save deep-research
✓ Session saved to sessions/deep-research.json (47 messages)
```

You can save mid-session and keep going. Save again later with the same name to overwrite, or use a different name to create a snapshot.

Resuming a saved session is done at startup — AIBA asks before the launch screens if you want to load a previous conversation.

---

## How Execution Works

Each turn in the REPL follows the same cycle:

1. **You type something** — a follow-up question, a refinement, a new direction
2. **History is trimmed** — tool noise stripped, old messages capped (see below)
3. **The agent runs** — with the trimmed history as context, plus effort-specific instructions and usage limits
4. **Output renders** — markdown is printed to the terminal
5. **Loop continues** — the prompt returns

Errors don't kill the session. If you hit a usage limit, AIBA tells you and keeps the REPL open — try a shorter prompt or `/clear` to reset. If something unexpected fails, the error is printed and the loop continues.

---

## History Trimming: A Key Engineering Decision

Every turn, AIBA trims the conversation history before passing it to the agent. This isn't an afterthought — it's a deliberate engineering choice that keeps the REPL fast, affordable, and contextually clean.

### Tool output is stripped

The agent calls tools constantly — browser snapshots, search results, file reads. These return verbose payloads: YAML, JSON, HTML, multi-page snapshots. If every tool output stayed in history, the token count would balloon within 3–4 turns.

But the agent's text response already synthesizes what mattered from those tool calls. The raw payloads are noise — the insight is in the text. So AIBA strips every tool-call and tool-return part from history, keeping only user prompts and model text responses.

**Result:** The agent remembers what it *found* without paying tokens to remember how it *looked*.

### Old messages are capped at 20

Even with tool noise removed, history grows. AIBA caps at 20 messages — system prompt preserved as message 0, plus the 19 most recent turns.

The cap isn't a dumb slice. It aligns to a user-message boundary so Gemini's strict turn ordering (user → model → user → model) never breaks. If trimming would cut midway through a turn pair, AIBA includes the full pair.

### Why this matters

Without trimming, a balanced-mode REPL session would exhaust its 300K token budget within 5–6 turns. Tool outputs alone can consume 60–80K tokens per turn. With trimming, the same budget supports 15–20+ turns — and the context the agent actually reads is cleaner.

It's the difference between a REPL that feels like a conversation and one that feels like a meter running.

---

## What's Carried Forward

After each trim, here's what the agent sees in its next turn:

| Kept | Stripped |
|---|---|
| System prompt | Tool-call parts |
| User prompts (all) | Tool-return parts (YAML, JSON, HTML snapshots) |
| Model text responses (all) | Messages beyond the 20-message cap |

The result: a clean, dense context window. Every token the agent reads is a token that helps it think.

---

## Next: Sessions

The `/save` command writes to `sessions/*.json` files. To understand how sessions are structured, how settings are stored, and how to resume from a saved file at startup — see [Sessions](sessions.md).

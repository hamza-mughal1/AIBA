# Sessions

A session is a snapshot — your conversation history and launch settings saved to a JSON file. Save one mid-REPL with `/save`, then resume it at startup whenever you're ready to pick up where you left off.

---

## Startup Resume Flow

The first thing AIBA asks at launch isn't about modes or templates — it's whether you want to resume a previous session.

```
∞  A I B A   Autonomous Internet Browsing Agent
──────────────────────────────────────────────────────────────────────────────

  Load a saved conversation?

  Resumes a previous session from a JSON file saved with /save.

  ▸  [y/N]:
```

Say yes, and you get a list of available sessions:

```
  Select a session

  [1]  deep-research
  [2]  competitor-analysis
  [3]  osint-thread

  ▸  Enter 1–3: 1
```

Select one, and here's what happens:

1. **Settings restore** — mode (agent/swarm), effort level, and template all reload from the session file. No need to re-pick.
2. **History renders** — the saved conversation is printed to the terminal so you can see where you left off.
3. **You're in** — the REPL starts with the restored agent and full history loaded.

If the session was saved in swarm mode, sub-agent count restores too. Every setting is exactly as you left it.

---

## What's in a Session File

Session files live in `sessions/*.json` and follow a simple wrapper structure:

```json
{
  "version": 1,
  "settings": {
    "mode": "agent",
    "effort": "balanced",
    "template_name": "job_search"
  },
  "messages": [ ... ]
}
```

| Field | Content |
|---|---|
| `version` | Schema version for forward compatibility |
| `settings` | Launch configuration — mode, effort, template, and any swarm-specific values like sub-agent count |
| `messages` | The conversation history, already trimmed — the same clean context the agent sees |

---


## Managing Sessions

### Location

All session files go into `sessions/` at the project root:

```
sessions/
├── deep-research.json
├── competitor-analysis.json
└── osint-thread.json
```

The directory is created automatically the first time you save.

### Naming

Any name works. Use something descriptive — the name is how you'll identify the session at startup.

- `deep-research.json` — good
- `session-1.json` — you'll forget what this was
- `Untitled.json` — you will definitely forget

### Listing

At startup, sessions are listed newest first. The last-saved session appears first.

### Overwriting

Save with the same name to overwrite. Save with a new name to create a snapshot. You can save multiple times in the same REPL session, capturing different states along the way.

---

## Next: Browser Session & Cookies

When you want to allow the agent to use your logins and browser state without giving the credentials and for sites like LinkedIn and Indeed (which hit you with a sign-in wall and don't like automations), you'll want a persistent browser profile. See [Browser Session & Cookies](browser-session.md).

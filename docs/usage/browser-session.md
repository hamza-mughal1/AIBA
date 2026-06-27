# Browser Session & Cookies

A browser session is a JSON file — `.playwright-mcp/cookies.json` — that holds your login state for sites the agent needs to access. Playwright loads it at startup. It never writes back.

Sessions save your conversation. Cookies save your login. They're separate.

---

## Why You Need It

Some sites — LinkedIn, Indeed, any platform behind a login page — hit the agent with a sign-in wall. Without valid cookies, there's nothing to browse. The agent navigates, sees a login form, and stalls.

Cookies skip the login entirely. The agent arrives already authenticated.

---

## How to Set It Up

### 1. Install a cookie exporter

Use **Cookie-Editor** ([Chrome](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) / [Firefox](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)) in your main browser. Any extension that exports cookies as JSON works.

### 2. Log into the site

Open the platform — LinkedIn, Indeed, wherever — and sign in normally with your browser. Browse around once to make sure the session is active.

### 3. Export the cookies

Open Cookie-Editor on that site. Click **Export** — it copies the full cookie set to your clipboard as JSON.

### 4. Paste into AIBA

Paste the JSON into `.playwright-mcp/cookies.json` in the project root. If the file doesn't exist, create it.

```bash
# Create the directory if it's not there
mkdir -p .playwright-mcp
```

That's it. Run AIBA — Playwright loads the cookies on startup and the agent shows up authenticated.

---

## Refreshing Expired Cookies

Cookies expire. When the agent suddenly hits a login wall where it used to sail through, the session expired. Same process to fix:

1. Log into the site again in your main browser
2. Export fresh cookies from Cookie-Editor
3. Replace `.playwright-mcp/cookies.json` with the new export

No restart needed — the next agent run picks up the new file.

---

## How It Works

Playwright launches with two flags that make this possible:

| Flag | What it does |
|---|---|
| `--isolated` | No connection to your personal browser profile. No history, no bookmarks, no cookie collisions — a clean sandbox. |
| `--storage-state` | Points to `.playwright-mcp/cookies.json`. Read-only — Playwright loads the cookies at startup and applies them to the browsing context. It never modifies the file. |

---

!!! warning "Use a test account"
    Platforms like LinkedIn and Indeed actively detect automated browsing patterns. If the agent's behavior triggers a detection, the platform may issue a **temporary ban** on the account whose cookies are in use.
    
    Create a separate test account for AIBA. Don't risk your primary profile.

---

## Next: AIBA-beats

Sessions capture conversations. Cookies capture login state. AIBA-beats captures *scheduling* — running agents on a timer, unattended. See [AIBA-beats](../aiba-beats/introduction.md).

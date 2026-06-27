# Troubleshooting

Something not working? You're in the right place.

---

## Before Anything Else

1. **Check your `.env`** — is `GEMINI_API_KEY` set and valid?
2. **Run a simple test** — `python main.py`, pick Agent mode, quick effort, general browsing, and ask "what is 2+2?"
3. **Read the docs** — the [Engineering](engineering.md) page explains every design decision; the [Guardrails](security/guardrails.md) page covers safety systems

---

## Common Issues

### "GEMINI_API_KEY not set" or authentication errors

Get a free key from [Google AI Studio](https://aistudio.google.com/). Paste it into `.env`:

```
GEMINI_API_KEY=AIza...
```

### Playwright won't start / browser errors

Make sure Playwright browsers are installed:

```bash
npx playwright install chromium
```

If you're on a headless server, ensure `PLAYWRIGHT_HEADLESS=true` in `.env`.

### Rate limits / quota exceeded

Gemini free tier has usage caps. If you hit them frequently:

- Switch to `WEB_SEARCH_ENGINE=duckduckgo` (free, no quota)
- Lower `MAX_CONCURRENT_SUB_AGENTS` to reduce parallel API calls
- Use `quick` or `balanced` effort mode instead of `max`

### Email sending fails

Gmail requires an [App Password](https://support.google.com/accounts/answer/185833), not your account password. Set it in `.env`:

```
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
```

---

## Still Stuck?

- **Open a GitHub issue** — [github.com/hamza-mughal1/AIBA/issues](https://github.com/hamza-mughal1/AIBA/issues)
- **Connect on LinkedIn** — [linkedin.com/in/-hamza-mughal](https://www.linkedin.com/in/-hamza-mughal/)

I built AIBA and I'm happy to help. Don't hesitate to reach out.

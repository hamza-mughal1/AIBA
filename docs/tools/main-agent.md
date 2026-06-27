# Main Agent Tools

The main agent (Orchestrator) has five tools — three of its own, plus two shared CSV tools. It never touches the web — it plans, dispatches, tracks, and reports.

---

### The orchestrator's tools: [spawn_sub_agents](#spawn_sub_agents), [send_email](#send_email), [todo](common-tools.md#todo), [read_csv](common-tools.md#read_csv), and [append_csv](common-tools.md#append_csv)

---

## `spawn_sub_agents`

Dispatch a list of prompts to concurrent sub-agents. Each gets its own independent, internet-capable agent context.

```python
spawn_sub_agents([
    "Go to example.com and find all email addresses...",
    "Search LinkedIn for engineers at the target company...",
    "Check the company's careers page for tech stack...",
])
```

All prompts run in parallel, bounded by `max_concurrent_sub_agents` and `request_timeout_seconds` settings. The results are aggregated and returned together.

---

## `send_email`

Send an email via SMTP with an optional file attachment.

| Parameter | Description |
|---|---|
| `to` | Recipient email address |
| `subject` | Subject line |
| `body` | Plain text message |
| `attachment_filename` (optional) | Just the filename — looked up in `static/` |

Attachments must pre-exist in the `static/` directory. The orchestrator does not create files; it only attaches what's there.

---

## `todo`, `read_csv` and `append_csv`

The main agent also has `todo`, `read_csv` and `append_csv` — the same functions available to the sub-agent in Agent mode. 

These tools are shared between both agents. The full details are documented in [Common Tools](common-tools.md).

---

## Next: Sub-Agent Tools

The main agent plans. The sub-agent executes. See what tools the sub-agent brings to the web — [Sub-Agent Tools](sub-agent.md).

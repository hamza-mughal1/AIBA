# Sub-Agent Tools

The sub-agent is the web worker. It has five groups of capabilities — some always available, some loaded on demand, some injected only in certain modes.

---

### Tool groups: [Discovery](#discovery), [Browser Automation](#browser-automation), [File & Image](#file-image), [Meta](#meta), and [CSV & Todo (injected)](#csv-todo-injected)

---

## Discovery

### `web_search`

It uses native search engine (e.g. Google) if available (or allowed from the env `WEB_SEARCH_ENGINE=native`) else it uses DuckDuckGo search. Returns a list of result links with snippets. This is the sub-agent's primary reconnaissance tool — used for broad-spectrum discovery, target surface mapping, and dorking.

The sub-agent is instructed to run multiple search variations with different operators per target (e.g., `site:facebook.com` combined with keywords, names, location filters).

### `web_fetch`

Fetch a URL and parse it to markdown. A first-pass probe for static or semi-static pages. If the returned content is sparse, JavaScript-dependent, or blocked, the sub-agent escalates to the browser.

---

## Browser Automation

The Playwright MCP server provides full browser control. It is **deferred** — not loaded at startup. The sub-agent must call `load_capability` to bring it into memory first.

| Tool | Purpose |
|---|---|
| `browser_navigate(url)` | Go to a URL. Saves an accessibility snapshot to a `.yml` file, returns only the file path |
| `browser_snapshot(filename)` | Capture the current page's accessibility tree to a file |
| `browser_click(selector)` | Click an element. Use `ref` from the snapshot for precision |
| `browser_type(selector, text)` | Type text into an input |
| `browser_fill(selector, value)` | Fill a form field |
| `browser_evaluate(script)` | Execute arbitrary JavaScript in the page context |
| `browser_take_screenshot` | Capture a visual screenshot of the viewport |
| `browser_press_key(key)` | Press a keyboard key |
| `browser_hover(selector)` | Hover over an element |
| `browser_select_option(selector, value)` | Select a dropdown option |
| `browser_drag(selector, target)` | Drag an element to a target |
| `browser_wait_for(ms)` | Wait for a specified duration |
| `browser_close` | Close the current page |
| `browser_tabs` | Manage browser tabs |

### How the sub-agent uses the browser

A typical deep-dive follows this pattern:

1. `browser_navigate(url)` → returns a snapshot file path
2. `read_and_filter_file` on that path → extracts relevant links and data
3. `browser_click` on promising links → each returns a new snapshot path
4. `read_and_filter_file` on each → extracts structured data
5. `browser_evaluate` → extracts JSON-LD, meta tags, JS state
6. `browser_take_screenshot` → `read_image` → visual verification

### Configuration

- **Headless by default** — controlled by `PLAYWRIGHT_HEADLESS` env var in the REPL. Beats always force headless.
- **Cookies** — loaded from `.playwright-mcp/cookies.json` via `--storage-state`. See [Browser Session & Cookies](../usage/browser-session.md).
- **Artifacts** — screenshots and snapshots go to `.playwright-mcp/`.

---

## File & Image

### `read_image`

Read a local image file and return it to the agent's vision model. Used after `browser_take_screenshot` for visual analysis of rendered content — profile pages, contact sections, team grids, areas where CSS or canvas may hide data.

### `read_and_filter_file`

Read a text file with filters. `browser_navigate`, `browser_click`, and `browser_snapshot` all return file paths — this tool extracts what matters from those files.

| Parameter | Description |
|---|---|
| `file_path` | Path to the text file |
| `start_line` | Optional — 1-indexed start line |
| `end_line` | Optional — 1-indexed end line (defaults to the first 300 lines) |
| `search_string` | Optional — only return lines containing this substring |
| `search_regex` | Optional — only return lines matching this regex |

The sub-agent is trained to filter aggressively — run multiple passes with different regex patterns and line ranges rather than requesting the full snapshot.

---

## Meta

### `search_tools`

Search the agent's own internal tool registry for deferred or hidden Python tools. This is **not** a web search tool. The sub-agent is instructed to call this only if it genuinely needs to discover a tool it knows exists but can't see.

### `load_capability`

Load a deferred capability bundle into memory. Currently used for the Playwright MCP server — the sub-agent calls this when a task requires interactive browser automation.

---

## CSV & Todo (injected)

The sub-agent does not always have CSV and todo tools. They are **injected per-run** based on the execution mode:

| Mode | CSV & Todo tools? | How |
|---|---|---|
| **Agent mode** | Yes | Injected via `csv_toolset` in `run_sub_agent()` |
| **Swarm mode** | No | `spawn_sub_agents()` calls the raw `sub_agent.run()` — no injection |

The engineering decisions behind when and why these tools appear — and how CSV access is whitelisted — are documented in [Common Tools](common-tools.md).

---

## Next: Common Tools

The tools shared between both agents — CSV read/write, todo tracking, and the access control layer — are covered in [Common Tools](common-tools.md).

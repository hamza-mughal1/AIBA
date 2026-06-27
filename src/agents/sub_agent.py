import mimetypes
import os
import re
from pathlib import Path
from typing import Any

from fastmcp.client.transports.stdio import StdioTransport
from pydantic_ai import Agent, AgentRetries, BinaryContent, ToolReturn
from pydantic_ai.capabilities import MCP as MCPCapability
from pydantic_ai.capabilities import (
    IncludeToolReturnSchemas,
    ReinjectSystemPrompt,
    Thinking,
    WebFetch,
    WebSearch,
)
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.run import AgentRunResult
from pydantic_ai.toolsets.function import FunctionToolset
from pydantic_ai_shields import InputGuard, SecretRedaction

from src.prompts import EffortMode, get_effort_config
from src.tools.common_tools import append_csv as _append_csv
from src.tools.common_tools import read_csv as _read_csv
from src.tools.common_tools import todo as _todo
from src.utils.settings import AibaSettings

STORAGE_STATE_PATH = str(Path(".playwright-mcp/cookies.json").resolve())

_settings = AibaSettings()

# @playwright/mcp respects the HEADLESS env var (0=headed/visible, 1=headless).
# Merge with os.environ so the subprocess inherits PATH, DISPLAY, HOME, etc.
mcp_env = {**os.environ, "HEADLESS": "1" if _settings.playwright_headless else "0"}

# ----- System prompt for the sub-agent -----
SYSTEM_PROMPT = """
# ROLE AND CORE OBJECTIVE
You are an AIBA (Autonomous Internet Browsing Agent) Sub-Agent — an elite, maximum-effort web reconnaissance operative. Your singular mandate is to deliver the **most complete, accurate, and deeply researched results possible**, regardless of token cost, tool calls, or execution time. Mediocrity and surface-level scraping are unacceptable. You go deep, you cross-verify, you exhaust every lead.

---

## IMPORTANT: FRAMEWORK META-TOOLS

The following tools are **Pydantic AI framework administration tools** — they are NOT web search or browsing tools. Do NOT call them as part of your investigation.

- **`search_tools`**: Searches the agent's internal tool registry for deferred/hidden Python tools. It does NOT search the web. Call this ONLY if you genuinely need to discover a tool that you know exists but isn't visible. In most runs you will never need this.
- **`load_capability`**: Loads a deferred capability bundle (e.g. the Playwright browser MCP server) into memory. The browser tools will appear after loading, but you should only load Playwright when a task explicitly requires interactive browser automation.

**For web searching, always use `web_search`** (the DuckDuckGo search capability) — that is your dedicated internet search tool. If you need to search the web, do NOT call `search_tools`.

---

## OPERATING PHILOSOPHY: MAXIMUM DEPTH, ZERO COMPROMISE

1. **No Shortcuts:** Never choose a lighter tool to save resources. If a browser can reveal more than a static fetch, use the browser. If visual inspection can catch something text missed, take the screenshot.
2. **Multi-Hop Exhaustion:** A single page visit is not enough. Click through pagination, expand collapsed sections, follow "Load More" buttons, navigate sub-pages, open profiles, inspect modals. Leave no interactive element unexplored.
3. **Cross-Verification:** Corroborate findings across multiple sources. If you find an email on one page, verify it against the company's domain pattern, WHOIS data, or a secondary source. Never trust a single data point.
4. **Layered Extraction:** `browser_navigate` saves a snapshot to a `.yml` file and returns only the path — use `read_and_filter_file` to inspect it. Combine with `browser_evaluate` (JS runtime) and `browser_take_screenshot` (visual) for complete coverage.
5. **Tool Stacking:** The tools are designed to be used in combination, not isolation. A proper investigation chain uses 4–6 tools minimum per target.

---

## TOOL ARSENAL

### 1. Web Search (`web_search`)
- **Purpose:** Broad-spectrum discovery, dorking, and target surface mapping.
- **Protocol:** Execute multiple search variations with different operators. For LinkedIn targets, combine `site:linkedin.com` with role keywords, company names, and location filters. For corporate targets, dork for `site:company.com careers`, `site:company.com "team"`, `site:company.com/about`. Run at least 3–5 distinct searches per reconnaissance vector before concluding.

### 2. Web Fetch (`web_fetch`)
- **Purpose:** Rapid initial assessment of static or semi-static pages.
- **Protocol:** Use as a first-pass probe. If the returned markdown is sparse, missing structured data, or clearly JS-dependent, immediately escalate to the browser. Never accept an empty or thin `web_fetch` result as final — always verify with the browser.

### 3. Playwright MCP Server (`browser_*` toolkit)
- **Purpose:** Full-spectrum browser automation for dynamic sites, SPAs, authenticated sessions, form interactions, and visual verification.
- **Available Actions:**
  - `browser_navigate(url)` — Navigate to a URL. Saves the page accessibility snapshot
    to a `.yml` file and returns ONLY the file path link. The snapshot content is NOT in
    the response — use `read_and_filter_file` with the link to inspect it.
  - `browser_snapshot` — Capture the current page's accessibility tree.
    **ALWAYS pass `filename`** (e.g. `".playwright-mcp/<xyz>.yml"`) so it saves to a file and only returns
    the path. Without `filename`, the full YAML dump is returned inline — NEVER omit it.
  - `browser_click(selector)` — Click an element. Use `ref` from snapshot for precision.
  - `browser_type(selector, text)` — Type text into an input field.
  - `browser_fill(selector, value)` — Fill a form field.
  - `browser_evaluate(script)` — Execute arbitrary JavaScript in the page context.
  - `browser_take_screenshot` — Capture a visual screenshot of the current viewport. Must save them in `.playwright-mcp/`.
  - `browser_press_key(key)` — Press a keyboard key.
  - `browser_hover(selector)` — Hover over an element.
  - `browser_select_option(selector, value)` — Select a dropdown option.
  - `browser_drag(selector, target)` — Drag an element to a target.
  - `browser_wait_for(ms)` — Wait for a specified duration.
  - `browser_close` — Close the current page.
  - `browser_tabs` — Manage browser tabs.
- **Deep Exploration Protocol:**
  1. Navigate to target page.
  2. Use `read_and_filter_file` on the saved snapshot link to find relevant elements.
  3. Click into every promising link, profile, or detail section (each returns a snapshot link).
  4. Use `read_and_filter_file` on each returned snapshot link to extract data.
  5. Use `browser_evaluate` to extract structured data (JSON-LD, meta tags, window.__INITIAL_STATE__).
  6. Use `browser_take_screenshot` → `read_image` for visual verification of complex layouts.

### 4. Read Image (`read_image`)
- **Purpose:** Visual intelligence for rendered content that text parsers miss.
- **Protocol:** After `browser_take_screenshot`, pass the file path to `read_image` for visual analysis. Use this on profile pages, contact sections, team grids, and any area where CSS obfuscation or canvas rendering may hide data.

### 5. File Filter (`read_and_filter_file`)
- **Purpose:** Precision extraction from large text dumps.
- **Protocol:** `browser_navigate`, `browser_click`, and `browser_snapshot(filename="...")` all return
    only a file path link to the saved snapshot. Use `read_and_filter_file` immediately on that
    link with targeted filters (regex for emails, search strings for names, line ranges for sections).
    Filter aggressively — run multiple passes if needed (emails, phones, names, company info).
    By default `read_and_filter_file` returns the first 300 lines; use `start_line`/`end_line` to
    narrow. Never request the full unfiltered snapshot content.

---

## TACTICAL EXECUTION PIPELINES

### Pipeline A: Deep Search & Map
`web_search` (3–5 variant queries) → For each promising result: `web_fetch` (first pass) → If thin/blocked: escalate to Pipeline B → Compile discovered URLs into a target list.

### Pipeline B: Full Browser Deep-Dive (The Default Pipeline)
`browser_navigate(url)` → `read_and_filter_file` (inspect the returned snapshot, isolate links/names/emails) → For each relevant link: `browser_click` → `read_and_filter_file` → `browser_evaluate` (extract structured data) → `browser_take_screenshot` → `read_image` → Repeat for all pagination, tabs, and sub-pages until exhausted.

### Pipeline C: Visual & JS Bypass
Page blocks text extraction → `browser_take_screenshot` → `read_image` (visual reasoning) → `browser_evaluate` (bypass obfuscation, extract from JS objects) → `browser_snapshot(filename="recheck.yml")` → `read_and_filter_file` → Loop until data is recovered.

### Pipeline D: Authenticated Deep Access
For LinkedIn or auth-gated sites: `browser_navigate` → Let session cookies handle auth → `browser_click` to `/jobs`, `/company`, `/in/username` paths → Deep-click into profiles, job listings, company pages → Use `read_and_filter_file` on every snapshot link returned.

---

## STRUCTURAL IMPERATIVES

1. **Depth Over Speed:** A 10-tool-call investigation that finds the answer is infinitely better than a 2-tool-call shortcut that misses it. Use as many tools as needed.
2. **Exhaust Before Concluding:** Never report "not found" until you have tried: multiple search queries, browser navigation, snapshot inspection, JS extraction, visual screenshot analysis, and sub-page traversal.
3. **Output Quality:** Return structured, detailed results with source URLs, verification notes, and confidence indicators. Prefer tables or labeled sections over raw text dumps.
4. **Pivot Aggressively:** If one path dead-ends, immediately try a different search query, a different domain, a different tool combination. Creative persistence wins.
5. **Behavioral Tone:** Professional, thorough, and relentless. No conversational filler — but do log your reasoning for tool choices and pivot decisions so the orchestrator can follow your investigation trail.
6. **Storage:** All artifacts (screenshots, text dumps) go in `.playwright-mcp/` or the MCP's default output directory.
"""


# ----- Sub-Agent Definition -----
sub_agent_model = GoogleModel(
    model_name=AibaSettings().gemini_sub_model,
    provider=GoogleProvider(api_key=AibaSettings().gemini_api_key),
)

playwright_mcp_args = [
    "-y",
    "@playwright/mcp@latest",
    "--isolated",
    f"--storage-state={STORAGE_STATE_PATH}",
    "--output-dir",
    ".playwright-mcp",
]

if _settings.playwright_headless:
    playwright_mcp_args.append("--headless")

# ---- Playwright MCP via StdioTransport (deferred) ----
playwright_transport = StdioTransport(
    command="npx",
    args=playwright_mcp_args,
    env=mcp_env,
)

playwright_cap = MCPCapability(
    local=playwright_transport,
    id="playwright",
    description="Browser automation: navigate pages, take snapshots, click elements, fill forms.",
    defer_loading=True,
)

# ----- Configurable web search -----
if _settings.web_search_engine == "duckduckgo":
    _web_search_cap = WebSearch(native=False, local="duckduckgo")
else:
    _web_search_cap = WebSearch(local="duckduckgo")

# ----- Initialize the sub-agent with the specified model -----
sub_agent = Agent(
    model=sub_agent_model,
    system_prompt=SYSTEM_PROMPT,
    capabilities=[
        _web_search_cap,
        WebFetch(local=True),
        playwright_cap,
        ReinjectSystemPrompt(),
        IncludeToolReturnSchemas(
            tools=lambda ctx, td: bool(td.return_schema),
        ),
        *([SecretRedaction(), InputGuard()] if _settings.guardrails_enabled else []),
    ],
    tool_timeout=60.0,
    end_strategy="early",
    retries=AgentRetries(tools=1, output=1),
    max_concurrency=3,
)


# ----- Define tools for the sub-agent -----
@sub_agent.tool_plain
def read_image(file_path: str) -> ToolReturn:
    """Reads an image from a local file path and returns it to the agent.

    Args:
        file_path: The absolute or relative path to the image file.
    """
    path = Path(file_path)

    # 1. Error handling: check if the file exists
    if not path.is_file():
        raise FileNotFoundError(f"No image found at the path: {file_path}")

    # 2. Read the image bytes
    image_bytes = path.read_bytes()

    # 3. Dynamically guess the correct media type (default to image/png if unsure)
    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/png"

    # 4. Package into BinaryContent and return via ToolReturn
    return ToolReturn(
        return_value=BinaryContent(data=image_bytes, media_type=mime_type)
    )


@sub_agent.tool_plain
def read_and_filter_file(
    file_path: str,
    start_line: int | None = None,
    end_line: int | None = 300,
    search_string: str | None = None,
    search_regex: str | None = None,
) -> str:
    """Reads a file and extracts relevant lines based on line ranges or search criteria.

    Args:
        file_path: The path to the text file.
        start_line: Optional 1-indexed line number to start reading from.
        end_line: Optional 1-indexed line number to stop reading at (inclusive).
        search_string: Optional substring. If provided, only lines containing this exact text are returned.
        search_regex: Optional Python regular expression. If provided, only lines matching this regex are returned.
    """
    path = Path(file_path)
    if not path.is_file():
        return f"Error: File not found at {file_path}"

    try:
        # Read all lines from the file
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        return f"Error reading file: {str(e)}"

    output_lines = []

    # Compile regex if provided
    compiled_regex = None
    if search_regex:
        try:
            compiled_regex = re.compile(search_regex)
        except re.error as e:
            return f"Error: Invalid regular expression pattern: {str(e)}"

    # Process line by line (1-indexed for intuitive LLM usage)
    for idx, line in enumerate(lines, start=1):
        # 1. Apply line range filters if they exist
        if start_line is not None and idx < start_line:
            continue
        if end_line is not None and idx > end_line:
            continue

        # 2. Apply text search filters if they exist
        if search_string and search_string not in line:
            continue

        # 3. Apply regex filters if they exist
        if compiled_regex and not compiled_regex.search(line):
            continue

        # If it passes all criteria, keep it with its line number
        output_lines.append(f"{idx}: {line}")

    if not output_lines:
        return "No matching lines found based on the provided filters."

    return "\n".join(output_lines)


# ----- Main function to run the sub-agent -----
def run(
    prompt: str,
    effort_mode: EffortMode = EffortMode.BALANCED,
    **kwargs: Any,
) -> AgentRunResult:
    """Run the sub-agent. Returns the full result object.

    Args:
        prompt: The natural-language task for the sub-agent.
        effort_mode: Controls temperature, token budget, and instruction depth.
        **kwargs: Forwarded to sub_agent.run_sync (e.g. message_history,
            model_settings, usage_limits). Override config-derived defaults.

    Returns:
        AgentRunResult with .output, .all_messages(), .new_messages(), etc.
    """
    config = get_effort_config(effort_mode)
    run_kwargs: dict[str, Any] = {
        "instructions": config["instructions"],
        "model_settings": config["model_settings"],
        "usage_limits": config["usage_limits"],
    }
    if effort_mode == EffortMode.MAX:
        run_kwargs["capabilities"] = [Thinking(effort="high")]

    # REPL-provided kwargs take precedence over config defaults
    run_kwargs.update(kwargs)

    # CSV/todo tools are injected per-run so they are ONLY available when
    # run() is called directly (agent mode).  spawn_sub_agents() calls
    # sub_agent.run() — the pydantic-ai method — which skips injection.
    csv_toolset = FunctionToolset(tools=[_read_csv, _append_csv, _todo])

    return sub_agent.run_sync(
        prompt,
        toolsets=[csv_toolset],
        **run_kwargs,
    )

# Common Tools

The functions in `src/tools/common_tools.py` operate at two levels — they are the concrete tools that agents call **and** the global state machine that controls access to them.

---

### There are three common tools: [todo](#todo), [read_csv](#read_csv), and [append_csv](#append_csv)

---

## `todo`

Read or update the task plan. This is a stateful tool — tasks persist in memory for the lifetime of the agent run.

```python
# Write a plan
todo([
    {"id": 1, "task": "Scrape LinkedIn jobs", "status": "pending"},
    {"id": 2, "task": "Scrape Indeed jobs", "status": "pending"},
    {"id": 3, "task": "Merge and deduplicate", "status": "pending"},
])

# Read current state
todo()
```

| Parameter | Default | Description |
|---|---|---|
| `todos` | `None` | Pass a list of task dicts to write a new plan. Omit to read current state. |

Each task dict has three required keys:

| Key | Type | Values |
|---|---|---|
| `id` | `int` | Unique task identifier |
| `task` | `str` | Human-readable task description |
| `status` | `str` | `"pending"`, `"in-progress"`, or `"completed"` |

Output uses unicode icons: ○ pending, ◉ in-progress, ✓ completed.

_It allows the agent to remember the tasks in long runs without drifing from the goal._

---

## `read_csv`

Read a CSV file from `data/` and return it as a markdown table.

```python
read_csv(filename="jobs.csv", max_rows=200)
```

| Parameter | Default | Description |
|---|---|---|
| `filename` | — | Just the filename. Looked up in `data/`. |
| `max_rows` | 200 | Maximum rows to return. |

The output is a formatted markdown table with aligned columns and a row count footer when results are truncated.

---

## `append_csv`

Append rows to a CSV file in `data/`.

```python
append_csv("jobs.csv", [
    {"title": "Software Engineer", "company": "Acme Corp", "source": "linkedin"},
    {"title": "Product Manager", "company": "Beta Inc", "source": "indeed"},
])
```

Rules:

- The CSV must **pre-exist** with a header row. `append_csv` does not create files.
- All row keys must match the existing headers exactly — unknown columns are rejected.
- Missing columns in a row are also rejected.
- Whitelist checks apply (see below).

---

## How CSV Injection Works

The sub-agent gets `csv_toolset` — a bundle containing `read_csv`, `append_csv`, and `todo` — only when called through `run_sub_agent()`.

### The two call paths

```
User / Beat
    │
    ├── Agent Mode ──→ run_sub_agent()
    │                       │
    │                       ├── injects csv_toolset ──→ sub_agent has CSV+todo tools
    │                       └── calls sub_agent.run_sync(prompt, toolsets=[...])
    │
    └── Swarm Mode ──→ run_agent() ──→ spawn_sub_agents()
                                            │
                                            └── calls sub_agent.run(prompt)
                                                (no toolsets= argument)
                                                → sub_agent does NOT get CSV+todo tools
```

### Why the distinction

| Mode | Why CSV tools are (or aren't) injected |
|---|---|
| **Agent mode** | One sub-agent, full task ownership. It needs to track its own plan and persist results to CSVs. |
| **Swarm mode** | Multiple parallel sub-agents. CSV access from concurrent workers would cause race conditions and file corruption. The orchestrator owns the plan and synthesis. |

### How it's wired

In `run_sub_agent()`:

```python
csv_toolset = FunctionToolset(tools=[_read_csv, _append_csv, _todo])

return sub_agent.run_sync(
    prompt,
    toolsets=[csv_toolset],
    ...
)
```

`FunctionToolset` is the pydantic-ai mechanism for injecting plain Python functions as agent tools at call time. The tools are not registered on the agent itself — they're passed per-run, so they only appear when `run_sub_agent()` is the entry point.

---

## CSV Whitelisting

CSV access is governed by one global variable in `common_tools.py`:

| Variable | Type | Meaning |
|---|---|---|
| `_beat_allowed_csvs` | `list[str] \| None` | `None` = unrestricted (REPL). `list` = only those filenames allowed (beat). |

In beat mode the `_beat_allowed_csvs` is set to a list containing all of the whitelisted csv files allowed for that beat. (configured in the beat `allowed_csvs`). And in REPL mode it is set to `NONE` which allows the access to all of the csv files.

### Why whitelisting exists

In beat mode, a single misconfigured prompt could read or corrupt any CSV on disk. Whitelisting forces the user to explicitly declare which CSVs a beat may touch. The files must pre-exist with headers so the agent never creates rogue data files.

---

## Who Always Has These Tools

| Agent | `read_csv` | `append_csv` | `todo` | How |
|---|---|---|---|---|
| **Main agent (orchestrator)** | Always | Always | Always (own impl) | Registered with `@main_agent.tool_plain` at import time — permanently attached. |
| **Sub-agent (Agent mode)** | Yes | Yes | Yes | Injected via `csv_toolset` in `run_sub_agent()`. |
| **Sub-agent (Swarm mode)** | No | No | No | Not injected — sub-agents are stateless workers. |

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, AgentRetries
from pydantic_ai.capabilities import (
    IncludeToolReturnSchemas,
    ReinjectSystemPrompt,
    Thinking,
)
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.run import AgentRunResult
from pydantic_ai_shields import CostTracking, InputGuard, ToolGuard

from src.agents.sub_agent import sub_agent
from src.prompts import EffortMode, get_effort_config
from src.tools.common_tools import append_csv as _append_csv
from src.tools.common_tools import read_csv as _read_csv
from src.tools.common_tools import todo as _todo
from src.utils.settings import AibaSettings

_settings = AibaSettings()

MAIN_SYSTEM_PROMPT = """\
# ROLE AND CORE OBJECTIVE
You are the AIBA Main Orchestrator—a multi-stage strategic planning and execution engine. Your objective is to achieve exhaustive information retrieval by systematically executing a continuous discovery, planning, and multi-generational swarming loop.

You never interact with web browsers directly. Your role is to define the global research architecture, initialize and manage a strict state-driven task tracking system, dispatch concurrent workloads to a fleet of sub-agents, and recursively iterate on newly discovered intelligence vectors until all targets are verified or exhausted.

---

## AVAILABLE TOOLS AND PROTOCOLS

### 1. `todo`
* **Purpose:** Read or update the global execution plan state machine.
* **Format Constraints:** Each task dict must contain:
    * `id`: unique integer identifier
    * `task`: precise string description of the operational target
    * `status`: literal value constraint of "pending", "in-progress", or "completed"
* **Usage:** Pass a list of task dicts to persist a new plan. Omit the argument (or pass nothing) to read the current state.
* **Operational Mandate:** Invoke immediately during Phase 1 to establish your baseline plan. Re-invoke at the end of each wave to update task states or inject newly discovered sub-tasks. Read at the start of each turn to assess cross-turn state.

### 2. `spawn_sub_agents`
* **Purpose:** Dispatches concurrent, internet-capable sub-agent contexts to execute discrete web exploration tasks.
* **Operational Mandate:** Accepts a list of natural-language strings containing absolute contextual vectors, structural constraints, and direct commands.

### 3. `send_email`
* **Purpose:** Sends an email with optional file attachment via SMTP (Gmail).
* **Parameters:** `to` (recipient address), `subject`, `body` (plain text), `attachment_filename` (optional — just the filename, looked up automatically in the static/ folder).
* **Operational Mandate:** Use when the user asks to send results, reports, or attachments by email. Pass only the filename, not a full path.

---

## DETERMINISTIC ORCHESTRATION LOOP

You must continuously execute this four-phase cycle across multiple turns until the target objective is fully resolved.

### Phase 1: Initial Discovery and Planning
1. Break down the user's objective into atomic research vectors.
2. Initialize the global plan by calling `todo` with specific, isolated tasks covering distinct web targets (e.g., domain indices, directory scraping, platform graphs).

### Phase 2: Concurrent Swarm Deployment
1. Read the state table using `todo` (no arguments). Identify the immediate parallel-safe dependency tier.
2. Update the status of the selected tasks to "in-progress" via `todo`.
3. Invoke `spawn_sub_agents` with explicit instructions. Demand that sub-agents extract underlying structures, API footprints, and hidden identifiers rather than basic landing-page text.

### Phase 3: Ingestion, Pivot Detection, and Recalibration
1. Analyze the returned payloads from the sub-agent wave.
2. Match findings against your pending tasks. Update completed items to "completed" via `todo`.
3. **Detect Pivot Vectors:** If a sub-agent discovers an unmapped asset (e.g., a specific internal URL, a corporate entity name, an executive handle, or a pattern change), you must immediately generate a new set of tasks to exploit that lead. Append these new tasks to your tracking state with unique IDs and a "pending" status via `todo`.
4. **Synthesis Gate (CRITICAL):** After 2–3 waves, assess honestly: "Can I produce a useful, substantive answer with what I have right now?" If yes, proceed to Phase 4 synthesis immediately — even if some sub-tasks remain open. Only loop back to Phase 2 if a major vector is completely unaddressed AND your remaining budget can sustain another wave. **Perfect is the enemy of done.** Partial synthesis is far better than hitting a guardrail with zero output.

### Phase 4: High-Fidelity Intelligence Synthesis
1. Once all recursive paths have hit absolute technical boundaries or have been successfully evaluated as "completed," unify the structural payloads.
2. Compile the dense data findings, resolve inconsistencies, and deliver the finalized, structured report.

---

## ARCHITECTURAL CONSTRAINTS

* **State Alignment Enforced:** You are forbidden from executing a sub-agent wave without recording or updating the relevant actions inside the todo tracking system. The todo list is your anchor against execution drift.
* **Resource Budgeting:** Each effort mode allocates tool-call, token, and request budgets via pydantic-ai's UsageLimits. Operate within them. If a sub-agent exhausts its budget, reformulate the task into smaller atomic units rather than re-running the same large prompt.
* **Dependency Isolation:** If Task B requires data from Task A, do not execute them simultaneously. Run Task A, capture the structural output, update the todo state, and launch Task B in the subsequent wave using the newly acquired data vector.
* **Fault Isolation:** If a sub-agent execution thread encounters an anti-bot boundary or timeout, do not abandon the task. In your next recalibration loop, reformulate the task, update the todo tracking table, and instruct follow-up sub-agents to pivot to alternative execution paths (e.g., visual snapshot processing or custom evaluation scripts).
* **Zero Speculation:** Never infer or synthesize unverified data points. If a critical objective remains unreached after exhausting all logical pivot tracks, present the explicit verification limits reached in the final summary report.
"""

_main_agent_model = GoogleModel(
    model_name=_settings.gemini_main_model,
    provider=GoogleProvider(api_key=_settings.gemini_api_key),
)

_agent_todo: list[dict[str, Any]] = []
_current_effort_mode: EffortMode = EffortMode.BALANCED

main_agent = Agent(
    model=_main_agent_model,
    system_prompt=MAIN_SYSTEM_PROMPT,
    capabilities=[
        ReinjectSystemPrompt(),
        IncludeToolReturnSchemas(),
        *(
            [
                CostTracking(budget_usd=_settings.cost_budget_usd),
                ToolGuard(require_approval=_settings.require_approval_for),
                InputGuard(),
            ]
            if _settings.guardrails_enabled
            else []
        ),
    ],
    retries=AgentRetries(tools=1, output=1),
)

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"


@main_agent.tool_plain
def send_email(
    to: str,
    subject: str,
    body: str,
    attachment_filename: str | None = None,
) -> str:
    """Send an email via SMTP (Gmail by default).

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
        attachment_filename: Optional filename (looked up in the static/ folder).

    """
    try:
        msg = EmailMessage()
        msg["From"] = _settings.sender_email
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)

        if attachment_filename:
            path = STATIC_DIR / attachment_filename
            if not path.is_file():
                available = (
                    ", ".join(p.name for p in STATIC_DIR.iterdir() if p.is_file())
                    if STATIC_DIR.is_dir()
                    else "static/ directory not found"
                )
                return f"ERROR: File '{attachment_filename}' not found in static/. Available: {available}"
            msg.add_attachment(
                path.read_bytes(),
                maintype="application",
                subtype="octet-stream",
                filename=path.name,
            )

        with smtplib.SMTP(_settings.smtp_host, _settings.smtp_port) as server:
            server.starttls()
            server.login(_settings.smtp_username, _settings.smtp_password)
            server.send_message(msg)

        return f"Email sent successfully to {to}"
    except Exception as exc:
        return f"Email failed: {type(exc).__name__}: {exc}"


@main_agent.tool_plain
async def spawn_sub_agents(sub_agents: list[str]) -> str:
    """Spawn multiple AIBA Sub-Agents to execute prompts in parallel.

    Each string in `sub_agents` is handed to an independent, internet-capable sub-agent.
    All tasks run concurrently with a per-task timeout and concurrency limits.

    Args:
        sub_agents: List of natural-language prompt strings, one per sub-agent.

    Returns:
        Aggregated results from all sub-agents, delimited and indexed.

    """
    if not sub_agents:
        return "No sub-agent tasks to execute."

    semaphore = asyncio.Semaphore(_settings.max_concurrent_sub_agents)
    timeout = _settings.request_timeout_seconds

    async def run_one(prompt: str, idx: int) -> str:
        async with semaphore:
            try:
                config = get_effort_config(_current_effort_mode)
                with sub_agent.parallel_tool_call_execution_mode("sequential"):
                    result = await asyncio.wait_for(
                        sub_agent.run(
                            prompt,
                            instructions=config["instructions"],
                            model_settings=config["model_settings"],
                            usage_limits=config["usage_limits"],
                        ),
                        timeout=timeout,
                    )
                return f"=== SUB-AGENT {idx} RESULT ===\n{result.output}"

            except TimeoutError:
                return (
                    f"=== SUB-AGENT {idx} ERROR ===\n"
                    f"Task timed out after {timeout}s.\n"
                    f"Prompt snippet: {prompt[:100]}..."
                )
            except Exception as exc:
                return (
                    f"=== SUB-AGENT {idx} ERROR ===\n"
                    f"{type(exc).__name__}: {exc}\n"
                    f"Prompt snippet: {prompt[:100]}..."
                )

    # Schedule all tasks to run concurrently on the main event loop
    tasks = [run_one(prompt, i + 1) for i, prompt in enumerate(sub_agents)]
    results = await asyncio.gather(*tasks)

    header = f"Spawned {len(sub_agents)} sub-agent(s). All completions processed.\n\n"
    return header + "\n\n".join(results)


# ----- CSV tools (imported from src/tools/common_tools) -----
read_csv = main_agent.tool_plain(_read_csv)
append_csv = main_agent.tool_plain(_append_csv)
todo = main_agent.tool_plain(_todo)


# ----- Main orchestrator run function -----
def run(
    prompt: str,
    effort_mode: EffortMode = EffortMode.BALANCED,
    **kwargs: Any,
) -> AgentRunResult:
    """Run the main orchestrator agent. Returns the full result object
    so callers can access .output, .all_messages(), .new_messages(), etc.

    Args:
        prompt: Natural-language research or automation request.
        effort_mode: Controls temperature, token budget, and instruction depth
                     for both the orchestrator and spawned sub-agents.
        **kwargs: Forwarded to main_agent.run_sync (e.g. message_history,
            model_settings, usage_limits). Override config-derived defaults.

    Returns:
        AgentRunResult with .output, .all_messages(), .new_messages(), etc.

    """
    global _agent_todo, _current_effort_mode
    _agent_todo = []
    _current_effort_mode = effort_mode

    config = get_effort_config(effort_mode)
    run_kwargs: dict[str, Any] = {
        "instructions": config["main_instructions"],
        "model_settings": config["model_settings"],
        "usage_limits": config["usage_limits"],
    }
    if effort_mode == EffortMode.MAX:
        run_kwargs["capabilities"] = [Thinking(effort="high")]

    # REPL-provided kwargs take precedence
    run_kwargs.update(kwargs)

    return main_agent.run_sync(
        prompt,
        **run_kwargs,
    )

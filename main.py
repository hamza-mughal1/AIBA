import logging
import shutil
import sys
from typing import Any, cast

import logfire
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.run import AgentRunResult

from src.agents.main_agent import run as run_agent
from src.agents.sub_agent import run as run_sub_agent
from src.prompts import get_effort_config, get_template
from src.services import rendering as R
from src.services import repl, screens
from src.services.session import print_history
from src.utils.settings import AibaSettings


# ── Silence Google SDK AFC warnings ───────────────────────────────
# pydantic-ai handles tool orchestration — AFC is irrelevant here.
class _SuppressAFC(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "automatic function calling (AFC)" not in record.getMessage()


logging.getLogger("google_genai.models").addFilter(_SuppressAFC())

# ── Logfire ───────────────────────────────────────────────────────
_settings = AibaSettings()
if _settings.logfire_enabled:
    logfire.configure(
        token=_settings.logfire_token,
        console=logfire.ConsoleOptions(show_project_link=False),
        scrubbing=False,
    )
    logfire.instrument_system_metrics()
    logfire.instrument_pydantic_ai()

# ── Entry Point ───────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["beat", "beats"]:
        from src.services.beat_cli import beat_cli

        beat_cli()
        exit(0)

    loaded = screens.session()

    if loaded is not None:
        history, agent_fn, agent_name, config, session_settings = loaded
        print()
        print(R.hr("─", "dim"))
        print(
            f"  {R.C['green']}✓{R.C['reset']} Resuming conversation with {agent_name} ({len(history)} messages)"
        )
        print(R.hr("─", "dim"))

        print_history(history)

        class _LoadedResult:
            def all_messages(self):
                return history

        fake_result = cast(AgentRunResult, _LoadedResult())
        repl.run(agent_fn, fake_result, config, agent_name, session_settings)
        exit(0)

    # Fresh start — walk through all setup screens
    mode = screens.mode()
    template_name = screens.template()
    effort = screens.effort()
    sub_agent_count = _settings.max_concurrent_sub_agents
    if mode == "swarm":
        sub_agent_count = screens.sub_agents()

    extra = screens.prompt(mode)

    template = get_template(template_name)
    if not _settings.user_profile:
        print(
            f"\n  {R.C['yellow']}⚠{R.C['reset']}  USER_PROFILE is empty in .env —"
            f" templates like job_search will have no context."
        )
        print(
            f"  {R.C['dim']}Set USER_PROFILE in .env with your skills and experience.{R.C['reset']}\n"
        )

    prompt = template.generate_prompt(_settings.user_profile, extra)
    screens.confirm(mode, sub_agent_count, prompt)

    config = get_effort_config(effort)

    try:
        if mode == "agent":
            result = run_sub_agent(prompt=prompt, effort_mode=effort)
            agent_fn = run_sub_agent
            agent_name = "Agent"
        else:
            result = run_agent(prompt=prompt, effort_mode=effort)
            agent_fn = run_agent
            agent_name = "Orchestrator"

        print("\n\n")
        R.render_markdown(result.output)

        session_settings: dict[str, Any] = {
            "mode": mode,
            "effort": effort.value,
            "template_name": template_name,
        }
        if mode == "swarm":
            session_settings["sub_agent_count"] = sub_agent_count

        repl.run(agent_fn, result, config, agent_name, session_settings)

    except UsageLimitExceeded as exc:
        w = shutil.get_terminal_size().columns
        print(
            f"\n{R.C['yellow']}╔{'═' * (w - 2)}╗{R.C['reset']}\n"
            f"{R.C['yellow']}║{R.C['reset']}  {R.C['bold']}RESOURCE LIMIT HIT{R.C['reset']}\n"
            f"{R.C['yellow']}║{R.C['reset']}  {exc}\n"
            f"{R.C['yellow']}║{R.C['reset']}  Rerun with a higher effort mode.\n"
            f"{R.C['yellow']}╚{'═' * (w - 2)}╝{R.C['reset']}\n"
        )
    except Exception as exc:
        w = shutil.get_terminal_size().columns
        print(
            f"\n{R.C['red']}╔{'═' * (w - 2)}╗{R.C['reset']}\n"
            f"{R.C['red']}║{R.C['reset']}  {R.C['bold']}FATAL ERROR{R.C['reset']}\n"
            f"{R.C['red']}║{R.C['reset']}  {type(exc).__name__}: {exc}\n"
            f"{R.C['red']}╚{'═' * (w - 2)}╝{R.C['reset']}\n"
        )

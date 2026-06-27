from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.run import AgentRunResult

from src.prompts import EffortConfig
from src.services.rendering import C, hr, render_markdown
from src.services.session import (
    SESSIONS_DIR,
    load_session,
    print_history,
    save_session,
    trim_history,
)

_HELP = f"""  {C["bold"]}Commands:{C["reset"]}
  {C["teal"]}/exit, /quit{C["reset"]}   End the session
  {C["teal"]}/clear{C["reset"]}         Reset history (keeps system prompt)
  {C["teal"]}/history{C["reset"]}       Show message count
  {C["teal"]}/save <name>{C["reset"]}  Save conversation to {SESSIONS_DIR}/<name>.json
  {C["teal"]}/help{C["reset"]}          Show this message
"""


# ----- This is commented out to not include the load command in the REPL for now, as it is disorienting the UX -----

# _HELP += f"""  {C["teal"]}/load <name>{C["reset"]}  Load conversation from {SESSIONS_DIR}/<name>.json"""

def run(
    agent_fn: Callable[..., AgentRunResult],
    initial_result: AgentRunResult,
    config: EffortConfig,
    agent_name: str = "Agent",
    session_settings: dict[str, Any] | None = None,
) -> None:
    """Interactive REPL loop with persistent chat history."""
    history = initial_result.all_messages()
    if session_settings is None:
        session_settings = {}

    print(
        f"\n{C['dim']}Session started. Type /exit to quit, /clear to reset, /help for commands.{C['reset']}\n"
    )

    while True:
        try:
            user_input = input(f"  {C['teal']}▸{C['reset']}  ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C['dim']}Session ended.{C['reset']}")
            break

        if not user_input:
            continue

        lower = user_input.lower()

        if lower in ("/exit", "/quit"):
            print(f"  {C['dim']}Session ended.{C['reset']}")
            break

        if lower == "/clear":
            history = initial_result.all_messages()[:1]
            print(f"  {C['dim']}History cleared. System prompt preserved.{C['reset']}")
            continue

        if lower == "/history":
            print(f"  {C['dim']}Messages in history: {len(history)}{C['reset']}")
            continue

        if lower.startswith("/save "):
            raw = user_input[6:].strip()
            name = Path(raw).stem
            if not name:
                print(f"  {C['red']}✗{C['reset']}  Usage: /save <name>")
                continue
            try:
                save_session(name, history, session_settings)
                print(
                    f"  {C['green']}✓{C['reset']} Session saved to {SESSIONS_DIR / name.split('.')[0]}.json ({len(history)} messages)"
                )
            except Exception as exc:
                print(f"  {C['red']}✗{C['reset']} Failed to save: {exc}")
            continue

        # ----- This is commented out to not include the load command in the REPL for now, as it is disorienting the UX -----
        
        # if lower.startswith("/load "):
        #     raw = user_input[6:].strip()
        #     name = Path(raw).stem
        #     if not name:
        #         print(f"  {C['red']}✗{C['reset']}  Usage: /load <name>")
        #         continue
        #     try:
        #         loaded_history, loaded_settings = load_session(name)
        #         history = loaded_history
        #         if loaded_settings:
        #             session_settings = loaded_settings
        #         print(
        #             f"  {C['green']}✓{C['reset']} Loaded {len(history)} messages from {SESSIONS_DIR / name}.json"
        #         )
        #         print_history(loaded_history)
        #     except Exception as exc:
        #         print(f"  {C['red']}✗{C['reset']} Failed to load: {exc}")
        #     continue

        if lower == "/help":
            print(_HELP)
            continue

        if lower.startswith("/"):
            print(f"  {C['red']}✗{C['reset']}  Unknown command: '{user_input}'")
            print(_HELP)
            continue

        print(f"  {C['dim']}Thinking...{C['reset']}", end="\r")
        try:
            instructions_key = (
                "main_instructions" if agent_name == "Orchestrator" else "instructions"
            )
            result = agent_fn(
                user_input,
                message_history=history,
                instructions=config.get(instructions_key),
                model_settings=config["model_settings"],
                usage_limits=config["usage_limits"],
            )
            print(f"  {C['dim']}           {C['reset']}", end="\r")

            print()
            print(hr("─", "dim"))
            render_markdown(result.output)
            print(hr("─", "dim"))
            print()

            history = trim_history(result.all_messages())

        except UsageLimitExceeded as exc:
            print(f"\n  {C['yellow']}⚠{C['reset']}  Resource limit hit: {exc}")
            print(
                f"  {C['dim']}Try a shorter prompt or use /clear to reset.{C['reset']}"
            )
        except Exception as exc:
            print(f"\n  {C['red']}✗{C['reset']}  Error: {type(exc).__name__}: {exc}")

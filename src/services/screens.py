from src.agents.main_agent import run as run_agent
from src.agents.sub_agent import run as run_sub_agent
from src.prompts import EffortMode, get_effort_config, list_effort_modes, list_templates
from src.prompts.templates import register_all_templates
from src.services.rendering import C, badge, hr
from src.services.session import SESSIONS_DIR, list_sessions, load_session
from src.utils.settings import AibaSettings

_settings = AibaSettings()
register_all_templates()


def mode() -> str:
    """Step 1 — choose agent or swarm."""
    print()
    print(hr())
    print(
        f"{C['bold']}{C['green']}∞  A I B A{C['reset']}   {C['dim']}Autonomous Internet Browsing Agent{C['reset']}",
    )
    print(hr())
    print()
    print(f"  {C['bold']}{C['teal']}Step 1 — Select Mode{C['reset']}")
    print()
    print(
        f"  {C['bold']}[1]{C['reset']}  Agent   {C['dim']}Single autonomous agent, full internet access{C['reset']}",
    )
    print(
        f"          {C['dim']}Best for focused tasks, single-domain research.{C['reset']}",
    )
    print()
    print(
        f"  {C['bold']}[2]{C['reset']}  Swarm   {C['dim']}Orchestrated fleet of parallel sub-agents{C['reset']}",
    )
    print(
        f"          {C['dim']}Best for large-scale research, multi-hop mining.{C['reset']}",
    )
    print()
    while True:
        choice = input(f"  {C['teal']}▸{C['reset']}  Enter 1 or 2: ").strip()
        if choice == "1":
            return "agent"
        if choice == "2":
            return "swarm"
        print(f"  {C['red']}✗{C['reset']}  Invalid. Type 1 (Agent) or 2 (Swarm).")


def template() -> str:
    """Step 2 — choose a task template."""
    templates = list_templates()
    print()
    print(hr())
    print(f"  {C['bold']}{C['teal']}Step 2 — Select Template{C['reset']}")
    print()
    for i, tmpl in enumerate(templates, start=1):
        print(f"  {C['bold']}[{i}]{C['reset']}  {C['teal']}{tmpl.name}{C['reset']}")
        desc = tmpl.description
        from shutil import get_terminal_size

        w = get_terminal_size().columns
        while len(desc) > w - 10:
            cut = desc.rfind(" ", 0, w - 10)
            if cut == -1:
                cut = w - 10
            print(f"      {C['dim']}{desc[:cut]}{C['reset']}")
            desc = desc[cut:].lstrip()
        print(f"      {C['dim']}{desc}{C['reset']}")
        print()
    while True:
        choice = input(
            f"  {C['teal']}▸{C['reset']}  Enter 1–{len(templates)}: ",
        ).strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(templates):
                return templates[idx].name
        except ValueError:
            pass
        print(f"  {C['red']}✗{C['reset']}  Invalid. Enter a number 1–{len(templates)}.")


def effort() -> EffortMode:
    """Step 3 — choose how hard the agent tries."""
    modes = list_effort_modes()
    print()
    print(hr())
    print(f"  {C['bold']}{C['teal']}Step 3 — Effort Level{C['reset']}")
    print()
    descriptions = {
        EffortMode.QUICK: "Fast & cheap — minimal tool calls, short responses. Good for quick lookups.",
        EffortMode.BALANCED: "Thorough & pragmatic — cross-check 2–3 sources. Good default.",
        EffortMode.MAX: "Exhaustive deep-dive — maximum tools, maximum tokens, maximum quality.",
    }
    for i, m in enumerate(modes, start=1):
        print(f"  {C['bold']}[{i}]{C['reset']}  {C['teal']}{m.value}{C['reset']}")
        print(f"      {C['dim']}{descriptions[m]}{C['reset']}")
        print()
    while True:
        choice = input(f"  {C['teal']}▸{C['reset']}  Enter 1–{len(modes)}: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(modes):
                return modes[idx]
        except ValueError:
            pass
        print(f"  {C['red']}✗{C['reset']}  Invalid. Enter a number 1–{len(modes)}.")


def sub_agents() -> int:
    """Step 4 (swarm only) — max concurrent sub-agents."""
    default = _settings.max_concurrent_sub_agents
    print()
    print(hr())
    print(f"  {C['bold']}{C['teal']}Step 4 of 5 — Sub-Agent Pool{C['reset']}")
    print()
    print(
        f"  How many sub-agents can run in parallel?  {C['dim']}Range 1–50{C['reset']}",
    )
    print("  Higher values = more throughput, more API tokens.")
    print()
    while True:
        raw = input(
            f"  {C['teal']}▸{C['reset']}  Max sub-agents [{C['dim']}{default}{C['reset']}]: ",
        ).strip()
        if not raw:
            return default
        try:
            n = int(raw)
            if 1 <= n <= 50:
                return n
            print(f"  {C['red']}✗{C['reset']}  Must be between 1 and 50.")
        except ValueError:
            print(f"  {C['red']}✗{C['reset']}  Enter a number.")


def prompt(mode: str) -> str:
    """Step N — optional extra notes appended to the template prompt."""
    step = "4 of 4" if mode == "agent" else "5 of 5"
    print()
    print(hr())
    print(f"  {C['bold']}{C['teal']}Step {step} — Extra Notes{C['reset']}")
    print()
    print("  The template already generated a detailed prompt.")
    print("  Add any extra context, URLs, or notes below (optional).")
    print(f"  {C['dim']}(Ctrl+D or empty line to skip){C['reset']}")
    print()
    lines: list[str] = []
    try:
        while True:
            line = input()
            if line == "" and lines:
                break
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines).strip()


def confirm(mode: str, sub_agent_count: int, prompt: str) -> None:
    """Show summary before launching."""
    preview = prompt[:100] + ("…" if len(prompt) > 100 else "")
    print()
    print(hr("═"))
    print(f"  {C['bold']}{C['purple']}Launch Summary{C['reset']}")
    print(hr("═"))
    print(badge("Mode", mode.upper()))
    if mode == "swarm":
        print(badge("Sub-agents", str(sub_agent_count)))
    print(badge("Prompt", preview))
    print(hr("═"))
    print("\n\n\n")


def session():
    """Shown first — optionally load a saved conversation and resume it.

    Returns a tuple (history, agent_fn, agent_name, config, session_settings)
    if loaded, or None to proceed with the normal fresh-start flow.
    """
    print()
    print(hr())
    print(
        f"{C['bold']}{C['green']}∞  A I B A{C['reset']}   {C['dim']}Autonomous Internet Browsing Agent{C['reset']}",
    )
    print(hr())
    print()
    print(f"  {C['bold']}{C['teal']}Load a saved conversation?{C['reset']}")
    print("  Resumes a previous session from a JSON file saved with /save.")
    print()

    while True:
        choice = input(f"  {C['teal']}▸{C['reset']}  [y/N]: ").strip().lower()
        if choice in ("n", "no", ""):
            return None
        if choice in ("y", "yes"):
            break
        print(f"  {C['red']}✗{C['reset']}  Type 'y' or 'n'.")

    available = list_sessions()
    if not available:
        print(
            f"\n  {C['red']}✗{C['reset']}  No saved sessions found in {SESSIONS_DIR}/.",
        )
        return None

    print()
    print(f"  {C['bold']}{C['teal']}Select a session{C['reset']}")
    print()
    for i, s in enumerate(available, start=1):
        print(f"  {C['bold']}[{i}]{C['reset']}  {C['teal']}{s}{C['reset']}")
    print()

    while True:
        choice = input(
            f"  {C['teal']}▸{C['reset']}  Enter 1–{len(available)}: ",
        ).strip()
        if not choice:
            continue
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(available):
                name = available[idx]
                break
        except ValueError:
            pass
        print(f"  {C['red']}✗{C['reset']}  Enter a number 1–{len(available)}.")

    try:
        history, saved_settings = load_session(name)
    except Exception as exc:
        print(f"  {C['red']}✗{C['reset']} Failed to load '{name}': {exc}")
        return None

    if saved_settings:
        mode_val = saved_settings.get("mode", "agent")
        effort_str = saved_settings.get("effort", "balanced")
        template_name = saved_settings.get("template_name", "general_browsing")
        sub_agent_count = saved_settings.get("sub_agent_count")

        try:
            effort_val = EffortMode(effort_str)
        except ValueError:
            effort_val = EffortMode.BALANCED

        if mode_val == "swarm":
            agent_fn = run_agent
            agent_name = "Orchestrator"
        else:
            agent_fn = run_sub_agent
            agent_name = "Agent"

        config = get_effort_config(effort_val)
        session_settings = dict(saved_settings)

        print()
        print(hr("─", "dim"))
        print(f"  {C['green']}✓{C['reset']} Restoring session with saved settings:")
        print(badge("Mode", mode_val))
        print(badge("Effort", effort_val.value))
        print(badge("Template", template_name))
        if sub_agent_count:
            print(badge("Sub-agents", str(sub_agent_count)))
        print(hr("─", "dim"))

        return (history, agent_fn, agent_name, config, session_settings)

    print()
    print(f"  {C['bold']}{C['teal']}Agent type{C['reset']}")
    print("  Press Enter for default (Agent) or type 'orch' for Orchestrator.")
    agent_type = input(f"  {C['teal']}▸{C['reset']}  [Agent]: ").strip().lower()
    if agent_type in ("orch", "orchestrator"):
        agent_fn = run_agent
        agent_name = "Orchestrator"
    else:
        agent_fn = run_sub_agent
        agent_name = "Agent"

    config = get_effort_config(EffortMode.BALANCED)
    session_settings = {
        "mode": "agent" if agent_name == "Agent" else "swarm",
        "effort": "balanced",
    }

    return (history, agent_fn, agent_name, config, session_settings)

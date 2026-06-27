"""CLI dispatcher for beat subcommands (list, run, schedule)."""

from __future__ import annotations

import sys

from src.services import rendering as R
from src.services.beats import (
    load_beats,
    os_schedule_instructions,
    run_all_due,
    run_beat,
)


def beat_cli() -> None:
    """Dispatch beat subcommands before entering the interactive flow."""
    sub = sys.argv[2] if len(sys.argv) > 2 else ""

    if sub == "list":
        beats = load_beats()
        if not beats:
            print("No beats configured. Edit beats.yaml to add one.")
            return
        print()
        print(R.hr())
        print(f"  {R.C['bold']}{R.C['teal']}Beats{R.C['reset']}")
        print(R.hr())
        for name, beat in beats.items():
            print(f"\n  {R.C['bold']}{R.C['green']}{name}{R.C['reset']}")
            print(f"  {R.C['dim']}Schedule:{R.C['reset']}   {beat.schedule}")
            print(f"  {R.C['dim']}Mode:{R.C['reset']}       {beat.mode}")
            print(f"  {R.C['dim']}Template:{R.C['reset']}   {beat.template}")
            print(f"  {R.C['dim']}Effort:{R.C['reset']}     {beat.effort}")
            print(f"  {R.C['dim']}Sub-agents:{R.C['reset']} {beat.sub_agents}")
            if beat.prompt_extra:
                print(
                    f"  {R.C['dim']}Extra:{R.C['reset']}      {beat.prompt_extra[:80]}"
                )
            if beat.allowed_csvs:
                print(
                    f"  {R.C['dim']}CSVs:{R.C['reset']}       {', '.join(beat.allowed_csvs)}"
                )
            if beat.notify_email:
                print(f"  {R.C['dim']}Notify:{R.C['reset']}     {beat.notify_email}")
        print()
        return

    if sub == "run":
        target = sys.argv[3] if len(sys.argv) > 3 else ""
        if target == "--all":
            results = run_all_due()
            for r in results:
                status = r.get("status", "?")
                icon = {
                    "success": R.C["green"] + "✓",
                    "error": R.C["red"] + "✗",
                    "skipped": R.C["dim"] + "○",
                }.get(status, "?")
                out = (r.get("output") or "")[:100]
                print(f"  {icon}{R.C['reset']} {r.get('beat', '?')}: {out}")
            return
        if not target:
            print("Usage: python main.py beat run <name>")
            print("       python main.py beat run --all")
            return
        result = run_beat(target)
        status = result.get("status", "?")
        icon = {
            "success": R.C["green"] + "✓",
            "error": R.C["red"] + "✗",
            "skipped": R.C["dim"] + "○",
        }.get(status, "?")
        print(f"  {icon}{R.C['reset']} {target}: {status}")
        if result.get("output"):
            R.render_markdown(result["output"])
        if result.get("errors"):
            for err in result["errors"]:
                print(f"  {R.C['red']}✗{R.C['reset']} {err}")
        return

    if sub == "schedule":
        print()
        print(os_schedule_instructions())
        print()
        return

    # Help
    print()
    print(f"  {R.C['bold']}Usage:{R.C['reset']}")
    print(f"  {R.C['teal']}python main.py beat list{R.C['reset']}       List all beats")
    print(
        f"  {R.C['teal']}python main.py beat run <name>{R.C['reset']}  Run a single beat"
    )
    print(
        f"  {R.C['teal']}python main.py beat run --all{R.C['reset']}  Run all due beats"
    )
    print(
        f"  {R.C['teal']}python main.py beat schedule{R.C['reset']}   Show OS scheduler setup"
    )
    print()

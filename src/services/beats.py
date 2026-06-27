"""Beat system — scheduled autonomous agent runs.

Beats are pre-configured one-shot agent invocations defined in beats.yaml.
An external scheduler (cron/launchd/Task Scheduler) polls `beat run --all`
every few minutes to fire beats that are due.
"""

from __future__ import annotations

import json
import smtplib
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import yaml
import markdown
from croniter import croniter
from pydantic import BaseModel, EmailStr, Field, model_validator

from src.agents.main_agent import run as run_orch
from src.agents.sub_agent import run as run_agent
from src.prompts import EffortMode, get_template
from src.tools.common_tools import (
    get_beat_allowed_csvs,
    set_beat_allowed_csvs,
)
from src.utils.settings import AibaSettings

BEATS_YAML = Path("beats.yaml")
STATE_PATH = Path("data/beat_state.json")
LOGS_DIR = Path("logs")


class BeatConfig(BaseModel):
    """Validated beat configuration loaded from beats.yaml."""
    
    name: str = Field(
        ...,
        description="Unique name for this beat (used in logs and state)",
    )

    schedule: str = Field(
        ...,
        description="Cron expression — e.g. '0 9 * * *', '*/30 * * * *'",
    )
    template: str = Field(
        ...,
        description="Template name registered in src/prompts/templates.py",
    )
    effort: str = Field(
        default="balanced",
        description="quick | balanced | max",
    )
    mode: str = Field(
        default="agent",
        description="agent (single sub-agent with browser + CSV/todo) | swarm (orchestrator with sub-agents)",
    )
    sub_agents: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Max concurrent sub-agents for this beat",
    )
    prompt_extra: str = Field(
        default="",
        description="Additional instructions appended to the template-generated prompt",
    )
    budget_override_usd: float | None = Field(
        default=None,
        description="Override the global COST_BUDGET_USD for this beat",
    )
    notify_email: EmailStr = Field(
        default="",
        description="Email address to send run summary to (SMTP must be configured)",
    )
    headless: bool = Field(
        default=True,
        description="Force headless browser. Beats always run headless — ignored if false.",
    )
    allowed_csvs: list[str] = Field(
        default_factory=list,
        description=(
            "CSV files the agent may read and append to. "
            "Each file must pre-exist with header columns. "
            "The agent reads before acting (dedup) and appends after acting (record)."
        ),
    )

    @model_validator(mode="after")
    def _template_exists(self) -> BeatConfig:
        from src.prompts import list_templates

        available = [t.name for t in list_templates()]
        if self.template not in available:
            raise ValueError(
                f"Template '{self.template}' not found. "
                f"Available: {', '.join(available)}"
            )
        return self

    @model_validator(mode="after")
    def _effort_valid(self) -> BeatConfig:
        try:
            EffortMode(self.effort)
        except ValueError:
            raise ValueError(
                f"Effort '{self.effort}' is not a valid EffortMode. "
                f"Valid: {', '.join(e.value for e in EffortMode)}"
            )
        return self

    @model_validator(mode="after")
    def _mode_valid(self) -> BeatConfig:
        if self.mode not in ("agent", "swarm"):
            raise ValueError(
                f"Mode '{self.mode}' is invalid. Must be 'agent' or 'swarm'."
            )
        return self

    @model_validator(mode="after")
    def _valid_cron_expression(self) -> BeatConfig:
        """Validate the cron expression."""
        try:
            croniter(self.schedule)
        except (ValueError, KeyError) as exc:
            raise ValueError(f"Invalid cron expression '{self.schedule}': {exc}")

        return self


def load_beats(path: Path = BEATS_YAML) -> dict[str, BeatConfig]:
    """Load and validate all beats from beats.yaml."""
    if not path.is_file():
        return {}

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    beats_root = raw.get("beats") if isinstance(raw, dict) else None
    if not beats_root or not isinstance(beats_root, dict):
        return {}

    beats: dict[str, BeatConfig] = {}
    for name, data in beats_root.items():
        if not isinstance(data, dict):
            raise ValueError(f"Beat '{name}': expected a dictionary of settings")
        beats[name] = BeatConfig.model_validate(data)

    return beats


def is_due(schedule: str, last_run: datetime | None) -> bool:
    """Return True if enough time has passed since last_run for this cron schedule."""
    if last_run is None:
        return True

    now = datetime.now(timezone.utc)
    last_naive = last_run.replace(tzinfo=None)
    it = croniter(schedule, last_naive)
    next_run: datetime = it.get_next(datetime)

    return now >= next_run.replace(tzinfo=timezone.utc)


def load_state() -> dict[str, dict[str, Any]]:
    """Read beat state from JSON. Returns empty dict if missing or corrupt."""
    if not STATE_PATH.is_file():
        return {}

    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict[str, dict[str, Any]]) -> None:
    """Atomically write beat state to disk."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
    tmp.replace(STATE_PATH)


def log_beat_run(beat_name: str, result: dict[str, Any]) -> None:
    """Write structured JSON log and append one-line markdown summary."""
    beat_log_dir = LOGS_DIR / beat_name
    beat_log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    iso = timestamp.strftime("%Y-%m-%dT%H%M%S")

    log_entry = {
        "beat": beat_name,
        "started_at": result.get("started_at"),
        "finished_at": timestamp.isoformat(),
        "duration_s": result.get("duration_s", 0),
        "status": result.get("status", "unknown"),
        "agent_output_summary": (result.get("output") or "")[:500],
        "tool_calls": result.get("tool_calls", 0),
        "cost_usd": result.get("cost_usd", 0),
        "errors": result.get("errors", []),
    }

    (beat_log_dir / f"{iso}.json").write_text(
        json.dumps(log_entry, indent=2, default=str), encoding="utf-8"
    )

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    icon = "✓" if result.get("status") == "success" else "✗"
    summary_line = (
        f"{timestamp.strftime('%Y-%m-%d %H:%M')} "
        f"| {beat_name} "
        f"| {icon} "
        f"${log_entry['cost_usd']:.2f} "
        f"| {log_entry['agent_output_summary'][:120]}\n"
    )

    with (LOGS_DIR / "beat_summary.md").open("a", encoding="utf-8") as f:
        f.write(summary_line)


def run_beat(name: str) -> dict[str, Any]:
    """Load a beat, check schedule, resolve config, and fire a one-shot agent run.

    Returns a dict with status, output, cost, and errors for logging.
    """
    beats = load_beats()
    if name not in beats:
        return {
            "status": "error",
            "output": None,
            "errors": [f"Beat '{name}' not found in beats.yaml"],
            "duration_s": 0,
            "cost_usd": 0,
            "tool_calls": 0,
        }

    beat = beats[name]
    state = load_state()
    beat_state = state.get(name, {})
    last_run_str = beat_state.get("last_run")
    last_run = datetime.fromisoformat(last_run_str) if last_run_str else None

    if not is_due(beat.schedule, last_run):
        return {
            "status": "skipped",
            "output": f"Not due yet. Last run: {last_run_str or 'never'}",
            "errors": [],
            "duration_s": 0,
            "cost_usd": 0,
            "tool_calls": 0,
        }

    started_at = datetime.now(timezone.utc)
    t0 = time.monotonic()
    settings = AibaSettings()

    # Save references to restore after the current run to avoid side effects 
    # on upcoming beats.
    old_allowed = get_beat_allowed_csvs()
    old_headless = settings.playwright_headless
    old_budget = settings.cost_budget_usd
    old_max = settings.max_concurrent_sub_agents

    # Apply beat overrides via setters
    set_beat_allowed_csvs(list(beat.allowed_csvs))
    settings.playwright_headless = True  # beats always headless
    if beat.budget_override_usd is not None:
        settings.cost_budget_usd = beat.budget_override_usd
    settings.max_concurrent_sub_agents = beat.sub_agents

    result_info: dict[str, Any]

    try:
        template = get_template(beat.template)
        effort_mode = EffortMode(beat.effort)

        prompt = template.generate_prompt(settings.user_profile, beat.prompt_extra)

        if beat.mode == "agent":
            agent_result = run_agent(prompt=prompt, effort_mode=effort_mode)
        else:
            agent_result = run_orch(prompt=prompt, effort_mode=effort_mode)

        output = (
            agent_result.output
            if hasattr(agent_result, "output")
            else str(agent_result)
        )

        usage = agent_result.usage

        try:
            cost_usd = float(agent_result.response.cost().total_price)
        except Exception:
            cost_usd = 0.0

        result_info = {
            "status": "success",
            "output": output,
            "tool_calls": usage.tool_calls,
            "cost_usd": cost_usd,
            "errors": [],
            "started_at": started_at.isoformat(),
            "duration_s": round(time.monotonic() - t0, 2),
        }
    except Exception as exc:
        result_info = {
            "status": "error",
            "output": None,
            "tool_calls": 0,
            "cost_usd": 0,
            "errors": [f"{type(exc).__name__}: {exc}"],
            "started_at": started_at.isoformat(),
            "duration_s": round(time.monotonic() - t0, 2),
        }
    finally:
        # Restore globals
        set_beat_allowed_csvs(old_allowed)
        settings.playwright_headless = old_headless
        settings.cost_budget_usd = old_budget
        settings.max_concurrent_sub_agents = old_max

    # Persist state
    state[name] = {
        "last_run": started_at.isoformat(),
        "last_status": result_info["status"],
        "total_runs": beat_state.get("total_runs", 0) + 1,
    }
    save_state(state)

    # Log
    if result_info["status"] != "skipped":
        log_beat_run(name, result_info)

    # Email summary
    if beat.notify_email and result_info["status"] in ("success", "error"):
        _send_beat_summary(beat, result_info, settings)

    return result_info


def run_all_due() -> list[dict[str, Any]]:
    """Run every beat whose schedule has elapsed since last run."""
    beats = load_beats()
    results: list[dict[str, Any]] = []

    for name in beats:
        result = run_beat(name)
        results.append(result)

    return results


def os_schedule_instructions() -> str:
    """Return OS-specific instructions for setting up the external scheduler."""
    import platform
    import shutil

    cwd = Path.cwd()
    uv_path = shutil.which("uv") or "uv"
    cmd = f"cd {cwd} && {uv_path} run python main.py beat run --all"

    lines = [
        "# Schedule AIBA Beats",
        "",
        "Add this line to your system scheduler to poll every 5 minutes:",
        "",
    ]

    system = platform.system().lower()
    if system == "linux":
        lines += [
            "## Linux (cron)",
            "",
            "```",
            "# Run: \n",
            "crontab -e\n",
            "# Then paste this line at the end of the file: \n",
            f"*/5 * * * * {cmd} >> {cwd}/logs/cron.log 2>&1",
            "```",
        ]
    elif system == "darwin":
        lines += [
            "## macOS (launchd) or crontab",
            "",
            "### Option A: crontab (simplest)",
            "```",
            "# Run: crontab -e",
            f"*/5 * * * * {cmd} >> {cwd}/logs/cron.log 2>&1",
            "```",
            "",
            "### Option B: launchd",
            "Create ~/Library/LaunchAgents/com.aiba.beats.plist with StartInterval=300",
        ]
    elif system == "windows":
        lines += [
            "## Windows (Task Scheduler)",
            "",
            "1. Open Task Scheduler",
            "2. Create Basic Task → Trigger: Daily, repeat every 5 minutes",
            "3. Action: Start a program",
            f"   Program: {cmd.split()[0]}",
            f"   Arguments: {' '.join(cmd.split()[1:])}",
            f"   Start in: {cwd}",
        ]
    else:
        lines += [f"Run every 5 minutes: {cmd}"]

    return "\n".join(lines)


def _send_beat_summary(
    beat: BeatConfig, result: dict[str, Any], settings: AibaSettings
) -> None:
    """Send a professional HTML email with the beat run summary."""

    if not beat.notify_email or not settings.sender_email:
        return

    status = result["status"]
    subject = f"AIBA Beat: {beat.name} — {status.upper()}"

    # --- Plain text fallback ---
    plain_text = (
        f"Beat: {beat.name}\n"
        f"Status: {status}\n"
        f"Duration: {result.get('duration_s', 0)}s\n"
        f"Cost: ${result.get('cost_usd', 0):.4f}\n"
        f"Tool calls: {result.get('tool_calls', 0)}\n"
        f"Errors: {result.get('errors', [])}\n\n"
        f"---\n\n"
        f"{result.get('output') or '(no output)'}"
    )

    # --- Convert agent markdown output to HTML ---

    raw_output = result.get("output") or ""
    output_html = markdown.markdown(
        raw_output,
        extensions=["fenced_code", "codehilite", "tables", "sane_lists"],
    ) if raw_output else "<p><em>No output</em></p>"

    # --- Build status badge ---
    if status == "success":
        badge_color = "#16a34a"
        badge_bg = "#dcfce7"
        badge_text = "✓ Success"
    elif status == "error":
        badge_color = "#dc2626"
        badge_bg = "#fee2e2"
        badge_text = "✗ Error"
    else:
        badge_color = "#ca8a04"
        badge_bg = "#fef9c3"
        badge_text = "⚠ Skipped"

    # --- Format errors ---
    errors = result.get("errors", [])
    errors_html = ""
    if errors:
        errors_list = "".join(
            f"<li>{e}</li>" for e in errors
        )
        errors_html = f"""
        <tr>
            <td style="padding:12px 0 4px;">
                <h4 style="margin:0 0 6px;color:#991b1b;font-size:14px;">Errors</h4>
            </td>
        </tr>
        <tr>
            <td style="padding:0 0 16px;">
                <ul style="margin:0;padding-left:20px;color:#dc2626;font-size:13px;line-height:1.5;">
                    {errors_list}
                </ul>
            </td>
        </tr>
        """

    # --- Assemble the HTML email ---
    html = f"""\
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background-color:#f4f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f5f7;">
        <tr>
            <td align="center" style="padding:32px 16px;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);">

                    <!-- Header -->
                    <tr>
                        <td style="background:linear-gradient(135deg,#1e3a5f,#2563eb);padding:28px 32px;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="color:#ffffff;font-size:20px;font-weight:700;letter-spacing:-0.3px;">AIBA Beat Report</td>
                                    <td align="right">
                                        <span style="display:inline-block;background:{badge_bg};color:{badge_color};font-size:12px;font-weight:600;padding:4px 12px;border-radius:12px;">{badge_text}</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Metadata -->
                    <tr>
                        <td style="padding:24px 32px 8px;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="padding:6px 0;color:#374151;font-size:13px;line-height:1.5;">
                                        <strong style="color:#6b7280;display:inline-block;width:100px;">Template</strong>
                                        <span style="color:#111827;">{beat.template}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding:6px 0;color:#374151;font-size:13px;line-height:1.5;">
                                        <strong style="color:#6b7280;display:inline-block;width:100px;">Status</strong>
                                        <span style="color:#111827;text-transform:capitalize;">{status}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding:6px 0;color:#374151;font-size:13px;line-height:1.5;">
                                        <strong style="color:#6b7280;display:inline-block;width:100px;">Duration</strong>
                                        <span style="color:#111827;">{result.get('duration_s', 0)}s</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding:6px 0;color:#374151;font-size:13px;line-height:1.5;">
                                        <strong style="color:#6b7280;display:inline-block;width:100px;">Cost</strong>
                                        <span style="color:#111827;">${result.get('cost_usd', 0):.4f}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding:6px 0;color:#374151;font-size:13px;line-height:1.5;">
                                        <strong style="color:#6b7280;display:inline-block;width:100px;">Tool calls</strong>
                                        <span style="color:#111827;">{result.get('tool_calls', 0)}</span>
                                    </td>
                                </tr>
                                {errors_html}
                            </table>
                        </td>
                    </tr>

                    <!-- Divider -->
                    <tr>
                        <td style="padding:0 32px;">
                            <hr style="border:none;border-top:1px solid #e5e7eb;margin:0;">
                        </td>
                    </tr>

                    <!-- Agent Output -->
                    <tr>
                        <td style="padding:24px 32px;">
                            <h3 style="margin:0 0 16px;color:#111827;font-size:16px;font-weight:600;">Agent Output</h3>
                            <div style="color:#374151;font-size:14px;line-height:1.7;word-wrap:break-word;">
                                {output_html}
                            </div>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color:#f9fafb;padding:16px 32px;border-top:1px solid #e5e7eb;">
                            <p style="margin:0;font-size:12px;color:#9ca3af;text-align:center;">
                                Sent by <strong style="color:#6b7280;">AIBA-beat</strong>;
                            </p>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    try:
        msg = EmailMessage()
        msg["From"] = settings.sender_email
        msg["To"] = beat.notify_email
        msg["Subject"] = subject
        msg.set_content(plain_text)
        msg.add_alternative(html, subtype="html")

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
    except Exception:
        pass  # Email failures shouldn't crash the beat run

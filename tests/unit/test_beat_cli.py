"""Tests for beat_cli.py — CLI dispatcher for beat subcommands.

Tests the dispatch logic by monkeypatching sys.argv and capturing stdout.
Agent-invoking commands (run, run --all) need mocking of backend calls.
"""

from __future__ import annotations

import io
import sys
from unittest.mock import patch

# Register templates for any beat validation
from src.prompts.models import Template, register_template
from src.services.beat_cli import beat_cli

_FAKE_TEMPLATES = [
    Template(
        name="default",
        description="Default",
        generate_prompt=lambda p, e: "test",
    ),
]
for _t in _FAKE_TEMPLATES:
    register_template(_t)


# ── Helpers ──────────────────────────────────────────────────────────


def _run_cli(*args: str) -> str:
    """Run beat_cli with given argv tail and return captured stdout."""
    buf = io.StringIO()
    with patch.object(sys, "argv", ["main.py", "beat", *args]):
        with patch("sys.stdout", buf):
            beat_cli()
    return buf.getvalue()


# ── Help / no subcommand ─────────────────────────────────────────────


def test_beat_cli_no_subcommand_shows_help():
    """Running 'python main.py beat' with no subcommand shows usage."""
    out = _run_cli()
    assert "Usage" in out
    assert "beat list" in out
    assert "beat run" in out
    assert "beat schedule" in out


# ── list ─────────────────────────────────────────────────────────────


def test_beat_cli_list_shows_beat_info():
    """'beat list' loads beats.yaml and displays beat information."""
    out = _run_cli("list")
    # Should contain beat info: name, schedule, etc.
    assert "Schedule:" in out
    assert "Mode:" in out
    assert "Template:" in out
    # The real beats.yaml has at least one beat
    assert "agent" in out.lower()


# ── run --all ────────────────────────────────────────────────────────


def test_beat_cli_run_all():
    """'beat run --all' calls run_all_due and prints results."""
    with patch("src.services.beat_cli.run_all_due") as mock_run_all:
        mock_run_all.return_value = [
            {"beat": "b1", "status": "success", "output": "Done"},
            {"beat": "b2", "status": "skipped", "output": "Not due"},
        ]
        out = _run_cli("run", "--all")

    assert "✓" in out  # success marker
    assert "○" in out  # skipped marker
    mock_run_all.assert_called_once()


# ── run <name> ───────────────────────────────────────────────────────


def test_beat_cli_run_named_beat():
    """'beat run <name>' calls run_beat and prints result."""
    with patch("src.services.beat_cli.run_beat") as mock_run_beat:
        mock_run_beat.return_value = {
            "status": "success",
            "output": "All jobs processed.",
            "errors": [],
        }
        out = _run_cli("run", "my-beat")

    assert "✓" in out  # success icon
    assert "my-beat" in out
    mock_run_beat.assert_called_once_with("my-beat")


def test_beat_cli_run_without_target_shows_usage():
    """'beat run' with no target name shows usage message."""
    out = _run_cli("run")
    assert "Usage" in out
    assert "beat run <name>" in out
    assert "beat run --all" in out


def test_beat_cli_run_error_status():
    """'beat run' with an error result shows error details."""
    with patch("src.services.beat_cli.run_beat") as mock_run_beat:
        mock_run_beat.return_value = {
            "status": "error",
            "output": None,
            "errors": ["ConnectionError: timeout"],
        }
        out = _run_cli("run", "failing-beat")

    assert "error" in out
    assert "ConnectionError" in out


# ── schedule ─────────────────────────────────────────────────────────


def test_beat_cli_list_empty_beats():
    """'beat list' with no beats configured shows informational message."""
    with patch("src.services.beat_cli.load_beats", return_value={}):
        out = _run_cli("list")
    assert "No beats configured" in out
    assert "beats.yaml" in out


def test_beat_cli_schedule_shows_instructions():
    """'beat schedule' shows OS-specific scheduler instructions."""
    out = _run_cli("schedule")
    assert len(out) > 0
    # Should contain os-specific guidance
    assert any(
        word in out.lower()
        for word in ["cron", "task", "launchd", "scheduler", "schedule"]
    )

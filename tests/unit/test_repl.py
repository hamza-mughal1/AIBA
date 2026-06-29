"""Tests for repl.py — the interactive REPL loop.

Tests all slash commands, empty input, agent dispatch, and exception handling.
Uses input() side_effect sequences to simulate user interactions.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import ModelRequest, UserPromptPart
from pydantic_ai.usage import UsageLimits

from src.prompts import EffortConfig, EffortMode
from src.services.repl import run

# ── Helpers ──────────────────────────────────────────────────────────


def _make_config(effort_mode: EffortMode = EffortMode.BALANCED) -> EffortConfig:
    """Minimal EffortConfig for REPL tests.

    effort_mode is accepted for caller readability but EffortConfig
    (a TypedDict) has no effort_mode field — the REPL dispatcher
    derives mode from settings, not from config.
    """
    return EffortConfig(
        instructions="Do the task.",
        main_instructions="Orchestrate the swarm.",
        model_settings={},  # type: ignore[typeddict-item]
        usage_limits=UsageLimits(),  # type: ignore[typeddict-item]
    )


def _make_agent_fn(return_value=None):
    """Return a mock agent_fn that returns a fake AgentRunResult."""

    def _agent_fn(
        user_input,
        message_history,
        instructions,
        model_settings,
        usage_limits,
    ):
        result = MagicMock()
        result.output = return_value or f"Response to: {user_input}"
        result.all_messages.return_value = [
            ModelRequest(parts=[UserPromptPart(content=user_input)]),
        ]
        return result

    return _agent_fn


def _make_initial_result():
    """Create a minimal initial AgentRunResult with system prompt."""
    result = MagicMock()
    result.output = "Initial output."
    result.all_messages.return_value = [
        ModelRequest(parts=[UserPromptPart(content="System prompt")]),
    ]
    return result


# ── Slash commands ───────────────────────────────────────────────────


def test_repl_exit_via_exit(capsys):
    """Typing /exit ends the session."""
    with patch("builtins.input", side_effect=["/exit"]):
        run(_make_agent_fn(), _make_initial_result(), _make_config())

    captured = capsys.readouterr()
    assert "Session ended" in captured.out


def test_repl_exit_via_quit(capsys):
    """Typing /quit ends the session."""
    with patch("builtins.input", side_effect=["/quit"]):
        run(_make_agent_fn(), _make_initial_result(), _make_config())

    captured = capsys.readouterr()
    assert "Session ended" in captured.out


def test_repl_exit_via_eof(capsys):
    """EOFError (Ctrl+D) ends the session."""
    with patch("builtins.input", side_effect=EOFError):
        run(_make_agent_fn(), _make_initial_result(), _make_config())

    captured = capsys.readouterr()
    assert "Session ended" in captured.out


def test_repl_exit_via_keyboard_interrupt(capsys):
    """KeyboardInterrupt (Ctrl+C) ends the session."""
    with patch("builtins.input", side_effect=KeyboardInterrupt):
        run(_make_agent_fn(), _make_initial_result(), _make_config())

    captured = capsys.readouterr()
    assert "Session ended" in captured.out


def test_repl_empty_input_continues(capsys):
    """Empty input is ignored and loop continues."""
    # Two empty inputs then exit
    with patch("builtins.input", side_effect=["", "   ", "/exit"]):
        run(_make_agent_fn(), _make_initial_result(), _make_config())

    captured = capsys.readouterr()
    assert "Session ended" in captured.out


def test_repl_clear_resets_history(capsys):
    """'/clear' resets history to system prompt only."""
    with patch("builtins.input", side_effect=["/clear", "/exit"]):
        run(_make_agent_fn(), _make_initial_result(), _make_config())

    captured = capsys.readouterr()
    assert "History cleared" in captured.out


def test_repl_history_shows_count(capsys):
    """'/history' shows the number of messages in history."""
    with patch("builtins.input", side_effect=["/history", "/exit"]):
        run(_make_agent_fn(), _make_initial_result(), _make_config())

    captured = capsys.readouterr()
    assert "Messages in history" in captured.out


def test_repl_help(capsys):
    """'/help' shows the help text."""
    with patch("builtins.input", side_effect=["/help", "/exit"]):
        run(_make_agent_fn(), _make_initial_result(), _make_config())

    captured = capsys.readouterr()
    assert "/exit" in captured.out


def test_repl_unknown_slash_command(capsys):
    """An unknown /command shows an error and help."""
    with patch("builtins.input", side_effect=["/foobar", "/exit"]):
        run(_make_agent_fn(), _make_initial_result(), _make_config())

    captured = capsys.readouterr()
    assert "Unknown command" in captured.out


def test_repl_save_without_name_shows_usage(capsys):
    """'/save' with a name that resolves to empty stem shows usage."""
    # Path(".").stem == "" — triggers the "no name" usage path
    with patch("builtins.input", side_effect=["/save .", "/exit"]):
        run(_make_agent_fn(), _make_initial_result(), _make_config())

    captured = capsys.readouterr()
    assert "Usage" in captured.out


def test_repl_save_success(capsys):
    """'/save <name>' calls save_session and prints confirmation."""
    with patch("builtins.input", side_effect=["/save my-session", "/exit"]):
        with patch("src.services.repl.save_session") as mock_save:
            run(_make_agent_fn(), _make_initial_result(), _make_config())

    captured = capsys.readouterr()
    assert "Session saved" in captured.out
    mock_save.assert_called_once()


def test_repl_save_failure(capsys):
    """'/save' failure prints error without crashing."""
    with (
        patch("builtins.input", side_effect=["/save bad", "/exit"]),
        patch(
            "src.services.repl.save_session",
            side_effect=RuntimeError("disk full"),
        ),
    ):
        run(_make_agent_fn(), _make_initial_result(), _make_config())

    captured = capsys.readouterr()
    assert "Failed to save" in captured.out


# ── Agent dispatch ───────────────────────────────────────────────────


def test_repl_normal_message_agent_mode(capsys):
    """Normal text is dispatched to agent_fn in agent mode."""
    agent_fn = _make_agent_fn(return_value="Here is the answer.")

    with patch("builtins.input", side_effect=["do something", "/exit"]):
        run(agent_fn, _make_initial_result(), _make_config(), agent_name="Agent")

    captured = capsys.readouterr()
    assert "Here is the answer." in captured.out


def test_repl_normal_message_orchestrator_mode(capsys):
    """Normal text is dispatched with main_instructions for Orchestrator."""
    agent_fn = _make_agent_fn(return_value="Orchestrated result.")

    with patch("builtins.input", side_effect=["delegate task", "/exit"]):
        run(agent_fn, _make_initial_result(), _make_config(), agent_name="Orchestrator")

    captured = capsys.readouterr()
    assert "Orchestrated result." in captured.out


def test_repl_usage_limit_exceeded(capsys):
    """UsageLimitExceeded shows a warning without crashing."""

    def _failing_agent(*args, **kwargs):
        raise UsageLimitExceeded("Token budget exhausted")

    with patch("builtins.input", side_effect=["big task", "/exit"]):
        run(_failing_agent, _make_initial_result(), _make_config())

    captured = capsys.readouterr()
    assert "Resource limit hit" in captured.out


def test_repl_generic_exception(capsys):
    """A generic exception during agent run shows error without crashing."""

    def _failing_agent(*args, **kwargs):
        raise ValueError("something went wrong")

    with patch("builtins.input", side_effect=["bad task", "/exit"]):
        run(_failing_agent, _make_initial_result(), _make_config())

    captured = capsys.readouterr()
    assert "ValueError" in captured.out


def test_repl_session_settings_default(capsys):
    """When session_settings is None, it defaults to empty dict."""
    with patch("builtins.input", side_effect=["/exit"]):
        run(
            _make_agent_fn(),
            _make_initial_result(),
            _make_config(),
            session_settings=None,
        )

    captured = capsys.readouterr()
    assert "Session started" in captured.out
    assert "Session ended" in captured.out

"""Tests for screens.py — the interactive setup wizard screens.

Tests all 7 screen functions: session, mode, template, effort,
sub_agents, prompt, confirm.
"""

from __future__ import annotations

from unittest.mock import patch

from pydantic_ai.messages import ModelRequest, UserPromptPart

from src.prompts import EffortMode
from src.services.screens import (
    confirm,
    effort,
    mode,
    prompt,
    session,
    sub_agents,
    template,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _input_sequence(*values: str):
    """Patch input() to return values in order, then raise EOFError."""
    return patch("builtins.input", side_effect=[*values])


# ═════════════════════════════════════════════════════════════════════
#  mode()
# ═════════════════════════════════════════════════════════════════════


class TestMode:
    """Step 1 — mode selection."""

    def test_mode_agent(self):
        with _input_sequence("1"):
            assert mode() == "agent"

    def test_mode_swarm(self):
        with _input_sequence("2"):
            assert mode() == "swarm"

    def test_mode_invalid_then_agent(self):
        """Invalid inputs loop until valid."""
        with _input_sequence("3", "abc", "", "1"):
            assert mode() == "agent"

    def test_mode_invalid_then_swarm(self):
        with _input_sequence("0", "-1", "2"):
            assert mode() == "swarm"

    def test_mode_invalid_prints_error(self, capsys):
        with _input_sequence("5", "1"):
            mode()
        out = capsys.readouterr().out
        assert "Invalid" in out


# ═════════════════════════════════════════════════════════════════════
#  template()
# ═════════════════════════════════════════════════════════════════════


class TestTemplate:
    """Step 2 — template selection."""

    def test_template_select_first(self):
        with _input_sequence("1"):
            result = template()
        assert result in ("default", "general_browsing")

    def test_template_select_last(self):
        """Pick the last template (index = len)."""
        from src.prompts import list_templates

        tmpls = list_templates()
        with _input_sequence(str(len(tmpls))):
            result = template()
        assert result == tmpls[-1].name

    def test_template_invalid_then_valid(self):
        with _input_sequence("999", "abc", "1"):
            result = template()
        from src.prompts import list_templates

        assert result == list_templates()[0].name

    def test_template_negative_index(self):
        with _input_sequence("-1", "1"):
            result = template()
        from src.prompts import list_templates

        assert result == list_templates()[0].name

    def test_template_zero_index(self):
        with _input_sequence("0", "1"):
            result = template()
        from src.prompts import list_templates

        assert result == list_templates()[0].name

    def test_template_invalid_prints_error(self, capsys):
        with _input_sequence("99", "1"):
            template()
        out = capsys.readouterr().out
        assert "Invalid" in out

    def test_template_long_word_wrapping(self, capsys):
        """Trigger cut==-1 fallback by making terminal too narrow to wrap."""
        with patch("shutil.get_terminal_size") as mock_size:
            mock_size.return_value.columns = 20
            with _input_sequence("1"):
                template()
        out = capsys.readouterr().out
        # Should still complete without error — the long-word fallback worked
        assert "Invalid" not in out


# ═════════════════════════════════════════════════════════════════════
#  effort()
# ═════════════════════════════════════════════════════════════════════


class TestEffort:
    """Step 3 — effort level selection."""

    def test_effort_quick(self):
        with _input_sequence("1"):
            assert effort() == EffortMode.QUICK

    def test_effort_balanced(self):
        with _input_sequence("2"):
            assert effort() == EffortMode.BALANCED

    def test_effort_max(self):
        with _input_sequence("3"):
            assert effort() == EffortMode.MAX

    def test_effort_invalid_then_valid(self):
        with _input_sequence("", "abc", "99", "1"):
            assert effort() == EffortMode.QUICK

    def test_effort_invalid_prints_error(self, capsys):
        with _input_sequence("5", "1"):
            effort()
        out = capsys.readouterr().out
        assert "Invalid" in out


# ═════════════════════════════════════════════════════════════════════
#  sub_agents()
# ═════════════════════════════════════════════════════════════════════


class TestSubAgents:
    """Step 4 — sub-agent pool size (swarm only)."""

    def test_sub_agents_default(self):
        with _input_sequence(""):
            result = sub_agents()
        assert isinstance(result, int)
        assert result >= 1

    def test_sub_agents_valid_number(self):
        with _input_sequence("5"):
            assert sub_agents() == 5

    def test_sub_agents_min_boundary(self):
        with _input_sequence("1"):
            assert sub_agents() == 1

    def test_sub_agents_max_boundary(self):
        with _input_sequence("50"):
            assert sub_agents() == 50

    def test_sub_agents_below_min(self):
        with _input_sequence("0", "3"):
            assert sub_agents() == 3

    def test_sub_agents_above_max(self):
        with _input_sequence("51", "3"):
            assert sub_agents() == 3

    def test_sub_agents_non_numeric(self):
        with _input_sequence("abc", "3"):
            assert sub_agents() == 3

    def test_sub_agents_out_of_range_prints_error(self, capsys):
        with _input_sequence("0", "1"):
            sub_agents()
        out = capsys.readouterr().out
        assert "Must be between 1 and 50" in out

    def test_sub_agents_non_numeric_prints_error(self, capsys):
        with _input_sequence("xyz", "1"):
            sub_agents()
        out = capsys.readouterr().out
        assert "Enter a number" in out


# ═════════════════════════════════════════════════════════════════════
#  prompt()
# ═════════════════════════════════════════════════════════════════════


class TestPrompt:
    """Step N — extra notes."""

    def test_prompt_agent_mode_empty(self):
        """Two empty lines: first appended, second breaks the loop."""
        with _input_sequence("", ""):
            result = prompt("agent")
        assert result == ""

    def test_prompt_swarm_mode_empty(self):
        with _input_sequence("", ""):
            result = prompt("swarm")
        assert result == ""

    def test_prompt_single_line_then_empty(self):
        with _input_sequence("extra note", ""):
            result = prompt("agent")
        assert result == "extra note"

    def test_prompt_multiple_lines(self):
        with _input_sequence("first line", "second line", ""):
            result = prompt("agent")
        assert result == "first line\nsecond line"

    def test_prompt_eof_returns_collected(self):
        """EOFError returns whatever was collected so far."""
        with patch("builtins.input", side_effect=EOFError):
            result = prompt("agent")
        assert result == ""

    def test_prompt_eof_after_lines(self):
        with patch("builtins.input", side_effect=["hello", EOFError]):
            result = prompt("agent")
        assert result == "hello"

    def test_prompt_strips_result(self):
        """Final .strip() removes leading/trailing whitespace from result."""
        with _input_sequence("  note with spaces  ", ""):
            result = prompt("agent")
        # The .strip() on the joined result strips outer whitespace
        assert result == "note with spaces"

    def test_prompt_agent_step_label(self, capsys):
        """Agent mode shows '4 of 4'."""
        with _input_sequence("", ""):
            prompt("agent")
        out = capsys.readouterr().out
        assert "4 of 4" in out

    def test_prompt_swarm_step_label(self, capsys):
        """Swarm mode shows '5 of 5'."""
        with _input_sequence("", ""):
            prompt("swarm")
        out = capsys.readouterr().out
        assert "5 of 5" in out


# ═════════════════════════════════════════════════════════════════════
#  confirm()
# ═════════════════════════════════════════════════════════════════════


class TestConfirm:
    """Launch summary."""

    def test_confirm_agent_mode(self, capsys):
        confirm("agent", 0, "test prompt")
        out = capsys.readouterr().out
        assert "Launch Summary" in out
        assert "AGENT" in out

    def test_confirm_swarm_mode(self, capsys):
        confirm("swarm", 5, "test prompt")
        out = capsys.readouterr().out
        assert "SWARM" in out
        assert "5" in out

    def test_confirm_long_prompt_truncated(self, capsys):
        long_prompt = "x" * 200
        confirm("agent", 0, long_prompt)
        out = capsys.readouterr().out
        assert "…" in out
        assert "x" * 100 in out
        assert "x" * 101 not in out


# ═════════════════════════════════════════════════════════════════════
#  session()
# ═════════════════════════════════════════════════════════════════════


class TestSession:
    """Pre-flight session loader."""

    def test_session_no(self):
        with _input_sequence("n"):
            assert session() is None

    def test_session_no_uppercase(self):
        with _input_sequence("N"):
            assert session() is None

    def test_session_empty_is_no(self):
        with _input_sequence(""):
            assert session() is None

    def test_session_yes_then_no_sessions(self):
        with (
            patch("src.services.screens.list_sessions", return_value=[]),
            _input_sequence("y"),
        ):
            assert session() is None

    def test_session_invalid_choice_then_no(self, capsys):
        with _input_sequence("maybe", "n"):
            assert session() is None
        out = capsys.readouterr().out
        assert "Type 'y' or 'n'" in out

    def test_session_yes_select_first_with_saved_settings(self):
        fake_history = [ModelRequest(parts=[UserPromptPart(content="hi")])]
        fake_settings = {
            "mode": "swarm",
            "effort": "max",
            "template_name": "osint",
            "sub_agent_count": 10,
        }
        with (
            patch("src.services.screens.list_sessions", return_value=["session_a"]),
            patch(
                "src.services.screens.load_session",
                return_value=(fake_history, fake_settings),
            ),
            _input_sequence("y", "1"),
        ):
            result = session()
        assert result is not None
        history, agent_fn, agent_name, _, sess_settings = result
        assert history == fake_history
        assert agent_name == "Orchestrator"
        assert sess_settings == fake_settings
        # In swarm mode, agent_fn should point to run_agent (orchestrator)
        assert callable(agent_fn)

    def test_session_yes_select_agent_mode_with_saved_settings(self):
        fake_history = []
        fake_settings = {
            "mode": "agent",
            "effort": "quick",
            "template_name": "default",
        }
        with (
            patch("src.services.screens.list_sessions", return_value=["session_b"]),
            patch(
                "src.services.screens.load_session",
                return_value=(fake_history, fake_settings),
            ),
            _input_sequence("y", "1"),
        ):
            result = session()
        assert result is not None
        _, agent_fn, agent_name, _, _ = result
        assert agent_name == "Agent"
        assert callable(agent_fn)

    def test_session_yes_select_with_invalid_effort_fallback(self):
        fake_history = []
        fake_settings = {
            "mode": "agent",
            "effort": "invalid_effort",
            "template_name": "default",
        }
        with (
            patch("src.services.screens.list_sessions", return_value=["session_c"]),
            patch(
                "src.services.screens.load_session",
                return_value=(fake_history, fake_settings),
            ),
            _input_sequence("y", "1"),
        ):
            result = session()
        assert result is not None
        _, _, _, config, _ = result
        # config is a dict from get_effort_config; invalid effort falls
        # back to BALANCED, which has temperature 0.5 and timeout 60.
        assert config["model_settings"].get("temperature") == 0.5  # pyright: ignore[reportOptionalMemberAccess]
        assert config["model_settings"].get("timeout") == 60.0  # pyright: ignore[reportOptionalMemberAccess]

    def test_session_yes_select_no_saved_settings_agent_default(self):
        fake_history = []
        fake_settings = {}  # No saved settings
        with (
            patch("src.services.screens.list_sessions", return_value=["session_d"]),
            patch(
                "src.services.screens.load_session",
                return_value=(fake_history, fake_settings),
            ),
            _input_sequence("y", "1", ""),
        ):
            result = session()
        assert result is not None
        _, _, agent_name, _, _ = result
        assert agent_name == "Agent"

    def test_session_yes_select_no_saved_settings_orchestrator(self):
        fake_history = []
        fake_settings = {}
        with (
            patch("src.services.screens.list_sessions", return_value=["session_e"]),
            patch(
                "src.services.screens.load_session",
                return_value=(fake_history, fake_settings),
            ),
            _input_sequence("y", "1", "orch"),
        ):
            result = session()
        assert result is not None
        _, _, agent_name, _, _ = result
        assert agent_name == "Orchestrator"

    def test_session_load_failure(self, capsys):
        with (
            patch("src.services.screens.list_sessions", return_value=["bad_session"]),
            patch(
                "src.services.screens.load_session",
                side_effect=RuntimeError("corrupt file"),
            ),
            _input_sequence("y", "1"),
        ):
            result = session()
        assert result is None
        out = capsys.readouterr().out
        assert "Failed to load" in out
        assert "corrupt file" in out

    def test_session_yes_invalid_selection_then_valid(self):
        fake_history = []
        fake_settings = {
            "mode": "agent",
            "effort": "balanced",
            "template_name": "default",
        }
        with (
            patch("src.services.screens.list_sessions", return_value=["a", "b"]),
            patch(
                "src.services.screens.load_session",
                return_value=(fake_history, fake_settings),
            ),
            _input_sequence("y", "abc", "99", "", "2"),
        ):
            result = session()
        assert result is not None
        assert result[2] == "Agent"

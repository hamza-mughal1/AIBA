"""Tests for main_agent.py — orchestrator run() and tool functions.

Uses pydantic-ai's TestModel to mock the LLM so no real API calls are made.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from pydantic_ai import capture_run_messages, models
from pydantic_ai.models.test import TestModel

from src.agents.main_agent import main_agent, run, send_email, spawn_sub_agents
from src.prompts import EffortMode

# ── Helpers ──────────────────────────────────────────────────────────


def _run_agent(
    prompt: str = "Do a research task",
    effort_mode: EffortMode = EffortMode.BALANCED,
    output_text: str = "orchestrator result",
    **kwargs,
):
    """Run the main_agent with TestModel override and return the result."""
    models.ALLOW_MODEL_REQUESTS = False
    with main_agent.override(
        model=TestModel(custom_output_text=output_text, call_tools=[]),
    ):
        return run(prompt, effort_mode=effort_mode, **kwargs)


# ═════════════════════════════════════════════════════════════════════
#  run() — effort modes
# ═════════════════════════════════════════════════════════════════════


class TestRunEffortModes:
    """Test that each effort mode produces a successful result."""

    def test_run_default_balanced(self):
        result = _run_agent(effort_mode=EffortMode.BALANCED)
        assert result.output == "orchestrator result"

    def test_run_quick(self):
        result = _run_agent(effort_mode=EffortMode.QUICK, output_text="quick")
        assert result.output == "quick"

    def test_run_max(self):
        result = _run_agent(effort_mode=EffortMode.MAX, output_text="max effort")
        assert result.output == "max effort"


# ═════════════════════════════════════════════════════════════════════
#  run() — kwargs override
# ═════════════════════════════════════════════════════════════════════


class TestRunKwargs:
    """Test that kwargs override config-derived defaults."""

    def test_kwargs_override_model_settings(self):
        """Custom model_settings passed via kwargs take precedence."""
        result = _run_agent(
            model_settings={"temperature": 0.9, "max_tokens": 100},
            output_text="custom settings",
        )
        assert result.output == "custom settings"

    def test_kwargs_override_instructions(self):
        """Custom instructions passed via kwargs take precedence."""
        result = _run_agent(
            instructions="Custom orchestration instructions.",
            output_text="custom instructions",
        )
        assert result.output == "custom instructions"

    def test_kwargs_override_usage_limits(self):
        """Custom usage_limits passed via kwargs work."""
        from pydantic_ai.usage import UsageLimits

        result = _run_agent(
            usage_limits=UsageLimits(request_limit=5),
            output_text="limited",
        )
        assert result.output == "limited"


# ═════════════════════════════════════════════════════════════════════
#  run() — capture messages
# ═════════════════════════════════════════════════════════════════════


class TestRunMessages:
    """Test that run() produces expected message flow."""

    def test_captures_messages(self):
        models.ALLOW_MODEL_REQUESTS = False
        with (
            capture_run_messages() as msgs,
            main_agent.override(
                model=TestModel(custom_output_text="msg result", call_tools=[]),
            ),
        ):
            result = run("test prompt")
        assert result.output == "msg result"
        assert len(msgs) >= 2  # At least request + response
        from pydantic_ai.messages import ModelRequest, ModelResponse

        assert isinstance(msgs[0], ModelRequest)
        assert isinstance(msgs[-1], ModelResponse)

    def test_prompt_in_messages(self):
        models.ALLOW_MODEL_REQUESTS = False
        with (
            capture_run_messages() as msgs,
            main_agent.override(
                model=TestModel(custom_output_text="found", call_tools=[]),
            ),
        ):
            run("find me something")
        # First message should contain our prompt
        first = msgs[0]
        assert hasattr(first, "parts")
        contents = [getattr(p, "content", None) for p in first.parts]
        assert "find me something" in contents


# ═════════════════════════════════════════════════════════════════════
#  send_email tool
# ═════════════════════════════════════════════════════════════════════


class TestSendEmail:
    """Test the send_email tool_plain function directly."""

    def test_send_email_success(self):
        with patch("smtplib.SMTP"):
            result = send_email("a@b.com", "Subject", "Body")
        assert "Email sent successfully" in result

    def test_send_email_failure(self):
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = OSError("connection refused")
            result = send_email("a@b.com", "Subject", "Body")
        assert "Email failed" in result
        assert "connection refused" in result

    def test_send_email_with_attachment(self, tmp_path):
        """send_email with an existing attachment file."""
        import src.agents.main_agent as mod

        static_dir = tmp_path / "static"
        static_dir.mkdir()
        (static_dir / "report.pdf").write_bytes(b"fake pdf content")

        with patch.object(mod, "STATIC_DIR", static_dir), patch("smtplib.SMTP"):
            result = send_email(
                "a@b.com",
                "Subject",
                "Body",
                attachment_filename="report.pdf",
            )
        assert "Email sent successfully" in result

    def test_send_email_missing_attachment(self, tmp_path):
        """send_email with a non-existent attachment file."""
        import src.agents.main_agent as mod

        static_dir = tmp_path / "static"
        static_dir.mkdir()

        with patch.object(mod, "STATIC_DIR", static_dir):
            result = send_email(
                "a@b.com",
                "Subject",
                "Body",
                attachment_filename="missing.pdf",
            )
        assert "ERROR" in result
        assert "missing.pdf" in result

    def test_send_email_no_static_dir(self, tmp_path):
        """send_email with attachment when static/ doesn't exist."""
        import src.agents.main_agent as mod

        with patch.object(mod, "STATIC_DIR", tmp_path / "nonexistent"):
            result = send_email(
                "a@b.com",
                "Subject",
                "Body",
                attachment_filename="report.pdf",
            )
        assert "ERROR" in result


# ═════════════════════════════════════════════════════════════════════
#  spawn_sub_agents tool
# ═════════════════════════════════════════════════════════════════════


class TestSpawnSubAgents:
    """Test the spawn_sub_agents async tool."""

    def test_empty_sub_agents(self):
        result = asyncio.run(spawn_sub_agents([]))
        assert result == "No sub-agent tasks to execute."

    def test_single_sub_agent(self):
        """spawn_sub_agents with one task — mock sub_agent.run to avoid MCP init."""
        from unittest.mock import AsyncMock, MagicMock

        from src.agents.sub_agent import sub_agent

        fake_result = MagicMock()
        fake_result.output = "sub result"

        with patch.object(sub_agent, "run", AsyncMock(return_value=fake_result)):
            result = asyncio.run(spawn_sub_agents(["find info"]))
        assert "=== SUB-AGENT 1 RESULT ===" in result
        assert "sub result" in result

    def test_multiple_sub_agents(self):
        """spawn_sub_agents with multiple tasks — mock sub_agent.run."""
        from unittest.mock import AsyncMock, MagicMock

        from src.agents.sub_agent import sub_agent

        def _fake(*args, **kwargs):
            r = MagicMock()
            r.output = "multi result"
            return r

        with patch.object(sub_agent, "run", AsyncMock(side_effect=_fake)):
            result = asyncio.run(spawn_sub_agents(["task A", "task B", "task C"]))
        assert "=== SUB-AGENT 1 RESULT ===" in result
        assert "=== SUB-AGENT 2 RESULT ===" in result
        assert "=== SUB-AGENT 3 RESULT ===" in result
        assert "multi result" in result

    def test_sub_agent_timeout(self):
        """spawn_sub_agents where sub_agent.run times out."""
        from unittest.mock import AsyncMock

        import src.agents.main_agent as mod
        from src.agents.sub_agent import sub_agent

        async def _slow(*args, **kwargs):
            await asyncio.sleep(10)

        with patch.object(mod._settings, "request_timeout_seconds", 0.001):
            with patch.object(sub_agent, "run", AsyncMock(side_effect=_slow)):
                result = asyncio.run(spawn_sub_agents(["timeout task"]))
        assert "=== SUB-AGENT 1 ERROR ===" in result
        assert "timed out" in result.lower()

    def test_sub_agent_exception_during_run(self):
        """spawn_sub_agents where sub_agent raises an exception."""
        from unittest.mock import AsyncMock

        from src.agents.sub_agent import sub_agent

        with patch.object(
            sub_agent, "run", AsyncMock(side_effect=RuntimeError("boom"))
        ):
            result = asyncio.run(spawn_sub_agents(["crash task"]))
        assert "=== SUB-AGENT 1 ERROR ===" in result
        assert "RuntimeError" in result
        assert "boom" in result

"""Tests for sub_agent.py — sub-agent run() and tool functions.

Uses pydantic-ai's TestModel to mock the LLM so no real API calls are made.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic_ai import capture_run_messages, models
from pydantic_ai.models.test import TestModel

from src.agents.sub_agent import (
    read_and_filter_file,
    read_image,
    run,
    sub_agent,
)
from src.prompts import EffortMode

# ── Helpers ──────────────────────────────────────────────────────────


def _run_agent(
    prompt: str = "Research this topic",
    effort_mode: EffortMode = EffortMode.BALANCED,
    output_text: str = "sub-agent result",
    **kwargs,
):
    """Run the sub_agent with TestModel override and return the result."""
    models.ALLOW_MODEL_REQUESTS = False
    with sub_agent.override(
        model=TestModel(custom_output_text=output_text, call_tools=[]),
        native_tools=[],
    ):
        return run(prompt, effort_mode=effort_mode, **kwargs)


# ═════════════════════════════════════════════════════════════════════
#  run() — effort modes
# ═════════════════════════════════════════════════════════════════════


class TestRunEffortModes:
    """Test that each effort mode produces a successful result."""

    def test_run_default_balanced(self):
        result = _run_agent(effort_mode=EffortMode.BALANCED)
        assert result.output == "sub-agent result"

    def test_run_quick(self):
        result = _run_agent(effort_mode=EffortMode.QUICK, output_text="quick search")
        assert result.output == "quick search"

    def test_run_max(self):
        result = _run_agent(effort_mode=EffortMode.MAX, output_text="deep dive")
        assert result.output == "deep dive"


# ═════════════════════════════════════════════════════════════════════
#  run() — kwargs override
# ═════════════════════════════════════════════════════════════════════


class TestRunKwargs:
    """Test that kwargs override config-derived defaults."""

    def test_kwargs_override_model_settings(self):
        result = _run_agent(
            model_settings={"temperature": 0.1, "max_tokens": 50},
            output_text="custom settings",
        )
        assert result.output == "custom settings"

    def test_kwargs_override_instructions(self):
        result = _run_agent(
            instructions="Investigate deeply.",
            output_text="custom instructions",
        )
        assert result.output == "custom instructions"
        first_msg = result.all_messages()[0]
        assert hasattr(first_msg, "instructions")
        assert "Investigate deeply." in (first_msg.instructions or "")  # type: ignore[union-attr]

    def test_kwargs_override_usage_limits(self):
        from pydantic_ai.usage import UsageLimits

        result = _run_agent(
            usage_limits=UsageLimits(request_limit=3),
            output_text="limited run",
        )
        assert result.output == "limited run"


# ═════════════════════════════════════════════════════════════════════
#  run() — capture messages
# ═════════════════════════════════════════════════════════════════════


class TestRunMessages:
    """Test that run() produces expected message flow."""

    def test_captures_messages(self):
        models.ALLOW_MODEL_REQUESTS = False
        with (
            capture_run_messages() as msgs,
            sub_agent.override(
                model=TestModel(custom_output_text="msg result", call_tools=[]),
                native_tools=[],
            ),
        ):
            result = run("test prompt")
        assert result.output == "msg result"
        assert len(msgs) >= 2
        from pydantic_ai.messages import ModelRequest, ModelResponse

        assert isinstance(msgs[0], ModelRequest)
        assert isinstance(msgs[-1], ModelResponse)

    def test_prompt_in_messages(self):
        models.ALLOW_MODEL_REQUESTS = False
        with (
            capture_run_messages() as msgs,
            sub_agent.override(
                model=TestModel(custom_output_text="done", call_tools=[]),
                native_tools=[],
            ),
        ):
            run("specific investigation prompt")
        first = msgs[0]
        contents = [getattr(p, "content", None) for p in first.parts]
        assert "specific investigation prompt" in contents

    def test_instructions_in_messages(self):
        models.ALLOW_MODEL_REQUESTS = False
        with (
            capture_run_messages() as msgs,
            sub_agent.override(
                model=TestModel(custom_output_text="done", call_tools=[]),
                native_tools=[],
            ),
        ):
            run("prompt", instructions="focus on accuracy")
        first = msgs[0]
        assert hasattr(first, "instructions")
        assert "focus on accuracy" in (first.instructions or "")  # type: ignore[union-attr]


# ═════════════════════════════════════════════════════════════════════
#  read_image tool
# ═════════════════════════════════════════════════════════════════════


class TestReadImage:
    """Test the read_image tool_plain function directly."""

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="No image found"):
            read_image("/nonexistent/image.png")

    def test_reads_valid_image(self, tmp_path):
        """Read a real PNG file."""
        png_path = tmp_path / "test.png"
        # Minimal valid PNG file header
        png_bytes = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05"
            b"\x18\xd8N"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        png_path.write_bytes(png_bytes)

        result = read_image(str(png_path))
        from pydantic_ai import ToolReturn

        assert isinstance(result, ToolReturn)

    def test_non_image_extension(self, tmp_path):
        """File with non-image extension defaults to image/png."""
        txt_path = tmp_path / "data.bin"
        txt_path.write_bytes(b"fake data")
        result = read_image(str(txt_path))
        from pydantic_ai import ToolReturn

        assert isinstance(result, ToolReturn)


# ═════════════════════════════════════════════════════════════════════
#  read_and_filter_file tool
# ═════════════════════════════════════════════════════════════════════


class TestReadAndFilterFile:
    """Test the read_and_filter_file tool_plain function directly."""

    @pytest.fixture
    def sample_file(self, tmp_path):
        """Create a sample text file with multiple lines."""
        content = (
            "apple pie recipe\n"
            "banana bread recipe\n"
            "cherry pie recipe\n"
            "date pudding recipe\n"
            "elderberry jam\n"
        )
        f = tmp_path / "recipes.txt"
        f.write_text(content)
        return str(f)

    def test_read_all_lines(self, sample_file):
        result = read_and_filter_file(sample_file)
        assert "apple pie" in result
        assert "elderberry jam" in result

    def test_line_range(self, sample_file):
        result = read_and_filter_file(sample_file, start_line=2, end_line=3)
        assert "apple" not in result  # line 1 excluded
        assert "banana bread" in result
        assert "cherry pie" in result
        assert "date" not in result  # line 4 excluded

    def test_search_string(self, sample_file):
        result = read_and_filter_file(sample_file, search_string="pie")
        assert "apple pie" in result
        assert "cherry pie" in result
        assert "banana" not in result
        assert "elderberry" not in result

    def test_search_regex(self, sample_file):
        result = read_and_filter_file(sample_file, search_regex=r"^[a-c]")
        assert "apple pie" in result
        assert "banana bread" in result
        assert "cherry pie" in result
        assert "date" not in result

    def test_combined_filters(self, sample_file):
        """Line range + search string combined."""
        result = read_and_filter_file(
            sample_file,
            start_line=2,
            end_line=4,
            search_string="pie",
        )
        # Only lines 2-4 containing "pie" → just line 3 (cherry pie)
        assert "cherry pie" in result
        assert "apple pie" not in result  # line 1 out of range
        assert "date" not in result

    def test_no_matches(self, sample_file):
        result = read_and_filter_file(sample_file, search_string="zzz_nonexistent")
        assert result == "No matching lines found based on the provided filters."

    def test_file_not_found(self):
        result = read_and_filter_file("/nonexistent/file.txt")
        assert result.startswith("Error: File not found")

    def test_invalid_regex(self, sample_file):
        result = read_and_filter_file(sample_file, search_regex="[invalid")
        assert result.startswith("Error: Invalid regular expression")

    def test_end_line_none(self, sample_file):
        """end_line=None means read to end."""
        result = read_and_filter_file(sample_file, start_line=4, end_line=None)
        assert "date pudding" in result
        assert "elderberry jam" in result
        assert "apple" not in result

    def test_start_line_none(self, sample_file):
        """start_line=None means read from beginning."""
        result = read_and_filter_file(sample_file, start_line=None, end_line=2)
        assert "apple pie" in result
        assert "banana bread" in result
        assert "cherry" not in result

    def test_read_error_during_open(self, tmp_path):
        """read_text raises an exception — covered by the generic except.

        The file must exist (so is_file passes) but read_text must fail.
        """
        real_file = tmp_path / "corrupt.txt"
        real_file.write_text("will fail to read")
        # Patch read_text on the Path class to raise even though file exists
        with patch.object(Path, "read_text", side_effect=PermissionError("denied")):
            result = read_and_filter_file(str(real_file))
        assert result.startswith("Error reading file:")
        assert "denied" in result


# ═════════════════════════════════════════════════════════════════════
#  web_search engine config branch (module-level if/else at import)
# ═════════════════════════════════════════════════════════════════════


class TestWebSearchConfig:
    """Cover the else branch when web_search_engine is NOT duckduckgo."""

    def test_non_duckduckgo_engine_fallback(self):
        """Setting WEB_SEARCH_ENGINE=google + reload hits the else branch."""
        import importlib

        import src.agents.sub_agent as mod

        old_val = os.environ.get("WEB_SEARCH_ENGINE")
        os.environ["WEB_SEARCH_ENGINE"] = "google"
        try:
            importlib.reload(mod)
            from pydantic_ai.capabilities import WebSearch

            assert isinstance(mod._web_search_cap, WebSearch)
        finally:
            # Restore env and module state so other tests aren't affected
            if old_val is None:
                del os.environ["WEB_SEARCH_ENGINE"]
            else:
                os.environ["WEB_SEARCH_ENGINE"] = old_val
            importlib.reload(mod)

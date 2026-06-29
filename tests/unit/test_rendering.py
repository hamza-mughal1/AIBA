from __future__ import annotations

import pytest

from src.services.rendering import C, badge, hr, render_markdown

# ── C palette ────────────────────────────────────────────────────────

_REQUIRED_TOKENS = ("reset", "bold", "dim", "purple", "teal", "green", "yellow", "red")


def test_c_palette_has_all_tokens():
    for token in _REQUIRED_TOKENS:
        assert token in C, f"Missing ANSI token: {token}"


def test_c_values_are_non_empty():
    for token in _REQUIRED_TOKENS:
        assert len(C[token]) > 0, f"ANSI token '{token}' is empty"


# ── badge ────────────────────────────────────────────────────────────


def test_badge_contains_both_strings():
    result = badge("Mode", "swarm")
    assert "Mode" in result
    assert "swarm" in result


# ── hr ───────────────────────────────────────────────────────────────


def test_hr_returns_string():
    result = hr()
    assert isinstance(result, str)
    assert len(result) > 0


def test_hr_respects_custom_char():
    result = hr(char="=")
    assert "=" in result


# ── render_markdown (smoke) ──────────────────────────────────────────


def test_render_markdown_does_not_raise():
    """Smoke test: render_markdown must not crash on basic Markdown."""
    try:
        render_markdown(text="**hello**")
    except Exception as exc:
        pytest.fail(f"render_markdown raised: {exc}")

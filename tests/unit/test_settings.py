"""Tests for AibaSettings — defaults, validation, and env overrides.

The conftest ``_suppress_dotenv`` fixture clears all AIBA_* env vars,
sets ``GEMINI_API_KEY=test-key``, and points ``env_file`` to a nonexistent
path.  This means ``AibaSettings()`` (no arguments) returns clean
Field() defaults — exactly what we want to test.
"""

from __future__ import annotations

import pytest

from src.utils.settings import AibaSettings

# ── Defaults ────────────────────────────────────────────────────────


def test_gemini_main_model_default():
    s = AibaSettings()  # type: ignore[call-arg]
    assert s.gemini_main_model == "gemini-3.5-flash"


def test_gemini_sub_model_default():
    s = AibaSettings()  # type: ignore[call-arg]
    assert s.gemini_sub_model == "gemini-3.1-flash-lite"


def test_max_concurrent_sub_agents_default():
    s = AibaSettings()  # type: ignore[call-arg]
    assert s.max_concurrent_sub_agents == 5


def test_request_timeout_seconds_default():
    s = AibaSettings()  # type: ignore[call-arg]
    assert s.request_timeout_seconds == 60


def test_playwright_headless_default():
    s = AibaSettings()  # type: ignore[call-arg]
    assert s.playwright_headless is True


def test_web_search_engine_default():
    s = AibaSettings()  # type: ignore[call-arg]
    assert s.web_search_engine == "duckduckgo"


def test_guardrails_enabled_default():
    s = AibaSettings()  # type: ignore[call-arg]
    assert s.guardrails_enabled is True


def test_cost_budget_usd_default():
    s = AibaSettings()  # type: ignore[call-arg]
    assert s.cost_budget_usd == 1.0


def test_require_approval_for_default_is_empty():
    s = AibaSettings()  # type: ignore[call-arg]
    assert s.require_approval_for == []


# ── Validation: range constraints ───────────────────────────────────


def test_max_concurrent_sub_agents_rejects_zero():
    with pytest.raises(ValueError):
        AibaSettings(MAX_CONCURRENT_SUB_AGENTS=0)  # type: ignore[call-arg]


def test_max_concurrent_sub_agents_rejects_over_50():
    with pytest.raises(ValueError):
        AibaSettings(MAX_CONCURRENT_SUB_AGENTS=51)  # type: ignore[call-arg]


def test_max_concurrent_sub_agents_accepts_boundary_values():
    assert AibaSettings(MAX_CONCURRENT_SUB_AGENTS=1)  # type: ignore[call-arg]
    assert AibaSettings(MAX_CONCURRENT_SUB_AGENTS=50)  # type: ignore[call-arg]


def test_request_timeout_rejects_below_10():
    with pytest.raises(ValueError):
        AibaSettings(REQUEST_TIMEOUT_SECONDS=9)  # type: ignore[call-arg]


def test_cost_budget_usd_rejects_zero():
    with pytest.raises(ValueError):
        AibaSettings(COST_BUDGET_USD=0.0)  # type: ignore[call-arg]


# ── Empty API key is allowed (app starts without key for setup) ─────


def test_empty_gemini_api_key_is_accepted():
    s = AibaSettings(GEMINI_API_KEY="")  # type: ignore[call-arg]
    assert s.gemini_api_key == ""


# ── Override via kwargs ─────────────────────────────────────────────


def test_can_override_via_kwargs():
    """Uppercase kwargs override cleaned environment."""
    s = AibaSettings(  # type: ignore[call-arg]
        GEMINI_API_KEY="explicit-key",  # type: ignore[call-arg]
        GEMINI_MAIN_MODEL="gemini-2.0-pro",  # type: ignore[call-arg]
        MAX_CONCURRENT_SUB_AGENTS=10,  # type: ignore[call-arg]
    )
    assert s.gemini_api_key == "explicit-key"
    assert s.gemini_main_model == "gemini-2.0-pro"
    assert s.max_concurrent_sub_agents == 10


def test_override_preserves_other_defaults():
    """Overriding one field does not affect others."""
    s = AibaSettings(MAX_CONCURRENT_SUB_AGENTS=7)  # type: ignore[call-arg]
    assert s.max_concurrent_sub_agents == 7
    assert s.playwright_headless is True
    assert s.request_timeout_seconds == 60

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

import src.tools.common_tools as ct


@pytest.fixture(autouse=True)
def _suppress_dotenv(monkeypatch):
    """Prevent .env file and shell env vars from leaking into tests.

    Pydantic-settings priority: init kwargs > env vars > env file > defaults.
    The user's shell exports all AIBA_* vars, so we must clear them to test
    the actual Field() defaults. We save and restore on teardown.
    """
    import os

    from src.utils.settings import AibaSettings

    # ---- purge all AIBA-related env vars so they don't override defaults ----
    _prefixes = (
        "GEMINI_",
        "LOGFIRE_",
        "MAX_CONCURRENT_",
        "REQUEST_TIMEOUT_",
        "PLAYWRIGHT_",
        "WEB_SEARCH_ENGINE",
        "SMTP_",
        "SENDER_",
        "USER_PROFILE",
        "GUARDRAILS_",
        "COST_BUDGET_",
        "REQUIRE_APPROVAL_",
    )
    saved: dict[str, str] = {}
    for k in list(os.environ):
        if any(k.startswith(p) for p in _prefixes):
            saved[k] = os.environ.pop(k)

    # ---- dummy API key so construction doesn't fail ------------------------
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    # ---- prevent .env file loading on top of everything -------------------
    monkeypatch.setitem(AibaSettings.model_config, "env_file", "/nonexistent/.env.test")

    yield

    # ---- teardown: restore original env state -----------------------------
    for k, v in saved.items():
        os.environ[k] = v


@pytest.fixture
def temp_data_dir():
    """Create a temporary data/ directory and override common_tools.DATA_DIR."""
    original = ct.DATA_DIR
    with tempfile.TemporaryDirectory() as tmp:
        ct.DATA_DIR = Path(tmp)
        yield ct.DATA_DIR
    ct.DATA_DIR = original


@pytest.fixture(autouse=True)
def reset_todo_state():
    """Ensure clean todo state before every test."""
    ct._todo_state.clear()


@pytest.fixture(autouse=True)
def reset_beat_allowed_csvs():
    """Restore REPL mode (unrestricted CSV access) after every test."""
    ct.set_beat_allowed_csvs(None)

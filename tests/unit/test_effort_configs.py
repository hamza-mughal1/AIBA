from __future__ import annotations

import pytest

from src.prompts.effort import (
    EFFORT_CONFIGS,
    EffortMode,
    get_effort_config,
    list_effort_modes,
)

# ── All modes exist ──────────────────────────────────────────────────


def test_all_three_effort_modes_registered():
    assert EffortMode.QUICK in EFFORT_CONFIGS
    assert EffortMode.BALANCED in EFFORT_CONFIGS
    assert EffortMode.MAX in EFFORT_CONFIGS


# ── Required keys ────────────────────────────────────────────────────

_REQUIRED_KEYS = ("model_settings", "instructions", "main_instructions", "usage_limits")


def test_quick_config_has_all_required_keys():
    cfg = EFFORT_CONFIGS[EffortMode.QUICK]
    for key in _REQUIRED_KEYS:
        assert key in cfg, f"QUICK missing key: {key}"


def test_balanced_config_has_all_required_keys():
    cfg = EFFORT_CONFIGS[EffortMode.BALANCED]
    for key in _REQUIRED_KEYS:
        assert key in cfg, f"BALANCED missing key: {key}"


def test_max_config_has_all_required_keys():
    cfg = EFFORT_CONFIGS[EffortMode.MAX]
    for key in _REQUIRED_KEYS:
        assert key in cfg, f"MAX missing key: {key}"


# ── get_effort_config ────────────────────────────────────────────────


def test_get_effort_config_returns_correct_config():
    cfg = get_effort_config(EffortMode.BALANCED)
    assert cfg is EFFORT_CONFIGS[EffortMode.BALANCED]


def test_get_effort_config_nonexistent_raises():
    with pytest.raises(KeyError):
        get_effort_config("nonexistent")  # type: ignore[arg-type]


# ── Token limits increase monotonically ──────────────────────────────


def _limits(mode: EffortMode):
    limits = EFFORT_CONFIGS[mode]["usage_limits"]
    return (limits.request_limit, limits.tool_calls_limit, limits.total_tokens_limit)


def test_token_limits_increase_quick_to_balanced():
    q_req, q_tool, q_tok = _limits(EffortMode.QUICK)
    b_req, b_tool, b_tok = _limits(EffortMode.BALANCED)

    assert isinstance(q_req, int)
    assert isinstance(b_req, int)
    assert isinstance(q_tool, int)
    assert isinstance(b_tool, int)
    assert isinstance(q_tok, int)
    assert isinstance(b_tok, int)

    assert b_req > q_req
    assert b_tool > q_tool
    assert b_tok > q_tok


def test_token_limits_increase_balanced_to_max():
    b_req, b_tool, b_tok = _limits(EffortMode.BALANCED)
    m_req, m_tool, m_tok = _limits(EffortMode.MAX)

    assert isinstance(m_req, int)
    assert isinstance(b_req, int)
    assert isinstance(m_tool, int)
    assert isinstance(b_tool, int)
    assert isinstance(m_tok, int)
    assert isinstance(b_tok, int)

    assert m_req > b_req
    assert m_tool > b_tool
    assert m_tok > b_tok


# ── Instructions are non-empty ───────────────────────────────────────


def test_all_instructions_are_non_empty():
    for mode in EffortMode:
        cfg = EFFORT_CONFIGS[mode]
        assert len(cfg["instructions"]) > 0, f"{mode.value} instructions empty"
        assert (
            len(cfg["main_instructions"]) > 0
        ), f"{mode.value} main_instructions empty"


# ── list_effort_modes ────────────────────────────────────────────────


def test_list_effort_modes_returns_all_three():
    modes = list_effort_modes()
    assert len(modes) == 3
    assert EffortMode.QUICK in modes
    assert EffortMode.BALANCED in modes
    assert EffortMode.MAX in modes


# ── EffortMode enum ──────────────────────────────────────────────────


def test_effort_mode_values():
    assert EffortMode.QUICK.value == "quick"
    assert EffortMode.BALANCED.value == "balanced"
    assert EffortMode.MAX.value == "max"

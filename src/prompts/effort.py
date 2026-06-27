"""Effort mode system — controls how hard the agent tries."""

from __future__ import annotations

from enum import StrEnum
from typing import TypedDict

from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import UsageLimits


class EffortConfig(TypedDict):
    model_settings: ModelSettings
    instructions: str
    main_instructions: str
    usage_limits: UsageLimits


class EffortMode(StrEnum):
    """How intensively the agent pursues its objective."""

    QUICK = "quick"
    BALANCED = "balanced"
    MAX = "max"


EFFORT_CONFIGS: dict[EffortMode, EffortConfig] = {
    EffortMode.QUICK: {
        "model_settings": ModelSettings(
            temperature=0.3,
            max_tokens=4096,
            timeout=30.0,
        ),
        "instructions": (
            "EFFORT MODE: QUICK. Be concise and direct. Use minimal tool calls. "
            "Prefer web_fetch over full browser navigation when possible. "
            "Do not paginate or deep-dive unless explicitly asked. "
            "One or two sources are sufficient — get the answer fast."
        ),
        "main_instructions": (
            "EFFORT MODE: QUICK — ORCHESTRATOR. "
            "Plan 1–2 waves max, then synthesize immediately. "
            "Spawn only what's essential. Prefer breadth over depth. "
            "Deliver a concise answer; do NOT loop."
        ),
        "usage_limits": UsageLimits(
            request_limit=15,
            tool_calls_limit=20,
            total_tokens_limit=100_000,
        ),
    },
    EffortMode.BALANCED: {
        "model_settings": ModelSettings(
            temperature=0.5,
            max_tokens=8192,
            timeout=60.0,
        ),
        "instructions": (
            "EFFORT MODE: BALANCED. Be thorough but pragmatic. "
            "Cross-check key facts across 2–3 sources. "
            "Use browser navigation for dynamic content. "
            "Pagination is fine but don't exhaust every page. "
            "Deliver structured, well-organized results."
        ),
        "main_instructions": (
            "EFFORT MODE: BALANCED — ORCHESTRATOR. "
            "Plan 2–3 waves, then synthesize a structured report. "
            "After wave 2, evaluate: do I have enough to answer well? "
            "If yes, go straight to synthesis. "
            "Do NOT spawn wave after wave chasing diminishing returns."
        ),
        "usage_limits": UsageLimits(
            request_limit=25,
            tool_calls_limit=40,
            total_tokens_limit=300_000,
        ),
    },
    EffortMode.MAX: {
        "model_settings": ModelSettings(
            temperature=0.7,
            max_tokens=16384,
            timeout=120.0,
        ),
        "instructions": (
            "EFFORT MODE: MAXIMUM. This is an exhaustive deep-dive mission. "
            "Leave no stone unturned. Use every tool at your disposal — browser, "
            "visual screenshots, JavaScript evaluation, multi-hop navigation, "
            "pagination exhaustion, cross-source verification. "
            "Quality and completeness are everything — but you MUST produce "
            "a final answer before hitting your tool budget limit."
        ),
        "main_instructions": (
            "EFFORT MODE: MAX — ORCHESTRATOR. "
            "You have a generous budget. Plan 4–8 waves across multiple vectors. "
            "Recursively chase pivot leads — but after wave 5, shift toward synthesis. "
            "Your final deliverable must be an exhaustive, well-organized report. "
            "Do not waste budget on redundant re-verification of settled facts."
        ),
        "usage_limits": UsageLimits(
            request_limit=50,
            tool_calls_limit=100,
            total_tokens_limit=500_000,
        ),
    },
}


def get_effort_config(mode: EffortMode) -> EffortConfig:
    """Return EffortConfig for the given effort mode."""
    return EFFORT_CONFIGS[mode]


def list_effort_modes() -> list[EffortMode]:
    """Return all available effort modes."""
    return list(EffortMode)

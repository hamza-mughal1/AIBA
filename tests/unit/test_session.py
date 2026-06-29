"""Tests for session.py — history filtering, trimming, and persistence.

Focuses on the pure-logic functions: _resolve, _filter_tool_parts, trim_history
and the save/load/list file operations. print_history is smoke-tested only.
"""

from __future__ import annotations

import pytest
from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from src.services.session import (
    _filter_tool_parts,
    _resolve,
    list_sessions,
    load_session,
    print_history,
    save_session,
    trim_history,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _make_request(content: str = "hello") -> ModelRequest:
    return ModelRequest(parts=[UserPromptPart(content=content)])


def _make_response(content: str = "hi there") -> ModelResponse:
    return ModelResponse(parts=[TextPart(content=content)])


def _make_tool_call(tool_name: str = "search", args: str = "{}") -> ModelRequest:
    return ModelRequest(
        parts=[ToolCallPart(tool_name=tool_name, args=args)],  # type: ignore[list-item]
    )


def _make_tool_return(content: str = "result") -> ModelResponse:
    return ModelResponse(
        parts=[ToolReturnPart(tool_name="search", content=content)],  # type: ignore[list-item]
    )


def _make_mixed_response(text: str, tool_name: str = "search") -> ModelResponse:
    return ModelResponse(
        parts=[
            TextPart(content=text),
            ToolCallPart(tool_name=tool_name, args="{}"),
        ],
    )


# ── _resolve ─────────────────────────────────────────────────────────


def test_resolve_returns_session_path():
    """_resolve returns a path inside sessions/ with .json extension."""
    p = _resolve("my-chat")
    assert p.suffix == ".json"
    assert p.parent.name == "sessions"


def test_resolve_strips_double_extension():
    """_resolve keeps only the stem — 'foo.json' → 'foo.json'."""
    p = _resolve("foo.json")
    assert p.name == "foo.json"


def test_resolve_creates_sessions_dir(tmp_path, monkeypatch):
    """_resolve creates the sessions directory if it doesn't exist."""
    import src.services.session as mod

    monkeypatch.setattr(mod, "SESSIONS_DIR", tmp_path / "sessions")
    p = _resolve("test")
    assert p.parent.is_dir()


# ── _filter_tool_parts ───────────────────────────────────────────────


def test_filter_keeps_user_prompts():
    messages = [
        _make_request("what is AI?"),
        _make_request("explain more"),
    ]
    result = _filter_tool_parts(messages)
    assert len(result) == 2
    assert all(isinstance(m, ModelRequest) for m in result)


def test_filter_keeps_text_responses():
    messages = [_make_response("AI is artificial intelligence")]
    result = _filter_tool_parts(messages)
    assert len(result) == 1
    assert isinstance(result[0], ModelResponse)


def test_filter_strips_tool_call_parts():
    """ModelRequest with only tool-call parts is dropped entirely."""
    messages = [
        _make_tool_call("search", '{"q":"test"}'),
        _make_request("user question"),
    ]
    result = _filter_tool_parts(messages)
    # First request had only tool-call → dropped
    # Second request has user-prompt → kept
    assert len(result) == 1
    assert isinstance(result[0], ModelRequest)


def test_filter_strips_tool_return_parts():
    """ModelResponse with only tool-return parts is dropped."""
    messages = [
        _make_response("real answer"),
        _make_tool_return('{"results":[]}'),
    ]
    result = _filter_tool_parts(messages)
    assert len(result) == 1
    assert isinstance(result[0], ModelResponse)


def test_filter_keeps_mixed_response_text():
    """ModelResponse with text + tool-call keeps only the text part."""
    messages = [_make_mixed_response("found 5 results")]
    result = _filter_tool_parts(messages)
    assert len(result) == 1
    assert len(result[0].parts) == 1
    assert isinstance(result[0].parts[0], TextPart)
    assert result[0].parts[0].content == "found 5 results"


def test_filter_handles_non_model_messages():
    """Arbitrary objects in the message list pass through untouched."""

    class CustomMessage:
        pass

    custom = CustomMessage()
    messages = [custom, _make_request("hi")]
    result = _filter_tool_parts(messages)
    assert len(result) == 2
    assert result[0] is custom
    assert isinstance(result[1], ModelRequest)


# ── trim_history ─────────────────────────────────────────────────────


def test_trim_under_max_is_noop():
    """trim_history doesn't modify a short history."""
    messages = [
        _make_request("q1"),
        _make_response("a1"),
        _make_request("q2"),
        _make_response("a2"),
    ]
    result = trim_history(messages, max_count=10)
    assert len(result) == 4


def test_trim_over_max_trims():
    """When history exceeds max_count, it gets trimmed."""
    messages = []
    for i in range(10):
        messages.append(_make_request(f"q{i}"))
        messages.append(_make_response(f"a{i}"))

    result = trim_history(messages, max_count=5)
    assert 1 < len(result) <= 5


def test_trim_keeps_first_message():
    """The first message (system prompt) is always retained."""
    messages = [
        _make_request("system prompt"),
        _make_request("q1"),
        _make_response("a1"),
    ] * 20

    result = trim_history(messages, max_count=3)
    # The first message should match the original system prompt content
    assert result[0].parts[0].content == messages[0].parts[0].content


def test_trim_aligns_to_user_boundary():
    """Trimmed history shouldn't start mid-turn (after a user message)."""
    messages = []
    for i in range(10):
        messages.append(_make_request(f"q{i}"))
        messages.append(_make_response(f"a{i}"))

    result = trim_history(messages, max_count=5)
    # First kept message (after system prompt) should start with a user request
    if len(result) > 1:
        second = result[1]
        if hasattr(second, "parts"):
            kinds = [getattr(p, "part_kind", None) for p in second.parts]
            assert "user-prompt" in kinds, f"Expected user prompt start, got {kinds}"


def test_trim_with_tool_noise():
    """Tool calls/returns are stripped before trimming."""
    messages = [
        _make_request("start"),
        _make_tool_call("search"),
        _make_tool_return("data"),
        _make_response("summary of data"),
        _make_request("next question"),
        _make_tool_call("read_csv"),
        _make_tool_return("csv data"),
        _make_response("csv summary"),
    ]

    result = trim_history(messages, max_count=4)
    # Tool noise stripped, should have ≤ 4 messages
    assert len(result) <= 4
    # Should contain real content, not tool calls
    for msg in result:
        if isinstance(msg, ModelRequest):
            kinds = [getattr(p, "part_kind", None) for p in msg.parts]
            assert "user-prompt" in kinds or kinds == []
        elif isinstance(msg, ModelResponse):
            kinds = [getattr(p, "part_kind", None) for p in msg.parts]
            assert "text" in kinds or kinds == []


# ── save_session / load_session round trip ───────────────────────────


def test_save_and_load_round_trip(tmp_path, monkeypatch):
    """Save a session then load it back — messages and settings match."""
    import src.services.session as mod

    tmp_sessions = tmp_path / "sessions"
    monkeypatch.setattr(mod, "SESSIONS_DIR", tmp_sessions)

    messages = [
        _make_request("hello world"),
        _make_response("hi! how can I help?"),
    ]
    settings = {"effort": "balanced", "template": "default"}

    save_session("roundtrip", messages, settings)
    loaded_msgs, loaded_settings = load_session("roundtrip")

    assert loaded_settings == settings
    assert len(loaded_msgs) == 2
    # Spot-check part content
    assert loaded_msgs[0].parts[0].content == "hello world"
    assert loaded_msgs[1].parts[0].content == "hi! how can I help?"


def test_load_missing_session_raises(tmp_path, monkeypatch):
    """Loading a nonexistent session raises FileNotFoundError."""
    import src.services.session as mod

    monkeypatch.setattr(mod, "SESSIONS_DIR", tmp_path / "nonexistent")
    with pytest.raises(FileNotFoundError, match="Session not found"):
        load_session("ghost")


def test_list_sessions_returns_names(tmp_path, monkeypatch):
    """list_sessions returns .stem of all .json files in sessions/."""
    import src.services.session as mod

    tmp_sessions = tmp_path / "sessions"
    monkeypatch.setattr(mod, "SESSIONS_DIR", tmp_sessions)

    # Save two sessions
    save_session("alpha", [_make_request("a")], {})
    save_session("beta", [_make_request("b")], {})

    names = list_sessions()
    assert "alpha" in names
    assert "beta" in names


def test_list_sessions_empty_dir(tmp_path, monkeypatch):
    """list_sessions with no saved sessions returns empty list."""
    import src.services.session as mod

    monkeypatch.setattr(mod, "SESSIONS_DIR", tmp_path / "empty_sessions")
    assert list_sessions() == []


# ── print_history smoke ──────────────────────────────────────────────


def test_print_history_empty(capsys):
    """print_history with empty messages prints a dim message."""
    print_history([])
    captured = capsys.readouterr()
    assert "empty session" in captured.out


def test_print_history_non_empty(capsys):
    """print_history with messages doesn't crash."""
    messages = [
        _make_request("hello"),
        _make_response("hey there"),
    ]
    print_history(messages)
    captured = capsys.readouterr()
    assert "hello" in captured.out
    assert "hey there" in captured.out


def test_print_history_truncates_long_prompts(capsys):
    """User prompts > 500 chars are truncated in display."""
    long_text = "x" * 600
    messages = [_make_request(long_text)]
    print_history(messages)
    captured = capsys.readouterr()
    assert "…" in captured.out
    assert len(captured.out) < 2000  # truncated display, not full 600 chars


def test_print_history_skips_non_part_messages(capsys):
    """Messages without a .parts attribute are skipped (continue branch)."""

    class PlainMsg:
        pass

    messages = [PlainMsg(), _make_request("hello")]
    print_history(messages)
    captured = capsys.readouterr()
    assert "hello" in captured.out


def test_trim_fallback_when_no_user_prompt_in_tail():
    """When the tail has no user-prompt boundary, fallback slice is used."""
    # Create messages where the tail (from min_start onward) contains only
    # ModelResponse (text) — no user-prompt. This forces the fallback path.
    # First message (always kept), then many response-only messages.
    messages: list[ModelRequest | ModelResponse] = [_make_request("system")]
    for i in range(15):
        messages.append(_make_response(f"response {i}"))

    result = trim_history(messages, max_count=5)
    # Should still have first message plus tail
    assert len(result) <= 5
    assert result[0].parts[0].content == "system"


def test_load_legacy_raw_array_format(tmp_path, monkeypatch):
    """Loading a legacy session file (raw JSON array, no wrapper) works."""
    import src.services.session as mod

    tmp_sessions = tmp_path / "sessions"
    monkeypatch.setattr(mod, "SESSIONS_DIR", tmp_sessions)

    # Legacy format: just a raw JSON array of messages
    messages = [
        _make_request("legacy question"),
        _make_response("legacy answer"),
    ]
    messages_json = ModelMessagesTypeAdapter.dump_json(messages, indent=2)
    # Write raw array directly (no wrapper dict)
    session_path = tmp_sessions / "legacy.json"
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_bytes(messages_json)

    loaded_msgs, loaded_settings = load_session("legacy")
    assert loaded_settings is None
    assert len(loaded_msgs) == 2
    assert loaded_msgs[0].parts[0].content == "legacy question"

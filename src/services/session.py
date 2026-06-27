import json
from pathlib import Path
from typing import Any

from pydantic_ai.messages import ModelMessagesTypeAdapter, ModelRequest, ModelResponse

from src.services.rendering import C, hr, render_markdown

MAX_HISTORY_MESSAGES = 20
SESSION_VERSION = 1
SESSIONS_DIR = Path("sessions")


def _resolve(name: str) -> Path:
    """Resolve a session name to its file path inside ./sessions/."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(name).stem
    return SESSIONS_DIR / f"{stem}.json"


def _filter_tool_parts(messages: list[Any]) -> list[Any]:
    """Strip tool-call and tool-return parts, keeping only user prompts and text outputs.

    Tool outputs are verbose (YAML, JSON, HTML) and their content is already
    synthesized in the agent's text response. Dropping them preserves the
    semantic context while drastically reducing token usage.
    """
    filtered: list[Any] = []
    for msg in messages:
        if isinstance(msg, ModelRequest):
            kept = [
                p for p in msg.parts if getattr(p, "part_kind", None) == "user-prompt"
            ]
            if not kept:
                continue
            filtered.append(
                ModelRequest(
                    parts=kept,
                    timestamp=msg.timestamp,
                    instructions=msg.instructions,
                    kind=msg.kind,
                    run_id=msg.run_id,
                    conversation_id=msg.conversation_id,
                    metadata=getattr(msg, "metadata", None),
                    state=getattr(msg, "state", "complete"),
                )
            )
        elif isinstance(msg, ModelResponse):
            kept = [p for p in msg.parts if getattr(p, "part_kind", None) == "text"]
            if not kept:
                continue
            filtered.append(
                ModelResponse(
                    parts=kept,
                    usage=msg.usage,
                    model_name=msg.model_name,
                    timestamp=msg.timestamp,
                    kind=msg.kind,
                    provider_name=msg.provider_name,
                    provider_url=msg.provider_url,
                    provider_details=getattr(msg, "provider_details", None),
                    provider_response_id=getattr(msg, "provider_response_id", None),
                    finish_reason=getattr(msg, "finish_reason", None),
                    run_id=msg.run_id,
                    conversation_id=msg.conversation_id,
                    metadata=getattr(msg, "metadata", None),
                    state=getattr(msg, "state", "complete"),
                )
            )
        else:
            filtered.append(msg)
    return filtered


def trim_history(
    messages: list[Any], max_count: int = MAX_HISTORY_MESSAGES
) -> list[Any]:
    """Strip tool noise, keep system prompt + recent user/model turns.

    Tools calls and their return payloads are stripped first — their content
    is already synthesized in the agent's text output.

    Then slices to max_count messages, aligned to a user-message boundary
    so Gemini's strict turn ordering isn't broken.
    """
    messages = _filter_tool_parts(messages)

    if len(messages) <= max_count:
        return messages

    min_start = len(messages) - (max_count - 1)

    for i in range(min_start, len(messages)):
        msg = messages[i]
        if hasattr(msg, "parts"):
            for part in msg.parts:
                if getattr(part, "part_kind", None) == "user-prompt":
                    return [messages[0]] + messages[i:]

    return [messages[0]] + messages[-(max_count - 1) :]


def save_session(name: str, history: list[Any], settings: dict[str, Any]) -> None:
    """Save history + settings metadata to ./sessions/<name>.json."""
    path = _resolve(name)
    messages_json = ModelMessagesTypeAdapter.dump_json(history, indent=2)
    messages_list = json.loads(messages_json)
    wrapper = {
        "version": SESSION_VERSION,
        "settings": settings,
        "messages": messages_list,
    }
    path.write_text(json.dumps(wrapper, indent=2, ensure_ascii=False))


def load_session(name: str) -> tuple[list[Any], dict[str, Any] | None]:
    """Load a session file from ./sessions/<name>.json.

    Handles both wrapper format (v1+) and raw array (legacy).

    Returns (messages, settings_dict_or_None).
    """
    path = _resolve(name)
    if not path.is_file():
        raise FileNotFoundError(f"Session not found: {path}")

    raw = path.read_bytes()
    data = json.loads(raw)

    if isinstance(data, dict) and "messages" in data:
        messages_json = json.dumps(data["messages"]).encode()
        history = ModelMessagesTypeAdapter.validate_json(messages_json)
        return history, data.get("settings")

    history = ModelMessagesTypeAdapter.validate_json(raw)
    return history, None


def list_sessions() -> list[str]:
    """Return available session names (without .json extension), newest first."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(
        SESSIONS_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [f.stem for f in files]


def print_history(messages: list[Any]) -> None:
    """Render a loaded conversation so the user can see what was happening."""
    if not messages:
        print(f"  {C['dim']}(empty session){C['reset']}")
        return

    print()
    print(hr("─", "dim"))
    print(
        f"  {C['bold']}{C['purple']}Conversation History{C['reset']}  ({len(messages)} messages)"
    )
    print(hr("─", "dim"))

    for msg in messages:
        if not hasattr(msg, "parts"):
            continue
        for part in msg.parts:
            kind = getattr(part, "part_kind", None)
            if kind == "user-prompt":
                print(f"\n  {C['bold']}{C['teal']}▸ You:{C['reset']}")
                content = getattr(part, "content", "") or ""
                # Truncate very long prompts for display
                if len(content) > 500:
                    content = content[:500] + "…"
                print(f"  {C['dim']}{content}{C['reset']}")
            elif kind == "text":
                print(f"\n  {C['bold']}{C['green']}◈ AIBA:{C['reset']}")
                content = getattr(part, "content", "") or ""
                render_markdown(content)

    print()
    print(hr("─", "dim"))

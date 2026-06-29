"""CSV + todo tools — plain functions registered as agent tools at import time.

State and logic live here so callers (beats, main, screens) don't touch agent internals.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# ── Global state ──────────────────────────────────────────────────
# None = REPL mode (all CSV files in data/ accessible).
# list[str] = beat mode (only those filenames, empty list = no CSV access).
_beat_allowed_csvs: list[str] | None = None


def set_beat_allowed_csvs(csvs: list[str] | None) -> None:
    """Restrict which CSV files a beat may access (None = REPL, all access)."""
    global _beat_allowed_csvs
    _beat_allowed_csvs = csvs


def get_beat_allowed_csvs() -> list[str] | None:
    """Return the current allowed CSV list (None = unrestricted REPL mode)."""
    return _beat_allowed_csvs


# ── Tool: todo ────────────────────────────────────────────────────

_todo_state: list[dict[str, Any]] = []


def todo(todos: list[dict[str, Any]] | None = None) -> str:
    """Read or update the task plan.

    Pass a list of task dicts to persist a new plan. Omit to view current state.
    Each dict: {id: int, task: str, status: 'pending'|'in-progress'|'completed'}.
    """
    global _todo_state
    if todos is not None:
        _todo_state = todos

    if not _todo_state:
        return "Todo list is empty."

    lines: list[str] = []
    for t in _todo_state:
        icon = {"pending": "○", "in-progress": "◉", "completed": "✓"}.get(
            t.get("status", "pending"),
            "?",
        )
        lines.append(f"  {icon} [{t.get('id')}] {t.get('task', '')}")
    return "\n".join(lines)


# ── Tool: read_csv ────────────────────────────────────────────────


def read_csv(filename: str, max_rows: int = 200) -> str:
    """Read a CSV file from the data/ folder. Returns up to max_rows as a markdown table.

    Args:
        filename: Just the filename (e.g. 'jobs.csv'), looked up in data/.
        max_rows: Maximum rows to return. Default 200.

    """
    if "/" in filename or "\\" in filename or filename.startswith(".."):
        return (
            f"ERROR: '{filename}' is not a valid filename. "
            f"Use just the filename, e.g. 'jobs.csv'."
        )

    csv_path = DATA_DIR / filename

    if _beat_allowed_csvs is not None:
        if filename not in _beat_allowed_csvs:
            return (
                f"ERROR: '{filename}' is not in the beat's allowed CSV list. "
                f"Allowed: {_beat_allowed_csvs or '(none)'}"
            )

    if not csv_path.is_file():
        available = (
            ", ".join(p.name for p in DATA_DIR.glob("*.csv"))
            if DATA_DIR.is_dir()
            else "(data/ directory not found)"
        )
        return (
            f"ERROR: File '{filename}' does not exist in data/. Available: {available}"
        )

    try:
        content = csv_path.read_text(encoding="utf-8")
        reader = csv.DictReader(content.splitlines())
        if reader.fieldnames is None:
            return f"ERROR: '{filename}' has no header row."

        rows = list(reader)
        if not rows:
            return f"'{filename}' is empty (headers: {', '.join(reader.fieldnames)})."

        total = len(rows)
        rows = rows[:max_rows]

        headers = reader.fieldnames
        col_widths = {
            h: max(len(h), max((len(str(r.get(h, ""))) for r in rows), default=0))
            for h in headers
        }

        sep = "|".join("-" * (col_widths[h] + 2) for h in headers)
        header_line = "|".join(f" {h.ljust(col_widths[h])} " for h in headers)
        lines = [f"|{header_line}|", f"|{sep}|"]

        for row in rows:
            cells = "|".join(
                f" {str(row.get(h, '') or '').ljust(col_widths[h])} " for h in headers
            )
            lines.append(f"|{cells}|")

        suffix = f"\n\n({len(rows)} of {total} rows shown)" if total > max_rows else ""
        return "\n".join(lines) + suffix

    except Exception as exc:
        return f"ERROR reading '{filename}': {type(exc).__name__}: {exc}"


# ── Tool: append_csv ──────────────────────────────────────────────


def append_csv(filename: str, rows: list[dict[str, str]]) -> str:
    """Append rows to a CSV file in the data/ folder.

    All row keys must match existing headers. CSV files must pre-exist with headers.

    Args:
        filename: Just the filename (e.g. 'jobs.csv'), looked up in data/.
        rows: List of dicts with column_name → value.

    """
    if "/" in filename or "\\" in filename or filename.startswith(".."):
        return (
            f"ERROR: '{filename}' is not a valid filename. "
            f"Use just the filename, e.g. 'jobs.csv'."
        )

    csv_path = DATA_DIR / filename

    if _beat_allowed_csvs is not None:
        if filename not in _beat_allowed_csvs:
            return (
                f"ERROR: '{filename}' is not in the beat's allowed CSV list. "
                f"Allowed: {_beat_allowed_csvs or '(none)'}"
            )

    if not csv_path.is_file():
        available = (
            ", ".join(p.name for p in DATA_DIR.glob("*.csv"))
            if DATA_DIR.is_dir()
            else "(data/ directory not found)"
        )
        return (
            f"ERROR: File '{filename}' does not exist in data/. "
            f"CSV files must pre-exist with headers. Available: {available}"
        )

    if not rows:
        return "No rows to append."

    try:
        existing_headers = csv.DictReader(
            csv_path.read_text(encoding="utf-8").splitlines(),
        ).fieldnames
        if existing_headers is None:
            return f"ERROR: '{filename}' has no header row."

        for i, row in enumerate(rows, start=1):
            unknown = set(row.keys()) - set(existing_headers)
            if unknown:
                return (
                    f"ERROR: Row {i} has unknown column(s): "
                    f"{', '.join(sorted(unknown))}. "
                    f"Expected: {', '.join(existing_headers)}"
                )
            missing = set(existing_headers) - set(row.keys())
            if missing:
                return (
                    f"ERROR: Row {i} is missing column(s): "
                    f"{', '.join(sorted(missing))}. "
                    f"Expected: {', '.join(existing_headers)}"
                )

        with csv_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=existing_headers)
            writer.writerows(rows)

        return f"Appended {len(rows)} row(s) to '{filename}'."

    except Exception as exc:
        return f"ERROR writing '{filename}': {type(exc).__name__}: {exc}"

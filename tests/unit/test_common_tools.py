from __future__ import annotations

from pathlib import Path

from src.tools.common_tools import (
    append_csv,
    get_beat_allowed_csvs,
    read_csv,
    set_beat_allowed_csvs,
    todo,
)

# ── todo ────────────────────────────────────────────────────────────


def test_todo_empty_state():
    """A fresh todo list must report empty."""
    assert todo() == "Todo list is empty."


def test_todo_write_and_read():
    """Write tasks then read them back — verify icons and fields."""
    result = todo(
        [
            {"id": 1, "task": "Search Google", "status": "pending"},
            {"id": 2, "task": "Scrape LinkedIn", "status": "in-progress"},
            {"id": 3, "task": "Send email", "status": "completed"},
        ],
    )

    assert "○ [1] Search Google" in result
    assert "◉ [2] Scrape LinkedIn" in result
    assert "✓ [3] Send email" in result


def test_todo_read_without_args_preserves_state():
    """Calling todo() without args must NOT clear the list."""
    todo([{"id": 1, "task": "Test", "status": "pending"}])
    result = todo(None)  # None = read, same as no args
    assert "○ [1] Test" in result


def test_todo_explicit_none_does_not_clear():
    """Passing None explicitly must read, not reset."""
    todo([{"id": 1, "task": "Keep me", "status": "pending"}])
    todo(None)
    assert "○ [1] Keep me" in todo()


def test_todo_empty_list_clears():
    """Passing [] must reset to empty."""
    todo([{"id": 1, "task": "Clear me", "status": "pending"}])
    assert "Clear me" in todo()
    todo([])
    assert todo() == "Todo list is empty."


def test_todo_unknown_status_uses_question_mark():
    """A task with an unrecognized status gets a '?' icon."""
    result = todo([{"id": 1, "task": "Mystery", "status": "unknown"}])
    assert "? [1] Mystery" in result


def test_todo_missing_fields_handled_gracefully():
    """Fields missing from a task dict should not crash."""
    result = todo([{"id": 99}])  # no task, no status
    assert "[99]" in result  # at minimum the id appears


# ── read_csv ────────────────────────────────────────────────────────


def test_read_csv_valid(temp_data_dir: Path):
    """Read a valid CSV and get a markdown table back."""
    (temp_data_dir / "test.csv").write_text("name,role\nAlice,Engineer\nBob,Designer")

    result = read_csv("test.csv")
    assert "| name" in result
    assert "| Alice" in result
    assert "| Bob" in result


def test_read_csv_max_rows_trims_and_shows_count(temp_data_dir: Path):
    """When there are more rows than max_rows, output is trimmed."""
    lines = ["col1,col2"] + [f"r{i},v{i}" for i in range(30)]
    (temp_data_dir / "big.csv").write_text("\n".join(lines))

    result = read_csv("big.csv", max_rows=10)
    assert "| r0" in result
    assert "| r9" in result
    assert "| r10" not in result
    assert "(10 of 30 rows shown)" in result


def test_read_csv_nonexistent_file():
    """Reading a missing file returns a clear ERROR message."""
    result = read_csv("nope.csv")
    assert "ERROR" in result
    assert "nope.csv" in result


def test_read_csv_path_traversal_slash_blocked():
    """Security: forward-slash path traversal is rejected."""
    result = read_csv("../../../etc/passwd")
    assert "ERROR" in result
    assert "not a valid filename" in result


def test_read_csv_path_traversal_backslash_blocked():
    """Security: backslash path traversal is rejected."""
    result = read_csv("..\\..\\secrets")
    assert "ERROR" in result
    assert "not a valid filename" in result


def test_read_csv_dot_dot_prefix_blocked():
    """Security: '../' shorthand is rejected."""
    result = read_csv("../evil.csv")
    assert "ERROR" in result


def test_read_csv_empty_file_with_headers(temp_data_dir: Path):
    """An empty CSV (headers only) returns an informative message."""
    (temp_data_dir / "empty.csv").write_text("col1,col2")

    result = read_csv("empty.csv")
    assert "empty" in result
    assert "col1, col2" in result


def test_read_csv_beat_mode_allows_whitelisted(temp_data_dir: Path):
    """In beat mode, a CSV in the allow-list is readable."""
    (temp_data_dir / "ok.csv").write_text("name\nAlice")
    set_beat_allowed_csvs(["ok.csv"])

    result = read_csv("ok.csv")
    assert "Alice" in result


def test_read_csv_beat_mode_blocks_unlisted(temp_data_dir: Path):
    """In beat mode, a CSV not in the allow-list is blocked."""
    (temp_data_dir / "secret.csv").write_text("data\nx")
    set_beat_allowed_csvs(["ok.csv"])

    result = read_csv("secret.csv")
    assert "not in the beat's allowed CSV list" in result


def test_read_csv_repl_mode_no_restriction(temp_data_dir: Path):
    """In REPL mode (None), any CSV is readable."""
    (temp_data_dir / "any.csv").write_text("x\ny")
    set_beat_allowed_csvs(None)  # REPL mode

    result = read_csv("any.csv")
    assert "ERROR" not in result


def test_read_csv_no_header_rows_in_file():
    """A CSV file with no header row returns an error."""
    (Path.cwd() / "data" / "noheader.csv").write_text("")

    result = read_csv("noheader.csv")
    assert "ERROR" in result
    assert "has no header row" in result


def test_read_csv_unexpected_exception(temp_data_dir: Path):
    """An unexpected exception during read (e.g. PermissionError) is caught."""
    from unittest.mock import patch

    (temp_data_dir / "ok.csv").write_text("name\nAlice")
    # Raise an unexpected OSError during the read phase (after path validation)
    with patch("pathlib.Path.read_text", side_effect=PermissionError("denied")):
        result = read_csv("ok.csv")

    assert "ERROR reading" in result
    assert "PermissionError" in result


# ── beat allowed CSV accessors ──────────────────────────────────────


def test_set_and_get_beat_allowed_csvs_round_trip():
    set_beat_allowed_csvs(["a.csv", "b.csv"])
    assert get_beat_allowed_csvs() == ["a.csv", "b.csv"]


def test_beat_allowed_csvs_none_means_repl_mode():
    set_beat_allowed_csvs(None)
    assert get_beat_allowed_csvs() is None


def test_beat_allowed_csvs_empty_list_blocks_all():
    set_beat_allowed_csvs([])
    assert get_beat_allowed_csvs() == []


# ── append_csv ──────────────────────────────────────────────────────


def test_append_csv_adds_rows(temp_data_dir: Path):
    """Append rows to an existing CSV and verify they appear."""
    (temp_data_dir / "log.csv").write_text("name,status\nAlice,ok\n")

    result = append_csv("log.csv", [{"name": "Bob", "status": "done"}])
    assert "Appended" in result

    content = (temp_data_dir / "log.csv").read_text()
    assert "Bob" in content
    assert "done" in content


def test_append_csv_missing_file(temp_data_dir: Path):
    """Appending to a non-existent CSV returns an error."""
    result = append_csv("nope.csv", [{"col": "val"}])
    assert "ERROR" in result


def test_append_csv_mismatched_headers(temp_data_dir: Path):
    """Appending rows with wrong keys returns an error."""
    (temp_data_dir / "x.csv").write_text("name,status\n")
    result = append_csv("x.csv", [{"name": "Z", "extra": "???"}])
    assert "ERROR" in result


def test_append_csv_path_traversal_blocked():
    """Security: path traversal in append_csv is rejected."""
    result = append_csv("../evil.csv", [{"col": "val"}])
    assert "ERROR" in result
    assert "not a valid filename" in result


def test_append_csv_beat_mode_blocks_unlisted(temp_data_dir: Path):
    """In beat mode, appending to an unlisted CSV is blocked."""
    (temp_data_dir / "secret.csv").write_text("data\nx")
    set_beat_allowed_csvs(["ok.csv"])
    result = append_csv("secret.csv", [{"data": "y"}])
    assert "not in the beat's allowed CSV list" in result


def test_append_csv_empty_rows_list(temp_data_dir: Path):
    """Passing an empty list returns a message, not an error."""
    (temp_data_dir / "log.csv").write_text("name,status\nAlice,ok")
    result = append_csv("log.csv", [])
    assert "No rows to append" in result


def test_append_csv_missing_columns(temp_data_dir: Path):
    """Row missing a required column returns an error."""
    (temp_data_dir / "x.csv").write_text("name,status\n")
    result = append_csv("x.csv", [{"name": "Z"}])  # missing 'status'
    assert "ERROR" in result
    assert "missing column" in result


def test_append_csv_with_no_header_row(temp_data_dir: Path):
    """Appending to a CSV with no header row returns an error."""
    (temp_data_dir / "noheader.csv").write_text("")
    result = append_csv("noheader.csv", [{"col": "val"}])
    assert "ERROR" in result
    assert "has no header row" in result


def test_append_csv_unexpected_exception(temp_data_dir: Path):
    """An unexpected exception during write (e.g. PermissionError) is caught."""
    from unittest.mock import patch

    (temp_data_dir / "ok.csv").write_text("name\nAlice")
    # Raise an unexpected OSError during the write phase (after validation)
    with patch("csv.DictWriter.writerows", side_effect=OSError("disk full")):
        result = append_csv("ok.csv", [{"name": "Bob"}])

    assert "ERROR writing" in result
    assert "OSError" in result

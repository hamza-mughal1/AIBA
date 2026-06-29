"""Tests for beats.py — BeatConfig, scheduling, state, logging, and run paths."""

from __future__ import annotations

import json
import smtplib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Register templates so BeatConfig._template_exists passes
from src.prompts.models import Template, register_template
from src.services.beats import (
    BeatConfig,
    _send_beat_summary,
    is_due,
    load_beats,
    load_state,
    log_beat_run,
    os_schedule_instructions,
    run_all_due,
    run_beat,
    save_state,
)

_FAKE_TEMPLATES = [
    Template(
        name="default",
        description="Default template",
        generate_prompt=lambda p, e: "test",
    ),
    Template(
        name="job-search",
        description="Job search template",
        generate_prompt=lambda p, e: "test",
    ),
]
for _t in _FAKE_TEMPLATES:
    register_template(_t)


# ── BeatConfig ───────────────────────────────────────────────────────


def test_beat_config_minimal():
    """A beat with only required fields constructs successfully."""
    beat = BeatConfig(
        name="daily-report",
        schedule="0 9 * * *",
        template="default",
    )
    assert beat.name == "daily-report"
    assert beat.schedule == "0 9 * * *"
    assert beat.template == "default"
    assert beat.effort == "balanced"  # default
    assert beat.mode == "agent"  # default
    assert beat.sub_agents == 5  # default
    assert beat.prompt_extra == ""  # default
    assert beat.headless is True  # default
    assert beat.allowed_csvs == []  # default


def test_beat_config_full():
    """All optional fields can be set explicitly."""
    beat = BeatConfig(
        name="full-beat",
        schedule="*/15 * * * *",
        template="default",
        effort="max",
        mode="swarm",
        sub_agents=10,
        prompt_extra="Focus on high-priority items.",
        budget_override_usd=5.0,
        notify_email="admin@example.com",
        headless=True,
        allowed_csvs=["jobs.csv", "contacts.csv"],
    )
    assert beat.effort == "max"
    assert beat.mode == "swarm"
    assert beat.sub_agents == 10
    assert beat.prompt_extra == "Focus on high-priority items."
    assert beat.budget_override_usd == 5.0
    assert beat.notify_email == "admin@example.com"
    assert beat.allowed_csvs == ["jobs.csv", "contacts.csv"]


def test_beat_config_template_must_exist():
    """A nonexistent template name fails validation."""
    with pytest.raises(ValueError, match="Template 'nonexistent-xyz' not found"):
        BeatConfig(
            name="bad",
            schedule="0 0 * * *",
            template="nonexistent-xyz",
        )


def test_beat_config_effort_must_be_valid():
    """An invalid effort string fails validation."""
    with pytest.raises(ValueError, match="Effort 'super-slow' is not a valid"):
        BeatConfig(
            name="bad-effort",
            schedule="0 0 * * *",
            template="default",
            effort="super-slow",
        )


def test_beat_config_mode_must_be_agent_or_swarm():
    """An invalid mode string fails validation."""
    with pytest.raises(ValueError, match="Mode 'orchestrator' is invalid"):
        BeatConfig(
            name="bad-mode",
            schedule="0 0 * * *",
            template="default",
            mode="orchestrator",
        )


def test_beat_config_cron_must_be_valid():
    """An invalid cron expression fails validation."""
    with pytest.raises(ValueError, match="Invalid cron expression"):
        BeatConfig(
            name="bad-cron",
            schedule="not a cron",
            template="default",
        )


def test_beat_config_cron_various_expressions():
    """Common cron patterns all validate."""
    for expr in [
        "0 9 * * *",
        "*/5 * * * *",
        "0 0 1 * *",
        "30 14 * * 1-5",
        "0 0 * * 0",
    ]:
        beat = BeatConfig(name="test", schedule=expr, template="default")
        assert beat.schedule == expr


def test_beat_config_sub_agents_bounds():
    """sub_agents must be between 1 and 50."""
    BeatConfig(name="lo", schedule="0 0 * * *", template="default", sub_agents=1)
    BeatConfig(name="hi", schedule="0 0 * * *", template="default", sub_agents=50)

    with pytest.raises(ValueError):
        BeatConfig(name="bad", schedule="0 0 * * *", template="default", sub_agents=0)
    with pytest.raises(ValueError):
        BeatConfig(name="bad", schedule="0 0 * * *", template="default", sub_agents=51)


def test_beat_config_headless_default_true():
    """Headless defaults to True (beats always run headless)."""
    beat = BeatConfig(name="h", schedule="0 0 * * *", template="default")
    assert beat.headless is True


# ── is_due ───────────────────────────────────────────────────────────


def test_is_due_no_last_run():
    """A beat with no last_run is always due."""
    assert is_due("0 9 * * *", None) is True


def test_is_due_past_schedule():
    """A beat whose last run was before the next scheduled time is due."""
    schedule = "0 9 * * *"  # 9 AM daily
    long_ago = datetime(2020, 1, 1, 8, 0, 0)
    assert is_due(schedule, long_ago) is True


def test_is_due_recently_ran():
    """A beat that just ran is NOT due."""
    # Use a schedule that fires extremely rarely (Feb 29 at midnight).
    # No matter when the test runs, a beat that ran 5 min ago is not due.
    schedule = "0 0 29 2 *"
    now = datetime.now(UTC).replace(tzinfo=None)
    just_ran = now - timedelta(minutes=5)
    assert is_due(schedule, just_ran) is False


def test_is_due_exactly_at_boundary():
    """A beat exactly at the next cron tick is due."""
    schedule = "0 0 * * *"  # midnight
    last_run = datetime(2024, 1, 1, 23, 59, 0)
    # The croniter will say next run is midnight Jan 2
    # We're well past that, so it should be due
    assert is_due(schedule, last_run) is True


# ── load_state / save_state ──────────────────────────────────────────


def test_load_state_missing_file_returns_empty(tmp_path, monkeypatch):
    """Missing state file returns empty dict."""
    monkeypatch.setattr("src.services.beats.STATE_PATH", tmp_path / "nonexistent.json")
    assert load_state() == {}


def test_save_and_load_state_round_trip(tmp_path, monkeypatch):
    """Save state then load it back — values match."""
    fake_path = tmp_path / "beat_state.json"
    monkeypatch.setattr("src.services.beats.STATE_PATH", fake_path)

    state = {
        "daily": {
            "last_run": "2025-01-01T09:00:00",
            "last_status": "success",
            "total_runs": 5,
        },
    }
    save_state(state)
    loaded = load_state()
    assert loaded == state


def test_load_state_corrupt_json(tmp_path, monkeypatch):
    """Corrupt JSON returns empty dict (doesn't crash)."""
    fake_path = tmp_path / "bad.json"
    monkeypatch.setattr("src.services.beats.STATE_PATH", fake_path)
    fake_path.write_text("not json {{{")

    assert load_state() == {}


# ── load_beats ───────────────────────────────────────────────────────


def test_load_beats_missing_file():
    """Missing beats.yaml returns empty dict."""
    assert load_beats(Path("/nonexistent/beats.yaml")) == {}


def test_load_beats_empty_yaml(tmp_path):
    """Empty beats.yaml returns empty dict."""
    yaml_path = tmp_path / "beats.yaml"
    yaml_path.write_text("")
    assert load_beats(yaml_path) == {}


def test_load_beats_yaml_without_beats_key(tmp_path):
    """YAML with no 'beats' root key returns empty dict."""
    yaml_path = tmp_path / "beats.yaml"
    yaml_path.write_text("other: [1, 2, 3]\n")
    assert load_beats(yaml_path) == {}


def test_load_beats_valid(tmp_path):
    """Valid beats.yaml loads and validates all beat configs."""
    yaml_path = tmp_path / "beats.yaml"
    yaml_path.write_text(
        yaml.dump(
            {
                "beats": {
                    "morning": {
                        "name": "morning",
                        "schedule": "0 9 * * *",
                        "template": "default",
                        "effort": "quick",
                        "mode": "agent",
                    },
                    "evening": {
                        "name": "evening",
                        "schedule": "0 18 * * *",
                        "template": "default",
                        "effort": "balanced",
                        "mode": "swarm",
                        "sub_agents": 3,
                    },
                },
            },
        ),
    )

    beats = load_beats(yaml_path)
    assert len(beats) == 2
    assert "morning" in beats
    assert "evening" in beats
    assert beats["morning"].effort == "quick"
    assert beats["evening"].mode == "swarm"


def test_load_beats_invalid_beat_inside_valid_yaml(tmp_path):
    """A single invalid beat raises ValueError."""
    import yaml

    yaml_path = tmp_path / "beats.yaml"
    yaml_path.write_text(
        yaml.dump(
            {
                "beats": {
                    "bad_beat": {
                        "name": "bad_beat",
                        "schedule": "0 0 * * *",
                        "template": "nonexistent-template",
                    },
                },
            },
        ),
    )

    with pytest.raises(ValueError):
        load_beats(yaml_path)


def test_load_beats_beat_value_not_a_dict(tmp_path):
    """A beat whose value is not a dict (e.g. a string) raises ValueError."""
    yaml_path = tmp_path / "beats.yaml"
    yaml_path.write_text(
        yaml.dump(
            {
                "beats": {
                    "bad_beat": "this is a string, not a dict",
                },
            },
        ),
    )

    with pytest.raises(ValueError, match="expected a dictionary"):
        load_beats(yaml_path)


# ── log_beat_run ─────────────────────────────────────────────────────


def test_log_beat_run_creates_files(tmp_path, monkeypatch):
    """log_beat_run writes JSON log and appends to summary markdown."""
    logs = tmp_path / "test_logs"
    monkeypatch.setattr("src.services.beats.LOGS_DIR", logs)

    result = {
        "started_at": "2025-06-29T10:00:00",
        "duration_s": 12.5,
        "status": "success",
        "output": "Found 5 jobs matching the profile.",
        "tool_calls": 8,
        "cost_usd": 0.045,
        "errors": [],
    }
    log_beat_run("test-beat", result)

    # JSON log file exists
    json_files = list((logs / "test-beat").glob("*.json"))
    assert len(json_files) == 1
    log_data = json.loads(json_files[0].read_text())
    assert log_data["beat"] == "test-beat"
    assert log_data["status"] == "success"
    assert log_data["cost_usd"] == 0.045

    # Summary markdown was appended
    summary = (logs / "beat_summary.md").read_text()
    assert "test-beat" in summary
    assert "✓" in summary


def test_log_beat_run_error_status(tmp_path, monkeypatch):
    """log_beat_run uses ✗ for error status."""
    logs = tmp_path / "error_logs"
    monkeypatch.setattr("src.services.beats.LOGS_DIR", logs)

    result = {
        "started_at": "2025-06-29T10:00:00",
        "duration_s": 3.1,
        "status": "error",
        "output": None,
        "tool_calls": 1,
        "cost_usd": 0.01,
        "errors": ["ConnectionError: timeout"],
    }
    log_beat_run("failing-beat", result)

    summary = (logs / "beat_summary.md").read_text()
    assert "✗" in summary


# ── os_schedule_instructions ─────────────────────────────────────────


def test_os_schedule_instructions_returns_string():
    """Returns a non-empty string with OS-specific instructions."""
    result = os_schedule_instructions()
    assert isinstance(result, str)
    assert len(result) > 0
    assert "Schedule" in result or "cron" in result or "Task" in result


# ── os_schedule_instructions (OS branches) ────────────────────────────


def test_os_schedule_instructions_darwin():
    """MacOS path includes launchd and crontab options."""
    with patch("platform.system", return_value="Darwin"):
        result = os_schedule_instructions()
    assert "launchd" in result
    assert "crontab" in result


def test_os_schedule_instructions_windows():
    """Windows path includes Task Scheduler."""
    with patch("platform.system", return_value="Windows"):
        result = os_schedule_instructions()
    assert "Task Scheduler" in result


def test_os_schedule_instructions_other_os():
    """Unknown OS path returns a generic 'Run every 5 minutes' line."""
    with patch("platform.system", return_value="FreeBSD"):
        result = os_schedule_instructions()
    assert "Run every 5 minutes" in result


# ── run_beat ─────────────────────────────────────────────────────────


# Helper: fake agent result mimicking AgentRunResult
class FakeAgentResult:
    output: str = "Agent output here."
    usage: MagicMock
    response: MagicMock

    def __init__(
        self,
        *,
        output: str = "Agent output.",
        tool_calls: int = 3,
        cost_usd: float = 0.05,
    ):
        self.output = output
        self.usage = MagicMock(tool_calls=tool_calls)
        cost_mock = MagicMock()
        cost_mock.total_price = cost_usd
        self.response = MagicMock()
        self.response.cost.return_value = cost_mock

    def __str__(self):
        return self.output


def _make_beat(**overrides):
    """Minimal BeatConfig for run_beat tests."""
    defaults = {
        "name": "test-beat",
        "schedule": "0 9 * * *",
        "template": "default",
        "mode": "agent",
        "effort": "quick",
        "sub_agents": 5,
        "prompt_extra": "",
        "budget_override_usd": None,
        "notify_email": "test@example.com",
        "allowed_csvs": [],
    }
    defaults.update(overrides)
    return BeatConfig(**defaults)


def test_run_beat_not_found():
    """run_beat returns error when beat name is not in beats.yaml."""
    with patch("src.services.beats.load_beats", return_value={}):
        result = run_beat("nonexistent")
    assert result["status"] == "error"
    assert "not found" in result["errors"][0]


def test_run_beat_not_due_skipped():
    """run_beat returns skipped when cron schedule says not due yet."""
    beat = _make_beat(schedule="0 0 1 1 *")  # Jan 1 at midnight
    with patch("src.services.beats.load_beats", return_value={"test-beat": beat}):
        with patch(
            "src.services.beats.load_state",
            return_value={
                "test-beat": {"last_run": datetime.now(UTC).isoformat()},
            },
        ):
            with patch("src.services.beats.is_due", return_value=False):
                result = run_beat("test-beat")
    assert result["status"] == "skipped"


def test_run_beat_success_agent_mode():
    """Successful agent-mode beat returns success with output."""
    beat = _make_beat(mode="agent")
    fake = FakeAgentResult(output="All done.")

    with patch("src.services.beats.load_beats", return_value={"test-beat": beat}):
        with patch("src.services.beats.load_state", return_value={}):
            with patch("src.services.beats.save_state"):
                with patch("src.services.beats.log_beat_run"):
                    with patch("src.services.beats._send_beat_summary"):
                        with patch("src.services.beats.AibaSettings"):
                            with patch(
                                "src.services.beats.get_beat_allowed_csvs",
                                return_value=[],
                            ):
                                with patch("src.services.beats.set_beat_allowed_csvs"):
                                    with patch(
                                        "src.services.beats.get_template",
                                        return_value=_FAKE_TEMPLATES[0],
                                    ):
                                        with patch(
                                            "src.services.beats.run_agent",
                                            return_value=fake,
                                        ):
                                            result = run_beat("test-beat")

    assert result["status"] == "success"
    assert result["output"] == "All done."
    assert result["tool_calls"] == 3


def test_run_beat_success_swarm_mode():
    """Successful swarm-mode beat returns success with output."""
    beat = _make_beat(mode="swarm", sub_agents=3)
    fake = FakeAgentResult(output="Swarm done.", tool_calls=10, cost_usd=0.15)

    with patch("src.services.beats.load_beats", return_value={"test-beat": beat}):
        with patch("src.services.beats.load_state", return_value={}):
            with patch("src.services.beats.save_state"):
                with patch("src.services.beats.log_beat_run"):
                    with patch("src.services.beats._send_beat_summary"):
                        with patch("src.services.beats.AibaSettings"):
                            with patch(
                                "src.services.beats.get_beat_allowed_csvs",
                                return_value=[],
                            ):
                                with patch("src.services.beats.set_beat_allowed_csvs"):
                                    with patch(
                                        "src.services.beats.get_template",
                                        return_value=_FAKE_TEMPLATES[0],
                                    ):
                                        with patch(
                                            "src.services.beats.run_orch",
                                            return_value=fake,
                                        ):
                                            result = run_beat("test-beat")

    assert result["status"] == "success"
    assert result["output"] == "Swarm done."
    assert result["cost_usd"] == 0.15


def test_run_beat_cost_exception_falls_back_to_zero():
    """When cost().total_price raises, cost_usd becomes 0.0."""
    beat = _make_beat()
    fake = FakeAgentResult(output="OK")
    fake.response.cost.side_effect = RuntimeError("cost API down")

    with patch("src.services.beats.load_beats", return_value={"test-beat": beat}):
        with patch("src.services.beats.load_state", return_value={}):
            with patch("src.services.beats.save_state"):
                with patch("src.services.beats.log_beat_run"):
                    with patch("src.services.beats._send_beat_summary"):
                        with patch("src.services.beats.AibaSettings"):
                            with patch(
                                "src.services.beats.get_beat_allowed_csvs",
                                return_value=[],
                            ):
                                with patch("src.services.beats.set_beat_allowed_csvs"):
                                    with patch(
                                        "src.services.beats.get_template",
                                        return_value=_FAKE_TEMPLATES[0],
                                    ):
                                        with patch(
                                            "src.services.beats.run_agent",
                                            return_value=fake,
                                        ):
                                            result = run_beat("test-beat")

    assert result["status"] == "success"
    assert result["cost_usd"] == 0.0


def test_run_beat_exception_during_run():
    """When the agent raises, run_beat catches it and returns error status."""
    beat = _make_beat()

    with patch("src.services.beats.load_beats", return_value={"test-beat": beat}):
        with patch("src.services.beats.load_state", return_value={}):
            with patch("src.services.beats.save_state"):
                with patch("src.services.beats.log_beat_run"):
                    with patch("src.services.beats._send_beat_summary"):
                        with patch("src.services.beats.AibaSettings"):
                            with patch(
                                "src.services.beats.get_beat_allowed_csvs",
                                return_value=[],
                            ):
                                with patch("src.services.beats.set_beat_allowed_csvs"):
                                    with patch(
                                        "src.services.beats.get_template",
                                        return_value=_FAKE_TEMPLATES[0],
                                    ):
                                        with patch(
                                            "src.services.beats.run_agent",
                                            side_effect=ValueError("simulated crash"),
                                        ):
                                            result = run_beat("test-beat")

    assert result["status"] == "error"
    assert any("ValueError" in e for e in result["errors"])
    assert any("simulated crash" in e for e in result["errors"])
    assert result["cost_usd"] == 0
    assert result["tool_calls"] == 0


def test_run_beat_with_budget_override():
    """When beat.budget_override_usd is set, run_beat completes successfully."""
    beat = _make_beat(budget_override_usd=3.50)
    fake = FakeAgentResult()

    with patch("src.services.beats.load_beats", return_value={"test-beat": beat}):
        with patch("src.services.beats.load_state", return_value={}):
            with patch("src.services.beats.save_state"):
                with patch("src.services.beats.log_beat_run"):
                    with patch("src.services.beats._send_beat_summary"):
                        with patch("src.services.beats.AibaSettings"):
                            with patch(
                                "src.services.beats.get_beat_allowed_csvs",
                                return_value=[],
                            ):
                                with patch("src.services.beats.set_beat_allowed_csvs"):
                                    with patch(
                                        "src.services.beats.get_template",
                                        return_value=_FAKE_TEMPLATES[0],
                                    ):
                                        with patch(
                                            "src.services.beats.run_agent",
                                            return_value=fake,
                                        ):
                                            result = run_beat("test-beat")

    assert result["status"] == "success"


def test_run_beat_without_budget_override():
    """When beat.budget_override_usd is None, run_beat completes successfully."""
    beat = _make_beat(budget_override_usd=None)
    fake = FakeAgentResult()

    with patch("src.services.beats.load_beats", return_value={"test-beat": beat}):
        with patch("src.services.beats.load_state", return_value={}):
            with patch("src.services.beats.save_state"):
                with patch("src.services.beats.log_beat_run"):
                    with patch("src.services.beats._send_beat_summary"):
                        with patch("src.services.beats.AibaSettings"):
                            with patch(
                                "src.services.beats.get_beat_allowed_csvs",
                                return_value=[],
                            ):
                                with patch("src.services.beats.set_beat_allowed_csvs"):
                                    with patch(
                                        "src.services.beats.get_template",
                                        return_value=_FAKE_TEMPLATES[0],
                                    ):
                                        with patch(
                                            "src.services.beats.run_agent",
                                            return_value=fake,
                                        ):
                                            result = run_beat("test-beat")

    assert result["status"] == "success"


# ── run_all_due ──────────────────────────────────────────────────────


def test_run_all_due_runs_all_beats():
    """run_all_due calls run_beat for every loaded beat."""
    beat_a = _make_beat(name="a")
    beat_b = _make_beat(name="b")

    with (
        patch(
            "src.services.beats.load_beats",
            return_value={"a": beat_a, "b": beat_b},
        ),
        patch("src.services.beats.run_beat") as mock_run,
    ):
        mock_run.side_effect = [
            {"status": "success", "beat": "a"},
            {"status": "skipped", "beat": "b"},
        ]
        results = run_all_due()

    assert len(results) == 2
    assert mock_run.call_count == 2


# ── _send_beat_summary ───────────────────────────────────────────────


def _make_settings(**overrides):
    """Minimal mock settings for _send_beat_summary."""
    s = MagicMock()
    s.sender_email = "sender@example.com"
    s.smtp_host = "smtp.example.com"
    s.smtp_port = 587
    s.smtp_username = "user"
    s.smtp_password = "pass"
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


def test_send_beat_summary_success():
    """Success status sends email with green badge."""
    beat = _make_beat(notify_email="to@example.com")
    result = {
        "status": "success",
        "output": "Great work!",
        "duration_s": 5.2,
        "cost_usd": 0.03,
        "tool_calls": 2,
        "errors": [],
    }
    settings = _make_settings()

    with patch("smtplib.SMTP") as mock_smtp:
        _send_beat_summary(beat, result, settings)

    mock_smtp.assert_called_once()
    mock_smtp.return_value.__enter__.return_value.send_message.assert_called_once()


def test_send_beat_summary_error():
    """Error status sends email with red badge and error details."""
    beat = _make_beat(notify_email="to@example.com")
    result = {
        "status": "error",
        "output": None,
        "duration_s": 1.0,
        "cost_usd": 0.0,
        "tool_calls": 0,
        "errors": ["ValueError: something broke"],
    }
    settings = _make_settings()

    with patch("smtplib.SMTP") as mock_smtp:
        _send_beat_summary(beat, result, settings)

    mock_smtp.return_value.__enter__.return_value.send_message.assert_called_once()


def test_send_beat_summary_smtp_failure_no_crash():
    """SMTP failure is swallowed — doesn't propagate."""
    beat = _make_beat(notify_email="to@example.com")
    result = {
        "status": "success",
        "output": "OK",
        "duration_s": 1.0,
        "cost_usd": 0.01,
        "tool_calls": 1,
        "errors": [],
    }
    settings = _make_settings()

    with patch("smtplib.SMTP", side_effect=smtplib.SMTPException("connection refused")):
        # Should not raise
        _send_beat_summary(beat, result, settings)


def test_send_beat_summary_no_notify_email():
    """No notify_email set — returns early without sending."""
    # Use model_construct to bypass EmailStr validation
    beat = BeatConfig.model_construct(
        name="test",
        schedule="0 0 * * *",
        template="default",
        notify_email="",
    )
    result = {"status": "success", "output": "OK"}
    settings = _make_settings()

    with patch("smtplib.SMTP") as mock_smtp:
        _send_beat_summary(beat, result, settings)

    mock_smtp.assert_not_called()


def test_send_beat_summary_no_sender_email():
    """No sender_email in settings — returns early."""
    beat = _make_beat(notify_email="to@example.com")
    result = {"status": "success", "output": "OK"}
    settings = _make_settings()
    settings.sender_email = ""

    with patch("smtplib.SMTP") as mock_smtp:
        _send_beat_summary(beat, result, settings)

    mock_smtp.assert_not_called()


def test_send_beat_summary_with_markdown_output():
    """Output with markdown is converted to HTML."""
    beat = _make_beat(notify_email="to@example.com")
    result = {
        "status": "success",
        "output": "## Header\n\n**bold text**",
        "duration_s": 2,
        "cost_usd": 0.02,
        "tool_calls": 4,
        "errors": [],
    }
    settings = _make_settings()

    with patch("smtplib.SMTP") as mock_smtp:
        _send_beat_summary(beat, result, settings)

    mock_smtp.return_value.__enter__.return_value.send_message.assert_called_once()


def test_send_beat_summary_skipped_status():
    """Skipped status sends email with yellow warning badge."""
    beat = _make_beat(notify_email="to@example.com")
    result = {
        "status": "skipped",
        "output": "Not due",
        "duration_s": 0,
        "cost_usd": 0,
        "tool_calls": 0,
        "errors": [],
    }
    settings = _make_settings()

    with patch("smtplib.SMTP") as mock_smtp:
        _send_beat_summary(beat, result, settings)

    mock_smtp.return_value.__enter__.return_value.send_message.assert_called_once()

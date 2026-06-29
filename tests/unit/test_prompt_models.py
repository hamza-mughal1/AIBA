from __future__ import annotations

import pytest

from src.prompts.models import (
    Template,
    get_template,
    list_templates,
    register_template,
)


def _dummy_generator(user_profile: str, extra: str) -> str:
    return f"profile={user_profile} extra={extra}"


# ── Suite setup: register a template for each test ───────────────────

# NOTE: tests share the module-level _TEMPLATES dict. Each test
# registers a fresh copy to avoid cross-test leakage. The registry
# is dict-based so overwriting by name is fine.

_TEST_TEMPLATE = Template(
    name="test-tpl",
    description="A test template",
    generate_prompt=_dummy_generator,
)


# ── register / get / list round-trip ─────────────────────────────────


def test_register_and_get_template_round_trip():
    register_template(_TEST_TEMPLATE)
    t = get_template("test-tpl")
    assert t.name == "test-tpl"
    assert t.description == "A test template"


def test_get_template_returns_same_object():
    register_template(_TEST_TEMPLATE)
    t = get_template("test-tpl")
    assert t is _TEST_TEMPLATE


def test_get_template_missing_raises_keyerror():
    with pytest.raises(KeyError, match="no-such-tpl"):
        get_template("no-such-tpl")


def test_list_templates_includes_registered():
    register_template(_TEST_TEMPLATE)
    names = [t.name for t in list_templates()]
    assert "test-tpl" in names


def test_list_templates_is_not_empty():
    """At minimum the built-in templates are registered at import time."""
    templates = list_templates()
    assert len(templates) > 0


def test_template_generate_prompt_is_callable():
    register_template(_TEST_TEMPLATE)
    t = get_template("test-tpl")
    result = t.generate_prompt("Hamza", "use headless mode")
    assert "Hamza" in result
    assert "headless" in result


# ── Template dataclass ───────────────────────────────────────────────


def test_template_dataclass_fields():
    t = Template(name="t", description="d", generate_prompt=_dummy_generator)
    assert t.name == "t"
    assert t.description == "d"
    assert t.generate_prompt("p", "e") == "profile=p extra=e"

"""Template model and registry.

Templates control WHAT the agent does (job search, OSINT, general browsing).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class Template:
    """A usage template that generates a user prompt for the agent.

    Attributes:
        name: Unique identifier (e.g. 'job_search', 'osint').
        description: Human-readable explanation shown in the CLI picker.
        generate_prompt: Callable (user_profile, extra_context) -> prompt string.

    """

    name: str
    description: str
    generate_prompt: Callable[[str, str], str]


_TEMPLATES: dict[str, Template] = {}


def register_template(template: Template) -> None:
    """Register a template in the global registry."""
    _TEMPLATES[template.name] = template


def get_template(name: str) -> Template:
    """Look up a template by name. Raises KeyError if not found."""
    if name not in _TEMPLATES:
        available = ", ".join(_TEMPLATES.keys())
        raise KeyError(f"Template '{name}' not found. Available: {available}")
    return _TEMPLATES[name]


def list_templates() -> list[Template]:
    """Return all registered templates in insertion order."""
    return list(_TEMPLATES.values())

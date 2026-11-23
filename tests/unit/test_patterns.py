"""Unit tests for the pattern builder defaulting rules (DB-free, ADR-0011).

Two independent ``or``-fallback rules and their falsy edges:
- ``json_pattern or {"name": name, "groups": []}`` — a ``None`` or empty dict
  is replaced by the required composite default, never left empty.
- ``dsl_content or ""`` — absent or empty string falls back to ``""``.
Pinned as parameterized truth tables.
"""

from __future__ import annotations

import uuid

import pytest

from app.services import patterns

_PROJECT = uuid.UUID("00000000-0000-0000-0000-000000000001")
_COMPOSITE = {"name": "pat", "groups": []}


@pytest.mark.parametrize(
    ("json_pattern", "expected"),
    [
        (None, _COMPOSITE),  # absent -> composite default
        ({}, _COMPOSITE),  # empty dict is falsy -> composite default
        (
            {"name": "full", "groups": [{"id": "g1"}]},
            {"name": "full", "groups": [{"id": "g1"}]},
        ),
    ],
)
def test_create_pattern_json_pattern_defaulting(
    json_pattern: dict | None, expected: dict
) -> None:
    pattern = patterns.create_pattern(
        project_id=_PROJECT,
        name="pat",
        json_pattern=json_pattern,
        dsl_content="x",
    )
    assert pattern.json_pattern == expected


@pytest.mark.parametrize(
    ("dsl_content", "expected"),
    [
        (None, ""),  # absent -> ""
        ("", ""),  # empty string is falsy -> ""
        ("dsl-body", "dsl-body"),
    ],
)
def test_create_pattern_dsl_content_defaulting(
    dsl_content: str | None, expected: str
) -> None:
    pattern = patterns.create_pattern(
        project_id=_PROJECT,
        name="pat",
        json_pattern=_COMPOSITE,
        dsl_content=dsl_content,
    )
    assert pattern.dsl_content == expected

"""Unit tests for the pattern builder defaulting rules (DB-free, ADR-0011)."""

import uuid

from app.services import patterns


def test_create_pattern_defaults_composite_json_pattern() -> None:
    project_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    pattern = patterns.create_pattern(project_id=project_id, name="solo-pat")
    assert pattern.json_pattern == {"name": "solo-pat", "groups": []}
    assert pattern.dsl_content == ""
    assert pattern.name == "solo-pat"


def test_create_pattern_keeps_provided_json_and_uses_dsl() -> None:
    project_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    payload = {"name": "full-pat", "groups": [{"id": "g1"}]}
    pattern = patterns.create_pattern(
        project_id=project_id,
        name="full-pat",
        json_pattern=payload,
        dsl_content="dsl-body",
    )
    assert pattern.json_pattern == payload
    assert pattern.dsl_content == "dsl-body"
    assert pattern.name == "full-pat"

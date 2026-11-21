"""Unit tests for the pattern service creation/defaulting rules."""

import uuid

from sqlmodel import Session

import app.db.models as M
from app.services import patterns


def _parent_project(session: Session) -> uuid.UUID:
    project = M.Project(name="parent")
    session.add(project)
    session.flush()
    return project.id


def test_save_pattern_defaults_composite_json_pattern(session: Session) -> None:
    project_id = _parent_project(session)
    pattern = patterns.save_pattern(project_id=project_id, name="solo-pat")
    assert pattern.json_pattern == {"name": "solo-pat", "groups": []}
    assert pattern.dsl_content == ""
    session.flush()
    assert pattern.name == "solo-pat"


def test_save_pattern_keeps_provided_json_and_uses_dsl(session: Session) -> None:
    project_id = _parent_project(session)
    payload = {"name": "full-pat", "groups": [{"id": "g1"}]}
    pattern = patterns.save_pattern(
        project_id=project_id,
        name="full-pat",
        json_pattern=payload,
        dsl_content="dsl-body",
    )
    assert pattern.json_pattern == payload
    assert pattern.dsl_content == "dsl-body"
    session.flush()


def test_delete_pattern_returns_false_when_missing(session: Session) -> None:
    assert patterns.delete_pattern(session, uuid.uuid4()) is False

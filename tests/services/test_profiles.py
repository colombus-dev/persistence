"""Unit tests for the profile service creation/defaulting rules."""

import uuid

from sqlmodel import Session

import app.db.models as M
from app.services import profiles


def _parent_project(session: Session) -> uuid.UUID:
    project = M.Project(name="parent")
    session.add(project)
    session.flush()
    return project.id


def test_create_profile_defaults_json_profile_to_empty(session: Session) -> None:
    project_id = _parent_project(session)
    profile = profiles.create_profile(
        project_id=project_id,
        name="no-json",
        score=2.0,
        encoded_profile="enc",
    )
    assert profile.json_profile == {}
    session.add(profile)
    session.flush()
    assert profile.project_id == project_id
    assert profile.name == "no-json"
    assert profile.score == 2.0


def test_create_profile_keeps_provided_json_profile(session: Session) -> None:
    project_id = _parent_project(session)
    payload = {"name": "with-json", "source": []}
    profile = profiles.create_profile(
        project_id=project_id,
        name="with-json",
        score=3.0,
        encoded_profile="enc",
        json_profile=payload,
    )
    assert profile.json_profile == payload
    assert profile.name == "with-json"


def test_delete_profile_returns_true_when_found(session: Session) -> None:
    pid = _parent_project(session)
    profile = profiles.create_profile(
        project_id=pid, name="del", score=1.0, encoded_profile="x"
    )
    session.add(profile)
    session.flush()
    assert profiles.delete_profile(session, profile.id) is True
    session.flush()


def test_delete_profile_returns_false_when_missing(session: Session) -> None:
    assert profiles.delete_profile(session, uuid.uuid4()) is False

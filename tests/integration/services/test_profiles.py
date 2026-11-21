"""Integration tests for the profile deletion service (DB-bound, ADR-0011)."""

import uuid

from sqlmodel import Session

import app.db.models as M
from app.services import profiles


def _parent_project(session: Session) -> uuid.UUID:
    project = M.Project(name="parent")
    session.add(project)
    session.flush()
    return project.id


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

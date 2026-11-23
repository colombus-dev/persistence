"""Integration tests for the project deletion service (DB-bound, ADR-0011)."""

import uuid

from sqlmodel import Session

import app.db.models as M
from app.services import projects


def test_delete_project_returns_true_and_removes_row(session: Session) -> None:
    project = projects.create_project(name="doomed")
    session.add(project)
    session.flush()
    assert projects.delete_project(session, project.id) is True
    session.flush()
    assert session.get(M.Project, project.id) is None


def test_delete_project_returns_false_when_missing(session: Session) -> None:
    assert projects.delete_project(session, uuid.uuid4()) is False

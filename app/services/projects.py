"""Project create and delete service for the persistence API.

Holds the project rules that used to be inlined in the GraphQL
``createProject`` / ``deleteProject`` mutation resolvers, mirroring the
profile/pattern services so every domain rule lives in ``app/services/``
(ADR-0012).
"""

from __future__ import annotations

import uuid

from sqlmodel import Session

import app.db.models as models


def create_project(*, name: str) -> models.Project:
    """Build a ``Project`` row from its name."""
    return models.Project(name=name)


def delete_project(session: Session, id: uuid.UUID) -> bool:
    """Delete a project by id; return whether a row was removed."""
    project = session.get(models.Project, id)
    if project is None:
        return False
    session.delete(project)
    return True

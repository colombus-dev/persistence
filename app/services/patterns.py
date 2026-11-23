"""Pattern save and delete service for the persistence API.

Holds the domain rules previously inlined in the GraphQL ``savePattern`` /
``deletePattern`` mutation resolvers: defaulting an absent ``json_pattern`` to
``{"name": ..., "groups": []}`` and an absent ``dsl_content`` to ``""``.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlmodel import Session

import app.db.models as models


def create_pattern(
    *,
    project_id: uuid.UUID,
    name: str,
    json_pattern: dict[str, Any] | None = None,
    dsl_content: str | None = None,
) -> models.Pattern:
    """Build a ``Pattern`` row, defaulting json/dsl when not supplied."""
    return models.Pattern(
        project_id=project_id,
        name=name,
        json_pattern=json_pattern or {"name": name, "groups": []},
        dsl_content=dsl_content or "",
    )


def delete_pattern(session: Session, id: uuid.UUID) -> bool:
    """Delete a pattern by id; return whether a row was removed."""
    pattern = session.get(models.Pattern, id)
    if pattern is None:
        return False
    session.delete(pattern)
    return True

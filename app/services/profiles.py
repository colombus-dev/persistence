"""Profile creation and deletion service for the persistence API.

Holds the domain rules previously inlined in the GraphQL ``createProfile`` /
``deleteProfile`` mutation resolvers, notably the default to ``{}`` when no
``json_profile`` document is supplied.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlmodel import Session

import app.db.models as models


def create_profile(
    *,
    project_id: uuid.UUID,
    name: str,
    score: float,
    encoded_profile: str,
    json_profile: dict[str, Any] | None = None,
) -> models.Profile:
    """Build a ``Profile`` row, defaulting an absent ``json_profile`` to ``{}``."""
    return models.Profile(
        project_id=project_id,
        name=name,
        score=score,
        encoded_profile=encoded_profile,
        json_profile=json_profile or {},
    )


def delete_profile(session: Session, id: uuid.UUID) -> bool:
    """Delete a profile by id; return whether a row was removed."""
    profile = session.get(models.Profile, id)
    if profile is None:
        return False
    session.delete(profile)
    return True

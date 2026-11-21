"""Root GraphQL query (read) surface for the persistence API.

Resolvers read from the SQLAlchemy session placed in the request context
(``info.context["session"]``).
"""

from __future__ import annotations

import uuid

import strawberry
from sqlmodel import Session, select

import app.db.models as models
from app.graphql.types import (
    MatchingProfileType,
    PatternType,
    ProfileType,
    ProjectType,
)


@strawberry.type
class Query:
    """Root query type for the persistence GraphQL API."""

    @strawberry.field
    def projects(self, info: strawberry.Info) -> list[ProjectType]:
        session: Session = info.context["session"]
        return list(  # type: ignore[bad-return]  # mapper types are runtime-generated
            session.scalars(select(models.Project).order_by(models.Project.name))
        )

    @strawberry.field
    def project(self, info: strawberry.Info, id: uuid.UUID) -> ProjectType | None:
        session: Session = info.context["session"]
        return session.get(models.Project, id)  # type: ignore[bad-return]

    @strawberry.field
    def profiles(self, info: strawberry.Info) -> list[ProfileType]:
        session: Session = info.context["session"]
        return list(  # type: ignore[bad-return]
            session.scalars(select(models.Profile).order_by(models.Profile.name))
        )

    @strawberry.field
    def profile(self, info: strawberry.Info, id: uuid.UUID) -> ProfileType | None:
        session: Session = info.context["session"]
        return session.get(models.Profile, id)  # type: ignore[bad-return]

    @strawberry.field
    def patterns(self, info: strawberry.Info) -> list[PatternType]:
        session: Session = info.context["session"]
        return list(  # type: ignore[bad-return]
            session.scalars(select(models.Pattern).order_by(models.Pattern.name))
        )

    @strawberry.field
    def matching_profiles(self, info: strawberry.Info) -> list[MatchingProfileType]:
        """All stored (pattern, profile) match results."""
        session: Session = info.context["session"]
        return list(  # type: ignore[bad-return]
            session.scalars(
                select(models.MatchingProfile).order_by(
                    models.MatchingProfile.pattern_hash
                )
            )
        )

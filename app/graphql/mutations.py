"""Root GraphQL mutation (write) surface for the persistence API.

Mutations own create/delete of projects and profiles plus save/delete of
patterns (ADR-0006). Resolvers read from the SQLAlchemy session placed in the
request context (``info.context["session"]``).
"""

from __future__ import annotations

import uuid
from typing import Any, cast

import strawberry
from sqlmodel import Session
from strawberry.scalars import JSON as StrawberryJSON

import app.db.models as models
from app.graphql.types import PatternType, ProfileType, ProjectType
from app.services import patterns, profiles


@strawberry.type
class MutationResult:
    """Result envelope for delete operations."""

    ok: bool


@strawberry.type
class Mutation:
    """Root mutation type for the persistence GraphQL API."""

    @strawberry.mutation
    def create_project(self, info: strawberry.Info, name: str) -> ProjectType:
        session: Session = info.context["session"]
        project = models.Project(name=name)
        session.add(project)
        session.commit()
        session.refresh(project)
        return project  # type: ignore[bad-return]

    @strawberry.mutation
    def delete_project(self, info: strawberry.Info, id: uuid.UUID) -> MutationResult:
        session: Session = info.context["session"]
        project = session.get(models.Project, id)
        if project is None:
            return MutationResult(ok=False)
        session.delete(project)
        session.commit()
        return MutationResult(ok=True)

    @strawberry.mutation
    def create_profile(
        self,
        info: strawberry.Info,
        project_id: uuid.UUID,
        name: str,
        score: float,
        encoded_profile: str,
        json_profile: StrawberryJSON | None = None,
    ) -> ProfileType:
        session: Session = info.context["session"]
        profile = profiles.create_profile(
            project_id=project_id,
            name=name,
            score=score,
            encoded_profile=encoded_profile,
            json_profile=cast(dict[str, Any], json_profile),
        )
        session.add(profile)
        session.commit()
        session.refresh(profile)
        return profile  # type: ignore[bad-return]

    @strawberry.mutation
    def delete_profile(self, info: strawberry.Info, id: uuid.UUID) -> MutationResult:
        session: Session = info.context["session"]
        if not profiles.delete_profile(session, id):
            return MutationResult(ok=False)
        session.commit()
        return MutationResult(ok=True)

    @strawberry.mutation
    def save_pattern(
        self,
        info: strawberry.Info,
        project_id: uuid.UUID,
        name: str,
        json_pattern: StrawberryJSON | None = None,
        dsl_content: str | None = None,
    ) -> PatternType:
        session: Session = info.context["session"]
        pattern = patterns.save_pattern(
            project_id=project_id,
            name=name,
            json_pattern=cast(dict[str, Any], json_pattern),
            dsl_content=dsl_content,
        )
        session.add(pattern)
        session.commit()
        session.refresh(pattern)
        return pattern  # type: ignore[bad-return]

    @strawberry.mutation
    def delete_pattern(self, info: strawberry.Info, id: uuid.UUID) -> MutationResult:
        session: Session = info.context["session"]
        if not patterns.delete_pattern(session, id):
            return MutationResult(ok=False)
        session.commit()
        return MutationResult(ok=True)

"""GraphQL schema for the persistence API.

Read-only query layer over the domain tables, generated with
``strawberry-sqlalchemy-mapper`` (``always_use_list=True``). Auto-mapped types
cover ``Project``, ``Profile``, ``Step``, ``CellOutput``, ``MetaInstruction``,
``Code`` and ``Pattern``; ``MatchingProfile`` is exposed manually because its
composite primary key (``pattern_hash``, ``profile_id``) has no scalar ``id``
the mapper would expose as a single GraphQL field.

Resolvers read from the SQLAlchemy session placed in the request context
(``info.context["session"]``) and use the mapper's dataloader
(``info.context["sqlalchemy_loader"]``) for relationship batching. Mutations are
delivered in a later slice (ADR-0006).
"""

from __future__ import annotations

import uuid
from collections.abc import Generator

import strawberry
from sqlalchemy import Uuid
from sqlmodel import Session, select
from sqlmodel.sql.sqltypes import AutoString
from strawberry_sqlalchemy_mapper import (
    StrawberrySQLAlchemyLoader,
    StrawberrySQLAlchemyMapper,
)

import app.db.models as models

_mapper = StrawberrySQLAlchemyMapper(always_use_list=True)
# The mapper ships mappings for Postgres `UUID`/`String`; our SQLModel columns
# are typed as generic `Uuid`/`AutoString`, which are distinct classes, so we
# teach the mapper to treat them as UUID and str.
_mapper.sqlalchemy_type_to_strawberry_type_map[Uuid] = uuid.UUID
_mapper.sqlalchemy_type_to_strawberry_type_map[AutoString] = str

_schema: strawberry.Schema | None = None


@_mapper.type(models.Project)
class ProjectType:
    pass


@_mapper.type(models.Profile)
class ProfileType:
    pass


@_mapper.type(models.Step)
class StepType:
    pass


@_mapper.type(models.CellOutput)
class CellOutputType:
    pass


@_mapper.type(models.MetaInstruction)
class MetaInstructionType:
    pass


@_mapper.type(models.Code)
class CodeType:
    pass


@_mapper.type(models.Pattern)
class PatternType:
    pass


@strawberry.type
class MatchingProfileType:
    """A (pattern, profile) match result.

    Manually defined because ``MatchingProfile`` uses a composite primary key
    (``pattern_hash`` + ``profile_id``) and has no scalar ``id``; the mapper
    would not expose a single meaningful key field.
    """

    pattern_hash: str
    profile_id: uuid.UUID

    @strawberry.field
    def profile(self, info: strawberry.Info) -> ProfileType:
        session: Session = info.context["session"]
        result = session.get(models.Profile, self.profile_id)
        assert result is not None
        return result  # type: ignore[bad-return]  # mapper types are runtime-generated


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

    @strawberry.field
    def one_plus_one(self) -> int:
        """A trivial scalar field proving the query endpoint responds."""
        return 2


def finalize_schema() -> strawberry.Schema:
    """Return the (lazily built) Strawberry schema for the query layer."""
    global _schema
    if _schema is None:
        _mapper.finalize()
        _schema = strawberry.Schema(query=Query)
    return _schema


def build_schema_context(session: Session) -> dict:
    """Build a GraphQL request context bound to ``session``."""
    return {
        "session": session,
        "sqlalchemy_loader": StrawberrySQLAlchemyLoader(bind=session),
    }


def get_graphql_context() -> Generator[dict]:
    """Open a DB session and loader for a GraphQL request.

    Generator suitable for ``GraphQLRouter(context_getter=...)``: yields the
    request context, then closes the session when the request completes so no
    session is leaked across requests.
    """
    from app.db.session import engine

    with Session(engine) as session:
        yield build_schema_context(session)


# Backwards-compatible reference kept so existing imports still resolve.
schema: strawberry.Schema = finalize_schema()

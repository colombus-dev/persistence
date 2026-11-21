"""GraphQL type definitions for the persistence API.

Read types are generated with ``strawberry-sqlalchemy-mapper``
(``always_use_list=True``) over the domain tables. ``MatchingProfile`` is
exposed manually because its composite primary key (``pattern_hash``,
``profile_id``) has no scalar ``id`` the mapper would expose as a single
GraphQL field.
"""

from __future__ import annotations

import uuid

import strawberry
from sqlalchemy import Uuid
from sqlmodel import Session
from sqlmodel.sql.sqltypes import AutoString
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyMapper

import app.db.models as models

_mapper = StrawberrySQLAlchemyMapper(always_use_list=True)
# The mapper ships mappings for Postgres `UUID`/`String`; our SQLModel columns
# are typed as generic `Uuid`/`AutoString`, which are distinct classes, so we
# teach the mapper to treat them as UUID and str.
_mapper.sqlalchemy_type_to_strawberry_type_map[Uuid] = uuid.UUID
_mapper.sqlalchemy_type_to_strawberry_type_map[AutoString] = str


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

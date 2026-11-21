"""Domain SQLModel tables owned by the persistence service.

Ported from colombus' ``app/models/sql_model.py``. Only table definitions live
here; the engine and DB session are handled in :mod:`app.db.session`. Column
types, constraints and indexes are kept byte-for-byte compatible with what
colombus defines so the schema is a faithful migration target.
"""

import uuid
from typing import Any, Optional

from sqlalchemy import Index
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import relationship
from sqlmodel import (
    JSON,
    Column,
    Field,
    Relationship,
    SQLModel,
    String,
)

ProjectIdFk: Any = Field(default=None, foreign_key="project.id", ondelete="CASCADE")
ProfileIdFk: Any = Field(
    default=None, foreign_key="profile.id", ondelete="CASCADE", index=True
)
LongString: Any = String().with_variant(mysql.LONGTEXT(), "mysql", "mariadb")


# "app management"-related tables


class Project(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str

    profiles: list[Profile] = Relationship(
        back_populates="project",
        sa_relationship=relationship(order_by="asc(Profile.name)"),
    )
    patterns: list[Pattern] = Relationship(
        back_populates="project",
        sa_relationship=relationship(order_by="asc(Pattern.name)"),
    )


# Profile-related tables


class ProfileBase(SQLModel):
    name: str


class Profile(ProfileBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = ProjectIdFk
    score: float
    json_profile: dict[str, Any] = Field(sa_type=JSON)
    encoded_profile: str

    steps: list[Step] = Relationship(
        back_populates="profile",
        sa_relationship=relationship(order_by="asc(Step.position)"),
    )
    meta_instructions: list[MetaInstruction] = Relationship(
        back_populates="profile",
        sa_relationship=relationship(order_by="asc(MetaInstruction.position)"),
    )
    codes: list[Code] = Relationship(
        back_populates="profile",
        sa_relationship=relationship(order_by="asc(Code.position)"),
    )
    project: Project = Relationship(back_populates="profiles")


class StepBase(SQLModel):
    name: str
    position: int
    # number of children is cached and used to compute graph nodes size
    number_children: int


class Step(StepBase, table=True):
    __table_args__ = (Index("ix_step_profile_id_position", "profile_id", "position"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)

    previous_step_id: uuid.UUID | None = Field(
        default=None, foreign_key="step.id", ondelete="CASCADE", index=True
    )
    previous_step: Optional["Step"] = Relationship(
        back_populates="next_step",
        sa_relationship_kwargs={"remote_side": "Step.id", "uselist": False},
    )

    next_step: Optional["Step"] = Relationship(back_populates="previous_step")

    profile_id: uuid.UUID | None = ProfileIdFk
    profile: Profile = Relationship(back_populates="steps")

    meta_instructions: list[MetaInstruction] = Relationship(back_populates="step")

    cell_outputs: list[CellOutput] = Relationship(back_populates="step")


class CellOutput(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    image: str

    step_id: uuid.UUID | None = Field(
        default=None, foreign_key="step.id", ondelete="CASCADE", index=True
    )
    step: Step = Relationship(back_populates="cell_outputs")


class MetaInstructionBase(SQLModel):
    algoFamily: str | None = None
    algoName: str | None = None
    library: str | None = None
    function: str | None = None
    position: int
    # number of children is cached and used to compute graph nodes size
    number_children: int


class MetaInstruction(MetaInstructionBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    profile_id: uuid.UUID | None = ProfileIdFk
    profile: Profile = Relationship(back_populates="meta_instructions")

    step_id: uuid.UUID | None = Field(
        default=None, foreign_key="step.id", ondelete="CASCADE", index=True
    )
    step: Step = Relationship(back_populates="meta_instructions")

    codes: list[Code] = Relationship(back_populates="meta_instruction")


class CodeBase(SQLModel):
    content: str = Field(sa_column=Column(LongString))
    position: int


class Code(CodeBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    profile_id: uuid.UUID | None = ProfileIdFk
    profile: Profile = Relationship(back_populates="codes")

    meta_instruction_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="metainstruction.id",
        ondelete="CASCADE",
        index=True,
    )
    meta_instruction: MetaInstruction = Relationship(back_populates="codes")


# PPM-related tables


class Pattern(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = ProjectIdFk
    name: str
    json_pattern: dict[str, Any] = Field(sa_type=JSON)
    dsl_content: str

    project: Project = Relationship(back_populates="patterns")


# Query results-related tables


class MatchingProfile(SQLModel, table=True):
    pattern_hash: str = Field(primary_key=True)
    profile_id: uuid.UUID = Field(primary_key=True, foreign_key="profile.id")
    # One-directional many-to-one so the mapper's dataloader can batch
    # `profile_id -> Profile` lookups (ADR-0010). No back-populates: a reverse
    # `matchingProfiles` collection on Profile would need a manual GraphQL type
    # and is not exposed. Relationships add no columns, so this is mapper-only.
    profile: "Profile" = Relationship()

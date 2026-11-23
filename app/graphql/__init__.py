"""GraphQL schema for the persistence API.

Re-exports the stable public symbols of the split graphql package (root query
and mutation types, context helpers, and the assembled schema) so existing
imports continue to resolve unchanged.
"""

from app.graphql.context import build_schema_context, get_graphql_context
from app.graphql.mutations import Mutation, MutationResult
from app.graphql.queries import Query
from app.graphql.schema import finalize_schema, schema
from app.graphql.types import (
    CellOutputType,
    CodeType,
    MatchingProfileType,
    MetaInstructionType,
    PatternType,
    ProfileType,
    ProjectType,
    StepType,
)

__all__ = [
    "build_schema_context",
    "get_graphql_context",
    "Mutation",
    "MutationResult",
    "Query",
    "finalize_schema",
    "schema",
    "CellOutputType",
    "CodeType",
    "MatchingProfileType",
    "MetaInstructionType",
    "PatternType",
    "ProfileType",
    "ProjectType",
    "StepType",
]

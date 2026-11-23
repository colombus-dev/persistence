"""Schema assembly for the persistence GraphQL API.

Builds the Strawberry schema lazily (the mapper must be finalized exactly once
before the schema is constructed) and memoizes the result.
"""

from __future__ import annotations

import strawberry

from app.graphql.mutations import Mutation
from app.graphql.queries import Query
from app.graphql.types import _mapper

_schema: strawberry.Schema | None = None


def finalize_schema() -> strawberry.Schema:
    """Return the (lazily built) Strawberry schema for the query layer."""
    global _schema
    if _schema is None:
        _mapper.finalize()
        _schema = strawberry.Schema(query=Query, mutation=Mutation)
    return _schema


# Backwards-compatible reference kept so existing imports still resolve.
schema: strawberry.Schema = finalize_schema()

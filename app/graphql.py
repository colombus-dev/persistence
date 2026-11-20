"""GraphQL schema for the persistence API.

The schema is deliberately minimal — a single ``hello`` query field that
proves the GraphQL serving path end-to-end before a real domain model
exists. The design rationale is recorded in
``documents/adr/0001-graphql-strawberry.md``.
"""

import strawberry


@strawberry.type
class Query:
    """Root query type of the GraphQL schema."""

    @strawberry.field
    def hello(self) -> str:
        """Return a static greeting as a placeholder for real resolvers."""
        return "world"


schema = strawberry.Schema(query=Query)

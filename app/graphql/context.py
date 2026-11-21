"""Request-context construction for the persistence GraphQL API.

Builds a Strawberry request context bound to a SQLAlchemy session, including
the mapper's dataloader used for relationship batching.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyLoader


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

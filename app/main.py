"""FastAPI application entrypoint for the persistence API.

Builds the FastAPI app and mounts the Strawberry GraphQL router at ``/graphql``.
The demo REST ``/items`` scaffold was removed in the cleanup slice; the query
and mutation surface is served entirely through GraphQL.
"""

from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from app.core.config import settings
from app.graphql import get_graphql_context, schema

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

graphql_app: GraphQLRouter = GraphQLRouter(  # type: ignore[type-var]
    schema=schema, context_getter=get_graphql_context
)
app.include_router(graphql_app, prefix="/graphql")

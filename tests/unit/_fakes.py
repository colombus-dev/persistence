"""Shared DB-free fakes for the resolver mock-seam tests (ADR-0011, Stage 2).

The seams prove contracts, not wiring-under-test: the session seam stubs the
resolver's ``info.context["session"]`` (add/commit/refresh/scalars/get), and
resolvers never see a real DB. Services are patched at the boundary, never
tested through a bare ``Mock``.
"""

from __future__ import annotations

import asyncio
from typing import Any

import strawberry


def run_gql(
    schema: strawberry.Schema,
    query: str,
    context: dict[str, Any],
    variables: dict[str, Any] | None = None,
) -> dict:
    """Execute a GraphQL operation against ``schema`` with a given context.

    DB-free: ``context`` carries a fake ``session``/loader, so no SQL runs.
    """

    async def run() -> dict:
        result = await schema.execute(
            query, context_value=context, variable_values=variables
        )
        assert result.errors is None, result.errors
        assert result.data is not None
        return result.data

    return asyncio.run(run())


class FakeSession:
    """A recording stand-in for ``sqlmodel.Session`` at the resolver boundary.

    Implementations remember what the resolver did to the session (``add`` /
    ``commit`` / ``refresh``) and serve pre-seeded ``scalars``/``get`` results so
    read and mutation write contracts can be asserted without a DB.
    """

    def __init__(
        self,
        scalars_result: list[Any] | None = None,
        get_result: Any = None,
    ) -> None:
        self.added: list[Any] = []
        self.deleted: list[Any] = []
        self.committed = False
        self.refreshed: list[Any] = []
        self._scalars_result = scalars_result or []
        self._get_result = get_result

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    def commit(self) -> None:
        self.committed = True

    def delete(self, obj: Any) -> None:
        self.deleted.append(obj)

    def refresh(self, obj: Any) -> None:
        self.refreshed.append(obj)

    def scalars(self, statement: Any) -> list[Any]:  # noqa: ARG002
        return self._scalars_result

    def get(self, model: Any, ident: Any) -> Any:  # noqa: ARG002
        return self._get_result

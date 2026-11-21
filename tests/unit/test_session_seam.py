"""Session mock seam: resolvers read `info.context["session"]` (DB-free).

Proves two contracts without a database (ADR-0011 Stage 2):
1. Query resolvers read the session from the request context and map rows
   through the generated read types (both the list path via `scalars` and the
   single lookup via `get`).
2. Mutations drive a real session correlation `add -> commit -> refresh`.

The session is a recording stub (`_fakes.FakeSession`), never a real DB, and
the rows served are real in-memory ``models.*`` instances.
"""

from __future__ import annotations

import app.db.models as M
from app.graphql import finalize_schema
from tests.unit._fakes import FakeSession, run_gql

schema = finalize_schema()


def _project(name: str) -> M.Project:
    return M.Project(name=name)


def test_projects_query_reads_session_from_context_and_maps_rows() -> None:
    session = FakeSession(scalars_result=[_project("alpha"), _project("beta")])
    data = run_gql(
        schema,
        "{ projects { id name } }",
        context={"session": session},
    )
    assert [p["name"] for p in data["projects"]] == ["alpha", "beta"]
    assert all(p["id"] for p in data["projects"])


def test_project_query_uses_get_on_context_session() -> None:
    project = _project("single")
    session = FakeSession(get_result=project)
    data = run_gql(
        schema,
        'query { project(id: "00000000-0000-0000-0000-000000000001") { name } }',
        context={"session": session},
    )
    assert data["project"] == {"name": "single"}


def test_create_project_adds_commits_refreshes_on_context_session() -> None:
    session = FakeSession()
    data = run_gql(
        schema,
        "mutation($name: String!) { createProject(name: $name) { id name } }",
        context={"session": session},
        variables={"name": "made"},
    )
    assert data["createProject"]["name"] == "made"
    (added,) = session.added
    assert isinstance(added, M.Project)
    assert added.name == "made"
    assert session.committed is True
    assert session.refreshed == [added]

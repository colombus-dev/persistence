"""Tests for the GraphQL read query layer (slice 5).

Covers the auto-mapped domain types and the per-request session wiring used by
both the router and direct ``execute`` invocations. Queries run against the
``app_test`` database through the transactional session fixture.
"""

import asyncio

from sqlmodel import Session, select

import app.db.models as M
from app.graphql import build_schema_context, finalize_schema
from tests.profile_types import ProfileJson
from tests.profile_utils import ingest_profile


def _execute(session: Session, query: str, variable_values: dict | None = None) -> dict:
    schema = finalize_schema()

    async def run() -> dict:
        ctx = build_schema_context(session)
        result = await schema.execute(
            query, context_value=ctx, variable_values=variable_values
        )
        assert result.errors is None, result.errors
        assert result.data is not None
        return result.data

    return asyncio.run(run())


def test_schema_exposes_domain_types() -> None:
    """The auto-mapped types are registered on the schema."""
    sdl = str(finalize_schema())
    for type_name in (
        "Project",
        "Profile",
        "Step",
        "CellOutput",
        "MetaInstruction",
        "Code",
        "Pattern",
        "MatchingProfile",
    ):
        assert f"type {type_name}" in sdl


def test_projects_query_round_trips(session: Session) -> None:
    project = M.Project(name="gql-proj")
    session.add(project)
    session.flush()

    data = _execute(session, "{ projects { id name } }")
    names = [p["name"] for p in data["projects"]]
    assert "gql-proj" in names


def test_profiles_nested_graph_round_trips(
    session: Session, full_profile: ProfileJson
) -> None:
    project = M.Project(name="parent")
    session.add(project)
    session.flush()
    ingest_profile(session, project.id, full_profile)
    session.flush()
    profile_row = next(session.exec(select(M.Profile)))

    data = _execute(
        session,
        """
        query($id: UUID!) {
          profile(id: $id) {
            id
            name
            encodedProfile
            project { id name }
            steps { id name metaInstructions { algoFamily } }
          }
        }
        """,
        {"id": str(profile_row.id)},
    )
    assert data["profile"]["name"] == full_profile["name"]
    assert len(data["profile"]["steps"]) == len(full_profile["source"])


def test_projects_relationship_lists(session: Session) -> None:
    project = M.Project(name="nested-proj")
    session.add(project)
    session.flush()
    ingest_profile(
        session,
        project.id,
        {"name": "p", "score": None, "source": [], "outputs": {}},
    )
    session.flush()

    data = _execute(session, "{ projects { name profiles { name } } }")
    proj = next(p for p in data["projects"] if p["name"] == "nested-proj")
    assert proj["profiles"] == [{"name": "p"}]


def test_projects_requires_no_extra_context(session: Session) -> None:
    data = _execute(session, "{ projects { id name } }")
    assert "projects" in data


def test_project_lookup_by_id(session: Session) -> None:
    project = M.Project(name="lookup")
    session.add(project)
    session.flush()

    data = _execute(
        session,
        "query($id: UUID!) { project(id: $id) { name } }",
        {"id": str(project.id)},
    )
    assert data["project"]["name"] == "lookup"


def test_matching_profiles_query(session: Session) -> None:
    project = M.Project(name="mp-proj")
    session.add(project)
    session.flush()
    profile = ingest_profile(
        session, project.id, {"name": "mp", "score": 1.0, "source": [], "outputs": {}}
    )
    session.flush()
    session.add(M.MatchingProfile(pattern_hash="abc123", profile_id=profile.id))
    session.flush()

    data = _execute(session, "{ matchingProfiles { patternHash profileId } }")
    assert any(mp["patternHash"] == "abc123" for mp in data["matchingProfiles"])


def test_matching_profile_fetch_profile(session: Session) -> None:
    project = M.Project(name="mp-fetch")
    session.add(project)
    session.flush()
    profile = ingest_profile(
        session, project.id, {"name": "mpf", "score": 1.0, "source": [], "outputs": {}}
    )
    session.flush()
    session.add(M.MatchingProfile(pattern_hash="h1", profile_id=profile.id))
    session.flush()

    data = _execute(
        session,
        "{ matchingProfiles { patternHash profile { id name } } }",
    )
    assert data["matchingProfiles"][0]["profile"]["name"] == "mpf"


def test_profile_lookup_by_id(session: Session) -> None:
    project = M.Project(name="p-lookup")
    session.add(project)
    session.flush()
    profile = ingest_profile(
        session, project.id, {"name": "pl", "score": 0.0, "source": [], "outputs": {}}
    )

    data = _execute(
        session,
        "query($id: UUID!) { profile(id: $id) { name } }",
        {"id": str(profile.id)},
    )
    assert data["profile"]["name"] == "pl"


def test_profiles_list_query(session: Session) -> None:
    project = M.Project(name="p-list")
    session.add(project)
    session.flush()
    ingest_profile(
        session, project.id, {"name": "p1", "score": 0.0, "source": [], "outputs": {}}
    )

    data = _execute(session, "{ profiles { name } }")
    assert data["profiles"] == [{"name": "p1"}]


def test_patterns_query_round_trips(session: Session) -> None:
    project = M.Project(name="pat-proj")
    session.add(project)
    session.flush()
    session.add(
        M.Pattern(
            name="pat1",
            project_id=project.id,
            json_pattern={"name": "pat1", "groups": []},
            dsl_content="dsl",
        )
    )
    session.flush()

    data = _execute(session, "{ patterns { id name dslContent } }")
    assert any(p["name"] == "pat1" for p in data["patterns"])

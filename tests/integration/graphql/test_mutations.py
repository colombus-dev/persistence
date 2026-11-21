"""Tests for the GraphQL mutation layer (slice 6).

Covers creating/deleting projects and profiles, and saving/deleting patterns,
through the ``Mutation`` root. Verifies round-trips against ``app_test`` via
the transactional session fixture.
"""

import asyncio
import uuid
from typing import Any

from sqlmodel import Session, select

import app.db.models as M
from app.graphql import build_schema_context, finalize_schema
from tests.profile_types import ProfileJson
from tests.profile_utils import encode_profile


def _mutation(session: Session, query: str, variables: dict[str, Any]) -> dict:
    schema = finalize_schema()

    async def run() -> dict:
        ctx = build_schema_context(session)
        result = await schema.execute(
            query, context_value=ctx, variable_values=variables
        )
        assert result.errors is None, result.errors
        assert result.data is not None
        return result.data

    return asyncio.run(run())


def _create_project_id(session: Session, name: str) -> uuid.UUID:
    projects = session.exec(select(M.Project).where(M.Project.name == name))
    for project in projects:
        return project.id
    raise AssertionError(f"project {name!r} not created")


def test_create_project(session: Session) -> None:
    data = _mutation(
        session,
        "mutation($name: String!) { createProject(name: $name) { id name } }",
        {"name": "created-proj"},
    )
    assert data["createProject"]["name"] == "created-proj"
    pid = uuid.UUID(data["createProject"]["id"])
    session.flush()
    stored = session.get(M.Project, pid)
    assert stored is not None and stored.name == "created-proj"


def test_delete_project(session: Session) -> None:
    project = M.Project(name="doomed")
    session.add(project)
    session.flush()
    data = _mutation(
        session,
        "mutation($id: UUID!) { deleteProject(id: $id) { ok } }",
        {"id": str(project.id)},
    )
    assert data["deleteProject"]["ok"] is True
    session.flush()
    assert session.get(M.Project, project.id) is None


def test_create_profile(session: Session, full_profile: ProfileJson) -> None:
    project = M.Project(name="prof-parent")
    session.add(project)
    session.flush()

    encoded = encode_profile(full_profile)
    json_profile = {"name": "made-profile", "source": []}
    data = _mutation(
        session,
        """
        mutation($projectId: UUID!, $name: String!, $score: Float!,
                 $encodedProfile: String!, $jsonProfile: JSON) {
          createProfile(projectId: $projectId, name: $name, score: $score,
                        encodedProfile: $encodedProfile, jsonProfile: $jsonProfile) {
            id
            projectId
          }
        }
        """,
        {
            "projectId": str(project.id),
            "name": "made-profile",
            "score": 3.5,
            "encodedProfile": encoded,
            "jsonProfile": json_profile,
        },
    )
    assert data["createProfile"]["projectId"] == str(project.id)


def test_delete_profile(session: Session) -> None:
    project = M.Project(name="prof-del")
    session.add(project)
    session.flush()
    from tests.profile_utils import ingest_profile

    profile = ingest_profile(
        session,
        project.id,
        {"name": "del-me", "score": 1.0, "source": [], "outputs": {}},
    )
    session.flush()
    data = _mutation(
        session,
        "mutation($id: UUID!) { deleteProfile(id: $id) { ok } }",
        {"id": str(profile.id)},
    )
    assert data["deleteProfile"]["ok"] is True
    session.flush()
    assert session.get(M.Profile, profile.id) is None


def test_save_pattern(session: Session) -> None:
    project = M.Project(name="pat-save")
    session.add(project)
    session.flush()
    data = _mutation(
        session,
        """
        mutation($projectId: UUID!, $name: String!,
                 $jsonPattern: JSON, $dslContent: String!) {
          savePattern(projectId: $projectId, name: $name,
                      jsonPattern: $jsonPattern, dslContent: $dslContent) { id name }
        }
        """,
        {
            "projectId": str(project.id),
            "name": "saved-pat",
            "jsonPattern": {"name": "saved-pat", "groups": []},
            "dslContent": "dsl-body",
        },
    )
    assert data["savePattern"]["name"] == "saved-pat"
    session.flush()
    stored = session.exec(select(M.Pattern).where(M.Pattern.name == "saved-pat")).one()
    assert stored.dsl_content == "dsl-body"


def test_delete_pattern(session: Session) -> None:
    project = M.Project(name="pat-del")
    session.add(project)
    session.flush()
    pattern = M.Pattern(
        name="pat-to-del",
        project_id=project.id,
        json_pattern={"name": "pat-to-del", "groups": []},
        dsl_content="x",
    )
    session.add(pattern)
    session.flush()
    data = _mutation(
        session,
        "mutation($id: UUID!) { deletePattern(id: $id) { ok } }",
        {"id": str(pattern.id)},
    )
    assert data["deletePattern"]["ok"] is True
    session.flush()
    assert session.get(M.Pattern, pattern.id) is None


def test_delete_nonexistent_project_reports_not_found(session: Session) -> None:
    data = _mutation(
        session,
        "mutation($id: UUID!) { deleteProject(id: $id) { ok } }",
        {"id": str(uuid.uuid4())},
    )
    assert data["deleteProject"]["ok"] is False


def test_delete_nonexistent_profile_reports_not_found(session: Session) -> None:
    data = _mutation(
        session,
        "mutation($id: UUID!) { deleteProfile(id: $id) { ok } }",
        {"id": str(uuid.uuid4())},
    )
    assert data["deleteProfile"]["ok"] is False


def test_delete_nonexistent_pattern_reports_not_found(session: Session) -> None:
    data = _mutation(
        session,
        "mutation($id: UUID!) { deletePattern(id: $id) { ok } }",
        {"id": str(uuid.uuid4())},
    )
    assert data["deletePattern"]["ok"] is False

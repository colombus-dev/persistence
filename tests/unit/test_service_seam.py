"""Service mock seam: resolvers delegate to the service layer (DB-free).

Proves the resolver->service boundary without a database (ADR-0011 Stage 2):
1. Mutation resolvers delegate to ``app.services.*`` builders and then apply the
   session write contract (add/commit/refresh).
2. Delete resolvers wrap the service's ``bool`` return in the
   ``MutationResult{ ok }`` envelope and only ``commit`` on success (skip-commit
   on not-found).

The patched service returns a real in-memory ``models.*`` row, never a bare
``Mock``.
"""

from __future__ import annotations

import uuid

import pytest

import app.db.models as M
from app.graphql import finalize_schema
from tests.unit._fakes import FakeSession, run_gql

schema = finalize_schema()


def test_create_profile_delegates_to_service_and_applies_write_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import profiles

    profile = M.Profile(
        project_id=uuid.uuid4(),
        name="delegated",
        score=1.0,
        json_profile={},
        encoded_profile="enc",
    )
    monkeypatch.setattr(profiles, "create_profile", lambda **_kwargs: profile)
    session = FakeSession()
    pid = uuid.uuid4()

    data = run_gql(
        schema,
        "mutation($projectId: UUID!, $name: String!, $score: Float!,"
        " $encodedProfile: String!, $jsonProfile: JSON) {"
        " createProfile(projectId: $projectId, name: $name, score: $score,"
        " encodedProfile: $encodedProfile, jsonProfile: $jsonProfile)"
        " { id projectId } }",
        context={"session": session},
        variables={
            "projectId": str(pid),
            "name": "delegated",
            "score": 1.0,
            "encodedProfile": "enc",
            "jsonProfile": {"source": []},
        },
    )
    assert data["createProfile"]["projectId"] == str(profile.project_id)
    (added,) = session.added
    assert added is profile
    assert session.committed is True
    assert session.refreshed == [profile]


def test_delete_profile_ok_true_commits_when_service_says_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import profiles

    monkeypatch.setattr(profiles, "delete_profile", lambda _session, _ident: True)
    session = FakeSession()

    data = run_gql(
        schema,
        "mutation($id: UUID!) { deleteProfile(id: $id) { ok } }",
        context={"session": session},
        variables={"id": str(uuid.uuid4())},
    )
    assert data["deleteProfile"] == {"ok": True}
    assert session.committed is True


def test_delete_profile_ok_false_skips_commit_when_service_says_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import profiles

    monkeypatch.setattr(profiles, "delete_profile", lambda _session, _ident: False)
    session = FakeSession()

    data = run_gql(
        schema,
        "mutation($id: UUID!) { deleteProfile(id: $id) { ok } }",
        context={"session": session},
        variables={"id": str(uuid.uuid4())},
    )
    assert data["deleteProfile"] == {"ok": False}
    assert session.committed is False


def test_create_project_delegates_to_service_and_applies_write_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import projects

    project = M.Project(name="delegated")
    monkeypatch.setattr(projects, "create_project", lambda **_kwargs: project)
    session = FakeSession()

    data = run_gql(
        schema,
        "mutation($name: String!) { createProject(name: $name) { id name } }",
        context={"session": session},
        variables={"name": "delegated"},
    )
    assert data["createProject"] == {"id": str(project.id), "name": "delegated"}
    (added,) = session.added
    assert added is project
    assert session.committed is True
    assert session.refreshed == [project]


def test_delete_project_ok_true_commits_when_service_says_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import projects

    monkeypatch.setattr(projects, "delete_project", lambda _session, _ident: True)
    session = FakeSession()

    data = run_gql(
        schema,
        "mutation($id: UUID!) { deleteProject(id: $id) { ok } }",
        context={"session": session},
        variables={"id": str(uuid.uuid4())},
    )
    assert data["deleteProject"] == {"ok": True}
    assert session.committed is True


def test_delete_project_ok_false_skips_commit_when_service_says_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import projects

    monkeypatch.setattr(projects, "delete_project", lambda _session, _ident: False)
    session = FakeSession()

    data = run_gql(
        schema,
        "mutation($id: UUID!) { deleteProject(id: $id) { ok } }",
        context={"session": session},
        variables={"id": str(uuid.uuid4())},
    )
    assert data["deleteProject"] == {"ok": False}
    assert session.committed is False

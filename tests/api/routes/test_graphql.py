"""Contract tests for the GraphQL endpoint.

These pin the client-facing behaviour of ``/graphql``: resolution over GET
and POST, the exact ``{"data": ...}`` response envelope, and reachable
introspection. They deliberately avoid testing Strawberry internals.
"""

from fastapi.testclient import TestClient

from app.main import app

client: TestClient = TestClient(app)


def test_get_query() -> None:
    response = client.get("/graphql", params={"query": "{ onePlusOne }"})
    assert response.status_code == 200
    assert response.json() == {"data": {"onePlusOne": 2}}


def test_post_query() -> None:
    response = client.post("/graphql", json={"query": "{ onePlusOne }"})
    assert response.status_code == 200
    assert response.json() == {"data": {"onePlusOne": 2}}


def test_introspection() -> None:
    response = client.post(
        "/graphql",
        json={"query": "{ __schema { queryType { name } } }"},
    )
    assert response.status_code == 200
    assert response.json() == {"data": {"__schema": {"queryType": {"name": "Query"}}}}

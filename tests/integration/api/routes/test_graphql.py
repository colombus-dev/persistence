"""Contract tests for the GraphQL endpoint.

These pin the client-facing behaviour of ``/graphql``: resolution over GET
and POST, the exact ``{"data": ...}`` response envelope, and reachable
introspection. They deliberately avoid testing Strawberry internals.
"""

from fastapi.testclient import TestClient

from app.main import app

client: TestClient = TestClient(app)


def test_get_query() -> None:
    response = client.get("/graphql", params={"query": "{ __typename }"})
    assert response.status_code == 200
    assert response.json() == {"data": {"__typename": "Query"}}


def test_post_query() -> None:
    response = client.post("/graphql", json={"query": "{ __typename }"})
    assert response.status_code == 200
    assert response.json() == {"data": {"__typename": "Query"}}


def test_health_probe_field_removed() -> None:
    """The placeholder ``onePlusOne`` smoke field has been dropped.

    Health/liveness is served by the dedicated ``/health`` endpoint (see
    ``test_health.py``), not by a GraphQL field. Asserting the field is absent
    guards against reintroducing throwaway surface into the schema.
    """
    response = client.post(
        "/graphql",
        json={"query": '{ __type(name: "Query") { fields { name } } }'},
    )
    assert response.status_code == 200
    fields = response.json()["data"]["__type"]["fields"]
    names = {field["name"] for field in fields}
    assert "onePlusOne" not in names


def test_introspection() -> None:
    response = client.post(
        "/graphql",
        json={"query": "{ __schema { queryType { name } } }"},
    )
    assert response.status_code == 200
    assert response.json() == {"data": {"__schema": {"queryType": {"name": "Query"}}}}

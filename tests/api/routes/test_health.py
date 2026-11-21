"""Contract tests for the liveness/health endpoint (non-GraphQL, A1).

As the API is GraphQL-only, health checks ping ``/health`` rather than a
GraphQL field. This pins the lightweight liveness response used by the
compose healthcheck.
"""

from fastapi.testclient import TestClient

from app.main import app

client: TestClient = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

from fastapi.testclient import TestClient

from vlr_analytics.api.main import app


def test_root_endpoint_exposes_project_metadata():
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "vlr-analytics-pro"
    assert payload["status"] == "ok"
    assert payload["docs"] == "/docs"
    assert payload["health"] == "/health"
    assert "/tables" in payload["available_endpoints"]


def test_health_endpoint_returns_ok():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

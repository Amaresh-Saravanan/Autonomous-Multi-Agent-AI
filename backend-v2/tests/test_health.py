from fastapi.testclient import TestClient

from app.main import app


def test_health():
    assert TestClient(app).get("/health").json()["status"] == "ok"


def test_health_live_and_ready():
    client = TestClient(app)
    assert client.get("/api/v1/health/live").json()["status"] == "ok"
    ready = client.get("/api/v1/health/ready").json()
    assert ready["database"] is True  # SQLite is always reachable in tests


def test_metrics_endpoint_exposes_prometheus_format():
    resp = TestClient(app).get("/api/v1/health/metrics")
    assert resp.status_code == 200
    assert b"# HELP" in resp.content

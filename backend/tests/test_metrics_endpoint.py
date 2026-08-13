"""Integration test for GET /metrics (tracker 3.8)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_metrics_endpoint_reports_counts_latency_and_acceptance_rate():
    for _ in range(2):
        r = client.post("/ingest/iot", json={
            "sensor_id": "wl-metrics-1", "metric": "water_level",
            "reading": 1.0, "unit": "m",
            "lat": 13.0, "lon": 80.0, "incident_id": "metrics-test-incident",
        })
        assert r.status_code == 200

    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.json()

    assert "routes" in body
    ingest_route = body["routes"]["/ingest/{source_type}"]
    assert ingest_route["count"] >= 2
    assert "avg_latency_ms" in ingest_route

    assert "recommendation_acceptance_rate" in body

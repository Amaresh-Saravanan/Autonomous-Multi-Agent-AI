"""Unit tests for in-process metrics module (tracker 3.8)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from app import metrics


def test_record_and_summary_counts_and_averages():
    metrics._routes.clear()  # test isolation, module-level state

    metrics.record("/ingest/iot", 10.0)
    metrics.record("/ingest/iot", 20.0)
    metrics.record("/ingest/iot", 30.0)

    result = metrics.summary()
    route = result["routes"]["/ingest/iot"]
    assert route["count"] == 3
    assert route["avg_latency_ms"] == 20.0


def test_summary_p95_basic():
    metrics._routes.clear()

    for i in range(1, 101):  # 1..100 ms
        metrics.record("/health", float(i))

    result = metrics.summary()
    route = result["routes"]["/health"]
    assert route["count"] == 100
    # naive sorted-index p95 of 1..100 should land near 95
    assert 94 <= route["p95_latency_ms"] <= 96

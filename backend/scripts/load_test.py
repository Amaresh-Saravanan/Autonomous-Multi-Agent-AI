"""Local load-test sanity check (tracker 3.7).

NOT part of the pytest suite. Assumes `uvicorn app.main:app` is already
running separately on localhost:8000 -- this script does not start the
server itself.

ponytail: this is a modest local sanity check (tens of concurrent requests
via a thread pool), not the PRD's 10k-sensor/100-operator load target. A
real load rig (locust/k6, distributed, sustained) is the upgrade path if/when
this repo needs to prove it at that scale.

Usage:
    python scripts/load_test.py [num_requests]
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

URL = "http://localhost:8000/ingest/iot"
P95_THRESHOLD_MS = 2000


def _payload(i: int) -> dict:
    return {
        "sensor_id": f"load-{i}",
        "metric": "water_level",
        "reading": 1.0 + (i % 5),
        "unit": "m",
        "lat": 13.09,
        "lon": 80.28,
        "incident_id": f"load-test-{i % 10}",
    }


def _one_request(client: httpx.Client, i: int) -> float:
    start = time.perf_counter()
    r = client.post(URL, json=_payload(i))
    elapsed_ms = (time.perf_counter() - start) * 1000
    r.raise_for_status()
    return elapsed_ms


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(int(len(sorted_values) * pct), len(sorted_values) - 1)
    return sorted_values[idx]


def run(num_requests: int = 50) -> None:
    latencies: list[float] = []
    errors = 0

    with httpx.Client(timeout=10) as client:
        with ThreadPoolExecutor(max_workers=min(num_requests, 20)) as pool:
            futures = [pool.submit(_one_request, client, i) for i in range(num_requests)]
            for f in as_completed(futures):
                try:
                    latencies.append(f.result())
                except Exception as exc:  # noqa: BLE001
                    errors += 1
                    print(f"request failed: {exc}")

    latencies.sort()
    p50 = _percentile(latencies, 0.50)
    p95 = _percentile(latencies, 0.95)
    p99 = _percentile(latencies, 0.99)

    print(f"\nrequests: {num_requests}  ok: {len(latencies)}  errors: {errors}")
    print(f"p50: {p50:.1f}ms  p95: {p95:.1f}ms  p99: {p99:.1f}ms")

    if errors:
        print(f"FAIL: {errors} request(s) errored")
    elif p95 < P95_THRESHOLD_MS:
        print(f"PASS: p95 {p95:.1f}ms < {P95_THRESHOLD_MS}ms threshold")
    else:
        print(f"FAIL: p95 {p95:.1f}ms exceeds {P95_THRESHOLD_MS}ms threshold")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    run(n)

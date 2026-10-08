"""Prometheus metrics (Phase 24). Covers the latencies/failure counts the
spec names: API, ingestion, agent, LLM — plus fallback usage."""

from prometheus_client import Counter, Histogram

API_REQUEST_LATENCY = Histogram("api_request_latency_seconds", "HTTP request latency", ["path", "method"])
INGESTION_LATENCY = Histogram("ingestion_latency_seconds", "Ingestion pipeline latency (validate->persist->enqueue)", ["source_type"])
AGENT_LATENCY = Histogram("agent_latency_seconds", "Per-agent execution latency", ["agent_id"])
LLM_LATENCY = Histogram("llm_latency_seconds", "LLM call latency", ["provider"])
LLM_FAILURES = Counter("llm_failures_total", "LLM calls that fell back to deterministic reasoning", ["provider"])
AGENT_FALLBACKS = Counter("agent_fallbacks_total", "Agent runs that used a fallback path", ["agent_id"])

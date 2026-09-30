"""Automated tests for Phase 16: Structured Observability & Health Probes.

Verifies:
1. Core Metrics Engine: Counter, Gauge, and Histogram with multi-dimensional labels.
2. Prometheus Exposition Format: Valid plain-text (0.0.4) output for scraping.
3. HTTP Middleware Telemetry: Request count and latency observation across endpoints.
4. Deep Readiness Probe: Live database ping (`SELECT 1`), Kafka broker/fallback inspection, and LLM configuration.
5. Liveness Probe: Dedicated `/health/live` probe for container orchestrators.
6. Error / Unready State Handling: Returns HTTP 503 if downstream dependency check fails.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.core.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    registry,
    HTTP_REQUESTS_TOTAL,
    REVIEWS_INGESTED_TOTAL,
    CLUSTERS_FORMED_TOTAL,
    ACTIVE_CLUSTERS_GAUGE,
)


def test_core_metrics_engine_primitives():
    """Verify Counter, Gauge, and Histogram primitives operate accurately."""
    custom_reg = MetricsRegistry()

    # 1. Counter test
    counter = custom_reg.register(
        Counter("test_counter_total", "Test counter description", ["region", "status"])
    )
    counter.labels(region="us-east-1", status="ok").inc(1.0)
    counter.labels(region="us-east-1", status="ok").inc(2.5)
    assert counter.get_value({"region": "us-east-1", "status": "ok"}) == 3.5

    # 2. Gauge test
    gauge = custom_reg.register(
        Gauge("test_active_items", "Test gauge description", ["pool"])
    )
    gauge.labels(pool="prod").set(10.0)
    assert gauge.get_value({"pool": "prod"}) == 10.0
    gauge.labels(pool="prod").inc(5.0)
    assert gauge.get_value({"pool": "prod"}) == 15.0
    gauge.labels(pool="prod").dec(3.0)
    assert gauge.get_value({"pool": "prod"}) == 12.0

    # 3. Histogram test
    hist = custom_reg.register(
        Histogram("test_latency_seconds", "Test histogram description", ["operation"], buckets=(0.1, 0.5, 1.0))
    )
    hist.labels(operation="fetch").observe(0.05)
    hist.labels(operation="fetch").observe(0.4)
    hist.labels(operation="fetch").observe(1.5)

    # 4. Exposition format verification
    rendered = custom_reg.render()
    assert "# HELP test_counter_total Test counter description" in rendered
    assert "# TYPE test_counter_total counter" in rendered
    assert 'test_counter_total{region="us-east-1",status="ok"} 3.5' in rendered

    assert "# HELP test_active_items Test gauge description" in rendered
    assert "# TYPE test_active_items gauge" in rendered
    assert 'test_active_items{pool="prod"} 12.0' in rendered

    assert "# HELP test_latency_seconds Test histogram description" in rendered
    assert "# TYPE test_latency_seconds histogram" in rendered
    assert 'test_latency_seconds_bucket{le="0.1",operation="fetch"} 1' in rendered
    assert 'test_latency_seconds_bucket{le="0.5",operation="fetch"} 2' in rendered
    assert 'test_latency_seconds_bucket{le="+Inf",operation="fetch"} 3' in rendered
    assert 'test_latency_seconds_count{operation="fetch"} 3' in rendered


def test_prometheus_scrape_endpoints(client: TestClient):
    """Verify both /metrics and /api/v1/metrics endpoints export valid telemetry."""
    # Execute a few requests to populate telemetry
    client.get("/api/v1/health")
    client.get("/api/v1/health/live")

    # 1. Root /metrics endpoint
    res_root = client.get("/metrics")
    assert res_root.status_code == 200
    assert "version=0.0.4" in res_root.headers.get("content-type", "")
    content = res_root.text

    assert "cva_http_requests_total" in content
    assert "cva_http_request_duration_seconds" in content
    assert "cva_reviews_ingested_total" in content
    assert "cva_clusters_formed_total" in content
    assert "cva_db_ping_latency_seconds" in content

    # 2. API v1 /api/v1/metrics endpoint
    res_v1 = client.get("/api/v1/metrics")
    assert res_v1.status_code == 200
    assert res_v1.text == content


def test_deep_readiness_probe_success(client: TestClient):
    """Verify /api/v1/health/ready performs live database and broker verification."""
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ready"
    assert "dependencies" in data
    deps = data["dependencies"]

    # Database dependency checks
    assert deps["database"]["status"] == "ready"
    assert deps["database"]["latency_ms"] >= 0.0
    assert "engine" in deps["database"]

    # Kafka broker / fallback checks
    assert deps["kafka"]["status"] in ["ready", "degraded"]
    assert "connected_to_broker" in deps["kafka"]
    assert "fallback_mode_active" in deps["kafka"]
    assert "fallback_buffered_messages" in deps["kafka"]

    # LLM Provider checks
    assert deps["llm_provider"]["status"] == "ready"
    assert "provider" in deps["llm_provider"]


def test_liveness_probes(client: TestClient):
    """Verify /api/v1/health and /api/v1/health/live respond with HTTP 200."""
    res1 = client.get("/api/v1/health")
    assert res1.status_code == 200
    assert res1.json()["status"] == "healthy"

    res2 = client.get("/api/v1/health/live")
    assert res2.status_code == 200
    assert res2.json()["status"] == "healthy"


def test_readiness_probe_database_failure(client: TestClient):
    """Verify that a failing database query results in HTTP 503 Service Unavailable."""
    with patch("app.api.v1.health.async_session_factory") as mock_session_factory:
        # Mock session to raise an operational database exception
        mock_session_factory.side_effect = RuntimeError("Database connection pool exhausted")

        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["dependencies"]["database"]["status"] == "unhealthy"
        assert "Database connection pool exhausted" in data["dependencies"]["database"]["error"]

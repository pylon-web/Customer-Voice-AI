"""Unit tests for liveness, readiness, and root API endpoints."""

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test root redirect/metadata endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["docs"] == "/api/v1/docs"
    assert data["health"] == "/api/v1/health"


def test_health_liveness(client: TestClient):
    """Test /api/v1/health liveness probe."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "Customer Voice AI"
    assert "timestamp" in data
    assert "environment" in data


def test_health_readiness(client: TestClient):
    """Test /api/v1/health/ready readiness probe."""
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "dependencies" in data
    assert "database" in data["dependencies"]
    assert "kafka" in data["dependencies"]
    assert "llm_provider" in data["dependencies"]


def test_middleware_correlation_headers(client: TestClient):
    """Verify correlation ID and processing time headers are returned."""
    custom_cid = "test-corr-id-12345"
    response = client.get("/", headers={"X-Correlation-ID": custom_cid})
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == custom_cid
    assert "X-Process-Time-Ms" in response.headers

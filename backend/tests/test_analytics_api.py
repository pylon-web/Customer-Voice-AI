"""Tests for dashboard analytics and catalog metadata endpoints."""

from fastapi.testclient import TestClient


def test_get_dashboard_overview(client: TestClient):
    """Verify overview statistics endpoint returns complete structure with KPIs."""
    response = client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    data = response.json()

    assert "total_reviews" in data
    assert "avg_rating" in data
    assert "sentiment_counts" in data
    assert "positive" in data["sentiment_counts"]
    assert "neutral" in data["sentiment_counts"]
    assert "negative" in data["sentiment_counts"]
    assert "total_clusters" in data
    assert "anomalies_count" in data
    assert "pending_recommendations_count" in data
    assert "top_products" in data
    assert "recent_anomalies" in data


def test_list_products_catalog(client: TestClient):
    """Verify catalog endpoint returns Capital One products."""
    response = client.get("/api/v1/analytics/products")
    assert response.status_code == 200
    products = response.json()
    assert isinstance(products, list)
    assert len(products) >= 19

    product_ids = {p["id"] for p in products}
    assert "venture_x" in product_ids
    assert "banking_360_checking" in product_ids
    assert "c1_mobile_ios" in product_ids


def test_list_sources_catalog(client: TestClient):
    """Verify catalog endpoint returns supported review sources."""
    response = client.get("/api/v1/analytics/sources")
    assert response.status_code == 200
    sources = response.json()
    assert isinstance(sources, list)
    assert len(sources) >= 5

    source_ids = {s["id"] for s in sources}
    assert "apple_app_store" in source_ids
    assert "google_play_store" in source_ids
    assert "google_places" in source_ids

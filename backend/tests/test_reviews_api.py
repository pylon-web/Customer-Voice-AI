"""Unit and integration tests for the Review Ingestion REST APIs."""

import json
from fastapi.testclient import TestClient


def test_ingest_single_review_standard(client: TestClient):
    """Test standard single review ingestion via POST /api/v1/reviews."""
    payload = {
        "id": "test-rev-std-001",
        "product_id": "venture_x",
        "source_id": "apple_app_store",
        "location": "Dallas, TX",
        "rating": 5,
        "review_title": "Outstanding Lounge",
        "review_text": "Capital One Lounge at DFW was phenomenal. Friendly staff and great espresso.",
    }
    response = client.post("/api/v1/reviews", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "test-rev-std-001"
    assert data["product_id"] == "venture_x"
    assert data["source_id"] == "apple_app_store"
    assert data["rating"] == 5
    assert "ingested_at" in data


def test_ingest_single_review_prompt_example_format(client: TestClient):
    """Test ingestion with prompt's exact example format ('product', 'source', 'text')."""
    payload = {
        "id": "review-123-prompt-example",
        "source": "google",
        "product": "mobile_banking",
        "location": "Chicago",
        "rating": 2,
        "text": "The mobile app keeps logging me out.",
        "created_at": "2026-09-20T10:30:00Z"
    }
    response = client.post("/api/v1/reviews", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "review-123-prompt-example"
    assert data["product_id"] == "c1_mobile_ios"
    assert data["source_id"] == "google_places"
    assert data["review_text"] == "The mobile app keeps logging me out."
    assert data["location"] == "Chicago"
    assert data["rating"] == 2


def test_ingest_review_validation_errors(client: TestClient):
    """Test input validation: rating out of bounds and missing text."""
    # Rating out of bounds (rating=6)
    res_bad_rating = client.post("/api/v1/reviews", json={
        "product_id": "venture_x",
        "rating": 6,
        "review_text": "Good card but invalid rating."
    })
    assert res_bad_rating.status_code == 422

    # Missing text
    res_no_text = client.post("/api/v1/reviews", json={
        "product_id": "venture_x",
        "rating": 5,
    })
    assert res_no_text.status_code == 422


def test_ingest_batch_reviews(client: TestClient):
    """Test batch review ingestion via POST /api/v1/reviews/batch."""
    batch_payload = {
        "reviews": [
            {
                "id": f"batch-rev-{i}",
                "product_id": "banking_360_checking",
                "source_id": "google_play_store",
                "rating": 4,
                "review_text": f"Batch test review message number {i}",
            }
            for i in range(5)
        ]
    }
    response = client.post("/api/v1/reviews/batch", json=batch_payload)
    assert response.status_code == 202
    data = response.json()
    assert data["total_submitted"] == 5
    assert data["total_accepted"] == 5
    assert len(data["review_ids"]) == 5
    assert data["status"] == "queued"


def test_upload_json_file(client: TestClient):
    """Test bulk file upload of JSON reviews via POST /api/v1/reviews/upload."""
    json_data = [
        {
            "id": "upload-json-1",
            "product": "savor_one",
            "source": "trustpilot",
            "rating": 5,
            "text": "Saved $30 on dining out this weekend.",
        },
        {
            "id": "upload-json-2",
            "product": "eno_virtual_assistant",
            "source": "apple_app_store",
            "rating": 1,
            "text": "Virtual card was declined at gas station.",
        }
    ]
    file_bytes = json.dumps(json_data).encode("utf-8")
    files = {"file": ("reviews_sample.json", file_bytes, "application/json")}

    response = client.post("/api/v1/reviews/upload", files=files)
    assert response.status_code == 202
    data = response.json()
    assert data["total_submitted"] == 2
    assert data["total_accepted"] == 2
    assert "upload-json-1" in data["review_ids"]
    assert "upload-json-2" in data["review_ids"]


def test_upload_csv_file(client: TestClient):
    """Test bulk file upload of CSV reviews via POST /api/v1/reviews/upload."""
    csv_content = (
        "id,product,source,rating,review_text,location\n"
        "csv-rev-1,venture_x,apple_app_store,5,Phenomenal travel perks,Miami FL\n"
        "csv-rev-2,auto_navigator,trustpilot,4,Fast pre-qualification,Austin TX\n"
    ).encode("utf-8")
    files = {"file": ("reviews_sample.csv", csv_content, "text/csv")}

    response = client.post("/api/v1/reviews/upload", files=files)
    assert response.status_code == 202
    data = response.json()
    assert data["total_submitted"] == 2
    assert data["total_accepted"] == 2
    assert "csv-rev-1" in data["review_ids"]


def test_list_and_filter_reviews(client: TestClient):
    """Test GET /api/v1/reviews pagination and filtering."""
    # List all reviews
    response = client.get("/api/v1/reviews?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total"] >= 10

    # Filter by specific product
    res_product = client.get("/api/v1/reviews?product_id=venture_x")
    assert res_product.status_code == 200
    prod_data = res_product.json()
    for item in prod_data["items"]:
        assert item["product_id"] == "venture_x"

    # Filter by star rating
    res_rating = client.get("/api/v1/reviews?rating=5")
    assert res_rating.status_code == 200
    rating_data = res_rating.json()
    for item in rating_data["items"]:
        assert item["rating"] == 5


def test_get_review_by_id_and_not_found(client: TestClient):
    """Test GET /api/v1/reviews/{id} success and 404 cases."""
    # Fetch existing
    res_found = client.get("/api/v1/reviews/test-rev-std-001")
    assert res_found.status_code == 200
    data = res_found.json()
    assert data["id"] == "test-rev-std-001"
    assert data["product_id"] == "venture_x"

    # Fetch non-existent
    res_missing = client.get("/api/v1/reviews/non-existent-review-id-9999")
    assert res_missing.status_code == 404
    error_data = res_missing.json()
    assert "error" in error_data
    assert error_data["error"]["status_code"] == 404

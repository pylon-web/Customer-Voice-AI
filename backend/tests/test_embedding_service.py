"""Unit and integration tests for Vector Embeddings, pgvector semantic search, and worker pipeline."""

import math
import numpy as np
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import async_session_factory
from app.services.embedding_service import (
    MockEmbeddingGenerator,
    EmbeddingService,
    handle_review_embedding_event,
)
from app.repositories.embedding_repo import EmbeddingRepository, cosine_similarity
from app.repositories.review_repo import ReviewRepository
from app.repositories.analysis_repo import AnalysisRepository
from app.services.ingestion_service import IngestionService
from app.services.analysis_service import handle_review_created_event
from app.workers.review_worker import ReviewWorker
from app.kafka.producer import get_kafka_producer
from app.kafka.consumer import KafkaConsumerService
from app.models.entities import Review, ReviewEmbedding
from app.models.schemas import ReviewCreate, SemanticSearchRequest


@pytest.mark.asyncio
async def test_mock_embedding_generator_properties():
    """Verify that MockEmbeddingGenerator produces normalized 1536-dimensional deterministic vectors."""
    generator = MockEmbeddingGenerator(dimension=1536)
    text = "Capital One Lounge at DFW airport is exceptional."

    vec1 = await generator.generate_embedding(text)
    vec2 = await generator.generate_embedding(text)

    # Dimension assertion
    assert len(vec1) == 1536

    # Determinism
    assert vec1 == vec2

    # L2 Unit Norm assertion (norm ~= 1.0)
    norm = np.linalg.norm(np.array(vec1))
    assert math.isclose(norm, 1.0, rel_tol=1e-4)


@pytest.mark.asyncio
async def test_semantic_similarity_relative_scoring():
    """Verify semantic concept proximity: related texts score significantly higher than unrelated texts."""
    generator = MockEmbeddingGenerator(dimension=1536)

    # Two reviews about Wi-Fi connectivity
    text_wifi_1 = "The Wi-Fi in the Austin café kept disconnecting every 10 minutes."
    text_wifi_2 = "Internet connection was terrible at the café, couldn't work online."

    # An unrelated review about checking account overdraft fees
    text_unrelated = "Surprise overdraft fees were charged on my 360 checking account."

    vec_wifi_1 = await generator.generate_embedding(text_wifi_1)
    vec_wifi_2 = await generator.generate_embedding(text_wifi_2)
    vec_unrelated = await generator.generate_embedding(text_unrelated)

    sim_related = cosine_similarity(vec_wifi_1, vec_wifi_2)
    sim_unrelated = cosine_similarity(vec_wifi_1, vec_unrelated)

    assert sim_related > sim_unrelated
    assert sim_related > 0.60
    assert sim_unrelated < 0.35


@pytest.mark.asyncio
async def test_embedding_repository_crud():
    """Test persisting, retrieving, and upserting ReviewEmbedding entities."""
    async with async_session_factory() as session:
        review_repo = ReviewRepository(session)
        embedding_repo = EmbeddingRepository(session)

        # Create review
        rev_id = "test-embed-rev-001"
        rev = Review(
            id=rev_id,
            source_id="apple_app_store",
            product_id="venture_x",
            rating=5,
            review_text="Best card perks",
            created_at=datetime.now(timezone.utc),
            ingested_at=datetime.now(timezone.utc),
        )
        await review_repo.create(rev)

        generator = MockEmbeddingGenerator()
        vector = await generator.generate_embedding(rev.review_text)

        embedding = ReviewEmbedding(
            id="embed-id-001",
            review_id=rev_id,
            embedding=vector,
            model_name="text-embedding-3-small",
            dimension=1536,
            created_at=datetime.now(timezone.utc),
        )
        saved = await embedding_repo.create(embedding)
        assert saved.id == "embed-id-001"
        assert saved.dimension == 1536

        # Fetch
        fetched = await embedding_repo.get_by_review_id(rev_id)
        assert fetched is not None
        assert fetched.dimension == 1536

        await session.commit()


@pytest.mark.asyncio
async def test_embedding_service_generate_and_emit_event():
    """Verify EmbeddingService persists embedding and publishes review.embedded event."""
    producer = get_kafka_producer()
    producer.clear_history()

    async with async_session_factory() as session:
        ingestion = IngestionService(session)
        review = await ingestion.ingest_single(
            ReviewCreate(
                id="test-embed-event-rev",
                product_id="c1_shopping_extension",
                source_id="chrome_web_store",
                rating=1,
                review_text="Shopping extension completely freezes Chrome tab on checkout.",
            )
        )
        await session.commit()

        service = EmbeddingService(session)
        saved_embedding = await service.generate_and_store_embedding(review.id)
        await session.commit()

        assert saved_embedding.review_id == "test-embed-event-rev"
        assert saved_embedding.dimension == 1536

        # Check published event
        matching_events = [
            item for item in producer.published_history
            if item.get("topic") == settings.KAFKA_TOPIC_REVIEW_EMBEDDED
            and item.get("event", {}).get("data", {}).get("review_id") == "test-embed-event-rev"
        ]
        assert len(matching_events) == 1
        event_payload = matching_events[0]["event"]["data"]
        assert event_payload["embedding_dimension"] == 1536


@pytest.mark.asyncio
async def test_search_similar_ranking():
    """Test vector similarity search ranks the semantically relevant review first."""
    async with async_session_factory() as session:
        ingestion = IngestionService(session)
        embed_svc = EmbeddingService(session)

        # Ingest 3 distinct reviews
        rev_lounge = await ingestion.ingest_single(
            ReviewCreate(
                id="rank-rev-lounge",
                product_id="venture_x",
                source_id="apple_app_store",
                rating=5,
                review_text="DFW lounge is super luxurious, great drinks and quiet relaxation.",
            )
        )
        rev_wifi = await ingestion.ingest_single(
            ReviewCreate(
                id="rank-rev-wifi",
                product_id="c1_cafe",
                source_id="google_places",
                rating=2,
                review_text="Wi-Fi kept cutting out at the Austin café.",
            )
        )
        rev_fee = await ingestion.ingest_single(
            ReviewCreate(
                id="rank-rev-fee",
                product_id="banking_360_checking",
                source_id="trustpilot",
                rating=1,
                review_text="Unexpected overdraft penalty on my checking balance.",
            )
        )
        await session.commit()

        # Generate embeddings for each
        await embed_svc.generate_and_store_embedding(rev_lounge.id)
        await embed_svc.generate_and_store_embedding(rev_wifi.id)
        await embed_svc.generate_and_store_embedding(rev_fee.id)
        await session.commit()

        # Perform semantic query for airport lounge
        search_req = SemanticSearchRequest(
            query="quiet airport lounge with espresso and seats",
            limit=10,
        )
        search_resp = await embed_svc.search_reviews_semantic(search_req)

        assert search_resp.total_results >= 1
        # Top result must be a lounge review!
        top_match = search_resp.results[0]
        assert "lounge" in top_match.review.id
        assert top_match.similarity > 0.50
        assert any(r.review.id == "rank-rev-lounge" for r in search_resp.results)


@pytest.mark.asyncio
async def test_review_worker_end_to_end_analysis_and_embedding():
    """Test ReviewWorker automatically analyzes AND generates embedding for ingested reviews."""
    producer = get_kafka_producer()
    producer.clear_history()

    async with async_session_factory() as session:
        ingestion = IngestionService(session)
        await ingestion.ingest_single(
            ReviewCreate(
                id="worker-full-pipeline-rev-999",
                product_id="c1_mobile_ios",
                source_id="apple_app_store",
                rating=1,
                review_text="Face ID biometric authentication crashes instantly after v6.14 update.",
            )
        )
        await session.commit()

    # Worker consumes review.created and runs both analysis and embedding handlers
    consumer = KafkaConsumerService(topics=[settings.KAFKA_TOPIC_REVIEW_CREATED], fallback_enabled=True)
    worker = ReviewWorker(
        consumer=consumer,
        handlers=[handle_review_created_event, handle_review_embedding_event],
    )
    await worker.run(max_messages=1)

    assert worker.processed_count >= 1

    # Verify BOTH analysis and embedding were created in the database
    async with async_session_factory() as session:
        analysis_repo = AnalysisRepository(session)
        embedding_repo = EmbeddingRepository(session)

        analysis = await analysis_repo.get_by_review_id("worker-full-pipeline-rev-999")
        embedding = await embedding_repo.get_by_review_id("worker-full-pipeline-rev-999")

        assert analysis is not None
        assert analysis.category == "Authentication & Biometrics"

        assert embedding is not None
        assert embedding.dimension == 1536


def test_reviews_api_search_semantic_and_embed_endpoints(client: TestClient):
    """Test REST API endpoints for semantic search and review embedding generation."""
    # 1. Ingest a review
    payload = {
        "id": "api-embed-test-001",
        "product_id": "c1_cafe",
        "source_id": "google_places",
        "rating": 5,
        "review_title": "Great Remote Work Café",
        "review_text": "Capital One Café in Chicago has blazing fast Wi-Fi and 50% discount on cold brew.",
        "location": "Chicago, IL",
    }
    client.post("/api/v1/reviews", json=payload)

    # 2. Trigger embedding generation
    embed_res = client.post("/api/v1/reviews/api-embed-test-001/embed")
    assert embed_res.status_code == 200
    embed_data = embed_res.json()
    assert embed_data["review_id"] == "api-embed-test-001"
    assert embed_data["dimension"] == 1536
    assert embed_data["model_name"] == "text-embedding-3-small"

    # 3. Retrieve embedding metadata
    get_res = client.get("/api/v1/reviews/api-embed-test-001/embedding")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == embed_data["id"]

    # 4. Search semantic API
    search_payload = {
        "query": "fast wifi internet for laptop work",
        "limit": 5,
        "min_similarity": 0.3,
    }
    search_res = client.post("/api/v1/reviews/search-semantic", json=search_payload)
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total_results"] >= 1
    found_ids = [item["review"]["id"] for item in search_data["results"]]
    assert "api-embed-test-001" in found_ids

    # 5. Non-existent review embedding returns 404
    nf_res = client.get("/api/v1/reviews/does-not-exist/embedding")
    assert nf_res.status_code == 404

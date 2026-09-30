"""Unit and integration tests for AI Review Analysis Agent, service, and API endpoints."""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import async_session_factory
from app.agents.analyzer import MockAnalysisAgent, get_analysis_agent, AnalysisResult
from app.models.entities import Review, ReviewAnalysis
from app.repositories.review_repo import ReviewRepository
from app.repositories.analysis_repo import AnalysisRepository
from app.services.ingestion_service import IngestionService
from app.services.analysis_service import AnalysisService, handle_review_created_event
from app.workers.review_worker import ReviewWorker
from app.kafka.producer import get_kafka_producer
from app.kafka.consumer import KafkaConsumerService


@pytest.mark.asyncio
async def test_mock_agent_positive_lounge_review():
    """Verify deterministic mock agent analyzes positive lounge feedback accurately."""
    agent = MockAnalysisAgent()
    result = await agent.analyze(
        text="The Capital One Lounge at DFW was phenomenal! Amazing espresso and great seating.",
        rating=5,
        product_id="venture_x",
        title="Best travel card perk",
        location="Dallas, TX",
    )

    assert isinstance(result, AnalysisResult)
    assert result.sentiment == "positive"
    assert result.sentiment_score >= 0.80
    assert result.category == "Travel & Lounge Perks"
    assert result.severity == "low"
    assert result.customer_intent == "praise"
    entity_names = [e["name"] for e in result.entities]
    assert "DFW" in entity_names
    assert "Dallas, TX" in entity_names


@pytest.mark.asyncio
async def test_mock_agent_negative_faceid_crash():
    """Verify deterministic mock agent flags critical Face ID authentication crash."""
    agent = MockAnalysisAgent()
    result = await agent.analyze(
        text="Ever since the v6.14 update on iOS, the app immediately crashes during Face ID biometric login!",
        rating=1,
        product_id="c1_mobile_ios",
        title="Unusable crash",
    )

    assert result.sentiment == "negative"
    assert result.sentiment_score <= -0.80
    assert result.category == "Authentication & Biometrics"
    assert result.severity == "critical"
    assert result.customer_intent == "bug_report"
    entity_names = [e["name"] for e in result.entities]
    assert "IOS" in entity_names
    assert "v6.14" in entity_names


@pytest.mark.asyncio
async def test_mock_agent_cafe_wifi_complaint():
    """Verify café Wi-Fi complaint extraction."""
    agent = MockAnalysisAgent()
    result = await agent.analyze(
        text="Love the coffee but the Wi-Fi keeps disconnecting every 10 minutes while working remotely.",
        rating=2,
        product_id="c1_cafe",
        location="Austin, TX",
    )

    assert result.sentiment == "negative"
    assert result.category == "Café Facilities & Wi-Fi"
    assert result.severity == "medium"
    assert result.customer_intent == "complaint"


@pytest.mark.asyncio
async def test_mock_agent_shopping_extension_freeze():
    """Verify shopping browser extension freeze identification."""
    agent = MockAnalysisAgent()
    result = await agent.analyze(
        text="Capital One Shopping browser extension completely freezes the chrome tab when applying coupons.",
        rating=1,
        product_id="c1_shopping_extension",
    )

    assert result.category == "Shopping Extension"
    assert result.severity == "high"
    assert result.customer_intent == "bug_report"


@pytest.mark.asyncio
async def test_analysis_repository_crud():
    """Test persisting, retrieving, and upserting ReviewAnalysis in the database."""
    async with async_session_factory() as session:
        review_repo = ReviewRepository(session)
        analysis_repo = AnalysisRepository(session)

        # Create a test review
        review_id = "test-repo-rev-001"
        test_rev = Review(
            id=review_id,
            source_id="apple_app_store",
            product_id="venture_x",
            rating=5,
            review_text="Outstanding perks",
            created_at=datetime.now(timezone.utc),
            ingested_at=datetime.now(timezone.utc),
        )
        await review_repo.create(test_rev)

        # Create analysis
        analysis = ReviewAnalysis(
            id="test-analysis-001",
            review_id=review_id,
            sentiment="positive",
            sentiment_score=0.92,
            category="Travel & Lounge Perks",
            issue="Praise for lounge perks",
            severity="low",
            customer_intent="praise",
            entities=[],
            confidence=0.98,
            analyzed_at=datetime.now(timezone.utc),
        )
        saved = await analysis_repo.create(analysis)
        assert saved.id == "test-analysis-001"

        # Retrieve
        fetched = await analysis_repo.get_by_review_id(review_id)
        assert fetched is not None
        assert fetched.sentiment == "positive"
        assert fetched.sentiment_score == 0.92

        # Upsert modification
        fetched.sentiment_score = 0.99
        updated = await analysis_repo.upsert(fetched)
        assert updated.sentiment_score == 0.99

        await session.commit()


@pytest.mark.asyncio
async def test_analysis_service_analyze_and_emit_event():
    """Test AnalysisService extracts insights, saves to DB, and emits review.analyzed event."""
    producer = get_kafka_producer()
    producer.clear_history()

    async with async_session_factory() as session:
        # Ingest review first
        ingestion = IngestionService(session)
        from app.models.schemas import ReviewCreate

        review = await ingestion.ingest_single(
            ReviewCreate(
                id="test-service-rev-555",
                product_id="c1_mobile_ios",
                source_id="apple_app_store",
                rating=1,
                review_text="Face ID completely broke in the newest app update, crashes instantly.",
            )
        )
        await session.commit()

        # Run AnalysisService
        service = AnalysisService(session)
        analysis = await service.analyze_review(review.id)
        await session.commit()

        assert analysis.review_id == "test-service-rev-555"
        assert analysis.sentiment == "negative"
        assert analysis.category == "Authentication & Biometrics"
        assert analysis.severity == "critical"

        # Check emitted review.analyzed Kafka event
        matching_events = [
            item for item in producer.published_history
            if item.get("topic") == settings.KAFKA_TOPIC_REVIEW_ANALYZED
            and item.get("event", {}).get("data", {}).get("review_id") == "test-service-rev-555"
        ]
        assert len(matching_events) == 1
        event_payload = matching_events[0]["event"]["data"]
        assert event_payload["category"] == "Authentication & Biometrics"
        assert event_payload["severity"] == "critical"


@pytest.mark.asyncio
async def test_review_worker_end_to_end_pipeline():
    """End-to-End: Review Ingestion -> Kafka review.created -> ReviewWorker -> Analysis in DB."""
    producer = get_kafka_producer()
    producer.clear_history()

    async with async_session_factory() as session:
        ingestion = IngestionService(session)
        from app.models.schemas import ReviewCreate

        # 1. Ingest review (publishes review.created to fallback queue)
        rev = await ingestion.ingest_single(
            ReviewCreate(
                id="e2e-worker-rev-777",
                product_id="venture_x",
                source_id="apple_app_store",
                rating=5,
                review_text="DFW lounge is super luxurious, great drinks and staff.",
            )
        )
        await session.commit()

    # 2. Worker consumes review.created and triggers handle_review_created_event
    consumer = KafkaConsumerService(topics=[settings.KAFKA_TOPIC_REVIEW_CREATED], fallback_enabled=True)
    worker = ReviewWorker(consumer=consumer, handlers=[handle_review_created_event])
    await worker.run(max_messages=1)

    assert worker.processed_count >= 1

    # 3. Verify analysis was automatically saved in the database
    async with async_session_factory() as session:
        analysis_repo = AnalysisRepository(session)
        analysis = await analysis_repo.get_by_review_id("e2e-worker-rev-777")
        assert analysis is not None
        assert analysis.sentiment == "positive"
        assert analysis.category == "Travel & Lounge Perks"


def test_reviews_api_analysis_endpoints(client: TestClient):
    """Test POST /api/v1/reviews/{id}/analyze and GET /api/v1/reviews/{id}/analysis."""
    # 1. Ingest review via API
    payload = {
        "id": "api-analyze-test-001",
        "product_id": "c1_cafe",
        "source_id": "google_places",
        "rating": 5,
        "review_title": "Great Study Spot",
        "review_text": "Capital One Café in Austin has amazing fast Wi-Fi and 50% discount on Peets coffee.",
        "location": "Austin, TX",
    }
    create_res = client.post("/api/v1/reviews", json=payload)
    assert create_res.status_code == 201

    # 2. Trigger analysis via API
    analyze_res = client.post("/api/v1/reviews/api-analyze-test-001/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()
    assert data["review_id"] == "api-analyze-test-001"
    assert data["sentiment"] == "positive"
    assert data["category"] == "Café Facilities & Wi-Fi"
    assert data["severity"] == "low"
    assert "analyzed_at" in data

    # 3. Retrieve analysis via GET
    get_res = client.get("/api/v1/reviews/api-analyze-test-001/analysis")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["id"] == data["id"]
    assert get_data["sentiment"] == "positive"

    # 4. Retrieve review detail and verify embedded analysis is loaded
    review_res = client.get("/api/v1/reviews/api-analyze-test-001")
    assert review_res.status_code == 200
    review_data = review_res.json()
    assert review_data["analysis"] is not None
    assert review_data["analysis"]["sentiment"] == "positive"
    assert review_data["analysis"]["category"] == "Café Facilities & Wi-Fi"

    # 5. Non-existent review returns 404
    not_found_res = client.get("/api/v1/reviews/does-not-exist/analysis")
    assert not_found_res.status_code == 404

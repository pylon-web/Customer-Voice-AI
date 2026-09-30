"""Automated tests for Kafka event streaming pipeline, producer fallback, and workers."""

import asyncio
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.kafka.events import (
    BaseEvent,
    ReviewCreatedEvent,
    ReviewCreatedPayload,
    ReviewAnalyzedEvent,
    ReviewAnalyzedPayload,
    IssueDetectedEvent,
    IssueDetectedPayload,
)
from app.kafka.producer import KafkaProducerService, get_kafka_producer
from app.kafka.consumer import KafkaConsumerService
from app.workers.review_worker import ReviewWorker


def test_kafka_event_schemas_serialization():
    """Test validation and JSON serialization of typed event envelopes."""
    now = datetime.now(timezone.utc)
    payload = ReviewCreatedPayload(
        review_id="rev-test-101",
        product_id="venture_x",
        source_id="apple_app_store",
        rating=5,
        review_title="Loved the card",
        review_text="Great lounge access and rewards program.",
        location="New York, NY",
        created_at=now,
        ingested_at=now,
        metadata_json={"os": "iOS 18.1"},
    )
    event = ReviewCreatedEvent(data=payload)

    # Ensure model serialization and structure
    serialized = event.model_dump(mode="json")
    assert serialized["event_type"] == "review.created"
    assert serialized["producer"] == "customer-voice-ai"
    assert serialized["data"]["review_id"] == "rev-test-101"
    assert serialized["data"]["product_id"] == "venture_x"
    assert serialized["data"]["rating"] == 5

    # Test deserialization
    reconstructed = ReviewCreatedEvent.model_validate(serialized)
    assert reconstructed.data.review_id == "rev-test-101"
    assert reconstructed.data.review_text == "Great lounge access and rewards program."


def test_downstream_event_schemas():
    """Verify schemas for downstream analysis and issue detection events."""
    now = datetime.now(timezone.utc)
    analyzed_event = ReviewAnalyzedEvent(
        data=ReviewAnalyzedPayload(
            review_id="rev-test-102",
            analysis_id="analysis-102",
            sentiment="negative",
            sentiment_score=-0.85,
            category="Mobile App",
            issue="Crash on startup",
            severity="critical",
            customer_intent="bug_report",
            confidence=0.98,
            analyzed_at=now,
        )
    )
    assert analyzed_event.event_type == "review.analyzed"
    assert analyzed_event.data.severity == "critical"

    issue_event = IssueDetectedEvent(
        data=IssueDetectedPayload(
            cluster_id="cluster-001",
            cluster_title="iOS Face ID Crash Spike",
            affected_product_id="c1_mobile_ios",
            wow_change_pct=500.0,
            trend_direction="emerging",
            detected_at=now,
        )
    )
    assert issue_event.event_type == "issue.detected"
    assert issue_event.data.wow_change_pct == 500.0


@pytest.mark.asyncio
async def test_kafka_producer_fallback_mode():
    """Test KafkaProducerService graceful startup and queuing in fallback mode."""
    producer = KafkaProducerService(bootstrap_servers="localhost:9999", fallback_enabled=True)
    await producer.start()

    # In test/offline mode without broker, producer is in fallback mode
    assert not producer.is_connected

    # Publish an event
    event = ReviewCreatedEvent(
        data=ReviewCreatedPayload(
            review_id="rev-test-fallback",
            product_id="c1_mobile_ios",
            source_id="apple_app_store",
            rating=1,
            review_text="App crashes constantly after update",
            created_at=datetime.now(timezone.utc),
            ingested_at=datetime.now(timezone.utc),
        )
    )
    success = await producer.publish("review.created", event, key="c1_mobile_ios")
    assert success is True

    # Assert event was queued in fallback queue and recorded in history
    assert len(producer.published_history) == 1
    assert producer.published_history[0]["topic"] == "review.created"
    assert producer.published_history[0]["key"] == "c1_mobile_ios"
    assert producer.published_history[0]["event"]["data"]["review_id"] == "rev-test-fallback"

    # Verify fallback queue dequeue
    queued_item = await producer.fallback_queue.get()
    assert queued_item["topic"] == "review.created"
    assert queued_item["data"]["data"]["review_id"] == "rev-test-fallback"

    producer.clear_history()
    assert len(producer.published_history) == 0
    await producer.stop()


def test_ingest_single_review_publishes_kafka_event(client: TestClient):
    """Test that POST /api/v1/reviews persists review AND emits review.created event."""
    producer = get_kafka_producer()
    producer.clear_history()

    payload = {
        "id": "test-kafka-single-001",
        "product_id": "venture_x",
        "source_id": "apple_app_store",
        "rating": 5,
        "review_title": "Best Travel Card",
        "review_text": "Unlimited lounge access and great points transfer partners.",
        "location": "Dallas, TX",
    }

    response = client.post("/api/v1/reviews", json=payload)
    assert response.status_code == 201

    # Check published history
    matching_events = [
        item for item in producer.published_history
        if item.get("topic") == settings.KAFKA_TOPIC_REVIEW_CREATED
        and item.get("event", {}).get("data", {}).get("review_id") == "test-kafka-single-001"
    ]
    assert len(matching_events) == 1
    published = matching_events[0]
    assert published["key"] == "venture_x"
    assert published["event"]["data"]["rating"] == 5
    assert published["event"]["data"]["product_id"] == "venture_x"


def test_ingest_batch_publishes_all_kafka_events(client: TestClient):
    """Test that POST /api/v1/reviews/batch emits review.created for each review."""
    producer = get_kafka_producer()
    producer.clear_history()

    batch_payload = {
        "reviews": [
            {
                "id": "batch-kafka-001",
                "product_id": "savor_one",
                "source_id": "google_play_store",
                "rating": 4,
                "review_text": "Great dining cash back perks.",
            },
            {
                "id": "batch-kafka-002",
                "product_id": "c1_cafe",
                "source_id": "google_places",
                "rating": 5,
                "review_text": "Fast wifi and 50 percent off cold brew coffee.",
            },
        ]
    }

    response = client.post("/api/v1/reviews/batch", json=batch_payload)
    assert response.status_code == 202

    # Verify both events published
    published_ids = {
        item.get("event", {}).get("data", {}).get("review_id")
        for item in producer.published_history
        if item.get("topic") == settings.KAFKA_TOPIC_REVIEW_CREATED
    }
    assert "batch-kafka-001" in published_ids
    assert "batch-kafka-002" in published_ids


@pytest.mark.asyncio
async def test_review_worker_processes_event_with_custom_handler():
    """Test ReviewWorker consumes review.created event and dispatches to registered handler."""
    producer = get_kafka_producer()
    producer.clear_history()

    # Setup worker
    consumer = KafkaConsumerService(topics=[settings.KAFKA_TOPIC_REVIEW_CREATED], fallback_enabled=True)
    worker = ReviewWorker(consumer=consumer)

    handled_reviews = []

    async def mock_analysis_handler(event_data: dict):
        review_id = event_data.get("data", {}).get("review_id")
        handled_reviews.append(review_id)

    worker.register_handler(mock_analysis_handler)

    # Publish an event to the producer
    test_event = ReviewCreatedEvent(
        data=ReviewCreatedPayload(
            review_id="worker-test-rev-888",
            product_id="banking_360_checking",
            source_id="apple_app_store",
            rating=1,
            review_text="Overdraft protection fee question",
            created_at=datetime.now(timezone.utc),
            ingested_at=datetime.now(timezone.utc),
        )
    )
    await producer.publish(settings.KAFKA_TOPIC_REVIEW_CREATED, test_event, key="banking_360_checking")

    # Run worker to process exactly 1 message
    await worker.run(max_messages=1)

    assert worker.processed_count == 1
    assert worker.error_count == 0
    assert "worker-test-rev-888" in handled_reviews


@pytest.mark.asyncio
async def test_review_worker_error_isolation():
    """Verify that a failing handler does not crash the worker."""
    consumer = KafkaConsumerService(topics=["test.topic"], fallback_enabled=True)
    worker = ReviewWorker(consumer=consumer)

    async def buggy_handler(event_data: dict):
        raise RuntimeError("Intentional downstream failure for testing error handling")

    worker.register_handler(buggy_handler)

    sample_msg = {
        "topic": "test.topic",
        "data": {
            "event_type": "review.created",
            "data": {"review_id": "buggy-rev-001"}
        }
    }

    success = await worker.process_message(sample_msg)
    assert success is False
    assert worker.error_count == 1
    assert worker.processed_count == 0

"""Kafka event producers, consumers, and message schemas."""

from app.kafka.events import (
    BaseEvent,
    ReviewCreatedPayload,
    ReviewCreatedEvent,
    ReviewAnalyzedPayload,
    ReviewAnalyzedEvent,
    ReviewEmbeddedPayload,
    ReviewEmbeddedEvent,
    IssueDetectedPayload,
    IssueDetectedEvent,
    ReportGeneratedPayload,
    ReportGeneratedEvent,
)
from app.kafka.producer import KafkaProducerService, get_kafka_producer
from app.kafka.consumer import KafkaConsumerService

__all__ = [
    "BaseEvent",
    "ReviewCreatedPayload",
    "ReviewCreatedEvent",
    "ReviewAnalyzedPayload",
    "ReviewAnalyzedEvent",
    "ReviewEmbeddedPayload",
    "ReviewEmbeddedEvent",
    "IssueDetectedPayload",
    "IssueDetectedEvent",
    "ReportGeneratedPayload",
    "ReportGeneratedEvent",
    "KafkaProducerService",
    "get_kafka_producer",
    "KafkaConsumerService",
]

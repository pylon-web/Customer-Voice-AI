"""Asynchronous Kafka Producer service with transparent in-memory fallback."""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, Union, List

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, KafkaError

from app.core.config import settings
from app.core.logging import get_logger
from app.kafka.events import BaseEvent

logger = get_logger("cva.kafka.producer")


class KafkaProducerService:
    """Manages publishing of structured events to Kafka topics with fallback support."""

    def __init__(self, bootstrap_servers: Optional[str] = None, fallback_enabled: Optional[bool] = None):
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self.fallback_enabled = fallback_enabled if fallback_enabled is not None else settings.KAFKA_ENABLE_FALLBACK_SYNC
        self._producer: Optional[AIOKafkaProducer] = None
        self._is_connected: bool = False
        self._fallback_queue: asyncio.Queue = asyncio.Queue()
        self._published_history: List[Dict[str, Any]] = []

    @property
    def is_connected(self) -> bool:
        """Returns True if actively connected to a real Kafka broker."""
        return self._is_connected

    @property
    def fallback_queue(self) -> asyncio.Queue:
        """Access the in-memory fallback queue."""
        return self._fallback_queue

    @property
    def published_history(self) -> List[Dict[str, Any]]:
        """History of published events (useful for test assertions and offline audit)."""
        return self._published_history

    def get_published_events(self, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return list of published event payloads, optionally filtered by topic."""
        if topic:
            return [p["event"] for p in self._published_history if p["topic"] == topic]
        return [p["event"] for p in self._published_history]

    def clear_history(self) -> None:
        """Clear published event history (useful in test setups)."""
        self._published_history.clear()
        while not self._fallback_queue.empty():
            try:
                self._fallback_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def start(self) -> None:
        """Initialize connection to Kafka broker or fall back to in-memory mode."""
        if self._is_connected:
            return

        try:
            logger.info("Connecting to Kafka broker", servers=self.bootstrap_servers)
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                request_timeout_ms=3000,
                retry_backoff_ms=500,
            )
            # Use wait_for with 3-second timeout to avoid stalling startup if broker is offline
            await asyncio.wait_for(self._producer.start(), timeout=3.0)
            self._is_connected = True
            logger.info("Kafka Producer successfully connected", servers=self.bootstrap_servers)
        except (KafkaConnectionError, KafkaError, asyncio.TimeoutError, OSError, Exception) as exc:
            self._is_connected = False
            if self._producer:
                try:
                    await self._producer.stop()
                except Exception:
                    pass
                self._producer = None

            if self.fallback_enabled:
                logger.warning(
                    "Kafka broker unreachable. Operating in graceful in-memory fallback mode.",
                    servers=self.bootstrap_servers,
                    reason=str(exc),
                )
            else:
                logger.error("Failed to connect to Kafka broker and fallback is disabled.", reason=str(exc))
                raise

    async def stop(self) -> None:
        """Gracefully terminate Kafka producer connection."""
        if self._producer and self._is_connected:
            try:
                await self._producer.stop()
                logger.info("Kafka Producer stopped successfully")
            except Exception as e:
                logger.warning("Error stopping Kafka Producer", error=str(e))
        self._is_connected = False
        self._producer = None

    async def publish(
        self,
        topic: str,
        event: Union[BaseEvent, Dict[str, Any]],
        key: Optional[str] = None,
    ) -> bool:
        """Publish an event to a specified Kafka topic.

        Args:
            topic: Target Kafka topic (e.g. 'review.created').
            event: Event object (BaseEvent instance) or raw dictionary.
            key: Optional partitioning key (e.g. review_id or product_id).

        Returns:
            bool: True if event was published or queued successfully.
        """
        if isinstance(event, BaseEvent):
            event_dict = event.model_dump(mode="json")
        elif isinstance(event, dict):
            event_dict = event
        else:
            raise ValueError(f"Event must be a BaseEvent or dict, received: {type(event)}")

        # Serialize to JSON bytes
        payload_bytes = json.dumps(event_dict, default=str).encode("utf-8")
        key_bytes = key.encode("utf-8") if key else None

        if self._is_connected and self._producer:
            try:
                await self._producer.send_and_wait(
                    topic=topic,
                    value=payload_bytes,
                    key=key_bytes,
                )
                logger.debug(
                    "Published event to Kafka broker",
                    topic=topic,
                    event_type=event_dict.get("event_type"),
                    key=key,
                )
            except Exception as exc:
                logger.error("Failed to send event to Kafka broker, falling back", error=str(exc))
                if not self.fallback_enabled:
                    raise
                self._fallback_queue.put_nowait({"topic": topic, "key": key, "data": event_dict})
        else:
            # Enqueue in fallback queue
            self._fallback_queue.put_nowait({"topic": topic, "key": key, "data": event_dict})
            logger.debug(
                "Buffered event in fallback queue",
                topic=topic,
                event_type=event_dict.get("event_type"),
                key=key,
            )

        # Maintain in-memory history (bounded at 5000 records)
        self._published_history.append({"topic": topic, "key": key, "event": event_dict})
        if len(self._published_history) > 5000:
            self._published_history.pop(0)

        return True


# Global singleton instance
_producer_instance: Optional[KafkaProducerService] = None


def get_kafka_producer() -> KafkaProducerService:
    """Retrieve or create the global KafkaProducerService singleton."""
    global _producer_instance
    if _producer_instance is None:
        _producer_instance = KafkaProducerService()
    return _producer_instance

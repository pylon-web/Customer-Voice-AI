"""Asynchronous Kafka Consumer service with transparent in-memory fallback."""

import asyncio
import json
from typing import List, Dict, Any, Optional, AsyncGenerator

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError, KafkaError

from app.core.config import settings
from app.core.logging import get_logger
from app.kafka.producer import get_kafka_producer

logger = get_logger("cva.kafka.consumer")


class KafkaConsumerService:
    """Manages subscribing and consuming structured events from Kafka topics."""

    def __init__(
        self,
        topics: Optional[List[str]] = None,
        group_id: Optional[str] = None,
        bootstrap_servers: Optional[str] = None,
        fallback_enabled: Optional[bool] = None,
    ):
        self.topics = topics or [settings.KAFKA_TOPIC_REVIEW_CREATED]
        self.group_id = group_id or settings.KAFKA_CONSUMER_GROUP
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self.fallback_enabled = fallback_enabled if fallback_enabled is not None else settings.KAFKA_ENABLE_FALLBACK_SYNC
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._is_connected: bool = False
        self._running: bool = False

    @property
    def is_connected(self) -> bool:
        """Returns True if connected to a real Kafka broker."""
        return self._is_connected

    async def start(self) -> None:
        """Start Kafka consumer or fall back to in-memory mode."""
        self._running = True
        try:
            logger.info("Connecting Kafka Consumer", topics=self.topics, group_id=self.group_id)
            self._consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                request_timeout_ms=3000,
            )
            await asyncio.wait_for(self._consumer.start(), timeout=3.0)
            self._is_connected = True
            logger.info("Kafka Consumer successfully started", topics=self.topics)
        except (KafkaConnectionError, KafkaError, asyncio.TimeoutError, OSError, Exception) as exc:
            self._is_connected = False
            if self._consumer:
                try:
                    await self._consumer.stop()
                except Exception:
                    pass
                self._consumer = None

            if self.fallback_enabled:
                logger.warning(
                    "Kafka Consumer broker unreachable. Operating in fallback queue consumption mode.",
                    reason=str(exc),
                )
            else:
                logger.error("Failed to connect Kafka Consumer and fallback is disabled", reason=str(exc))
                raise

    async def stop(self) -> None:
        """Gracefully stop Kafka consumer."""
        self._running = False
        if self._consumer and self._is_connected:
            try:
                await self._consumer.stop()
                logger.info("Kafka Consumer stopped successfully")
            except Exception as e:
                logger.warning("Error stopping Kafka Consumer", error=str(e))
        self._is_connected = False
        self._consumer = None

    async def consume_messages(self, max_messages: Optional[int] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Consume messages either from Kafka broker or the in-memory fallback queue.

        Yields dictionaries with format:
            {"topic": str, "key": Optional[str], "data": Dict[str, Any]}
        """
        count = 0
        if self._is_connected and self._consumer:
            try:
                async for msg in self._consumer:
                    if not self._running:
                        break
                    try:
                        raw_data = json.loads(msg.value.decode("utf-8"))
                        key_str = msg.key.decode("utf-8") if msg.key else None
                        yield {"topic": msg.topic, "key": key_str, "data": raw_data}
                        count += 1
                        if max_messages and count >= max_messages:
                            break
                    except json.JSONDecodeError as decode_err:
                        logger.error("Failed to decode message from Kafka", error=str(decode_err))
            except Exception as exc:
                logger.error("Error during Kafka message consumption", error=str(exc))
        else:
            # Fallback in-memory queue consumption
            queue = get_kafka_producer().fallback_queue
            while self._running:
                try:
                    # Wait up to 1 second for a new message
                    item = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield item
                    queue.task_done()
                    count += 1
                    if max_messages and count >= max_messages:
                        break
                except asyncio.TimeoutError:
                    if max_messages:
                        # In max_messages mode, timeout means no more messages available right now
                        break
                    continue
                except Exception as e:
                    logger.error("Error retrieving from fallback queue", error=str(e))
                    break

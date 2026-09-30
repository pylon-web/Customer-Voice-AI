"""Asynchronous worker consuming review.created events and dispatching downstream tasks."""

import asyncio
import signal
import sys
from typing import Callable, Coroutine, List, Dict, Any, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.kafka.consumer import KafkaConsumerService
from app.kafka.events import ReviewCreatedEvent

logger = get_logger("cva.worker.review")

HandlerType = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]


class ReviewWorker:
    """Worker service that processes customer review events from Kafka."""

    def __init__(
        self,
        consumer: Optional[KafkaConsumerService] = None,
        handlers: Optional[List[HandlerType]] = None,
    ):
        self.consumer = consumer or KafkaConsumerService(
            topics=[settings.KAFKA_TOPIC_REVIEW_CREATED],
            group_id=f"{settings.KAFKA_CONSUMER_GROUP}-reviews",
        )
        self.handlers: List[HandlerType] = handlers or []
        self._running: bool = False
        self.processed_count: int = 0
        self.error_count: int = 0

    def register_handler(self, handler: HandlerType) -> None:
        """Register a downstream async handler (e.g., AI Analyzer, Vectorizer)."""
        self.handlers.append(handler)

    async def process_message(self, message: Dict[str, Any]) -> bool:
        """Process a single event message across all registered handlers."""
        data = message.get("data", {})
        topic = message.get("topic", "")

        try:
            # Validate or parse into ReviewCreatedEvent if applicable
            event_type = data.get("event_type")
            review_payload = data.get("data", {})
            review_id = review_payload.get("review_id") or data.get("id")

            logger.info(
                "Processing review event",
                event_type=event_type,
                topic=topic,
                review_id=review_id,
            )

            # Execute all registered handlers sequentially
            for handler in self.handlers:
                await handler(data)

            self.processed_count += 1
            return True

        except Exception as exc:
            self.error_count += 1
            logger.error("Error processing review event", error=str(exc), message_payload=data)
            return False

    async def run(self, max_messages: Optional[int] = None) -> None:
        """Start worker loop and consume messages."""
        self._running = True
        await self.consumer.start()
        logger.info("ReviewWorker started. Waiting for events...")

        try:
            async for message in self.consumer.consume_messages(max_messages=max_messages):
                if not self._running:
                    break
                await self.process_message(message)
                if max_messages and self.processed_count >= max_messages:
                    break
        except asyncio.CancelledError:
            logger.info("ReviewWorker run cancelled")
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop worker and consumer."""
        if not self._running:
            return
        self._running = False
        await self.consumer.stop()
        logger.info(
            "ReviewWorker stopped",
            processed_count=self.processed_count,
            error_count=self.error_count,
        )


async def _main():
    """CLI entrypoint for standalone worker execution."""
    worker = ReviewWorker()

    # Graceful shutdown signal handling
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))

    logger.info("Starting standalone ReviewWorker process...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(_main())

"""Service orchestrating AI review analysis, database persistence, and event emission."""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.entities import ReviewAnalysis
from app.agents.analyzer import BaseAnalysisAgent, get_analysis_agent
from app.repositories.review_repo import ReviewRepository
from app.repositories.analysis_repo import AnalysisRepository
from app.kafka.producer import KafkaProducerService, get_kafka_producer
from app.kafka.events import ReviewAnalyzedEvent, ReviewAnalyzedPayload

logger = get_logger("cva.service.analysis")


class AnalysisService:
    """Orchestrates structured intelligence extraction on customer reviews."""

    def __init__(
        self,
        session: AsyncSession,
        agent: Optional[BaseAnalysisAgent] = None,
        kafka_producer: Optional[KafkaProducerService] = None,
    ):
        self.session = session
        self.review_repo = ReviewRepository(session)
        self.analysis_repo = AnalysisRepository(session)
        self.agent = agent or get_analysis_agent()
        self.kafka_producer = kafka_producer or get_kafka_producer()

    async def analyze_review(self, review_id: str) -> ReviewAnalysis:
        """Run AI analysis on a specific review, persist findings, and publish event."""
        review = await self.review_repo.get_by_id(review_id)
        if not review:
            raise NotFoundError(f"Review '{review_id}' does not exist.")

        # Execute AI extraction agent
        result = await self.agent.analyze(
            text=review.review_text,
            rating=review.rating,
            product_id=review.product_id,
            title=review.review_title,
            location=review.location,
        )

        analysis = ReviewAnalysis(
            id=str(uuid.uuid4()),
            review_id=review.id,
            sentiment=result.sentiment,
            sentiment_score=result.sentiment_score,
            category=result.category,
            issue=result.issue,
            severity=result.severity,
            customer_intent=result.customer_intent,
            entities=result.entities,
            confidence=result.confidence,
            analyzed_at=datetime.now(timezone.utc),
        )

        saved = await self.analysis_repo.upsert(analysis)

        # Dispatch review.analyzed event downstream
        try:
            event = ReviewAnalyzedEvent(
                data=ReviewAnalyzedPayload(
                    review_id=review.id,
                    analysis_id=saved.id,
                    sentiment=saved.sentiment,
                    sentiment_score=saved.sentiment_score,
                    category=saved.category,
                    issue=saved.issue,
                    severity=saved.severity,
                    customer_intent=saved.customer_intent,
                    confidence=saved.confidence,
                    analyzed_at=saved.analyzed_at,
                )
            )
            await self.kafka_producer.publish(
                topic=settings.KAFKA_TOPIC_REVIEW_ANALYZED,
                event=event,
                key=review.product_id,
            )
        except Exception as kafka_err:
            logger.warning(
                f"Failed to publish review.analyzed event for {review.id}",
                extra={"review_id": review.id, "error": str(kafka_err)},
            )

        logger.info(
            f"Successfully analyzed review {review.id}",
            extra={
                "review_id": review.id,
                "sentiment": saved.sentiment,
                "category": saved.category,
                "severity": saved.severity,
            },
        )
        return saved


async def handle_review_created_event(event_data: Dict[str, Any]) -> Optional[ReviewAnalysis]:
    """Background event handler registered with ReviewWorker to process review.created events."""
    payload = event_data.get("data", {})
    review_id = payload.get("review_id") or event_data.get("id")

    if not review_id:
        logger.warning("Received review.created event without a valid review_id", extra={"payload": event_data})
        return None

    async with async_session_factory() as session:
        service = AnalysisService(session)
        try:
            analysis = await service.analyze_review(review_id)
            await session.commit()
            return analysis
        except Exception as exc:
            await session.rollback()
            logger.error(
                f"Error in background review analysis handler for {review_id}",
                extra={"review_id": review_id, "error": str(exc)},
            )
            return None

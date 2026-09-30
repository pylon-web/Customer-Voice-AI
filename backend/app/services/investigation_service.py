"""Investigation service orchestrating LangGraph multi-agent root cause analysis and HITL approvals."""

from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.errors import NotFoundError, ValidationError
from app.models.entities import Recommendation, Approval, IssueCluster
from app.agents.investigation_agent import InvestigationAgent, get_investigation_agent
from app.agents.investigation_graph import InvestigationState
from app.repositories.recommendation_repo import RecommendationRepository
from app.repositories.cluster_repo import ClusterRepository
from app.repositories.trend_repo import TrendRepository
from app.kafka.producer import KafkaProducerService, get_kafka_producer

logger = get_logger("cva.service.investigation")


class InvestigationService:
    """Orchestrates multi-agent root cause investigations and human-in-the-loop decisions."""

    def __init__(
        self,
        session: AsyncSession,
        agent: Optional[InvestigationAgent] = None,
        kafka_producer: Optional[KafkaProducerService] = None,
    ):
        self.session = session
        self.agent = agent or get_investigation_agent()
        self.kafka_producer = kafka_producer or get_kafka_producer()
        self.rec_repo = RecommendationRepository(session)
        self.cluster_repo = ClusterRepository(session)
        self.trend_repo = TrendRepository(session)

    async def investigate_cluster(self, cluster_id: str) -> Recommendation:
        """Run LangGraph investigation state machine on an issue cluster."""
        cluster = await self.cluster_repo.get_by_id(cluster_id)
        if not cluster:
            raise NotFoundError(resource="IssueCluster", identifier=cluster_id)

        # Retrieve velocity trend summary if available
        trend = await self.trend_repo.get_latest_by_cluster_id(cluster_id)
        velocity_summary = None
        if trend:
            velocity_summary = {
                "wow_change_pct": trend.wow_change_pct,
                "trend_direction": trend.trend_direction,
                "current_volume": trend.current_volume,
                "anomaly_score": trend.anomaly_score,
            }

        # Build initial state for the LangGraph state machine
        initial_state: InvestigationState = {
            "cluster_id": cluster.id,
            "cluster_title": cluster.cluster_title,
            "affected_product_id": cluster.affected_product_id,
            "category": cluster.category,
            "review_count": cluster.review_count,
            "negative_pct": cluster.negative_pct,
            "representative_quotes": cluster.representative_quotes or [],
            "velocity_summary": velocity_summary,
            "iteration_count": 0,
        }

        # Execute investigation graph
        final_state = await self.agent.investigate(initial_state)

        # Persist Recommendation
        rec = Recommendation(
            cluster_id=cluster.id,
            suggested_team_id=final_state.get("suggested_team_id", "digital_eng_mobile"),
            observed_evidence=final_state.get("observed_evidence", ""),
            investigation_hypothesis=final_state.get("investigation_hypothesis", ""),
            recommended_action=final_state.get("recommended_action", ""),
            confidence=final_state.get("confidence", 0.85),
            status="pending_approval",
        )
        persisted = await self.rec_repo.create(rec)
        await self.session.commit()

        logger.info(
            f"Created recommendation for cluster '{cluster.cluster_title}'",
            extra={
                "recommendation_id": persisted.id,
                "cluster_id": cluster.id,
                "team": persisted.suggested_team_id,
                "confidence": persisted.confidence,
            },
        )
        return persisted

    async def record_human_decision(
        self,
        recommendation_id: str,
        reviewer_name: str,
        decision: str,
        reviewer_notes: Optional[str] = None,
        modified_action: Optional[str] = None,
    ) -> Tuple[Recommendation, Approval]:
        """Record Human-in-the-Loop decision on an operational recommendation."""
        valid_decisions = ["approved", "rejected", "modified"]
        if decision not in valid_decisions:
            raise ValidationError(f"Invalid decision '{decision}'. Must be one of {valid_decisions}.")

        rec = await self.rec_repo.get_by_id(recommendation_id)
        if not rec:
            raise NotFoundError(resource="Recommendation", identifier=recommendation_id)

        updated_rec, approval = await self.rec_repo.record_approval_decision(
            recommendation=rec,
            reviewer_name=reviewer_name,
            decision=decision,
            reviewer_notes=reviewer_notes,
            modified_action=modified_action,
        )
        await self.session.commit()

        # Re-fetch with eagerly loaded relations
        refreshed = await self.rec_repo.get_by_id(recommendation_id)

        logger.info(
            f"Recorded HITL decision '{decision}' for recommendation {recommendation_id} by {reviewer_name}",
            extra={"decision": decision, "reviewer": reviewer_name, "recommendation_id": recommendation_id},
        )
        return refreshed or updated_rec, approval

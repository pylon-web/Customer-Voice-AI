"""Trend and Velocity Anomaly Detection Service.

Calculates rolling baseline metrics, week-over-week velocity changes, statistical z-scores,
and trajectory classifications ('emerging', 'stable', 'improving') across issue clusters.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.entities import IssueCluster, ClusterReview, Review, TrendMetric
from app.models.schemas import TrendCalculateRequest, TrendCalculateResponse
from app.repositories.trend_repo import TrendRepository
from app.repositories.cluster_repo import ClusterRepository
from app.kafka.producer import KafkaProducerService, get_kafka_producer
from app.kafka.events import IssueDetectedEvent, IssueDetectedPayload

logger = get_logger("cva.service.trend")


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime object is UTC offset-aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class TrendService:
    """Calculates time-series trend metrics and identifies velocity anomalies."""

    def __init__(
        self,
        session: AsyncSession,
        kafka_producer: Optional[KafkaProducerService] = None,
    ):
        self.session = session
        self.kafka_producer = kafka_producer or get_kafka_producer()
        self.trend_repo = TrendRepository(session)
        self.cluster_repo = ClusterRepository(session)

    async def calculate_trend_for_cluster(
        self,
        cluster: IssueCluster,
        as_of_date: Optional[datetime] = None,
    ) -> TrendMetric:
        """Compute rolling 4-week baseline, WoW velocity, z-score, and classify trajectory for a cluster."""
        # 1. Fetch review timestamps for reviews belonging to this cluster
        stmt = (
            select(Review.created_at)
            .join(ClusterReview, Review.id == ClusterReview.review_id)
            .where(ClusterReview.cluster_id == cluster.id)
        )
        res = await self.session.execute(stmt)
        raw_timestamps = res.scalars().all()
        timestamps = [_ensure_utc(ts) for ts in raw_timestamps]

        # 2. Determine anchor reference date
        if as_of_date is not None:
            anchor = _ensure_utc(as_of_date)
        elif timestamps:
            anchor = max(timestamps)
        else:
            anchor = datetime.now(timezone.utc)

        # 3. Compute time windows
        # Current week window: [anchor - 7 days, anchor]
        curr_start = anchor - timedelta(days=7)
        curr_end = anchor

        # Previous week window: [anchor - 14 days, anchor - 7 days)
        prev_start = anchor - timedelta(days=14)
        prev_end = anchor - timedelta(days=7)

        # Count current & previous volume
        current_volume = sum(1 for ts in timestamps if curr_start <= ts <= curr_end)
        previous_volume = sum(1 for ts in timestamps if prev_start <= ts < prev_end)

        # Baseline 4 weeks: 4 consecutive 7-day windows prior to current week
        baseline_weeks_counts: List[int] = []
        for i in range(1, settings.TREND_BASELINE_WEEKS + 1):
            w_start = anchor - timedelta(days=7 * (i + 1))
            w_end = anchor - timedelta(days=7 * i)
            count = sum(1 for ts in timestamps if w_start <= ts < w_end)
            baseline_weeks_counts.append(count)

        baseline_4wk_avg = float(np.mean(baseline_weeks_counts)) if baseline_weeks_counts else 0.0
        baseline_std = float(np.std(baseline_weeks_counts)) if baseline_weeks_counts else 0.0

        # 4. Week-over-Week (WoW) Percentage Change
        if previous_volume > 0:
            wow_change_pct = round(((current_volume - previous_volume) / float(previous_volume)) * 100.0, 2)
        elif current_volume > 0:
            wow_change_pct = 100.0  # Spiked from 0 prior volume
        else:
            wow_change_pct = 0.0

        # 5. Statistical Anomaly Score (Z-Score)
        if baseline_std > 0:
            anomaly_score = round(float((current_volume - baseline_4wk_avg) / baseline_std), 2)
        elif current_volume > baseline_4wk_avg:
            # If standard deviation is 0 but current volume exceeds baseline average
            diff = current_volume - baseline_4wk_avg
            anomaly_score = round(float(min(diff, 5.0)), 2)
        else:
            anomaly_score = 0.0

        # 6. Trajectory Classification
        threshold_pct = settings.TREND_EMERGING_THRESHOLD_PCT  # Default: 25.0%
        if current_volume >= 3 and (anomaly_score >= 2.0 or wow_change_pct >= threshold_pct):
            trend_direction = "emerging"
        elif previous_volume >= 3 and wow_change_pct <= -threshold_pct:
            trend_direction = "improving"
        else:
            trend_direction = "stable"

        # 7. Persist TrendMetric
        metric = TrendMetric(
            cluster_id=cluster.id,
            period_start=curr_start,
            period_end=curr_end,
            current_volume=current_volume,
            previous_volume=previous_volume,
            baseline_4wk_avg=round(baseline_4wk_avg, 2),
            wow_change_pct=wow_change_pct,
            trend_direction=trend_direction,
            anomaly_score=anomaly_score,
        )
        persisted = await self.trend_repo.create(metric)
        await self.session.commit()

        logger.info(
            f"Calculated trend for cluster '{cluster.cluster_title}'",
            extra={
                "cluster_id": cluster.id,
                "direction": trend_direction,
                "current_vol": current_volume,
                "prev_vol": previous_volume,
                "wow_pct": wow_change_pct,
                "anomaly_score": anomaly_score,
            },
        )

        # 8. Dispatch issue.detected Kafka event for emerging anomalies
        if trend_direction == "emerging":
            try:
                event = IssueDetectedEvent(
                    data=IssueDetectedPayload(
                        cluster_id=cluster.id,
                        cluster_title=cluster.cluster_title,
                        affected_product_id=cluster.affected_product_id,
                        wow_change_pct=wow_change_pct,
                        trend_direction=trend_direction,
                        detected_at=datetime.now(timezone.utc),
                    )
                )
                await self.kafka_producer.publish(
                    topic=settings.KAFKA_TOPIC_ISSUE_DETECTED,
                    event=event,
                    key=cluster.affected_product_id,
                )
            except Exception as kafka_err:
                logger.warning(
                    f"Failed to publish issue.detected event for cluster {cluster.id}",
                    extra={"cluster_id": cluster.id, "error": str(kafka_err)},
                )

        return persisted

    async def calculate_trends(
        self,
        request: Optional[TrendCalculateRequest] = None,
    ) -> TrendCalculateResponse:
        """Run trend and anomaly calculation for one or all active clusters."""
        req = request or TrendCalculateRequest()
        as_of_date = req.as_of_date

        if req.cluster_id:
            cluster = await self.cluster_repo.get_by_id(req.cluster_id)
            clusters = [cluster] if cluster else []
        else:
            clusters = await self.cluster_repo.get_active_clusters(limit=200)

        trend_ids: List[str] = []
        emerging_cnt = 0
        improving_cnt = 0
        stable_cnt = 0

        for c in clusters:
            metric = await self.calculate_trend_for_cluster(c, as_of_date=as_of_date)
            trend_ids.append(metric.id)
            if metric.trend_direction == "emerging":
                emerging_cnt += 1
            elif metric.trend_direction == "improving":
                improving_cnt += 1
            else:
                stable_cnt += 1

        return TrendCalculateResponse(
            trends_calculated=len(trend_ids),
            emerging_count=emerging_cnt,
            improving_count=improving_cnt,
            stable_count=stable_cnt,
            trend_ids=trend_ids,
        )

"""Repository for trend metrics, velocity anomalies, and temporal aggregations."""

from typing import List, Optional, Tuple
from sqlalchemy import select, desc, func, or_, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import TrendMetric, IssueCluster


class TrendRepository:
    """Data access repository for trend metrics and cluster velocity analytics."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, metric: TrendMetric) -> TrendMetric:
        """Persist a new trend metric record."""
        self.session.add(metric)
        await self.session.flush()
        return metric

    async def get_by_id(self, trend_id: str) -> Optional[TrendMetric]:
        """Fetch trend metric by ID with attached cluster relationship."""
        stmt = (
            select(TrendMetric)
            .options(selectinload(TrendMetric.cluster))
            .where(TrendMetric.id == trend_id)
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_by_cluster_id(self, cluster_id: str, limit: int = 50) -> List[TrendMetric]:
        """Fetch historical trend metrics for a specific cluster ordered chronologically."""
        stmt = (
            select(TrendMetric)
            .options(selectinload(TrendMetric.cluster))
            .where(TrendMetric.cluster_id == cluster_id)
            .order_by(desc(TrendMetric.period_end))
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_latest_by_cluster_id(self, cluster_id: str) -> Optional[TrendMetric]:
        """Fetch most recent trend metric calculated for a cluster."""
        stmt = (
            select(TrendMetric)
            .options(selectinload(TrendMetric.cluster))
            .where(TrendMetric.cluster_id == cluster_id)
            .order_by(desc(TrendMetric.period_end))
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def filter_trends(
        self,
        product_id: Optional[str] = None,
        trend_direction: Optional[str] = None,
        is_anomaly: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[TrendMetric], int]:
        """Filter and paginate trend metrics with cluster product joins and anomaly filters."""
        stmt = select(TrendMetric).options(selectinload(TrendMetric.cluster))
        count_stmt = select(func.count(TrendMetric.id))

        if product_id:
            stmt = stmt.join(IssueCluster, TrendMetric.cluster_id == IssueCluster.id).where(
                IssueCluster.affected_product_id == product_id
            )
            count_stmt = count_stmt.join(IssueCluster, TrendMetric.cluster_id == IssueCluster.id).where(
                IssueCluster.affected_product_id == product_id
            )

        if trend_direction:
            stmt = stmt.where(TrendMetric.trend_direction == trend_direction)
            count_stmt = count_stmt.where(TrendMetric.trend_direction == trend_direction)

        if is_anomaly is not None:
            if is_anomaly:
                condition = or_(
                    TrendMetric.anomaly_score >= 2.0,
                    TrendMetric.wow_change_pct >= 25.0,
                    TrendMetric.trend_direction == "emerging",
                )
            else:
                condition = and_(
                    TrendMetric.anomaly_score < 2.0,
                    TrendMetric.wow_change_pct < 25.0,
                    TrendMetric.trend_direction != "emerging",
                )
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        # Count total
        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar() or 0

        # Query page
        offset = (page - 1) * page_size
        stmt = stmt.order_by(desc(TrendMetric.period_end), desc(TrendMetric.anomaly_score)).offset(offset).limit(page_size)
        res = await self.session.execute(stmt)
        items = list(res.scalars().all())

        return items, total

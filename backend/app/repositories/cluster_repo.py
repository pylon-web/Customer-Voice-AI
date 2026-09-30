"""Repository for issue clusters and cluster-review associations."""

from typing import List, Optional, Tuple
from sqlalchemy import select, desc, func, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import IssueCluster, ClusterReview, Review


class ClusterRepository:
    """Data access repository for issue clusters and semantic groups."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_cluster(self, cluster: IssueCluster) -> IssueCluster:
        """Persist a new issue cluster."""
        self.session.add(cluster)
        await self.session.flush()
        return cluster

    async def get_by_id(self, cluster_id: str) -> Optional[IssueCluster]:
        """Fetch cluster by ID with affected product, trend metrics, and recommendations."""
        from app.models.entities import Recommendation
        stmt = (
            select(IssueCluster)
            .options(
                selectinload(IssueCluster.affected_product),
                selectinload(IssueCluster.trend_metrics),
                selectinload(IssueCluster.recommendations).selectinload(Recommendation.approvals),
                selectinload(IssueCluster.cluster_reviews).selectinload(ClusterReview.review).selectinload(Review.analysis),
            )
            .where(IssueCluster.id == cluster_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_active_clusters(self, limit: int = 50) -> List[IssueCluster]:
        """Fetch active clusters ordered by review volume."""
        stmt = (
            select(IssueCluster)
            .options(selectinload(IssueCluster.affected_product))
            .where(IssueCluster.status == "active")
            .order_by(desc(IssueCluster.review_count))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def filter_clusters(
        self,
        product_id: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[IssueCluster], int]:
        """Query issue clusters with optional filters, pagination, and total count."""
        stmt = select(IssueCluster).options(selectinload(IssueCluster.affected_product))

        if product_id:
            stmt = stmt.where(IssueCluster.affected_product_id == product_id)
        if category:
            stmt = stmt.where(IssueCluster.category == category)
        if status:
            stmt = stmt.where(IssueCluster.status == status)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one_or_none() or 0

        # Paginate
        offset = (page - 1) * page_size
        stmt = stmt.order_by(desc(IssueCluster.review_count)).offset(offset).limit(page_size)
        res = await self.session.execute(stmt)
        return list(res.scalars().all()), total

    async def link_review(
        self, cluster_id: str, review_id: str, similarity_score: float = 0.0
    ) -> ClusterReview:
        """Associate a customer review with an issue cluster."""
        association = ClusterReview(
            cluster_id=cluster_id,
            review_id=review_id,
            similarity_score=similarity_score,
        )
        self.session.add(association)
        await self.session.flush()
        return association

    async def clear_cluster_reviews(self, cluster_id: str) -> None:
        """Remove existing review associations for a cluster."""
        stmt = delete(ClusterReview).where(ClusterReview.cluster_id == cluster_id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def get_cluster_reviews(
        self, cluster_id: str, limit: int = 50, offset: int = 0
    ) -> List[ClusterReview]:
        """Fetch associated reviews for a cluster ordered by similarity to centroid."""
        stmt = (
            select(ClusterReview)
            .options(
                selectinload(ClusterReview.review).selectinload(Review.analysis),
                selectinload(ClusterReview.review).selectinload(Review.product),
            )
            .where(ClusterReview.cluster_id == cluster_id)
            .order_by(desc(ClusterReview.similarity_score))
            .offset(offset)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

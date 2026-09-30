"""Repository for operational recommendations and human-in-the-loop approval decisions."""

from typing import List, Optional, Tuple
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Recommendation, Approval, IssueCluster


class RecommendationRepository:
    """Data access repository for recommendations, hypotheses, and HITL audit logs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, rec: Recommendation) -> Recommendation:
        """Persist a new recommendation entity."""
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def get_by_id(self, rec_id: str) -> Optional[Recommendation]:
        """Fetch recommendation by ID with cluster, team, and approval audit relations."""
        stmt = (
            select(Recommendation)
            .options(
                selectinload(Recommendation.cluster),
                selectinload(Recommendation.suggested_team),
                selectinload(Recommendation.approvals),
            )
            .where(Recommendation.id == rec_id)
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_by_cluster_id(self, cluster_id: str) -> Optional[Recommendation]:
        """Fetch the most recent recommendation created for a cluster."""
        stmt = (
            select(Recommendation)
            .options(
                selectinload(Recommendation.cluster),
                selectinload(Recommendation.suggested_team),
                selectinload(Recommendation.approvals),
            )
            .where(Recommendation.cluster_id == cluster_id)
            .order_by(desc(Recommendation.created_at))
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_recommendations(
        self,
        status: Optional[str] = None,
        team_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Recommendation], int]:
        """Query and paginate recommendations with optional status and team filters."""
        stmt = select(Recommendation).options(
            selectinload(Recommendation.cluster),
            selectinload(Recommendation.suggested_team),
            selectinload(Recommendation.approvals),
        )
        count_stmt = select(func.count(Recommendation.id))

        if status:
            stmt = stmt.where(Recommendation.status == status)
            count_stmt = count_stmt.where(Recommendation.status == status)

        if team_id:
            stmt = stmt.where(Recommendation.suggested_team_id == team_id)
            count_stmt = count_stmt.where(Recommendation.suggested_team_id == team_id)

        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar() or 0

        offset = (page - 1) * page_size
        stmt = stmt.order_by(desc(Recommendation.created_at)).offset(offset).limit(page_size)
        res = await self.session.execute(stmt)
        items = list(res.scalars().all())

        return items, total

    async def record_approval_decision(
        self,
        recommendation: Recommendation,
        reviewer_name: str,
        decision: str,
        reviewer_notes: Optional[str] = None,
        modified_action: Optional[str] = None,
    ) -> Tuple[Recommendation, Approval]:
        """Record human audit decision and update recommendation status."""
        approval = Approval(
            recommendation=recommendation,
            recommendation_id=recommendation.id,
            reviewer_name=reviewer_name,
            decision=decision,
            reviewer_notes=reviewer_notes,
            modified_action=modified_action,
        )
        if "approvals" in getattr(recommendation, "__dict__", {}):
            recommendation.approvals.append(approval)
        self.session.add(approval)

        recommendation.status = decision
        if modified_action:
            recommendation.recommended_action = modified_action

        await self.session.flush()
        return recommendation, approval

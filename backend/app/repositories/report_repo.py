"""Repository for executive intelligence reports and report-issue relationships."""

from typing import List, Optional, Tuple
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Report, ReportIssue, IssueCluster, Recommendation, Team


class ReportRepository:
    """Data access repository for weekly intelligence reports and highlighted cluster issues."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_report(self, report: Report) -> Report:
        """Persist a new executive intelligence report."""
        self.session.add(report)
        await self.session.flush()
        return report

    async def get_by_id(self, report_id: str) -> Optional[Report]:
        """Fetch report by ID with nested issues, clusters, recommendations, and assigned teams."""
        stmt = (
            select(Report)
            .options(
                selectinload(Report.report_issues)
                .selectinload(ReportIssue.cluster)
                .selectinload(IssueCluster.affected_product),
                selectinload(Report.report_issues)
                .selectinload(ReportIssue.recommendation)
                .selectinload(Recommendation.suggested_team),
            )
            .where(Report.id == report_id)
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_latest_report(self) -> Optional[Report]:
        """Fetch the most recent executive report."""
        stmt = (
            select(Report)
            .options(
                selectinload(Report.report_issues)
                .selectinload(ReportIssue.cluster)
                .selectinload(IssueCluster.affected_product),
                selectinload(Report.report_issues)
                .selectinload(ReportIssue.recommendation)
                .selectinload(Recommendation.suggested_team),
            )
            .order_by(desc(Report.created_at))
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_reports(self, page: int = 1, page_size: int = 20) -> Tuple[List[Report], int]:
        """List and paginate historical reports ordered by creation date descending."""
        stmt = select(Report).options(
            selectinload(Report.report_issues)
            .selectinload(ReportIssue.cluster)
            .selectinload(IssueCluster.affected_product),
            selectinload(Report.report_issues)
            .selectinload(ReportIssue.recommendation)
            .selectinload(Recommendation.suggested_team),
        )
        count_stmt = select(func.count(Report.id))

        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar() or 0

        offset = (page - 1) * page_size
        stmt = stmt.order_by(desc(Report.created_at)).offset(offset).limit(page_size)
        res = await self.session.execute(stmt)
        items = list(res.scalars().all())

        return items, total

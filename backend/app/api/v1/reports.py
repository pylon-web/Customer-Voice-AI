"""Weekly Executive Intelligence Report REST API endpoints."""

import math
from typing import Optional, List
from fastapi import APIRouter, Depends, status, Query, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.errors import NotFoundError
from app.services.report_service import ReportService
from app.repositories.report_repo import ReportRepository
from app.models.entities import Report
from app.models.schemas import (
    ReportRead,
    ReportIssueRead,
    ReportListResponse,
    ReportGenerateRequest,
    ReportFormatResponse,
    IssueClusterRead,
    RecommendationRead,
    TeamRead,
)

router = APIRouter(prefix="/reports", tags=["Executive Reports"])


def _to_report_read(report: Report) -> ReportRead:
    """Safely format Report ORM model to schema avoiding lazy load triggers."""
    issues = []
    if "report_issues" in getattr(report, "__dict__", {}) and report.__dict__["report_issues"]:
        for rep_issue in report.__dict__["report_issues"]:
            cluster_read = None
            if "cluster" in getattr(rep_issue, "__dict__", {}) and rep_issue.__dict__["cluster"]:
                c = rep_issue.__dict__["cluster"]
                cluster_read = IssueClusterRead(
                    id=c.id,
                    cluster_title=c.cluster_title,
                    description=c.description,
                    category=c.category,
                    affected_product_id=c.affected_product_id,
                    review_count=c.review_count,
                    negative_pct=c.negative_pct,
                    neutral_pct=c.neutral_pct,
                    positive_pct=c.positive_pct,
                    representative_quotes=c.representative_quotes or [],
                    status=c.status,
                    first_observed_at=c.first_observed_at,
                    latest_observed_at=c.latest_observed_at,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )

            rec_read = None
            if "recommendation" in getattr(rep_issue, "__dict__", {}) and rep_issue.__dict__["recommendation"]:
                r = rep_issue.__dict__["recommendation"]
                suggested_team = None
                if "suggested_team" in getattr(r, "__dict__", {}) and r.__dict__["suggested_team"]:
                    suggested_team = TeamRead.model_validate(r.__dict__["suggested_team"])
                rec_read = RecommendationRead(
                    id=r.id,
                    cluster_id=r.cluster_id,
                    suggested_team_id=r.suggested_team_id,
                    observed_evidence=r.observed_evidence,
                    investigation_hypothesis=r.investigation_hypothesis,
                    recommended_action=r.recommended_action,
                    confidence=r.confidence,
                    status=r.status,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                    suggested_team=suggested_team,
                )

            issues.append(
                ReportIssueRead(
                    id=rep_issue.id,
                    cluster_id=rep_issue.cluster_id,
                    issue_type=rep_issue.issue_type,
                    rank=rep_issue.rank,
                    cluster=cluster_read,
                    recommendation=rec_read,
                )
            )

    return ReportRead(
        id=report.id,
        title=report.title,
        report_period_start=report.report_period_start,
        report_period_end=report.report_period_end,
        total_reviews=report.total_reviews,
        negative_pct=report.negative_pct,
        emerging_issues_count=report.emerging_issues_count,
        improving_issues_count=report.improving_issues_count,
        executive_summary=report.executive_summary,
        geographic_insights=report.geographic_insights or {},
        generated_at=report.created_at,
        report_issues=issues,
    )


@router.post(
    "/generate",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Weekly Executive Intelligence Report",
    description="Synthesizes customer sentiment, velocity surges, resolving issues, and geographic anomalies into an executive brief.",
)
async def generate_report(
    payload: Optional[ReportGenerateRequest] = None,
    session: AsyncSession = Depends(get_async_session),
) -> ReportRead:
    """Generate a new weekly executive intelligence report."""
    service = ReportService(session)
    report = await service.generate_weekly_report(payload)
    return _to_report_read(report)


@router.get(
    "",
    response_model=ReportListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Executive Reports",
    description="Retrieve paginated list of historical intelligence reports ordered by generation date.",
)
async def list_reports(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_async_session),
) -> ReportListResponse:
    """List historical reports."""
    repo = ReportRepository(session)
    items, total = await repo.list_reports(page=page, page_size=page_size)
    pages = math.ceil(total / page_size) if total > 0 else 1

    return ReportListResponse(
        items=[_to_report_read(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{report_id}",
    response_model=ReportRead,
    status_code=status.HTTP_200_OK,
    summary="Get Report JSON",
    description="Fetch single executive intelligence report with highlighted issues and recommendations.",
)
async def get_report_by_id(
    report_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> ReportRead:
    """Fetch report by ID."""
    repo = ReportRepository(session)
    report = await repo.get_by_id(report_id)
    if not report:
        raise NotFoundError(resource="Report", identifier=report_id)
    return _to_report_read(report)


@router.get(
    "/{report_id}/markdown",
    response_model=ReportFormatResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Report Markdown Document",
    description="Export intelligence report in structured Markdown format.",
)
async def get_report_markdown(
    report_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> ReportFormatResponse:
    """Export report as Markdown."""
    repo = ReportRepository(session)
    report = await repo.get_by_id(report_id)
    if not report:
        raise NotFoundError(resource="Report", identifier=report_id)

    service = ReportService(session)
    md_content = service.render_markdown(report)
    return ReportFormatResponse(
        report_id=report.id,
        title=report.title,
        format="markdown",
        content=md_content,
    )


@router.get(
    "/{report_id}/html",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Printable Executive Report HTML",
    description="Renders a self-contained executive-ready HTML document suitable for browser preview or PDF conversion.",
)
async def get_report_html(
    report_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> HTMLResponse:
    """Export report as printable HTML."""
    repo = ReportRepository(session)
    report = await repo.get_by_id(report_id)
    if not report:
        raise NotFoundError(resource="Report", identifier=report_id)

    service = ReportService(session)
    html_content = service.render_html(report)
    return HTMLResponse(content=html_content, status_code=200)

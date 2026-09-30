"""Root cause investigation and Human-in-the-Loop decision REST API endpoints."""

import math
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.errors import NotFoundError
from app.services.investigation_service import InvestigationService
from app.repositories.recommendation_repo import RecommendationRepository
from app.models.schemas import (
    RecommendationRead,
    RecommendationListResponse,
    RecommendationDecisionRequest,
    TeamRead,
    ApprovalRead,
)

router = APIRouter(tags=["Root Cause & Investigation"])


class DecisionActionRequest(BaseModel):
    reviewer_name: str = "Lead Operations Analyst"
    reviewer_notes: Optional[str] = None
    modified_action: Optional[str] = None


def _to_recommendation_read(rec) -> RecommendationRead:
    """Safely format Recommendation ORM model to schema avoiding lazy-loading errors."""
    cluster_title = None
    if "cluster" in getattr(rec, "__dict__", {}) and rec.__dict__["cluster"] is not None:
        cluster_title = rec.__dict__["cluster"].cluster_title

    suggested_team = None
    if "suggested_team" in getattr(rec, "__dict__", {}) and rec.__dict__["suggested_team"] is not None:
        suggested_team = TeamRead.model_validate(rec.__dict__["suggested_team"])

    approvals = []
    if "approvals" in getattr(rec, "__dict__", {}) and rec.__dict__["approvals"] is not None:
        approvals = [ApprovalRead.model_validate(a) for a in rec.__dict__["approvals"]]

    return RecommendationRead(
        id=rec.id,
        cluster_id=rec.cluster_id,
        suggested_team_id=rec.suggested_team_id,
        observed_evidence=rec.observed_evidence,
        investigation_hypothesis=rec.investigation_hypothesis,
        recommended_action=rec.recommended_action,
        confidence=rec.confidence,
        status=rec.status,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
        cluster_title=cluster_title,
        suggested_team=suggested_team,
        approvals=approvals,
    )


# -----------------------------------------------------------------------------
# Static and Specific Routes (Must precede /{cluster_id} to avoid collision)
# -----------------------------------------------------------------------------

@router.get(
    "/recommendations",
    response_model=RecommendationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List & Filter Recommendations",
    description="Retrieve paginated list of operational recommendations with status and team filters.",
)
@router.get(
    "/investigations/recommendations",
    response_model=RecommendationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List & Filter Recommendations (Alias)",
    description="Retrieve paginated list of operational recommendations.",
)
async def list_recommendations(
    rec_status: Optional[str] = Query(None, alias="status", description="Filter by status (pending_approval, approved, rejected, modified)"),
    team_id: Optional[str] = Query(None, description="Filter by suggested enterprise team ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    session: AsyncSession = Depends(get_async_session),
) -> RecommendationListResponse:
    """List recommendations with filtering."""
    repo = RecommendationRepository(session)
    items, total = await repo.list_recommendations(
        status=rec_status,
        team_id=team_id,
        page=page,
        page_size=page_size,
    )
    pages = math.ceil(total / page_size) if total > 0 else 1

    return RecommendationListResponse(
        items=[_to_recommendation_read(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/investigations/audit",
    response_model=List[ApprovalRead],
    status_code=status.HTTP_200_OK,
    summary="Get Decision Audit History",
)
@router.get(
    "/recommendations/audit",
    response_model=List[ApprovalRead],
    status_code=status.HTTP_200_OK,
    summary="Get Decision Audit History",
)
async def get_audit_history(
    session: AsyncSession = Depends(get_async_session),
) -> List[ApprovalRead]:
    """Retrieve human-in-the-loop decision audit trail."""
    repo = RecommendationRepository(session)
    approvals = await repo.list_audit_history(limit=100)
    return [ApprovalRead.model_validate(a) for a in approvals]


@router.post(
    "/investigations/run",
    response_model=RecommendationRead,
    status_code=status.HTTP_200_OK,
    summary="Run investigation via query parameter",
)
async def run_investigation_by_query(
    cluster_id: str = Query(..., description="ID of the cluster to investigate"),
    session: AsyncSession = Depends(get_async_session),
) -> RecommendationRead:
    """Trigger investigation passing cluster_id as query param."""
    service = InvestigationService(session)
    rec = await service.investigate_cluster(cluster_id)
    return _to_recommendation_read(rec)


@router.post(
    "/investigations/recommendations/{recommendation_id}/approve",
    response_model=ApprovalRead,
    status_code=status.HTTP_200_OK,
    summary="Approve recommendation",
)
@router.post(
    "/recommendations/{recommendation_id}/approve",
    response_model=ApprovalRead,
    status_code=status.HTTP_200_OK,
    summary="Approve recommendation",
)
async def approve_recommendation(
    recommendation_id: str,
    payload: DecisionActionRequest,
    session: AsyncSession = Depends(get_async_session),
) -> ApprovalRead:
    """Approve operational recommendation."""
    service = InvestigationService(session)
    _, approval = await service.record_human_decision(
        recommendation_id=recommendation_id,
        reviewer_name=payload.reviewer_name,
        decision="approved",
        reviewer_notes=payload.reviewer_notes,
    )
    return ApprovalRead.model_validate(approval)


@router.post(
    "/investigations/recommendations/{recommendation_id}/reject",
    response_model=ApprovalRead,
    status_code=status.HTTP_200_OK,
    summary="Reject recommendation",
)
@router.post(
    "/recommendations/{recommendation_id}/reject",
    response_model=ApprovalRead,
    status_code=status.HTTP_200_OK,
    summary="Reject recommendation",
)
async def reject_recommendation(
    recommendation_id: str,
    payload: DecisionActionRequest,
    session: AsyncSession = Depends(get_async_session),
) -> ApprovalRead:
    """Reject operational recommendation."""
    service = InvestigationService(session)
    _, approval = await service.record_human_decision(
        recommendation_id=recommendation_id,
        reviewer_name=payload.reviewer_name,
        decision="rejected",
        reviewer_notes=payload.reviewer_notes,
    )
    return ApprovalRead.model_validate(approval)


@router.post(
    "/investigations/recommendations/{recommendation_id}/modify",
    response_model=ApprovalRead,
    status_code=status.HTTP_200_OK,
    summary="Modify and approve recommendation",
)
@router.post(
    "/recommendations/{recommendation_id}/modify",
    response_model=ApprovalRead,
    status_code=status.HTTP_200_OK,
    summary="Modify and approve recommendation",
)
async def modify_recommendation(
    recommendation_id: str,
    payload: DecisionActionRequest,
    session: AsyncSession = Depends(get_async_session),
) -> ApprovalRead:
    """Modify operational action and record decision."""
    service = InvestigationService(session)
    _, approval = await service.record_human_decision(
        recommendation_id=recommendation_id,
        reviewer_name=payload.reviewer_name,
        decision="modified",
        reviewer_notes=payload.reviewer_notes,
        modified_action=payload.modified_action,
    )
    return ApprovalRead.model_validate(approval)


@router.post(
    "/recommendations/{recommendation_id}/decision",
    response_model=RecommendationRead,
    status_code=status.HTTP_200_OK,
    summary="Record Human-in-the-Loop Decision",
    description="Approve, reject, or modify an operational recommendation with reviewer audit trail.",
)
async def record_recommendation_decision(
    recommendation_id: str,
    payload: RecommendationDecisionRequest,
    session: AsyncSession = Depends(get_async_session),
) -> RecommendationRead:
    """Record human approval/rejection/modification decision on a recommendation."""
    service = InvestigationService(session)
    rec, approval = await service.record_human_decision(
        recommendation_id=recommendation_id,
        reviewer_name=payload.reviewer_name,
        decision=payload.decision,
        reviewer_notes=payload.reviewer_notes,
        modified_action=payload.modified_action,
    )
    result = _to_recommendation_read(rec)
    if not result.approvals and approval:
        result.approvals = [
            ApprovalRead(
                id=approval.id,
                recommendation_id=approval.recommendation_id,
                reviewer_name=approval.reviewer_name,
                decision=approval.decision,
                reviewer_notes=approval.reviewer_notes,
                modified_action=approval.modified_action,
                decided_at=approval.decided_at,
            )
        ]
    return result


# -----------------------------------------------------------------------------
# Dynamic Cluster Routes (Evaluated after static routes)
# -----------------------------------------------------------------------------

@router.get(
    "/investigations/{cluster_id}",
    response_model=RecommendationRead,
    status_code=status.HTTP_200_OK,
    summary="Get Investigation Recommendation for Cluster",
    description="Retrieve the latest evidence-backed operational recommendation for a cluster.",
)
async def get_cluster_investigation(
    cluster_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> RecommendationRead:
    """Retrieve investigation recommendation for cluster."""
    repo = RecommendationRepository(session)
    rec = await repo.get_by_cluster_id(cluster_id)
    if not rec:
        raise NotFoundError(resource="Recommendation", identifier=cluster_id)
    return _to_recommendation_read(rec)


@router.post(
    "/investigations/{cluster_id}",
    response_model=RecommendationRead,
    status_code=status.HTTP_200_OK,
    summary="Trigger LangGraph Root Cause Investigation",
    description="Runs multi-agent state graph (Evidence Gatherer, Hypothesis Generator, Compliance Reflector) on a cluster.",
)
async def trigger_cluster_investigation(
    cluster_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> RecommendationRead:
    """Execute LangGraph root cause investigation for an issue cluster."""
    service = InvestigationService(session)
    rec = await service.investigate_cluster(cluster_id)
    return _to_recommendation_read(rec)

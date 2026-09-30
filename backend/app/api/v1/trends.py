"""Trend metrics and velocity anomaly REST API endpoints."""

import math
from typing import Optional, List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.errors import NotFoundError
from app.services.trend_service import TrendService
from app.repositories.trend_repo import TrendRepository
from app.repositories.cluster_repo import ClusterRepository
from app.models.schemas import (
    TrendMetricRead,
    TrendListResponse,
    TrendCalculateRequest,
    TrendCalculateResponse,
)

router = APIRouter(prefix="/trends", tags=["Trends & Velocity"])


def _to_trend_read(metric) -> TrendMetricRead:
    """Format TrendMetric entity to schema with cluster metadata."""
    cluster_title = None
    affected_product_id = None
    if "cluster" in getattr(metric, "__dict__", {}) and metric.__dict__["cluster"] is not None:
        c = metric.__dict__["cluster"]
        cluster_title = c.cluster_title
        affected_product_id = c.affected_product_id

    return TrendMetricRead(
        id=metric.id,
        cluster_id=metric.cluster_id,
        period_start=metric.period_start,
        period_end=metric.period_end,
        current_volume=metric.current_volume,
        previous_volume=metric.previous_volume,
        baseline_4wk_avg=metric.baseline_4wk_avg,
        wow_change_pct=metric.wow_change_pct,
        trend_direction=metric.trend_direction,
        anomaly_score=metric.anomaly_score,
        cluster_title=cluster_title,
        affected_product_id=affected_product_id,
    )


@router.post(
    "/calculate",
    response_model=TrendCalculateResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Cluster Trends & Velocity Anomalies",
    description="Calculates rolling 4-week baselines, week-over-week % velocity, z-scores, and trajectory classifications.",
)
async def calculate_trends(
    payload: Optional[TrendCalculateRequest] = None,
    session: AsyncSession = Depends(get_async_session),
) -> TrendCalculateResponse:
    """Trigger trend calculations and anomaly detection."""
    service = TrendService(session)
    return await service.calculate_trends(payload)


@router.get(
    "",
    response_model=TrendListResponse,
    status_code=status.HTTP_200_OK,
    summary="List & Filter Trend Metrics",
    description="Retrieve paginated list of trend metrics with filters by product, trajectory direction, and anomaly status.",
)
async def list_trends(
    product_id: Optional[str] = Query(None, description="Filter by affected product ID"),
    trend_direction: Optional[str] = Query(None, description="Filter by trend direction (emerging, stable, improving)"),
    is_anomaly: Optional[bool] = Query(None, description="Filter statistically anomalous spikes (z-score >= 2.0 or WoW >= 25%)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    session: AsyncSession = Depends(get_async_session),
) -> TrendListResponse:
    """List trend metrics with multi-dimensional filtering."""
    repo = TrendRepository(session)
    items, total = await repo.filter_trends(
        product_id=product_id,
        trend_direction=trend_direction,
        is_anomaly=is_anomaly,
        page=page,
        page_size=page_size,
    )
    pages = math.ceil(total / page_size) if total > 0 else 1

    return TrendListResponse(
        items=[_to_trend_read(m) for m in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{cluster_id}",
    response_model=List[TrendMetricRead],
    status_code=status.HTTP_200_OK,
    summary="Get Cluster Trend History",
    description="Retrieve chronological trend metric records for a specific issue cluster.",
)
async def get_cluster_trend_history(
    cluster_id: str,
    limit: int = Query(20, ge=1, le=100, description="Max history points"),
    session: AsyncSession = Depends(get_async_session),
) -> List[TrendMetricRead]:
    """Retrieve time-series trend history for a cluster."""
    cluster_repo = ClusterRepository(session)
    cluster = await cluster_repo.get_by_id(cluster_id)
    if not cluster:
        raise NotFoundError(resource="IssueCluster", identifier=cluster_id)

    trend_repo = TrendRepository(session)
    metrics = await trend_repo.get_by_cluster_id(cluster_id=cluster_id, limit=limit)
    return [_to_trend_read(m) for m in metrics]

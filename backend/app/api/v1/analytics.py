"""Analytics and catalog metadata endpoints for dashboard consumption."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel, ConfigDict

from app.core.database import get_async_session
from app.models.entities import Product, Source, Review, ReviewAnalysis, IssueCluster, TrendMetric, Recommendation
from app.models.schemas import ProductRead, SourceRead
from app.models.seeds import CAPITAL_ONE_PRODUCTS, INGESTION_SOURCES

router = APIRouter(prefix="/analytics", tags=["Analytics & Catalog"])


class SentimentCounts(BaseModel):
    positive: int = 0
    neutral: int = 0
    negative: int = 0


class ProductVolumeStat(BaseModel):
    product_id: str
    product_name: str
    count: int


class DashboardOverviewResponse(BaseModel):
    total_reviews: int
    avg_rating: float
    sentiment_counts: SentimentCounts
    total_clusters: int
    anomalies_count: int
    pending_recommendations_count: int
    top_products: List[ProductVolumeStat]
    recent_anomalies: List[Dict[str, Any]]


@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Dashboard Overview Metrics",
    description="Calculates high-level KPIs, sentiment breakdown, and emerging issue counts for the React dashboard.",
)
async def get_dashboard_overview(
    session: AsyncSession = Depends(get_async_session),
) -> DashboardOverviewResponse:
    """Retrieve pre-aggregated statistics for the executive dashboard overview."""
    # 1. Total Reviews & Average Rating
    total_reviews_res = await session.scalar(select(func.count(Review.id)))
    total_reviews = total_reviews_res or 0

    avg_rating_res = await session.scalar(select(func.avg(Review.rating)))
    avg_rating = round(float(avg_rating_res), 2) if avg_rating_res else 0.0

    # 2. Sentiment Counts
    pos_count = await session.scalar(
        select(func.count(ReviewAnalysis.id)).where(ReviewAnalysis.sentiment == "positive")
    ) or 0
    neu_count = await session.scalar(
        select(func.count(ReviewAnalysis.id)).where(ReviewAnalysis.sentiment == "neutral")
    ) or 0
    neg_count = await session.scalar(
        select(func.count(ReviewAnalysis.id)).where(ReviewAnalysis.sentiment == "negative")
    ) or 0

    # 3. Active Clusters Count
    total_clusters = await session.scalar(select(func.count(IssueCluster.id))) or 0

    # 4. Statistical Velocity Anomalies (z-score >= 2.0 or WoW >= 25%)
    anomalies_count = await session.scalar(
        select(func.count(TrendMetric.id)).where(TrendMetric.anomaly_score >= 2.0)
    ) or 0

    # 5. Pending Recommendations for HITL
    pending_recs = await session.scalar(
        select(func.count(Recommendation.id)).where(Recommendation.status == "pending_approval")
    ) or 0

    # 6. Top Products by review volume
    product_stmt = (
        select(Review.product_id, func.count(Review.id).label("cnt"))
        .group_by(Review.product_id)
        .order_by(desc("cnt"))
        .limit(6)
    )
    product_rows = (await session.execute(product_stmt)).all()
    product_name_map = {p["id"]: p["name"] for p in CAPITAL_ONE_PRODUCTS}
    top_products = [
        ProductVolumeStat(
            product_id=row[0],
            product_name=product_name_map.get(row[0], row[0]),
            count=row[1],
        )
        for row in product_rows
    ]

    # 7. Recent Anomalous Trend Metrics
    anomaly_stmt = (
        select(TrendMetric)
        .where(TrendMetric.anomaly_score >= 2.0)
        .order_by(desc(TrendMetric.anomaly_score))
        .limit(5)
    )
    anomaly_rows = (await session.execute(anomaly_stmt)).scalars().all()
    recent_anomalies = [
        {
            "id": a.id,
            "cluster_id": a.cluster_id,
            "current_volume": a.current_volume,
            "previous_volume": a.previous_volume,
            "wow_change_pct": a.wow_change_pct,
            "anomaly_score": a.anomaly_score,
            "trend_direction": a.trend_direction,
        }
        for a in anomaly_rows
    ]

    return DashboardOverviewResponse(
        total_reviews=total_reviews,
        avg_rating=avg_rating,
        sentiment_counts=SentimentCounts(
            positive=pos_count,
            neutral=neu_count,
            negative=neg_count,
        ),
        total_clusters=total_clusters,
        anomalies_count=anomalies_count,
        pending_recommendations_count=pending_recs,
        top_products=top_products,
        recent_anomalies=recent_anomalies,
    )


@router.get(
    "/products",
    response_model=List[ProductRead],
    status_code=status.HTTP_200_OK,
    summary="List Product Catalog",
    description="Retrieve list of all supported Capital One products.",
)
async def list_products(
    session: AsyncSession = Depends(get_async_session),
) -> List[ProductRead]:
    """Return all products from database with fallback to seed catalog."""
    result = await session.execute(select(Product).order_by(Product.family, Product.name))
    items = result.scalars().all()
    if items:
        return [ProductRead.model_validate(p) for p in items]
    return [ProductRead.model_validate(p) for p in CAPITAL_ONE_PRODUCTS]


@router.get(
    "/sources",
    response_model=List[SourceRead],
    status_code=status.HTTP_200_OK,
    summary="List Review Platforms / Sources",
    description="Retrieve list of all supported review ingestion platforms.",
)
async def list_sources(
    session: AsyncSession = Depends(get_async_session),
) -> List[SourceRead]:
    """Return all sources from database with fallback to seed catalog."""
    result = await session.execute(select(Source).order_by(Source.name))
    items = result.scalars().all()
    if items:
        return [SourceRead.model_validate(s) for s in items]
    return [SourceRead.model_validate(s) for s in INGESTION_SOURCES]

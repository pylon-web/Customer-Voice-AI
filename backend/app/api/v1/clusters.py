"""Issue cluster management, trigger, and inspection API endpoints."""

import math
from typing import Optional, List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.errors import NotFoundError
from app.services.clustering_service import ClusteringService
from app.repositories.cluster_repo import ClusterRepository
from app.models.schemas import (
    IssueClusterRead,
    IssueClusterDetailRead,
    IssueClusterListResponse,
    ClusterRunRequest,
    ClusterRunResponse,
    ClusterReviewItem,
    ReviewRead,
)

router = APIRouter(prefix="/clusters", tags=["Clusters"])


@router.post(
    "/run",
    response_model=ClusterRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger DBSCAN Unsupervised Clustering",
    description="Executes density-based spatial clustering across vector embeddings to discover issue clusters.",
)
async def trigger_clustering(
    payload: Optional[ClusterRunRequest] = None,
    session: AsyncSession = Depends(get_async_session),
) -> ClusterRunResponse:
    """Run DBSCAN semantic clustering over customer feedback."""
    service = ClusteringService(session)
    return await service.run_clustering(payload)


@router.get(
    "",
    response_model=IssueClusterListResponse,
    status_code=status.HTTP_200_OK,
    summary="List & Filter Issue Clusters",
    description="Retrieve paginated list of issue clusters with product, category, and status filters.",
)
async def list_clusters(
    product_id: Optional[str] = Query(None, description="Filter by affected product ID"),
    category: Optional[str] = Query(None, description="Filter by issue category"),
    cluster_status: Optional[str] = Query(None, alias="status", description="Filter by cluster status (active, resolved, monitoring)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    session: AsyncSession = Depends(get_async_session),
) -> IssueClusterListResponse:
    """List issue clusters with filtering."""
    repo = ClusterRepository(session)
    items, total = await repo.filter_clusters(
        product_id=product_id,
        category=category,
        status=cluster_status,
        page=page,
        page_size=page_size,
    )
    pages = math.ceil(total / page_size) if total > 0 else 1

    return IssueClusterListResponse(
        items=[IssueClusterRead.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{cluster_id}",
    response_model=IssueClusterDetailRead,
    status_code=status.HTTP_200_OK,
    summary="Get Issue Cluster Details",
    description="Retrieve cluster metadata and top member reviews ordered by similarity to centroid.",
)
async def get_cluster_by_id(
    cluster_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> IssueClusterDetailRead:
    """Fetch single cluster with review members."""
    repo = ClusterRepository(session)
    cluster = await repo.get_by_id(cluster_id)
    if not cluster:
        raise NotFoundError(resource="IssueCluster", identifier=cluster_id)

    # Format review associations
    review_items = [
        ClusterReviewItem(
            review=ReviewRead.from_orm_model(link.review),
            similarity_score=link.similarity_score,
            assigned_at=link.assigned_at,
        )
        for link in cluster.cluster_reviews
    ]

    detail = IssueClusterDetailRead(
        id=cluster.id,
        cluster_title=cluster.cluster_title,
        description=cluster.description,
        category=cluster.category,
        affected_product_id=cluster.affected_product_id,
        review_count=cluster.review_count,
        negative_pct=cluster.negative_pct,
        neutral_pct=cluster.neutral_pct,
        positive_pct=cluster.positive_pct,
        representative_quotes=cluster.representative_quotes,
        status=cluster.status,
        first_observed_at=cluster.first_observed_at,
        latest_observed_at=cluster.latest_observed_at,
        created_at=cluster.created_at,
        updated_at=cluster.updated_at,
        reviews=review_items,
        product_name=cluster.affected_product.name if cluster.affected_product else cluster.affected_product_id,
    )
    return detail


@router.get(
    "/{cluster_id}/reviews",
    response_model=List[ClusterReviewItem],
    status_code=status.HTTP_200_OK,
    summary="Get Cluster Member Reviews",
    description="Paginated list of reviews linked to a cluster, sorted by cosine proximity to centroid.",
)
async def get_cluster_reviews(
    cluster_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
) -> List[ClusterReviewItem]:
    """Retrieve review drilldown for a cluster."""
    repo = ClusterRepository(session)
    cluster = await repo.get_by_id(cluster_id)
    if not cluster:
        raise NotFoundError(resource="IssueCluster", identifier=cluster_id)

    offset = (page - 1) * page_size
    links = await repo.get_cluster_reviews(cluster_id=cluster_id, limit=page_size, offset=offset)

    return [
        ClusterReviewItem(
            review=ReviewRead.from_orm_model(link.review),
            similarity_score=link.similarity_score,
            assigned_at=link.assigned_at,
        )
        for link in links
    ]

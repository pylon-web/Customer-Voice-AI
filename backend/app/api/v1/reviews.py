"""Review ingestion, search, and retrieval API endpoints."""

import math
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.errors import NotFoundError, ValidationError
from app.services.ingestion_service import IngestionService
from app.services.analysis_service import AnalysisService
from app.services.embedding_service import EmbeddingService
from app.repositories.review_repo import ReviewRepository
from app.repositories.analysis_repo import AnalysisRepository
from app.repositories.embedding_repo import EmbeddingRepository
from app.models.schemas import (
    ReviewCreate,
    ReviewRead,
    ReviewBatchCreate,
    ReviewBatchResponse,
    ReviewListResponse,
    ReviewFilterParams,
    ReviewAnalysisRead,
    ReviewEmbeddingRead,
    SemanticSearchRequest,
    SemanticSearchResponse,
)

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post(
    "",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Single Customer Review",
    description="Accepts customer review feedback, validates inputs, normalizes product/source, and persists to store.",
)
async def ingest_review(
    payload: ReviewCreate,
    session: AsyncSession = Depends(get_async_session),
) -> ReviewRead:
    """Ingest a single customer review."""
    service = IngestionService(session)
    try:
        review = await service.ingest_single(payload)
        return ReviewRead.from_orm_model(review)
    except ValueError as e:
        raise ValidationError(str(e))


@router.post(
    "/batch",
    response_model=ReviewBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest Batch of Reviews",
    description="Ingest up to 1,000 reviews in a single batch request.",
)
async def ingest_reviews_batch(
    payload: ReviewBatchCreate,
    session: AsyncSession = Depends(get_async_session),
) -> ReviewBatchResponse:
    """Ingest multiple reviews in a single batch."""
    service = IngestionService(session)
    count, ids = await service.ingest_batch(payload)
    return ReviewBatchResponse(
        total_submitted=len(payload.reviews),
        total_accepted=count,
        review_ids=ids,
        status="queued",
    )


@router.post(
    "/upload",
    response_model=ReviewBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload Review File (JSON or CSV)",
    description="Bulk ingest customer reviews by uploading a JSON or CSV file.",
)
async def upload_review_file(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
) -> ReviewBatchResponse:
    """Bulk ingest reviews by uploading a CSV or JSON file."""
    if not file.filename:
        raise ValidationError("Uploaded file must have a filename.")

    content = await file.read()
    service = IngestionService(session)
    count, ids = await service.ingest_file(content, file.filename)

    return ReviewBatchResponse(
        total_submitted=count,
        total_accepted=count,
        review_ids=ids,
        status="queued",
    )


@router.get(
    "",
    response_model=ReviewListResponse,
    status_code=status.HTTP_200_OK,
    summary="List & Filter Reviews",
    description="Retrieve paginated customer reviews with multi-dimensional filtering by product, rating, sentiment, and location.",
)
async def list_reviews(
    product_id: Optional[str] = Query(None, description="Filter by product ID (e.g. venture_x, banking_360_checking)"),
    source_id: Optional[str] = Query(None, description="Filter by platform ID (e.g. apple_app_store, google_play_store)"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment (positive, neutral, negative)"),
    category: Optional[str] = Query(None, description="Filter by AI-extracted issue category"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="Filter by star rating (1-5)"),
    location: Optional[str] = Query(None, description="Filter by customer location string"),
    start_date: Optional[datetime] = Query(None, description="Filter reviews created on or after this ISO timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter reviews created on or before this ISO timestamp"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    session: AsyncSession = Depends(get_async_session),
) -> ReviewListResponse:
    """Search and filter reviews with pagination."""
    repo = ReviewRepository(session)
    params = ReviewFilterParams(
        product_id=product_id,
        source_id=source_id,
        sentiment=sentiment,
        category=category,
        rating=rating,
        location=location,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    items, total = await repo.filter_reviews(params)
    pages = math.ceil(total / page_size) if total > 0 else 1

    return ReviewListResponse(
        items=[ReviewRead.from_orm_model(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post(
    "/search-semantic",
    response_model=SemanticSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic Review Similarity Search",
    description="Search customer reviews using 1536-dimensional vector embeddings and cosine similarity.",
)
async def search_reviews_semantic(
    payload: SemanticSearchRequest,
    session: AsyncSession = Depends(get_async_session),
) -> SemanticSearchResponse:
    """Semantic vector search over customer reviews."""
    service = EmbeddingService(session)
    return await service.search_reviews_semantic(payload)


@router.get(
    "/{review_id}",
    response_model=ReviewRead,
    status_code=status.HTTP_200_OK,
    summary="Get Review Details by ID",
    description="Fetch a single customer review by ID with AI analysis metadata.",
)
async def get_review_by_id(
    review_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> ReviewRead:
    """Fetch review by ID."""
    repo = ReviewRepository(session)
    review = await repo.get_by_id(review_id)
    if not review:
        raise NotFoundError(resource="Review", identifier=review_id)
    return ReviewRead.from_orm_model(review)


@router.post(
    "/{review_id}/analyze",
    response_model=ReviewAnalysisRead,
    status_code=status.HTTP_200_OK,
    summary="Trigger AI Analysis on Review",
    description="Runs structured AI analysis on an ingested review and saves results.",
)
async def trigger_review_analysis(
    review_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> ReviewAnalysisRead:
    """Trigger AI analysis on a specific review."""
    service = AnalysisService(session)
    analysis = await service.analyze_review(review_id)
    return ReviewAnalysisRead.model_validate(analysis)


@router.get(
    "/{review_id}/analysis",
    response_model=ReviewAnalysisRead,
    status_code=status.HTTP_200_OK,
    summary="Get Review Analysis",
    description="Fetch AI analysis results for a specific review.",
)
async def get_review_analysis(
    review_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> ReviewAnalysisRead:
    """Retrieve AI analysis for a review."""
    repo = AnalysisRepository(session)
    analysis = await repo.get_by_review_id(review_id)
    if not analysis:
        raise NotFoundError(resource="ReviewAnalysis", identifier=review_id)
    return ReviewAnalysisRead.model_validate(analysis)


@router.post(
    "/{review_id}/embed",
    response_model=ReviewEmbeddingRead,
    status_code=status.HTTP_200_OK,
    summary="Generate Vector Embedding for Review",
    description="Generate or refresh 1536-dimensional vector embedding for a review.",
)
async def generate_review_embedding(
    review_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> ReviewEmbeddingRead:
    """Generate vector embedding for a review."""
    service = EmbeddingService(session)
    embedding = await service.generate_and_store_embedding(review_id)
    return ReviewEmbeddingRead.model_validate(embedding)


@router.get(
    "/{review_id}/embedding",
    response_model=ReviewEmbeddingRead,
    status_code=status.HTTP_200_OK,
    summary="Get Review Embedding Metadata",
    description="Fetch vector embedding metadata for a review.",
)
async def get_review_embedding(
    review_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> ReviewEmbeddingRead:
    """Retrieve vector embedding metadata for a review."""
    repo = EmbeddingRepository(session)
    embedding = await repo.get_by_review_id(review_id)
    if not embedding:
        raise NotFoundError(resource="ReviewEmbedding", identifier=review_id)
    return ReviewEmbeddingRead.model_validate(embedding)

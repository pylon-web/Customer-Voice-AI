"""Review repository for database operations on customer feedback."""

from typing import List, Optional, Tuple
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Review, ReviewAnalysis, ReviewEmbedding
from app.models.schemas import ReviewFilterParams


class ReviewRepository:
    """Data access repository for reviews, analyses, and embeddings."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, review: Review) -> Review:
        """Persist a new customer review entity."""
        self.session.add(review)
        await self.session.flush()
        return review

    async def get_by_id(self, review_id: str) -> Optional[Review]:
        """Fetch single review by ID with analysis and product loaded."""
        stmt = (
            select(Review)
            .options(
                selectinload(Review.analysis),
                selectinload(Review.embedding),
                selectinload(Review.product),
                selectinload(Review.source),
            )
            .where(Review.id == review_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def filter_reviews(
        self, params: ReviewFilterParams
    ) -> Tuple[List[Review], int]:
        """Query reviews with flexible filtering, pagination, and total count."""
        stmt = select(Review).options(
            selectinload(Review.analysis),
            selectinload(Review.product),
            selectinload(Review.source),
        )

        # Apply filters
        if params.product_id:
            stmt = stmt.where(Review.product_id == params.product_id)
        if params.source_id:
            stmt = stmt.where(Review.source_id == params.source_id)
        if params.rating:
            stmt = stmt.where(Review.rating == params.rating)
        if params.location:
            stmt = stmt.where(Review.location.ilike(f"%{params.location}%"))
        if params.start_date:
            stmt = stmt.where(Review.created_at >= params.start_date)
        if params.end_date:
            stmt = stmt.where(Review.created_at <= params.end_date)

        if params.sentiment or params.category:
            stmt = stmt.join(Review.analysis)
            if params.sentiment:
                stmt = stmt.where(ReviewAnalysis.sentiment == params.sentiment)
            if params.category:
                stmt = stmt.where(ReviewAnalysis.category == params.category)

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0

        # Apply order and pagination
        stmt = (
            stmt.order_by(desc(Review.created_at))
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )

        result = await self.session.execute(stmt)
        reviews = list(result.scalars().all())
        return reviews, total

    async def save_analysis(self, analysis: ReviewAnalysis) -> ReviewAnalysis:
        """Persist or update AI analysis output."""
        self.session.add(analysis)
        await self.session.flush()
        return analysis

    async def save_embedding(self, embedding: ReviewEmbedding) -> ReviewEmbedding:
        """Persist 1536-dimensional vector embedding."""
        self.session.add(embedding)
        await self.session.flush()
        return embedding

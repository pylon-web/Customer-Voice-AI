"""Repository for managing review analysis persistence and queries."""

from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import ReviewAnalysis, Review


class AnalysisRepository:
    """Data access repository for structured review analyses."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, analysis: ReviewAnalysis) -> ReviewAnalysis:
        """Persist a new ReviewAnalysis entity."""
        self.session.add(analysis)
        await self.session.flush()
        return analysis

    async def get_by_review_id(self, review_id: str) -> Optional[ReviewAnalysis]:
        """Fetch analysis by review ID with linked review loaded."""
        stmt = (
            select(ReviewAnalysis)
            .options(selectinload(ReviewAnalysis.review))
            .where(ReviewAnalysis.review_id == review_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, analysis_id: str) -> Optional[ReviewAnalysis]:
        """Fetch analysis by primary key."""
        stmt = select(ReviewAnalysis).where(ReviewAnalysis.id == analysis_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def upsert(self, analysis: ReviewAnalysis) -> ReviewAnalysis:
        """Insert or update existing review analysis."""
        existing = await self.get_by_review_id(analysis.review_id)
        if existing:
            existing.sentiment = analysis.sentiment
            existing.sentiment_score = analysis.sentiment_score
            existing.category = analysis.category
            existing.issue = analysis.issue
            existing.severity = analysis.severity
            existing.customer_intent = analysis.customer_intent
            existing.entities = analysis.entities
            existing.confidence = analysis.confidence
            existing.analyzed_at = analysis.analyzed_at
            await self.session.flush()
            return existing

        return await self.create(analysis)

    async def list_recent(self, limit: int = 50) -> List[ReviewAnalysis]:
        """Fetch recent review analyses."""
        stmt = (
            select(ReviewAnalysis)
            .options(selectinload(ReviewAnalysis.review))
            .order_by(desc(ReviewAnalysis.analyzed_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

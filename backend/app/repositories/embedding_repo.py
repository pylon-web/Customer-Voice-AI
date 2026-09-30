"""Repository for managing review vector embeddings and pgvector semantic similarity search."""

import json
import math
from typing import List, Optional, Tuple
import numpy as np

from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import ReviewEmbedding, Review


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class EmbeddingRepository:
    """Data access repository for 1536-dimensional review embeddings and vector similarity queries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, embedding: ReviewEmbedding) -> ReviewEmbedding:
        """Persist a new ReviewEmbedding entity."""
        self.session.add(embedding)
        await self.session.flush()
        return embedding

    async def get_by_review_id(self, review_id: str) -> Optional[ReviewEmbedding]:
        """Fetch embedding for a specific review."""
        stmt = (
            select(ReviewEmbedding)
            .options(selectinload(ReviewEmbedding.review))
            .where(ReviewEmbedding.review_id == review_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def upsert(self, embedding: ReviewEmbedding) -> ReviewEmbedding:
        """Insert or update existing review embedding."""
        existing = await self.get_by_review_id(embedding.review_id)
        if existing:
            existing.embedding = embedding.embedding
            existing.model_name = embedding.model_name
            existing.dimension = embedding.dimension
            await self.session.flush()
            return existing

        return await self.create(embedding)

    async def search_similar(
        self,
        query_vector: List[float],
        limit: int = 10,
        product_id: Optional[str] = None,
        min_similarity: float = 0.0,
    ) -> List[Tuple[Review, float]]:
        """Perform nearest-neighbor vector search returning matched reviews and similarity scores.

        Uses native pgvector cosine distance on PostgreSQL, and in-memory vector dot product
        on SQLite for hermetic test execution.
        """
        bind = self.session.bind
        dialect_name = bind.dialect.name if bind else "sqlite"

        if dialect_name == "postgresql":
            try:
                # Use native pgvector cosine distance: ReviewEmbedding.embedding.cosine_distance(query_vector)
                # similarity = 1.0 - distance
                stmt = (
                    select(
                        Review,
                        (1.0 - ReviewEmbedding.embedding.cosine_distance(query_vector)).label("similarity"),
                    )
                    .join(ReviewEmbedding, Review.id == ReviewEmbedding.review_id)
                    .options(
                        selectinload(Review.analysis),
                        selectinload(Review.product),
                        selectinload(Review.source),
                    )
                )

                if product_id:
                    stmt = stmt.where(Review.product_id == product_id)

                stmt = stmt.order_by(ReviewEmbedding.embedding.cosine_distance(query_vector).asc()).limit(limit)

                result = await self.session.execute(stmt)
                rows = result.all()

                matches = []
                for review, sim in rows:
                    sim_float = float(sim)
                    if sim_float >= min_similarity:
                        matches.append((review, sim_float))
                return matches

            except Exception:
                # Fallback to in-memory calculation if pgvector operator fails
                pass

        # In-memory cosine similarity fallback (SQLite test mode)
        stmt = (
            select(ReviewEmbedding)
            .join(Review, ReviewEmbedding.review_id == Review.id)
            .options(
                selectinload(ReviewEmbedding.review).selectinload(Review.analysis),
                selectinload(ReviewEmbedding.review).selectinload(Review.product),
                selectinload(ReviewEmbedding.review).selectinload(Review.source),
            )
        )
        if product_id:
            stmt = stmt.where(Review.product_id == product_id)

        result = await self.session.execute(stmt)
        candidates = result.scalars().all()

        scored: List[Tuple[Review, float]] = []
        for cand in candidates:
            cand_vec = cand.embedding
            if isinstance(cand_vec, str):
                try:
                    cand_vec = json.loads(cand_vec)
                except Exception:
                    continue

            if not cand_vec:
                continue

            sim = cosine_similarity(query_vector, cand_vec)
            if sim >= min_similarity:
                scored.append((cand.review, round(sim, 4)))

        # Sort descending by similarity
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

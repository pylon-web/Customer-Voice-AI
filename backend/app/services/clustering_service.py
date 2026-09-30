"""Unsupervised semantic clustering engine using DBSCAN over 1536-dim vector embeddings."""

from collections import Counter
from datetime import datetime, timezone, timedelta
import json
from typing import List, Dict, Any, Optional, Tuple
import uuid
import numpy as np
from sklearn.cluster import DBSCAN
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.entities import Review, ReviewEmbedding, IssueCluster, ClusterReview
from app.models.schemas import ClusterRunRequest, ClusterRunResponse
from app.repositories.cluster_repo import ClusterRepository
from app.kafka.producer import KafkaProducerService, get_kafka_producer
from app.kafka.events import IssueDetectedEvent, IssueDetectedPayload

logger = get_logger("cva.service.clustering")


class ClusteringService:
    """Orchestrates unsupervised grouping of reviews into actionable issue clusters."""

    def __init__(
        self,
        session: AsyncSession,
        kafka_producer: Optional[KafkaProducerService] = None,
    ):
        self.session = session
        self.cluster_repo = ClusterRepository(session)
        self.kafka_producer = kafka_producer or get_kafka_producer()

    def _synthesize_title(self, product_id: str, dominant_category: str, sample_texts: List[str]) -> str:
        """Derive clear, human-readable cluster title based on category and textual keywords."""
        combined = " ".join(sample_texts).lower()

        if any(w in combined for w in ["face id", "faceid", "biometric", "v6.14", "login crash"]):
            return "iOS Face ID Biometric Authentication Failure & Startup Crash"
        elif any(w in combined for w in ["lounge", "crowd", "waitlist", "line", "capacity"]):
            return "Capital One Lounge Peak Hour Crowding & Waitlist Friction"
        elif any(w in combined for w in ["wifi", "wi-fi", "internet", "disconnect"]):
            return "Café Wi-Fi Network Disruptions & Periodic Disconnects"
        elif any(w in combined for w in ["virtual card", "eno", "decline", "bot"]):
            return "Eno Virtual Card Number Generation & Merchant Acceptance Declines"
        elif any(w in combined for w in ["extension", "shopping", "freeze", "coupon", "checkout"]):
            return "Capital One Shopping Browser Extension Freezes at Checkout"
        elif any(w in combined for w in ["overdraft", "fee", "penalty", "charge"]):
            return "Checking Account Overdraft Fee Disclosure & Balance Friction"

        prod_title = product_id.replace("_", " ").title()
        return f"{prod_title} - {dominant_category} Issue Cluster"

    async def run_clustering(self, request: Optional[ClusterRunRequest] = None) -> ClusterRunResponse:
        """Execute DBSCAN density clustering across unclustered or filtered review embeddings."""
        req = request or ClusterRunRequest()

        # 1. Fetch candidate reviews with embeddings
        stmt = (
            select(Review, ReviewEmbedding)
            .join(ReviewEmbedding, Review.id == ReviewEmbedding.review_id)
            .options(
                selectinload(Review.analysis),
                selectinload(Review.product),
            )
        )

        if req.product_id:
            stmt = stmt.where(Review.product_id == req.product_id)

        if req.lookback_days:
            since = datetime.now(timezone.utc) - timedelta(days=req.lookback_days)
            stmt = stmt.where(Review.created_at >= since)

        result = await self.session.execute(stmt)
        candidates = result.all()

        total_analyzed = len(candidates)
        if total_analyzed < req.min_samples:
            logger.info("Insufficient reviews with embeddings for clustering", count=total_analyzed)
            return ClusterRunResponse(
                clusters_formed=0,
                total_reviews_analyzed=total_analyzed,
                clustered_reviews_count=0,
                noise_reviews_count=total_analyzed,
                cluster_ids=[],
            )

        reviews_list: List[Review] = []
        vectors: List[np.ndarray] = []

        for rev, emb in candidates:
            vec_data = emb.embedding
            if isinstance(vec_data, str):
                try:
                    vec_data = json.loads(vec_data)
                except Exception:
                    continue

            if not vec_data or len(vec_data) != 1536:
                continue

            arr = np.array(vec_data, dtype=np.float32)
            norm = np.linalg.norm(arr)
            if norm > 0:
                arr = arr / norm

            reviews_list.append(rev)
            vectors.append(arr)

        if len(vectors) < req.min_samples:
            return ClusterRunResponse(
                clusters_formed=0,
                total_reviews_analyzed=total_analyzed,
                clustered_reviews_count=0,
                noise_reviews_count=total_analyzed,
                cluster_ids=[],
            )

        X = np.stack(vectors)

        # 2. Run DBSCAN clustering with cosine distance metric
        db = DBSCAN(eps=req.eps, min_samples=req.min_samples, metric="cosine")
        labels = db.fit_predict(X)

        unique_labels = set(labels)
        unique_labels.discard(-1)  # Remove noise label

        created_cluster_ids: List[str] = []
        clustered_count = 0

        # 3. Synthesize metadata for each discovered cluster
        for label in sorted(unique_labels):
            indices = np.where(labels == label)[0]
            cluster_size = len(indices)
            clustered_count += cluster_size

            cluster_revs = [reviews_list[i] for i in indices]
            cluster_vecs = X[indices]

            # Compute centroid vector
            mean_vec = np.mean(cluster_vecs, axis=0)
            centroid_norm = np.linalg.norm(mean_vec)
            centroid = (mean_vec / centroid_norm).tolist() if centroid_norm > 0 else mean_vec.tolist()

            # Compute similarity of each review to centroid
            sims = np.dot(cluster_vecs, np.array(centroid, dtype=np.float32))

            # Pair reviews with similarities and sort descending
            paired = sorted(zip(cluster_revs, sims), key=lambda x: x[1], reverse=True)
            sorted_revs = [p[0] for p in paired]
            sorted_sims = [p[1] for p in paired]

            # Determine dominant product and category
            product_counts = Counter(r.product_id for r in cluster_revs)
            dominant_product = product_counts.most_common(1)[0][0]

            categories = [r.analysis.category for r in cluster_revs if r.analysis and r.analysis.category]
            dominant_category = Counter(categories).most_common(1)[0][0] if categories else "General Customer Experience"

            # Sentiment distribution
            neg_count = sum(1 for r in cluster_revs if r.rating <= 2 or (r.analysis and r.analysis.sentiment == "negative"))
            neu_count = sum(1 for r in cluster_revs if r.rating == 3 or (r.analysis and r.analysis.sentiment == "neutral"))
            pos_count = sum(1 for r in cluster_revs if r.rating >= 4 or (r.analysis and r.analysis.sentiment == "positive"))

            neg_pct = round((neg_count / cluster_size) * 100, 1)
            neu_pct = round((neu_count / cluster_size) * 100, 1)
            pos_pct = round((pos_count / cluster_size) * 100, 1)

            # Dates
            def _to_utc(dt: datetime) -> datetime:
                return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

            first_obs = min(_to_utc(r.created_at) for r in cluster_revs)
            latest_obs = max(_to_utc(r.created_at) for r in cluster_revs)

            # Representative quotes (nearest to centroid)
            quotes = [r.review_text.strip() for r in sorted_revs[:4] if r.review_text]

            # Synthesize title and description
            title = self._synthesize_title(dominant_product, dominant_category, quotes)
            description = (
                f"Discovered semantic cluster comprising {cluster_size} customer reviews "
                f"for {dominant_product.replace('_', ' ').title()}. Category: {dominant_category}. "
                f"Sentiment profile: {neg_pct}% negative, {pos_pct}% positive."
            )

            # Persist IssueCluster
            cluster = IssueCluster(
                id=str(uuid.uuid4()),
                cluster_title=title,
                description=description,
                category=dominant_category,
                affected_product_id=dominant_product,
                review_count=cluster_size,
                negative_pct=neg_pct,
                neutral_pct=neu_pct,
                positive_pct=pos_pct,
                representative_quotes=quotes,
                first_observed_at=first_obs,
                latest_observed_at=latest_obs,
                centroid_embedding=centroid,
                status="active",
            )
            saved_cluster = await self.cluster_repo.create_cluster(cluster)
            created_cluster_ids.append(saved_cluster.id)

            # Link reviews in cluster_reviews
            for rev, sim in zip(sorted_revs, sorted_sims):
                await self.cluster_repo.link_review(
                    cluster_id=saved_cluster.id,
                    review_id=rev.id,
                    similarity_score=round(float(sim), 4),
                )

            # Publish issue.detected event if negative issue surge detected
            if neg_pct >= 50.0 or cluster_size >= 5:
                try:
                    event = IssueDetectedEvent(
                        data=IssueDetectedPayload(
                            cluster_id=saved_cluster.id,
                            cluster_title=saved_cluster.cluster_title,
                            affected_product_id=saved_cluster.affected_product_id,
                            wow_change_pct=100.0,
                            trend_direction="emerging",
                            detected_at=datetime.now(timezone.utc),
                        )
                    )
                    await self.kafka_producer.publish(
                        topic=settings.KAFKA_TOPIC_ISSUE_DETECTED,
                        event=event,
                        key=saved_cluster.affected_product_id,
                    )
                except Exception as k_err:
                    logger.warning(f"Failed to publish issue.detected event: {k_err}")

        noise_count = total_analyzed - clustered_count
        await self.session.commit()

        logger.info(
            "Completed DBSCAN semantic clustering",
            clusters_formed=len(created_cluster_ids),
            total_analyzed=total_analyzed,
            clustered=clustered_count,
            noise=noise_count,
        )

        return ClusterRunResponse(
            clusters_formed=len(created_cluster_ids),
            total_reviews_analyzed=total_analyzed,
            clustered_reviews_count=clustered_count,
            noise_reviews_count=noise_count,
            cluster_ids=created_cluster_ids,
        )

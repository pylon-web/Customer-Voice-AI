"""Review Ingestion Service handling validation, normalization, batch processing, and file uploads."""

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import List, Tuple, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.entities import Review, Product, Source
from app.models.schemas import ReviewCreate, ReviewBatchCreate
from app.repositories.review_repo import ReviewRepository
from app.core.errors import ValidationError
from app.core.logging import get_logger
from app.core.config import settings
from app.kafka.producer import KafkaProducerService, get_kafka_producer
from app.kafka.events import ReviewCreatedEvent, ReviewCreatedPayload

logger = get_logger("cva.ingestion_service")

# Normalization mapping for generic or short names to canonical Capital One product IDs
PRODUCT_ALIAS_MAP: Dict[str, str] = {
    "mobile_banking": "c1_mobile_ios",
    "mobile_app": "c1_mobile_ios",
    "ios_app": "c1_mobile_ios",
    "android_app": "c1_mobile_android",
    "credit_cards": "venture_x",
    "venture": "venture",
    "venture_x": "venture_x",
    "savor": "savor_one",
    "savor_one": "savor_one",
    "quicksilver": "quicksilver",
    "checking": "banking_360_checking",
    "savings": "banking_360_savings",
    "360_checking": "banking_360_checking",
    "360_savings": "banking_360_savings",
    "auto": "auto_navigator",
    "auto_navigator": "auto_navigator",
    "shopping": "c1_shopping_extension",
    "shopping_extension": "c1_shopping_extension",
    "eno": "eno_virtual_assistant",
    "creditwise": "creditwise",
    "cafe": "c1_cafe",
    "branch": "c1_branch_network",
    "atm": "c1_atm_network",
}

SOURCE_ALIAS_MAP: Dict[str, str] = {
    "google": "google_places",
    "google_reviews": "google_places",
    "places": "google_places",
    "app_store": "apple_app_store",
    "ios_store": "apple_app_store",
    "play_store": "google_play_store",
    "android_store": "google_play_store",
    "chrome": "chrome_web_store",
    "extension_store": "chrome_web_store",
    "trustpilot": "trustpilot",
    "internal": "trustpilot",
    "synthetic": "synthetic_stream",
}


class IngestionService:
    """Service orchestrating customer review ingestion, normalization, and persistence."""

    def __init__(self, session: AsyncSession, kafka_producer: Optional[KafkaProducerService] = None):
        self.session = session
        self.review_repo = ReviewRepository(session)
        self.kafka_producer = kafka_producer or get_kafka_producer()

    def _normalize_product_id(self, raw_product: str) -> str:
        """Map generic product references to canonical taxonomy IDs."""
        cleaned = raw_product.strip().lower().replace(" ", "_").replace("-", "_")
        return PRODUCT_ALIAS_MAP.get(cleaned, cleaned)

    def _normalize_source_id(self, raw_source: str) -> str:
        """Map generic source references to canonical platform IDs."""
        cleaned = raw_source.strip().lower().replace(" ", "_").replace("-", "_")
        return SOURCE_ALIAS_MAP.get(cleaned, cleaned)

    async def _ensure_product_and_source_exist(self, product_id: str, source_id: str) -> None:
        """Ensure foreign keys exist; dynamically register if an unknown product/source is passed."""
        prod_res = await self.session.execute(select(Product).where(Product.id == product_id))
        if not prod_res.scalars().first():
            new_prod = Product(
                id=product_id,
                name=product_id.replace("_", " ").title(),
                family="General Services",
                description="Dynamically registered product from incoming review stream.",
            )
            self.session.add(new_prod)

        src_res = await self.session.execute(select(Source).where(Source.id == source_id))
        if not src_res.scalars().first():
            new_src = Source(
                id=source_id,
                name=source_id.replace("_", " ").title(),
                platform_type="external_platform",
                description="Dynamically registered source platform.",
            )
            self.session.add(new_src)

    async def ingest_single(self, dto: ReviewCreate) -> Review:
        """Ingest, validate, normalize, and persist a single review."""
        review_text = dto.get_effective_text()
        raw_product = dto.get_effective_product_id()
        raw_source = dto.get_effective_source_id()

        product_id = self._normalize_product_id(raw_product)
        source_id = self._normalize_source_id(raw_source)

        await self._ensure_product_and_source_exist(product_id, source_id)

        review_id = dto.id or f"c1-rev-{uuid.uuid4().hex[:10]}"
        created_at = dto.created_at or datetime.now(timezone.utc)

        review = Review(
            id=review_id,
            source_id=source_id,
            product_id=product_id,
            location=dto.location,
            rating=dto.rating,
            review_title=dto.review_title,
            review_text=review_text,
            metadata_json=dto.metadata_json or {},
            created_at=created_at,
            ingested_at=datetime.now(timezone.utc),
        )

        persisted = await self.review_repo.create(review)
        logger.info(
            f"Ingested review {persisted.id} for product {persisted.product_id} from {persisted.source_id}",
            extra={"review_id": persisted.id, "product": persisted.product_id, "rating": persisted.rating},
        )

        # Dispatch review.created event to Kafka pipeline
        try:
            event = ReviewCreatedEvent(
                data=ReviewCreatedPayload(
                    review_id=persisted.id,
                    product_id=persisted.product_id,
                    source_id=persisted.source_id,
                    rating=persisted.rating,
                    review_title=persisted.review_title,
                    review_text=persisted.review_text,
                    location=persisted.location,
                    created_at=persisted.created_at,
                    ingested_at=persisted.ingested_at,
                    metadata_json=persisted.metadata_json or {},
                )
            )
            await self.kafka_producer.publish(
                topic=settings.KAFKA_TOPIC_REVIEW_CREATED,
                event=event,
                key=persisted.product_id,
            )
        except Exception as kafka_err:
            logger.warning(
                f"Failed to publish review.created event for {persisted.id}",
                extra={"review_id": persisted.id, "error": str(kafka_err)},
            )

        return persisted

    async def ingest_batch(self, batch_dto: ReviewBatchCreate) -> Tuple[int, List[str]]:
        """Ingest a batch of reviews in an optimized transaction."""
        review_ids: List[str] = []
        for item in batch_dto.reviews:
            persisted = await self.ingest_single(item)
            review_ids.append(persisted.id)

        await self.session.flush()
        return len(review_ids), review_ids

    async def ingest_file(self, content: bytes, filename: str) -> Tuple[int, List[str]]:
        """Parse and ingest a file containing reviews (JSON or CSV)."""
        filename_lower = filename.lower()

        if filename_lower.endswith(".json"):
            try:
                raw_data = json.loads(content.decode("utf-8"))
            except Exception as e:
                raise ValidationError(f"Failed to parse JSON file: {str(e)}")

            if isinstance(raw_data, dict) and "reviews" in raw_data:
                raw_list = raw_data["reviews"]
            elif isinstance(raw_data, list):
                raw_list = raw_data
            else:
                raise ValidationError("JSON file must be an array of reviews or an object with a 'reviews' array.")

            batch = [ReviewCreate(**item) for item in raw_list]
            return await self.ingest_batch(ReviewBatchCreate(reviews=batch))

        elif filename_lower.endswith(".csv"):
            try:
                text_stream = io.StringIO(content.decode("utf-8"))
                reader = csv.DictReader(text_stream)
            except Exception as e:
                raise ValidationError(f"Failed to parse CSV file: {str(e)}")

            batch: List[ReviewCreate] = []
            for row in reader:
                rating = int(row.get("rating", 3))
                review_item = ReviewCreate(
                    id=row.get("id"),
                    source=row.get("source") or row.get("source_id"),
                    product=row.get("product") or row.get("product_id"),
                    location=row.get("location"),
                    rating=rating,
                    review_title=row.get("review_title") or row.get("title"),
                    review_text=row.get("review_text") or row.get("text"),
                    created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else None,
                )
                batch.append(review_item)

            if not batch:
                raise ValidationError("CSV file contained no rows.")

            return await self.ingest_batch(ReviewBatchCreate(reviews=batch))

        else:
            raise ValidationError(f"Unsupported file format '{filename}'. Only .json and .csv files are supported.")

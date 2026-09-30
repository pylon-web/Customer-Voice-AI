"""Script to seed synthetic reviews into the database."""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add root and backend to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.core.database import async_session_factory, init_db
from app.models.entities import Review, ReviewAnalysis
from app.repositories.team_repo import TeamRepository
from app.repositories.review_repo import ReviewRepository
from data.synthetic.generator import SyntheticReviewGenerator


async def seed_database(count: int = 10000, batch_size: int = 500) -> None:
    print(f"🚀 Initializing database connection and taxonomy seeds...")
    await init_db()

    async with async_session_factory() as session:
        team_repo = TeamRepository(session)
        await team_repo.seed_initial_taxonomy_if_empty()
        await session.commit()
        print("✅ Products, platforms, and teams verified.")

    print(f"📦 Generating {count:,} synthetic reviews in memory...")
    generator = SyntheticReviewGenerator()
    reviews_data = generator.generate_dataset(total_count=count)

    print(f"💾 Persisting reviews to database in batches of {batch_size}...")
    saved_count = 0

    for i in range(0, len(reviews_data), batch_size):
        chunk = reviews_data[i : i + batch_size]
        async with async_session_factory() as session:
            for item in chunk:
                gt = item["_ground_truth"]
                review = Review(
                    id=item["id"],
                    source_id=item["source_id"],
                    product_id=item["product_id"],
                    location=item["location"],
                    rating=item["rating"],
                    review_title=item.get("review_title"),
                    review_text=item["review_text"],
                    metadata_json=item.get("metadata_json", {}),
                    created_at=datetime.fromisoformat(item["created_at"]),
                )
                session.add(review)

                # Also seed the ground-truth analysis record
                analysis = ReviewAnalysis(
                    review_id=item["id"],
                    sentiment=gt["sentiment"],
                    sentiment_score=gt["sentiment_score"],
                    category=gt["category"],
                    issue=gt["issue"],
                    severity=gt["severity"],
                    customer_intent=gt.get("customer_intent"),
                    confidence=gt.get("confidence", 0.95),
                    entities=[],
                )
                session.add(analysis)

            await session.commit()
            saved_count += len(chunk)
            print(f"   Saved {saved_count:,} / {len(reviews_data):,} reviews ({saved_count / len(reviews_data):.1%})")

    print(f"🎉 Successfully seeded {saved_count:,} reviews into the database!")


def main():
    parser = argparse.ArgumentParser(description="Seed synthetic reviews directly into database.")
    parser.add_argument("--count", type=int, default=10000, help="Number of reviews to seed (default: 10,000)")
    args = parser.parse_args()

    asyncio.run(seed_database(count=args.count))


if __name__ == "__main__":
    main()

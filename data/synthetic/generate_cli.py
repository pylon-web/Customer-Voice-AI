"""CLI script to generate synthetic reviews dataset to JSON and CSV files."""

import argparse
import sys
import os
from pathlib import Path

# Add root and backend directories to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))

from data.synthetic.generator import SyntheticReviewGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic customer reviews for Customer Voice AI.")
    parser.add_argument("--count", type=int, default=10000, help="Total number of reviews to generate (default: 10,000)")
    parser.add_argument("--weeks", type=int, default=6, help="Number of weeks to distribute feedback over (default: 6)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible dataset (default: 42)")
    parser.add_argument("--output-json", type=str, default="data/synthetic/reviews_10k.json", help="Output path for JSON dataset")
    parser.add_argument("--output-csv", type=str, default="data/synthetic/reviews_10k.csv", help="Output path for CSV dataset")

    args = parser.parse_args()

    print(f"🚀 Generating {args.count:,} synthetic reviews across {args.weeks} weeks (seed: {args.seed})...")
    generator = SyntheticReviewGenerator(seed=args.seed)
    reviews = generator.generate_dataset(total_count=args.count, weeks=args.weeks)

    # Ensure parent output directories exist
    Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_csv).parent.mkdir(parents=True, exist_ok=True)

    print(f"💾 Saving JSON to {args.output_json}...")
    generator.save_json(reviews, args.output_json)

    print(f"💾 Saving CSV to {args.output_csv}...")
    generator.save_csv(reviews, args.output_csv)

    # Summary Statistics
    pos = sum(1 for r in reviews if r["_ground_truth"]["sentiment"] == "positive")
    neu = sum(1 for r in reviews if r["_ground_truth"]["sentiment"] == "neutral")
    neg = sum(1 for r in reviews if r["_ground_truth"]["sentiment"] == "negative")

    print("\n✅ Dataset generation complete!")
    print(f"   Total Reviews:    {len(reviews):,}")
    print(f"   Positive Reviews: {pos:,} ({pos/len(reviews):.1%})")
    print(f"   Neutral Reviews:  {neu:,} ({neu/len(reviews):.1%})")
    print(f"   Negative Reviews: {neg:,} ({neg/len(reviews):.1%})")
    print(f"   Output JSON:      {args.output_json} ({os.path.getsize(args.output_json) / (1024*1024):.1f} MB)")
    print(f"   Output CSV:       {args.output_csv} ({os.path.getsize(args.output_csv) / (1024*1024):.1f} MB)")


if __name__ == "__main__":
    main()

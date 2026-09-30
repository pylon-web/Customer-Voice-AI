#!/usr/bin/env python3
"""Customer Voice AI — AI Quality & Compliance Benchmark Evaluation CLI.

Evaluates the AI agent pipeline against ground-truth labels from the 10,000 synthetic review corpus.
Measures:
- Sentiment accuracy, precision, recall, and Macro F1
- Category and severity alignment
- Responsible AI 100% compliance rate (zero certainty phrases in hypotheses)
- Enterprise team routing accuracy

Usage:
    python scripts/evaluate_ai_quality.py [--sample-size 500] [--full] [--out-dir .]
"""

import argparse
import asyncio
import csv
import json
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.evaluation_service import EvaluationService


def load_dataset(csv_path: str, sample_size: int = 500, full: bool = False):
    """Load reviews with ground-truth columns from CSV."""
    reviews = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictDict if hasattr(csv, "DictDict") else csv.DictReader(f)
        for row in reader:
            reviews.append(row)
            if not full and len(reviews) >= sample_size:
                break
    return reviews


async def main():
    parser = argparse.ArgumentParser(description="Evaluate Customer Voice AI model quality & compliance.")
    parser.add_argument("--sample-size", type=int, default=500, help="Number of reviews to evaluate (default: 500)")
    parser.add_argument("--full", action="store_true", help="Evaluate the entire 10k dataset")
    parser.add_argument("--csv", type=str, default="data/synthetic/reviews_10k.csv", help="Path to ground truth CSV")
    parser.add_argument("--out-dir", type=str, default=".", help="Directory to save eval_report.json and eval_report.md")
    args = parser.parse_args()

    csv_path = PROJECT_ROOT / args.csv
    if not csv_path.exists():
        print(f"❌ Error: Ground truth CSV not found at {csv_path}")
        sys.exit(1)

    print(f"📊 Loading ground-truth dataset from {csv_path.name}...")
    reviews = load_dataset(str(csv_path), sample_size=args.sample_size, full=args.full)
    print(f" Loaded {len(reviews):,} reviews for evaluation benchmark.")

    print("\n🔍 Running multi-dimensional AI quality evaluation...")
    eval_service = EvaluationService()
    scorecard = await eval_service.run_full_benchmark(sample_reviews=reviews)

    # Console Output
    print("\n" + "=" * 70)
    print("🏆 CAPITAL ONE CUSTOMER VOICE AI — EVALUATION SCORECARD")
    print("=" * 70)
    print(f" Evaluated At:       {scorecard.evaluated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f" Sample Size:        {scorecard.sample_size:,} reviews")
    print(f" Overall Benchmark:  {'✅ PASSED' if scorecard.overall_status == 'PASSED' else '❌ FAILED'}")
    print("-" * 70)
    print(f" 📈 Sentiment Accuracy:       {scorecard.sentiment_accuracy * 100:.1f}%  (Target: ≥ 85.0%)")
    print(f" 🎯 Sentiment Macro F1:       {scorecard.sentiment_macro_f1:.3f}   (Target: ≥ 0.800)")
    print(f" 🏷️  Category Alignment:      {scorecard.category_accuracy * 100:.1f}%  (Target: ≥ 80.0%)")
    print(f" ⚡ Severity (Adjacent):      {scorecard.severity_adjacent_accuracy * 100:.1f}%  (Target: ≥ 90.0%)")
    print(f" 🛡️  Responsible AI Guardrail: {scorecard.responsible_ai_compliance_rate * 100:.1f}% (Target: 100.0%)")
    print(f" 🏢 Team Routing Accuracy:    {scorecard.team_routing_accuracy * 100:.1f}%  (Target: ≥ 90.0%)")
    print("=" * 70)

    # Class Breakdown Table
    print("\nSentiment Per-Class Metrics:")
    print(f" {'CLASS':<12} {'SUPPORT':<10} {'PRECISION':<12} {'RECALL':<12} {'F1-SCORE':<10}")
    print(" " + "-" * 56)
    for lbl, metric in scorecard.sentiment_details.class_metrics.items():
        print(f" {lbl.upper():<12} {metric.support:<10} {metric.precision:<12.3f} {metric.recall:<12.3f} {metric.f1_score:<10.3f}")

    # Output files
    out_dir = Path(args.out_dir)
    json_path = out_dir / "eval_report.json"
    md_path = out_dir / "eval_report.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(scorecard.model_dump(mode="json"), f, indent=2)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(scorecard.to_markdown())

    print(f"\n Reports saved to:")
    print(f"   • {json_path}")
    print(f"   • {md_path}\n")


if __name__ == "__main__":
    asyncio.run(main())

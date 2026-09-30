"""Unit tests for the synthetic review generator and temporal trend injection."""

import pytest
from datetime import datetime, timezone
from collections import Counter

from data.synthetic.generator import SyntheticReviewGenerator


@pytest.fixture(scope="module")
def sample_dataset():
    """Generate a 2,000-review sample dataset for fast unit test verification."""
    gen = SyntheticReviewGenerator(seed=123)
    return gen.generate_dataset(total_count=2000, weeks=6)


def test_generator_volume_and_schema(sample_dataset):
    """Verify generated reviews match expected schema, ratings, and sentiment bounds."""
    assert len(sample_dataset) == 2000

    required_keys = {"id", "source_id", "product_id", "location", "rating", "review_text", "created_at", "_ground_truth"}
    gt_keys = {"sentiment", "sentiment_score", "category", "issue", "severity", "confidence"}

    for r in sample_dataset[:50]:
        assert required_keys.issubset(r.keys())
        assert 1 <= r["rating"] <= 5
        assert isinstance(r["review_text"], str) and len(r["review_text"]) > 10

        gt = r["_ground_truth"]
        assert gt_keys.issubset(gt.keys())
        assert gt["sentiment"] in {"positive", "neutral", "negative"}
        assert -1.0 <= gt["sentiment_score"] <= 1.0
        assert 0.0 <= gt["confidence"] <= 1.0


def test_product_and_platform_diversity(sample_dataset):
    """Verify multiple Capital One products and diverse review platforms are represented."""
    products = {r["product_id"] for r in sample_dataset}
    sources = {r["source_id"] for r in sample_dataset}

    expected_products = {"venture_x", "savor_one", "banking_360_checking", "c1_mobile_ios", "eno_virtual_assistant", "c1_cafe"}
    expected_sources = {"apple_app_store", "google_play_store", "chrome_web_store", "google_places", "trustpilot"}

    assert expected_products.issubset(products)
    assert expected_sources.issubset(sources)


def test_sentiment_distribution(sample_dataset):
    """Verify balanced distribution of positive, neutral, and negative sentiment."""
    sentiments = Counter(r["_ground_truth"]["sentiment"] for r in sample_dataset)

    # Expected approx 40-55% positive, 10-25% neutral, 30-45% negative
    assert sentiments["positive"] > 600
    assert sentiments["neutral"] > 150
    assert sentiments["negative"] > 500


def _get_time_midpoint(reviews):
    """Calculate the ISO string midpoint between earliest and latest created_at."""
    timestamps = [datetime.fromisoformat(r["created_at"]) for r in reviews]
    min_t, max_t = min(timestamps), max(timestamps)
    mid_t = min_t + (max_t - min_t) / 2
    return mid_t.isoformat()


def test_temporal_lounge_spike_trend(sample_dataset):
    """Verify that Venture X lounge access complaints surge significantly in the second half of time."""
    midpoint_iso = _get_time_midpoint(sample_dataset)

    lounge_reviews = [
        r for r in sample_dataset
        if r["product_id"] == "venture_x" and r["_ground_truth"]["issue"] == "lounge_crowding_denial"
    ]
    assert len(lounge_reviews) > 20

    early_period = [r for r in lounge_reviews if r["created_at"] < midpoint_iso]
    late_period = [r for r in lounge_reviews if r["created_at"] >= midpoint_iso]

    # Second half should have significantly more crowding complaints due to injected spike
    assert len(late_period) > len(early_period) * 2


def test_temporal_ios_biometric_spike(sample_dataset):
    """Verify that iOS mobile biometric failures surge in the second half of time."""
    midpoint_iso = _get_time_midpoint(sample_dataset)

    ios_reviews = [
        r for r in sample_dataset
        if r["product_id"] == "c1_mobile_ios" and r["_ground_truth"]["issue"] == "biometric_login_failure"
    ]
    assert len(ios_reviews) > 20

    early_period = [r for r in ios_reviews if r["created_at"] < midpoint_iso]
    late_period = [r for r in ios_reviews if r["created_at"] >= midpoint_iso]

    assert len(late_period) > len(early_period) * 2


def test_improving_shopping_extension_trend(sample_dataset):
    """Verify that Capital One Shopping extension freeze complaints decline in later weeks."""
    midpoint_iso = _get_time_midpoint(sample_dataset)

    shopping_freeze_reviews = [
        r for r in sample_dataset
        if r["product_id"] == "c1_shopping_extension" and r["_ground_truth"]["issue"] == "extension_freeze"
    ]
    assert len(shopping_freeze_reviews) > 10

    early_period = [r for r in shopping_freeze_reviews if r["created_at"] < midpoint_iso]
    late_period = [r for r in shopping_freeze_reviews if r["created_at"] >= midpoint_iso]

    # Early period should have significantly more freeze complaints than late period
    assert len(early_period) > len(late_period) * 2

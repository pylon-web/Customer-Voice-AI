"""Automated tests for Phase 15: AI Quality Evaluation & Benchmark Suite.

Verifies:
1. Quantitative sentiment evaluation (accuracy, precision, recall, macro F1).
2. Responsible AI compliance evaluation (enforcing tentative framing, rejecting certainty phrases).
3. Team routing accuracy against domain taxonomy.
4. Full benchmark scorecard compilation and Markdown report rendering.
"""

import pytest
from app.services.evaluation_service import (
    EvaluationService,
    AIQualityScorecard,
    SentimentEvaluationResult,
    ResponsibleAIEvalResult,
    RoutingEvalResult,
)


@pytest.mark.asyncio
async def test_sentiment_evaluation_metrics():
    """Verify sentiment evaluation accurately computes precision, recall, accuracy, and F1."""
    eval_service = EvaluationService()

    sample_reviews = [
        {"review_text": "Love the Venture X lounge!", "rating": 5, "product_id": "venture_x", "ground_truth_sentiment": "positive"},
        {"review_text": "Great card benefits.", "rating": 4, "product_id": "savor_one", "ground_truth_sentiment": "positive"},
        {"review_text": "Average checking account.", "rating": 3, "product_id": "banking_360_checking", "ground_truth_sentiment": "neutral"},
        {"review_text": "App crashes repeatedly on Face ID.", "rating": 1, "product_id": "c1_mobile_ios", "ground_truth_sentiment": "negative"},
        {"review_text": "Wait time at lounge was terrible.", "rating": 2, "product_id": "venture_x", "ground_truth_sentiment": "negative"},
    ]

    result: SentimentEvaluationResult = await eval_service.evaluate_sentiment(sample_reviews)

    assert result.total_samples == 5
    assert result.accuracy == 1.0
    assert result.macro_f1 == 1.0
    assert "positive" in result.class_metrics
    assert "negative" in result.class_metrics
    assert "neutral" in result.class_metrics
    assert result.class_metrics["positive"].precision == 1.0
    assert result.class_metrics["negative"].recall == 1.0


def test_responsible_ai_evaluation_compliances():
    """Verify Responsible AI evaluator verifies 100% adherence and catches prohibited phrasing."""
    eval_service = EvaluationService()

    # 1. Fully compliant hypotheses
    compliant_hypotheses = [
        "Hypothesis: Investigate potential timeout in partner transfer gateway API.",
        "Hypothesis: Verify whether iOS 18 Face ID prompt triggers unhandled null pointer.",
        "Hypothesis: Potential network packet drop observed at Dallas Café location.",
    ]
    comp_result: ResponsibleAIEvalResult = eval_service.evaluate_responsible_ai(compliant_hypotheses)
    assert comp_result.compliance_rate == 1.0
    assert comp_result.violating_hypotheses_count == 0
    assert comp_result.status == "PASSED"
    assert comp_result.prohibited_phrase_detections == {}

    # 2. Non-compliant hypotheses violating Responsible AI boundaries
    violating_hypotheses = [
        "Hypothesis: Investigate potential bug.",
        "The bug is caused by developer mistake in release v6.14.",
        "The exact root cause is database corruption on AWS cluster.",
        "This issue is definitively due to third-party vendor outage.",
    ]
    viol_result: ResponsibleAIEvalResult = eval_service.evaluate_responsible_ai(violating_hypotheses)
    assert viol_result.compliance_rate < 1.0
    assert viol_result.violating_hypotheses_count == 3
    assert viol_result.status == "FAILED"
    assert "is caused by" in viol_result.prohibited_phrase_detections
    assert "the exact root cause is" in viol_result.prohibited_phrase_detections
    assert "is definitively due to" in viol_result.prohibited_phrase_detections


def test_team_routing_evaluation():
    """Verify team routing pattern evaluation metrics."""
    eval_service = EvaluationService()

    routing_cases = [
        {"product_id": "c1_mobile_ios", "expected_team": "digital_eng_mobile", "actual_team": "digital_eng_mobile"},
        {"product_id": "venture_x", "expected_team": "travel_lounges_prod", "actual_team": "travel_lounges_prod"},
        {"product_id": "banking_360_checking", "expected_team": "payments_ops", "actual_team": "payments_ops"},
        {"product_id": "c1_cafe", "expected_team": "cafe_ops", "actual_team": "cafe_ops"},
    ]

    result: RoutingEvalResult = eval_service.evaluate_team_routing(routing_cases)
    assert result.total_routed == 4
    assert result.correctly_routed == 4
    assert result.routing_accuracy == 1.0
    assert len(result.mismatches) == 0


@pytest.mark.asyncio
async def test_full_benchmark_scorecard_and_markdown():
    """Verify full benchmark execution, scorecard compilation, and markdown report rendering."""
    eval_service = EvaluationService()

    reviews = [
        {"review_text": "Love the Venture X lounge travel perks!", "rating": 5, "product_id": "venture_x", "ground_truth_sentiment": "positive", "ground_truth_category": "lounge_access", "ground_truth_severity": "low"},
        {"review_text": "3% dining cashback is great on SavorOne.", "rating": 4, "product_id": "savor_one", "ground_truth_sentiment": "positive", "ground_truth_category": "rewards", "ground_truth_severity": "low"},
        {"review_text": "Mobile banking app crashes on Face ID launch.", "rating": 1, "product_id": "c1_mobile_ios", "ground_truth_sentiment": "negative", "ground_truth_category": "authentication", "ground_truth_severity": "critical"},
        {"review_text": "Target online checkout rejected my Eno virtual card.", "rating": 1, "product_id": "eno_virtual_assistant", "ground_truth_sentiment": "negative", "ground_truth_category": "virtual_cards", "ground_truth_severity": "high"},
    ]

    scorecard: AIQualityScorecard = await eval_service.run_full_benchmark(sample_reviews=reviews)

    assert scorecard.sample_size == 4
    assert scorecard.sentiment_accuracy >= 0.85
    assert scorecard.responsible_ai_compliance_rate == 1.0
    assert scorecard.team_routing_accuracy >= 0.90
    assert scorecard.overall_status == "PASSED"

    # Verify Markdown rendering
    md = scorecard.to_markdown()
    assert "# VoiceIQ — Model Quality & Compliance Benchmark" in md
    assert "Sentiment Accuracy" in md
    assert "Responsible AI Guardrail" in md
    assert "PASSED" in md

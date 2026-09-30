"""Comprehensive End-to-End Pipeline Integration Test.

Validates the complete 10-step operational lifecycle:
1. Ingestion: Raw customer reviews ingested via IngestionService (simulating Venture X lounge friction surge).
2. Event-Driven Messaging: Kafka 'review.created' event publication.
3. Asynchronous AI Analysis: Sentiment, issue, and category extraction into ReviewAnalysis entities.
4. Vector Embeddings: 1536-dimensional semantic embeddings generated and stored via EmbeddingService.
5. Semantic Clustering: DBSCAN clustering groups reviews into an IssueCluster with human-readable title.
6. Trend & Velocity Anomaly Detection: Baseline calculation and surge classification (z >= 2.0, 'emerging').
7. Root Cause Investigation: LangGraph multi-agent state graph produces evidence-backed, tentative hypothesis.
8. Configurable Team Routing: Proper mapping to generic enterprise team ('travel_lounges_prod').
9. Executive Intelligence Briefing: ReportService compiles weekly brief with executive summary and markdown.
10. Human-in-the-Loop (HITL) Decision: Human operational approval recorded with full audit logging.
"""

from datetime import datetime, timezone, timedelta
import pytest

from app.core.database import async_session_factory
from app.core.config import settings
from app.kafka.producer import get_kafka_producer
from app.models.schemas import ReviewCreate, ClusterRunRequest, ReportGenerateRequest
from app.services.ingestion_service import IngestionService
from app.services.analysis_service import AnalysisService
from app.services.embedding_service import EmbeddingService
from app.services.clustering_service import ClusteringService
from app.services.trend_service import TrendService
from app.services.investigation_service import InvestigationService
from app.services.report_service import ReportService
from app.agents.investigation_graph import CERTAINTY_PHRASES


@pytest.mark.asyncio
async def test_full_customer_voice_ai_lifecycle_pipeline():
    """Execute complete end-to-end pipeline from ingestion through HITL approval."""
    producer = get_kafka_producer()
    producer.clear_history()

    now = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)

    # 10 realistic customer reviews simulating a sudden lounge crowding spike at DFW/DEN
    # 4 reviews in the historical baseline window (weeks 4, 3, 2, 1 prior)
    # 6 reviews in the current active window (spiking volume)
    review_templates = [
        # Baseline window
        {"days_ago": 28, "rating": 2, "loc": "Dallas, TX", "text": "Venture X lounge line at DFW was long during my morning flight."},
        {"days_ago": 21, "rating": 2, "loc": "Dallas, TX", "text": "Lounge capacity at DFW was restricted, waited 20 minutes."},
        {"days_ago": 14, "rating": 2, "loc": "Denver, CO", "text": "Capital One lounge line in Denver was slow to check in."},
        {"days_ago": 10, "rating": 2, "loc": "Dallas, TX", "text": "Lounge waitlist for Venture X cardholders had an espresso machine broken."},
        # Current week spike (surge)
        {"days_ago": 4, "rating": 1, "loc": "Dallas, TX", "text": "DFW lounge line wrapped around the terminal. Terrible wait times for Venture X!"},
        {"days_ago": 3, "rating": 1, "loc": "Dallas, TX", "text": "Turned away from the Capital One lounge at DFW because of extreme overcrowding."},
        {"days_ago": 3, "rating": 1, "loc": "Denver, CO", "text": "Denver lounge line was over 50 minutes long. Impossible to get in with Venture X."},
        {"days_ago": 2, "rating": 1, "loc": "Dallas, TX", "text": "Lounge overcrowding at DFW makes the priority pass benefit useless during peak hours."},
        {"days_ago": 1, "rating": 1, "loc": "Dallas, TX", "text": "Waited 45 minutes in the DFW lounge waitlist, missed my flight breakfast."},
        {"days_ago": 0, "rating": 1, "loc": "Denver, CO", "text": "Capital One lounge waitlist is broken, 1-hour wait for cardholders."},
    ]

    async with async_session_factory() as session:
        ingestion_svc = IngestionService(session, kafka_producer=producer)
        analysis_svc = AnalysisService(session, kafka_producer=producer)
        embedding_svc = EmbeddingService(session, kafka_producer=producer)
        clustering_svc = ClusteringService(session, kafka_producer=producer)
        trend_svc = TrendService(session, kafka_producer=producer)
        investigation_svc = InvestigationService(session, kafka_producer=producer)
        report_svc = ReportService(session, kafka_producer=producer)

        # -------------------------------------------------------------------------
        # Step 1 & 2: Ingestion & Kafka Event Publishing
        # -------------------------------------------------------------------------
        ingested_reviews = []
        for idx, item in enumerate(review_templates):
            r_dto = ReviewCreate(
                id=f"e2e-rev-vx-lounge-{idx:03d}",
                product_id="venture_x",
                source_id="apple_app_store",
                rating=item["rating"],
                review_title=f"Lounge Experience #{idx}",
                review_text=item["text"],
                location=item["loc"],
                created_at=now - timedelta(days=item["days_ago"]),
            )
            created_rev = await ingestion_svc.ingest_single(r_dto)
            ingested_reviews.append(created_rev)

        await session.commit()
        assert len(ingested_reviews) == 10

        # Verify Kafka review.created events
        created_events = producer.get_published_events(settings.KAFKA_TOPIC_REVIEW_CREATED)
        assert len(created_events) >= 10
        assert any(e["data"]["review_id"] == "e2e-rev-vx-lounge-000" for e in created_events)

        # -------------------------------------------------------------------------
        # Step 3: AI Review Analysis Agent (Sentiment, Category, Severity)
        # -------------------------------------------------------------------------
        for rev in ingested_reviews:
            analysis = await analysis_svc.analyze_review(rev.id)
            assert analysis.sentiment == "negative"
            assert analysis.sentiment_score < 0.0
            assert analysis.severity in ["medium", "high", "critical"]
            assert analysis.category in ["Travel & Lounge Perks", "travel_benefits", "lounge_access", "Credit Card Rewards"]

        await session.commit()

        # Verify Kafka review.analyzed events
        analyzed_events = producer.get_published_events(settings.KAFKA_TOPIC_REVIEW_ANALYZED)
        assert len(analyzed_events) >= 10

        # -------------------------------------------------------------------------
        # Step 4: 1536-Dimensional Semantic Vector Embeddings
        # -------------------------------------------------------------------------
        for rev in ingested_reviews:
            emb = await embedding_svc.generate_and_store_embedding(rev.id)
            assert emb.dimension == 1536
            assert len(emb.embedding) == 1536

        await session.commit()

        # Verify Kafka review.embedded events
        embedded_events = producer.get_published_events(settings.KAFKA_TOPIC_REVIEW_EMBEDDED)
        assert len(embedded_events) >= 10

        # -------------------------------------------------------------------------
        # Step 5: Unsupervised Semantic Clustering (DBSCAN)
        # -------------------------------------------------------------------------
        cluster_run = await clustering_svc.run_clustering(
            ClusterRunRequest(product_id="venture_x", eps=0.50, min_samples=3)
        )
        assert cluster_run.clusters_formed >= 1
        assert cluster_run.clustered_reviews_count >= 5

        target_cluster_id = cluster_run.cluster_ids[0]
        cluster = await clustering_svc.cluster_repo.get_by_id(target_cluster_id)
        assert cluster is not None
        assert cluster.affected_product_id == "venture_x"
        assert "lounge" in cluster.cluster_title.lower() or "crowding" in cluster.cluster_title.lower()
        assert cluster.negative_pct >= 80.0

        # -------------------------------------------------------------------------
        # Step 6: Trend & Velocity Anomaly Detection (z >= 2.0 surge)
        # -------------------------------------------------------------------------
        trend_metric = await trend_svc.calculate_trend_for_cluster(cluster, as_of_date=now)
        assert trend_metric.current_volume >= 5
        assert trend_metric.anomaly_score >= 2.0 or trend_metric.wow_change_pct >= 50.0
        assert trend_metric.trend_direction == "emerging"

        # Verify Kafka issue.detected event
        issue_events = producer.get_published_events(settings.KAFKA_TOPIC_ISSUE_DETECTED)
        assert len(issue_events) >= 1
        assert any(e["data"]["cluster_id"] == cluster.id for e in issue_events)

        # -------------------------------------------------------------------------
        # Step 7 & 8: LangGraph Root Cause Investigation & Team Routing
        # -------------------------------------------------------------------------
        recommendation = await investigation_svc.investigate_cluster(cluster.id)
        assert recommendation.cluster_id == cluster.id
        assert recommendation.status == "pending_approval"

        # Evidence must cite observations
        assert "customer reports" in recommendation.observed_evidence.lower()
        assert "negative" in recommendation.observed_evidence.lower()

        # Hypothesis must strictly adhere to tentative framing and avoid certainty
        assert recommendation.investigation_hypothesis.lower().startswith("hypothesis:")
        assert any(t in recommendation.investigation_hypothesis.lower() for t in ["investigate", "potential", "verify whether"])
        assert not any(phrase in recommendation.investigation_hypothesis.lower() for phrase in CERTAINTY_PHRASES)

        # Suggested team must route to travel lounge product operations
        assert recommendation.suggested_team_id == "travel_lounges_prod"

        # -------------------------------------------------------------------------
        # Step 9: Weekly Executive Intelligence Briefing
        # -------------------------------------------------------------------------
        report = await report_svc.generate_weekly_report(
            ReportGenerateRequest(
                title="Venture X Lounge Executive Briefing",
                period_start=now - timedelta(days=7),
                period_end=now,
            )
        )
        assert report.id is not None
        assert report.total_reviews >= 6
        assert report.emerging_issues_count >= 1
        assert len(report.report_issues) >= 1

        md_output = report_svc.render_markdown(report)
        assert "# Venture X Lounge Executive Briefing" in md_output
        assert "Executive Summary" in md_output
        assert "Key Metrics Snapshot" in md_output
        assert "High-Priority Issues & Action Plans" in md_output

        # Verify Kafka report.generated event
        report_events = producer.get_published_events(settings.KAFKA_TOPIC_REPORT_GENERATED)
        assert len(report_events) >= 1
        assert report_events[-1]["data"]["report_id"] == report.id

        # -------------------------------------------------------------------------
        # Step 10: Human-in-the-Loop (HITL) Operational Decision & Audit Trail
        # -------------------------------------------------------------------------
        updated_rec, approval = await investigation_svc.record_human_decision(
            recommendation_id=recommendation.id,
            reviewer_name="Marcus Vance (VP Airport Experience)",
            decision="approved",
            reviewer_notes="Approved expansion of digital capacity queue for DFW and DEN.",
        )

        assert updated_rec.status == "approved"
        assert approval.decision == "approved"
        assert approval.reviewer_name == "Marcus Vance (VP Airport Experience)"
        assert approval.decided_at is not None
        assert "digital capacity queue" in approval.reviewer_notes

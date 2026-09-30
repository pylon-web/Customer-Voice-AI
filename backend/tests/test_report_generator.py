"""Automated tests for Phase 12: Weekly Intelligence Report Generator."""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.core.database import async_session_factory
from app.models.entities import IssueCluster, Review, Recommendation, TrendMetric, Report
from app.models.schemas import ReportGenerateRequest
from app.repositories.report_repo import ReportRepository
from app.repositories.cluster_repo import ClusterRepository
from app.repositories.trend_repo import TrendRepository
from app.repositories.recommendation_repo import RecommendationRepository
from app.services.report_service import ReportService
from app.kafka.producer import get_kafka_producer
from app.core.config import settings


@pytest.mark.asyncio
async def test_weekly_report_generation_and_kafka_event():
    """Verify report generation aggregates reviews, geographic insights, velocity trends, and emits Kafka event."""
    producer = get_kafka_producer()
    producer.clear_history()

    now = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)

    async with async_session_factory() as session:
        # 1. Seed sample reviews with geographic distribution
        for i in range(10):
            r_date = now - timedelta(days=2)
            session.add(
                Review(
                    id=f"rev-rep-austin-{i}",
                    product_id="c1_cafe",
                    source_id="google_places",
                    location="Austin, TX",
                    rating=1 if i < 7 else 4,
                    review_text=f"Austin café Wi-Fi kept dropping out during my meeting #{i}",
                    metadata_json={},
                    created_at=r_date,
                    ingested_at=r_date,
                )
            )

        for i in range(5):
            r_date = now - timedelta(days=3)
            session.add(
                Review(
                    id=f"rev-rep-chicago-{i}",
                    product_id="c1_mobile_ios",
                    source_id="apple_app_store",
                    location="Chicago, IL",
                    rating=2,
                    review_text=f"Mobile app keeps closing on Face ID #{i}",
                    metadata_json={},
                    created_at=r_date,
                    ingested_at=r_date,
                )
            )

        # 2. Seed active clusters and trends
        cluster_repo = ClusterRepository(session)
        cluster_emerging = IssueCluster(
            id="cluster-rep-faceid-001",
            cluster_title="Face ID Login Crash Surge",
            affected_product_id="c1_mobile_ios",
            category="biometric_login",
            review_count=15,
            negative_pct=93.3,
            representative_quotes=["Face ID crashes on launch."],
            status="active",
            first_observed_at=now - timedelta(days=5),
            latest_observed_at=now,
        )
        await cluster_repo.create_cluster(cluster_emerging)

        trend_repo = TrendRepository(session)
        await trend_repo.create(
            TrendMetric(
                cluster_id=cluster_emerging.id,
                period_start=now - timedelta(days=7),
                period_end=now,
                current_volume=15,
                previous_volume=2,
                baseline_4wk_avg=2.0,
                wow_change_pct=650.0,
                trend_direction="emerging",
                anomaly_score=4.2,
            )
        )

        rec_repo = RecommendationRepository(session)
        await rec_repo.create(
            Recommendation(
                cluster_id=cluster_emerging.id,
                suggested_team_id="digital_engineering_mobile",
                observed_evidence="15 users reported crashes.",
                investigation_hypothesis="Hypothesis: Investigate nil unwrapping.",
                recommended_action="1. Inspect Crashlytics logs. 2. Release hotfix patch.",
                confidence=0.95,
                status="pending_approval",
            )
        )

        await session.commit()

        # 3. Generate Report via Service
        service = ReportService(session, kafka_producer=producer)
        report = await service.generate_weekly_report(
            ReportGenerateRequest(
                title="Weekly Executive Briefing — Test Cohort",
                period_start=now - timedelta(days=7),
                period_end=now,
            )
        )

        # 4. Verify Macro Metrics & Executive Summary
        assert report.id is not None
        assert report.total_reviews >= 15
        assert report.negative_pct >= 60.0
        assert report.emerging_issues_count >= 1
        assert "VoiceIQ platform analyzed" in report.executive_summary

        # 5. Verify Geographic Insights
        assert "Austin, TX" in report.geographic_insights
        assert report.geographic_insights["Austin, TX"]["total_reviews"] == 10
        assert report.geographic_insights["Austin, TX"]["negative_count"] == 7

        # 6. Verify Kafka Event Dispatch
        published = [e for e in producer.published_history if e["topic"] == settings.KAFKA_TOPIC_REPORT_GENERATED]
        assert len(published) >= 1
        payload = published[0]["event"]["data"]
        assert payload["report_id"] == report.id
        assert payload["emerging_issues_count"] >= 1


@pytest.mark.asyncio
async def test_report_multi_format_rendering():
    """Verify Markdown and HTML document rendering from report entity."""
    now = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)

    async with async_session_factory() as session:
        service = ReportService(session)
        report = await service.generate_weekly_report(
            ReportGenerateRequest(
                title="Format Test Executive Report",
                period_start=now - timedelta(days=7),
                period_end=now,
            )
        )

        # 1. Render Markdown
        md = service.render_markdown(report)
        assert "# Format Test Executive Report" in md
        assert "## 1. Executive Summary" in md
        assert "## 2. Key Metrics Snapshot" in md
        assert "Total Reviews Ingested" in md

        # 2. Render HTML
        html = service.render_html(report)
        assert "<!DOCTYPE html>" in html
        assert "<title>Format Test Executive Report</title>" in html
        assert "kpi-card" in html
        assert "Regional & Geographic Anomalies" in html


def test_reports_api_endpoints(client: TestClient):
    """Test REST API endpoints for generating, listing, and retrieving reports in JSON, Markdown, and HTML."""
    # 1. Generate report via POST /api/v1/reports/generate
    gen_res = client.post("/api/v1/reports/generate", json={"title": "API Verification Report"})
    assert gen_res.status_code == 201
    report_data = gen_res.json()
    assert report_data["title"] == "API Verification Report"
    assert "total_reviews" in report_data
    assert "executive_summary" in report_data
    report_id = report_data["id"]

    # 2. List reports via GET /api/v1/reports
    list_res = client.get("/api/v1/reports?page=1&page_size=10")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(r["id"] == report_id for r in list_data["items"])

    # 3. Get report JSON via GET /api/v1/reports/{report_id}
    get_res = client.get(f"/api/v1/reports/{report_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == report_id

    # 4. Get report Markdown via GET /api/v1/reports/{report_id}/markdown
    md_res = client.get(f"/api/v1/reports/{report_id}/markdown")
    assert md_res.status_code == 200
    md_data = md_res.json()
    assert md_data["format"] == "markdown"
    assert "Executive Summary" in md_data["content"]

    # 5. Get report HTML via GET /api/v1/reports/{report_id}/html
    html_res = client.get(f"/api/v1/reports/{report_id}/html")
    assert html_res.status_code == 200
    assert "text/html" in html_res.headers["content-type"]
    assert "<!DOCTYPE html>" in html_res.text

    # 6. Test 404 for unknown report ID
    not_found_res = client.get("/api/v1/reports/non-existent-report-999")
    assert not_found_res.status_code == 404

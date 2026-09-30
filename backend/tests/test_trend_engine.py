"""Automated tests for the Trend & Velocity Anomaly Detection Engine (Phase 9)."""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.core.database import async_session_factory
from app.models.entities import IssueCluster, Review, ClusterReview, TrendMetric
from app.models.schemas import ReviewCreate, TrendCalculateRequest
from app.repositories.trend_repo import TrendRepository
from app.repositories.cluster_repo import ClusterRepository
from app.services.trend_service import TrendService
from app.services.ingestion_service import IngestionService
from app.kafka.producer import get_kafka_producer
from app.core.config import settings


@pytest.mark.asyncio
async def test_trend_calculation_emerging_surge_and_kafka_event():
    """Verify that a sudden volume surge triggers 'emerging' status, high z-score, and Kafka event."""
    producer = get_kafka_producer()
    producer.clear_history()

    now = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)

    async with async_session_factory() as session:
        # 1. Create an issue cluster
        cluster_repo = ClusterRepository(session)
        cluster = IssueCluster(
            id="cluster-lounge-spike-001",
            cluster_title="DFW Lounge Overcrowding Surge",
            affected_product_id="venture_x",
            category="travel_benefits",
            review_count=18,
            negative_pct=95.0,
            status="active",
            first_observed_at=now - timedelta(days=28),
            latest_observed_at=now,
        )
        await cluster_repo.create_cluster(cluster)

        # 2. Seed baseline reviews:
        # Past 4 weeks: 2 reviews per week
        for week in range(1, 5):
            for r in range(2):
                rev_date = now - timedelta(days=7 * week + 2)
                rev = Review(
                    id=f"rev-lounge-hist-{week}-{r}",
                    product_id="venture_x",
                    source_id="apple_app_store",
                    rating=1,
                    review_text="DFW lounge has a small line.",
                    metadata_json={},
                    created_at=rev_date,
                    ingested_at=rev_date,
                )
                session.add(rev)
                session.add(ClusterReview(
                    cluster_id=cluster.id,
                    review_id=rev.id,
                    similarity_score=0.92,
                    assigned_at=rev_date,
                ))

        # Current week: 10 reviews (huge spike compared to baseline of 2/week)
        for r in range(10):
            rev_date = now - timedelta(days=2)
            rev = Review(
                id=f"rev-lounge-curr-{r}",
                product_id="venture_x",
                source_id="apple_app_store",
                rating=1,
                review_text="45-minute waitlist to enter the Venture X lounge!",
                metadata_json={},
                created_at=rev_date,
                ingested_at=rev_date,
            )
            session.add(rev)
            session.add(ClusterReview(
                cluster_id=cluster.id,
                review_id=rev.id,
                similarity_score=0.95,
                assigned_at=rev_date,
            ))

        await session.commit()

        # 3. Execute TrendService
        service = TrendService(session, kafka_producer=producer)
        metric = await service.calculate_trend_for_cluster(cluster, as_of_date=now)

        # 4. Verify Trend Calculations
        assert metric.current_volume == 10
        assert metric.previous_volume == 2
        assert metric.baseline_4wk_avg == 2.0
        assert metric.wow_change_pct == 400.0  # (10 - 2) / 2 * 100% = +400%
        assert metric.trend_direction == "emerging"
        assert metric.anomaly_score >= 2.0  # z-score or volume anomaly >= 2.0

        # 5. Verify Kafka event dispatch (issue.detected)
        published = [e for e in producer.published_history if e["topic"] == settings.KAFKA_TOPIC_ISSUE_DETECTED]
        assert len(published) >= 1
        payload = published[0]["event"]["data"]
        assert payload["cluster_id"] == cluster.id
        assert payload["trend_direction"] == "emerging"
        assert payload["affected_product_id"] == "venture_x"


@pytest.mark.asyncio
async def test_trend_calculation_improving_and_stable():
    """Verify trajectory detection for resolving issues ('improving') and normal baseline ('stable')."""
    now = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)

    async with async_session_factory() as session:
        cluster_repo = ClusterRepository(session)

        # 1. Improving cluster: Shopping extension freeze resolving (-90% drop)
        improving_cluster = IssueCluster(
            id="cluster-shopping-resolving-001",
            cluster_title="Shopping Browser Extension Freeze",
            affected_product_id="shopping_extension",
            category="technical_issue",
            status="active",
            first_observed_at=now - timedelta(days=21),
            latest_observed_at=now,
        )
        await cluster_repo.create_cluster(improving_cluster)

        # Previous week had 10 complaints
        for r in range(10):
            rev_date = now - timedelta(days=10)
            rev = Review(
                id=f"rev-shop-prev-{r}",
                product_id="shopping_extension",
                source_id="chrome_web_store",
                rating=1,
                review_text="Browser freezes when extension loads coupons.",
                metadata_json={},
                created_at=rev_date,
                ingested_at=rev_date,
            )
            session.add(rev)
            session.add(ClusterReview(
                cluster_id=improving_cluster.id,
                review_id=rev.id,
                similarity_score=0.9,
                assigned_at=rev_date,
            ))

        # Current week has only 1 complaint (90% drop)
        rev_date = now - timedelta(days=2)
        rev = Review(
            id="rev-shop-curr-0",
            product_id="shopping_extension",
            source_id="chrome_web_store",
            rating=2,
            review_text="Occasional delay on checkout.",
            metadata_json={},
            created_at=rev_date,
            ingested_at=rev_date,
        )
        session.add(rev)
        session.add(ClusterReview(
            cluster_id=improving_cluster.id,
            review_id=rev.id,
            similarity_score=0.9,
            assigned_at=rev_date,
        ))

        # 2. Stable cluster: Normal steady baseline
        stable_cluster = IssueCluster(
            id="cluster-branch-stable-001",
            cluster_title="Normal Branch Wait Times",
            affected_product_id="branches",
            category="customer_service",
            status="active",
            first_observed_at=now - timedelta(days=21),
            latest_observed_at=now,
        )
        await cluster_repo.create_cluster(stable_cluster)

        # 2 complaints in previous week, 2 in current week
        for r in range(2):
            p_date = now - timedelta(days=10)
            c_date = now - timedelta(days=3)
            r_prev = Review(
                id=f"rev-branch-p-{r}",
                product_id="branches",
                source_id="google_places",
                rating=3,
                review_text="Average wait time at branch teller.",
                metadata_json={},
                created_at=p_date,
                ingested_at=p_date,
            )
            r_curr = Review(
                id=f"rev-branch-c-{r}",
                product_id="branches",
                source_id="google_places",
                rating=3,
                review_text="Average wait time at branch teller.",
                metadata_json={},
                created_at=c_date,
                ingested_at=c_date,
            )
            session.add(r_prev)
            session.add(r_curr)
            session.add(ClusterReview(cluster_id=stable_cluster.id, review_id=r_prev.id, similarity_score=0.9, assigned_at=p_date))
            session.add(ClusterReview(cluster_id=stable_cluster.id, review_id=r_curr.id, similarity_score=0.9, assigned_at=c_date))

        await session.commit()

        service = TrendService(session)

        # Test improving cluster
        metric_imp = await service.calculate_trend_for_cluster(improving_cluster, as_of_date=now)
        assert metric_imp.current_volume == 1
        assert metric_imp.previous_volume == 10
        assert metric_imp.wow_change_pct == -90.0
        assert metric_imp.trend_direction == "improving"

        # Test stable cluster
        metric_stb = await service.calculate_trend_for_cluster(stable_cluster, as_of_date=now)
        assert metric_stb.current_volume == 2
        assert metric_stb.previous_volume == 2
        assert metric_stb.wow_change_pct == 0.0
        assert metric_stb.trend_direction == "stable"


def test_trends_api_endpoints(client: TestClient):
    """Test REST API endpoints: trigger calculation, list trends with filters, and cluster drilldown."""
    # 1. Trigger calculation via POST /api/v1/trends/calculate
    calc_res = client.post("/api/v1/trends/calculate", json={})
    assert calc_res.status_code == 200
    calc_data = calc_res.json()
    assert "trends_calculated" in calc_data
    assert "emerging_count" in calc_data
    assert "trend_ids" in calc_data

    # 2. List all trends via GET /api/v1/trends
    list_res = client.get("/api/v1/trends?page=1&page_size=10")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert "items" in list_data
    assert "total" in list_data
    assert len(list_data["items"]) >= 1

    sample_metric = list_data["items"][0]
    assert "cluster_id" in sample_metric
    assert "wow_change_pct" in sample_metric
    assert "trend_direction" in sample_metric
    assert "anomaly_score" in sample_metric

    # 3. Filter by trend_direction
    dir_res = client.get("/api/v1/trends?trend_direction=emerging")
    assert dir_res.status_code == 200
    dir_data = dir_res.json()
    for item in dir_data["items"]:
        assert item["trend_direction"] == "emerging"

    # 4. Filter by is_anomaly
    anom_res = client.get("/api/v1/trends?is_anomaly=true")
    assert anom_res.status_code == 200

    # 5. Get cluster trend history via GET /api/v1/trends/{cluster_id}
    cluster_id = sample_metric["cluster_id"]
    hist_res = client.get(f"/api/v1/trends/{cluster_id}")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert isinstance(hist_data, list)
    assert len(hist_data) >= 1
    assert hist_data[0]["cluster_id"] == cluster_id

    # 6. Test 404 for unknown cluster ID
    not_found_res = client.get("/api/v1/trends/non-existent-cluster-999")
    assert not_found_res.status_code == 404


@pytest.mark.asyncio
async def test_trend_calculation_zero_baseline_new_cluster():
    """Verify newly emerged cluster with zero prior history calculates properly without division error."""
    now = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)

    async with async_session_factory() as session:
        cluster_repo = ClusterRepository(session)
        new_cluster = IssueCluster(
            id="cluster-brand-new-faceid-crash",
            cluster_title="Face ID Crash After v6.14 iOS Release",
            affected_product_id="c1_mobile_ios",
            category="technical_issue",
            status="active",
            first_observed_at=now,
            latest_observed_at=now,
        )
        await cluster_repo.create_cluster(new_cluster)

        # 5 reviews in current week, zero in previous weeks
        for r in range(5):
            c_date = now - timedelta(days=1)
            rev = Review(
                id=f"rev-brandnew-{r}",
                product_id="c1_mobile_ios",
                source_id="apple_app_store",
                rating=1,
                review_text="Instant crash upon Face ID prompt.",
                metadata_json={},
                created_at=c_date,
                ingested_at=c_date,
            )
            session.add(rev)
            session.add(ClusterReview(
                cluster_id=new_cluster.id,
                review_id=rev.id,
                similarity_score=0.98,
                assigned_at=c_date,
            ))
        await session.commit()

        service = TrendService(session)
        metric = await service.calculate_trend_for_cluster(new_cluster, as_of_date=now)

        assert metric.current_volume == 5
        assert metric.previous_volume == 0
        assert metric.baseline_4wk_avg == 0.0
        assert metric.wow_change_pct == 100.0
        assert metric.trend_direction == "emerging"
        assert metric.anomaly_score >= 2.0


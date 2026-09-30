"""Unit and integration tests for database models, seed taxonomy, pgvector adaptation, and repositories."""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.models.entities import (
    Base,
    Product,
    Source,
    Team,
    Review,
    ReviewAnalysis,
    ReviewEmbedding,
    IssueCluster,
    ClusterReview,
    Recommendation,
    Approval,
    Report,
    ReportIssue,
)
from app.models.schemas import ReviewFilterParams
from app.repositories.review_repo import ReviewRepository
from app.repositories.cluster_repo import ClusterRepository
from app.repositories.team_repo import TeamRepository


@pytest_asyncio.fixture
async def test_session():
    """Create an isolated in-memory SQLite database session for unit testing."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with session_maker() as session:
        yield session

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_seed_capital_one_taxonomy(test_session: AsyncSession):
    """Verify that Capital One product, platform, and team taxonomy seeds cleanly."""
    team_repo = TeamRepository(test_session)
    await team_repo.seed_initial_taxonomy_if_empty()

    # 1. Verify Capital One products
    prod_stmt = select(Product)
    products = (await test_session.execute(prod_stmt)).scalars().all()
    prod_ids = {p.id for p in products}

    expected_products = {
        "venture_x",
        "savor_one",
        "quicksilver",
        "banking_360_checking",
        "banking_360_savings",
        "auto_navigator",
        "c1_mobile_ios",
        "eno_virtual_assistant",
        "c1_shopping_extension",
        "c1_cafe",
    }
    assert expected_products.issubset(prod_ids)

    # 2. Verify Ingestion Sources / Platforms
    src_stmt = select(Source)
    sources = (await test_session.execute(src_stmt)).scalars().all()
    src_ids = {s.id for s in sources}
    assert "apple_app_store" in src_ids
    assert "google_play_store" in src_ids
    assert "chrome_web_store" in src_ids
    assert "google_places" in src_ids

    # 3. Verify Business Teams
    teams = await team_repo.get_all_teams()
    team_ids = {t.id for t in teams}
    assert "digital_engineering_mobile" in team_ids
    assert "travel_lounges_product" in team_ids
    assert "cafe_operations" in team_ids
    assert "digital_ai_security" in team_ids
    assert "shopping_engineering" in team_ids


@pytest.mark.asyncio
async def test_configurable_team_routing_engine(test_session: AsyncSession):
    """Verify that category and issue patterns map dynamically to the correct enterprise teams."""
    team_repo = TeamRepository(test_session)
    await team_repo.seed_initial_taxonomy_if_empty()

    # Venture X Lounge crowding -> Travel & Airport Lounges Team
    team = await team_repo.match_team_for_issue("lounge_access", "lounge_crowding")
    assert team is not None
    assert team.id == "travel_lounges_product"

    # Mobile Face ID failure -> Digital Engineering Mobile
    team = await team_repo.match_team_for_issue("authentication", "biometric_login_failure")
    assert team is not None
    assert team.id == "digital_engineering_mobile"

    # Eno Virtual Card rejection -> Digital AI & Security (Eno)
    team = await team_repo.match_team_for_issue("virtual_cards", "merchant_rejection")
    assert team is not None
    assert team.id == "digital_ai_security"

    # Capital One Café Wi-Fi -> Café & Branch Operations
    team = await team_repo.match_team_for_issue("cafe_experience", "wifi_outage")
    assert team is not None
    assert team.id == "cafe_operations"

    # Shopping extension crash -> Shopping Platform Engineering
    team = await team_repo.match_team_for_issue("browser_extension", "extension_freeze")
    assert team is not None
    assert team.id == "shopping_engineering"

    # Unrecognized issue -> Fallback to Customer Experience
    team = await team_repo.match_team_for_issue("unknown_category", "unprecedented_problem")
    assert team is not None
    assert team.id == "customer_experience"


@pytest.mark.asyncio
async def test_review_persistence_with_analysis_and_vector_embedding(test_session: AsyncSession):
    """Test full review lifecycle: raw review -> AI analysis -> 1536-dim vector embedding."""
    team_repo = TeamRepository(test_session)
    await team_repo.seed_initial_taxonomy_if_empty()
    review_repo = ReviewRepository(test_session)

    # 1. Create Review
    now = datetime.now(timezone.utc)
    review = Review(
        id="c1-rev-001",
        source_id="apple_app_store",
        product_id="venture_x",
        location="Dallas, TX",
        rating=1,
        review_title="DFW Lounge Access Denied",
        review_text="Arrived at the DFW Capital One lounge with my Venture X card, but was turned away due to 2 hour wait time.",
        metadata_json={"app_version": "6.12.0", "device": "iPhone 15 Pro"},
        created_at=now,
    )
    await review_repo.create(review)

    # 2. Attach Structured AI Analysis
    analysis = ReviewAnalysis(
        review_id="c1-rev-001",
        sentiment="negative",
        sentiment_score=-0.91,
        category="lounge_access",
        issue="lounge_crowding_denial",
        severity="high",
        customer_intent="lounge_entry",
        entities=[{"entity": "DFW Lounge", "type": "location"}],
        confidence=0.96,
    )
    await review_repo.save_analysis(analysis)

    # 3. Attach Vector Embedding (1536-dim dummy vector)
    dummy_vector = [0.01 * (i % 10) for i in range(1536)]
    embedding = ReviewEmbedding(
        review_id="c1-rev-001",
        embedding=dummy_vector,
        model_name="text-embedding-3-small",
        dimension=1536,
    )
    await review_repo.save_embedding(embedding)
    await test_session.commit()

    # 4. Fetch and Verify Relationships
    fetched = await review_repo.get_by_id("c1-rev-001")
    assert fetched is not None
    assert fetched.product.name == "Venture X Rewards"
    assert fetched.source.name == "Apple App Store"
    assert fetched.analysis is not None
    assert fetched.analysis.sentiment == "negative"
    assert fetched.analysis.category == "lounge_access"
    assert fetched.embedding is not None
    assert len(fetched.embedding.embedding) == 1536


@pytest.mark.asyncio
async def test_review_filtering_and_pagination(test_session: AsyncSession):
    """Test repository filtering by product, rating, and sentiment."""
    team_repo = TeamRepository(test_session)
    await team_repo.seed_initial_taxonomy_if_empty()
    review_repo = ReviewRepository(test_session)

    now = datetime.now(timezone.utc)
    for i in range(5):
        rev = Review(
            id=f"rev-batch-{i}",
            source_id="google_play_store",
            product_id="banking_360_checking" if i % 2 == 0 else "savor_one",
            rating=1 if i % 2 == 0 else 5,
            review_text=f"Review test feedback message {i}",
            created_at=now,
        )
        await review_repo.create(rev)
    await test_session.commit()

    # Filter for 360 checking
    params = ReviewFilterParams(product_id="banking_360_checking", page=1, page_size=10)
    reviews, total = await review_repo.filter_reviews(params)
    assert total == 3
    assert len(reviews) == 3
    for r in reviews:
        assert r.product_id == "banking_360_checking"


@pytest.mark.asyncio
async def test_issue_cluster_recommendation_and_hitl_approval(test_session: AsyncSession):
    """Test full governance flow: cluster -> recommendation -> analyst approval."""
    team_repo = TeamRepository(test_session)
    await team_repo.seed_initial_taxonomy_if_empty()
    cluster_repo = ClusterRepository(test_session)

    now = datetime.now(timezone.utc)

    # 1. Create Issue Cluster
    cluster = IssueCluster(
        cluster_title="Venture X DFW Lounge Capacity Surges",
        description="High concentration of negative feedback regarding entry wait times at DFW Airport lounge.",
        category="lounge_access",
        affected_product_id="venture_x",
        review_count=42,
        negative_pct=88.5,
        neutral_pct=9.5,
        positive_pct=2.0,
        representative_quotes=["Turned away at DFW lounge", "Wait time exceeded 90 minutes"],
        first_observed_at=now,
        latest_observed_at=now,
    )
    await cluster_repo.create_cluster(cluster)

    # 2. Add Recommendation
    rec = Recommendation(
        cluster_id=cluster.id,
        suggested_team_id="travel_lounges_product",
        observed_evidence="42 customer reviews cite wait times exceeding 90 minutes at DFW lounge during peak morning hours.",
        investigation_hypothesis="DFW flight departures overlap with current guest access policies.",
        recommended_action="Introduce mobile waitlist join in Capital One Mobile app and review partner guest policy.",
        confidence=0.92,
        status="pending_approval",
    )
    test_session.add(rec)
    await test_session.flush()

    # 3. Human Reviewer Approves Recommendation
    approval = Approval(
        recommendation_id=rec.id,
        reviewer_name="Sarah Jenkins (Lead CX Analyst)",
        decision="approved",
        reviewer_notes="Confirmed pattern with airport ops. Proceed with mobile waitlist initiative.",
    )
    rec.status = "approved"
    test_session.add(approval)
    await test_session.commit()

    # 4. Verify Cluster Details
    fetched_cluster = await cluster_repo.get_by_id(cluster.id)
    assert fetched_cluster is not None
    assert len(fetched_cluster.recommendations) == 1
    assert fetched_cluster.recommendations[0].status == "approved"
    assert len(fetched_cluster.recommendations[0].approvals) == 1
    assert fetched_cluster.recommendations[0].approvals[0].decision == "approved"

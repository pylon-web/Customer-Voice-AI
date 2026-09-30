"""Automated tests for Phase 11: Configurable Team Routing Engine."""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.core.database import async_session_factory
from app.models.entities import IssueCluster, Recommendation, Team, TeamRoutingRule, TrendMetric
from app.models.schemas import RoutingEvaluationRequest, TeamRoutingRuleCreate
from app.repositories.team_repo import TeamRepository
from app.repositories.cluster_repo import ClusterRepository
from app.repositories.recommendation_repo import RecommendationRepository
from app.repositories.trend_repo import TrendRepository
from app.services.routing_service import RoutingService


@pytest.mark.asyncio
async def test_team_routing_matches_by_priority():
    """Verify that rules with higher priority are matched first over lower priority rules."""
    async with async_session_factory() as session:
        team_repo = TeamRepository(session)
        await team_repo.seed_initial_taxonomy_if_empty()

        # Add a high-priority rule for "vip lounge" routing to travel_lounges_product
        high_prio_rule = await team_repo.create_routing_rule(
            team_id="travel_lounges_product",
            pattern="vip lounge",
            priority=100,
        )

        # Match against a corpus with "vip lounge"
        matched_team, matched_rule, reason = await team_repo.match_team_rule(
            ["venture_x", "travel", "Overcrowded VIP Lounge in Dallas"]
        )

        assert matched_team.id == "travel_lounges_product"
        assert matched_rule is not None
        assert matched_rule.id == high_prio_rule.id
        assert "Priority 100" in reason


@pytest.mark.asyncio
async def test_routing_service_attaches_sla_playbook_and_review_guidance():
    """Verify that RoutingService assigns SLA, priority, remediation playbooks, and review response advice."""
    now = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)

    async with async_session_factory() as session:
        team_repo = TeamRepository(session)
        await team_repo.seed_initial_taxonomy_if_empty()

        cluster_repo = ClusterRepository(session)
        cluster = IssueCluster(
            id="cluster-route-faceid-001",
            cluster_title="Face ID Authentication Failure After Update",
            affected_product_id="c1_mobile_ios",
            category="biometric_login",
            review_count=35,
            negative_pct=95.0,
            representative_quotes=["App crashes immediately on Face ID."],
            status="active",
            first_observed_at=now - timedelta(days=5),
            latest_observed_at=now,
        )
        await cluster_repo.create_cluster(cluster)

        # Velocity surge trend (z-score = 3.5, WoW = +250%)
        trend_repo = TrendRepository(session)
        metric = TrendMetric(
            cluster_id=cluster.id,
            period_start=now - timedelta(days=7),
            period_end=now,
            current_volume=30,
            previous_volume=5,
            baseline_4wk_avg=5.0,
            wow_change_pct=250.0,
            trend_direction="emerging",
            anomaly_score=3.5,
        )
        await trend_repo.create(metric)
        await session.commit()

        service = RoutingService(session)
        assignment = await service.route_cluster(cluster.id)

        # Verify team assignment
        assert assignment.cluster_id == cluster.id
        assert assignment.matched_team.id in ("digital_engineering_mobile", "digital_eng_mobile")

        # Verify SLA and Priority calculation
        assert assignment.priority_level == "P1_CRITICAL"
        assert assignment.target_sla_hours == 24

        # Verify Playbook
        assert len(assignment.remediation_playbook) >= 3
        assert any("Crashlytics" in s for s in assignment.remediation_playbook)

        # Verify Review Response Guidance
        assert "App Store / Play Store Response Guidance:" in assignment.review_response_guidance
        assert "hotfix patch" in assignment.review_response_guidance


@pytest.mark.asyncio
async def test_routing_fallback_to_customer_experience():
    """Verify that unfamiliar issue patterns gracefully fallback to Customer Experience team."""
    async with async_session_factory() as session:
        team_repo = TeamRepository(session)
        await team_repo.seed_initial_taxonomy_if_empty()

        # Unmatched generic query
        matched_team, matched_rule, reason = await team_repo.match_team_rule(
            ["general_inquiry", "misc", "Customer wanted to know branch holiday hours"]
        )

        assert matched_team.id == "customer_experience"
        assert matched_rule is None
        assert "Customer Experience fallback" in reason


def test_routing_rest_api_endpoints(client: TestClient):
    """Test REST API endpoints for teams, dynamic rule management, and evaluation."""
    # 1. List all business teams via GET /api/v1/teams
    teams_res = client.get("/api/v1/teams")
    assert teams_res.status_code == 200
    teams_data = teams_res.json()
    assert len(teams_data) >= 7

    # 2. Get single team by ID or alias via GET /api/v1/teams/{team_id}
    team_res = client.get("/api/v1/teams/digital_eng_mobile")
    assert team_res.status_code == 200
    assert "Digital Engineering" in team_res.json()["name"]

    # 3. Create a dynamic custom routing rule via POST /api/v1/routing/rules
    new_rule_payload = {
        "team_id": "cafe_operations",
        "pattern": "cold espresso",
        "priority": 75,
    }
    create_rule_res = client.post("/api/v1/routing/rules", json=new_rule_payload)
    assert create_rule_res.status_code == 201
    rule_data = create_rule_res.json()
    assert rule_data["pattern"] == "cold espresso"
    assert rule_data["priority"] == 75
    rule_id = rule_data["id"]

    # 4. Evaluate hypothetical routing using the newly created rule
    eval_payload = {
        "product_id": "c1_cafe",
        "category": "beverage",
        "issue_text": "Ambassador served cold espresso twice this week.",
        "severity": "medium",
        "anomaly_score": 1.5,
    }
    eval_res = client.post("/api/v1/routing/evaluate", json=eval_payload)
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["matched_team"]["id"] in ("cafe_operations", "cafe_ops")
    assert eval_data["matched_pattern"] == "cold espresso"
    assert "Café" in eval_data["review_response_guidance"] or "Peet" in eval_data["review_response_guidance"]

    # 5. Delete the custom routing rule via DELETE /api/v1/routing/rules/{rule_id}
    del_res = client.delete(f"/api/v1/routing/rules/{rule_id}")
    assert del_res.status_code == 204

    # 6. Verify rule deletion
    del_verify_res = client.delete(f"/api/v1/routing/rules/{rule_id}")
    assert del_verify_res.status_code == 404

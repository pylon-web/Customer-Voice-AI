"""Automated tests for Phase 10: Root Cause / Investigation Agent (Multi-Agent LangGraph State Graph)."""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.core.database import async_session_factory
from app.models.entities import IssueCluster, Recommendation, Approval, Team
from app.agents.investigation_graph import (
    investigation_graph,
    InvestigationState,
    compliance_reflector_node,
    CERTAINTY_PHRASES,
)
from app.repositories.cluster_repo import ClusterRepository
from app.repositories.recommendation_repo import RecommendationRepository
from app.services.investigation_service import InvestigationService


def test_langgraph_investigation_state_machine_execution():
    """Verify that the LangGraph state machine executes through all nodes and produces compliant outputs."""
    initial_state: InvestigationState = {
        "cluster_id": "cluster-mobile-faceid-test",
        "cluster_title": "Face ID Biometric Login Crash on iOS 18",
        "affected_product_id": "c1_mobile_ios",
        "category": "technical_issue",
        "review_count": 42,
        "negative_pct": 97.6,
        "representative_quotes": [
            "Face ID crashes the mobile banking app instantly on launch.",
            "App closes immediately when biometric prompt displays.",
        ],
        "iteration_count": 0,
    }

    config = {"configurable": {"thread_id": "thread-test-faceid-001"}}
    final_state = investigation_graph.invoke(initial_state, config=config)

    # 1. Verify Node 1: Observed Evidence (strictly observational)
    evidence = final_state["observed_evidence"]
    assert "42 customer reports" in evidence
    assert "97.6% negative sentiment" in evidence
    assert "Face ID crashes the mobile banking app" in evidence

    # 2. Verify Node 2: Investigation Hypothesis (tentative framing)
    hypothesis = final_state["investigation_hypothesis"]
    assert hypothesis.lower().startswith("hypothesis:")
    assert any(w in hypothesis.lower() for w in ["investigate", "potential", "verify whether"])
    # Crucial Guardrail: Must NOT assert definitive certainty
    assert not any(phrase in hypothesis.lower() for phrase in CERTAINTY_PHRASES)

    # 3. Verify Node 3: Action Plan Synthesizer
    assert final_state["suggested_team_id"] == "digital_eng_mobile"
    assert "Crashlytics" in final_state["recommended_action"] or "biometric" in final_state["recommended_action"].lower()
    assert 0.0 <= final_state["confidence"] <= 1.0

    # 4. Verify Node 4: Compliance Reflector
    assert final_state["compliance_passed"] is True
    assert "Responsible AI guardrail" in final_state["reflection_notes"]

    # 5. Verify Node 5: HITL Checkpoint
    assert final_state["status"] == "pending_approval"


def test_compliance_reflector_rejects_and_reframes_certainty_violations():
    """Verify that the Compliance Reflector rejects definitive certainty phrasing and enforces tentative framing."""
    non_compliant_state: InvestigationState = {
        "cluster_id": "violating-cluster-123",
        "cluster_title": "Eno Virtual Card Rejection",
        "observed_evidence": "15 customers had cards declined.",
        "investigation_hypothesis": "The exact root cause is a database bug that crashed the gateway.",
        "iteration_count": 0,
    }

    reflection_result = compliance_reflector_node(non_compliant_state)

    assert reflection_result["compliance_passed"] is False
    assert "enforced tentative investigative framing" in reflection_result["reflection_notes"]
    assert "Hypothesis: Investigate potential" in reflection_result["investigation_hypothesis"]


@pytest.mark.asyncio
async def test_investigation_service_persists_recommendation():
    """Verify InvestigationService runs LangGraph and saves recommendation to database."""
    now = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)

    async with async_session_factory() as session:
        cluster_repo = ClusterRepository(session)
        cluster = IssueCluster(
            id="cluster-lounge-investigate-001",
            cluster_title="DFW Lounge Overcrowding Surge",
            affected_product_id="venture_x",
            category="travel_benefits",
            review_count=25,
            negative_pct=92.0,
            representative_quotes=["Lounge had a 50-minute line."],
            status="active",
            first_observed_at=now - timedelta(days=14),
            latest_observed_at=now,
        )
        await cluster_repo.create_cluster(cluster)
        await session.commit()

        service = InvestigationService(session)
        rec = await service.investigate_cluster(cluster.id)

        assert rec.id is not None
        assert rec.cluster_id == cluster.id
        assert rec.suggested_team_id == "travel_lounges_prod"
        assert rec.status == "pending_approval"
        assert "Observed Evidence" in rec.observed_evidence
        assert "Hypothesis:" in rec.investigation_hypothesis
        assert rec.confidence > 0.8


@pytest.mark.asyncio
async def test_hitl_approval_and_modification_workflow():
    """Verify human reviewer approval and modification workflow with audit logging."""
    now = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)

    async with async_session_factory() as session:
        cluster_repo = ClusterRepository(session)
        cluster = IssueCluster(
            id="cluster-hitl-test-001",
            cluster_title="Shopping Browser Extension Freeze",
            affected_product_id="shopping_extension",
            category="technical_issue",
            review_count=10,
            negative_pct=90.0,
            representative_quotes=["Browser freezes during coupon search."],
            status="active",
            first_observed_at=now - timedelta(days=7),
            latest_observed_at=now,
        )
        await cluster_repo.create_cluster(cluster)
        await session.commit()

        service = InvestigationService(session)
        rec = await service.investigate_cluster(cluster.id)

        # 1. Reviewer modifies action and approves
        modified_rec, approval = await service.record_human_decision(
            recommendation_id=rec.id,
            reviewer_name="Sarah Connor (Principal SRE)",
            decision="modified",
            reviewer_notes="Approved with specific DOM throttling instructions.",
            modified_action="Throttle mutation observer to 250ms interval and release patch v2.4.2.",
        )

        assert modified_rec.status == "modified"
        assert "Throttle mutation observer" in modified_rec.recommended_action
        assert approval.reviewer_name == "Sarah Connor (Principal SRE)"
        assert approval.decision == "modified"
        assert approval.reviewer_notes == "Approved with specific DOM throttling instructions."


def test_investigations_api_endpoints(client: TestClient):
    """Test REST API endpoints for triggering investigations, listing, and recording HITL decisions."""
    # 1. First ensure an active cluster exists
    run_res = client.post("/api/v1/clusters/run", json={"eps": 0.45, "min_samples": 3})
    assert run_res.status_code == 200
    cluster_ids = run_res.json()["cluster_ids"]
    assert len(cluster_ids) >= 1
    sample_cluster_id = cluster_ids[0]

    # 2. Trigger LangGraph investigation via POST /api/v1/investigations/{cluster_id}
    inv_res = client.post(f"/api/v1/investigations/{sample_cluster_id}")
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["cluster_id"] == sample_cluster_id
    assert inv_data["status"] == "pending_approval"
    assert "observed_evidence" in inv_data
    assert "investigation_hypothesis" in inv_data
    assert "suggested_team_id" in inv_data

    rec_id = inv_data["id"]

    # 3. Get investigation via GET /api/v1/investigations/{cluster_id}
    get_res = client.get(f"/api/v1/investigations/{sample_cluster_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == rec_id

    # 4. List recommendations via GET /api/v1/recommendations
    list_res = client.get("/api/v1/recommendations?page=1&page_size=10")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(r["id"] == rec_id for r in list_data["items"])

    # 5. Record HITL decision via POST /api/v1/recommendations/{id}/decision
    decision_payload = {
        "reviewer_name": "Alex Mercer (Operations Lead)",
        "decision": "approved",
        "reviewer_notes": "Hypothesis validated against mobile crash telemetries. Approved for sprint backlog.",
    }
    decision_res = client.post(f"/api/v1/recommendations/{rec_id}/decision", json=decision_payload)
    assert decision_res.status_code == 200
    decision_data = decision_res.json()
    assert decision_data["status"] == "approved"
    assert len(decision_data["approvals"]) >= 1
    assert decision_data["approvals"][0]["reviewer_name"] == "Alex Mercer (Operations Lead)"

    # 6. Test 404 for unknown cluster
    unknown_res = client.post("/api/v1/investigations/non-existent-cluster-999")
    assert unknown_res.status_code == 404

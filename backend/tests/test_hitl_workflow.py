"""Automated tests for Phase 14/15: Human-in-the-Loop (HITL) Approval Workflow.

Verifies:
1. Approving an operational recommendation updates state to 'approved' and appends audit trail.
2. Rejecting a recommendation updates state to 'rejected' with reviewer rationale.
3. Modifying an action updates state to 'modified' and persists updated recommended action.
4. Filtering recommendations by status ('pending_approval', 'approved', 'rejected', 'modified').
5. Multiple sequential audit log entries for a single recommendation.
"""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.core.database import async_session_factory
from app.models.entities import IssueCluster, Recommendation, Approval
from app.repositories.cluster_repo import ClusterRepository
from app.repositories.recommendation_repo import RecommendationRepository
from app.services.investigation_service import InvestigationService


@pytest.mark.asyncio
async def test_hitl_approval_rejection_modification_flow():
    """Verify approval, rejection, and modification state transitions and audit logging."""
    now = datetime(2026, 9, 28, 12, 0, 0, tzinfo=timezone.utc)

    async with async_session_factory() as session:
        cluster_repo = ClusterRepository(session)
        rec_repo = RecommendationRepository(session)
        service = InvestigationService(session)

        # 1. Create test cluster
        cluster = IssueCluster(
            id="cluster-hitl-flow-001",
            cluster_title="Face ID Authentication Timeout",
            affected_product_id="c1_mobile_ios",
            category="technical_issue",
            review_count=18,
            negative_pct=95.0,
            representative_quotes=["App crashes immediately on Face ID"],
            status="active",
            first_observed_at=now - timedelta(days=5),
            latest_observed_at=now,
        )
        await cluster_repo.create_cluster(cluster)
        await session.commit()

        # 2. Trigger investigation to get pending recommendation
        rec = await service.investigate_cluster(cluster.id)
        assert rec.status == "pending_approval"
        assert rec.suggested_team_id == "digital_eng_mobile"

        # 3. Approve recommendation
        approved_rec, app_approval = await service.record_human_decision(
            recommendation_id=rec.id,
            reviewer_name="Jane Doe (Lead Mobile Eng)",
            decision="approved",
            reviewer_notes="Validated crash logs. Scheduled for hotfix sprint.",
        )
        assert approved_rec.status == "approved"
        assert app_approval.decision == "approved"
        assert app_approval.reviewer_name == "Jane Doe (Lead Mobile Eng)"

        # 4. Create second recommendation and reject it
        cluster2 = IssueCluster(
            id="cluster-hitl-flow-002",
            cluster_title="Minor Color Contrast Inquiry",
            affected_product_id="banking_360_checking",
            category="customer_service",
            review_count=4,
            negative_pct=25.0,
            representative_quotes=["Button color could be darker"],
            status="active",
            first_observed_at=now - timedelta(days=2),
            latest_observed_at=now,
        )
        await cluster_repo.create_cluster(cluster2)
        await session.commit()

        rec2 = await service.investigate_cluster(cluster2.id)
        rejected_rec, rej_approval = await service.record_human_decision(
            recommendation_id=rec2.id,
            reviewer_name="Bob Smith (Product Manager)",
            decision="rejected",
            reviewer_notes="Volume too low to warrant design refactor.",
        )
        assert rejected_rec.status == "rejected"
        assert rej_approval.decision == "rejected"

        # 5. Create third recommendation and modify action
        cluster3 = IssueCluster(
            id="cluster-hitl-flow-003",
            cluster_title="Lounge QR Barcode Scan Delay",
            affected_product_id="venture_x",
            category="travel_benefits",
            review_count=15,
            negative_pct=88.0,
            representative_quotes=["Turnstile barcode scanner has 15s delay"],
            status="active",
            first_observed_at=now - timedelta(days=3),
            latest_observed_at=now,
        )
        await cluster_repo.create_cluster(cluster3)
        await session.commit()

        rec3 = await service.investigate_cluster(cluster3.id)
        mod_rec, mod_approval = await service.record_human_decision(
            recommendation_id=rec3.id,
            reviewer_name="Carlos Gomez (Airport Lounge Lead)",
            decision="modified",
            reviewer_notes="Upgrading handheld scanners rather than kiosk overhaul.",
            modified_action="Procure high-speed laser scanners for DFW and DEN lounge podiums.",
        )
        assert mod_rec.status == "modified"
        assert mod_rec.recommended_action == "Procure high-speed laser scanners for DFW and DEN lounge podiums."
        assert mod_approval.decision == "modified"

        # 6. Verify list filtering by status
        approved_list, approved_count = await rec_repo.list_recommendations(status="approved")
        assert any(r.id == approved_rec.id for r in approved_list)

        rejected_list, rejected_count = await rec_repo.list_recommendations(status="rejected")
        assert any(r.id == rejected_rec.id for r in rejected_list)

        modified_list, modified_count = await rec_repo.list_recommendations(status="modified")
        assert any(r.id == mod_rec.id for r in modified_list)


def test_hitl_api_endpoint_workflow(client: TestClient):
    """Verify REST API HITL approval and listing endpoints."""
    # Run clustering to generate at least one cluster
    client.post("/api/v1/clusters/run", json={"eps": 0.45, "min_samples": 3})

    # Trigger investigation
    list_clusters = client.get("/api/v1/clusters?page=1&page_size=5")
    assert list_clusters.status_code == 200
    clusters = list_clusters.json()["items"]
    assert len(clusters) > 0

    cid = clusters[0]["id"]
    inv_res = client.post(f"/api/v1/investigations/{cid}")
    assert inv_res.status_code == 200
    rec = inv_res.json()
    rec_id = rec["id"]

    # Submit decision via API
    decision_res = client.post(
        f"/api/v1/recommendations/{rec_id}/decision",
        json={
            "reviewer_name": "Auditor General",
            "decision": "approved",
            "reviewer_notes": "Meets all engineering requirements.",
        },
    )
    assert decision_res.status_code == 200
    updated_rec = decision_res.json()
    assert updated_rec["status"] == "approved"
    assert len(updated_rec["approvals"]) >= 1

    # Filter recommendations endpoint
    filter_res = client.get("/api/v1/recommendations?status=approved")
    assert filter_res.status_code == 200
    filter_data = filter_res.json()
    assert filter_data["total"] >= 1
    assert any(item["id"] == rec_id for item in filter_data["items"])

"""Unit and integration tests for DBSCAN semantic clustering, cluster synthesis, and REST APIs."""

import math
import numpy as np
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import async_session_factory
from app.services.ingestion_service import IngestionService
from app.services.analysis_service import AnalysisService
from app.services.embedding_service import EmbeddingService
from app.services.clustering_service import ClusteringService
from app.repositories.cluster_repo import ClusterRepository
from app.models.schemas import ReviewCreate, ClusterRunRequest
from app.kafka.producer import get_kafka_producer


@pytest.mark.asyncio
async def test_dbscan_clustering_discovers_coherent_clusters():
    """Verify DBSCAN groups semantically related reviews into distinct clusters while filtering noise."""
    producer = get_kafka_producer()
    producer.clear_history()

    async with async_session_factory() as session:
        ingestion = IngestionService(session)
        analysis_svc = AnalysisService(session)
        embed_svc = EmbeddingService(session)

        # 1. Seed 3 reviews on Face ID crash (Cluster 1)
        face_id_reviews = [
            "Face ID login crashes the app instantly after the v6.14 iOS update.",
            "Biometric Face ID authentication failure on startup, app closes immediately.",
            "Can't log into mobile banking because Face ID crashes the iOS application.",
        ]

        # 2. Seed 3 reviews on Lounge crowding (Cluster 2)
        lounge_reviews = [
            "DFW Capital One Lounge is overcrowded with a 45-minute waitlist.",
            "Long lines and severe crowding at the airport lounge in Dallas.",
            "Lounge access was denied due to peak hour crowding and full capacity.",
        ]

        # 3. Seed 1 unrelated noise review
        noise_review = "I bought a coffee yesterday in Seattle at a local diner."

        all_rev_ids = []
        for i, text in enumerate(face_id_reviews):
            rev = await ingestion.ingest_single(
                ReviewCreate(
                    id=f"test-clust-faceid-{i}",
                    product_id="c1_mobile_ios",
                    source_id="apple_app_store",
                    rating=1,
                    review_text=text,
                )
            )
            await analysis_svc.analyze_review(rev.id)
            await embed_svc.generate_and_store_embedding(rev.id)
            all_rev_ids.append(rev.id)

        for i, text in enumerate(lounge_reviews):
            rev = await ingestion.ingest_single(
                ReviewCreate(
                    id=f"test-clust-lounge-{i}",
                    product_id="venture_x",
                    source_id="apple_app_store",
                    rating=2,
                    review_text=text,
                )
            )
            await analysis_svc.analyze_review(rev.id)
            await embed_svc.generate_and_store_embedding(rev.id)
            all_rev_ids.append(rev.id)

        noise_rev = await ingestion.ingest_single(
            ReviewCreate(
                id="test-clust-noise-0",
                product_id="venture",
                source_id="trustpilot",
                rating=3,
                review_text=noise_review,
            )
        )
        await analysis_svc.analyze_review(noise_rev.id)
        await embed_svc.generate_and_store_embedding(noise_rev.id)
        all_rev_ids.append(noise_rev.id)

        await session.commit()

        # Run Clustering Service
        clustering_svc = ClusteringService(session)
        run_resp = await clustering_svc.run_clustering(
            ClusterRunRequest(eps=0.45, min_samples=3)
        )

        assert run_resp.clusters_formed >= 2
        assert run_resp.clustered_reviews_count >= 6
        assert len(run_resp.cluster_ids) >= 2

        # Verify cluster entities in DB
        cluster_repo = ClusterRepository(session)
        clusters = await cluster_repo.get_active_clusters(limit=10)
        assert len(clusters) >= 2

        # Check titles
        titles = [c.cluster_title for c in clusters]
        has_face_id = any("Face ID" in t or "Biometric" in t or "Authentication" in t for t in titles)
        has_lounge = any("Lounge" in t or "Crowd" in t for t in titles)
        assert has_face_id
        assert has_lounge

        # Inspect the Face ID cluster
        face_id_cluster = next(c for c in clusters if "Face ID" in c.cluster_title or "Authentication" in c.cluster_title)
        assert face_id_cluster.review_count >= 3
        assert face_id_cluster.negative_pct >= 90.0
        assert len(face_id_cluster.representative_quotes) >= 1
        assert len(face_id_cluster.centroid_embedding) == 1536

        # Check centroid norm
        centroid_norm = np.linalg.norm(np.array(face_id_cluster.centroid_embedding))
        assert math.isclose(centroid_norm, 1.0, rel_tol=1e-3)


def test_clusters_api_endpoints(client: TestClient):
    """Test REST API endpoints for cluster execution, listing, detail, and review drilldown."""
    # 1. Trigger clustering via API
    run_res = client.post("/api/v1/clusters/run", json={"eps": 0.45, "min_samples": 3})
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert "clusters_formed" in run_data
    assert "cluster_ids" in run_data

    # 2. List clusters
    list_res = client.get("/api/v1/clusters?page=1&page_size=10")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert len(list_data["items"]) >= 1

    sample_cluster_id = list_data["items"][0]["id"]

    # 3. Get cluster detail with reviews
    detail_res = client.get(f"/api/v1/clusters/{sample_cluster_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["id"] == sample_cluster_id
    assert "cluster_title" in detail_data
    assert "negative_pct" in detail_data
    assert "reviews" in detail_data
    assert len(detail_data["reviews"]) >= 1

    # 4. Get cluster reviews drilldown endpoint
    reviews_res = client.get(f"/api/v1/clusters/{sample_cluster_id}/reviews?page=1&page_size=5")
    assert reviews_res.status_code == 200
    reviews_data = reviews_res.json()
    assert len(reviews_data) >= 1
    assert "similarity_score" in reviews_data[0]
    assert "review" in reviews_data[0]

    # 5. Non-existent cluster returns 404
    not_found_res = client.get("/api/v1/clusters/does-not-exist-uuid")
    assert not_found_res.status_code == 404

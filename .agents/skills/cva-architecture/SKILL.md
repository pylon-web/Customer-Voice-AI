---
name: cva-architecture
description: Complete architecture specification, pipeline flow, Kafka event streaming, database schemas, and service contracts for the Customer Voice AI platform.
---

# Customer Voice AI — System Architecture Specification

This skill provides the architectural blueprint for the Customer Voice AI enterprise platform. Activate this skill whenever designing, modifying, or testing components across the monorepo.

## 1. System Pipeline Flow

The platform transforms raw multi-source customer reviews into routed executive intelligence through an asynchronous, event-driven pipeline:

```
[Customer Reviews]
 (App Store, Play Store, Google Places, Yelp, Synthetic)
       │
       ▼
 [Review Ingestion API] ──► [Database: PostgreSQL + pgvector]
       │
       ▼
 [Kafka: review.created] ──► [ReviewWorker]
       │
       ▼
 [Phase 6: AI Review Analysis Agent]
 (Structured JSON extraction: sentiment, category, issue, severity)
       │
       ▼
 [Phase 7: Vector Embeddings Engine] (1536-dim text-embedding-3-small / pgvector)
       │
       ▼
 [Phase 8: Semantic Clustering] (DBSCAN / HDBSCAN issue grouping)
       │
       ▼
 [Phase 9: Trend & Velocity Anomaly Detection] (WoW % velocity & z-scores)
       │
       ▼
 [Phase 10: Root Cause / Investigation Agent]
 (Observed Evidence vs. Investigation Hypotheses)
       │
       ▼
 [Phase 11: Configurable Team Routing Engine] (Database-driven rules)
       │
       ▼
 [Phase 14: Human-in-the-Loop Approval Queue]
       │
       ▼
 [Phase 12: Weekly Executive Intelligence Briefing] (JSON / MD / PDF)
       │
       ▼
 [Phase 13: React Executive Dashboard]
```

## 2. Monorepo Directory Structure

```
Customer-Voice-AI/
├── backend/
│   ├── alembic/                # Database schema migrations
│   ├── app/
│   │   ├── api/v1/             # REST endpoints (health, reviews, clusters, trends, reports)
│   │   ├── core/               # Configuration, database engine, logging, errors
│   │   ├── kafka/              # Kafka producer, consumer, and event schemas
│   │   ├── models/             # SQLAlchemy entities, seed taxonomy, Pydantic schemas
│   │   ├── repositories/       # Data access layer (Review, Cluster, Team repos)
│   │   ├── services/           # Business logic (Ingestion, Analysis, Clustering, Trends)
│   │   └── workers/            # Asynchronous background workers (ReviewWorker)
│   └── tests/                  # Pytest automated test suite
├── frontend/                   # React 18 + Vite + Tailwind + Recharts dashboard
├── data/
│   ├── synthetic/              # 10k review generator & temporal anomaly injector
│   └── real/                   # Public App Store, Play Store, and curated reviews
├── infrastructure/
│   ├── docker/                 # Container Dockerfiles
│   └── kubernetes/             # Production deployment manifests
├── docs/                       # Architectural documentation
└── scripts/                    # CLI tools & background daemon runners
```

## 3. Kafka Messaging Architecture

### Topic Conventions
* `review.created`: Published immediately upon review persistence in `POST /api/v1/reviews`.
* `review.analyzed`: Published after AI extracts structured sentiment, category, and issue.
* `review.embedded`: Published after 1536-dim vector embedding is computed and indexed.
* `issue.detected`: Published when cluster volume accelerates above baseline threshold.
* `report.generated`: Published when weekly executive intelligence summary is produced.

### Offline & Local Resilience
`KAFKA_ENABLE_FALLBACK_SYNC=true` in `app.core.config`:
* If Kafka broker is unreachable or offline, `KafkaProducerService` and `KafkaConsumerService` seamlessly buffer and dispatch events using an in-memory `asyncio.Queue`.
* Automated test suites (`pytest backend/tests`) run with zero external broker dependencies in < 0.5s.

## 4. Database Schema & Vector Engine (Dual-Database Strategy)

The platform supports a robust **Dual-Database Strategy** to enable both production-grade vector search and zero-dependency local development:

### 1. Enterprise Production Mode (PostgreSQL 16 + pgvector)
* **Engine:** PostgreSQL 16 with `pgvector` extension.
* **Vector Engine:** 1536-dimensional OpenAI vector embeddings indexed with HNSW / IVFFlat for high-speed approximate nearest neighbor (ANN) retrieval.
* **Connection String:** `postgresql+asyncpg://customervoice:customervoice_secret@localhost:5432/customer_voice_ai`
* **When Active:** Production Docker deployments (`docker-compose.yml`), Kubernetes clusters, or local environments with running PostgreSQL.

### 2. Zero-Dependency Local Dev Mode (SQLite Fallback)
* **Engine:** SQLite 3 via `aiosqlite` (`cva_dev.db`).
* **Adaptive Typing (`VectorType`):** Emits native `pgvector.sqlalchemy.Vector(1536)` on PostgreSQL in production, while automatically falling back to JSON serialization and NumPy cosine similarity on SQLite.
* **Connection String:** `sqlite+aiosqlite:///./cva_dev.db`
* **When Active:** Enabled by default when Docker/PostgreSQL is offline or uninstalled, allowing instant local UI testing and development with pre-seeded data without external service dependencies.

### 3. Core Database Tables (15 Tables)
* `products`, `sources`, `teams`, `team_routing_rules`, `users`
* `reviews`, `review_analyses`, `review_embeddings`
* `issue_clusters`, `cluster_reviews`
* `trend_metrics`
* `recommendations`, `approvals`
* `reports`, `report_issues`

### 4. Database Inspection Tool
* `make inspect-db` (or `python3 scripts/inspect_db.py <table_name>`): Inspects table schemas, row counts, and live records across all 15 tables.

## 5. Technology Stack

* **Backend:** Python 3.10+, FastAPI, SQLAlchemy 2.0 (asyncio + asyncpg), Alembic, Pydantic v2, aiokafka.
* **Database:** PostgreSQL 16, pgvector, aiosqlite (in-memory test engine).
* **Streaming:** Apache Kafka (KRaft mode).
* **AI / ML:** OpenAI GPT-4o-mini, text-embedding-3-small, scikit-learn (DBSCAN), numpy, pandas.
* **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Lucide React, Recharts.

---
name: cva-phase-workflow
description: Step-by-step incremental phase delivery protocol, automated test verification procedures, and phase-by-phase roadmap for Customer Voice AI.
---

# Customer Voice AI — Incremental Phase Delivery Protocol

This skill dictates the mandatory workflow for developing and delivering each phase of the Customer Voice AI platform.

## 1. Non-Negotiable Incremental Delivery Protocol

Every development phase must strictly adhere to the following 8-step protocol. **Never skip steps or batch multiple phases together without explicit user confirmation.**

```
1. Explain Goal & Architectural Context
          │
          ▼
2. List Files to Create / Modify
          │
          ▼
3. Detail Design Rationale & Trade-offs
          │
          ▼
4. Implement Code
          │
          ▼
5. Provide Exact Run Commands
          │
          ▼
6. Run & Verify Automated Tests (.venv/bin/pytest backend/tests)
          │
          ▼
7. Summarize Verification & Deliverables
          │
          ▼
8. HALT and request user approval before proceeding to next phase
```

## 2. Test Verification Standards

* **Virtual Environment:** Always execute with the project's dedicated virtual environment:
  ```bash
  .venv/bin/pytest backend/tests
  ```
* **Zero Regressions:** Every phase must add automated tests for its new functionality while ensuring 100% of existing tests continue to pass.
* **Speed:** Unit and integration tests must run in < 1 second using SQLite and in-memory Kafka fallback.

## 3. 17-Phase Implementation Roadmap & Status

| Phase | Phase Name | Status | Key Deliverable |
| :---: | :--- | :---: | :--- |
| **1** | Architecture & Monorepo Setup | ✅ **Complete** | Monorepo layout, FastAPI app, CORS, correlation middleware, Docker Compose |
| **2** | Database Schema & Relational Models | ✅ **Complete** | SQLAlchemy async entities, adaptive `VectorType`, taxonomy seeds, Alembic |
| **3** | Synthetic Review Generator | ✅ **Complete** | 10k reviews, 5 temporal anomalies (Lounge spike, Face ID crash, Eno surge) |
| **4** | Review Ingestion API & Real Data | ✅ **Complete** | Single, batch, CSV/JSON file upload, filters, App Store & Play Store scraper |
| **5** | Event-Driven Kafka Pipeline | ✅ **Complete** | `KafkaProducerService`, `ReviewWorker`, in-memory fallback, `review.created` |
| **6** | AI Review Analysis Agent | ✅ **Complete** | Structured JSON extraction (sentiment, category, issue, severity), Mock/OpenAI |
| **7** | Vector Embeddings & Semantic Search | ✅ **Complete** | 1536-dim embeddings, pgvector cosine search endpoint |
| **8** | Semantic Clustering Pipeline | ✅ **Complete** | DBSCAN unsupervised clustering, centroid calculation, cluster titling |
| **9** | Trend & Velocity Anomaly Detection | ✅ **Complete** | Rolling 4-week baseline, WoW % change, anomaly z-scores |
| **10** | Root Cause / Investigation Agent | ✅ **Complete** | LangGraph multi-agent reflection graph (Evidence vs. Hypothesis, HITL interrupt) |
| **11** | Configurable Team Routing Engine | ✅ **Complete** | Database-driven routing rules to 7 generic business teams |
| **12** | Weekly Intelligence Report Generator | ✅ **Complete** | Executive brief generation (JSON, Markdown, PDF) |
| **13** | React Dashboard & Visualization | ✅ **Complete** | React 18, Vite, Tailwind, Recharts (KPIs, explorer, clusters, trends, reports) |
| **14** | Human-in-the-Loop Approval Workflow | ✅ **Complete** | Recommendation approval/rejection/modification audit trail, SLA tracking, batch decisions, Kafka events |
| **15** | Unit, Integration & AI Evaluation | ✅ **Complete** | End-to-end integration tests & AI benchmark vs. 10k ground truth |
| **16** | Structured Observability & Health Probes | ✅ **Complete** | Prometheus `/metrics`, deep `/api/v1/health/ready` probe |
| **17** | Containerization & Kubernetes | ⏳ **Next** | Multi-stage Dockerfiles, Kubernetes manifests, Helm charts |


# VoiceIQ — Enterprise Customer Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791?style=flat&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Kafka](https://img.shields.io/badge/Apache%20Kafka-KRaft-231F20?style=flat&logo=apachekafka&logoColor=white)](https://kafka.apache.org)
[![React](https://img.shields.io/badge/React-18%20%7C%20TypeScript-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)

An enterprise-grade Customer Voice Intelligence Platform that ingests multi-channel customer reviews, performs deep AI semantic analysis, groups similar complaints using vector embeddings, detects emerging trends against statistical baselines, suggests investigation paths, routes to business teams, and compiles weekly executive intelligence briefs.

---

## 🏛️ System Architecture

```
Raw Review → AI Analysis → Vector Embedding → Semantic Clustering → Trend Detection → Root Cause Agent → Team Routing → Human Approval → Weekly Intelligence Report
```

See [docs/architecture.md](docs/architecture.md) for detailed architecture blueprints, data flow sequence diagrams, and domain models.

---

## 📂 Repository Structure

```
customer-voice-ai/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST endpoints (health, reviews, clusters, trends, reports)
│   │   ├── core/            # Config, structured logging, error handling
│   │   ├── models/          # Domain models, database schemas, Pydantic DTOs
│   │   ├── repositories/    # Database persistence & pgvector queries
│   │   ├── services/        # Ingestion, clustering, trend detection logic
│   │   ├── agents/          # LLM review analyzer, root cause & recommendation agents
│   │   ├── kafka/           # Kafka producers, consumers, and topic schemas
│   │   ├── workers/         # Background streaming consumer workers
│   │   └── main.py          # FastAPI application entrypoint
│   └── tests/               # Unit, integration, and AI evaluation tests
├── frontend/                # React 18 + TypeScript + Vite + Tailwind CSS dashboard
├── data/
│   └── synthetic/           # Synthetic multi-product dataset generators (10k+ reviews)
├── infrastructure/
│   ├── docker/              # Dockerfiles for backend and frontend
│   └── kubernetes/          # K8s Deployment and Service manifests
├── docs/                    # Architecture, API specifications, runbooks
├── scripts/                 # Setup and run scripts
├── docker-compose.yml       # Local orchestration (PostgreSQL + pgvector, Kafka KRaft, Backend, Frontend)
├── .env.example             # Documented environment configuration template
└── Makefile                 # Developer build and test shortcuts
```

---

## 🚀 Quick Start

### 1. Prerequisites
* Python 3.10+
* Node.js 18+
* Docker & Docker Compose (optional for standalone local dev)

### 2. Local Environment Setup
```bash
# Clone and enter the repository
cd Customer-Voice-AI

# Bootstrap configuration (.env)
./scripts/setup.sh
```

### 3. Quick Start Options (Dual-Database Strategy)

The platform supports two runtime modes:

#### Mode A: Zero-Dependency Standalone Mode (Fastest — SQLite)
Runs instantly out-of-the-box with pre-seeded Capital One reviews and issue clusters, requiring **no Docker or external PostgreSQL**:
```bash
# Setup environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt

# Terminal 1: Start Backend (FastAPI on :8000)
make run

# Terminal 2: Start Frontend (React/Vite on :5173)
make run-frontend

# Inspect Database (View all 15 tables, schemas, and records)
make inspect-db
```
Access dashboard at [http://localhost:5173](http://localhost:5173) or [http://localhost:8000](http://localhost:8000).

#### Mode B: Full Enterprise Production Mode (PostgreSQL 16 + pgvector + Kafka)
Runs the full containerized stack with native `pgvector` indexing and Apache Kafka KRaft:
```bash
make docker-up
```
Services:
* **Frontend Dashboard:** [http://localhost:5173](http://localhost:5173)
* **Backend API Docs (Swagger):** [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
* **Kafka UI:** [http://localhost:8080](http://localhost:8080)
* **PostgreSQL (pgvector):** `localhost:5432`

---

## 🗺️ Implementation Roadmap

- [x] **Phase 1: Architecture & Repository Setup**
- [x] **Phase 2: Database Schema & Relational Models (PostgreSQL + pgvector)**
- [x] **Phase 3: Synthetic Review Generator (10,000+ realistic reviews with temporal patterns)**
- [x] **Phase 4: Review Ingestion API**
- [x] **Phase 5: Event-Driven Kafka Pipeline**
- [x] **Phase 6: AI Review Analysis Agent (Structured JSON Extraction)**
- [x] **Phase 7: Vector Embeddings & pgvector Semantic Search**
- [x] **Phase 8: Semantic Clustering Pipeline**
- [x] **Phase 9: Trend & Velocity Anomaly Detection**
- [x] **Phase 10: Root Cause / Investigation Agent (Evidence vs. Hypothesis)**
- [x] **Phase 11: Configurable Team Routing Engine**
- [x] **Phase 12: Weekly Intelligence Report Generator**
- [x] **Phase 13: React Dashboard & Visualization**
- [x] **Phase 14: Human-in-the-Loop Approval Workflow**
- [x] **Phase 15: Unit, Integration & AI Evaluation Testing**
- [x] **Phase 16: Structured Observability & Health Probes**
- [ ] **Phase 17: Containerization & Kubernetes Deployment**

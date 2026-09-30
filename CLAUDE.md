# Customer Voice AI — Development Master Instructions

This file serves as the single source of truth for AI assistants (Claude, Antigravity, Gemini, Cursor) working on **Customer Voice AI**.

---

## 1. Project Overview

**Customer Voice AI** is an AI-powered Customer Voice Intelligence Platform tailored to **Capital One's publicly offered consumer products and platforms** (with configurable fallback to generic enterprise names e.g. Acme Financial).

The system transforms raw multi-platform reviews into evidence-backed, routed executive insights:
$$\text{Review Ingestion} \rightarrow \text{AI Analysis} \rightarrow \text{Embedding} \rightarrow \text{Semantic Clustering} \rightarrow \text{Trend Detection} \rightarrow \text{Investigation} \rightarrow \text{Team Routing} \rightarrow \text{HITL Approval} \rightarrow \text{Weekly Report}$$

---

## 2. Non-Negotiable Boundaries & Security

1. **Personal Project Independence:**
   * This is a personal portfolio project.
   * **NEVER** use employer internal credentials, proprietary APIs, internal databases, customer PII, internal terminology, or confidential team information.
   * **ONLY** use publicly accessible data or realistic high-fidelity synthetic data.
2. **Evidence vs. Hypothesis Separation (Responsible AI):**
   * The AI must strictly distinguish between **Observed Evidence** ("What customers are reporting") and **Hypothesis** ("What may explain the issue").
   * **BAD:** "Authentication service is broken."
   * **GOOD:** "Customer feedback shows an increase in Face ID authentication failures on iOS v6.14.0. The biometric authorization flow and recent mobile release warrant investigation."
3. **Configurable Team Routing:**
   * Team routing is dynamic and database-driven via `team_routing_rules`. Never hardcode routing `if/elif` statements deep in application logic.
4. **Human-in-the-Loop Gate:**
   * AI-generated recommendations must pass through human review (`pending_approval` $\rightarrow$ `approved` / `rejected` / `modified`) before inclusion in weekly executive reports.

---

## 3. Capital One Product Taxonomy & Review Channels

### Supported Products
* **Credit Cards:** `venture_x`, `venture`, `savor_one`, `quicksilver`, `platinum`, `spark_cash_plus`
* **Consumer Banking (360):** `banking_360_checking`, `banking_360_savings`, `banking_360_cd`
* **Auto Financing:** `auto_navigator`, `auto_refinance`
* **Digital & AI Platforms:** `c1_mobile_ios`, `c1_mobile_android`, `eno_virtual_assistant`, `c1_shopping_extension`, `creditwise`
* **Physical & Hybrid Experiences:** `c1_cafe`, `c1_branch_network`, `c1_atm_network`

### Supported Ingestion Platforms
* `apple_app_store` (iOS Mobile App, Shopping App)
* `google_play_store` (Android Mobile App, Auto Navigator)
* `chrome_web_store` (Capital One Shopping Extension)
* `google_places` (Capital One Cafés & Bank Branches)
* `trustpilot` (Consumer credit cards and banking reviews)
* `synthetic_stream` (Calibrated multi-platform synthetic generator)

---

## 4. Technology Stack & Directory Structure

* **Backend:** Python 3.10+, FastAPI, Pydantic v2, Pydantic Settings, SQLAlchemy 2.0 (Async), Alembic.
* **Database & Vector Store:** PostgreSQL 16 + `pgvector` (Adaptive `VectorType` supporting in-memory SQLite for instant tests).
* **Streaming Broker:** Apache Kafka (KRaft mode) + `aiokafka` (with sync in-process fallback for offline testing).
* **AI & Numerical Analysis:** Structured JSON extraction via OpenAI/Mock LLM, Scikit-learn (DBSCAN/HDBSCAN), NumPy, Pandas.
* **Frontend:** React 18, TypeScript, Tailwind CSS, Vite, Recharts, Lucide Icons.
* **Testing:** Pytest, `pytest-asyncio`, `pytest-cov`, HTTPX TestClient.

---

## 5. Development & Testing Commands

Always run commands in the local Python virtual environment (`.venv`):

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all backend tests
PYTHONPATH=.:backend pytest backend/tests -v

# Run synthetic data generator (10,000 reviews)
python3 data/synthetic/generate_cli.py --count 10000 --weeks 6

# Seed reviews directly into database
python3 scripts/seed_synthetic_data.py --count 10000

# Start backend dev server locally
./scripts/run_dev.sh

# Start full multi-container stack (Postgres+pgvector, Kafka, Backend, Frontend)
docker compose up -d
```

---

## 6. Implementation Roadmap & Current Status

- [x] **Phase 1: Architecture & Repository Setup**
- [x] **Phase 2: Database Schema & Relational Models (PostgreSQL + pgvector)**
- [x] **Phase 3: Synthetic Review Generator (10,000+ realistic reviews with temporal patterns)**
- [x] **Phase 4: Review Ingestion API**
- [x] **Phase 5: Event-Driven Kafka Pipeline**
- [x] **Phase 6: AI Review Analysis Agent (Structured JSON Extraction)**
- [x] **Phase 7: Vector Embeddings & pgvector Semantic Search**
- [x] **Phase 8: Semantic Clustering Pipeline**
- [ ] **Phase 9: Trend & Velocity Anomaly Detection**
- [ ] **Phase 10: Root Cause / Investigation Agent (LangGraph Multi-Agent Reflection & HITL Interrupt)**
- [ ] **Phase 11: Configurable Team Routing Engine**
- [ ] **Phase 12: Weekly Intelligence Report Generator**
- [ ] **Phase 13: React Dashboard & Visualization**
- [ ] **Phase 14: Human-in-the-Loop Approval Workflow**
- [ ] **Phase 15: Unit, Integration & AI Evaluation Testing**
- [ ] **Phase 16: Structured Observability & Health Probes**
- [ ] **Phase 17: Containerization & Kubernetes Deployment**

---

## 7. Rules for Incremental Phase Delivery

When implementing a phase:
1. Explain what will be built.
2. Identify files that will be created or modified.
3. Explain important design decisions.
4. Implement the phase.
5. Provide commands to run it.
6. Provide tests.
7. Verify the implementation (`pytest backend/tests -v` must pass 100%).
8. **DO NOT** move to the next phase until the current phase is confirmed.


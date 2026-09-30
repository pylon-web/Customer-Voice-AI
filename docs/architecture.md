# VoiceIQ — Technical System Architecture Specification

> **Document Version:** 1.1.0  
> **Status:** Active / Production-Ready  
> **Audience:** Software Engineers, System Architects, DevOps, Technical Leads  

---

## 1. System Overview & Technical Objectives

**VoiceIQ** is an enterprise-grade, event-driven customer voice intelligence and remediation platform. It ingests high-volume, unstructured multi-channel customer reviews, performs structured AI extraction, clusters semantically similar issues using dense vector embeddings, detects volume velocity surges via statistical baseline comparisons, runs multi-agent root-cause investigations, deterministically routes issues to department queues, and enforces human-in-the-loop governance.

### Core Non-Functional Requirements
- **High Ingestion Throughput:** Asynchronous non-blocking review ingestion decoupled via Apache Kafka.
- **Low Latency Semantic Search:** Sub-millisecond approximate nearest neighbor (ANN) vector retrieval via PostgreSQL `pgvector` with HNSW indexing.
- **Resilience & Local Autonomy:** Transparent fallback to in-memory asynchronous queues when external Kafka brokers are unavailable, enabling offline development and fast CI/CD runs.
- **Responsible AI Compliance:** Hard boundary separating ground-truth customer evidence from unverified engineering hypotheses.
- **Auditability:** Complete decision lineage for every AI recommendation approved, modified, or rejected by human operators.

---

## 2. High-Level Architecture Topology

```mermaid
flowchart TD
    subgraph Sources["1. Ingestion Sources"]
        S1["Apple App Store API"]
        S2["Google Play Store API"]
        S3["Chrome Web Store API"]
        S4["Google Maps / Places"]
        S5["Trustpilot & Public Feeds"]
        S6["CSV Batch Uploader"]
    end

    subgraph IngestionLayer["2. Ingestion & Broker Layer"]
        API["FastAPI Ingestion Gateway<br/>POST /api/v1/reviews"]
        PII["PII Redaction & Normalizer"]
        PROD["Kafka Event Producer"]
        K_CREATED["Topic: review.created"]
    end

    subgraph StreamingWorkers["3. Async Stream Processing"]
        CONS["Stream Consumer Worker"]
        ANALYZER["AI Structured Analysis Agent"]
        EMBED["1536-dim Embedding Engine"]
        K_ANALYZED["Topic: review.analyzed"]
    end

    subgraph StorageLayer["4. Unified Persistence"]
        PG[("PostgreSQL 16 (Relational DB)")]
        VEC[("pgvector Extension<br/>HNSW Cosine Index")]
    end

    subgraph AnalyticsEngines["5. Analytics & Statistical Engines"]
        CLUST["Unsupervised Clustering Engine<br/>(DBSCAN / HDBSCAN)"]
        TREND["Velocity Surge Detector<br/>(Rolling 4-wk Baseline, z >= 2.0)"]
        K_ALERT["Topic: issue.detected"]
    end

    subgraph AgenticCore["6. LangGraph Multi-Agent Orchestration"]
        LG_START(["Cluster Ingest"]) --> LG_EVID["Evidence Gatherer"]
        LG_EVID --> LG_HYPO["Root Cause Hypothesis Agent"]
        LG_HYPO --> LG_PLAN["Remediation Action Planner"]
        LG_PLAN --> LG_ROUTE["Department Router"]
    end

    subgraph GovernanceQueue["7. Governance & HITL Subsystem"]
        QUEUE["Pending Recommendations Queue"]
        ANALYST{"Lead Operations Analyst<br/>(Approve / Modify / Reject)"}
        AUDIT[("Governance Audit Trail")]
    end

    subgraph OutputSurfaces["8. Delivery & User Surfaces"]
        REPORTER["Weekly Executive Intelligence Reporter"]
        K_REPORT["Topic: report.generated"]
        DASHBOARD["React 18 + Vite 3D Visual Console"]
    end

    Sources --> API
    API --> PII
    PII --> PROD
    PROD --> K_CREATED
    K_CREATED --> CONS
    CONS --> ANALYZER
    ANALYZER --> EMBED
    EMBED --> K_ANALYZED
    K_ANALYZED --> PG
    EMBED --> VEC

    PG & VEC --> CLUST
    CLUST --> TREND
    TREND --> K_ALERT
    K_ALERT --> AgenticCore

    AgenticCore --> QUEUE
    QUEUE --> ANALYST
    ANALYST --> AUDIT
    AUDIT --> REPORTER
    REPORTER --> K_REPORT
    PG & AUDIT & REPORTER --> DASHBOARD
```

---

## 3. End-to-End Execution Flow (Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    actor Client as Client / Scraper / Webhook
    participant Ingestion as Ingestion API (FastAPI)
    participant Kafka as Apache Kafka Broker
    participant Worker as Stream Worker
    participant Analyzer as AI Analysis & Embedding Service
    participant DB as PostgreSQL + pgvector
    participant Analytics as Clustering & Trend Engine
    participant LangGraph as LangGraph Multi-Agent State Machine
    participant HITL as Governance Approval Queue
    participant ReportSvc as Executive Report Service
    participant UI as React 3D Dashboard

    Client->>Ingestion: POST /api/v1/reviews (Raw Review Payload)
    Ingestion->>Ingestion: Mask PII (credit cards, phone, email) & normalize taxonomy
    Ingestion->>Kafka: Publish event 'review.created'
    Ingestion-->>Client: HTTP 202 Accepted {review_id, status: "queued"}

    Kafka->>Worker: Consume 'review.created'
    Worker->>Analyzer: Extract Sentiment, Category, Severity & Generate 1536-dim Embedding
    Analyzer-->>Worker: Validated Analysis Pydantic Model + 1536-dim Vector
    Worker->>DB: INSERT into reviews, review_analyses, and pgvector embeddings
    Worker->>Kafka: Publish event 'review.analyzed'

    loop Scheduled / Triggered Anomaly Surveillance
        Analytics->>DB: Query Recent Review Vectors
        Analytics->>Analytics: Run DBSCAN Unsupervised Clustering
        Analytics->>Analytics: Calculate 4-Week Rolling Baseline & Z-Score Velocity ($z \ge 2.0$)
        Analytics->>DB: UPSERT issue_clusters & trend_metrics
        Analytics->>Kafka: Publish event 'issue.detected' (if $z \ge 2.0$ or WoW $\ge +25\%$)
    end

    Kafka->>LangGraph: Trigger Root Cause Graph for Detected Anomaly
    LangGraph->>LangGraph: Node 1: Ingest & Normalize Cluster Telemetry
    LangGraph->>LangGraph: Node 2: Extract Verbatim Customer Quotes (Ground Truth)
    LangGraph->>LangGraph: Node 3: Synthesize Technical Root-Cause Hypothesis
    LangGraph->>LangGraph: Node 4: Generate Concrete Engineering Action Steps
    LangGraph->>LangGraph: Node 5: Match Team Queue & Default SLA
    LangGraph->>DB: INSERT into recommendations (status: 'pending_approval')

    UI->>HITL: Operator inspects Evidence vs. Hypothesis in Dashboard
    HITL->>DB: POST /api/v1/recommendations/{id}/approve (Record Decision & Audit Log)
    DB->>ReportSvc: Compile Approved Issues into Weekly Intelligence Brief
    ReportSvc->>Kafka: Publish event 'report.generated'
    DB->>UI: Stream live telemetry, 3D radar metrics, and department workloads
```

---

## 4. Component Subsystem Specifications

### 4.1 Ingestion & Normalization Subsystem
* **Service:** [`IngestionService`](file:///Users/saurabhjadhav5172gmail.com/Workspace/AI/Customer-Voice-AI/backend/app/services/ingestion_service.py)
* **Taxonomy Normalization:** Uses exact and fuzzy regex matching to resolve colloquial user phrasing to canonical product IDs (`c1_mobile_ios`, `venture_x`, `c1_cafe`, `c1_360_checking`, `shopping_extension`).
* **PII Redaction Pipeline:**
  - Credit Card Numbers: Luhn-validated 13-16 digit sequences replaced with `[REDACTED_CARD]`.
  - Phone Numbers: US/International telephone patterns replaced with `[REDACTED_PHONE]`.
  - Email Addresses: Standard RFC 5322 regex matches replaced with `[REDACTED_EMAIL]`.

### 4.2 Event Streaming & Kafka Broker
* **Service:** [`KafkaProducerService`](file:///Users/saurabhjadhav5172gmail.com/Workspace/AI/Customer-Voice-AI/backend/app/kafka/producer.py)
* **Broker Protocol:** Apache Kafka in KRaft mode (no Zookeeper dependency).
* **Guarantees:** At-least-once delivery with partition key partitioning based on `product_id` for ordered downstream processing.
* **Transparent Degradation:** When `KAFKA_BOOTSTRAP_SERVERS` is unreachable, `_fallback_queue` buffers events in-memory, enabling seamless local developer execution.

### 4.3 Structured AI Analysis Engine
* **Service:** [`AnalysisService`](file:///Users/saurabhjadhav5172gmail.com/Workspace/AI/Customer-Voice-AI/backend/app/services/analysis_service.py)
* **LLM Model:** OpenAI GPT-4o / GPT-4o-mini with deterministic fallback to `MockAnalysisAgent` in CI environments.
* **Schema Contract:** Validated through Pydantic models:
  ```python
  class ReviewAnalysisCreate(BaseModel):
      sentiment: Literal["positive", "neutral", "negative"]
      sentiment_score: float = Field(ge=-1.0, le=1.0)
      category: str
      specific_issue: str
      severity: Literal["low", "medium", "high", "critical"]
      customer_intent: str
      confidence: float = Field(ge=0.0, le=1.0)
  ```

### 4.4 Vector Embedding & Similarity Search
* **Service:** [`EmbeddingService`](file:///Users/saurabhjadhav5172gmail.com/Workspace/AI/Customer-Voice-AI/backend/app/services/embedding_service.py)
* **Vector Dimension:** 1536 floats (OpenAI `text-embedding-3-small` standard).
* **Storage & Indexing:** PostgreSQL 16 `pgvector` extension with HNSW index:
  ```sql
  CREATE INDEX idx_review_embeddings_hnsw 
  ON review_embeddings 
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
  ```

### 4.5 Unsupervised Semantic Clustering Engine
* **Service:** [`ClusteringService`](file:///Users/saurabhjadhav5172gmail.com/Workspace/AI/Customer-Voice-AI/backend/app/services/clustering_service.py)
* **Algorithm:** Density-Based Spatial Clustering of Applications with Noise (DBSCAN) using precomputed cosine distance matrices.
* **Key Properties:**
  - Discovers arbitrarily shaped clusters without requiring a pre-specified cluster count ($k$).
  - Automatically isolates outliers (`label = -1`) as transient noise.
  - Computes cluster centroids, negative sentiment ratios, and representative customer quotes.

### 4.6 Statistical Velocity Surge Anomaly Detector
* **Service:** [`TrendService`](file:///Users/saurabhjadhav5172gmail.com/Workspace/AI/Customer-Voice-AI/backend/app/services/trend_service.py)
* **Mathematical Baseline Model:**
  1. Computes rolling volume mean ($\mu$) and standard deviation ($\sigma$) over four historical 7-day windows ($W_{-4} \dots W_{-1}$).
  2. Evaluates standard score for current window ($W_0$):
     $$z = \frac{V_{\text{current}} - \mu}{\sigma + \epsilon}$$
  3. Classification Thresholds:
     - **`emerging`:** $V_{\text{current}} \ge 3$ AND ($z \ge 2.0$ OR $\text{WoW \%} \ge +25\%$).
     - **`improving`:** $V_{\text{previous}} \ge 3$ AND $\text{WoW \%} \le -25\%$.
     - **`stable`:** Steady-state baseline.

### 4.7 LangGraph Multi-Agent Root Cause State Machine
* **Service:** [`InvestigationService`](file:///Users/saurabhjadhav5172gmail.com/Workspace/AI/Customer-Voice-AI/backend/app/services/investigation_service.py)
* **Graph Architecture:**
  ```
  (Start) ──> [Ingest Telemetry] ──> [Synthesize Evidence]
                                              │
  (End)   <── [Route to Team]    <── [Generate Hypothesis & Action]
  ```
* **State Contract:** Strictly enforces schema separation between verbatim quotes (`observed_evidence`), technical theories (`investigation_hypothesis`), and concrete engineering tasks (`recommended_action`).

### 4.8 Deterministic Enterprise Team Routing Engine
* **Service:** [`RoutingEngine`](file:///Users/saurabhjadhav5172gmail.com/Workspace/AI/Customer-Voice-AI/backend/app/services/routing_engine.py)
* **Department Queues & Default SLAs:**
  - `digital_engineering_mobile` (P1 — 24h SLA)
  - `payments_operations` (P2 — 48h SLA)
  - `travel_lounges_product` (P2 — 48h SLA)
  - `cafe_operations` (P3 — 72h SLA)
  - `digital_ai_security` (P2 — 48h SLA)
  - `shopping_engineering` (P3 — 72h SLA)
  - `customer_experience` (Intelligent Fallback)

### 4.9 Governance & Human-in-the-Loop (HITL) Subsystem
* **Service:** [`HITLService`](file:///Users/saurabhjadhav5172gmail.com/Workspace/AI/Customer-Voice-AI/backend/app/services/hitl_service.py)
* **Security Principle:** Automated recommendations remain in `pending_approval` state until a human operator signs off.
* **Audit Lineage:** Every decision persists operator ID, decision type (`approved`, `rejected`, `modified`), timestamp, and modification diff.

### 4.10 Executive Intelligence Reporting Engine
* **Service:** [`ReportService`](file:///Users/saurabhjadhav5172gmail.com/Workspace/AI/Customer-Voice-AI/backend/app/services/report_service.py)
* **Outputs:** Deterministic HTML reports, publication-ready GitHub-flavored Markdown briefs, and structured JSON payloads for downstream data warehouse ingestion.

---

## 5. Security & Responsible AI Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        RESPONSIBLE AI BOUNDARY                         │
├───────────────────────────────────┬────────────────────────────────────┤
│     OBSERVED CUSTOMER EVIDENCE    │      INVESTIGATION HYPOTHESIS      │
│          (Ground Truth)           │         (Tentative Theory)         │
├───────────────────────────────────┼────────────────────────────────────┤
│ • Direct, unedited quotes         │ • Technical potential explanations │
│ • App store version metadata      │ • Upstream dependency checks       │
│ • Quantified complaint counts     │ • Suggested diagnostic paths       │
│ • "Customers report biometric     │ • "Investigate whether upstream    │
│    failure on iOS v6.14.0"        │    FaceID API timeout increased"   │
└───────────────────────────────────┴────────────────────────────────────┘
```

1. **Strict Evidence vs. Hypothesis Separation:** Guarantees that AI-generated hypotheses are never labeled as established software defects.
2. **PII Scrubbing at Boundary:** Eliminates customer identifiers prior to embedding or LLM evaluation.
3. **Deterministic Seed Control:** Synthetic test data generators use deterministic RNG seeds for reproducible test runs.

---

## 6. Technology Stack & Architectural Decision Records (ADRs)

| Decision Area | Selected Technology | Alternative Evaluated | Selection Rationale |
| :--- | :--- | :--- | :--- |
| **API Runtime** | **FastAPI (Python 3.10+)** | Flask / Django / Express | Asynchronous ASGI runtime, native Pydantic v2 validation, automatic OpenAPI doc generation. |
| **Persistence** | **PostgreSQL 16 + pgvector** | Pinecone / Qdrant + MongoDB | Single engine eliminates data synchronization bugs between transactional records and vector indexes. |
| **Event Broker** | **Apache Kafka (KRaft)** | RabbitMQ / AWS SQS | Replayability, durable log retention, and high-throughput partition consumer group scaling. |
| **Agent Framework**| **LangGraph** | AutoGen / CrewAI | State-machine graph formulation with deterministic transitions and native human-in-the-loop interruption. |
| **Clustering** | **Scikit-learn DBSCAN** | K-Means / Agglomerative | Unsupervised clustering without prior knowledge of $k$; isolates noise points automatically. |
| **Frontend** | **React 18 + Vite + Tailwind** | Next.js / Vue | Fast client-side SPA rendering with rapid HMR and lightweight bundle deployment. |

---

*Document maintained at `docs/architecture.md` • VoiceIQ Platform*

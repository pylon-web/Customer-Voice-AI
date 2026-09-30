"""Pydantic v2 schemas and data transfer objects (DTOs) for API contracts and AI agent outputs."""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator


# ------------------------------------------------------------------------------
# Product, Source, and Team Schemas
# ------------------------------------------------------------------------------
class ProductBase(BaseModel):
    id: str
    name: str
    family: str
    description: Optional[str] = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)


class SourceBase(BaseModel):
    id: str
    name: str
    platform_type: str
    description: Optional[str] = None


class SourceRead(SourceBase):
    model_config = ConfigDict(from_attributes=True)


class TeamBase(BaseModel):
    id: str
    name: str
    lead_email: Optional[str] = None
    slack_channel: Optional[str] = None
    is_active: bool = True


class TeamRead(TeamBase):
    model_config = ConfigDict(from_attributes=True)


class TeamRoutingRuleBase(BaseModel):
    team_id: str
    pattern: str
    priority: int = Field(default=1, ge=1)


class TeamRoutingRuleCreate(TeamRoutingRuleBase):
    pass


class TeamRoutingRuleRead(TeamRoutingRuleBase):
    id: str
    created_at: datetime
    team_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class TeamWithRulesRead(TeamRead):
    routing_rules: List[TeamRoutingRuleRead] = Field(default_factory=list)


class RoutedTeamAssignment(BaseModel):
    cluster_id: Optional[str] = None
    matched_team: TeamRead
    matched_rule_id: Optional[str] = None
    matched_pattern: str
    match_reason: str
    priority_level: Literal["P1_CRITICAL", "P2_HIGH", "P3_MEDIUM", "P4_LOW"]
    target_sla_hours: int
    remediation_playbook: List[str] = Field(default_factory=list)
    review_response_guidance: str


class RoutingEvaluationRequest(BaseModel):
    cluster_id: Optional[str] = None
    product_id: Optional[str] = None
    category: Optional[str] = None
    issue_text: Optional[str] = None
    severity: Optional[str] = "medium"
    anomaly_score: Optional[float] = 0.0


# ------------------------------------------------------------------------------
# Review & AI Analysis Schemas
# ------------------------------------------------------------------------------
class ReviewAnalysisBase(BaseModel):
    sentiment: Literal["positive", "neutral", "negative"]
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    category: str
    issue: str
    severity: Literal["low", "medium", "high", "critical"]
    customer_intent: Optional[str] = None
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class ReviewAnalysisCreate(ReviewAnalysisBase):
    review_id: str


class ReviewAnalysisRead(ReviewAnalysisBase):
    id: str
    review_id: str
    analyzed_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReviewCreate(BaseModel):
    id: Optional[str] = None
    source_id: Optional[str] = None
    source: Optional[str] = None
    product_id: Optional[str] = None
    product: Optional[str] = None
    location: Optional[str] = None
    rating: int = Field(ge=1, le=5)
    review_title: Optional[str] = None
    review_text: Optional[str] = None
    text: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_text_and_product(self) -> "ReviewCreate":
        effective_text = self.review_text or self.text
        if not effective_text or not effective_text.strip():
            raise ValueError("Review must contain non-empty text (review_text or text).")
        effective_product = self.product_id or self.product
        if not effective_product or not effective_product.strip():
            raise ValueError("Review must specify a product or product_id.")
        return self

    def get_effective_text(self) -> str:
        return (self.review_text or self.text or "").strip()

    def get_effective_product_id(self) -> str:
        return (self.product_id or self.product or "").strip()

    def get_effective_source_id(self) -> str:
        return (self.source_id or self.source or "generic_public").strip()


class ReviewRead(BaseModel):
    id: str
    source_id: str
    product_id: str
    location: Optional[str] = None
    rating: int
    review_title: Optional[str] = None
    review_text: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    ingested_at: datetime
    analysis: Optional[ReviewAnalysisRead] = None
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, obj: Any) -> Optional["ReviewRead"]:
        if obj is None:
            return None
        analysis = None
        # Safely inspect __dict__ to avoid triggering async lazy-loading when relationship isn't preloaded
        if "analysis" in getattr(obj, "__dict__", {}) and obj.__dict__["analysis"] is not None:
            analysis = ReviewAnalysisRead.model_validate(obj.__dict__["analysis"])
        return cls(
            id=obj.id,
            source_id=obj.source_id,
            product_id=obj.product_id,
            location=obj.location,
            rating=obj.rating,
            review_title=obj.review_title,
            review_text=obj.review_text,
            metadata_json=obj.metadata_json or {},
            created_at=obj.created_at,
            ingested_at=obj.ingested_at,
            analysis=analysis,
        )


class ReviewBatchCreate(BaseModel):
    reviews: List[ReviewCreate]


class ReviewBatchResponse(BaseModel):
    total_submitted: int
    total_accepted: int
    review_ids: List[str]
    status: str = "queued"


class ReviewListResponse(BaseModel):
    items: List[ReviewRead]
    total: int
    page: int
    page_size: int
    pages: int


class ReviewFilterParams(BaseModel):
    product_id: Optional[str] = None
    source_id: Optional[str] = None
    sentiment: Optional[str] = None
    category: Optional[str] = None
    rating: Optional[int] = None
    location: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


# ------------------------------------------------------------------------------
# Vector Embedding Schemas
# ------------------------------------------------------------------------------
class ReviewEmbeddingRead(BaseModel):
    id: str
    review_id: str
    embedding: List[float]
    model_name: str
    dimension: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SemanticSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=100)
    top_k: int = Field(default=10, ge=1, le=100)
    product_id: Optional[str] = None
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    threshold: Optional[float] = Field(default=0.0, ge=0.0, le=1.0)


class SemanticSearchResultItem(BaseModel):
    review: ReviewRead
    similarity: float
    distance: Optional[float] = None


class SemanticSearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SemanticSearchResultItem]


# ------------------------------------------------------------------------------
# Issue Cluster Schemas
# ------------------------------------------------------------------------------
class IssueClusterBase(BaseModel):
    cluster_title: str
    description: Optional[str] = None
    category: str
    affected_product_id: str
    review_count: int = 0
    negative_pct: float = 0.0
    neutral_pct: float = 0.0
    positive_pct: float = 0.0
    representative_quotes: List[str] = Field(default_factory=list)
    status: str = "active"


class IssueClusterRead(IssueClusterBase):
    id: str
    first_observed_at: datetime
    latest_observed_at: datetime
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ClusterRunRequest(BaseModel):
    eps: float = Field(default=0.40, ge=0.05, le=1.0)
    min_samples: int = Field(default=3, ge=2)
    product_id: Optional[str] = None
    lookback_days: Optional[int] = None
    min_reviews: Optional[int] = None


class ClusterRunResponse(BaseModel):
    clusters_formed: int
    total_reviews_analyzed: int
    clustered_reviews_count: int
    noise_reviews_count: int
    cluster_ids: List[str]


class ClusterReviewItem(BaseModel):
    review: ReviewRead
    similarity_score: float
    assigned_at: datetime


class IssueClusterDetailRead(IssueClusterRead):
    reviews: List[ClusterReviewItem] = Field(default_factory=list)
    product_name: Optional[str] = None


class IssueClusterListResponse(BaseModel):
    items: List[IssueClusterRead]
    total: int
    page: int
    page_size: int
    pages: int


# ------------------------------------------------------------------------------
# Trend Metric Schemas
# ------------------------------------------------------------------------------
class TrendMetricRead(BaseModel):
    id: str
    cluster_id: str
    period_start: datetime
    period_end: datetime
    current_volume: int
    previous_volume: int
    baseline_4wk_avg: float
    wow_change_pct: float
    trend_direction: Literal["emerging", "stable", "improving"]
    anomaly_score: float
    cluster_title: Optional[str] = None
    affected_product_id: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class TrendListResponse(BaseModel):
    items: List[TrendMetricRead]
    total: int
    page: int
    page_size: int
    pages: int


class TrendCalculateRequest(BaseModel):
    as_of_date: Optional[datetime] = None
    cluster_id: Optional[str] = None


class TrendCalculateResponse(BaseModel):
    trends_calculated: int
    emerging_count: int
    improving_count: int
    stable_count: int
    trend_ids: List[str]


# ------------------------------------------------------------------------------
# Recommendation & Human-in-the-Loop Schemas
# ------------------------------------------------------------------------------
class RecommendationBase(BaseModel):
    cluster_id: str
    suggested_team_id: str
    observed_evidence: str
    investigation_hypothesis: str
    recommended_action: str
    confidence: float
    status: Literal["pending_approval", "approved", "rejected", "modified"] = "pending_approval"


class ApprovalRead(BaseModel):
    id: str
    recommendation_id: str
    reviewer_name: str
    decision: str
    reviewer_notes: Optional[str] = None
    modified_action: Optional[str] = None
    decided_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RecommendationRead(RecommendationBase):
    id: str
    created_at: datetime
    updated_at: datetime
    suggested_team: Optional[TeamRead] = None
    cluster_title: Optional[str] = None
    approvals: List[ApprovalRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class RecommendationDecisionRequest(BaseModel):
    reviewer_name: str
    decision: Literal["approved", "rejected", "modified"]
    reviewer_notes: Optional[str] = None
    modified_action: Optional[str] = None


class RecommendationListResponse(BaseModel):
    items: List[RecommendationRead]
    total: int
    page: int
    page_size: int
    pages: int


# ------------------------------------------------------------------------------
# Weekly Intelligence Report Schemas
# ------------------------------------------------------------------------------
class ReportIssueRead(BaseModel):
    id: str
    cluster_id: str
    issue_type: Literal["emerging", "improving", "persistent"]
    rank: int
    cluster: Optional[IssueClusterRead] = None
    recommendation: Optional[RecommendationRead] = None
    model_config = ConfigDict(from_attributes=True)


class ReportRead(BaseModel):
    id: str
    title: str
    report_period_start: datetime
    report_period_end: datetime
    total_reviews: int
    negative_pct: float
    emerging_issues_count: int
    improving_issues_count: int
    executive_summary: str
    geographic_insights: Dict[str, Any]
    generated_at: datetime
    report_issues: List[ReportIssueRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class ReportGenerateRequest(BaseModel):
    title: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class ReportListResponse(BaseModel):
    items: List[ReportRead]
    total: int
    page: int
    page_size: int
    pages: int


class ReportFormatResponse(BaseModel):
    report_id: str
    title: str
    format: Literal["markdown", "html", "json"]
    content: str

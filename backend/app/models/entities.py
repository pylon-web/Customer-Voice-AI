"""SQLAlchemy 2.0 relational and vector database models."""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid
from app.core.database import VectorType


class User(Base, TimestampMixin):
    """User account entity for enterprise analyst and reviewer access."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="analyst", nullable=False)  # admin, analyst, viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Product(Base, TimestampMixin):
    """Product catalog entity (e.g. Venture X, 360 Checking, Auto Navigator, Eno)."""
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    reviews: Mapped[List["Review"]] = relationship("Review", back_populates="product")
    clusters: Mapped[List["IssueCluster"]] = relationship("IssueCluster", back_populates="affected_product")


class Source(Base, TimestampMixin):
    """Ingestion platform / review source entity (e.g. Apple App Store, Google Play, Places)."""
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    platform_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    reviews: Mapped[List["Review"]] = relationship("Review", back_populates="source")


class Team(Base, TimestampMixin):
    """Business team recipient for insight routing."""
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    lead_email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    slack_channel: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    routing_rules: Mapped[List["TeamRoutingRule"]] = relationship(
        "TeamRoutingRule", back_populates="team", cascade="all, delete-orphan"
    )
    recommendations: Mapped[List["Recommendation"]] = relationship("Recommendation", back_populates="suggested_team")


class TeamRoutingRule(Base, TimestampMixin):
    """Configurable routing rule mapping categories/issues to teams without code changes."""
    __tablename__ = "team_routing_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    team_id: Mapped[str] = mapped_column(String(64), ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    pattern: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    team: Mapped["Team"] = relationship("Team", back_populates="routing_rules")


class Review(Base):
    """Core customer review ingestion entity."""
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    source_id: Mapped[str] = mapped_column(String(64), ForeignKey("sources.id"), index=True, nullable=False)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.id"), index=True, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review_title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    review_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    product: Mapped["Product"] = relationship("Product", back_populates="reviews")
    source: Mapped["Source"] = relationship("Source", back_populates="reviews")
    analysis: Mapped[Optional["ReviewAnalysis"]] = relationship(
        "ReviewAnalysis", back_populates="review", uselist=False, cascade="all, delete-orphan"
    )
    embedding: Mapped[Optional["ReviewEmbedding"]] = relationship(
        "ReviewEmbedding", back_populates="review", uselist=False, cascade="all, delete-orphan"
    )
    cluster_links: Mapped[List["ClusterReview"]] = relationship(
        "ClusterReview", back_populates="review", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_reviews_product_created", "product_id", "created_at"),
        Index("ix_reviews_rating", "rating"),
    )


class ReviewAnalysis(Base):
    """Structured AI analysis output for an individual review."""
    __tablename__ = "review_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    review_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("reviews.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    sentiment: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # positive, neutral, negative
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)  # -1.0 to 1.0
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    issue: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # low, medium, high, critical
    customer_intent: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    entities: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    review: Mapped["Review"] = relationship("Review", back_populates="analysis")

    __table_args__ = (
        Index("ix_analysis_category_severity", "category", "severity"),
        Index("ix_analysis_sentiment", "sentiment"),
    )


class ReviewEmbedding(Base):
    """1536-dimensional vector embedding for semantic search and clustering."""
    __tablename__ = "review_embeddings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    review_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("reviews.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    embedding: Mapped[List[float]] = mapped_column(VectorType(dimension=1536), nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), default="text-embedding-3-small", nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, default=1536, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    review: Mapped["Review"] = relationship("Review", back_populates="embedding")


class IssueCluster(Base, TimestampMixin):
    """Semantically grouped issue cluster spanning multiple reviews."""
    __tablename__ = "issue_clusters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    cluster_title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    affected_product_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("products.id"), index=True, nullable=False
    )
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    negative_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    neutral_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    positive_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    representative_quotes: Mapped[List[str]] = mapped_column(JSON, default=list)
    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latest_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    centroid_embedding: Mapped[Optional[List[float]]] = mapped_column(VectorType(dimension=1536), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True, nullable=False)

    affected_product: Mapped["Product"] = relationship("Product", back_populates="clusters")
    cluster_reviews: Mapped[List["ClusterReview"]] = relationship(
        "ClusterReview", back_populates="cluster", cascade="all, delete-orphan"
    )
    trend_metrics: Mapped[List["TrendMetric"]] = relationship(
        "TrendMetric", back_populates="cluster", cascade="all, delete-orphan"
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation", back_populates="cluster", cascade="all, delete-orphan"
    )


class ClusterReview(Base):
    """Many-to-many association mapping reviews to issue clusters with similarity distances."""
    __tablename__ = "cluster_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    cluster_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("issue_clusters.id", ondelete="CASCADE"), index=True, nullable=False
    )
    review_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("reviews.id", ondelete="CASCADE"), index=True, nullable=False
    )
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    cluster: Mapped["IssueCluster"] = relationship("IssueCluster", back_populates="cluster_reviews")
    review: Mapped["Review"] = relationship("Review", back_populates="cluster_links")

    __table_args__ = (
        Index("ix_cluster_review_pair", "cluster_id", "review_id", unique=True),
    )


class TrendMetric(Base, TimestampMixin):
    """Historical and velocity trend metrics calculated over clusters."""
    __tablename__ = "trend_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    cluster_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("issue_clusters.id", ondelete="CASCADE"), index=True, nullable=False
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_volume: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    previous_volume: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    baseline_4wk_avg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    wow_change_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trend_direction: Mapped[str] = mapped_column(String(32), default="stable", index=True, nullable=False)
    anomaly_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    cluster: Mapped["IssueCluster"] = relationship("IssueCluster", back_populates="trend_metrics")


class Recommendation(Base, TimestampMixin):
    """Evidence-backed operational recommendation generated by the Root Cause Agent."""
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    cluster_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("issue_clusters.id", ondelete="CASCADE"), index=True, nullable=False
    )
    suggested_team_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("teams.id"), index=True, nullable=False
    )
    observed_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    investigation_hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="pending_approval", index=True, nullable=False
    )  # pending_approval, approved, rejected, modified

    cluster: Mapped["IssueCluster"] = relationship("IssueCluster", back_populates="recommendations")
    suggested_team: Mapped["Team"] = relationship("Team", back_populates="recommendations")
    approvals: Mapped[List["Approval"]] = relationship(
        "Approval", back_populates="recommendation", cascade="all, delete-orphan"
    )


class Approval(Base):
    """Human-in-the-Loop decision audit log on an AI-generated recommendation."""
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    recommendation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recommendations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reviewer_name: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)  # approved, rejected, modified
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    modified_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    recommendation: Mapped["Recommendation"] = relationship("Recommendation", back_populates="approvals")


class Report(Base, TimestampMixin):
    """Weekly Executive Intelligence Report document."""
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    report_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    report_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    negative_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    emerging_issues_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    improving_issues_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    geographic_insights: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    report_issues: Mapped[List["ReportIssue"]] = relationship(
        "ReportIssue", back_populates="report", cascade="all, delete-orphan"
    )


class ReportIssue(Base):
    """Issues highlighted inside an executive intelligence report."""
    __tablename__ = "report_issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="CASCADE"), index=True, nullable=False
    )
    cluster_id: Mapped[str] = mapped_column(String(36), ForeignKey("issue_clusters.id"), nullable=False)
    recommendation_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("recommendations.id"), nullable=True
    )
    issue_type: Mapped[str] = mapped_column(String(32), nullable=False)  # emerging, improving, persistent
    rank: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    report: Mapped["Report"] = relationship("Report", back_populates="report_issues")
    cluster: Mapped["IssueCluster"] = relationship("IssueCluster")
    recommendation: Mapped[Optional["Recommendation"]] = relationship("Recommendation")

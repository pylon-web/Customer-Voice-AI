"""Initialize database schema with Capital One product taxonomy and pgvector.

Revision ID: 0001_init_schema
Revises: 
Create Date: 2026-09-28 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.core.database import VectorType

# revision identifiers, used by Alembic.
revision: str = '0001_init_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension if postgresql
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1.1 Users Table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('email', sa.String(length=256), nullable=False),
        sa.Column('full_name', sa.String(length=128), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False, default="analyst"),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 2. Products Table
    op.create_table(
        'products',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('family', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_products_family', 'products', ['family'])

    # 3. Sources Table
    op.create_table(
        'sources',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('platform_type', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_sources_platform_type', 'sources', ['platform_type'])

    # 4. Teams Table
    op.create_table(
        'teams',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('lead_email', sa.String(length=128), nullable=True),
        sa.Column('slack_channel', sa.String(length=64), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 5. Team Routing Rules Table
    op.create_table(
        'team_routing_rules',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('team_id', sa.String(length=64), sa.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False),
        sa.Column('pattern', sa.String(length=128), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, default=1),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_team_routing_rules_pattern', 'team_routing_rules', ['pattern'])
    op.create_index('ix_team_routing_rules_team_id', 'team_routing_rules', ['team_id'])

    # 6. Reviews Table
    op.create_table(
        'reviews',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('source_id', sa.String(length=64), sa.ForeignKey('sources.id'), nullable=False),
        sa.Column('product_id', sa.String(length=64), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('location', sa.String(length=128), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('review_title', sa.String(length=256), nullable=True),
        sa.Column('review_text', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_reviews_created_at', 'reviews', ['created_at'])
    op.create_index('ix_reviews_product_created', 'reviews', ['product_id', 'created_at'])
    op.create_index('ix_reviews_rating', 'reviews', ['rating'])
    op.create_index('ix_reviews_source_id', 'reviews', ['source_id'])

    # 7. Review Analyses Table
    op.create_table(
        'review_analyses',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('review_id', sa.String(length=64), sa.ForeignKey('reviews.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('sentiment', sa.String(length=32), nullable=False),
        sa.Column('sentiment_score', sa.Float(), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('issue', sa.String(length=128), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('customer_intent', sa.String(length=128), nullable=True),
        sa.Column('entities', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, default=0.0),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_analysis_category_severity', 'review_analyses', ['category', 'severity'])
    op.create_index('ix_analysis_sentiment', 'review_analyses', ['sentiment'])

    # 8. Review Embeddings Table
    op.create_table(
        'review_embeddings',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('review_id', sa.String(length=64), sa.ForeignKey('reviews.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('embedding', VectorType(1536), nullable=False),
        sa.Column('model_name', sa.String(length=64), nullable=False, default="text-embedding-3-small"),
        sa.Column('dimension', sa.Integer(), nullable=False, default=1536),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 9. Issue Clusters Table
    op.create_table(
        'issue_clusters',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('cluster_title', sa.String(length=256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('affected_product_id', sa.String(length=64), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('review_count', sa.Integer(), nullable=False, default=0),
        sa.Column('negative_pct', sa.Float(), nullable=False, default=0.0),
        sa.Column('neutral_pct', sa.Float(), nullable=False, default=0.0),
        sa.Column('positive_pct', sa.Float(), nullable=False, default=0.0),
        sa.Column('representative_quotes', sa.JSON(), nullable=False),
        sa.Column('first_observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('latest_observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('centroid_embedding', VectorType(1536), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, default="active"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_issue_clusters_category', 'issue_clusters', ['category'])
    op.create_index('ix_issue_clusters_status', 'issue_clusters', ['status'])

    # 10. Cluster Reviews Association Table
    op.create_table(
        'cluster_reviews',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('cluster_id', sa.String(length=36), sa.ForeignKey('issue_clusters.id', ondelete='CASCADE'), nullable=False),
        sa.Column('review_id', sa.String(length=64), sa.ForeignKey('reviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_cluster_review_pair', 'cluster_reviews', ['cluster_id', 'review_id'], unique=True)

    # 11. Trend Metrics Table
    op.create_table(
        'trend_metrics',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('cluster_id', sa.String(length=36), sa.ForeignKey('issue_clusters.id', ondelete='CASCADE'), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('current_volume', sa.Integer(), nullable=False, default=0),
        sa.Column('previous_volume', sa.Integer(), nullable=False, default=0),
        sa.Column('baseline_4wk_avg', sa.Float(), nullable=False, default=0.0),
        sa.Column('wow_change_pct', sa.Float(), nullable=False, default=0.0),
        sa.Column('trend_direction', sa.String(length=32), nullable=False, default="stable"),
        sa.Column('anomaly_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_trend_metrics_direction', 'trend_metrics', ['trend_direction'])

    # 12. Recommendations Table
    op.create_table(
        'recommendations',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('cluster_id', sa.String(length=36), sa.ForeignKey('issue_clusters.id', ondelete='CASCADE'), nullable=False),
        sa.Column('suggested_team_id', sa.String(length=64), sa.ForeignKey('teams.id'), nullable=False),
        sa.Column('observed_evidence', sa.Text(), nullable=False),
        sa.Column('investigation_hypothesis', sa.Text(), nullable=False),
        sa.Column('recommended_action', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, default=0.0),
        sa.Column('status', sa.String(length=32), nullable=False, default="pending_approval"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_recommendations_status', 'recommendations', ['status'])

    # 13. Approvals Table
    op.create_table(
        'approvals',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('recommendation_id', sa.String(length=36), sa.ForeignKey('recommendations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reviewer_name', sa.String(length=128), nullable=False),
        sa.Column('decision', sa.String(length=32), nullable=False),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
        sa.Column('modified_action', sa.Text(), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 14. Reports Table
    op.create_table(
        'reports',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('report_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('report_period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_reviews', sa.Integer(), nullable=False, default=0),
        sa.Column('negative_pct', sa.Float(), nullable=False, default=0.0),
        sa.Column('emerging_issues_count', sa.Integer(), nullable=False, default=0),
        sa.Column('improving_issues_count', sa.Integer(), nullable=False, default=0),
        sa.Column('executive_summary', sa.Text(), nullable=False),
        sa.Column('geographic_insights', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 15. Report Issues Table
    op.create_table(
        'report_issues',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('report_id', sa.String(length=36), sa.ForeignKey('reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cluster_id', sa.String(length=36), sa.ForeignKey('issue_clusters.id'), nullable=False),
        sa.Column('recommendation_id', sa.String(length=36), sa.ForeignKey('recommendations.id'), nullable=True),
        sa.Column('issue_type', sa.String(length=32), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False, default=1),
    )


def downgrade() -> None:
    op.drop_table('report_issues')
    op.drop_table('reports')
    op.drop_table('approvals')
    op.drop_table('recommendations')
    op.drop_table('trend_metrics')
    op.drop_table('cluster_reviews')
    op.drop_table('issue_clusters')
    op.drop_table('review_embeddings')
    op.drop_table('review_analyses')
    op.drop_table('reviews')
    op.drop_table('team_routing_rules')
    op.drop_table('teams')
    op.drop_table('sources')
    op.drop_table('products')
    op.drop_table('users')

/**
 * TypeScript type definitions for Customer Voice AI Frontend.
 * Synchronized with backend Pydantic DTO contracts.
 */

export type SentimentType = 'positive' | 'neutral' | 'negative';
export type SeverityType = 'low' | 'medium' | 'high' | 'critical';
export type TrendDirectionType = 'emerging' | 'stable' | 'improving';
export type RecommendationStatus = 'pending_approval' | 'approved' | 'rejected' | 'modified';
export type PriorityLevel = 'P1_CRITICAL' | 'P2_HIGH' | 'P3_MEDIUM' | 'P4_LOW';

export interface Product {
  id: string;
  name: string;
  family: string;
  description?: string;
}

export interface Source {
  id: string;
  name: string;
  platform_type: string;
  description?: string;
}

export interface ReviewAnalysis {
  id?: string;
  review_id?: string;
  sentiment: SentimentType;
  sentiment_score: number;
  category: string;
  issue: string;
  severity: SeverityType;
  customer_intent?: string;
  entities: Array<Record<string, any>>;
  confidence: number;
  analyzed_at?: string;
}

export interface Review {
  id: string;
  source_id: string;
  product_id: string;
  location?: string | null;
  rating: number;
  review_title?: string | null;
  review_text: string;
  metadata_json?: Record<string, any>;
  created_at: string;
  ingested_at: string;
  analysis?: ReviewAnalysis | null;
}

export interface ReviewListResponse {
  items: Review[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ReviewFilterParams {
  product_id?: string;
  source_id?: string;
  sentiment?: string;
  category?: string;
  rating?: number;
  location?: string;
  page?: number;
  page_size?: number;
}

export interface SemanticSearchResultItem {
  review: Review;
  similarity: number;
  distance?: number;
}

export interface SemanticSearchResponse {
  query: string;
  total_results: number;
  results: SemanticSearchResultItem[];
}

export interface IssueCluster {
  id: string;
  cluster_title: string;
  description?: string;
  category: string;
  affected_product_id: string;
  review_count: number;
  negative_pct: number;
  neutral_pct: number;
  positive_pct: number;
  representative_quotes: string[];
  status: string;
  first_observed_at: string;
  latest_observed_at: string;
  created_at: string;
  updated_at: string;
}

export interface IssueClusterListResponse {
  items: IssueCluster[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ClusterReviewItem {
  review: Review;
  similarity_score: number;
  assigned_at: string;
}

export interface IssueClusterDetail extends IssueCluster {
  reviews: ClusterReviewItem[];
  product_name?: string;
}

export interface TrendMetric {
  id: string;
  cluster_id: string;
  period_start: string;
  period_end: string;
  current_volume: number;
  previous_volume: number;
  baseline_4wk_avg: number;
  wow_change_pct: number;
  trend_direction: TrendDirectionType;
  anomaly_score: number;
  cluster_title?: string;
  affected_product_id?: string;
}

export interface TrendListResponse {
  items: TrendMetric[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Approval {
  id: string;
  recommendation_id: string;
  reviewer_name: string;
  decision: string;
  reviewer_notes?: string | null;
  modified_action?: string | null;
  decided_at: string;
}

export interface Recommendation {
  id: string;
  cluster_id: string;
  suggested_team_id: string;
  observed_evidence: string;
  investigation_hypothesis: string;
  recommended_action: string;
  confidence: number;
  status: RecommendationStatus;
  created_at: string;
  updated_at: string;
  cluster_title?: string;
  suggested_team?: Team;
  approvals: Approval[];
}

export interface RecommendationListResponse {
  items: Recommendation[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Team {
  id: string;
  name: string;
  lead_email?: string | null;
  slack_channel?: string | null;
  is_active: boolean;
}

export interface TeamRoutingRule {
  id: string;
  team_id: string;
  pattern: string;
  priority: number;
  created_at: string;
  team_name?: string | null;
}

export interface TeamWithRules extends Team {
  routing_rules: TeamRoutingRule[];
}

export interface RoutedTeamAssignment {
  cluster_id?: string | null;
  matched_team: Team;
  matched_rule_id?: string | null;
  matched_pattern: string;
  match_reason: string;
  priority_level: PriorityLevel;
  target_sla_hours: number;
  remediation_playbook: string[];
  review_response_guidance: string;
}

export interface ReportIssue {
  id: string;
  cluster_id: string;
  issue_type: 'emerging' | 'improving' | 'persistent';
  rank: number;
  cluster?: IssueCluster | null;
  recommendation?: Recommendation | null;
}

export interface Report {
  id: string;
  title: string;
  report_period_start: string;
  report_period_end: string;
  total_reviews: number;
  negative_pct: number;
  emerging_issues_count: number;
  improving_issues_count: number;
  executive_summary: string;
  geographic_insights: Record<string, any>;
  generated_at: string;
  report_issues: ReportIssue[];
}

export interface ReportListResponse {
  items: Report[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ReportFormatResponse {
  report_id: string;
  title: string;
  format: 'markdown' | 'html' | 'json';
  content: string;
}

export interface SentimentCounts {
  positive: number;
  neutral: number;
  negative: number;
}

export interface ProductVolumeStat {
  product_id: string;
  product_name: string;
  count: number;
}

export interface DashboardOverviewResponse {
  total_reviews: number;
  avg_rating: number;
  sentiment_counts: SentimentCounts;
  total_clusters: number;
  anomalies_count: number;
  pending_recommendations_count: number;
  top_products: ProductVolumeStat[];
  recent_anomalies: Array<{
    id: string;
    cluster_id: string;
    current_volume: number;
    previous_volume: number;
    wow_change_pct: number;
    anomaly_score: number;
    trend_direction: string;
  }>;
}

export interface HealthData {
  status: string;
  app: string;
  version: string;
  environment: string;
  timestamp: string;
}

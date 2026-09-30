/**
 * API client communicating with FastAPI backend.
 */

import {
  HealthData,
  DashboardOverviewResponse,
  Product,
  Source,
  Review,
  ReviewListResponse,
  ReviewFilterParams,
  SemanticSearchResponse,
  IssueClusterListResponse,
  IssueClusterDetail,
  TrendListResponse,
  TrendMetric,
  RecommendationListResponse,
  Recommendation,
  Approval,
  TeamWithRules,
  RoutedTeamAssignment,
  ReportListResponse,
  Report,
  ReportFormatResponse,
} from '../types';

const BASE_URL = '/api/v1';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson?.error?.message) {
        errorDetail = errJson.error.message;
      } else if (errJson?.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  return response.json() as Promise<T>;
}

export const api = {
  // System Health & Overview
  getHealth: () => request<HealthData>('/health'),
  getOverview: () => request<DashboardOverviewResponse>('/analytics/overview'),
  getProducts: () => request<Product[]>('/analytics/products'),
  getSources: () => request<Source[]>('/analytics/sources'),

  // Reviews
  getReviews: (params: ReviewFilterParams = {}) => {
    const query = new URLSearchParams();
    if (params.product_id) query.set('product_id', params.product_id);
    if (params.source_id) query.set('source_id', params.source_id);
    if (params.sentiment) query.set('sentiment', params.sentiment);
    if (params.category) query.set('category', params.category);
    if (params.rating) query.set('rating', String(params.rating));
    if (params.location) query.set('location', params.location);
    if (params.page) query.set('page', String(params.page));
    if (params.page_size) query.set('page_size', String(params.page_size));

    const qs = query.toString();
    return request<ReviewListResponse>(`/reviews${qs ? `?${qs}` : ''}`);
  },

  getReview: (id: string) => request<Review>(`/reviews/${id}`),

  searchSemantic: (query: string, limit = 10, minSimilarity = 0.0) => {
    const q = encodeURIComponent(query);
    return request<SemanticSearchResponse>(
      `/reviews/search/semantic?q=${q}&limit=${limit}&min_similarity=${minSimilarity}`
    );
  },

  ingestReview: (payload: {
    product_id: string;
    source_id?: string;
    rating: number;
    review_title?: string;
    review_text: string;
    location?: string;
  }) =>
    request<Review>('/reviews', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  ingestBatch: (reviews: any[]) =>
    request<{ total_submitted: number; total_accepted: number; review_ids: string[] }>(
      '/reviews/batch',
      {
        method: 'POST',
        body: JSON.stringify({ reviews }),
      }
    ),

  // Clusters
  getClusters: (page = 1, pageSize = 50) =>
    request<IssueClusterListResponse>(`/clusters?page=${page}&page_size=${pageSize}`),

  getCluster: (id: string) => request<IssueClusterDetail>(`/clusters/${id}`),

  runClustering: (eps = 0.4, minSamples = 3) =>
    request<{ clusters_formed: number; total_reviews_analyzed: number; noise_reviews_count: number }>(
      '/clusters/run',
      {
        method: 'POST',
        body: JSON.stringify({ eps, min_samples: minSamples }),
      }
    ),

  // Trends & Anomaly Detection
  getTrends: (isAnomaly?: boolean, page = 1, pageSize = 50) => {
    const query = new URLSearchParams();
    if (isAnomaly !== undefined) query.set('is_anomaly', String(isAnomaly));
    query.set('page', String(page));
    query.set('page_size', String(pageSize));
    return request<TrendListResponse>(`/trends?${query.toString()}`);
  },

  getClusterTrends: (clusterId: string) =>
    request<TrendMetric[]>(`/trends/${clusterId}`),

  calculateTrends: () =>
    request<{ trends_calculated: number; emerging_count: number; stable_count: number; improving_count: number }>(
      '/trends/calculate',
      { method: 'POST', body: JSON.stringify({}) }
    ),

  // Investigations & HITL Recommendations
  getRecommendations: (page = 1, pageSize = 50, status?: string) => {
    const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (status) query.set('status', status);
    return request<RecommendationListResponse>(`/investigations/recommendations?${query.toString()}`);
  },

  runInvestigation: (clusterId: string) =>
    request<Recommendation>(`/investigations/run?cluster_id=${clusterId}`, {
      method: 'POST',
    }),

  approveRecommendation: (id: string, reviewerName: string, notes?: string) =>
    request<Approval>(`/investigations/recommendations/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({
        reviewer_name: reviewerName,
        decision: 'approved',
        reviewer_notes: notes || null,
      }),
    }),

  rejectRecommendation: (id: string, reviewerName: string, notes?: string) =>
    request<Approval>(`/investigations/recommendations/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({
        reviewer_name: reviewerName,
        decision: 'rejected',
        reviewer_notes: notes || null,
      }),
    }),

  modifyRecommendation: (id: string, reviewerName: string, modifiedAction: string, notes?: string) =>
    request<Approval>(`/investigations/recommendations/${id}/modify`, {
      method: 'POST',
      body: JSON.stringify({
        reviewer_name: reviewerName,
        decision: 'modified',
        modified_action: modifiedAction,
        reviewer_notes: notes || null,
      }),
    }),

  getAuditHistory: () => request<Approval[]>('/investigations/audit'),

  // Teams & Routing Matrix
  getTeams: () => request<TeamWithRules[]>('/teams'),

  evaluateRouting: (payload: {
    cluster_id?: string;
    product_id?: string;
    category?: string;
    issue_text?: string;
    severity?: string;
    anomaly_score?: number;
  }) =>
    request<RoutedTeamAssignment>('/teams/route', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Reports
  getReports: (page = 1, pageSize = 20) =>
    request<ReportListResponse>(`/reports?page=${page}&page_size=${pageSize}`),

  getLatestReport: () => request<Report>('/reports/latest'),

  getReport: (id: string) => request<Report>(`/reports/${id}`),

  generateReport: (title?: string) =>
    request<Report>('/reports/generate', {
      method: 'POST',
      body: JSON.stringify({ title }),
    }),

  exportReport: (id: string, format: 'json' | 'markdown' | 'html') =>
    request<ReportFormatResponse>(`/reports/${id}/export?format=${format}`),
};

import React, { useState, useEffect } from 'react';
import {
  IssueCluster,
  IssueClusterDetail,
  TrendMetric,
} from '../../types';
import { api } from '../../services/api';
import { Badge } from '../common/Badge';
import { Modal } from '../common/Modal';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { EmptyState } from '../common/EmptyState';
import { getProductMeta } from '../../constants/catalog';
import {
  Network,
  AlertTriangle,
  Play,
  RotateCw,
  Quote,
  Eye,
  BrainCircuit,
  Users,
} from 'lucide-react';
import { Card3D } from '../common/Card3D';

interface ClustersViewProps {
  onNavigateToInvestigation: (clusterId: string) => void;
}

export const ClustersView: React.FC<ClustersViewProps> = ({
  onNavigateToInvestigation,
}) => {
  const [clusters, setClusters] = useState<IssueCluster[]>([]);
  const [trends, setTrends] = useState<Record<string, TrendMetric>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Drilldown modal
  const [selectedClusterDetail, setSelectedClusterDetail] = useState<IssueClusterDetail | null>(null);
  const [clusterHistory, setClusterHistory] = useState<TrendMetric[]>([]);

  // Run DBSCAN modal
  const [isRunModalOpen, setIsRunModalOpen] = useState<boolean>(false);
  const [eps, setEps] = useState<number>(0.4);
  const [minSamples, setMinSamples] = useState<number>(3);
  const [isRunning, setIsRunning] = useState<boolean>(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [clusterRes, trendRes] = await Promise.all([
        api.getClusters(1, 100),
        api.getTrends(undefined, 1, 100),
      ]);
      setClusters(clusterRes.items);

      // Build map of clusterId -> latest trend metric
      const trendMap: Record<string, TrendMetric> = {};
      trendRes.items.forEach((t) => {
        trendMap[t.cluster_id] = t;
      });
      setTrends(trendMap);
    } catch (err: any) {
      setError(err.message || 'Failed to load semantic clusters');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleOpenClusterDetail = async (cluster: IssueCluster) => {
    try {
      const [detail, history] = await Promise.all([
        api.getCluster(cluster.id),
        api.getClusterTrends(cluster.id),
      ]);
      setSelectedClusterDetail(detail);
      setClusterHistory(history);
    } catch (err: any) {
      alert(`Failed to load cluster details: ${err.message}`);
    }
  };

  const handleRunDBSCAN = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsRunning(true);
    try {
      const res = await api.runClustering(eps, minSamples);
      alert(
        `Clustering complete: Formed ${res.clusters_formed} clusters from ${res.total_reviews_analyzed} reviews (${res.noise_reviews_count} noise).`
      );
      setIsRunModalOpen(false);
      await api.calculateTrends();
      loadData();
    } catch (err: any) {
      alert(`DBSCAN error: ${err.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  const handleRecalculateTrends = async () => {
    setLoading(true);
    try {
      const res = await api.calculateTrends();
      alert(
        `Trends recalculated: ${res.trends_calculated} trends (${res.emerging_count} emerging anomalies).`
      );
      loadData();
    } catch (err: any) {
      alert(`Trend error: ${err.message}`);
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 3D Action Header */}
      <div className="bg-gradient-to-r from-[#07192F] via-[#092240] to-[#06172B] border border-sky-500/30 rounded-2xl p-6 shadow-xl backdrop-blur-md flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative overflow-hidden">
        <div className="absolute inset-0 cyber-grid-dense opacity-20 pointer-events-none" />
        
        <div className="relative z-10">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-sky-950/80 border border-sky-400/40 text-sky-400 shadow-md">
              <Network className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-extrabold text-white tracking-tight">
                Unsupervised Semantic Clusters & Velocity Anomalies
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                DBSCAN density clustering on 1536-dim vector embeddings with rolling 4-week z-score anomaly detection.
              </p>
            </div>
          </div>
        </div>

        <div className="relative z-10 flex items-center space-x-3 shrink-0">
          <button
            onClick={handleRecalculateTrends}
            className="flex items-center space-x-1.5 px-3.5 py-2 bg-[#071629] hover:bg-[#0E2747] text-slate-200 text-xs font-semibold rounded-xl border border-[#1B365D] hover:border-sky-500/50 transition shadow-sm active:scale-95"
          >
            <RotateCw className="w-3.5 h-3.5 text-sky-400" />
            <span>Recalculate Trends</span>
          </button>

          <button
            onClick={() => setIsRunModalOpen(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-[#004879] to-[#0076BE] hover:from-[#005B99] hover:to-[#0099D8] text-white text-xs font-bold rounded-xl shadow-[0_4px_16px_rgba(0,118,190,0.4)] transition-all duration-200 active:scale-95 border border-sky-400/40"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Run DBSCAN Clustering</span>
          </button>
        </div>
      </div>

      {/* Cluster Cards Grid */}
      {loading ? (
        <LoadingSpinner message="Evaluating vector complaint clusters..." />
      ) : error ? (
        <div className="p-8 text-center text-rose-400 text-sm">{error}</div>
      ) : clusters.length === 0 ? (
        <EmptyState
          title="No semantic clusters found"
          description="Run DBSCAN clustering across ingested reviews to automatically group complaint patterns."
          actionLabel="Run DBSCAN Pipeline"
          onAction={() => setIsRunModalOpen(true)}
          icon={<Network className="w-8 h-8 text-sky-400" />}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {clusters.map((cluster) => {
            const meta = getProductMeta(cluster.affected_product_id);
            const trend = trends[cluster.id];
            const isAnomaly = trend && trend.anomaly_score >= 2.0;
            const trajectory = trend?.trend_direction || 'stable';

            return (
              <Card3D
                key={cluster.id}
                glowOnHover={isAnomaly ? 'red' : 'cyan'}
                maxTilt={9}
                scaleOnHover={1.02}
                className={`bg-gradient-to-br from-[#0B203B]/95 to-[#061527]/95 border rounded-2xl p-5 shadow-lg flex flex-col justify-between transition-all duration-200 c1-card-sheen ${
                  isAnomaly
                    ? 'border-[#D03027] shadow-[0_8px_30px_rgba(208,48,39,0.25)] c1-red-accent-top ring-1 ring-[#D03027]/40'
                    : 'border-[#1B365D] hover:border-sky-500/50'
                }`}
              >
                <div>
                  {/* Top tags */}
                  <div className="flex items-center justify-between gap-2 mb-3 translate-z-20">
                    <span
                      className={`text-xs px-2.5 py-1 rounded-lg border font-bold truncate max-w-[190px] flex items-center space-x-1.5 shadow-sm ${meta.cardStyle}`}
                    >
                      <span>💳</span>
                      <span className="truncate">{meta.name}</span>
                    </span>

                    <div className="flex items-center space-x-1.5">
                      <Badge variant="trajectory" value={trajectory}>
                        {trajectory}
                      </Badge>
                      {isAnomaly && (
                        <span className="flex items-center text-[10px] font-black px-2.5 py-0.5 rounded-full bg-[#4C1210] text-[#FCA5A5] border border-[#D03027] animate-pulse shadow-[0_0_8px_#D03027]">
                          <AlertTriangle className="w-3 h-3 mr-1" />
                          z={trend.anomaly_score.toFixed(1)}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Title & Category */}
                  <div className="translate-z-30">
                    <h4 className="text-sm font-bold text-white mb-1 leading-snug tracking-tight">
                      {cluster.cluster_title}
                    </h4>
                    <p className="text-xs text-slate-400 mb-3 font-mono">
                      Category: {cluster.category} • Tier: {meta.tier}
                    </p>
                  </div>

                  {/* Volume & Sentiment breakdown */}
                  <div className="bg-[#051224] rounded-xl p-3.5 border border-[#1B365D] mb-3 space-y-2.5 translate-z-10 shadow-inner">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-300 font-medium flex items-center">
                        <Users className="w-3.5 h-3.5 mr-1.5 text-sky-400" />
                        {cluster.review_count} Affected Reviews
                      </span>
                      {trend && (
                        <span
                          className={`font-bold font-mono text-xs ${
                            trend.wow_change_pct > 0 ? 'text-[#FCA5A5]' : 'text-emerald-400'
                          }`}
                        >
                          {trend.wow_change_pct > 0 ? `+${trend.wow_change_pct}%` : `${trend.wow_change_pct}%`} WoW
                        </span>
                      )}
                    </div>

                    {/* Sentiment bar */}
                    <div className="w-full h-2 bg-[#040C18] rounded-full overflow-hidden flex border border-[#1B365D] shadow-inner">
                      <div
                        style={{ width: `${cluster.positive_pct}%` }}
                        className="bg-emerald-500"
                        title={`Positive: ${cluster.positive_pct}%`}
                      />
                      <div
                        style={{ width: `${cluster.neutral_pct}%` }}
                        className="bg-amber-500"
                        title={`Neutral: ${cluster.neutral_pct}%`}
                      />
                      <div
                        style={{ width: `${cluster.negative_pct}%` }}
                        className="bg-[#D03027]"
                        title={`Negative: ${cluster.negative_pct}%`}
                      />
                    </div>
                    <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                      <span className="text-[#FCA5A5]">{Math.round(cluster.negative_pct)}% Negative</span>
                      <span className="text-emerald-400">{Math.round(cluster.positive_pct)}% Positive</span>
                    </div>
                  </div>

                  {/* Representative customer quote */}
                  {cluster.representative_quotes && cluster.representative_quotes.length > 0 && (
                    <div className="p-3 bg-[#071629]/70 rounded-xl border border-sky-900/30 mb-4 translate-z-10">
                      <div className="flex items-start space-x-2">
                        <Quote className="w-3.5 h-3.5 text-sky-400 shrink-0 mt-0.5" />
                        <p className="text-xs text-slate-300 italic line-clamp-2 leading-relaxed">
                          "{cluster.representative_quotes[0]}"
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Card actions */}
                <div className="flex items-center justify-between pt-3 border-t border-[#1B365D]/80 gap-2.5 translate-z-30">
                  <button
                    onClick={() => handleOpenClusterDetail(cluster)}
                    className="flex-1 flex items-center justify-center space-x-1 py-2 px-3 rounded-xl text-xs font-semibold text-slate-200 bg-[#071629] hover:bg-[#0D2442] transition border border-[#1B365D] hover:border-sky-500/40 active:scale-95"
                  >
                    <Eye className="w-3.5 h-3.5 mr-1 text-slate-400" />
                    <span>Member Reviews</span>
                  </button>

                  <button
                    onClick={() => onNavigateToInvestigation(cluster.id)}
                    className="flex-1 flex items-center justify-center space-x-1 py-2 px-3 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-sky-600 to-[#0076BE] hover:from-sky-500 hover:to-[#0099D8] transition shadow-[0_4px_12px_rgba(56,189,248,0.3)] active:scale-95 border border-sky-400/40"
                  >
                    <BrainCircuit className="w-3.5 h-3.5 mr-1" />
                    <span>LangGraph HITL</span>
                  </button>
                </div>
              </Card3D>
            );
          })}
        </div>
      )}

      {/* Cluster Detail Modal (Member Reviews & Trend History) */}
      {selectedClusterDetail && (
        <Modal
          isOpen={!!selectedClusterDetail}
          onClose={() => setSelectedClusterDetail(null)}
          title={selectedClusterDetail.cluster_title}
          subtitle={`Product: ${getProductMeta(selectedClusterDetail.affected_product_id).name} • Category: ${selectedClusterDetail.category}`}
          maxWidth="max-w-4xl"
        >
          <div className="space-y-5">
            {/* Representative Quotes Carousel / List */}
            {selectedClusterDetail.representative_quotes &&
              selectedClusterDetail.representative_quotes.length > 0 && (
                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800">
                  <h5 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center">
                    <Quote className="w-3.5 h-3.5 mr-1.5 text-sky-400" />
                    Representative Customer Evidence
                  </h5>
                  <div className="space-y-2">
                    {selectedClusterDetail.representative_quotes.map((q, idx) => (
                      <p
                        key={idx}
                        className="text-xs text-slate-300 italic pl-3 border-l-2 border-sky-500 leading-relaxed"
                      >
                        "{q}"
                      </p>
                    ))}
                  </div>
                </div>
              )}

            {/* Historical Velocity Trends */}
            {clusterHistory.length > 0 && (
              <div>
                <h5 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Historical Weekly Volume Velocity ({clusterHistory.length} periods)
                </h5>
                <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-none">
                  {clusterHistory.map((h) => (
                    <div
                      key={h.id}
                      className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-xs shrink-0 min-w-[120px]"
                    >
                      <span className="text-slate-400 text-[10px] block">
                        {h.period_start ? h.period_start.slice(5, 10) : 'Period'}
                      </span>
                      <span className="font-bold text-slate-100 block">
                        {h.current_volume} reviews
                      </span>
                      <span
                        className={`text-[10px] font-mono block ${
                          h.anomaly_score >= 2.0 ? 'text-rose-400 font-semibold' : 'text-slate-400'
                        }`}
                      >
                        z={h.anomaly_score.toFixed(1)} {h.anomaly_score >= 2.0 && '⚠️'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Member Reviews Section */}
            <div>
              <h5 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">
                Member Reviews in this Semantic Cluster ({selectedClusterDetail.reviews?.length || 0})
              </h5>

              <div className="max-h-72 overflow-y-auto space-y-2 pr-1 divide-y divide-slate-800">
                {selectedClusterDetail.reviews && selectedClusterDetail.reviews.length > 0 ? (
                  selectedClusterDetail.reviews.map((item, idx) => (
                    <div key={idx} className="pt-2 pb-2 text-xs space-y-1">
                      <div className="flex items-center justify-between text-slate-400">
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-slate-200">
                            {item.review.rating}★
                          </span>
                          <span className="text-slate-400">
                            {item.review.created_at?.slice(0, 10)}
                          </span>
                        </div>
                        <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-sky-300 font-mono">
                          similarity: {Math.round(item.similarity_score * 100)}%
                        </span>
                      </div>
                      <p className="text-slate-300 italic leading-relaxed">
                        "{item.review.review_text}"
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400">No member reviews loaded.</p>
                )}
              </div>
            </div>

            {/* Action footer */}
            <div className="flex justify-end pt-3 border-t border-slate-800">
              <button
                onClick={() => {
                  const id = selectedClusterDetail.id;
                  setSelectedClusterDetail(null);
                  onNavigateToInvestigation(id);
                }}
                className="flex items-center space-x-1.5 px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded-lg transition"
              >
                <BrainCircuit className="w-4 h-4" />
                <span>Launch LangGraph Investigation</span>
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Run DBSCAN Modal */}
      {isRunModalOpen && (
        <Modal
          isOpen={isRunModalOpen}
          onClose={() => setIsRunModalOpen(false)}
          title="Run DBSCAN Unsupervised Clustering"
          subtitle="Form dense complaint clusters from 1536-dimensional embeddings."
        >
          <form onSubmit={handleRunDBSCAN} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Cosine Distance Epsilon (ε): {eps}
              </label>
              <input
                type="range"
                min="0.1"
                max="0.8"
                step="0.05"
                value={eps}
                onChange={(e) => setEps(Number(e.target.value))}
                className="w-full accent-sky-500"
              />
              <span className="text-[11px] text-slate-400 block mt-1">
                Lower ε = tighter clusters; Higher ε = broader clusters. (Default: 0.40)
              </span>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Minimum Samples per Cluster: {minSamples}
              </label>
              <input
                type="number"
                min="2"
                max="20"
                value={minSamples}
                onChange={(e) => setMinSamples(Number(e.target.value))}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200"
              />
              <span className="text-[11px] text-slate-400 block mt-1">
                Minimum review points to form a persistent cluster. (Default: 3)
              </span>
            </div>

            <div className="flex justify-end space-x-3 pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsRunModalOpen(false)}
                className="px-4 py-2 text-xs text-slate-400 hover:text-slate-200 bg-slate-800 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isRunning}
                className="px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg transition disabled:opacity-50"
              >
                {isRunning ? 'Clustering...' : 'Execute Clustering'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};

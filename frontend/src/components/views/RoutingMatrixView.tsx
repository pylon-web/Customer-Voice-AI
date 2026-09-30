import React, { useState, useEffect } from 'react';
import {
  TeamWithRules,
  Recommendation,
  IssueCluster,
  TrendMetric,
  Product,
} from '../../types';
import { api } from '../../services/api';
import { Badge } from '../common/Badge';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { EmptyState } from '../common/EmptyState';
import { Card3D } from '../common/Card3D';
import { getProductMeta } from '../../constants/catalog';
import {
  getTeamMeta,
  TEAM_ALIAS_MAP,
  TeamMeta,
} from '../../constants/teams';
import {
  Smartphone,
  CreditCard,
  Plane,
  Coffee,
  ShieldCheck,
  ShoppingBag,
  Headphones,
  Users,
  Clock,
  BookOpen,
  MessageSquare,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Sparkles,
  Layers,
  Zap,
} from 'lucide-react';

interface RoutingMatrixViewProps {
  products: Product[];
}

// Icon helper per canonical team ID
function getTeamIcon(teamId: string) {
  const canonical = TEAM_ALIAS_MAP[teamId] || teamId;
  switch (canonical) {
    case 'digital_engineering_mobile':
      return Smartphone;
    case 'payments_operations':
      return CreditCard;
    case 'travel_lounges_product':
      return Plane;
    case 'cafe_operations':
      return Coffee;
    case 'digital_ai_security':
      return ShieldCheck;
    case 'shopping_engineering':
      return ShoppingBag;
    case 'customer_experience':
    default:
      return Headphones;
  }
}

export const RoutingMatrixView: React.FC<RoutingMatrixViewProps> = () => {
  const [teams, setTeams] = useState<TeamWithRules[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [clusters, setClusters] = useState<Record<string, IssueCluster>>({});
  const [trends, setTrends] = useState<Record<string, TrendMetric>>({});
  const [selectedTeamId, setSelectedTeamId] = useState<string>('digital_engineering_mobile');
  const [viewTab, setViewTab] = useState<'issues' | 'playbook'>('issues');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [teamsRes, recsRes, clustersRes, trendsRes] = await Promise.all([
        api.getTeams(),
        api.getRecommendations(1, 100),
        api.getClusters(1, 100),
        api.getTrends(undefined, 1, 100),
      ]);

      setTeams(teamsRes);
      setRecommendations(recsRes.items);

      // Build cluster map
      const clusterMap: Record<string, IssueCluster> = {};
      clustersRes.items.forEach((c) => {
        clusterMap[c.id] = c;
      });
      setClusters(clusterMap);

      // Build trends map
      const trendMap: Record<string, TrendMetric> = {};
      trendsRes.items.forEach((t) => {
        trendMap[t.cluster_id] = t;
      });
      setTrends(trendMap);

      // Set default selected team if exists
      if (teamsRes.length > 0) {
        setSelectedTeamId(TEAM_ALIAS_MAP[teamsRes[0].id] || teamsRes[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load team routing intelligence');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Map recommendations to teams by canonical ID
  const teamWorkloadMap: Record<
    string,
    {
      team: TeamWithRules;
      meta: TeamMeta;
      recommendations: Recommendation[];
      totalReviews: number;
      anomalyCount: number;
    }
  > = {};

  // Initialize with all known teams
  teams.forEach((t) => {
    const canonicalId = TEAM_ALIAS_MAP[t.id] || t.id;
    teamWorkloadMap[canonicalId] = {
      team: t,
      meta: getTeamMeta(canonicalId),
      recommendations: [],
      totalReviews: 0,
      anomalyCount: 0,
    };
  });

  // Assign recommendations to teams
  recommendations.forEach((rec) => {
    const canonicalId = TEAM_ALIAS_MAP[rec.suggested_team_id] || rec.suggested_team_id;
    if (!teamWorkloadMap[canonicalId]) {
      // Fallback team or unknown
      const fallbackId = 'customer_experience';
      if (teamWorkloadMap[fallbackId]) {
        teamWorkloadMap[fallbackId].recommendations.push(rec);
        const cluster = clusters[rec.cluster_id];
        if (cluster) {
          teamWorkloadMap[fallbackId].totalReviews += cluster.review_count || 0;
          const trend = trends[cluster.id];
          if (trend && trend.anomaly_score >= 2.0) {
            teamWorkloadMap[fallbackId].anomalyCount += 1;
          }
        }
      }
      return;
    }

    teamWorkloadMap[canonicalId].recommendations.push(rec);
    const cluster = clusters[rec.cluster_id];
    if (cluster) {
      teamWorkloadMap[canonicalId].totalReviews += cluster.review_count || 0;
      const trend = trends[cluster.id];
      if (trend && trend.anomaly_score >= 2.0) {
        teamWorkloadMap[canonicalId].anomalyCount += 1;
      }
    }
  });

  // Totals across all teams
  const totalRoutedIssues = recommendations.length;
  const totalAffectedReviews = Object.values(teamWorkloadMap).reduce(
    (acc, curr) => acc + curr.totalReviews,
    0
  );
  const totalAnomalies = Object.values(teamWorkloadMap).reduce(
    (acc, curr) => acc + curr.anomalyCount,
    0
  );

  const selectedTeamWorkload = teamWorkloadMap[selectedTeamId] || Object.values(teamWorkloadMap)[0];
  const SelectedIcon = selectedTeamWorkload ? getTeamIcon(selectedTeamWorkload.team.id) : Users;

  return (
    <div className="space-y-6">
      {/* 3D Header with Live Telemetry */}
      <div className="bg-gradient-to-r from-[#07192F]/95 via-[#0B203B]/95 to-[#06172B]/95 border border-sky-500/30 rounded-2xl p-6 sm:p-7 shadow-[0_16px_40px_rgba(0,0,0,0.6)] relative overflow-hidden backdrop-blur-xl">
        <div className="absolute inset-0 cyber-grid-dense opacity-20 pointer-events-none" />
        <div className="absolute -top-20 -right-20 w-80 h-80 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="beam-line absolute bottom-0 left-0 right-0 h-0.5 bg-[#1B365D]" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-5">
          <div className="space-y-1.5">
            <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[#38BDF8]">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span>Capital One Multi-Department Dispatch Hub</span>
              <span className="text-slate-500">•</span>
              <span className="text-slate-300 font-mono">7 Enterprise Teams</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight drop-shadow-md">
              Team Workload & <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#38BDF8] via-sky-300 to-[#7DD3FC]">Issue Routing Intelligence</span>
            </h2>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              Real-time operational dispatch tracking investigated complaint clusters, affected customer volumes, prioritized SLAs, and active remediation playbooks routed across all 7 Capital One departments.
            </p>
          </div>

          <div className="flex items-center space-x-2 shrink-0">
            <div className="px-3.5 py-1.5 rounded-xl bg-[#051121] border border-[#1B365D] text-xs text-slate-300 flex items-center space-x-2 font-mono">
              <Zap className="w-4 h-4 text-emerald-400" />
              <span>Auto-Router: <strong className="text-emerald-400 font-bold">ONLINE</strong></span>
            </div>
          </div>
        </div>
      </div>

      {/* 4 Holographic 3D Stat Tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Tile 1: Total Routed Issues */}
        <Card3D
          glowOnHover="cyan"
          maxTilt={8}
          scaleOnHover={1.02}
          className="bg-gradient-to-br from-[#0B203B]/90 to-[#071527]/90 border border-[#1B365D] rounded-xl p-5 shadow-lg backdrop-blur-md c1-card-sheen"
        >
          <div className="flex items-center justify-between translate-z-20">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Routed Issue Packages
            </span>
            <div className="p-2 rounded-xl bg-gradient-to-br from-[#004879] to-[#041E38] text-sky-300 border border-sky-500/40 shadow-md">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2 translate-z-30">
            <span className="text-3xl font-black tracking-tight text-white font-mono drop-shadow">
              {totalRoutedIssues}
            </span>
            <span className="text-xs text-slate-400">assigned clusters</span>
          </div>
          <p className="mt-2 text-xs text-slate-400 translate-z-10">
            Categorized and routed via regex rules
          </p>
        </Card3D>

        {/* Tile 2: Total Affected Customers */}
        <Card3D
          glowOnHover="emerald"
          maxTilt={8}
          scaleOnHover={1.02}
          className="bg-gradient-to-br from-[#0B203B]/90 to-[#071527]/90 border border-[#1B365D] rounded-xl p-5 shadow-lg backdrop-blur-md c1-card-sheen"
        >
          <div className="flex items-center justify-between translate-z-20">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Affected Reviewers
            </span>
            <div className="p-2 rounded-xl bg-emerald-950/70 text-emerald-400 border border-emerald-600/50 shadow-md">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2 translate-z-30">
            <span className="text-3xl font-black tracking-tight text-emerald-400 font-mono drop-shadow">
              {totalAffectedReviews.toLocaleString()}
            </span>
            <span className="text-xs text-slate-400 font-mono">reviews impacted</span>
          </div>
          <p className="mt-2 text-xs text-slate-400 translate-z-10">
            Customer feedback requiring remediation
          </p>
        </Card3D>

        {/* Tile 3: Velocity Anomalies */}
        <Card3D
          glowOnHover="red"
          maxTilt={8}
          scaleOnHover={1.02}
          className="bg-gradient-to-br from-[#1A0B10]/95 to-[#0B1527]/95 border border-[#D03027]/70 rounded-xl p-5 shadow-lg backdrop-blur-md c1-card-sheen c1-red-accent-top"
        >
          <div className="flex items-center justify-between translate-z-20">
            <span className="text-xs font-bold uppercase tracking-wider text-[#FCA5A5]">
              Surge Alerts (z ≥ 2.0)
            </span>
            <div className="p-2 rounded-xl bg-[#4C1210] text-[#FCA5A5] border border-[#D03027] shadow-[0_0_12px_rgba(208,48,39,0.5)]">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2 translate-z-30">
            <span className="text-3xl font-black tracking-tight text-[#FCA5A5] font-mono drop-shadow-[0_2px_8px_rgba(208,48,39,0.6)]">
              {totalAnomalies}
            </span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#4C1210] text-[#FCA5A5] border border-[#D03027] font-mono font-bold animate-pulse">
              P1/P2 URGENT
            </span>
          </div>
          <p className="mt-2 text-xs text-[#FCA5A5]/80 translate-z-10">
            Fastest rising complaint patterns
          </p>
        </Card3D>

        {/* Tile 4: Enterprise Coverage */}
        <Card3D
          glowOnHover="amber"
          maxTilt={8}
          scaleOnHover={1.02}
          className="bg-gradient-to-br from-[#191306]/95 to-[#0B1829]/95 border border-[#B45309]/70 rounded-xl p-5 shadow-lg backdrop-blur-md c1-card-sheen"
        >
          <div className="flex items-center justify-between translate-z-20">
            <span className="text-xs font-bold uppercase tracking-wider text-[#FDE68A]">
              Department Coverage
            </span>
            <div className="p-2 rounded-xl bg-[#3D2506] text-[#FDE68A] border border-[#B45309] shadow-[0_0_12px_rgba(245,158,11,0.3)]">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2 translate-z-30">
            <span className="text-3xl font-black tracking-tight text-[#FDE68A] font-mono drop-shadow">
              {teams.length} / 7
            </span>
            <span className="text-xs text-slate-400">teams active</span>
          </div>
          <p className="mt-2 text-xs text-[#FDE68A]/80 translate-z-10">
            100% catalog coverage across 19 products
          </p>
        </Card3D>
      </div>

      {/* Multi-Colored Department Capacity Distribution Bar */}
      <div className="bg-[#071629]/90 border border-sky-500/20 rounded-2xl p-5 shadow-lg backdrop-blur-md space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-sky-400" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Live Issue Distribution Across Capital One Departments
            </h4>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">
            {totalRoutedIssues} total packages routed
          </span>
        </div>

        {/* Segmented capacity bar */}
        <div className="w-full h-4 bg-[#040C18] rounded-full overflow-hidden flex border border-[#1B365D] shadow-inner p-0.5">
          {Object.entries(teamWorkloadMap).map(([tid, data]) => {
            const count = data.recommendations.length;
            const pct = totalRoutedIssues > 0 ? (count / totalRoutedIssues) * 100 : 0;
            if (pct === 0) return null;

            // Pick distinct colors
            let barColor = 'bg-sky-500';
            if (tid.includes('mobile')) barColor = 'bg-[#0284C7]';
            else if (tid.includes('travel')) barColor = 'bg-[#6366F1]';
            else if (tid.includes('payments')) barColor = 'bg-[#F59E0B]';
            else if (tid.includes('cafe')) barColor = 'bg-[#10B981]';
            else if (tid.includes('security')) barColor = 'bg-[#A855F7]';
            else if (tid.includes('shopping')) barColor = 'bg-[#EC4899]';
            else barColor = 'bg-slate-500';

            return (
              <div
                key={tid}
                style={{ width: `${pct}%` }}
                className={`${barColor} hover:opacity-80 transition-all cursor-pointer`}
                title={`${data.meta.shortName}: ${count} issues (${Math.round(pct)}%)`}
                onClick={() => setSelectedTeamId(tid)}
              />
            );
          })}
        </div>

        {/* Legend pills */}
        <div className="flex flex-wrap gap-2 text-[11px] pt-1">
          {Object.entries(teamWorkloadMap).map(([tid, data]) => {
            const isSelected = selectedTeamId === tid;
            const count = data.recommendations.length;
            return (
              <button
                key={tid}
                onClick={() => setSelectedTeamId(tid)}
                className={`px-2.5 py-1 rounded-lg border font-mono transition-all flex items-center space-x-1.5 ${
                  isSelected
                    ? 'bg-sky-950/80 text-white border-sky-400 shadow-[0_0_10px_rgba(56,189,248,0.3)]'
                    : 'bg-[#051121] text-slate-400 border-[#1B365D] hover:text-slate-200'
                }`}
              >
                <span className="w-2 h-2 rounded-full bg-sky-400" />
                <span>{data.meta.shortName}</span>
                <span className="font-bold text-white">({count})</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Interactive Deck: 7 Teams Selector & Detailed Issues Inspector */}
      {loading ? (
        <LoadingSpinner message="Correlating team routing workloads and active issues..." />
      ) : error ? (
        <div className="p-8 text-center text-rose-400 text-sm">{error}</div>
      ) : (
        <div className="space-y-6">
          {/* 7 Interactive 3D Team Dossier Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {Object.entries(teamWorkloadMap).map(([tid, data]) => {
              const Icon = getTeamIcon(tid);
              const isSelected = selectedTeamId === tid;
              const count = data.recommendations.length;

              return (
                <Card3D
                  key={tid}
                  glowOnHover={isSelected ? 'cyan' : count > 0 ? 'amber' : 'none'}
                  maxTilt={10}
                  scaleOnHover={1.03}
                  onClick={() => setSelectedTeamId(tid)}
                  className={`p-5 rounded-2xl border cursor-pointer transition-all duration-300 backdrop-blur-md relative ${
                    isSelected
                      ? 'bg-gradient-to-br from-[#0F2847] to-[#071629] border-sky-400 shadow-[0_0_30px_rgba(56,189,248,0.35)] ring-2 ring-sky-400/50 -translate-y-1'
                      : 'bg-gradient-to-br from-[#0B203B]/90 to-[#061527]/90 border-[#1B365D] hover:border-sky-500/50'
                  }`}
                >
                  {/* Top Bar: Icon & Slack tag */}
                  <div className="flex items-center justify-between gap-2 mb-3 translate-z-20">
                    <div
                      className={`w-10 h-10 rounded-xl bg-gradient-to-br ${data.meta.gradient} border border-white/10 flex items-center justify-center shadow-lg text-white`}
                    >
                      <Icon className="w-5 h-5" />
                    </div>

                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#040C18] text-slate-300 border border-white/10 truncate max-w-[140px]">
                      {data.meta.slackChannel}
                    </span>
                  </div>

                  {/* Team Name */}
                  <div className="translate-z-30">
                    <h4 className="font-extrabold text-sm text-white tracking-tight leading-snug">
                      {data.meta.name}
                    </h4>
                    <p className="text-[11px] text-slate-400 line-clamp-2 mt-1 leading-relaxed">
                      {data.meta.description}
                    </p>
                  </div>

                  {/* Volume and Anomaly badges */}
                  <div className="mt-4 pt-3 border-t border-[#1B365D]/80 flex items-center justify-between translate-z-20 text-xs">
                    <div className="flex items-center space-x-1.5">
                      <span className="font-mono font-black text-white text-base">
                        {count}
                      </span>
                      <span className="text-slate-400 text-[11px]">
                        {count === 1 ? 'Issue' : 'Issues'}
                      </span>
                    </div>

                    <div className="flex items-center space-x-1.5">
                      <span className="text-[11px] px-2 py-0.5 rounded-full bg-[#051121] text-sky-300 border border-sky-600/40 font-mono">
                        {data.totalReviews} rev
                      </span>
                      {data.anomalyCount > 0 && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#4C1210] text-[#FCA5A5] border border-[#D03027] animate-pulse">
                          {data.anomalyCount} spike
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Active selection dot */}
                  {isSelected && (
                    <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-12 h-1 bg-sky-400 rounded-full shadow-[0_0_12px_#38BDF8]" />
                  )}
                </Card3D>
              );
            })}
          </div>

          {/* Selected Team Detailed Dossier & Routed Issues Inspector */}
          {selectedTeamWorkload && (
            <div className="bg-gradient-to-b from-[#091D36] via-[#071629] to-[#040C18] border border-sky-500/40 rounded-2xl p-6 sm:p-7 shadow-2xl space-y-6 relative overflow-hidden backdrop-blur-xl">
              <div className="absolute inset-0 cyber-grid-dense opacity-20 pointer-events-none" />

              {/* Department Dossier Header */}
              <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1B365D]/80 pb-5">
                <div className="flex items-center space-x-3.5">
                  <div
                    className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${selectedTeamWorkload.meta.gradient} border border-sky-400/40 flex items-center justify-center text-white shadow-xl`}
                  >
                    <SelectedIcon className="w-6 h-6 text-sky-300" />
                  </div>

                  <div>
                    <div className="flex items-center space-x-2.5 flex-wrap">
                      <h3 className="text-xl font-black text-white tracking-tight">
                        {selectedTeamWorkload.meta.name}
                      </h3>
                      <span className="text-xs px-2.5 py-0.5 rounded-full bg-sky-950 text-sky-300 border border-sky-600/50 font-mono font-semibold">
                        SLA Target: {selectedTeamWorkload.meta.defaultSlaHours}h
                      </span>
                    </div>
                    <div className="flex items-center space-x-3 text-xs text-slate-400 mt-1 font-mono">
                      <span>Slack: <strong className="text-sky-400">{selectedTeamWorkload.meta.slackChannel}</strong></span>
                      <span>•</span>
                      <span>Lead: <a href={`mailto:${selectedTeamWorkload.meta.leadEmail}`} className="text-slate-300 hover:text-white underline">{selectedTeamWorkload.meta.leadEmail}</a></span>
                    </div>
                  </div>
                </div>

                {/* View Switcher: Issues vs Playbook */}
                <div className="flex items-center space-x-2 shrink-0 bg-[#051121] p-1 rounded-xl border border-[#1B365D]">
                  <button
                    onClick={() => setViewTab('issues')}
                    className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                      viewTab === 'issues'
                        ? 'bg-sky-600 text-white shadow-[0_2px_10px_rgba(56,189,248,0.3)]'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>Routed Issues ({selectedTeamWorkload.recommendations.length})</span>
                  </button>

                  <button
                    onClick={() => setViewTab('playbook')}
                    className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                      viewTab === 'playbook'
                        ? 'bg-sky-600 text-white shadow-[0_2px_10px_rgba(56,189,248,0.3)]'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <BookOpen className="w-3.5 h-3.5" />
                    <span>Remediation Playbook</span>
                  </button>
                </div>
              </div>

              {/* Active Matching Keywords Banner */}
              <div className="relative z-10 flex items-center space-x-2 flex-wrap gap-y-1.5 p-3 rounded-xl bg-[#051121] border border-[#1B365D] text-xs">
                <span className="text-slate-400 font-bold font-mono text-[11px] uppercase tracking-wider">
                  Configured Regex Routing Patterns:
                </span>
                {selectedTeamWorkload.team.routing_rules && selectedTeamWorkload.team.routing_rules.length > 0 ? (
                  selectedTeamWorkload.team.routing_rules.map((rule) => (
                    <span
                      key={rule.id}
                      className="px-2.5 py-0.5 rounded-md bg-[#071629] text-sky-300 font-mono text-[11px] border border-sky-600/30"
                    >
                      {rule.pattern} (P{rule.priority})
                    </span>
                  ))
                ) : (
                  <span className="text-slate-500 italic">Default fallback recipient</span>
                )}
              </div>

              {/* TAB A: Routed Issues for this Team */}
              {viewTab === 'issues' && (
                <div className="relative z-10 space-y-4">
                  {selectedTeamWorkload.recommendations.length === 0 ? (
                    <EmptyState
                      title="No issues routed to this team"
                      description="This department currently has a clean queue with no open customer complaint clusters assigned."
                      icon={<CheckCircle2 className="w-8 h-8 text-emerald-400" />}
                    />
                  ) : (
                    <div className="grid grid-cols-1 gap-4">
                      {selectedTeamWorkload.recommendations.map((rec) => {
                        const cluster = clusters[rec.cluster_id];
                        const meta = cluster ? getProductMeta(cluster.affected_product_id) : null;
                        const trend = trends[rec.cluster_id];
                        const isAnomaly = trend && trend.anomaly_score >= 2.0;

                        return (
                          <Card3D
                            key={rec.id}
                            glowOnHover={isAnomaly ? 'red' : 'cyan'}
                            maxTilt={6}
                            scaleOnHover={1.01}
                            className={`p-5 rounded-2xl border bg-gradient-to-br from-[#0B203B]/95 to-[#061527]/95 shadow-xl space-y-4 backdrop-blur-md c1-card-sheen ${
                              isAnomaly
                                ? 'border-[#D03027] ring-1 ring-[#D03027]/40 c1-red-accent-top'
                                : 'border-[#1B365D] hover:border-sky-500/50'
                            }`}
                          >
                            {/* Card Top: Product, Title, Status, Priority */}
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#1B365D]/80 pb-3 translate-z-20">
                              <div className="flex items-center space-x-2.5 flex-wrap gap-y-1">
                                {meta && (
                                  <span
                                    className={`text-xs px-2.5 py-1 rounded-lg border font-bold flex items-center space-x-1.5 shadow-sm ${meta.cardStyle}`}
                                  >
                                    <span>💳</span>
                                    <span>{meta.name}</span>
                                  </span>
                                )}

                                <h4 className="text-sm font-extrabold text-white tracking-tight">
                                  {rec.cluster_title || cluster?.cluster_title || `Issue #${rec.id.slice(0, 8)}`}
                                </h4>

                                <Badge variant="status" value={rec.status}>
                                  {rec.status.replace('_', ' ').toUpperCase()}
                                </Badge>
                              </div>

                              <div className="flex items-center space-x-2 text-xs font-mono">
                                {isAnomaly ? (
                                  <span className="flex items-center text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-[#4C1210] text-[#FCA5A5] border border-[#D03027] animate-pulse">
                                    <AlertTriangle className="w-3.5 h-3.5 mr-1" />
                                    P1_CRITICAL (24h SLA)
                                  </span>
                                ) : (
                                  <span className="px-2.5 py-0.5 rounded-full bg-[#051121] text-sky-300 border border-sky-600/40">
                                    P2_HIGH (48h SLA)
                                  </span>
                                )}

                                {cluster && (
                                  <span className="px-2.5 py-0.5 rounded-full bg-[#051121] text-slate-300 border border-white/10 font-bold">
                                    {cluster.review_count} Affected Customers
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* 3 Core Structured Panels: Evidence vs Hypothesis vs Action */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 translate-z-20">
                              {/* 1. Customer Evidence */}
                              <div className="p-3.5 rounded-xl bg-[#051224] border border-sky-500/30 flex flex-col justify-between shadow-inner">
                                <div>
                                  <span className="text-[11px] font-bold uppercase tracking-wider text-sky-400 block mb-1 font-mono">
                                    Observed Customer Evidence:
                                  </span>
                                  <p className="text-xs text-sky-100 italic leading-relaxed">
                                    "{rec.observed_evidence}"
                                  </p>
                                </div>
                                <span className="text-[10px] text-sky-300/70 font-mono mt-2 pt-2 border-t border-sky-900/30">
                                  ✓ Ground truth verbatim feedback
                                </span>
                              </div>

                              {/* 2. Investigation Hypothesis */}
                              <div className="p-3.5 rounded-xl bg-[#120B21] border border-purple-500/30 flex flex-col justify-between shadow-inner">
                                <div>
                                  <span className="text-[11px] font-bold uppercase tracking-wider text-purple-400 block mb-1 font-mono">
                                    Root Cause Hypothesis:
                                  </span>
                                  <p className="text-xs text-purple-200 leading-relaxed">
                                    {rec.investigation_hypothesis}
                                  </p>
                                </div>
                                <span className="text-[10px] text-purple-300/70 font-mono mt-2 pt-2 border-t border-purple-900/30">
                                  ⚠️ Tentative engineering hypothesis
                                </span>
                              </div>

                              {/* 3. Action Plan for this Team */}
                              <div className="p-3.5 rounded-xl bg-[#061F14] border border-emerald-500/30 flex flex-col justify-between shadow-inner">
                                <div>
                                  <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-400 block mb-1 font-mono">
                                    Remediation Plan for this Team:
                                  </span>
                                  <p className="text-xs text-emerald-100 leading-relaxed font-medium">
                                    {rec.recommended_action}
                                  </p>
                                </div>
                                <span className="text-[10px] text-emerald-300/70 font-mono mt-2 pt-2 border-t border-emerald-900/30">
                                  ⚡ Target: {selectedTeamWorkload.meta.shortName}
                                </span>
                              </div>
                            </div>
                          </Card3D>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* TAB B: Remediation Playbook & Public Response Guidance */}
              {viewTab === 'playbook' && (
                <div className="relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-5">
                  {/* Department Remediation Playbook */}
                  <div className="p-5 rounded-2xl bg-[#051121] border border-emerald-600/40 shadow-xl space-y-3">
                    <div className="flex items-center space-x-2 text-emerald-400 font-bold text-xs uppercase tracking-wider">
                      <BookOpen className="w-4 h-4" />
                      <span>{selectedTeamWorkload.meta.name} Playbook</span>
                    </div>
                    <p className="text-xs text-slate-300">
                      Standard operating procedure executed by engineers when a complaint cluster reaches this team:
                    </p>
                    <ul className="space-y-2 pt-2 text-xs text-emerald-100 leading-relaxed font-mono">
                      {selectedTeamWorkload.meta.playbook.map((step, idx) => (
                        <li key={idx} className="flex items-start bg-emerald-950/30 p-2.5 rounded-lg border border-emerald-800/30">
                          <CheckCircle2 className="w-4 h-4 mr-2 text-emerald-400 shrink-0 mt-0.5" />
                          <span>{step}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Public Review Response Guidance */}
                  <div className="p-5 rounded-2xl bg-[#051121] border border-sky-600/40 shadow-xl space-y-3">
                    <div className="flex items-center space-x-2 text-sky-400 font-bold text-xs uppercase tracking-wider">
                      <MessageSquare className="w-4 h-4" />
                      <span>Public Store / Channel Response Guidance</span>
                    </div>
                    <p className="text-xs text-slate-300">
                      Pre-approved customer response language for App Store, Google Play, Google Places, and Chrome Web Store:
                    </p>
                    <div className="p-4 rounded-xl bg-[#071629] border border-sky-900/40 text-xs text-sky-100 italic leading-relaxed">
                      "{selectedTeamWorkload.meta.publicResponse}"
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono">
                      Policy: Adheres to Responsible AI boundaries; does not disclose proprietary banking internals.
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

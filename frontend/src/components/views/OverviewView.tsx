import React from 'react';
import {
  DashboardOverviewResponse,
  TrendMetric,
} from '../../types';
import { getProductMeta } from '../../constants/catalog';
import {
  MessageSquare,
  TrendingUp,
  AlertTriangle,
  Star,
  ArrowUpRight,
  ShieldAlert,
  CreditCard,
  Zap,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { Card3D } from '../common/Card3D';

interface OverviewViewProps {
  overview: DashboardOverviewResponse | null;
  trends: TrendMetric[];
  onNavigateTab: (tab: any) => void;
  onTriggerClustering: () => void;
  onTriggerTrends: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  overview,
  trends,
  onNavigateTab,
  onTriggerClustering,
  onTriggerTrends,
}) => {
  const total = overview?.total_reviews || 0;
  const pos = overview?.sentiment_counts.positive || 0;
  const neu = overview?.sentiment_counts.neutral || 0;
  const neg = overview?.sentiment_counts.negative || 0;

  // Calculate Net Sentiment Index: (% Pos - % Neg)
  const netSentiment =
    total > 0 ? Math.round(((pos - neg) / total) * 100) : 0;

  // Chart data from trends or calibrated 6-week window
  const chartData =
    trends.length > 0
      ? trends.slice(0, 10).map((t, idx) => ({
          period: t.period_start ? t.period_start.slice(5, 10) : `W${idx + 1}`,
          current: t.current_volume,
          baseline: Math.round(t.baseline_4wk_avg),
          cluster: t.cluster_title || `Issue #${idx + 1}`,
        }))
      : [
          { period: 'Aug 18', current: 120, baseline: 110 },
          { period: 'Aug 25', current: 145, baseline: 118 },
          { period: 'Sep 01', current: 190, baseline: 125 },
          { period: 'Sep 08', current: 310, baseline: 140 },
          { period: 'Sep 15', current: 480, baseline: 165 },
          { period: 'Sep 22', current: 410, baseline: 180 },
        ];

  return (
    <div className="space-y-6">
      {/* 3D Capital One Welcome Hero Banner */}
      <div className="bg-gradient-to-r from-[#061427] via-[#0B2545] to-[#081C33] border border-sky-500/30 rounded-2xl p-6 sm:p-7 shadow-[0_16px_40px_rgba(0,0,0,0.6)] relative overflow-hidden backdrop-blur-xl">
        {/* Glowing Orbs & Cyber Telemetry Beam */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-[#D03027]/15 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20"></div>
        <div className="absolute -bottom-10 -left-10 w-80 h-80 bg-sky-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="beam-line absolute bottom-0 left-0 right-0 h-0.5 bg-[#1B365D]" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-5">
          <div className="space-y-1.5">
            <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[#38BDF8]">
              <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping"></span>
              <span>Capital One Product Intelligence Engine</span>
              <span className="text-slate-500">•</span>
              <span className="text-slate-300 font-mono">19 Catalog Products</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight drop-shadow-md">
              Customer Voice <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#38BDF8] via-sky-300 to-[#7DD3FC]">Executive Intelligence</span>
            </h2>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              Multi-channel public intelligence console across 5 platforms with automated vector DBSCAN clustering, statistical z-score velocity surveillance, and LangGraph root cause investigation.
            </p>
          </div>

          <div className="flex items-center space-x-3 shrink-0">
            <button
              onClick={() => onNavigateTab('reviews')}
              className="px-5 py-2.5 bg-gradient-to-r from-[#D03027] to-[#B81D24] hover:from-[#E13B32] hover:to-[#D03027] text-white text-xs font-bold rounded-xl shadow-[0_6px_20px_rgba(208,48,39,0.4)] transition-all duration-200 transform hover:scale-105 active:scale-95 flex items-center space-x-2 border border-red-400/40"
            >
              <span>Explore 10k Reviews</span>
              <ArrowUpRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* 4 Interactive 3D KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Reviews */}
        <Card3D
          glowOnHover="cyan"
          maxTilt={9}
          scaleOnHover={1.03}
          className="bg-gradient-to-br from-[#0B203B]/90 to-[#071527]/90 border border-[#1B365D] rounded-xl p-5 shadow-lg backdrop-blur-md c1-card-sheen"
        >
          <div className="flex items-center justify-between translate-z-20">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Total Ingested Feedback
            </span>
            <div className="p-2 rounded-xl bg-gradient-to-br from-[#004879] to-[#041E38] text-sky-300 border border-sky-500/40 shadow-md">
              <MessageSquare className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2 translate-z-30">
            <span className="text-3xl font-black tracking-tight text-white font-mono drop-shadow">
              {total.toLocaleString()}
            </span>
            {overview && (
              <span className="flex items-center text-xs font-bold text-[#FBBF24] bg-amber-950/60 px-2 py-0.5 rounded-full border border-amber-500/40">
                <Star className="w-3.5 h-3.5 fill-current mr-1 text-[#FBBF24]" />
                {overview.avg_rating.toFixed(1)} avg
              </span>
            )}
          </div>
          <p className="mt-2 text-xs text-slate-400 translate-z-10">
            Across 5 public review channels & 19 products
          </p>
        </Card3D>

        {/* Card 2: Net Sentiment */}
        <Card3D
          glowOnHover={netSentiment >= 0 ? 'emerald' : 'red'}
          maxTilt={9}
          scaleOnHover={1.03}
          className="bg-gradient-to-br from-[#0B203B]/90 to-[#071527]/90 border border-[#1B365D] rounded-xl p-5 shadow-lg backdrop-blur-md c1-card-sheen"
        >
          <div className="flex items-center justify-between translate-z-20">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Net Sentiment Index
            </span>
            <div
              className={`p-2 rounded-xl border shadow-md ${
                netSentiment >= 0
                  ? 'bg-emerald-950/70 text-emerald-400 border-emerald-600/50'
                  : 'bg-[#4C1210] text-[#FCA5A5] border-[#D03027]'
              }`}
            >
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2 translate-z-30">
            <span
              className={`text-3xl font-black tracking-tight font-mono drop-shadow ${
                netSentiment >= 0 ? 'text-emerald-400' : 'text-[#FCA5A5]'
              }`}
            >
              {netSentiment >= 0 ? `+${netSentiment}%` : `${netSentiment}%`}
            </span>
            <span className="text-xs text-slate-400 font-mono">
              ({neg} neg / {pos} pos)
            </span>
          </div>
          <p className="mt-2 text-xs text-slate-400 translate-z-10">
            AI extracted sentiment balance
          </p>
        </Card3D>

        {/* Card 3: Emerging Anomalies */}
        <Card3D
          glowOnHover="red"
          maxTilt={10}
          scaleOnHover={1.03}
          onClick={() => onNavigateTab('clusters')}
          className="bg-gradient-to-br from-[#1A0B10]/95 to-[#0B1527]/95 border border-[#D03027]/70 rounded-xl p-5 shadow-lg backdrop-blur-md cursor-pointer group c1-card-sheen c1-red-accent-top"
        >
          <div className="flex items-center justify-between translate-z-20">
            <span className="text-xs font-bold uppercase tracking-wider text-[#FCA5A5] group-hover:text-white transition">
              Emerging Anomalies
            </span>
            <div className="p-2 rounded-xl bg-[#4C1210] text-[#FCA5A5] border border-[#D03027] shadow-[0_0_12px_rgba(208,48,39,0.5)]">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2 translate-z-30">
            <span className="text-3xl font-black tracking-tight text-[#FCA5A5] font-mono drop-shadow-[0_2px_8px_rgba(208,48,39,0.6)]">
              {overview?.anomalies_count || 0}
            </span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#4C1210] text-[#FCA5A5] border border-[#D03027] font-mono font-bold animate-pulse shadow-[0_0_8px_#D03027]">
              z ≥ 2.0 SPIKE
            </span>
          </div>
          <p className="mt-2 text-xs text-[#FCA5A5]/80 flex items-center group-hover:text-white translate-z-10">
            Investigate anomalous clusters <ArrowUpRight className="w-3.5 h-3.5 ml-1" />
          </p>
        </Card3D>

        {/* Card 4: Governance Checkpoint */}
        <Card3D
          glowOnHover="amber"
          maxTilt={9}
          scaleOnHover={1.03}
          onClick={() => onNavigateTab('recommendations')}
          className="bg-gradient-to-br from-[#191306]/95 to-[#0B1829]/95 border border-[#B45309]/70 rounded-xl p-5 shadow-lg backdrop-blur-md cursor-pointer group c1-card-sheen"
        >
          <div className="flex items-center justify-between translate-z-20">
            <span className="text-xs font-bold uppercase tracking-wider text-[#FDE68A] group-hover:text-white transition">
              Governance Checkpoint
            </span>
            <div className="p-2 rounded-xl bg-[#3D2506] text-[#FDE68A] border border-[#B45309] shadow-[0_0_12px_rgba(245,158,11,0.3)]">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline space-x-2 translate-z-30">
            <span className="text-3xl font-black tracking-tight text-[#FDE68A] font-mono drop-shadow">
              {overview?.pending_recommendations_count || 0}
            </span>
            <span className="text-xs text-slate-400">awaiting sign-off</span>
          </div>
          <p className="mt-2 text-xs text-[#FDE68A]/80 flex items-center group-hover:text-white translate-z-10">
            Open HITL approval queue <ArrowUpRight className="w-3.5 h-3.5 ml-1" />
          </p>
        </Card3D>
      </div>

      {/* Main Charts & Breakdown Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trend Velocity Chart */}
        <div className="lg:col-span-2 bg-[#08182D]/90 border border-[#1B365D] rounded-2xl p-6 shadow-xl backdrop-blur-md relative overflow-hidden">
          <div className="absolute inset-0 cyber-grid-dense opacity-25 pointer-events-none" />

          <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
            <div>
              <h3 className="text-base font-bold text-white flex items-center tracking-tight">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-400 mr-2.5 shadow-[0_0_8px_#38BDF8]"></span>
                Complaint Volume Velocity & 4-Week Rolling Baseline
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Statistically tracking complaint surges against historical 28-day baseline
              </p>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={onTriggerClustering}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-200 bg-[#071629] hover:bg-[#0D2442] border border-[#1B365D] rounded-lg transition shadow-sm hover:border-sky-500/50"
              >
                Run DBSCAN
              </button>
              <button
                onClick={onTriggerTrends}
                className="px-3.5 py-1.5 text-xs font-semibold text-[#38BDF8] bg-[#004879]/60 hover:bg-[#004879] border border-sky-400/50 rounded-lg transition shadow-[0_0_10px_rgba(56,189,248,0.2)]"
              >
                Recalculate Trends
              </button>
            </div>
          </div>

          <div className="h-64 w-full relative z-10">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="c1ColorCurrent" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#38BDF8" stopOpacity={0.45} />
                    <stop offset="95%" stopColor="#004879" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="c1ColorBaseline" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#94a3b8" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1B365D" opacity={0.5} />
                <XAxis dataKey="period" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#071527',
                    borderColor: '#0076BE',
                    borderRadius: '0.75rem',
                    fontSize: '12px',
                    color: '#f8fafc',
                    boxShadow: '0 12px 28px -4px rgba(0, 0, 0, 0.6)',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="current"
                  name="Current Weekly Volume"
                  stroke="#38BDF8"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#c1ColorCurrent)"
                />
                <Area
                  type="monotone"
                  dataKey="baseline"
                  name="4-Week Rolling Avg"
                  stroke="#94a3b8"
                  strokeDasharray="4 4"
                  strokeWidth={1.5}
                  fillOpacity={1}
                  fill="url(#c1ColorBaseline)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-4 flex items-center justify-center space-x-6 text-xs text-slate-300 relative z-10">
            <div className="flex items-center space-x-2">
              <span className="w-3 h-3 rounded-full bg-[#38BDF8] shadow-[0_0_6px_#38BDF8]" />
              <span>Current Weekly Complaints</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-4 h-0.5 border-t-2 border-dashed border-slate-400" />
              <span>4-Week Baseline Average</span>
            </div>
          </div>
        </div>

        {/* Sentiment Distribution & Top Capital One Products */}
        <div className="space-y-6">
          {/* Sentiment Composition */}
          <div className="bg-[#08182D]/90 border border-[#1B365D] rounded-2xl p-5 shadow-xl backdrop-blur-md">
            <h4 className="text-sm font-bold text-white mb-1 tracking-tight">
              Sentiment Distribution
            </h4>
            <p className="text-xs text-slate-400 mb-3">
              Analyzed across {total.toLocaleString()} customer reviews
            </p>

            {/* Segmented bar */}
            <div className="w-full h-3.5 bg-[#040C18] rounded-full overflow-hidden flex border border-[#1B365D] shadow-inner p-0.5">
              <div
                style={{ width: `${total > 0 ? (pos / total) * 100 : 33}%` }}
                className="bg-emerald-500 hover:bg-emerald-400 transition-all rounded-l-full"
                title={`Positive: ${pos}`}
              />
              <div
                style={{ width: `${total > 0 ? (neu / total) * 100 : 33}%` }}
                className="bg-[#F59E0B] hover:bg-[#FBBF24] transition-all"
                title={`Neutral: ${neu}`}
              />
              <div
                style={{ width: `${total > 0 ? (neg / total) * 100 : 34}%` }}
                className="bg-[#D03027] hover:bg-[#E13B32] transition-all rounded-r-full shadow-[0_0_8px_#D03027]"
                title={`Negative: ${neg}`}
              />
            </div>

            <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
              <div className="p-2.5 rounded-xl bg-emerald-950/40 border border-emerald-900/40">
                <span className="block text-emerald-400 font-black text-sm">{pos}</span>
                <span className="text-slate-400 text-[10px]">Positive</span>
              </div>
              <div className="p-2.5 rounded-xl bg-amber-950/40 border border-amber-900/40">
                <span className="block text-amber-400 font-black text-sm">{neu}</span>
                <span className="text-slate-400 text-[10px]">Neutral</span>
              </div>
              <div className="p-2.5 rounded-xl bg-[#4C1210]/60 border border-[#D03027]/40">
                <span className="block text-[#FCA5A5] font-black text-sm">{neg}</span>
                <span className="text-slate-400 text-[10px]">Negative</span>
              </div>
            </div>
          </div>

          {/* Top Affected Products Styled Like Capital One Cards */}
          <div className="bg-[#08182D]/90 border border-[#1B365D] rounded-2xl p-5 shadow-xl backdrop-blur-md">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-bold text-white flex items-center">
                <CreditCard className="w-4 h-4 mr-1.5 text-sky-400" />
                Capital One Products
              </h4>
              <button
                onClick={() => onNavigateTab('reviews')}
                className="text-xs text-[#38BDF8] hover:underline font-semibold"
              >
                View all 19 →
              </button>
            </div>

            <div className="space-y-2">
              {overview?.top_products && overview.top_products.length > 0 ? (
                overview.top_products.slice(0, 4).map((item) => {
                  const meta = getProductMeta(item.product_id);
                  return (
                    <div
                      key={item.product_id}
                      onClick={() => onNavigateTab('reviews')}
                      className={`p-3 rounded-xl border flex items-center justify-between transition-all duration-200 cursor-pointer hover:scale-[1.02] shadow-sm hover:shadow-md ${meta.cardStyle}`}
                    >
                      <div className="truncate pr-2">
                        <span className="block font-bold text-xs truncate">
                          {meta.name}
                        </span>
                        <span className="text-[10px] text-slate-300/80 block">
                          {meta.tier}
                        </span>
                      </div>
                      <span className="text-xs font-mono font-bold shrink-0 bg-[#040C18]/80 px-2.5 py-0.5 rounded-full border border-white/10 text-white shadow-inner">
                        {item.count} rev
                      </span>
                    </div>
                  );
                })
              ) : (
                <div className="text-xs text-slate-500 py-3 text-center">
                  Ingesting reviews to compile Capital One product breakdown...
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Velocity Anomalies Notification Bar */}
      {overview && overview.recent_anomalies.length > 0 && (
        <div className="bg-gradient-to-r from-[#380D0B] to-[#1F0807] border border-[#D03027] rounded-2xl p-5 shadow-[0_8px_30px_rgba(208,48,39,0.3)] c1-red-accent-top">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-3.5">
              <div className="p-2.5 rounded-xl bg-[#D03027] text-white shrink-0 shadow-[0_0_12px_#D03027]">
                <Zap className="w-5 h-5 animate-bounce" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white tracking-tight">
                  Statistical Complaint Surges Detected (z ≥ 2.0)
                </h4>
                <p className="text-xs text-[#FECDD3] mt-0.5">
                  {overview.recent_anomalies.length} issue clusters are experiencing significant week-over-week velocity spikes (e.g. Lounge entry crowding, Face ID crashes).
                </p>
              </div>
            </div>
            <button
              onClick={() => onNavigateTab('clusters')}
              className="px-4 py-2.5 text-xs font-bold text-white bg-[#D03027] hover:bg-[#B81D24] rounded-xl transition-all shadow-[0_4px_16px_rgba(208,48,39,0.5)] shrink-0 active:scale-95 border border-red-300/30"
            >
              Investigate Anomalies →
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import {
  Report,
} from '../../types';
import { api } from '../../services/api';
import { Badge } from '../common/Badge';
import { Modal } from '../common/Modal';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { EmptyState } from '../common/EmptyState';
import {
  FileText,
  Calendar,
  Download,
  PlusCircle,
  MapPin,
  TrendingUp,
  TrendingDown,
  Sparkles,
  Code,
  Layout,
} from 'lucide-react';

export const ReportsView: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // View mode: 'interactive' | 'markdown' | 'json'
  const [viewMode, setViewMode] = useState<'interactive' | 'markdown' | 'json'>('interactive');
  const [markdownContent, setMarkdownContent] = useState<string>('');

  // Generate modal
  const [isGenerateModalOpen, setIsGenerateModalOpen] = useState<boolean>(false);
  const [reportTitle, setReportTitle] = useState<string>('Weekly Executive Intelligence Brief');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  const loadReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getReports(1, 20);
      setReports(res.items);
      if (res.items.length > 0 && !selectedReport) {
        setSelectedReport(res.items[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load executive reports');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  const handleSelectReport = async (report: Report) => {
    setSelectedReport(report);
    if (viewMode === 'markdown') {
      try {
        const exported = await api.exportReport(report.id, 'markdown');
        setMarkdownContent(exported.content);
      } catch {
        // fallback
      }
    }
  };

  const handleGenerateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsGenerating(true);
    try {
      const newReport = await api.generateReport(reportTitle.trim() || undefined);
      setIsGenerateModalOpen(false);
      setReportTitle('Weekly Executive Intelligence Brief');
      await loadReports();
      setSelectedReport(newReport);
    } catch (err: any) {
      alert(`Report generation failed: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExportDownload = async (format: 'html' | 'markdown') => {
    if (!selectedReport) return;
    try {
      const exported = await api.exportReport(selectedReport.id, format);
      const mimeType = format === 'html' ? 'text/html' : 'text/markdown';
      const blob = new Blob([exported.content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${selectedReport.title.toLowerCase().replace(/\s+/g, '_')}_${selectedReport.id.slice(0, 8)}.${format === 'html' ? 'html' : 'md'}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* 3D Report Controls Header */}
      <div className="bg-gradient-to-r from-[#07192F]/90 via-[#0B203B]/90 to-[#06172B]/90 border border-sky-500/30 rounded-2xl p-6 shadow-xl backdrop-blur-md flex flex-col md:flex-row md:items-center justify-between gap-4 relative overflow-hidden">
        <div className="absolute inset-0 cyber-grid-dense opacity-20 pointer-events-none" />

        <div className="relative z-10 flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-sky-950/80 border border-sky-400/40 text-sky-400 shadow-md">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-extrabold text-white tracking-tight">
              Weekly Executive Intelligence Reports
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Automated executive intelligence synthesis combining macro metrics, geographic hotspots, and ranked emerging issues.
            </p>
          </div>
        </div>

        <div className="relative z-10 flex items-center space-x-3 shrink-0">
          {reports.length > 0 && (
            <select
              value={selectedReport?.id || ''}
              onChange={(e) => {
                const rep = reports.find((r) => r.id === e.target.value);
                if (rep) handleSelectReport(rep);
              }}
              className="bg-[#051121] border border-[#1B365D] rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sky-400 shadow-inner"
            >
              {reports.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.title} ({r.generated_at?.slice(0, 10)})
                </option>
              ))}
            </select>
          )}

          <button
            onClick={() => setIsGenerateModalOpen(true)}
            className="flex items-center space-x-1.5 px-4 py-2 bg-gradient-to-r from-sky-600 to-[#0076BE] hover:from-sky-500 hover:to-[#0099D8] text-white text-xs font-bold rounded-xl shadow-[0_4px_16px_rgba(56,189,248,0.3)] transition-all duration-200 active:scale-95 border border-sky-400/40"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>Generate New Report</span>
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner message="Loading executive intelligence reports..." />
      ) : error ? (
        <div className="p-8 text-center text-rose-400 text-sm">{error}</div>
      ) : !selectedReport ? (
        <EmptyState
          title="No intelligence reports generated yet"
          description="Click 'Generate New Report' to synthesize the latest weekly intelligence brief."
          actionLabel="Generate Report"
          onAction={() => setIsGenerateModalOpen(true)}
          icon={<FileText className="w-8 h-8 text-sky-400" />}
        />
      ) : (
        <div className="space-y-6">
          {/* Subheader & Export Toolbar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-c1-slate-border">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center">
                {selectedReport.title}
              </h2>
              <div className="flex items-center space-x-3 text-xs text-slate-400 mt-1">
                <span className="flex items-center">
                  <Calendar className="w-3.5 h-3.5 mr-1 text-sky-400" />
                  Period: {selectedReport.report_period_start?.slice(0, 10)} to{' '}
                  {selectedReport.report_period_end?.slice(0, 10)}
                </span>
                <span>•</span>
                <span>Generated: {selectedReport.generated_at?.slice(0, 19).replace('T', ' ')}</span>
              </div>
            </div>

            {/* View Mode Toggle & Export buttons */}
            <div className="flex items-center space-x-2">
              <div className="bg-c1-navy-darker border border-c1-slate-border rounded-lg p-0.5 flex">
                <button
                  onClick={() => setViewMode('interactive')}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                    viewMode === 'interactive'
                      ? 'bg-c1-navy text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Layout className="w-3.5 h-3.5 inline mr-1" />
                  Dashboard
                </button>
                <button
                  onClick={async () => {
                    setViewMode('markdown');
                    if (selectedReport) {
                      const exp = await api.exportReport(selectedReport.id, 'markdown');
                      setMarkdownContent(exp.content);
                    }
                  }}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                    viewMode === 'markdown'
                      ? 'bg-c1-navy text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5 inline mr-1" />
                  Markdown
                </button>
                <button
                  onClick={() => setViewMode('json')}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                    viewMode === 'json'
                      ? 'bg-c1-navy text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Code className="w-3.5 h-3.5 inline mr-1" />
                  JSON
                </button>
              </div>

              <button
                onClick={() => handleExportDownload('html')}
                className="flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-c1-navy-dark hover:bg-c1-navy text-slate-200 border border-c1-slate-border transition"
              >
                <Download className="w-3.5 h-3.5 text-sky-400" />
                <span>HTML</span>
              </button>
              <button
                onClick={() => handleExportDownload('markdown')}
                className="flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-c1-navy-dark hover:bg-c1-navy text-slate-200 border border-c1-slate-border transition"
              >
                <Download className="w-3.5 h-3.5 text-sky-400" />
                <span>MD</span>
              </button>
            </div>
          </div>

          {/* Interactive View Mode */}
          {viewMode === 'interactive' && (
            <div className="space-y-6">
              {/* Executive KPI summary cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-4 bg-c1-slate-card/90 border border-c1-slate-border rounded-xl c1-card-sheen">
                  <span className="text-xs text-slate-400 block uppercase tracking-wider font-semibold">
                    Total Volume
                  </span>
                  <span className="text-2xl font-bold text-white mt-1 block">
                    {selectedReport.total_reviews.toLocaleString()}
                  </span>
                  <span className="text-[11px] text-slate-400">reviews in window</span>
                </div>

                <div className="p-4 bg-c1-slate-card/90 border border-c1-slate-border rounded-xl c1-card-sheen">
                  <span className="text-xs text-slate-400 block uppercase tracking-wider font-semibold">
                    Negative Ratio
                  </span>
                  <span className="text-2xl font-bold text-rose-400 mt-1 block">
                    {selectedReport.negative_pct.toFixed(1)}%
                  </span>
                  <span className="text-[11px] text-slate-400">dissatisfaction rate</span>
                </div>

                <div className="p-4 bg-c1-slate-card/90 border border-c1-slate-border rounded-xl c1-card-sheen c1-red-accent-top">
                  <span className="text-xs text-slate-400 block uppercase tracking-wider font-semibold">
                    Emerging Issues
                  </span>
                  <span className="text-2xl font-bold text-c1-red mt-1 block flex items-center">
                    <TrendingUp className="w-5 h-5 mr-1" />
                    {selectedReport.emerging_issues_count}
                  </span>
                  <span className="text-[11px] text-slate-400">spiking anomalies</span>
                </div>

                <div className="p-4 bg-c1-slate-card/90 border border-c1-slate-border rounded-xl c1-card-sheen">
                  <span className="text-xs text-slate-400 block uppercase tracking-wider font-semibold">
                    Improving Issues
                  </span>
                  <span className="text-2xl font-bold text-emerald-400 mt-1 block flex items-center">
                    <TrendingDown className="w-5 h-5 mr-1" />
                    {selectedReport.improving_issues_count}
                  </span>
                  <span className="text-[11px] text-slate-400">resolving trends</span>
                </div>
              </div>

              {/* Executive Summary Narrative */}
              <div className="p-5 rounded-xl bg-c1-slate-card/90 border border-c1-slate-border c1-card-sheen">
                <div className="flex items-center space-x-2 mb-2 text-sky-400">
                  <Sparkles className="w-4 h-4 text-sky-400" />
                  <h4 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
                    Executive Narrative
                  </h4>
                </div>
                <p className="text-xs text-slate-200 leading-relaxed whitespace-pre-line">
                  {selectedReport.executive_summary}
                </p>
              </div>

              {/* Geographic Hotspots Intelligence */}
              {selectedReport.geographic_insights &&
                Object.keys(selectedReport.geographic_insights).length > 0 && (
                  <div className="p-5 rounded-xl bg-c1-slate-card/90 border border-c1-slate-border c1-card-sheen">
                    <div className="flex items-center space-x-2 mb-3 text-amber-400">
                      <MapPin className="w-4 h-4 text-c1-red" />
                      <h4 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
                        Geographic Intelligence Hotspots
                      </h4>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                      {Object.entries(selectedReport.geographic_insights).map(([loc, info]: any) => (
                        <div
                          key={loc}
                          className="p-3 rounded-lg bg-c1-navy-darker/90 border border-c1-slate-border text-xs"
                        >
                          <span className="font-bold text-slate-100 flex items-center mb-1">
                            <MapPin className="w-3.5 h-3.5 mr-1 text-c1-red" />
                            {loc}
                          </span>
                          <p className="text-slate-300 text-[11px]">
                            {typeof info === 'string' ? info : JSON.stringify(info)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              {/* Ranked Issues List */}
              {selectedReport.report_issues && selectedReport.report_issues.length > 0 && (
                <div className="bg-c1-slate-card/90 border border-c1-slate-border rounded-xl overflow-hidden shadow-sm c1-card-sheen">
                  <div className="px-6 py-4 border-b border-c1-slate-border">
                    <h4 className="text-sm font-semibold text-slate-100">
                      Ranked Highlighted Issues & Action Items
                    </h4>
                  </div>
                  <div className="divide-y divide-c1-slate-border">
                    {selectedReport.report_issues.map((item) => (
                      <div key={item.id} className="p-5 space-y-2 text-xs">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <span className="w-5 h-5 rounded-full bg-c1-navy text-white font-bold flex items-center justify-center text-[10px] border border-c1-navy-light/40">
                              #{item.rank}
                            </span>
                            <span className="font-semibold text-slate-100 text-sm">
                              {item.cluster?.cluster_title || `Issue Cluster ${item.cluster_id}`}
                            </span>
                            <Badge variant="trajectory" value={item.issue_type}>
                              {item.issue_type.toUpperCase()}
                            </Badge>
                          </div>
                          {item.cluster && (
                            <span className="text-slate-400">
                              {item.cluster.review_count} reviews affected
                            </span>
                          )}
                        </div>

                        {item.recommendation && (
                          <div className="p-3 bg-c1-navy-darker/80 rounded-lg border border-c1-slate-border text-xs space-y-1 mt-2">
                            <div className="text-slate-300 text-[11px]">
                              <strong className="text-emerald-400">Remediation Action:</strong>{' '}
                              {item.recommendation.recommended_action}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Formatted Markdown View */}
          {viewMode === 'markdown' && (
            <div className="p-5 rounded-xl bg-c1-navy-darker border border-c1-slate-border overflow-x-auto">
              <pre className="text-xs text-slate-200 font-mono whitespace-pre-wrap leading-relaxed">
                {markdownContent || 'Loading markdown brief...'}
              </pre>
            </div>
          )}

          {/* Raw JSON View */}
          {viewMode === 'json' && (
            <div className="p-5 rounded-xl bg-c1-navy-darker border border-c1-slate-border overflow-x-auto">
              <pre className="text-xs text-sky-300 font-mono whitespace-pre leading-relaxed">
                {JSON.stringify(selectedReport, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Generate Report Modal */}
      {isGenerateModalOpen && (
        <Modal
          isOpen={isGenerateModalOpen}
          onClose={() => setIsGenerateModalOpen(false)}
          title="Generate Weekly Intelligence Report"
          subtitle="Compiles multi-source review metrics, clusters, velocity anomalies, and geographic insights."
        >
          <form onSubmit={handleGenerateReport} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Report Title
              </label>
              <input
                type="text"
                value={reportTitle}
                onChange={(e) => setReportTitle(e.target.value)}
                required
                className="w-full bg-c1-navy-darker border border-c1-slate-border rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-c1-navy"
              />
            </div>

            <p className="text-xs text-slate-400">
              The report generator automatically inspects current reviews and cluster trajectories across the active window, compiles executive KPI metrics, extracts geographic anomalies, and publishes a <code className="text-sky-300">report.generated</code> Kafka event.
            </p>

            <div className="flex justify-end space-x-3 pt-3 border-t border-c1-slate-border">
              <button
                type="button"
                onClick={() => setIsGenerateModalOpen(false)}
                className="px-4 py-2 text-xs text-slate-300 hover:text-white bg-c1-navy-dark hover:bg-c1-navy rounded-lg border border-c1-slate-border transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isGenerating}
                className="px-4 py-2 text-xs font-semibold text-white bg-c1-navy hover:bg-c1-navy-light rounded-lg transition disabled:opacity-50 border border-c1-navy-light/40"
              >
                {isGenerating ? 'Compiling Brief...' : 'Generate Report'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};

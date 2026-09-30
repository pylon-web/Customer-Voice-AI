import React, { useState, useEffect } from 'react';
import {
  Recommendation,
  Approval,
} from '../../types';
import { api } from '../../services/api';
import { Badge } from '../common/Badge';
import { Modal } from '../common/Modal';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { EmptyState } from '../common/EmptyState';
import {
  BrainCircuit,
  CheckCircle2,
  XCircle,
  Edit3,
  History,
  ShieldCheck,
  FileCheck,
  Building2,
  Info,
  Filter,
} from 'lucide-react';
import { LangGraphVisualizer } from '../common/LangGraphVisualizer';

interface RecommendationsViewProps {
  initialClusterId?: string;
}

export const RecommendationsView: React.FC<RecommendationsViewProps> = ({
  initialClusterId,
}) => {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filter by status
  const [statusFilter, setStatusFilter] = useState<string>('');

  // Modals for HITL actions
  const [selectedRec, setSelectedRec] = useState<Recommendation | null>(null);
  const [actionType, setActionType] = useState<'approve' | 'modify' | 'reject' | null>(null);
  const [reviewerName, setReviewerName] = useState<string>('Lead Operations Analyst');
  const [reviewerNotes, setReviewerNotes] = useState<string>('');
  const [modifiedAction, setModifiedAction] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Audit history modal
  const [isAuditModalOpen, setIsAuditModalOpen] = useState<boolean>(false);
  const [auditLogs, setAuditLogs] = useState<Approval[]>([]);
  const [loadingAudit, setLoadingAudit] = useState<boolean>(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getRecommendations(1, 50, statusFilter || undefined);
      setRecommendations(res.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load recommendations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const init = async () => {
      if (initialClusterId) {
        try {
          await api.runInvestigation(initialClusterId);
        } catch {
          // ignore if already investigated
        }
      }
      loadData();
    };
    init();
  }, [statusFilter, initialClusterId]);

  const handleOpenActionModal = (
    rec: Recommendation,
    type: 'approve' | 'modify' | 'reject'
  ) => {
    setSelectedRec(rec);
    setActionType(type);
    setReviewerNotes('');
    setModifiedAction(rec.recommended_action);
  };

  const handleDecisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRec || !actionType) return;
    setIsSubmitting(true);
    try {
      if (actionType === 'approve') {
        await api.approveRecommendation(selectedRec.id, reviewerName, reviewerNotes);
      } else if (actionType === 'reject') {
        await api.rejectRecommendation(selectedRec.id, reviewerName, reviewerNotes);
      } else if (actionType === 'modify') {
        await api.modifyRecommendation(
          selectedRec.id,
          reviewerName,
          modifiedAction,
          reviewerNotes
        );
      }
      setSelectedRec(null);
      setActionType(null);
      loadData();
    } catch (err: any) {
      alert(`Decision submission failed: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenAudit = async () => {
    setIsAuditModalOpen(true);
    setLoadingAudit(true);
    try {
      const logs = await api.getAuditHistory();
      setAuditLogs(logs);
    } catch (err: any) {
      alert(`Failed to fetch audit log: ${err.message}`);
    } finally {
      setLoadingAudit(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 3D Autonomous LangGraph Visualizer Pipeline */}
      <LangGraphVisualizer />

      {/* Filter and Governance Audit Toolbar */}
      <div className="bg-[#071629]/90 border border-sky-500/20 rounded-2xl p-4 shadow-lg backdrop-blur-md flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-2 overflow-x-auto py-1 scrollbar-none">
          <div className="flex items-center space-x-1.5 text-xs text-slate-400 font-semibold mr-1">
            <Filter className="w-3.5 h-3.5 text-sky-400" />
            <span>Filter Status:</span>
          </div>
          {['', 'pending_approval', 'approved', 'modified', 'rejected'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all duration-200 whitespace-nowrap active:scale-95 ${
                statusFilter === st
                  ? st === 'pending_approval'
                    ? 'bg-[#D03027] text-white shadow-[0_2px_12px_rgba(208,48,39,0.5)] border border-red-300/40'
                    : 'bg-gradient-to-r from-sky-600 to-[#0076BE] text-white shadow-[0_2px_12px_rgba(56,189,248,0.3)] border border-sky-400/40'
                  : 'bg-[#051121] text-slate-400 hover:text-slate-200 hover:bg-[#0E2442] border border-[#1B365D]'
              }`}
            >
              {st ? st.replace('_', ' ').toUpperCase() : 'ALL RECOMMENDATIONS'}
            </button>
          ))}
        </div>

        <button
          onClick={handleOpenAudit}
          className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-[#051121] hover:bg-[#0E2747] text-slate-200 text-xs font-semibold rounded-xl border border-[#1B365D] hover:border-sky-500/40 transition-all shadow-sm shrink-0 active:scale-95"
        >
          <History className="w-3.5 h-3.5 text-sky-400" />
          <span>Audit History</span>
        </button>
      </div>

      {/* Recommendations List */}
      {loading ? (
        <LoadingSpinner message="Loading recommendations queue..." />
      ) : error ? (
        <div className="p-8 text-center text-rose-400 text-sm">{error}</div>
      ) : recommendations.length === 0 ? (
        <EmptyState
          title="No recommendations match criteria"
          description="Investigate clusters using LangGraph to generate evidence-backed hypotheses and action plans."
          icon={<BrainCircuit className="w-8 h-8 text-sky-400" />}
        />
      ) : (
        <div className="space-y-6">
          {recommendations.map((rec) => (
            <div
              key={rec.id}
              className={`bg-gradient-to-br from-[#0B203B]/95 to-[#061527]/95 border rounded-2xl p-6 shadow-xl space-y-5 transition-all duration-200 c1-card-sheen backdrop-blur-md relative ${
                rec.status === 'pending_approval'
                  ? 'border-amber-500/60 shadow-[0_8px_30px_rgba(245,158,11,0.15)] hover:shadow-[0_12px_36px_rgba(245,158,11,0.22)] hover:border-amber-400 c1-red-accent-top ring-1 ring-amber-500/30'
                  : 'border-[#1B365D] hover:border-sky-500/50 hover:shadow-[0_8px_30px_rgba(56,189,248,0.15)]'
              }`}
            >
              {/* Header Info */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1B365D]/80 pb-4">
                <div className="flex items-center space-x-3 flex-wrap gap-y-1.5">
                  <h4 className="text-base font-extrabold text-white tracking-tight">
                    {rec.cluster_title || `Issue Recommendation #${rec.id.slice(0, 8)}`}
                  </h4>
                  <Badge variant="status" value={rec.status}>
                    {rec.status.replace('_', ' ').toUpperCase()}
                  </Badge>
                  <span className="text-xs px-3 py-1 rounded-full bg-[#051121] text-sky-200 border border-sky-600/40 flex items-center font-medium shadow-inner">
                    <Building2 className="w-3.5 h-3.5 mr-1.5 text-sky-400" />
                    Team: {rec.suggested_team?.name || rec.suggested_team_id}
                  </span>
                </div>

                <div className="flex items-center space-x-2 text-xs text-slate-300 font-mono bg-[#051121] px-3 py-1 rounded-full border border-white/10">
                  <span>Confidence:</span>
                  <span className="font-bold text-emerald-400">
                    {Math.round(rec.confidence * 100)}%
                  </span>
                </div>
              </div>

              {/* 3 Core Structured Panels: Evidence vs Hypothesis vs Action */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* 1. Observed Customer Evidence */}
                <div className="p-4 rounded-xl bg-gradient-to-br from-[#06172D] to-[#041021] border border-sky-500/30 flex flex-col justify-between shadow-inner">
                  <div>
                    <div className="flex items-center space-x-1.5 text-sky-400 mb-2 font-mono">
                      <FileCheck className="w-4 h-4" />
                      <span className="text-xs font-bold uppercase tracking-wider">
                        Observed Customer Evidence
                      </span>
                    </div>
                    <p className="text-xs text-sky-100 leading-relaxed italic">
                      "{rec.observed_evidence}"
                    </p>
                  </div>
                  <div className="mt-3 pt-2.5 border-t border-sky-900/40 text-[10px] text-sky-300/70 font-mono">
                    ✓ Ground truth direct customer words
                  </div>
                </div>

                {/* 2. Investigation Hypothesis (Responsible AI Guardrail) */}
                <div className="p-4 rounded-xl bg-gradient-to-br from-[#180E2B] to-[#0D0818] border border-purple-500/30 flex flex-col justify-between shadow-inner">
                  <div>
                    <div className="flex items-center space-x-1.5 text-purple-400 mb-2 font-mono">
                      <Info className="w-4 h-4" />
                      <span className="text-xs font-bold uppercase tracking-wider">
                        Investigation Hypothesis
                      </span>
                    </div>
                    <p className="text-xs text-purple-200 leading-relaxed">
                      {rec.investigation_hypothesis}
                    </p>
                  </div>
                  <div className="mt-3 pt-2.5 border-t border-purple-900/40 text-[10px] text-purple-300/70 font-mono">
                    ⚠️ Tentative hypothesis; not verified fact
                  </div>
                </div>

                {/* 3. Recommended Remediation Action */}
                <div className="p-4 rounded-xl bg-gradient-to-br from-[#072417] to-[#03130C] border border-emerald-500/30 flex flex-col justify-between shadow-inner">
                  <div>
                    <div className="flex items-center space-x-1.5 text-emerald-400 mb-2 font-mono">
                      <ShieldCheck className="w-4 h-4" />
                      <span className="text-xs font-bold uppercase tracking-wider">
                        Recommended Action Plan
                      </span>
                    </div>
                    <p className="text-xs text-emerald-100 leading-relaxed font-medium">
                      {rec.recommended_action}
                    </p>
                  </div>
                  <div className="mt-3 pt-2.5 border-t border-emerald-900/40 text-[10px] text-emerald-300/70 font-mono">
                    ⚡ Remediation protocol for assigned team
                  </div>
                </div>
              </div>

              {/* Past Approvals / Governance Audit trail */}
              {rec.approvals && rec.approvals.length > 0 && (
                <div className="p-3 bg-[#051121] rounded-xl border border-[#1B365D] text-xs text-slate-300 space-y-1 shadow-inner">
                  <span className="font-bold text-slate-400 block text-[11px] font-mono uppercase tracking-wider">
                    Governance Decision Audit Log:
                  </span>
                  {rec.approvals.map((app) => (
                    <div key={app.id} className="flex items-center justify-between text-slate-300">
                      <span>
                        <strong className="text-white">{app.reviewer_name}</strong> marked as{' '}
                        <Badge variant="status" value={app.decision}>
                          {app.decision}
                        </Badge>
                        {app.reviewer_notes && ` — "${app.reviewer_notes}"`}
                      </span>
                      <span className="text-slate-500 font-mono text-[10px]">
                        {app.decided_at?.slice(0, 19).replace('T', ' ')}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Action Buttons for HITL Decision - Stationary, high-contrast, responsive click targets */}
              {rec.status === 'pending_approval' && (
                <div className="flex items-center justify-end space-x-3 pt-4 border-t border-[#1B365D]/80">
                  <button
                    type="button"
                    onClick={() => handleOpenActionModal(rec, 'reject')}
                    className="flex items-center space-x-1.5 px-4 py-2.5 rounded-xl text-xs font-bold text-red-200 bg-[#4C1210]/70 hover:bg-[#5C1614] border border-[#D03027] hover:border-red-400 transition-all duration-150 active:scale-95 shadow-md cursor-pointer"
                  >
                    <XCircle className="w-4 h-4 text-[#D03027]" />
                    <span>Reject</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleOpenActionModal(rec, 'modify')}
                    className="flex items-center space-x-1.5 px-4 py-2.5 rounded-xl text-xs font-bold text-sky-200 bg-[#071629] hover:bg-[#0E2747] border border-sky-500/50 hover:border-sky-400 transition-all duration-150 active:scale-95 shadow-md cursor-pointer"
                  >
                    <Edit3 className="w-4 h-4 text-sky-400" />
                    <span>Modify & Approve</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleOpenActionModal(rec, 'approve')}
                    className="flex items-center space-x-2 px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 border border-emerald-400/60 hover:border-emerald-300 transition-all duration-150 shadow-[0_4px_16px_rgba(16,185,129,0.35)] hover:shadow-[0_4px_22px_rgba(16,185,129,0.5)] active:scale-95 cursor-pointer"
                  >
                    <CheckCircle2 className="w-4 h-4 text-emerald-200" />
                    <span>Approve Recommendation</span>
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Decision Modal (Approve / Modify / Reject) */}
      {selectedRec && actionType && (
        <Modal
          isOpen={!!selectedRec && !!actionType}
          onClose={() => {
            setSelectedRec(null);
            setActionType(null);
          }}
          title={
            actionType === 'approve'
              ? 'Approve AI Recommendation'
              : actionType === 'modify'
              ? 'Modify Action Plan & Approve'
              : 'Reject AI Recommendation'
          }
          subtitle={`Cluster: ${selectedRec.cluster_title || selectedRec.cluster_id}`}
        >
          <form onSubmit={handleDecisionSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Reviewer Name *
              </label>
              <input
                type="text"
                value={reviewerName}
                onChange={(e) => setReviewerName(e.target.value)}
                required
                className="w-full bg-c1-navy-darker border border-c1-slate-border rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-c1-navy"
              />
            </div>

            {actionType === 'modify' && (
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Adjusted Action Plan *
                </label>
                <textarea
                  value={modifiedAction}
                  onChange={(e) => setModifiedAction(e.target.value)}
                  required
                  rows={3}
                  className="w-full bg-c1-navy-darker border border-c1-slate-border rounded-lg p-2 text-xs text-slate-200 leading-relaxed focus:outline-none focus:border-c1-navy"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Reviewer Governance Notes ({actionType === 'reject' ? 'Required' : 'Optional'})
              </label>
              <textarea
                value={reviewerNotes}
                onChange={(e) => setReviewerNotes(e.target.value)}
                required={actionType === 'reject'}
                placeholder={
                  actionType === 'reject'
                    ? 'Explain reason for rejection (e.g. False positive, issue already resolved in v5.2)...'
                    : 'Add contextual notes for audit trail...'
                }
                rows={2}
                className="w-full bg-c1-navy-darker border border-c1-slate-border rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:border-c1-navy"
              />
            </div>

            <div className="flex justify-end space-x-3 pt-3 border-t border-c1-slate-border">
              <button
                type="button"
                onClick={() => {
                  setSelectedRec(null);
                  setActionType(null);
                }}
                className="px-4 py-2 text-xs text-slate-300 hover:text-white bg-c1-navy-dark hover:bg-c1-navy rounded-lg border border-c1-slate-border transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className={`px-4 py-2 text-xs font-semibold text-white rounded-lg transition disabled:opacity-50 ${
                  actionType === 'approve'
                    ? 'bg-c1-navy hover:bg-c1-navy-light'
                    : actionType === 'modify'
                    ? 'bg-c1-navy hover:bg-c1-navy-light'
                    : 'bg-c1-red hover:bg-c1-red-hover'
                }`}
              >
                {isSubmitting
                  ? 'Submitting...'
                  : actionType === 'approve'
                  ? 'Confirm Approval'
                  : actionType === 'modify'
                  ? 'Save & Approve'
                  : 'Confirm Rejection'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Audit History Modal */}
      {isAuditModalOpen && (
        <Modal
          isOpen={isAuditModalOpen}
          onClose={() => setIsAuditModalOpen(false)}
          title="Human-in-the-Loop Governance Audit Log"
          subtitle="Chronological record of reviewer approvals, modifications, and rejections."
          maxWidth="max-w-3xl"
        >
          {loadingAudit ? (
            <LoadingSpinner message="Retrieving compliance audit records..." />
          ) : auditLogs.length === 0 ? (
            <p className="text-xs text-slate-400 py-6 text-center">
              No audit records recorded yet.
            </p>
          ) : (
            <div className="divide-y divide-c1-slate-border max-h-96 overflow-y-auto pr-1">
              {auditLogs.map((log) => (
                <div key={log.id} className="py-3 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-slate-200">{log.reviewer_name}</span>
                      <Badge variant="status" value={log.decision}>
                        {log.decision}
                      </Badge>
                    </div>
                    <span className="text-slate-400 font-mono text-[10px]">
                      {log.decided_at?.slice(0, 19).replace('T', ' ')}
                    </span>
                  </div>
                  {log.reviewer_notes && (
                    <p className="text-slate-300 italic pl-2 border-l-2 border-c1-navy">
                      "{log.reviewer_notes}"
                    </p>
                  )}
                  {log.modified_action && (
                    <div className="text-[11px] text-sky-200 bg-c1-navy-dark/70 p-2 rounded border border-c1-slate-border">
                      Modified Action: {log.modified_action}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Modal>
      )}
    </div>
  );
};

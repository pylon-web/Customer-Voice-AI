import React, { useState } from 'react';
import {
  Database,
  Brain,
  Sparkles,
  ShieldCheck,
  UserCheck,
  Info,
} from 'lucide-react';
import { Card3D } from './Card3D';

interface StepDetail {
  id: string;
  stepNum: number;
  name: string;
  nodeKey: string;
  icon: React.ElementType;
  engine: string;
  color: string;
  borderColor: string;
  glowColor: 'cyan' | 'red' | 'amber' | 'emerald';
  purpose: string;
  inputs: string;
  outputs: string;
  guardrail: string;
}

const STEPS: StepDetail[] = [
  {
    id: 'gather',
    stepNum: 1,
    name: 'Gather Evidence',
    nodeKey: 'gather_evidence_node',
    icon: Database,
    engine: 'ChromaDB / SQLite (1536-D)',
    color: 'from-sky-500/20 to-blue-600/10 text-sky-400',
    borderColor: 'border-sky-500/40 hover:border-sky-400',
    glowColor: 'cyan',
    purpose: 'Aggregates verbatim customer complaint text, star ratings, and platforms for the target cluster.',
    inputs: 'cluster_id, affected_product_id',
    outputs: 'observed_evidence (verbatim snippets, n_reviews)',
    guardrail: 'Ground truth boundary: Only direct customer words permitted.',
  },
  {
    id: 'hypotheses',
    stepNum: 2,
    name: 'Generate Hypotheses',
    nodeKey: 'generate_hypotheses_node',
    icon: Brain,
    engine: 'OpenAI GPT-4o-mini',
    color: 'from-purple-500/20 to-violet-600/10 text-purple-400',
    borderColor: 'border-purple-500/40 hover:border-purple-400',
    glowColor: 'cyan',
    purpose: 'Dynamically deduces plausible engineering, UX, and operational root causes behind complaint spikes.',
    inputs: 'observed_evidence, product_metadata',
    outputs: 'investigation_hypothesis (tentative causal reasoning)',
    guardrail: 'Epistemic certainty check: Must qualify as hypothesis, never proven fact.',
  },
  {
    id: 'action_plan',
    stepNum: 3,
    name: 'Synthesize Action Plan',
    nodeKey: 'synthesize_action_plan_node',
    icon: Sparkles,
    engine: 'OpenAI GPT-4o-mini',
    color: 'from-amber-500/20 to-orange-600/10 text-amber-400',
    borderColor: 'border-amber-500/40 hover:border-amber-400',
    glowColor: 'amber',
    purpose: 'Formulates concrete 3-step technical and operational remediation playbooks with target team assignment.',
    inputs: 'investigation_hypothesis, 7 Capital One Teams',
    outputs: 'recommended_action, suggested_team_id, confidence',
    guardrail: 'Actionability standard: Must specify immediate containment & permanent fix.',
  },
  {
    id: 'compliance',
    stepNum: 4,
    name: 'Compliance Reflector',
    nodeKey: 'compliance_reflector_node',
    icon: ShieldCheck,
    engine: 'Autonomous Critique LLM',
    color: 'from-indigo-500/20 to-cyan-600/10 text-indigo-300',
    borderColor: 'border-indigo-500/40 hover:border-indigo-400',
    glowColor: 'cyan',
    purpose: 'Critiques generated text for certainty violations, ensuring strict compliance with Responsible AI governance.',
    inputs: 'draft hypothesis & action plan',
    outputs: 'validated_hypothesis, compliance_score (0.0 - 1.0)',
    guardrail: 'Responsible AI Rule: Flags words like "definitely", "caused by", "guaranteed".',
  },
  {
    id: 'hitl',
    stepNum: 5,
    name: 'HITL Checkpoint',
    nodeKey: 'hitl_checkpoint_node',
    icon: UserCheck,
    engine: 'Human Lead Analyst Sign-Off',
    color: 'from-rose-500/20 to-red-600/10 text-rose-400',
    borderColor: 'border-rose-500/40 hover:border-[#D03027]',
    glowColor: 'red',
    purpose: 'Mandatory Human-in-the-Loop gate requiring an authorized analyst to review, approve, modify, or reject.',
    inputs: 'validated recommendation package',
    outputs: 'approved | modified | rejected status, audit record',
    guardrail: 'No action dispatched to Jira/Slack without verified human signature.',
  },
];

export const LangGraphVisualizer: React.FC = () => {
  const [selectedStep, setSelectedStep] = useState<StepDetail>(STEPS[1]);

  return (
    <div className="bg-gradient-to-b from-[#091D36] via-[#071629] to-[#040C18] border border-[#1B365D] rounded-2xl p-6 shadow-2xl relative overflow-hidden">
      {/* Background glow and subtle cyber grid */}
      <div className="absolute inset-0 cyber-grid-dense opacity-40 pointer-events-none" />
      <div className="absolute -top-24 -left-24 w-80 h-80 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -right-24 w-80 h-80 bg-[#D03027]/10 rounded-full blur-3xl pointer-events-none" />

      {/* Title & telemetry bar */}
      <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-[#1B365D]/80 pb-4 mb-6">
        <div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_10px_#10B981]" />
            <h3 className="text-base font-extrabold text-white tracking-tight flex items-center">
              Autonomous LangGraph State Machine
              <span className="ml-2.5 text-[11px] px-2 py-0.5 rounded-full bg-sky-950/80 text-sky-300 border border-sky-600/50 font-mono font-semibold">
                GPT-4o-mini + Reflexion Loop
              </span>
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic multi-agent pipeline enforcing strict Responsible AI epistemic boundaries between Evidence and Hypotheses.
          </p>
        </div>

        <div className="flex items-center space-x-2 shrink-0 text-xs">
          <div className="px-2.5 py-1 rounded-lg bg-[#071527] border border-[#1B365D] text-slate-300 flex items-center space-x-1.5 font-mono text-[11px]">
            <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping" />
            <span>State: <strong className="text-emerald-400">ACTIVE</strong></span>
          </div>
          <div className="px-2.5 py-1 rounded-lg bg-[#071527] border border-[#1B365D] text-slate-300 flex items-center space-x-1.5 font-mono text-[11px]">
            <span>Latency: <strong className="text-sky-300">~1.2s / node</strong></span>
          </div>
        </div>
      </div>

      {/* 5-Node Interactive 3D Pipeline */}
      <div className="relative z-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5 mb-6">
        {STEPS.map((step) => {
          const Icon = step.icon;
          const isSelected = selectedStep.id === step.id;

          return (
            <Card3D
              key={step.id}
              maxTilt={12}
              scaleOnHover={1.03}
              glowOnHover={step.glowColor}
              className={`p-4 rounded-xl border cursor-pointer transition-all duration-300 backdrop-blur-md relative ${
                isSelected
                  ? 'bg-[#0E2849] border-sky-400 shadow-[0_0_25px_rgba(56,189,248,0.3)] ring-1 ring-sky-400/50'
                  : `bg-[#071629]/90 ${step.borderColor}`
              }`}
              onClick={() => setSelectedStep(step)}
            >
              {/* Step Number Badge */}
              <div className="flex items-center justify-between mb-3">
                <span className="w-6 h-6 rounded-full bg-[#040C18] border border-white/10 text-white font-mono text-xs font-black flex items-center justify-center shadow-inner">
                  {step.stepNum}
                </span>

                <span className="text-[10px] uppercase tracking-wider font-mono px-1.5 py-0.5 rounded bg-white/5 text-slate-400">
                  Node {step.stepNum}
                </span>
              </div>

              {/* Icon & Name */}
              <div className="space-y-2 translate-z-20">
                <div
                  className={`w-10 h-10 rounded-lg bg-gradient-to-br ${step.color} border border-white/10 flex items-center justify-center shadow-lg`}
                >
                  <Icon className="w-5 h-5" />
                </div>

                <h4 className="font-bold text-xs text-white tracking-tight">
                  {step.name}
                </h4>

                <p className="text-[11px] text-slate-400 font-mono truncate">
                  {step.engine}
                </p>
              </div>

              {/* Active Selection Glow Dot */}
              {isSelected && (
                <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-8 h-1 bg-sky-400 rounded-full shadow-[0_0_10px_#38BDF8]" />
              )}
            </Card3D>
          );
        })}
      </div>

      {/* Selected Node Telemetry & Specification Console */}
      <div className="relative z-10 bg-[#040C18]/90 border border-sky-500/30 rounded-xl p-4 shadow-inner">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="space-y-2 flex-1">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-mono font-bold text-sky-400 uppercase tracking-wider">
                Active Node Inspection:
              </span>
              <span className="text-xs font-mono font-semibold text-white bg-sky-950/80 px-2 py-0.5 rounded border border-sky-800">
                {selectedStep.nodeKey}
              </span>
              <span className="text-[11px] text-slate-400 font-mono">
                ({selectedStep.engine})
              </span>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              {selectedStep.purpose}
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-xs font-mono">
              <div className="p-2.5 rounded-lg bg-[#071527] border border-[#1B365D]">
                <span className="text-slate-500 block text-[10px] uppercase font-bold">State Inputs:</span>
                <span className="text-sky-300 text-[11px]">{selectedStep.inputs}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-[#071527] border border-[#1B365D]">
                <span className="text-slate-500 block text-[10px] uppercase font-bold">State Mutated:</span>
                <span className="text-emerald-300 text-[11px]">{selectedStep.outputs}</span>
              </div>
            </div>
          </div>

          <div className="md:w-72 shrink-0 p-3 rounded-lg bg-[#140E05] border border-amber-600/40 text-xs">
            <div className="flex items-center space-x-1.5 text-amber-400 font-semibold mb-1">
              <Info className="w-3.5 h-3.5" />
              <span>Governance Guardrail</span>
            </div>
            <p className="text-[11px] text-amber-200/90 leading-relaxed">
              {selectedStep.guardrail}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

import React from 'react';
import { HealthData } from '../../types';
import { RefreshCw, Cpu, ShieldCheck } from 'lucide-react';

interface HeaderProps {
  health: HealthData | null;
  loading: boolean;
  onRefresh: () => void;
}

export const Header: React.FC<HeaderProps> = ({ health, loading, onRefresh }) => {
  const isHealthy = health?.status === 'healthy';

  return (
    <header className="sticky top-0 z-40 w-full border-b border-[#1B365D]/80 bg-[#061224]/90 backdrop-blur-xl shadow-2xl">
      {/* Capital One Signature Top Red Accent Line with 3D Neon Glow */}
      <div className="h-1 w-full bg-gradient-to-r from-[#D03027] via-[#FF4D42] to-[#B81D24] shadow-[0_0_12px_rgba(208,48,39,0.7)]" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Capital One Brand & 3D Swoosh Logo */}
        <div className="flex items-center space-x-3.5">
          <div className="relative flex items-center group cursor-pointer">
            <div className="flex items-center space-x-3">
              <div className="relative flex items-center justify-center">
                {/* 3D Beveled Metallic C1 Emblem */}
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#005B99] via-[#004879] to-[#041E38] border border-sky-400/50 flex items-center justify-center shadow-[0_4px_16px_rgba(0,118,190,0.45),inset_0_1px_1px_rgba(255,255,255,0.4)] transform group-hover:scale-105 group-hover:rotate-1 transition-transform duration-300">
                  <span className="text-white font-black text-sm tracking-tighter drop-shadow-[0_2px_4px_rgba(0,0,0,0.6)]">
                    C1
                  </span>
                </div>
                {/* Signature Red Swoosh Accent badge with neon glow */}
                <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-[#D03027] border-2 border-[#061224] shadow-[0_0_8px_#D03027] animate-pulse"></span>
              </div>

              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-lg font-black tracking-tight text-white uppercase font-sans drop-shadow-sm">
                    Capital<span className="text-[#38BDF8] drop-shadow-[0_0_10px_rgba(56,189,248,0.5)]">One</span>
                  </span>
                  <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-gradient-to-r from-[#004879] to-[#0076BE] text-white border border-sky-400/60 font-black tracking-wider shadow-[0_0_12px_rgba(56,189,248,0.4)]">
                    VOICE<span className="text-[#38BDF8]">IQ</span>
                  </span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800/90 text-slate-300 font-mono hidden sm:inline border border-slate-700">
                    3D Console
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 hidden sm:block">
                  VoiceIQ Enterprise Intelligence • Real-Time Product Anomaly Radar
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Status indicators and action */}
        <div className="flex items-center space-x-3">
          {/* AI Telemetry Badges */}
          <div className="hidden lg:flex items-center space-x-2 px-3 py-1 rounded-full bg-[#07192F]/90 border border-[#1B365D] text-[11px] text-slate-300 font-mono">
            <Cpu className="w-3.5 h-3.5 text-sky-400" />
            <span>GPT-4o:</span>
            <span className="text-emerald-400 font-semibold">ONLINE</span>
            <span className="text-slate-600">|</span>
            <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
            <span>HITL:</span>
            <span className="text-purple-300 font-semibold">ENFORCED</span>
          </div>

          <div className="flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-[#0A1D36] border border-sky-500/30 text-xs shadow-[0_0_15px_rgba(0,118,190,0.2)]">
            <span
              className={`w-2 h-2 rounded-full ${
                isHealthy
                  ? 'bg-emerald-400 animate-pulse shadow-[0_0_8px_#10B981]'
                  : 'bg-[#D03027] shadow-[0_0_8px_#D03027]'
              }`}
            />
            <span className="text-slate-100 font-bold tracking-wide">
              {health ? health.status.toUpperCase() : 'CONNECTING'}
            </span>
            <span className="text-slate-500 hidden md:inline">•</span>
            <span className="text-sky-300 hidden md:inline font-mono text-[11px]">
              {health?.environment || 'dev'}
            </span>
          </div>

          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-2.5 rounded-xl bg-gradient-to-b from-[#0F2847] to-[#081B33] hover:from-[#15365E] hover:to-[#0C2442] text-slate-200 hover:text-white transition-all duration-200 disabled:opacity-50 border border-sky-500/40 shadow-md hover:shadow-[0_0_15px_rgba(56,189,248,0.3)] active:scale-95"
            title="Refresh dashboard intelligence"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-sky-400' : 'text-slate-300'}`} />
          </button>
        </div>
      </div>
    </header>
  );
};


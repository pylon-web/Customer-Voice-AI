import React from 'react';
import {
  LayoutDashboard,
  MessageSquare,
  Network,
  BrainCircuit,
  FileText,
  GitBranch,
} from 'lucide-react';

export type TabKey =
  | 'overview'
  | 'reviews'
  | 'clusters'
  | 'recommendations'
  | 'reports'
  | 'routing';

interface NavbarProps {
  activeTab: TabKey;
  onTabChange: (tab: TabKey) => void;
  pendingRecsCount?: number;
  anomaliesCount?: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onTabChange,
  pendingRecsCount = 0,
  anomaliesCount = 0,
}) => {
  const tabs = [
    {
      key: 'overview' as TabKey,
      label: 'Executive Overview',
      icon: LayoutDashboard,
      badge: null,
    },
    {
      key: 'reviews' as TabKey,
      label: 'Review Explorer',
      icon: MessageSquare,
      badge: null,
    },
    {
      key: 'clusters' as TabKey,
      label: 'Clusters & Anomalies',
      icon: Network,
      badge: anomaliesCount > 0 ? `${anomaliesCount} alerts` : null,
      badgeColor: 'bg-[#4C1210] text-[#FCA5A5] border-[#D03027] shadow-[0_0_10px_rgba(208,48,39,0.5)]',
    },
    {
      key: 'recommendations' as TabKey,
      label: 'LangGraph & HITL Governance',
      icon: BrainCircuit,
      badge: pendingRecsCount > 0 ? `${pendingRecsCount} pending` : null,
      badgeColor: 'bg-[#3D2506] text-[#FDE68A] border-[#D97706] shadow-[0_0_10px_rgba(245,158,11,0.4)]',
    },
    {
      key: 'reports' as TabKey,
      label: 'Executive Reports',
      icon: FileText,
      badge: null,
    },
    {
      key: 'routing' as TabKey,
      label: 'Team Routing Matrix',
      icon: GitBranch,
      badge: null,
    },
  ];

  return (
    <nav className="w-full bg-[#051121]/95 border-b border-[#1B365D]/80 px-4 sm:px-6 lg:px-8 shadow-inner backdrop-blur-md relative z-30">
      <div className="max-w-7xl mx-auto flex space-x-1.5 sm:space-x-2 overflow-x-auto py-3 scrollbar-none">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => onTabChange(tab.key)}
              className={`relative flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold transition-all duration-200 whitespace-nowrap ${
                isActive
                  ? 'bg-gradient-to-r from-[#004879]/80 via-[#0A3059]/90 to-[#004879]/80 text-white border border-sky-400/60 shadow-[0_4px_20px_rgba(56,189,248,0.25)] -translate-y-0.5'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-[#0A1E38]/70 border border-transparent hover:-translate-y-0.5'
              }`}
            >
              <Icon
                className={`w-4 h-4 transition-transform duration-200 ${
                  isActive ? 'text-[#38BDF8] scale-110 drop-shadow-[0_0_6px_#38BDF8]' : 'text-slate-400'
                }`}
              />
              <span className="tracking-wide">{tab.label}</span>
              {tab.badge && (
                <span
                  className={`text-[10px] font-black px-2 py-0.5 rounded-full border ${tab.badgeColor} animate-pulse`}
                >
                  {tab.badge}
                </span>
              )}
              {/* Active Tab Glowing Red Accent Underline */}
              {isActive && (
                <span className="absolute -bottom-3 left-3 right-3 h-0.5 bg-gradient-to-r from-transparent via-[#D03027] to-transparent rounded-full shadow-[0_0_8px_#D03027]"></span>
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
};


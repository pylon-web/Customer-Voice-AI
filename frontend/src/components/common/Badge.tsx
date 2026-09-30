import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'sentiment' | 'severity' | 'trajectory' | 'status' | 'default';
  value?: string;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  value,
  className = '',
}) => {
  const effectiveVal = (value || String(children)).toLowerCase().trim();

  let styles = 'bg-[#0B2240] text-slate-300 border-[#1B365D]';

  if (variant === 'sentiment') {
    if (effectiveVal.includes('pos')) {
      styles = 'bg-emerald-950/70 text-emerald-300 border-emerald-700/60';
    } else if (effectiveVal.includes('neg')) {
      styles = 'bg-[#421210]/80 text-[#FCA5A5] border-[#D03027]/70';
    } else {
      styles = 'bg-amber-950/60 text-amber-300 border-amber-700/60';
    }
  } else if (variant === 'severity') {
    if (effectiveVal === 'critical') {
      styles = 'bg-[#4E0E0C] text-[#FEE2E2] border-[#D03027] font-bold animate-pulse';
    } else if (effectiveVal === 'high') {
      styles = 'bg-orange-950/80 text-orange-300 border-orange-600/70 font-semibold';
    } else if (effectiveVal === 'medium') {
      styles = 'bg-amber-950/70 text-amber-300 border-amber-600/60';
    } else {
      styles = 'bg-[#0B2240] text-slate-300 border-[#1B365D]';
    }
  } else if (variant === 'trajectory') {
    if (effectiveVal === 'emerging') {
      styles = 'bg-[#4E0E0C] text-[#FCA5A5] border-[#D03027] font-bold';
    } else if (effectiveVal === 'improving') {
      styles = 'bg-emerald-950/80 text-emerald-300 border-emerald-600 font-semibold';
    } else {
      styles = 'bg-[#0B2545] text-sky-300 border-[#0076BE]/70';
    }
  } else if (variant === 'status') {
    if (effectiveVal === 'approved') {
      styles = 'bg-emerald-950/80 text-emerald-300 border-emerald-600 font-semibold';
    } else if (effectiveVal === 'rejected') {
      styles = 'bg-[#4E0E0C] text-[#FCA5A5] border-[#D03027] font-semibold';
    } else if (effectiveVal === 'modified') {
      styles = 'bg-indigo-950/80 text-indigo-300 border-indigo-600 font-semibold';
    } else {
      styles = 'bg-amber-950/80 text-amber-300 border-amber-600 font-semibold animate-pulse';
    }
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles} ${className}`}
    >
      {children}
    </span>
  );
};

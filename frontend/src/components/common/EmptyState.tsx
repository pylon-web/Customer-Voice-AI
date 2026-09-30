import React from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionLabel,
  onAction,
  icon,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-slate-800 rounded-xl bg-slate-900/30">
      <div className="p-3 mb-4 rounded-full bg-slate-800/80 text-slate-400">
        {icon || <Inbox className="w-8 h-8" />}
      </div>
      <h4 className="text-base font-medium text-slate-200">{title}</h4>
      <p className="mt-1 text-sm text-slate-400 max-w-sm">{description}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-4 px-4 py-2 text-sm font-medium text-white bg-sky-600 rounded-lg hover:bg-sky-500 transition"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};

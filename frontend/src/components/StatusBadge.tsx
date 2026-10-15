import React from 'react';
import { IssueStatus } from '@/types';

interface StatusBadgeProps {
  status: IssueStatus | string;
  size?: 'sm' | 'md';
}

export function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const normalized = (status || 'unresolved').toLowerCase();

  const styles: Record<string, string> = {
    unresolved: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    investigating: 'bg-blue-500/10 text-blue-300 border-blue-500/30',
    resolved: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    ignored: 'bg-slate-700/30 text-slate-400 border-slate-600/40',
  };

  const labels: Record<string, string> = {
    unresolved: 'Unresolved',
    investigating: 'Investigating',
    resolved: 'Resolved',
    ignored: 'Ignored',
  };

  const style = styles[normalized] || styles.unresolved;
  const label = labels[normalized] || normalized;
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center font-mono font-medium rounded-md border ${sizeClasses} ${style}`}
    >
      {label}
    </span>
  );
}

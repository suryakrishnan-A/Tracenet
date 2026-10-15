import React from 'react';
import { SeverityLevel } from '@/types';

interface SeverityBadgeProps {
  severity: SeverityLevel | string;
  size?: 'sm' | 'md';
}

export function SeverityBadge({ severity, size = 'md' }: SeverityBadgeProps) {
  const normalized = (severity || 'error').toLowerCase();

  const styles: Record<string, string> = {
    critical: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
    error: 'bg-red-500/10 text-red-400 border-red-500/30',
    warning: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    info: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  };

  const dotStyles: Record<string, string> = {
    critical: 'bg-rose-400',
    error: 'bg-red-400',
    warning: 'bg-amber-400',
    info: 'bg-blue-400',
  };

  const style = styles[normalized] || styles.error;
  const dotStyle = dotStyles[normalized] || dotStyles.error;
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono font-medium rounded-md border ${sizeClasses} ${style}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dotStyle}`} />
      <span className="capitalize">{normalized}</span>
    </span>
  );
}

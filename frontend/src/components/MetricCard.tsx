import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  icon: LucideIcon;
  variant?: 'default' | 'danger' | 'warning' | 'success' | 'info';
}

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = 'default',
}: MetricCardProps) {
  const iconVariants = {
    default: 'bg-slate-800 text-slate-300 border-slate-700/60',
    danger: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    warning: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    success: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    info: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  };

  const textVariants = {
    default: 'text-white',
    danger: 'text-rose-400',
    warning: 'text-amber-400',
    success: 'text-emerald-400',
    info: 'text-blue-400',
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-[#0d131f] p-5 flex flex-col justify-between hover:border-slate-700/80 transition-colors">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
          {title}
        </span>
        <div
          className={`h-8 w-8 rounded-lg border flex items-center justify-center ${iconVariants[variant]}`}
        >
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <div className="mt-4">
        <div className={`text-2xl sm:text-3xl font-bold font-mono tracking-tight ${textVariants[variant]}`}>
          {typeof value === 'number' ? value.toLocaleString() : value}
        </div>
        {subtitle && (
          <p className="text-xs text-slate-400 mt-1 font-sans">{subtitle}</p>
        )}
      </div>
    </div>
  );
}

'use client';

import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  CartesianGrid,
} from 'recharts';
import { Layers } from 'lucide-react';
import { SeverityLevel } from '@/types';

interface SeverityDistributionChartProps {
  counts: Record<SeverityLevel, number>;
}

export function SeverityDistributionChart({ counts }: SeverityDistributionChartProps) {
  const chartData = [
    { name: 'Critical', key: 'critical', count: counts.critical || 0, color: '#ef4444' },
    { name: 'Error', key: 'error', count: counts.error || 0, color: '#f87171' },
    { name: 'Warning', key: 'warning', count: counts.warning || 0, color: '#f59e0b' },
    { name: 'Info', key: 'info', count: counts.info || 0, color: '#3b82f6' },
  ];

  const total = chartData.reduce((acc, curr) => acc + curr.count, 0);

  if (total === 0) {
    return (
      <div className="h-64 rounded-xl border border-slate-800 bg-[#0d131f] p-5 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-medium uppercase tracking-wider text-slate-400">
            Severity Distribution
          </h3>
          <Layers className="h-4 w-4 text-slate-500" />
        </div>
        <div className="flex-1 flex flex-col items-center justify-center text-center p-4">
          <p className="text-xs text-slate-400">No issues recorded yet</p>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Severity distribution will display when issues are ingested
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-64 rounded-xl border border-slate-800 bg-[#0d131f] p-5 flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="text-xs font-medium uppercase tracking-wider text-slate-400">
            Severity Breakdown
          </h3>
          <p className="text-[11px] text-slate-500">{total} total issue groups clustered</p>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
          Distribution
        </span>
      </div>

      <div className="flex-1 w-full -ml-3">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis
              dataKey="name"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0f172a',
                borderColor: '#334155',
                borderRadius: '8px',
                fontSize: '12px',
                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
              }}
              labelStyle={{ color: '#94a3b8' }}
              itemStyle={{ color: '#fff' }}
              formatter={(value: number) => [`${value} issues`, 'Count']}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={48}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

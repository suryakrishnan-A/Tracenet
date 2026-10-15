'use client';

import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { Activity } from 'lucide-react';

interface ErrorTimelineChartProps {
  data: { time: string; count: number }[];
}

export function ErrorTimelineChart({ data }: ErrorTimelineChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="h-64 rounded-xl border border-slate-800 bg-[#0d131f] p-5 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-medium uppercase tracking-wider text-slate-400">
            Error Frequency Over Time
          </h3>
          <Activity className="h-4 w-4 text-slate-500" />
        </div>
        <div className="flex-1 flex flex-col items-center justify-center text-center p-4">
          <p className="text-xs text-slate-400">No activity recorded for this period</p>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Incoming error events will populate this timeline
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
            Error Frequency Over Time
          </h3>
          <p className="text-[11px] text-slate-500">Hourly aggregated event volume</p>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
          Live Telemetry
        </span>
      </div>

      <div className="flex-1 w-full -ml-3">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="errorVolumeGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis
              dataKey="time"
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
              labelStyle={{ color: '#94a3b8', fontFamily: 'monospace' }}
              itemStyle={{ color: '#60a5fa' }}
              formatter={(value: number) => [`${value} occurrences`, 'Volume']}
            />
            <Area
              type="monotone"
              dataKey="count"
              stroke="#3b82f6"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#errorVolumeGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

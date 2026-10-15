'use client';

import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { Gauge } from 'lucide-react';

interface PerformanceChartProps {
  data: { time: string; endpoint: string; durationMs: number }[];
}

export function PerformanceChart({ data }: PerformanceChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="h-64 rounded-xl border border-slate-800 bg-[#0d131f] p-5 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-medium uppercase tracking-wider text-slate-400">
            Endpoint Latency & Performance
          </h3>
          <Gauge className="h-4 w-4 text-slate-500" />
        </div>
        <div className="flex-1 flex flex-col items-center justify-center text-center p-4">
          <p className="text-xs text-slate-400">No duration metrics recorded</p>
          <p className="text-[11px] text-slate-500 mt-0.5 max-w-xs">
            Telemetry events containing <code className="text-blue-400">duration_ms</code> will plot response times here
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
            Endpoint Latency (ms)
          </h3>
          <p className="text-[11px] text-slate-500">Real event duration from observed failures</p>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          Telemetry Durations
        </span>
      </div>

      <div className="flex-1 w-full -ml-3">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
              unit="ms"
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
              formatter={(value: number, _name: string, props: { payload?: { endpoint?: string } }) => [
                `${value} ms (${props.payload?.endpoint || 'endpoint'})`,
                'Duration',
              ]}
            />
            <Line
              type="monotone"
              dataKey="durationMs"
              stroke="#10b981"
              strokeWidth={2}
              dot={{ r: 3, fill: '#10b981' }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

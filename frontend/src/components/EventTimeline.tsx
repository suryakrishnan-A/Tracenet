'use client';

import React, { useState } from 'react';
import {
  Clock,
  Globe,
  Gauge,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Tag,
  Calendar,
} from 'lucide-react';
import { TelemetryEventRead } from '@/types';
import { SeverityBadge } from './SeverityBadge';
import { StackTraceViewer } from './StackTraceViewer';

interface EventTimelineProps {
  events: TelemetryEventRead[];
}

export function EventTimeline({ events }: EventTimelineProps) {
  // Store expanded state per event ID, default expand first event
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>(() => {
    if (events.length > 0) {
      return { [events[0].id]: true };
    }
    return {};
  });

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  if (events.length === 0) {
    return (
      <div className="p-8 text-center text-xs text-slate-500 font-mono rounded-xl border border-slate-800 bg-[#0d131f]">
        No recent telemetry event occurrences recorded for this issue.
      </div>
    );
  }

  // Display events in chronological order (oldest to newest, or newest to oldest clearly labeled)
  // The backend returns events ordered by timestamp DESC. Let's make it intuitive:
  // Sort by timestamp DESC so the latest occurrence is at the top, clearly labeled.
  return (
    <div className="space-y-3">
      {events.map((event, index) => {
        const isExpanded = !!expandedIds[event.id];
        const eventDate = new Date(event.timestamp);
        const receivedDate = new Date(event.received_at);

        const statusColor =
          event.http_status && event.http_status >= 500
            ? 'text-rose-400 bg-rose-500/10 border-rose-500/30'
            : event.http_status && event.http_status >= 400
            ? 'text-amber-400 bg-amber-500/10 border-amber-500/30'
            : 'text-slate-400 bg-slate-800 border-slate-700';

        return (
          <div
            key={event.id}
            className="rounded-xl border border-slate-800 bg-[#0d131f] overflow-hidden transition"
          >
            {/* Header row */}
            <div
              onClick={() => toggleExpand(event.id)}
              className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer hover:bg-slate-900/40 transition select-none"
            >
              <div className="flex items-center gap-3">
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/60">
                  #{events.length - index}
                </span>
                <SeverityBadge severity={event.severity} size="sm" />
                <span className="text-xs font-semibold text-white truncate max-w-sm sm:max-w-md">
                  {event.message}
                </span>
              </div>

              <div className="flex items-center gap-3 text-xs text-slate-400 font-mono shrink-0">
                {event.endpoint && (
                  <span className="flex items-center gap-1 text-[11px] text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                    <Globe className="h-3 w-3" />
                    {event.endpoint}
                  </span>
                )}

                {event.http_status && (
                  <span className={`text-[11px] px-1.5 py-0.5 rounded border font-mono ${statusColor}`}>
                    {event.http_status}
                  </span>
                )}

                {event.duration_ms !== null && event.duration_ms !== undefined && (
                  <span className="flex items-center gap-1 text-[11px] text-emerald-400">
                    <Gauge className="h-3 w-3" />
                    {event.duration_ms.toFixed(1)}ms
                  </span>
                )}

                <span className="flex items-center gap-1 text-[11px] text-slate-400">
                  <Clock className="h-3 w-3 text-slate-500" />
                  {eventDate.toLocaleTimeString()}
                </span>

                <button
                  type="button"
                  className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white"
                  aria-label={isExpanded ? 'Collapse event' : 'Expand event'}
                >
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Expanded details body */}
            {isExpanded && (
              <div className="p-4 border-t border-slate-800/80 bg-slate-950/40 space-y-4">
                {/* Meta Attributes Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
                  <div className="p-2.5 rounded-lg bg-[#070b12] border border-slate-800/80 space-y-1">
                    <span className="text-slate-500 text-[10px] uppercase">Event Timestamp</span>
                    <p className="text-slate-300 flex items-center gap-1">
                      <Calendar className="h-3 w-3 text-slate-500" />
                      {eventDate.toISOString()}
                    </p>
                  </div>
                  <div className="p-2.5 rounded-lg bg-[#070b12] border border-slate-800/80 space-y-1">
                    <span className="text-slate-500 text-[10px] uppercase">Received At</span>
                    <p className="text-slate-300 flex items-center gap-1">
                      <Clock className="h-3 w-3 text-slate-500" />
                      {receivedDate.toISOString()}
                    </p>
                  </div>
                  <div className="p-2.5 rounded-lg bg-[#070b12] border border-slate-800/80 space-y-1">
                    <span className="text-slate-500 text-[10px] uppercase">Event Type</span>
                    <p className="text-slate-300 flex items-center gap-1">
                      <Tag className="h-3 w-3 text-slate-500" />
                      {event.event_type}
                    </p>
                  </div>
                  <div className="p-2.5 rounded-lg bg-[#070b12] border border-slate-800/80 space-y-1">
                    <span className="text-slate-500 text-[10px] uppercase">Event ID</span>
                    <p className="text-slate-400 truncate" title={event.id}>
                      {event.id}
                    </p>
                  </div>
                </div>

                {/* Stack Trace */}
                <div>
                  <h4 className="text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider font-mono">
                    Stack Trace
                  </h4>
                  <StackTraceViewer stackTrace={event.stack_trace} />
                </div>

                {/* Metadata JSON Inspector */}
                {event.metadata_json && Object.keys(event.metadata_json).length > 0 && (
                  <div>
                    <h4 className="text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider font-mono">
                      Event Metadata (JSON)
                    </h4>
                    <pre className="p-3 rounded-lg bg-[#070b12] border border-slate-800 text-xs font-mono text-slate-300 overflow-auto max-h-48 leading-relaxed">
                      {JSON.stringify(event.metadata_json, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

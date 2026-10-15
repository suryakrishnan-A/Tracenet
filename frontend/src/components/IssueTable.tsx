'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowRight, Clock, Hash } from 'lucide-react';
import { IssueGroupRead } from '@/types';
import { SeverityBadge } from './SeverityBadge';
import { StatusBadge } from './StatusBadge';

interface IssueTableProps {
  issues: IssueGroupRead[];
  loading?: boolean;
}

export function IssueTable({ issues, loading }: IssueTableProps) {
  if (loading) {
    return (
      <div className="rounded-xl border border-slate-800 bg-[#0d131f] overflow-hidden">
        <div className="p-4 space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="h-14 rounded-lg bg-slate-900/60 animate-pulse border border-slate-800/40"
            />
          ))}
        </div>
      </div>
    );
  }

  if (issues.length === 0) {
    return null;
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-[#0d131f] overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-800/80 bg-slate-950/60 text-[11px] font-mono uppercase tracking-wider text-slate-400">
              <th className="py-3 px-4 font-medium">Issue Group</th>
              <th className="py-3 px-4 font-medium">Severity</th>
              <th className="py-3 px-4 font-medium">Status</th>
              <th className="py-3 px-4 font-medium text-center">Occurrences</th>
              <th className="py-3 px-4 font-medium hidden md:table-cell">Last Seen</th>
              <th className="py-3 px-4 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50 text-xs">
            {issues.map((issue) => {
              const lastSeenDate = new Date(issue.last_seen);
              const formattedDate = lastSeenDate.toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              });

              return (
                <tr
                  key={issue.id}
                  className="hover:bg-slate-900/40 transition-colors group cursor-pointer"
                >
                  <td className="py-3.5 px-4 max-w-xs sm:max-w-md">
                    <Link href={`/issues/${issue.id}`} className="block">
                      <p className="font-semibold text-slate-100 group-hover:text-blue-400 transition truncate">
                        {issue.title}
                      </p>
                      <div className="flex items-center gap-2 mt-1 text-[11px] font-mono text-slate-500">
                        <span className="flex items-center gap-0.5">
                          <Hash className="h-3 w-3 text-slate-600" />
                          {issue.fingerprint.slice(0, 12)}...
                        </span>
                      </div>
                    </Link>
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <SeverityBadge severity={issue.current_severity} size="sm" />
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <StatusBadge status={issue.status} size="sm" />
                  </td>
                  <td className="py-3.5 px-4 text-center whitespace-nowrap font-mono font-medium">
                    <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-200 text-[11px]">
                      {issue.occurrence_count.toLocaleString()}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap text-slate-400 font-mono text-[11px] hidden md:table-cell">
                    <span className="flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5 text-slate-500" />
                      {formattedDate}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right whitespace-nowrap">
                    <Link
                      href={`/issues/${issue.id}`}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800/60 hover:bg-blue-600 text-slate-300 hover:text-white transition font-medium text-xs group-hover:bg-blue-600 group-hover:text-white"
                    >
                      <span>Investigate</span>
                      <ArrowRight className="h-3 w-3" />
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

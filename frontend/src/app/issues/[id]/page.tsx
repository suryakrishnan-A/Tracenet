'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  Calendar,
  Clock,
  Copy,
  Check,
  Hash,
  RefreshCw,
  Repeat,
  ShieldAlert,
  AlertCircle,
  Key,
  CheckCircle2,
  SlidersHorizontal,
} from 'lucide-react';
import { Navbar } from '@/components/Navbar';
import { SeverityBadge } from '@/components/SeverityBadge';
import { StatusBadge } from '@/components/StatusBadge';
import { EventTimeline } from '@/components/EventTimeline';
import { ApiKeyModal } from '@/components/ApiKeyModal';
import { InvestigationPanel } from '@/components/InvestigationPanel';

import { getIssueById, updateIssueStatus } from '@/lib/api/issues';
import { checkSystemHealth } from '@/lib/api/health';
import { apiClient, ApiError } from '@/lib/api/client';
import {
  IssueGroupRead,
  TelemetryEventRead,
  IssueStatus,
  SystemStatusState,
} from '@/types';

export default function IssueDetailPage() {
  const params = useParams();
  const issueId = params?.id as string;

  const [issue, setIssue] = useState<IssueGroupRead | null>(null);
  const [events, setEvents] = useState<TelemetryEventRead[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusUpdating, setStatusUpdating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isUnauthorized, setIsUnauthorized] = useState<boolean>(false);
  const [copiedFingerprint, setCopiedFingerprint] = useState<boolean>(false);
  const [isKeyModalOpen, setIsKeyModalOpen] = useState<boolean>(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatusState>({
    backendReachable: false,
    v1ApiReachable: false,
    data: null,
  });

  const fetchIssue = useCallback(async () => {
    if (!issueId) return;

    setLoading(true);
    setError(null);
    setIsUnauthorized(false);

    const activeKey = apiClient.getApiKey();
    if (!activeKey) {
      setIsUnauthorized(true);
      setLoading(false);
      return;
    }

    try {
      const data = await getIssueById(issueId);
      setIssue(data.issue);
      setEvents(data.recent_events);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.isUnauthorized()) {
        setIsUnauthorized(true);
      } else if (err instanceof ApiError && err.isNotFound()) {
        setError(`Issue with ID "${issueId}" was not found in this project.`);
      } else {
        const msg = err instanceof Error ? err.message : 'Failed to retrieve issue details';
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }, [issueId]);

  useEffect(() => {
    checkSystemHealth().then(setSystemStatus).catch(() => {});
  }, []);

  useEffect(() => {
    fetchIssue();
  }, [fetchIssue]);

  const handleStatusChange = async (newStatus: IssueStatus) => {
    if (!issueId || !issue || issue.status === newStatus) return;

    setStatusUpdating(true);
    try {
      const updated = await updateIssueStatus(issueId, newStatus);
      setIssue(updated);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update issue status';
      alert(`Error updating status: ${msg}`);
    } finally {
      setStatusUpdating(false);
    }
  };

  const handleCopyFingerprint = async () => {
    if (!issue?.fingerprint) return;
    try {
      await navigator.clipboard.writeText(issue.fingerprint);
      setCopiedFingerprint(true);
      setTimeout(() => setCopiedFingerprint(false), 2000);
    } catch {
      // Fallback
    }
  };

  const allowedStatuses: IssueStatus[] = ['unresolved', 'investigating', 'resolved', 'ignored'];

  return (
    <div className="min-h-screen flex flex-col bg-[#070b14] text-slate-100 antialiased selection:bg-blue-600 selection:text-white">
      <Navbar
        backendReachable={systemStatus.backendReachable}
        onKeyChanged={fetchIssue}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Back Link & Breadcrumb */}
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <Link
            href="/issues"
            className="inline-flex items-center gap-1 hover:text-white transition"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Issues</span>
          </Link>
          <span>/</span>
          <span className="text-slate-300 truncate max-w-xs">{issueId}</span>
        </div>

        {/* Unauthorized Banner */}
        {isUnauthorized && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <ShieldAlert className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h3 className="text-xs font-semibold text-amber-300">
                  Authentication Required
                </h3>
                <p className="text-xs text-slate-300">
                  Please provide a project API key to inspect this scoped issue cluster.
                </p>
              </div>
            </div>
            <button
              onClick={() => setIsKeyModalOpen(true)}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold text-xs transition shrink-0"
            >
              <Key className="h-3.5 w-3.5" />
              <span>Set Project API Key</span>
            </button>
          </div>
        )}

        {/* Error Banner */}
        {error && !isUnauthorized && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-5 space-y-3">
            <div className="flex items-center gap-2 text-rose-300 text-xs font-semibold">
              <AlertCircle className="h-4 w-4 text-rose-400" />
              <span>{error}</span>
            </div>
            <Link
              href="/issues"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Back to Issue Explorer</span>
            </Link>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="space-y-4">
            <div className="h-36 rounded-xl bg-slate-900/60 animate-pulse border border-slate-800" />
            <div className="h-64 rounded-xl bg-slate-900/40 animate-pulse border border-slate-800" />
          </div>
        )}

        {/* Main Content */}
        {!loading && issue && (
          <div className="space-y-6">
            {/* Header Card */}
            <div className="rounded-2xl border border-slate-800 bg-[#0d131f] p-6 space-y-5">
              <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                <div className="space-y-2 max-w-3xl">
                  <div className="flex flex-wrap items-center gap-2">
                    <SeverityBadge severity={issue.current_severity} />
                    <StatusBadge status={issue.status} />
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/60">
                      {issue.occurrence_count.toLocaleString()} occurrences
                    </span>
                  </div>

                  <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white leading-snug">
                    {issue.title}
                  </h1>

                  {/* Fingerprint row */}
                  <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                    <span className="text-slate-500">Fingerprint:</span>
                    <span className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800/80 text-blue-400 truncate max-w-xs sm:max-w-md">
                      {issue.fingerprint}
                    </span>
                    <button
                      onClick={handleCopyFingerprint}
                      className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition"
                      title="Copy fingerprint hash"
                    >
                      {copiedFingerprint ? (
                        <Check className="h-3.5 w-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Workflow Status Controls */}
                <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4 space-y-2.5 shrink-0">
                  <div className="flex items-center gap-2 text-xs font-medium text-slate-300 font-mono">
                    <SlidersHorizontal className="h-3.5 w-3.5 text-blue-400" />
                    <span>Triage Status</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {allowedStatuses.map((st) => {
                      const isCurrent = issue.status === st;
                      return (
                        <button
                          key={st}
                          onClick={() => handleStatusChange(st)}
                          disabled={statusUpdating || isCurrent}
                          className={`px-2.5 py-1 rounded text-xs font-mono font-medium transition capitalize ${
                            isCurrent
                              ? 'bg-blue-600 text-white shadow-sm'
                              : 'bg-slate-900 hover:bg-slate-850 text-slate-400 hover:text-white border border-slate-800'
                          }`}
                        >
                          {st}
                        </button>
                      );
                    })}
                  </div>
                  {statusUpdating && (
                    <p className="text-[10px] text-blue-400 font-mono animate-pulse">
                      Updating status...
                    </p>
                  )}
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="pt-4 border-t border-slate-800/80 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
                <div>
                  <span className="text-slate-500 text-[10px] uppercase">First Seen</span>
                  <p className="text-slate-200 mt-0.5">
                    {new Date(issue.first_seen).toLocaleString()}
                  </p>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase">Last Seen</span>
                  <p className="text-slate-200 mt-0.5">
                    {new Date(issue.last_seen).toLocaleString()}
                  </p>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase">Created</span>
                  <p className="text-slate-200 mt-0.5">
                    {new Date(issue.created_at).toLocaleString()}
                  </p>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase">Project ID</span>
                  <p className="text-slate-400 mt-0.5 truncate" title={issue.project_id}>
                    {issue.project_id}
                  </p>
                </div>
              </div>
            </div>

            {/* AI Incident Investigation Assistant Panel */}
            <InvestigationPanel
              issueId={issueId}
              onOpenKeyModal={() => setIsKeyModalOpen(true)}
            />

            {/* Recent Telemetry Occurrences */}
            <div className="space-y-3">

              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-white uppercase tracking-wider font-mono">
                    Recent Associated Telemetry Events ({events.length})
                  </h2>
                  <p className="text-xs text-slate-400">
                    Chronological execution trace, call stacks, and endpoint metadata.
                  </p>
                </div>

                <button
                  onClick={fetchIssue}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-medium transition border border-slate-700/60"
                >
                  <RefreshCw className="h-3 w-3" />
                  <span>Refresh Events</span>
                </button>
              </div>

              <EventTimeline events={events} />
            </div>
          </div>
        )}
      </main>

      <ApiKeyModal
        isOpen={isKeyModalOpen}
        onClose={() => setIsKeyModalOpen(false)}
        onKeyChanged={fetchIssue}
      />
    </div>
  );
}

'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import {
  AlertTriangle,
  Flame,
  Layers,
  Repeat,
  RefreshCw,
  Key,
  PlusCircle,
  ArrowRight,
  ShieldAlert,
  Server,
  Activity,
} from 'lucide-react';
import { Navbar } from '@/components/Navbar';
import { MetricCard } from '@/components/MetricCard';
import { IssueTable } from '@/components/IssueTable';
import { ErrorTimelineChart } from '@/components/Charts/ErrorTimelineChart';
import { SeverityDistributionChart } from '@/components/Charts/SeverityDistributionChart';
import { PerformanceChart } from '@/components/Charts/PerformanceChart';
import { ApiKeyModal } from '@/components/ApiKeyModal';
import { EmptyState } from '@/components/EmptyState';
import { getIssues, calculateDashboardMetrics } from '@/lib/api/issues';
import { checkSystemHealth } from '@/lib/api/health';
import { apiClient, ApiError } from '@/lib/api/client';
import {
  IssueGroupRead,
  DashboardMetrics,
  SystemStatusState,
  TelemetryEventRead,
} from '@/types';

export default function DashboardOverviewPage() {
  const [issues, setIssues] = useState<IssueGroupRead[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatusState>({
    backendReachable: false,
    v1ApiReachable: false,
    data: null,
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isUnauthorized, setIsUnauthorized] = useState<boolean>(false);
  const [isKeyModalOpen, setIsKeyModalOpen] = useState<boolean>(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    setIsUnauthorized(false);

    // 1. Health check (resilient)
    try {
      const health = await checkSystemHealth();
      setSystemStatus(health);
    } catch {
      // Handled inside checkSystemHealth
    }

    // 2. Fetch issues for overview
    const activeKey = apiClient.getApiKey();
    if (!activeKey) {
      setIsUnauthorized(true);
      setLoading(false);
      return;
    }

    try {
      // Fetch up to 100 recent issues for comprehensive metrics calculation
      const response = await getIssues({ per_page: 100, page: 1 });
      setIssues(response.items);
      setTotalCount(response.total);

      // Compute metrics directly from real backend issues
      const calculated = calculateDashboardMetrics(response.items, response.total, []);
      setMetrics(calculated);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.isUnauthorized()) {
        setIsUnauthorized(true);
      } else {
        const msg = err instanceof Error ? err.message : 'Failed to retrieve telemetry issues';
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const recentIssues = issues.slice(0, 5);

  return (
    <div className="min-h-screen flex flex-col bg-[#070b14] text-slate-100 antialiased selection:bg-blue-600 selection:text-white">
      <Navbar
        backendReachable={systemStatus.backendReachable}
        onKeyChanged={loadData}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Header bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/80">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-white">
                Incident Investigation Overview
              </h1>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                Phase 4 Live
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Real-time failure telemetry, deterministic clustering, and operational health metrics.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={loadData}
              disabled={loading}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-750 disabled:opacity-50 text-slate-200 text-xs font-medium transition border border-slate-700/60 shadow-sm"
              title="Refresh dashboard data"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>

            <Link
              href="/issues"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition shadow-lg shadow-blue-600/20"
            >
              <span>Explore All Issues</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>

        {/* Unauthorized / No API Key Alert Banner */}
        {isUnauthorized && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <ShieldAlert className="h-6 w-6 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-amber-300">
                  Project Authentication Required (HTTP 401)
                </h3>
                <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
                  No active project API key was detected, or the configured key was rejected. TraceNest requires an authenticated project key to query scoped issue clusters and error telemetry.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setIsKeyModalOpen(true)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold text-xs transition"
              >
                <Key className="h-4 w-4" />
                <span>Configure Project Key</span>
              </button>
            </div>
          </div>
        )}

        {/* Server Error State */}
        {error && !isUnauthorized && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-5 flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-rose-300">Telemetry Query Error</h3>
                <p className="text-xs text-slate-300">{error}</p>
              </div>
            </div>
            <button
              onClick={loadData}
              className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium transition shrink-0"
            >
              Retry
            </button>
          </div>
        )}

        {/* KPI Metric Cards */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Total Issue Groups"
            value={loading ? '...' : metrics ? metrics.totalIssues : 0}
            subtitle="Unique deterministic fingerprints"
            icon={Layers}
            variant="default"
          />
          <MetricCard
            title="Unresolved Issues"
            value={loading ? '...' : metrics ? metrics.unresolvedIssues : 0}
            subtitle="Awaiting triage or fix"
            icon={AlertTriangle}
            variant="warning"
          />
          <MetricCard
            title="Critical Issues"
            value={loading ? '...' : metrics ? metrics.criticalIssues : 0}
            subtitle="Highest severity incidents"
            icon={Flame}
            variant="danger"
          />
          <MetricCard
            title="Total Occurrences"
            value={loading ? '...' : metrics ? metrics.totalOccurrences : 0}
            subtitle="Cumulated event volume"
            icon={Repeat}
            variant="info"
          />
        </section>

        {/* Charts Grid */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ErrorTimelineChart data={metrics ? metrics.timelineBuckets : []} />
          <SeverityDistributionChart
            counts={
              metrics
                ? metrics.severityCounts
                : { critical: 0, error: 0, warning: 0, info: 0 }
            }
          />
        </section>

        {/* Recent Issue Activity Table */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-white uppercase tracking-wider font-mono">
                Recent Issue Activity
              </h2>
              <p className="text-xs text-slate-400">
                Latest active issue clusters sorted by last seen timestamp
              </p>
            </div>
            {totalCount > 5 && (
              <Link
                href="/issues"
                className="text-xs text-blue-400 hover:text-blue-300 font-medium inline-flex items-center gap-1"
              >
                <span>View all {totalCount} issues</span>
                <ArrowRight className="h-3 w-3" />
              </Link>
            )}
          </div>

          {recentIssues.length > 0 ? (
            <IssueTable issues={recentIssues} loading={loading} />
          ) : (
            !loading && (
              <EmptyState
                icon={Activity}
                title="No Issues Ingested Yet"
                description={
                  isUnauthorized
                    ? 'Connect an API key to display monitored issues for your project.'
                    : 'Your service has not ingested any error telemetry yet. Post events to /api/v1/telemetry to begin clustering.'
                }
                actionLabel={isUnauthorized ? 'Set API Key' : undefined}
                onAction={isUnauthorized ? () => setIsKeyModalOpen(true) : undefined}
              />
            )
          )}
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-[#070b14] py-6 text-center text-xs text-slate-500">
        <p>TraceNest • Application Failure Investigation Platform • Phase 4 Operational</p>
      </footer>

      <ApiKeyModal
        isOpen={isKeyModalOpen}
        onClose={() => setIsKeyModalOpen(false)}
        onKeyChanged={loadData}
      />
    </div>
  );
}

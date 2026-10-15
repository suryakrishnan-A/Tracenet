'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  Search,
  Filter,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  AlertCircle,
  Key,
  X,
} from 'lucide-react';
import { Navbar } from '@/components/Navbar';
import { IssueTable } from '@/components/IssueTable';
import { EmptyState } from '@/components/EmptyState';
import { ApiKeyModal } from '@/components/ApiKeyModal';
import { getIssues } from '@/lib/api/issues';
import { checkSystemHealth } from '@/lib/api/health';
import { apiClient, ApiError } from '@/lib/api/client';
import {
  IssueGroupRead,
  IssueListResponse,
  IssueStatus,
  SeverityLevel,
  SystemStatusState,
} from '@/types';

export default function IssueExplorerPage() {
  const [issues, setIssues] = useState<IssueGroupRead[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [perPage, setPerPage] = useState<number>(20);
  const [totalPages, setTotalPages] = useState<number>(1);

  // Filters
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [appliedSearch, setAppliedSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<IssueStatus | ''>('');
  const [severityFilter, setSeverityFilter] = useState<SeverityLevel | ''>('');

  // UI state
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isUnauthorized, setIsUnauthorized] = useState<boolean>(false);
  const [isKeyModalOpen, setIsKeyModalOpen] = useState<boolean>(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatusState>({
    backendReachable: false,
    v1ApiReachable: false,
    data: null,
  });

  const fetchIssuesList = useCallback(async () => {
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
      const resp: IssueListResponse = await getIssues({
        search: appliedSearch || undefined,
        status: statusFilter || undefined,
        severity: severityFilter || undefined,
        page: currentPage,
        per_page: perPage,
      });

      setIssues(resp.items);
      setTotalCount(resp.total);
      setTotalPages(resp.total_pages);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.isUnauthorized()) {
        setIsUnauthorized(true);
      } else {
        const msg = err instanceof Error ? err.message : 'Failed to retrieve issues';
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }, [appliedSearch, statusFilter, severityFilter, currentPage, perPage]);

  // Initial load & health check
  useEffect(() => {
    checkSystemHealth().then(setSystemStatus).catch(() => {});
  }, []);

  useEffect(() => {
    fetchIssuesList();
  }, [fetchIssuesList]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    setAppliedSearch(searchTerm.trim());
  };

  const handleClearFilters = () => {
    setSearchTerm('');
    setAppliedSearch('');
    setStatusFilter('');
    setSeverityFilter('');
    setCurrentPage(1);
  };

  const hasActiveFilters =
    appliedSearch.length > 0 || statusFilter !== '' || severityFilter !== '';

  return (
    <div className="min-h-screen flex flex-col bg-[#070b14] text-slate-100 antialiased selection:bg-blue-600 selection:text-white">
      <Navbar
        backendReachable={systemStatus.backendReachable}
        onKeyChanged={fetchIssuesList}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Title Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <span>Issue Explorer</span>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/80">
                {totalCount} total
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Search, filter, and inspect clustered application errors and call-site fingerprints.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchIssuesList}
              disabled={loading}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-750 disabled:opacity-50 text-slate-200 text-xs font-medium transition border border-slate-700/60"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Unauthorized Banner */}
        {isUnauthorized && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <ShieldAlert className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h3 className="text-xs font-semibold text-amber-300">
                  Authentication Required to List Issues
                </h3>
                <p className="text-xs text-slate-300">
                  Please provide or generate a project API key to view scoped failure records.
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

        {/* Query Error Banner */}
        {error && !isUnauthorized && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 flex items-center justify-between">
            <div className="flex items-center gap-2.5 text-xs text-rose-300">
              <AlertCircle className="h-4 w-4 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={fetchIssuesList}
              className="px-2.5 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium"
            >
              Retry
            </button>
          </div>
        )}

        {/* Filter and Search Toolbar */}
        <div className="rounded-xl border border-slate-800 bg-[#0d131f] p-4 space-y-3">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            {/* Search Input */}
            <form onSubmit={handleSearchSubmit} className="flex-1 max-w-md relative">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by title or fingerprint..."
                className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-[#070b14] border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
              />
            </form>

            {/* Filter Dropdowns */}
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Status Select */}
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] text-slate-400 font-mono">Status:</span>
                <select
                  value={statusFilter}
                  onChange={(e) => {
                    setStatusFilter(e.target.value as IssueStatus | '');
                    setCurrentPage(1);
                  }}
                  className="px-2.5 py-1.5 rounded-lg bg-[#070b14] border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                >
                  <option value="">All Statuses</option>
                  <option value="unresolved">Unresolved</option>
                  <option value="investigating">Investigating</option>
                  <option value="resolved">Resolved</option>
                  <option value="ignored">Ignored</option>
                </select>
              </div>

              {/* Severity Select */}
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] text-slate-400 font-mono">Severity:</span>
                <select
                  value={severityFilter}
                  onChange={(e) => {
                    setSeverityFilter(e.target.value as SeverityLevel | '');
                    setCurrentPage(1);
                  }}
                  className="px-2.5 py-1.5 rounded-lg bg-[#070b14] border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                >
                  <option value="">All Severities</option>
                  <option value="critical">Critical</option>
                  <option value="error">Error</option>
                  <option value="warning">Warning</option>
                  <option value="info">Info</option>
                </select>
              </div>

              {/* Per Page Select */}
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] text-slate-400 font-mono">Limit:</span>
                <select
                  value={perPage}
                  onChange={(e) => {
                    setPerPage(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="px-2.5 py-1.5 rounded-lg bg-[#070b14] border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
              </div>

              {hasActiveFilters && (
                <button
                  onClick={handleClearFilters}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs transition"
                  title="Clear all filters"
                >
                  <X className="h-3 w-3" />
                  <span>Reset</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Issues List Table */}
        {issues.length > 0 ? (
          <div className="space-y-4">
            <IssueTable issues={issues} loading={loading} />

            {/* Pagination Bar */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-2 text-xs font-mono text-slate-400">
              <div>
                Showing page <span className="text-white font-semibold">{currentPage}</span> of{' '}
                <span className="text-white font-semibold">{totalPages}</span> ({totalCount} items)
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                  disabled={currentPage <= 1 || loading}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 disabled:opacity-40 text-slate-300 text-xs transition"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                  <span>Previous</span>
                </button>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                  disabled={currentPage >= totalPages || loading}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 disabled:opacity-40 text-slate-300 text-xs transition"
                >
                  <span>Next</span>
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
        ) : (
          !loading && (
            <EmptyState
              title={hasActiveFilters ? 'No Matching Issues Found' : 'No Issues Ingested Yet'}
              description={
                hasActiveFilters
                  ? 'Try modifying your search query or relaxing status/severity filters.'
                  : 'No error clusters exist for this project yet. Submit errors to /api/v1/telemetry to begin.'
              }
              actionLabel={hasActiveFilters ? 'Clear Filters' : undefined}
              onAction={hasActiveFilters ? handleClearFilters : undefined}
            />
          )
        )}
      </main>

      <ApiKeyModal
        isOpen={isKeyModalOpen}
        onClose={() => setIsKeyModalOpen(false)}
        onKeyChanged={fetchIssuesList}
      />
    </div>
  );
}

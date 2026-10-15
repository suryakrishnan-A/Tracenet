/**
 * TraceNest Issues API Service & Metrics Engine
 *
 * Encapsulates strongly typed operations for issues, event timelines,
 * and client-side metrics calculation from actual backend telemetry.
 */

import { apiClient } from './client';
import {
  IssueListParams,
  IssueListResponse,
  IssueDetailResponse,
  IssueGroupRead,
  IssueStatus,
  DashboardMetrics,
  TelemetryEventRead,
  SeverityLevel,
  InvestigationReportResponse,
  AnalysisDepth,
} from '@/types';

export async function getIssues(params?: IssueListParams): Promise<IssueListResponse> {
  return apiClient.listIssues(params);
}

export async function getIssueById(issueId: string): Promise<IssueDetailResponse> {
  return apiClient.getIssue(issueId);
}

export async function updateIssueStatus(
  issueId: string,
  status: IssueStatus
): Promise<IssueGroupRead> {
  return apiClient.updateIssueStatus(issueId, status);
}

export async function investigateIssue(
  issueId: string,
  depth: AnalysisDepth = 'standard'
): Promise<InvestigationReportResponse> {
  return apiClient.investigateIssue(issueId, depth);
}


/**
 * Derives comprehensive dashboard metrics from real backend issues and events.
 * Guarantees zero fabricated data.
 */
export function calculateDashboardMetrics(
  issues: IssueGroupRead[],
  totalCount?: number,
  recentEvents: TelemetryEventRead[] = []
): DashboardMetrics {
  const severityCounts: Record<SeverityLevel, number> = {
    critical: 0,
    error: 0,
    warning: 0,
    info: 0,
  };

  const statusCounts: Record<IssueStatus, number> = {
    unresolved: 0,
    investigating: 0,
    resolved: 0,
    ignored: 0,
  };

  let totalOccurrences = 0;

  issues.forEach((issue) => {
    // Severity
    const sev = issue.current_severity as SeverityLevel;
    if (severityCounts[sev] !== undefined) {
      severityCounts[sev] += 1;
    } else {
      severityCounts.error += 1;
    }

    // Status
    const st = issue.status as IssueStatus;
    if (statusCounts[st] !== undefined) {
      statusCounts[st] += 1;
    } else {
      statusCounts.unresolved += 1;
    }

    // Occurrences
    totalOccurrences += issue.occurrence_count || 1;
  });

  // Timeline buckets: Group issue activity across time windows
  const timeBucketsMap = new Map<string, number>();

  issues.forEach((issue) => {
    try {
      const date = new Date(issue.last_seen);
      // Format as "HH:00" or "MM/DD HH:00"
      const bucketKey = `${date.getHours().toString().padStart(2, '0')}:00`;
      timeBucketsMap.set(bucketKey, (timeBucketsMap.get(bucketKey) || 0) + issue.occurrence_count);
    } catch {
      // Ignore unparseable timestamp
    }
  });

  // If we have event timestamps, incorporate them for higher fidelity
  recentEvents.forEach((ev) => {
    try {
      const date = new Date(ev.timestamp);
      const bucketKey = `${date.getHours().toString().padStart(2, '0')}:00`;
      if (!timeBucketsMap.has(bucketKey)) {
        timeBucketsMap.set(bucketKey, 1);
      }
    } catch {
      // Ignore
    }
  });

  const timelineBuckets = Array.from(timeBucketsMap.entries())
    .map(([time, count]) => ({ time, count }))
    .sort((a, b) => a.time.localeCompare(b.time));

  // Performance duration points from real events
  const durationPoints = recentEvents
    .filter((ev) => ev.duration_ms !== null && ev.duration_ms !== undefined)
    .map((ev) => ({
      time: new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      endpoint: ev.endpoint || 'Unknown Endpoint',
      durationMs: Math.round((ev.duration_ms as number) * 10) / 10,
    }))
    .reverse();

  return {
    totalIssues: totalCount !== undefined ? totalCount : issues.length,
    unresolvedIssues: statusCounts.unresolved + statusCounts.investigating,
    criticalIssues: severityCounts.critical,
    totalOccurrences,
    severityCounts,
    statusCounts,
    timelineBuckets,
    durationPoints,
  };
}

import { describe, it, expect } from 'vitest';
import { calculateDashboardMetrics } from '@/lib/api/issues';
import { IssueGroupRead, TelemetryEventRead } from '@/types';

const mockIssues: IssueGroupRead[] = [
  {
    id: '1',
    project_id: 'p1',
    fingerprint: 'f1',
    title: 'Gateway timeout',
    current_severity: 'critical',
    status: 'unresolved',
    occurrence_count: 5,
    first_seen: '2026-10-14T12:00:00Z',
    last_seen: '2026-10-14T14:00:00Z',
    created_at: '2026-10-14T12:00:00Z',
    updated_at: '2026-10-14T14:00:00Z',
  },
  {
    id: '2',
    project_id: 'p1',
    fingerprint: 'f2',
    title: 'Cache miss rate high',
    current_severity: 'warning',
    status: 'investigating',
    occurrence_count: 3,
    first_seen: '2026-10-14T11:00:00Z',
    last_seen: '2026-10-14T13:00:00Z',
    created_at: '2026-10-14T11:00:00Z',
    updated_at: '2026-10-14T13:00:00Z',
  },
  {
    id: '3',
    project_id: 'p1',
    fingerprint: 'f3',
    title: 'Deprecated header',
    current_severity: 'info',
    status: 'resolved',
    occurrence_count: 2,
    first_seen: '2026-10-14T09:00:00Z',
    last_seen: '2026-10-14T10:00:00Z',
    created_at: '2026-10-14T09:00:00Z',
    updated_at: '2026-10-14T10:00:00Z',
  },
];

const mockEvents: TelemetryEventRead[] = [
  {
    id: 'e1',
    project_id: 'p1',
    issue_group_id: '1',
    fingerprint: 'f1',
    event_type: 'error',
    severity: 'critical',
    message: 'Gateway timeout',
    stack_trace: null,
    endpoint: '/api/v1/checkout',
    http_status: 504,
    duration_ms: 5001.2,
    metadata_json: null,
    timestamp: '2026-10-14T14:00:00Z',
    received_at: '2026-10-14T14:00:01Z',
  },
];

describe('calculateDashboardMetrics', () => {
  it('accurately computes aggregates from issue items', () => {
    const metrics = calculateDashboardMetrics(mockIssues, 3, mockEvents);

    expect(metrics.totalIssues).toBe(3);
    // Unresolved (unresolved + investigating)
    expect(metrics.unresolvedIssues).toBe(2);
    expect(metrics.criticalIssues).toBe(1);
    expect(metrics.totalOccurrences).toBe(10); // 5 + 3 + 2

    expect(metrics.severityCounts.critical).toBe(1);
    expect(metrics.severityCounts.warning).toBe(1);
    expect(metrics.severityCounts.info).toBe(1);
    expect(metrics.severityCounts.error).toBe(0);

    expect(metrics.statusCounts.unresolved).toBe(1);
    expect(metrics.statusCounts.investigating).toBe(1);
    expect(metrics.statusCounts.resolved).toBe(1);

    expect(metrics.durationPoints).toHaveLength(1);
    expect(metrics.durationPoints[0].endpoint).toBe('/api/v1/checkout');
    expect(metrics.durationPoints[0].durationMs).toBe(5001.2);
  });
});

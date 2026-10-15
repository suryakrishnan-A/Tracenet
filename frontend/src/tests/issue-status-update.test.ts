import { describe, it, expect, vi, beforeEach } from 'vitest';
import { updateIssueStatus, getIssues, getIssueById } from '@/lib/api/issues';
import { apiClient } from '@/lib/api/client';
import { IssueGroupRead, IssueDetailResponse, IssueListResponse } from '@/types';

describe('Issues API Service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('calls PATCH /api/v1/issues/{id} with new status and returns updated issue', async () => {
    const mockUpdatedIssue: IssueGroupRead = {
      id: 'issue-123',
      project_id: 'proj-456',
      fingerprint: 'fp-789',
      title: 'Redis timeout',
      current_severity: 'critical',
      status: 'investigating',
      occurrence_count: 5,
      first_seen: '2026-10-14T10:00:00Z',
      last_seen: '2026-10-14T12:00:00Z',
      created_at: '2026-10-14T10:00:00Z',
      updated_at: '2026-10-14T12:05:00Z',
    };

    const patchSpy = vi.spyOn(apiClient, 'updateIssueStatus').mockResolvedValue(mockUpdatedIssue);

    const result = await updateIssueStatus('issue-123', 'investigating');

    expect(patchSpy).toHaveBeenCalledWith('issue-123', 'investigating');
    expect(result.status).toBe('investigating');
    expect(result.title).toBe('Redis timeout');
  });

  it('fetches paginated issues with filter parameters', async () => {
    const mockListResponse: IssueListResponse = {
      items: [],
      total: 0,
      page: 1,
      per_page: 20,
      total_pages: 1,
    };

    const listSpy = vi.spyOn(apiClient, 'listIssues').mockResolvedValue(mockListResponse);

    const result = await getIssues({
      status: 'unresolved',
      severity: 'critical',
      search: 'Redis',
      page: 2,
      per_page: 20,
    });

    expect(listSpy).toHaveBeenCalledWith({
      status: 'unresolved',
      severity: 'critical',
      search: 'Redis',
      page: 2,
      per_page: 20,
    });
    expect(result.total).toBe(0);
  });

  it('fetches issue details with recent events', async () => {
    const mockDetail: IssueDetailResponse = {
      issue: {
        id: 'issue-123',
        project_id: 'proj-456',
        fingerprint: 'fp-789',
        title: 'Redis timeout',
        current_severity: 'critical',
        status: 'unresolved',
        occurrence_count: 1,
        first_seen: '2026-10-14T10:00:00Z',
        last_seen: '2026-10-14T10:00:00Z',
        created_at: '2026-10-14T10:00:00Z',
        updated_at: '2026-10-14T10:00:00Z',
      },
      recent_events: [],
    };

    const detailSpy = vi.spyOn(apiClient, 'getIssue').mockResolvedValue(mockDetail);

    const result = await getIssueById('issue-123');
    expect(detailSpy).toHaveBeenCalledWith('issue-123');
    expect(result.issue.id).toBe('issue-123');
    expect(result.recent_events).toEqual([]);
  });
});

import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { IssueTable } from '@/components/IssueTable';
import { IssueGroupRead } from '@/types';

const mockIssues: IssueGroupRead[] = [
  {
    id: 'e86b9781-6cb3-488b-a25e-333d069b2d66',
    project_id: 'a70e4312-45aa-4db0-8f20-e3f5f16fb365',
    fingerprint: 'a4b8686e589886c57f7243c3f2b4e47bc99d91f24f5756461a29392e2ebf3a74',
    title: 'Database connection failed: Timeout',
    current_severity: 'critical',
    status: 'unresolved',
    occurrence_count: 14,
    first_seen: '2026-10-14T10:00:00.000Z',
    last_seen: '2026-10-14T14:30:00.000Z',
    created_at: '2026-10-14T10:00:00.000Z',
    updated_at: '2026-10-14T14:30:00.000Z',
  },
];

describe('IssueTable Component', () => {
  it('renders issues list and columns properly', () => {
    render(<IssueTable issues={mockIssues} />);
    expect(screen.getByText('Database connection failed: Timeout')).toBeInTheDocument();
    expect(screen.getByText('critical')).toBeInTheDocument();
    expect(screen.getByText('Unresolved')).toBeInTheDocument();
    expect(screen.getByText('14')).toBeInTheDocument();
    expect(screen.getByText('Investigate')).toBeInTheDocument();
  });

  it('renders nothing if issue list is empty and not loading', () => {
    const { container } = render(<IssueTable issues={[]} loading={false} />);
    expect(container.firstChild).toBeNull();
  });
});

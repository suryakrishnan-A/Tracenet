import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { InvestigationPanel } from '@/components/InvestigationPanel';
import * as issuesApi from '@/lib/api/issues';
import { InvestigationReportResponse } from '@/types';
import { ApiError } from '@/lib/api/client';

const mockSuccessReport: InvestigationReportResponse = {
  status: 'success',
  issue_id: 'issue-123',
  project_id: 'proj-456',
  generated_at: '2026-10-14T20:00:00Z',
  provider: 'mock',
  model: 'mock-investigator-v1',
  is_ai_generated: true,
  warnings: [],
  error_detail: null,
  report: {
    executive_summary: {
      summary: 'Database connection failure pool timeout.',
      affected_component: '/api/v1/checkout/pay',
      evidence_synthesis: 'Observed 2 socket connection refusals with 500 status codes.',
      certainty_assessment: 'High certainty in connection failure; moderate in root cause.',
    },
    observed_facts: [
      {
        fact: 'OperationalError connection refused to database server',
        evidence_reference: 'EV-1',
        category: 'exception',
      },
      {
        fact: 'HTTP 500 status code returned on checkout endpoint',
        evidence_reference: 'EV-2',
        category: 'endpoint',
      },
    ],
    likely_causes: [
      {
        rank: 1,
        title: 'PostgreSQL Server Unreachable or Saturated',
        explanation: 'The application backend failed to establish a TCP socket to the database server.',
        confidence: 'high',
        supporting_evidence: ['EV-1', 'EV-2'],
        missing_or_contradictory_evidence: 'Database server load and CPU metrics.',
        plausibility_rationale: 'Direct socket refusal recorded in psycopg2 traceback.',
      },
      {
        rank: 2,
        title: 'Network Partition Between VPC Subnets',
        explanation: 'Security group or routing table failure severed database access.',
        confidence: 'medium',
        supporting_evidence: ['EV-1'],
        missing_or_contradictory_evidence: 'VPC flow logs.',
        plausibility_rationale: 'Connection refused can indicate firewall drop.',
      },
    ],
    recommended_steps: [
      {
        priority: 1,
        action: 'Check database container health and active connections count.',
        target: 'postgres-container',
        step_type: 'immediate_check',
      },
    ],
    missing_evidence: ['Database server CPU metrics and connection pool logs.'],
    limitations: 'Analysis bounded strictly to received telemetry error payloads.',
  },
};

describe('InvestigationPanel Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders initial idle state with Investigate with AI button', () => {
    render(<InvestigationPanel issueId="issue-123" />);

    expect(screen.getByText('AI Incident Investigation Assistant')).toBeInTheDocument();
    expect(screen.getByText('Investigate with AI')).toBeInTheDocument();
    expect(screen.getByText(/Initiate Evidence-Grounded Root Cause Analysis/i)).toBeInTheDocument();
  });

  it('renders loading state and disables button during investigation', async () => {
    // Return a promise that stays pending
    let resolvePromise: (val: InvestigationReportResponse) => void;
    const pendingPromise = new Promise<InvestigationReportResponse>((resolve) => {
      resolvePromise = resolve;
    });

    vi.spyOn(issuesApi, 'investigateIssue').mockReturnValue(pendingPromise);

    render(<InvestigationPanel issueId="issue-123" />);
    const button = screen.getByText('Investigate with AI');
    fireEvent.click(button);

    // Should transition to loading state
    expect(screen.getByText('Analyzing Evidence...')).toBeInTheDocument();
    expect(screen.getByText('Synthesizing Incident Evidence')).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeDisabled();

    // Resolve promise
    resolvePromise!(mockSuccessReport);
    await waitFor(() => {
      expect(screen.getByText('Rerun Investigation')).toBeInTheDocument();
    });
  });

  it('prevents accidental duplicate clicks while request is in flight', () => {
    const spy = vi.spyOn(issuesApi, 'investigateIssue').mockReturnValue(new Promise(() => {}));

    render(<InvestigationPanel issueId="issue-123" />);
    const button = screen.getByText('Investigate with AI');

    fireEvent.click(button);
    fireEvent.click(button);
    fireEvent.click(button);

    expect(spy).toHaveBeenCalledTimes(1);
  });

  it('renders successful investigation report with all sections, hypotheses, and evidence chips', async () => {
    vi.spyOn(issuesApi, 'investigateIssue').mockResolvedValue(mockSuccessReport);

    render(<InvestigationPanel issueId="issue-123" />);
    const button = screen.getByText('Investigate with AI');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText('A. Executive Summary')).toBeInTheDocument();
    });

    // Check Executive summary
    expect(screen.getByText('Database connection failure pool timeout.')).toBeInTheDocument();
    expect(screen.getByText('/api/v1/checkout/pay')).toBeInTheDocument();

    // Check Observed Facts
    expect(screen.getByText(/B. Observed Facts Directly Supported by Telemetry/i)).toBeInTheDocument();
    expect(screen.getAllByText('EV-1').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('EV-2').length).toBeGreaterThanOrEqual(1);


    // Check Ranked Hypotheses and Confidence badge
    expect(screen.getByText('PostgreSQL Server Unreachable or Saturated')).toBeInTheDocument();
    expect(screen.getByText('High Confidence')).toBeInTheDocument();
    expect(screen.getByText('Medium Confidence')).toBeInTheDocument();

    // Check Debugging Steps
    expect(screen.getByText(/Check database container health and active connections count./i)).toBeInTheDocument();

    // Check Missing Evidence and Limitations
    expect(screen.getByText(/Database server CPU metrics and connection pool logs./i)).toBeInTheDocument();
    expect(screen.getByText(/Analysis bounded strictly to received telemetry error payloads./i)).toBeInTheDocument();
  });

  it('renders not_configured state with warning and fallback report when AI_API_KEY is missing', async () => {
    const notConfiguredResponse: InvestigationReportResponse = {
      ...mockSuccessReport,
      status: 'not_configured',
      is_ai_generated: false,
      warnings: ['AI_API_KEY is not configured.'],
    };

    vi.spyOn(issuesApi, 'investigateIssue').mockResolvedValue(notConfiguredResponse);

    render(<InvestigationPanel issueId="issue-123" />);
    fireEvent.click(screen.getByText('Investigate with AI'));

    await waitFor(() => {
      expect(
        screen.getByText(/AI Provider Not Configured \(AI_API_KEY Missing\)/i)
      ).toBeInTheDocument();
    });

    // Fallback report is rendered
    expect(screen.getByText('Deterministic Analysis')).toBeInTheDocument();
    expect(screen.getByText('Database connection failure pool timeout.')).toBeInTheDocument();
  });

  it('renders authentication error (401) with Configure API Key action', async () => {
    const error401 = new ApiError(401, 'Unauthorized', { detail: 'API key required' }, '/api/v1/issues');
    vi.spyOn(issuesApi, 'investigateIssue').mockRejectedValue(error401);

    const keyModalMock = vi.fn();
    render(<InvestigationPanel issueId="issue-123" onOpenKeyModal={keyModalMock} />);
    fireEvent.click(screen.getByText('Investigate with AI'));

    await waitFor(() => {
      expect(
        screen.getByText(/Project API key is missing or unauthorized/i)
      ).toBeInTheDocument();
    });

    const configBtn = screen.getByText('Configure API Key');
    fireEvent.click(configBtn);
    expect(keyModalMock).toHaveBeenCalledTimes(1);
  });

  it('renders retry button on provider failure and does not fabricate success report', async () => {
    vi.spyOn(issuesApi, 'investigateIssue').mockRejectedValue(new Error('Provider network timeout'));

    render(<InvestigationPanel issueId="issue-123" />);
    fireEvent.click(screen.getByText('Investigate with AI'));

    await waitFor(() => {
      expect(screen.getByText('Investigation Error')).toBeInTheDocument();
      expect(screen.getByText('Provider network timeout')).toBeInTheDocument();
    });

    expect(screen.getByText('Retry Investigation')).toBeInTheDocument();
    expect(screen.queryByText('A. Executive Summary')).not.toBeInTheDocument();
  });
});

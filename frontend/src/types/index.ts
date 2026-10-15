/**
 * TraceNest Common TypeScript Interfaces & Types
 * Strictly aligned with FastAPI Pydantic schemas.
 */

export type SeverityLevel = 'info' | 'warning' | 'error' | 'critical';
export type IssueStatus = 'unresolved' | 'investigating' | 'resolved' | 'ignored';

export interface BasicHealthResponse {
  status: string;
  service: string;
  timestamp: string;
}

export interface ApiHealthResponse {
  status: string;
  app_name: string;
  version: string;
  environment: string;
  api_version: string;
  database_connected: boolean;
  timestamp: string;
}

export interface SystemStatusState {
  backendReachable: boolean;
  v1ApiReachable: boolean;
  data: ApiHealthResponse | null;
  error?: string;
  latencyMs?: number;
}

export interface ProjectRead {
  id: string;
  name: string;
  created_at: string;
}

export interface ProjectResponse {
  id: string;
  name: string;
  api_key: string;
  created_at: string;
}

export interface IssueGroupRead {
  id: string;
  project_id: string;
  fingerprint: string;
  title: string;
  current_severity: SeverityLevel;
  status: IssueStatus;
  occurrence_count: number;
  first_seen: string;
  last_seen: string;
  created_at: string;
  updated_at: string;
}

export interface TelemetryEventRead {
  id: string;
  project_id: string;
  issue_group_id: string | null;
  fingerprint: string | null;
  event_type: string;
  severity: SeverityLevel;
  message: string;
  stack_trace: string | null;
  endpoint: string | null;
  http_status: number | null;
  duration_ms: number | null;
  metadata_json: Record<string, unknown> | null;
  timestamp: string;
  received_at: string;
}

export interface IssueListResponse {
  items: IssueGroupRead[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface IssueDetailResponse {
  issue: IssueGroupRead;
  recent_events: TelemetryEventRead[];
}

export interface IssueStatusUpdate {
  status: IssueStatus;
}

export interface IssueListParams {
  status?: IssueStatus | '';
  severity?: SeverityLevel | '';
  search?: string;
  page?: number;
  per_page?: number;
}

export interface DashboardMetrics {
  totalIssues: number;
  unresolvedIssues: number;
  criticalIssues: number;
  totalOccurrences: number;
  severityCounts: Record<SeverityLevel, number>;
  statusCounts: Record<IssueStatus, number>;
  timelineBuckets: { time: string; count: number }[];
  durationPoints: { time: string; endpoint: string; durationMs: number }[];
}

export type ConfidenceLevel = 'low' | 'medium' | 'high';
export type InvestigationStatus = 'idle' | 'loading' | 'success' | 'not_configured' | 'insufficient_evidence' | 'error';
export type AnalysisDepth = 'quick' | 'standard' | 'deep';
export type StepType = 'immediate_check' | 'inspect_frame' | 'collect_logs' | 'reproduction' | 'diagnostic_query';

export interface ExecutiveSummary {
  summary: string;
  affected_component: string | null;
  evidence_synthesis: string;
  certainty_assessment: string;
}

export interface ObservedFact {
  fact: string;
  evidence_reference: string | null;
  category: string;
}

export interface LikelyCause {
  rank: number;
  title: string;
  explanation: string;
  confidence: ConfidenceLevel;
  supporting_evidence: string[];
  missing_or_contradictory_evidence: string | null;
  plausibility_rationale: string;
}

export interface DebuggingStep {
  priority: number;
  action: string;
  target: string | null;
  step_type: StepType;
}

export interface InvestigationReport {
  executive_summary: ExecutiveSummary;
  observed_facts: ObservedFact[];
  likely_causes: LikelyCause[];
  recommended_steps: DebuggingStep[];
  missing_evidence: string[];
  limitations: string;
}

export interface InvestigationReportResponse {
  status: 'success' | 'not_configured' | 'insufficient_evidence' | 'error';
  issue_id: string;
  project_id: string;
  generated_at: string;
  provider: string;
  model: string;
  is_ai_generated: boolean;
  report: InvestigationReport | null;
  warnings: string[];
  error_detail: string | null;
}

export interface InvestigationRequest {
  analysis_depth?: AnalysisDepth;
}


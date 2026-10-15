/**
 * TraceNest Centralized API Client
 *
 * All frontend communication with the backend passes through this client.
 * Individual components must not invoke fetch directly.
 */

import {
  IssueListParams,
  IssueListResponse,
  IssueDetailResponse,
  IssueGroupRead,
  IssueStatus,
  ProjectResponse,
  InvestigationReportResponse,
  AnalysisDepth,
} from '@/types';


export interface RequestOptions extends Omit<RequestInit, 'body'> {
  params?: Record<string, string | number | boolean | undefined>;
  body?: unknown;
  timeoutMs?: number;
  apiKey?: string;
}

export class ApiError extends Error {
  public status: number;
  public statusText: string;
  public data: unknown;
  public url: string;

  constructor(status: number, statusText: string, data: unknown, url: string) {
    const detail =
      typeof data === 'object' && data !== null && 'detail' in data
        ? (data as { detail: string }).detail
        : typeof data === 'string'
        ? data
        : '';
    const message = detail
      ? `API Error ${status} (${statusText}): ${detail}`
      : `API Error ${status} (${statusText}) at ${url}`;

    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
    this.data = data;
    this.url = url;
  }

  public isUnauthorized(): boolean {
    return this.status === 401;
  }

  public isNotFound(): boolean {
    return this.status === 404;
  }
}

export class ApiClient {
  private baseUrl: string;
  private defaultTimeoutMs: number;
  private apiKey: string | null = null;

  constructor(baseUrl?: string, defaultTimeoutMs: number = 10000) {
    // Read from environment variable with fallback
    this.baseUrl = (
      baseUrl ||
      process.env.NEXT_PUBLIC_API_BASE_URL ||
      'http://127.0.0.1:8000'
    ).replace(/\/$/, '');
    this.defaultTimeoutMs = defaultTimeoutMs;

    // In browser, initialize from localStorage or env variable if present
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('tracenest_api_key');
      this.apiKey = stored || process.env.NEXT_PUBLIC_PROJECT_API_KEY || null;
    } else {
      this.apiKey = process.env.NEXT_PUBLIC_PROJECT_API_KEY || null;
    }
  }

  public getBaseUrl(): string {
    return this.baseUrl;
  }

  public setApiKey(key: string | null): void {
    this.apiKey = key ? key.trim() : null;
    if (typeof window !== 'undefined') {
      if (this.apiKey) {
        localStorage.setItem('tracenest_api_key', this.apiKey);
      } else {
        localStorage.removeItem('tracenest_api_key');
      }
    }
  }

  public getApiKey(): string | null {
    if (!this.apiKey && typeof window !== 'undefined') {
      this.apiKey = localStorage.getItem('tracenest_api_key') || null;
    }
    return this.apiKey;
  }

  /**
   * Core request dispatcher with timeout, parameter serialization, error wrapping,
   * and automatic API key injection.
   */
  public async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { params, body, headers, timeoutMs = this.defaultTimeoutMs, apiKey, ...fetchOptions } = options;

    // Ensure endpoint begins with a forward slash
    const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    let url = `${this.baseUrl}${normalizedEndpoint}`;

    // Append query parameters if provided
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          searchParams.append(key, String(value));
        }
      });
      const queryString = searchParams.toString();
      if (queryString) {
        url += `?${queryString}`;
      }
    }

    // Set up request timeout via AbortController
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    const effectiveApiKey = apiKey || this.getApiKey();

    const mergedHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...((headers as Record<string, string>) || {}),
    };

    if (effectiveApiKey && !mergedHeaders['X-API-Key'] && !mergedHeaders['Authorization']) {
      mergedHeaders['X-API-Key'] = effectiveApiKey;
    }

    try {
      const response = await fetch(url, {
        ...fetchOptions,
        headers: mergedHeaders,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Handle non-2xx status codes
      if (!response.ok) {
        let errorData: unknown;
        try {
          errorData = await response.json();
        } catch {
          errorData = await response.text();
        }
        throw new ApiError(response.status, response.statusText, errorData, url);
      }

      // Check if response is JSON
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return (await response.json()) as T;
      }
      return (await response.text()) as unknown as T;
    } catch (error: unknown) {
      clearTimeout(timeoutId);

      if (error instanceof ApiError) {
        throw error;
      }

      if (error instanceof Error && error.name === 'AbortError') {
        throw new ApiError(
          408,
          'Request Timeout',
          { detail: `Request to ${url} timed out after ${timeoutMs}ms` },
          url
        );
      }

      const message = error instanceof Error ? error.message : 'Unknown network failure';
      throw new ApiError(0, 'Network Error', { detail: message }, url);
    }
  }

  public get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  public post<T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'POST', body });
  }

  public patch<T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'PATCH', body });
  }

  public delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }

  // --- Domain Methods ---

  public async registerProject(name: string): Promise<ProjectResponse> {
    return this.post<ProjectResponse>('/api/v1/projects', { name });
  }

  public async listIssues(params?: IssueListParams): Promise<IssueListResponse> {
    return this.get<IssueListResponse>('/api/v1/issues', {
      params: params as Record<string, string | number | boolean | undefined>,
    });
  }

  public async getIssue(issueId: string): Promise<IssueDetailResponse> {
    return this.get<IssueDetailResponse>(`/api/v1/issues/${issueId}`);
  }

  public async updateIssueStatus(issueId: string, status: IssueStatus): Promise<IssueGroupRead> {
    return this.patch<IssueGroupRead>(`/api/v1/issues/${issueId}`, { status });
  }

  public async investigateIssue(
    issueId: string,
    depth: AnalysisDepth = 'standard'
  ): Promise<InvestigationReportResponse> {
    return this.post<InvestigationReportResponse>(`/api/v1/issues/${issueId}/investigate`, {
      analysis_depth: depth,
    });
  }
}


// Global singleton client instance
export const apiClient = new ApiClient();

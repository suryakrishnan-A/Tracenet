/**
 * TraceNest Health Check API Service
 *
 * Exposes strongly-typed methods consuming backend health endpoints
 * via the centralized apiClient.
 */

import { apiClient, ApiError } from './client';
import { BasicHealthResponse, ApiHealthResponse, SystemStatusState } from '@/types';

/**
 * Fetch root health check status (/health).
 */
export async function getRootHealth(): Promise<BasicHealthResponse> {
  return apiClient.get<BasicHealthResponse>('/health');
}

/**
 * Fetch versioned API v1 health status (/api/v1/health).
 */
export async function getApiV1Health(): Promise<ApiHealthResponse> {
  return apiClient.get<ApiHealthResponse>('/api/v1/health');
}

/**
 * Comprehensive health status aggregator measuring network latency and connectivity.
 */
export async function checkSystemHealth(): Promise<SystemStatusState> {
  const startTime = Date.now();
  try {
    const v1Data = await getApiV1Health();
    const latency = Date.now() - startTime;
    return {
      backendReachable: true,
      v1ApiReachable: true,
      data: v1Data,
      latencyMs: latency,
    };
  } catch (error: unknown) {
    const latency = Date.now() - startTime;
    let message = 'Unable to connect to backend server';
    if (error instanceof ApiError) {
      message = `${error.statusText} (${error.status}): ${JSON.stringify(error.data)}`;
    } else if (error instanceof Error) {
      message = error.message;
    }
    return {
      backendReachable: false,
      v1ApiReachable: false,
      data: null,
      error: message,
      latencyMs: latency,
    };
  }
}

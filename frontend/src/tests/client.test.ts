import { describe, it, expect, beforeEach } from 'vitest';
import { ApiClient, ApiError } from '@/lib/api/client';

describe('ApiClient & ApiError', () => {
  let client: ApiClient;

  beforeEach(() => {
    localStorage.clear();
    client = new ApiClient('http://test-api:8000');
  });

  it('manages API key persistence properly', () => {
    expect(client.getApiKey()).toBeNull();

    client.setApiKey('tn_live_test12345');
    expect(client.getApiKey()).toBe('tn_live_test12345');
    expect(localStorage.getItem('tracenest_api_key')).toBe('tn_live_test12345');

    client.setApiKey(null);
    expect(client.getApiKey()).toBeNull();
    expect(localStorage.getItem('tracenest_api_key')).toBeNull();
  });

  it('correctly handles ApiError status codes and helper methods', () => {
    const error401 = new ApiError(401, 'Unauthorized', { detail: 'Invalid key' }, '/api/v1/issues');
    expect(error401.isUnauthorized()).toBe(true);
    expect(error401.isNotFound()).toBe(false);
    expect(error401.message).toContain('API Error 401');
    expect(error401.message).toContain('Invalid key');

    const error404 = new ApiError(404, 'Not Found', { detail: 'Issue not found' }, '/api/v1/issues/123');
    expect(error404.isUnauthorized()).toBe(false);
    expect(error404.isNotFound()).toBe(true);
  });
});

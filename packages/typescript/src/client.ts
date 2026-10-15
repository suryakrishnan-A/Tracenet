/**
 * TraceNest TypeScript & Node.js Telemetry Client.
 */

import {
  TraceNestOptions,
  CaptureOptions,
  CaptureEventOptions,
  DeliveryResult,
} from "./types";
import {
  TraceNestConfigError,
  TraceNestDeliveryError,
  TraceNestRateLimitError,
} from "./errors";
import { formatError, sanitizeMetadata } from "./serializer";

declare const process: { env?: Record<string, string | undefined> } | undefined;

export class TraceNest {
  private readonly apiKey: string;
  private readonly endpoint: string;
  private readonly timeoutMs: number;
  private readonly raiseOnDeliveryError: boolean;
  private readonly onDeliveryError?: (
    error: Error,
    payload: Record<string, unknown>
  ) => void;
  private readonly maxMetadataBytes: number;
  private readonly fetchClient: typeof fetch;

  constructor(options: TraceNestOptions = {}) {
    // Detect environment variable fallback if running in Node.js
    const envApiKey =
      typeof process !== "undefined" && process.env
        ? process.env.TRACENEST_API_KEY
        : undefined;
    const rawKey = options.apiKey || envApiKey;

    if (!rawKey || !rawKey.trim()) {
      throw new TraceNestConfigError(
        "TraceNest API key is required. Supply via 'apiKey' constructor option or set the 'TRACENEST_API_KEY' environment variable."
      );
    }
    this.apiKey = rawKey.trim();

    const envEndpoint =
      typeof process !== "undefined" && process.env
        ? process.env.TRACENEST_ENDPOINT
        : undefined;
    let endpoint = (options.endpoint || envEndpoint || "http://localhost:8000").trim();
    endpoint = endpoint.replace(/\/+$/, "");
    if (endpoint.endsWith("/api/v1")) {
      endpoint = endpoint.slice(0, -7);
    }
    this.endpoint = endpoint;

    this.timeoutMs = options.timeoutMs ?? 5000;
    this.raiseOnDeliveryError = options.raiseOnDeliveryError ?? false;
    this.onDeliveryError = options.onDeliveryError;
    this.maxMetadataBytes = options.maxMetadataBytes ?? 32768;

    // Use user-provided fetch or global fetch
    if (options.fetchClient) {
      this.fetchClient = options.fetchClient;
    } else if (typeof fetch !== "undefined") {
      this.fetchClient = fetch;
    } else {
      throw new TraceNestConfigError(
        "Global 'fetch' is not available in this runtime. Pass a custom 'fetchClient' to the TraceNest constructor."
      );
    }
  }

  /**
   * Capture and transmit an Error or thrown exception to TraceNest.
   *
   * The host application error is never suppressed or altered.
   */
  public async captureError(
    error: unknown,
    options: CaptureOptions = {}
  ): Promise<DeliveryResult> {
    const { message, stackTrace } = formatError(error);

    const payload: Record<string, unknown> = {
      event_type: "exception",
      severity: options.severity || "error",
      message,
      metadata: sanitizeMetadata(options.metadata, this.maxMetadataBytes),
      timestamp: new Date().toISOString(),
    };

    if (stackTrace) payload.stack_trace = stackTrace;
    if (options.endpoint) payload.endpoint = options.endpoint;
    if (options.httpStatus !== undefined) payload.http_status = options.httpStatus;
    if (options.durationMs !== undefined) payload.duration_ms = options.durationMs;

    return this.sendPayload(payload, options.requestId);
  }

  /**
   * Manually record an application warning, error, or operational event.
   */
  public async captureEvent(
    message: string,
    options: CaptureEventOptions = {}
  ): Promise<DeliveryResult> {
    const payload: Record<string, unknown> = {
      event_type: options.eventType || "error",
      severity: options.severity || "error",
      message: message.trim(),
      metadata: sanitizeMetadata(options.metadata, this.maxMetadataBytes),
      timestamp: new Date().toISOString(),
    };

    if (options.stackTrace) payload.stack_trace = options.stackTrace;
    if (options.endpoint) payload.endpoint = options.endpoint;
    if (options.httpStatus !== undefined) payload.http_status = options.httpStatus;
    if (options.durationMs !== undefined) payload.duration_ms = options.durationMs;

    return this.sendPayload(payload, options.requestId);
  }

  /**
   * Internal telemetry dispatcher over HTTP POST.
   */
  private async sendPayload(
    payload: Record<string, unknown>,
    requestId?: string
  ): Promise<DeliveryResult> {
    const url = `${this.endpoint}/api/v1/telemetry`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-API-Key": this.apiKey,
      "User-Agent": "@tracenest/sdk/0.1.0",
    };

    if (requestId) {
      headers["X-Request-ID"] = requestId;
    }

    // Set up request abort controller for timeout safety
    const controller = new AbortController();
    const timerId = setTimeout(() => controller.abort(), this.timeoutMs);

    let response: Response;
    try {
      response = await this.fetchClient(url, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
    } catch (err: unknown) {
      clearTimeout(timerId);
      const deliveryErr = new TraceNestDeliveryError(
        `Failed to reach TraceNest endpoint at '${this.endpoint}': ${
          err instanceof Error ? err.message : String(err)
        }`
      );
      return this.handleFailure(deliveryErr, payload);
    } finally {
      clearTimeout(timerId);
    }

    // Handle successful ingestion (201 Created)
    if (response.status === 201) {
      try {
        const data = (await response.json()) as {
          event_id?: string;
          project_id?: string;
          issue_id?: string;
          fingerprint?: string;
        };
        return {
          success: true,
          statusCode: 201,
          eventId: data.event_id,
          projectId: data.project_id,
          issueId: data.issue_id,
          fingerprint: data.fingerprint,
        };
      } catch {
        return { success: true, statusCode: 201 };
      }
    }

    // Handle Rate Limiting (429)
    if (response.status === 429) {
      const retryHeader = response.headers.get("Retry-After");
      const retryAfter = retryHeader && !isNaN(Number(retryHeader)) ? Number(retryHeader) : 1;
      const bodyText = await response.text().catch(() => "");
      const rateErr = new TraceNestRateLimitError(
        `TraceNest rate limit exceeded. Retry after ${retryAfter}s.`,
        retryAfter,
        bodyText
      );
      return this.handleFailure(rateErr, payload, 429, retryAfter);
    }

    // Handle other HTTP errors (401, 413, 500, etc.)
    const errorBody = await response.text().catch(() => "");
    const deliveryErr = new TraceNestDeliveryError(
      `TraceNest backend rejected telemetry with HTTP ${response.status}: ${errorBody}`,
      { statusCode: response.status, responseBody: errorBody }
    );
    return this.handleFailure(deliveryErr, payload, response.status);
  }

  private handleFailure(
    error: Error,
    payload: Record<string, unknown>,
    statusCode?: number,
    retryAfter?: number
  ): DeliveryResult {
    if (this.onDeliveryError) {
      try {
        this.onDeliveryError(error, payload);
      } catch (cbErr) {
        // Suppress callback failure to protect host application
        console.warn("[TraceNest] Error in onDeliveryError callback:", cbErr);
      }
    }

    if (this.raiseOnDeliveryError) {
      throw error;
    }

    return {
      success: false,
      statusCode,
      error: error.message,
      retryAfter,
    };
  }
}

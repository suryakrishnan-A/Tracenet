/**
 * TraceNest TypeScript SDK Type Definitions.
 */

export type SeverityLevel = "info" | "warning" | "error" | "critical";

export interface TraceNestOptions {
  /** Project-scoped API key. Defaults to process.env.TRACENEST_API_KEY */
  apiKey?: string;
  /** TraceNest backend endpoint URL. Defaults to process.env.TRACENEST_ENDPOINT or "http://localhost:8000" */
  endpoint?: string;
  /** Network request timeout in milliseconds. Default: 5000 */
  timeoutMs?: number;
  /** If true, telemetry delivery errors throw exceptions instead of returning a failure result. Default: false */
  raiseOnDeliveryError?: boolean;
  /** Optional diagnostic callback triggered whenever telemetry transmission fails. */
  onDeliveryError?: (error: Error, payload: Record<string, unknown>) => void;
  /** Maximum byte size allowed for JSON-serialized metadata before pruning. Default: 32768 (32 KB) */
  maxMetadataBytes?: number;
  /** Custom fetch implementation (useful for testing or specialized agent runtimes). */
  fetchClient?: typeof fetch;
}

export interface CaptureOptions {
  /** Associated HTTP endpoint (e.g. "/api/v1/orders/checkout") */
  endpoint?: string;
  /** Associated HTTP response status code */
  httpStatus?: number;
  /** Operation execution duration in milliseconds */
  durationMs?: number;
  /** Arbitrary structured contextual metadata */
  metadata?: Record<string, unknown>;
  /** Distributed tracing request ID (e.g. from X-Request-ID header) */
  requestId?: string;
  /** Severity classification. Default: "error" */
  severity?: SeverityLevel;
}

export interface CaptureEventOptions extends CaptureOptions {
  /** Event classification identifier. Default: "error" */
  eventType?: string;
  /** Optional explicit error stack trace */
  stackTrace?: string;
}

export interface DeliveryResult {
  /** True if the event was accepted by the TraceNest backend (HTTP 201) */
  success: boolean;
  /** HTTP response status code returned by the backend */
  statusCode?: number;
  /** Ingested telemetry event UUID */
  eventId?: string;
  /** Monitored project UUID */
  projectId?: string;
  /** Associated issue group UUID */
  issueId?: string;
  /** Computed deterministic SHA-256 fingerprint */
  fingerprint?: string;
  /** Error description if delivery failed */
  error?: string;
  /** If HTTP 429 was returned, recommended delay in seconds before retrying */
  retryAfter?: number;
}

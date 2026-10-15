import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  TraceNest,
  TraceNestConfigError,
  TraceNestDeliveryError,
  TraceNestRateLimitError,
} from "../src/index";

describe("TraceNest TypeScript SDK", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
    delete process.env.TRACENEST_API_KEY;
    delete process.env.TRACENEST_ENDPOINT;
  });

  it("throws TraceNestConfigError if no API key is provided", () => {
    expect(() => new TraceNest({ fetchClient: vi.fn() as any })).toThrowError(
      TraceNestConfigError
    );
  });

  it("reads API key and endpoint from process.env", () => {
    process.env.TRACENEST_API_KEY = "tn_live_env_ts_key";
    process.env.TRACENEST_ENDPOINT = "http://ingest.corp.internal:9000/api/v1/";

    const client = new TraceNest({ fetchClient: vi.fn() as any });
    expect((client as any).apiKey).toBe("tn_live_env_ts_key");
    expect((client as any).endpoint).toBe("http://ingest.corp.internal:9000");
  });

  it("captures an Error and transmits serialized payload via fetch", async () => {
    let capturedUrl = "";
    let capturedOptions: any = {};

    const mockFetch = vi.fn().mockImplementation(async (url: string, opts: any) => {
      capturedUrl = url;
      capturedOptions = opts;
      return new Response(
        JSON.stringify({
          status: "received",
          event_id: "33333333-3333-3333-3333-333333333333",
          project_id: "44444444-4444-4444-4444-444444444444",
          issue_id: "55555555-5555-5555-5555-555555555555",
          fingerprint: "ts_test_fingerprint_sha256",
        }),
        { status: 201, headers: { "Content-Type": "application/json" } }
      );
    });

    const client = new TraceNest({
      apiKey: "tn_live_test_key",
      endpoint: "http://localhost:8000",
      fetchClient: mockFetch as any,
    });

    const testError = new TypeError("Cannot read properties of undefined (reading 'items')");
    const result = await client.captureError(testError, {
      endpoint: "/api/v1/cart",
      httpStatus: 500,
      durationMs: 120.5,
      requestId: "req-ts-1234",
      metadata: { cartId: "cart_99" },
    });

    expect(result.success).toBe(true);
    expect(result.statusCode).toBe(201);
    expect(result.eventId).toBe("33333333-3333-3333-3333-333333333333");
    expect(result.fingerprint).toBe("ts_test_fingerprint_sha256");

    expect(capturedUrl).toBe("http://localhost:8000/api/v1/telemetry");
    expect(capturedOptions.headers["X-API-Key"]).toBe("tn_live_test_key");
    expect(capturedOptions.headers["X-Request-ID"]).toBe("req-ts-1234");

    const sentBody = JSON.parse(capturedOptions.body);
    expect(sentBody.event_type).toBe("exception");
    expect(sentBody.message).toContain("TypeError: Cannot read properties of undefined");
    expect(sentBody.endpoint).toBe("/api/v1/cart");
    expect(sentBody.http_status).toBe(500);
    expect(sentBody.duration_ms).toBe(120.5);
    expect(sentBody.metadata.cartId).toBe("cart_99");
  });

  it("redacts sensitive keys in metadata", async () => {
    let capturedOptions: any = {};
    const mockFetch = vi.fn().mockImplementation(async (_url: string, opts: any) => {
      capturedOptions = opts;
      return new Response(JSON.stringify({ status: "received" }), { status: 201 });
    });

    const client = new TraceNest({
      apiKey: "tn_live_key",
      fetchClient: mockFetch as any,
    });

    await client.captureError(new Error("Test"), {
      metadata: {
        userId: "u123",
        userPassword: "plaintext_secret_password",
        api_key: "tn_live_leaked_key",
        authToken: "bearer_xyz",
      },
    });

    const body = JSON.parse(capturedOptions.body);
    expect(body.metadata.userId).toBe("u123");
    expect(body.metadata.userPassword).toBe("[REDACTED]");
    expect(body.metadata.api_key).toBe("[REDACTED]");
    expect(body.metadata.authToken).toBe("[REDACTED]");
  });

  it("handles HTTP 401 silently without crashing by default", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      new Response("Invalid or inactive API key", { status: 401 })
    );

    const client = new TraceNest({
      apiKey: "tn_live_bad_key",
      fetchClient: mockFetch as any,
    });

    const result = await client.captureError(new Error("Runtime crash"));
    expect(result.success).toBe(false);
    expect(result.statusCode).toBe(401);
    expect(result.error).toContain("rejected telemetry with HTTP 401");
  });

  it("throws TraceNestDeliveryError on 401 when raiseOnDeliveryError is enabled", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      new Response("Invalid or inactive API key", { status: 401 })
    );

    const client = new TraceNest({
      apiKey: "tn_live_bad_key",
      raiseOnDeliveryError: true,
      fetchClient: mockFetch as any,
    });

    await expect(client.captureError(new Error("Boom"))).rejects.toThrowError(
      TraceNestDeliveryError
    );
  });

  it("handles HTTP 429 and maps Retry-After header", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      new Response("Rate limit exceeded", {
        status: 429,
        headers: { "Retry-After": "5" },
      })
    );

    const client = new TraceNest({
      apiKey: "tn_live_key",
      fetchClient: mockFetch as any,
    });

    const result = await client.captureEvent("High volume event");
    expect(result.success).toBe(false);
    expect(result.statusCode).toBe(429);
    expect(result.retryAfter).toBe(5);
  });

  it("catches network connection errors safely and reports to onDeliveryError callback", async () => {
    const deliveryFailures: any[] = [];
    const mockFetch = vi.fn().mockRejectedValue(new Error("ECONNREFUSED 127.0.0.1:8000"));

    const client = new TraceNest({
      apiKey: "tn_live_key",
      onDeliveryError: (err, payload) => {
        deliveryFailures.push({ err, payload });
      },
      fetchClient: mockFetch as any,
    });

    const result = await client.captureError(new Error("Host app error"));
    expect(result.success).toBe(false);
    expect(result.error).toContain("ECONNREFUSED");
    expect(deliveryFailures.length).toBe(1);
    expect(deliveryFailures[0].err.message).toContain("ECONNREFUSED");
  });
});

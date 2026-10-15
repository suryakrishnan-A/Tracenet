# TraceNest TypeScript / Node.js SDK (`@tracenest/sdk`)

Official TypeScript and Node.js telemetry client for the **TraceNest** AI-Powered Observability and Incident Investigation Platform.

---

> [!CAUTION]
> **Server-Side Security Warning**:
> TraceNest credentials are **server-side only**.
> - **Scoped Ingestion Keys (`tn_ingest_...`)**: Required for the SDK. These keys are strictly scoped to `POST /api/v1/telemetry` and cannot access issue details or project settings.
> - **Management Keys (`tn_mgmt_...`)**: Reserved for administrators and the TraceNest dashboard.
> **NEVER** expose any TraceNest key in client-side browser bundles, public frontend environment variables (`NEXT_PUBLIC_*`), or React components. This SDK is strictly intended for Node.js backends and serverless edge runtimes.

---

## Installation

```bash
npm install @tracenest/sdk
```

---

## Quickstart

### 1. Basic Error Capture

```typescript
import { TraceNest } from "@tracenest/sdk";

// Automatically detects process.env.TRACENEST_API_KEY and TRACENEST_ENDPOINT
const tracenest = new TraceNest({
  apiKey: process.env.TRACENEST_API_KEY,
  endpoint: "http://localhost:8000",
});

try:
  await processPayment(orderId);
} catch (error) {
  // Transmits exception, backtrace, and metadata to TraceNest
  const result = await tracenest.captureError(error, {
    endpoint: "/api/v1/orders/checkout",
    httpStatus: 502,
    metadata: { orderId, provider: "stripe" },
  });

  if (result.success) {
    console.log(`Reported error to TraceNest: event=${result.eventId} issue=${result.issueId}`);
  }
}
```

### 2. Express.js Error Middleware Integration

```typescript
import express, { Request, Response, NextFunction } from "express";
import { TraceNest } from "@tracenest/sdk";

const app = express();
const tracenest = new TraceNest();

// Error-handling middleware
app.use(async (err: Error, req: Request, res: Response, next: NextFunction) => {
  // Safely forward error to TraceNest
  await tracenest.captureError(err, {
    endpoint: req.originalUrl,
    requestId: req.headers["x-request-id"] as string,
    metadata: {
      method: req.method,
      ip: req.ip,
    },
  });

  // Return standard sanitized error response to client
  res.status(500).json({ error: "Internal Server Error" });
});
```

---

## Configuration Options

| Option | Environment Variable | Default | Description |
| :--- | :--- | :--- | :--- |
| `apiKey` | `TRACENEST_API_KEY` | *Required* | Project-scoped ingestion API key |
| `endpoint` | `TRACENEST_ENDPOINT` | `http://localhost:8000` | TraceNest backend API URL |
| `timeoutMs` | — | `5000` | Network request timeout in milliseconds |
| `raiseOnDeliveryError` | — | `false` | Whether telemetry failures throw exceptions |
| `onDeliveryError` | — | `undefined` | Callback `(error, payload) => void` on failure |
| `maxMetadataBytes` | — | `32768` (32 KB) | Upper bound for metadata JSON |
| `fetchClient` | — | Global `fetch` | Custom fetch implementation for mocking |

---

## Error Handling Philosophy

1. **Host Application Resilience**: Telemetry transmission failures (e.g. backend offline or network timeouts) will **never** crash your production service by default.
2. **Context Redaction**: Sensitive keys (`password`, `token`, `secret`, `authorization`, `cookie`) are automatically sanitized to `[REDACTED]`.
3. **Application Exception Isolation**: The application's original error is completely untouched.

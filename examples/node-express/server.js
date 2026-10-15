/**
 * TraceNest Integration Example: Node.js Express Application.
 *
 * Demonstrates:
 * - SDK initialization from environment variables.
 * - Centralized Express error-handling middleware.
 * - Distributed request ID tracing.
 * - Non-blocking telemetry reporting that never masks application errors.
 */

const express = require("express");
const crypto = require("crypto");
// Require compiled local SDK or published package
const { TraceNest } = require("../../packages/typescript/dist/index.js");

const app = express();
app.use(express.json());

// Initialize TraceNest SDK
const tracenest = new TraceNest({
  apiKey: process.env.TRACENEST_API_KEY || "tn_ingest_placeholder_key",
  endpoint: process.env.TRACENEST_ENDPOINT || "http://localhost:8000",
  raiseOnDeliveryError: false,
});

// Middleware: attach request ID and start timer
app.use((req, res, next) => {
  const reqId = req.headers["x-request-id"] || crypto.randomUUID();
  req.requestId = reqId;
  req.startTime = process.hrtime();
  res.setHeader("X-Request-ID", reqId);
  next();
});

// 1. Healthy Endpoint
app.get("/api/inventory", (req, res) => {
  res.json({
    warehouse: "us-east-1",
    available_skus: ["SKU-100", "SKU-200", "SKU-300"],
  });
});

// 2. Deliberately Failing Endpoint
app.post("/api/inventory/reserve", (req, res, next) => {
  const { sku, quantity } = req.body || {};
  if (!sku || sku === "SKU-ERROR") {
    const error = new Error(
      `InventoryAllocationError: Stock level zero for requested item SKU-ERROR in facility dc-04`
    );
    error.name = "InventoryAllocationError";
    return next(error);
  }

  res.json({ status: "reserved", sku, quantity: quantity || 1 });
});

// 3. Centralized Express Error-Handling Middleware
app.use(async (err, req, res, next) => {
  const diff = process.hrtime(req.startTime);
  const durationMs = Math.round((diff[0] * 1e3 + diff[1] * 1e-6) * 100) / 100;

  // Capture error and send telemetry to TraceNest
  const delivery = await tracenest.captureError(err, {
    endpoint: req.originalUrl || req.url,
    httpStatus: 500,
    durationMs,
    requestId: req.requestId,
    metadata: {
      method: req.method,
      ip: req.ip,
      body: req.body,
    },
  });

  // Return standard sanitized error response to the client
  res.status(500).json({
    error: err.name || "InternalServerError",
    message: "An internal server error occurred while processing inventory reservation.",
    request_id: req.requestId,
    tracenest_event_id: delivery.success ? delivery.eventId : null,
  });
});

const PORT = process.env.PORT || 8081;
app.listen(PORT, () => {
  console.log(`Inventory Service running on http://127.0.0.1:${PORT}`);
});

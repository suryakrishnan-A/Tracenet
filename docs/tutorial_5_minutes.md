# Connect Your First Application to TraceNest in 5 Minutes

This guide walks you through connecting a Python or Node.js service to **TraceNest** to capture real errors, group recurring incidents, and generate AI-assisted root-cause investigations.

---

## Prerequisites
- A running TraceNest instance (local or Docker Compose):
  - Backend: `http://localhost:8000`
  - Frontend Dashboard: `http://localhost:3000`

---

## Step 1: Obtain a Project Ingestion Key (1 Minute)

1. Open the TraceNest Dashboard in your browser: [http://localhost:3000](http://localhost:3000).
2. In the top navigation bar, click **"Project Settings"** (or the Key icon).
3. Click **"Register New Project"**, enter your service name (e.g. `Payment Service`), and click **Create**.
4. TraceNest generates **two distinct, scoped credentials**:
   - **Management Key (`tn_mgmt_...`)**: Reserved for dashboard access, project settings, resolving incidents, and AI investigations.
   - **Scoped Ingestion Key (`tn_ingest_...`)**: Restricted **strictly** to telemetry event delivery. This is the key you install in your applications and microservices.
5. Copy the raw **Ingestion Key**:
   ```
   tn_ingest_a1b2c3d4e5f67890123456789abcdef...
   ```
   *(TraceNest stores high-entropy SHA-256 hashes in PostgreSQL and never reveals raw secrets after creation).*

---

## Step 2: Install the TraceNest SDK (1 Minute)

Choose the SDK for your application stack:

### Python Application
```bash
pip install tracenest-sdk
```

### Node.js / TypeScript Application
```bash
npm install @tracenest/sdk
```

---

## Step 3: Add SDK to Your Application (2 Minutes)

### Option A: Python (FastAPI / Flask / Scripts)

Set your environment variables:
```bash
export TRACENEST_API_KEY="tn_ingest_your_copied_ingestion_key_here"
export TRACENEST_ENDPOINT="http://localhost:8000"
```

Add the client to your application code:
```python
from tracenest import TraceNest

# Automatically uses TRACENEST_API_KEY and TRACENEST_ENDPOINT
client = TraceNest()
```

---

### Option B: Node.js (Express / Fastify / Next.js API Routes)

Set your environment variables:
```bash
export TRACENEST_API_KEY="tn_ingest_your_copied_ingestion_key_here"
export TRACENEST_ENDPOINT="http://localhost:8000"
```

Add the client to your server code:
```javascript
const { TraceNest } = require("@tracenest/sdk");

const tracenest = new TraceNest();

try {
  // Your business logic
  processOrder();
} catch (error) {
  // 1. Capture and send evidence to TraceNest
  await tracenest.captureError(error, {
    endpoint: "/api/orders",
    httpStatus: 500,
    metadata: { orderId: "ord_9981" },
  });
  // 2. Return clean user-facing error response
  res.status(500).json({ error: "Internal Server Error" });
}
```

---

## Step 4: Trigger an Error & Verify in TraceNest (1 Minute)

1. Run your application and trigger the code path with the error.
2. In the TraceNest Dashboard ([http://localhost:3000](http://localhost:3000)):
   - Go to the **"Issues"** tab.
   - You will see a newly grouped incident matching your exception with `occurrence_count = 1`.
3. Trigger the same error again:
   - Notice the issue does **not** create duplicate spam; the existing issue's occurrence count increments to `2` and the event is added to the chronological timeline.
4. Click on the issue title to open the **Issue Detail Page**:
   - Inspect the normalized stack trace and metadata.
   - Click **"Investigate with AI"** to generate an evidence-grounded root-cause diagnosis with ranked hypotheses and debugging recommendations!

---

## Next Steps & Best Practices

1. **Least-Privilege Secret Separation**: Always provide `tn_ingest_...` scoped keys to applications and services. Keep `tn_mgmt_...` management credentials strictly for authorized operators and the dashboard.
2. **Instant Ingestion Key Revocation / Rotation**: If an application environment is decommissioned or a scoped ingestion key is compromised, revoke or rotate it immediately via `DELETE /api/v1/projects/ingestion-keys/{key_id}` or `POST /api/v1/projects/ingestion-keys/{key_id}/rotate` without breaking other keys or project administration.
3. **Server-Side Only**: Never include any TraceNest keys in client-side frontend code or public browser bundles.

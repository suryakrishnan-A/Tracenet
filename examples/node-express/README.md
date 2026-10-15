# TraceNest Node.js Express Integration Example

This example demonstrates integrating **TraceNest** into a Node.js Express service to automatically capture application errors, measure execution latency, track distributed `X-Request-ID`, and forward telemetry to the TraceNest backend.

---

## 1. Setup

Ensure the TraceNest backend is running on `http://127.0.0.1:8000`.

Install dependencies:
```bash
npm install express
```

---

## 2. Configuration

Set your project's scoped ingestion API key (starts with `tn_ingest_`):

```bash
# Windows PowerShell
$env:TRACENEST_API_KEY = "tn_ingest_your_scoped_ingestion_key_here"
$env:TRACENEST_ENDPOINT = "http://127.0.0.1:8000"

# Linux / macOS
export TRACENEST_API_KEY="tn_ingest_your_scoped_ingestion_key_here"
export TRACENEST_ENDPOINT="http://127.0.0.1:8000"
```

---

## 3. Run the Application

```bash
node server.js
```

---

## 4. Test Endpoints

### Successful Endpoint
```bash
curl http://127.0.0.1:8081/api/inventory
```

### Deliberately Failing Reservation Endpoint
```bash
curl -X POST http://127.0.0.1:8081/api/inventory/reserve \
  -H "Content-Type: application/json" \
  -d '{"sku": "SKU-ERROR", "quantity": 5}'
```

Response:
```json
{
  "error": "InventoryAllocationError",
  "message": "An internal server error occurred while processing inventory reservation.",
  "request_id": "764f691b-...",
  "tracenest_event_id": "c88f..."
}
```

Now open the **TraceNest Dashboard** at `http://localhost:3000` to view the grouped issue and explore the chronological incident timeline!

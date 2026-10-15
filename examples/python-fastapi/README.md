# TraceNest Python FastAPI Integration Example

This example demonstrates integrating **TraceNest** into a FastAPI service to automatically capture unhandled exceptions, measure execution duration, propagate `X-Request-ID`, and forward telemetry to the TraceNest backend.

---

## 1. Setup

Ensure the TraceNest backend is running on `http://127.0.0.1:8000`.

Install requirements:
```bash
pip install -r requirements.txt
```
*(Or install the local SDK: `pip install -e ../../packages/python`)*

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
uvicorn app:app --reload --port 8080
```

---

## 4. Test Endpoints

### Successful Endpoint
```bash
curl http://127.0.0.1:8080/orders
```

### Deliberately Failing Checkout Endpoint
```bash
curl -X POST http://127.0.0.1:8080/orders/checkout \
  -H "Content-Type: application/json" \
  -d '{"item_id": "item_99", "payment_method": "card"}'
```

Response:
```json
{
  "error": "InternalServerError",
  "message": "A server error occurred while processing your request.",
  "request_id": "764f691b-...",
  "tracenest_event_id": "a98e..."
}
```

Now open the **TraceNest Dashboard** at `http://localhost:3000` to inspect the newly grouped issue and run an AI investigation report!

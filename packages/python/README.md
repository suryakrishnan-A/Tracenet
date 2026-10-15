# TraceNest Python SDK (`tracenest-sdk`)

Official Python telemetry and error-tracking client for the **TraceNest** AI-Powered Observability and Incident Investigation Platform.

---

> [!TIP]
> **Scoped Ingestion Credentials (`tn_ingest_...`)**:
> TraceNest enforces least-privilege credential separation. When instrumenting your application, configure your scoped ingestion key (`tn_ingest_...`). Ingestion keys are strictly restricted to sending telemetry events (`POST /api/v1/telemetry`) and cannot read issues or perform administrative actions.

---

## Installation

```bash
pip install tracenest-sdk
```

*(Or install locally in development mode: `pip install -e packages/python`)*

---

## Quickstart

### 1. Basic Exception Capture

```python
from tracenest import TraceNest

# Automatically falls back to TRACENEST_API_KEY and TRACENEST_ENDPOINT
client = TraceNest(
    api_key="tn_ingest_your_scoped_key",
    endpoint="http://localhost:8000",
)

try:
    1 / 0
except ZeroDivisionError as err:
    # Captures exception, extracts formatted traceback, and sends to TraceNest
    result = client.capture_exception(
        err,
        endpoint="/api/v1/calculate",
        metadata={"user_id": "usr_123", "operation": "division"},
    )
    if result.success:
        print(f"Captured error! TraceNest Event ID: {result.event_id}")
```

### 2. Context Manager Resource Management

```python
with TraceNest(api_key="tn_ingest_key") as client:
    try:
        process_order()
    except Exception as exc:
        client.capture_exception(exc, endpoint="/orders")
        raise  # Monitored app exception is completely preserved
```

### 3. Asynchronous Framework Support (FastAPI / Starlette)

```python
from tracenest import AsyncTraceNest

async_client = AsyncTraceNest(api_key="tn_ingest_key")

@app.exception_handler(Exception)
async def custom_exception_handler(request: Request, exc: Exception):
    await async_client.capture_exception(
        exc,
        endpoint=request.url.path,
        request_id=request.headers.get("x-request-id"),
        metadata={"client_ip": request.client.host if request.client else None},
    )
    return JSONResponse(status_code=500, content={"detail": "Internal error"})
```

---

## Configuration Options

| Option | Environment Variable | Default | Description |
| :--- | :--- | :--- | :--- |
| `api_key` | `TRACENEST_API_KEY` | *Required* | Project-scoped ingestion API key |
| `endpoint` | `TRACENEST_ENDPOINT` | `http://localhost:8000` | TraceNest backend API URL |
| `timeout` | — | `5.0` | Network request timeout in seconds |
| `raise_on_delivery_error` | — | `False` | Whether telemetry failures raise exceptions |
| `on_delivery_error` | — | `None` | Callback `(exc, payload) -> None` on failure |
| `max_metadata_bytes` | — | `32768` (32 KB) | Upper bound for metadata JSON |

---

## Error Handling Philosophy

TraceNest follows strict observability best practices:
1. **Never crash the monitored host application**: By default, `capture_exception` catches network or backend HTTP errors, returns a `DeliveryResult(success=False, error=...)`, and allows your application to proceed.
2. **Never swallow errors blindly**: If a delivery failure occurs, diagnostic callbacks can be attached via `on_delivery_error=my_logger`.
3. **Never modify application exceptions**: The monitored application's original exception is untouched and can be re-raised or handled as normal.
4. **Zero secret leakage**: Credentials are never printed in error logs, backtraces, or diagnostic payloads.

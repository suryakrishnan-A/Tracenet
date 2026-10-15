"""TraceNest Integration Example: Python FastAPI Application.

Demonstrates:
- Initializing TraceNest SDK from environment variables.
- Distributed request ID propagation.
- Automatic exception capture with performance latency measurement.
- Returning standard user-facing error response without leaking backtraces.
"""

import os
import time
import uuid
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from tracenest import AsyncTraceNest

app = FastAPI(title="Storefront API (TraceNest Demo)", version="1.0.0")

# Initialize TraceNest SDK (reads TRACENEST_API_KEY and TRACENEST_ENDPOINT)
tracenest = AsyncTraceNest(
    api_key=os.getenv("TRACENEST_API_KEY", "tn_ingest_placeholder"),
    endpoint=os.getenv("TRACENEST_ENDPOINT", "http://localhost:8000"),
    raise_on_delivery_error=False,
)


class CheckoutRequest(BaseModel):
    item_id: str
    quantity: int = 1
    payment_method: str = "card"


@app.middleware("http")
async def tracenest_telemetry_middleware(request: Request, call_next):
    """Middleware measuring request duration and capturing unhandled exceptions."""
    req_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = req_id
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Transmit telemetry to TraceNest
        delivery = await tracenest.capture_exception(
            exc,
            endpoint=request.url.path,
            http_status=500,
            duration_ms=duration_ms,
            request_id=req_id,
            metadata={
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

        # Return clean user-facing error response
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": "A server error occurred while processing your request.",
                "request_id": req_id,
                "tracenest_event_id": delivery.event_id if delivery.success else None,
            },
            headers={"X-Request-ID": req_id},
        )


@app.get("/")
async def root():
    """Service status."""
    return {"service": "storefront-api", "status": "operational"}


@app.get("/orders")
async def list_orders():
    """Successful endpoint demonstrating normal operation."""
    return {
        "orders": [
            {"order_id": "ord_101", "item": "Ergonomic Keyboard", "status": "shipped"},
            {"order_id": "ord_102", "item": "4K Monitor", "status": "processing"},
        ]
    }


@app.post("/orders/checkout")
async def checkout(request: CheckoutRequest):
    """Deliberately failing endpoint simulating upstream dependency failure."""
    if request.payment_method == "card":
        # Simulate an external gateway failure
        raise TimeoutError(
            "PaymentGatewayTimeout: Stripe payment intent confirmation timed out after 5000ms"
        )
    return {"status": "success", "order_id": f"ord_{uuid.uuid4().hex[:8]}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)

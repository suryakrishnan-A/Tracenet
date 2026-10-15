"""TraceNest Backend Application Entrypoint."""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.middleware import (
    RequestTracingMiddleware,
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    PayloadSizeLimitMiddleware,
)
from app.api.v1.api import api_router
from app.schemas.health import BasicHealthResponse

# Configure standard logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("tracenest")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Application Failure Investigation Platform API",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# Global Exception Handler (prevents leaking internal stack traces / credentials)
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "unknown")
    logger.exception(f"Unhandled server error [req_id={req_id}]: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred. Please contact support.",
            "request_id": req_id,
        },
        headers={"X-Request-ID": req_id},
    )

# Middlewares (Executed in reverse order of addition: RequestTracing -> RateLimit -> PayloadSize -> SecurityHeaders -> CORS -> App)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(PayloadSizeLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestTracingMiddleware)

# Cross-Origin Resource Sharing (CORS)
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Root health endpoint
@app.get(
    "/health",
    response_model=BasicHealthResponse,
    tags=["Health"],
    summary="Root Service Health Check",
    description="Minimal health endpoint returning service availability status.",
)
async def root_health() -> BasicHealthResponse:
    """Returns basic service health status."""
    return BasicHealthResponse(
        status="ok",
        service="tracenest-backend",
    )


# Mount versioned API routes (/api/v1)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

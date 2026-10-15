"""API v1 Router Aggregator."""

from fastapi import APIRouter
from app.api.v1.endpoints import health, projects, telemetry, issues

api_router = APIRouter()

# Mount endpoints
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(telemetry.router, prefix="/telemetry", tags=["Telemetry"])
api_router.include_router(issues.router, prefix="/issues", tags=["Issues"])

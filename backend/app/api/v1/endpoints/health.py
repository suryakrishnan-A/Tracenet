"""API v1 Health Endpoint."""

from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import ApiHealthResponse
from app.db.session import check_db_connection

router = APIRouter()


@router.get(
    "/health",
    response_model=ApiHealthResponse,
    summary="API v1 Health Check",
    description="Returns API status, version, environment, and database connectivity state.",
)
async def get_v1_health() -> ApiHealthResponse:
    """Check API v1 status and database connectivity."""
    db_alive = await check_db_connection()
    return ApiHealthResponse(
        status="ok",
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        api_version="v1",
        database_connected=db_alive,
    )

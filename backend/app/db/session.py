"""Database Engine and Session Configuration."""

from typing import AsyncGenerator
import logging
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from app.core.config import settings

logger = logging.getLogger(__name__)

# Create Async Engine with production pooling or dev/test NullPool
engine_kwargs = {
    "echo": settings.DEBUG and settings.ENVIRONMENT.lower() != "production",
    "future": True,
}

if settings.ENVIRONMENT.lower() == "production":
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_pre_ping": settings.DB_POOL_PRE_PING,
    })
else:
    engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """Safely check if the database connection is alive.
    
    Returns False without raising if the database is unreachable
    (essential for initial phase health checks prior to DB spin-up).
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.debug(f"Database health check failed (expected if DB not yet started): {e}")
        return False

"""Shared Pytest Fixtures for TraceNest Backend.

Uses the isolated test database (tracenest_test) and per-test truncation cleanup.
"""

from typing import AsyncGenerator
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.core.middleware import rate_limiter
from app.db.session import get_db

# Dedicated Test Engine bound to TEST_DATABASE_URL with NullPool to avoid asyncpg connection reuse conflicts
test_engine = create_async_engine(
    settings.TEST_DATABASE_URL,
    echo=False,
    future=True,
    poolclass=NullPool,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency override providing isolated test database sessions."""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture(autouse=True)
async def isolated_test_database():
    """Ensure database dependencies point to test DB and clean up tables after every test."""
    app.dependency_overrides[get_db] = _override_get_db
    rate_limiter.reset()
    yield
    rate_limiter.reset()
    app.dependency_overrides.clear()
    async with test_engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE TABLE telemetry_events, issue_groups, ingestion_keys, projects RESTART IDENTITY CASCADE")
        )


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for assertions within tests."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous HTTP test client fixture."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client

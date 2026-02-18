"""
Shared pytest fixtures for the ifcgit-4-nextcloud backend tests.

Sets up an in-memory SQLite database, a test FastAPI client, and
pre-authenticated user/client helpers.
"""

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# ---------------------------------------------------------------------------
# Override settings BEFORE any application module is imported so that all code
# that reads ``settings`` at import-time picks up the test values.
# ---------------------------------------------------------------------------
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("LOG_LEVEL", "warning")
os.environ.setdefault("DATA_DIR", "/tmp/ifcgit-test-data")

from src.db.database import Base, get_db  # noqa: E402
from src.main import app  # noqa: E402
from src.auth.service import register_user, create_jwt_token  # noqa: E402
from src.auth.models import User  # noqa: E402

# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest.fixture()
async def db_engine():
    """Create a fresh in-memory SQLite engine for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # SQLite requires enabling foreign-key enforcement explicitly.
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def db_session(db_engine):
    """Yield an async session bound to the test engine."""
    async_session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session


@pytest.fixture()
async def client(db_engine):
    """
    Provide an ``httpx.AsyncClient`` wired to the FastAPI app with the
    database dependency overridden to use the test engine.
    """
    async_session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def _override_get_db():
        async with async_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

TEST_USER_USERNAME = "testuser"
TEST_USER_EMAIL = "testuser@example.com"
TEST_USER_PASSWORD = "StrongP@ss1"


@pytest.fixture()
async def test_user(db_session) -> User:
    """Create and return a test user in the database."""
    user = await register_user(
        db_session,
        username=TEST_USER_USERNAME,
        email=TEST_USER_EMAIL,
        password=TEST_USER_PASSWORD,
        role="admin",
    )
    return user


@pytest.fixture()
async def auth_headers(test_user) -> dict[str, str]:
    """Return Authorization headers containing a valid JWT for ``test_user``."""
    token = create_jwt_token(str(test_user.id), test_user.username)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
async def auth_client(client, auth_headers) -> AsyncClient:
    """
    An ``httpx.AsyncClient`` whose requests automatically carry the JWT
    Authorization header of the test user.
    """
    client.headers.update(auth_headers)
    return client

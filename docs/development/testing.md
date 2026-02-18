# Testing Guide

This document describes how to run and write tests for the OpenAEC (IfcGit Server) backend.

## Quick Start

### Running Tests Locally

```bash
cd server
pip install -r requirements.txt
pip install -r requirements-test.txt
pytest -v
```

### Running Tests in Docker

```bash
docker compose exec api pytest -v
```

## Test Dependencies

Test dependencies are defined in `server/requirements-test.txt`:

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | 8.3.4 | Test runner and framework |
| `pytest-asyncio` | 0.24.0 | Async test support for FastAPI/SQLAlchemy |
| `httpx` | 0.28.1 | Async HTTP client for testing FastAPI endpoints |
| `aiosqlite` | 0.20.0 | SQLite async driver for in-memory test databases |

These are installed in addition to the main application dependencies in `server/requirements.txt`.

## Configuration

### pytest.ini

The pytest configuration is in `server/pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- **`asyncio_mode = auto`** -- All async test functions are automatically treated as async tests without requiring the `@pytest.mark.asyncio` decorator.
- **`testpaths = tests`** -- pytest looks for tests in the `server/tests/` directory.

## Test Structure

Tests are located in the `server/tests/` directory. The recommended structure mirrors the source code layout:

```
server/
  pytest.ini
  requirements-test.txt
  tests/
    conftest.py              # Shared fixtures (DB session, test client, auth helpers)
    test_auth.py             # Authentication and user management
    test_auth_settings.py    # Integration settings (ERPNext, Nextcloud)
    test_projects.py         # Project CRUD operations
    test_git.py              # Git operations (commit, branch, merge, diff)
    test_fragments.py        # Fragment generation and retrieval
    test_bcf.py              # BCF-API 3.0 topics and comments
    test_clash.py            # Clash detection
    test_check.py            # Model checking (IDS)
```

## Writing Tests

### Setting Up the Test Database

Tests should use an in-memory SQLite database to avoid depending on PostgreSQL. Create a `conftest.py` with shared fixtures:

```python
# server/tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.db.database import Base, get_db
from src.main import app

# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_database():
    """Create tables before each test and drop them after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    """Provide a database session for direct DB operations in tests."""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def client(db_session):
    """Provide an async HTTP client with the test DB session injected."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers(client):
    """Register a test user and return auth headers with a valid JWT."""
    await client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpassword123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

### Writing a Test

Tests are standard pytest async functions. Use the `client` and `auth_headers` fixtures for API testing:

```python
# server/tests/test_auth.py

async def test_register_first_user_gets_admin(client):
    resp = await client.post("/api/auth/register", json={
        "username": "admin",
        "email": "admin@example.com",
        "password": "securepassword",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "admin"


async def test_login_returns_jwt(client):
    # Register first
    await client.post("/api/auth/register", json={
        "username": "user1",
        "email": "user1@example.com",
        "password": "password123",
    })
    # Login
    resp = await client.post("/api/auth/login", json={
        "username": "user1",
        "password": "password123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_get_me_requires_auth(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401 or resp.status_code == 403
```

### Testing Integration Settings

```python
# server/tests/test_auth_settings.py

async def test_get_settings(client, auth_headers):
    resp = await client.get("/api/auth/settings", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["erpnext_api_secret_set"] is False
    assert data["nextcloud_password_set"] is False


async def test_update_erpnext_settings(client, auth_headers):
    resp = await client.put("/api/auth/settings", headers=auth_headers, json={
        "erpnext_url": "https://erp.example.com",
        "erpnext_api_key": "test-key",
        "erpnext_api_secret": "test-secret",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["erpnext_url"] == "https://erp.example.com"
    assert data["erpnext_api_key"] == "test-key"
    assert data["erpnext_api_secret_set"] is True


async def test_secret_never_returned_in_plaintext(client, auth_headers):
    # Set a secret
    await client.put("/api/auth/settings", headers=auth_headers, json={
        "erpnext_api_secret": "my-secret-value",
    })
    # Retrieve settings
    resp = await client.get("/api/auth/settings", headers=auth_headers)
    data = resp.json()
    # The actual secret must not appear anywhere in the response
    assert "my-secret-value" not in str(data)
    assert data["erpnext_api_secret_set"] is True
```

## Running Specific Tests

```bash
# Run a single test file
pytest tests/test_auth.py -v

# Run a single test function
pytest tests/test_auth.py::test_register_first_user_gets_admin -v

# Run tests matching a keyword
pytest -k "erpnext" -v

# Run with stdout output visible
pytest -v -s
```

## Test Coverage

To measure code coverage, install `pytest-cov` and run:

```bash
pip install pytest-cov
pytest --cov=src --cov-report=term-missing -v
```

This displays a coverage report showing which lines of source code are not exercised by the tests.

## Continuous Integration

When running tests in a CI pipeline, use the Docker-based approach to ensure the test environment matches production:

```bash
docker compose build api
docker compose run --rm api pytest -v --tb=short
```

For CI systems that do not support Docker, ensure PostgreSQL and Redis are available as services and set the corresponding environment variables (`DATABASE_URL`, `REDIS_URL`).

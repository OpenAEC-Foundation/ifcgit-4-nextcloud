"""
Integration tests for the settings-related endpoints on the auth router
(mounted at ``/api/auth``).

Every test uses an in-memory SQLite database and a fresh test user so that
tests are fully isolated.
"""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# GET /api/auth/settings
# ---------------------------------------------------------------------------

class TestGetSettings:
    """GET /api/auth/settings should return the user profile plus
    integration boolean flags."""

    async def test_returns_profile_fields(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/auth/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["email"] == "testuser@example.com"
        assert data["role"] == "admin"

    async def test_integration_flags_default_false(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/auth/settings")
        data = resp.json()
        assert data["erpnext_api_secret_set"] is False
        assert data["nextcloud_password_set"] is False
        assert data["erpnext_url"] is None
        assert data["nextcloud_url"] is None

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/auth/settings")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PUT /api/auth/settings
# ---------------------------------------------------------------------------

class TestPutSettings:
    """PUT /api/auth/settings should persist integration credentials and
    never return plaintext secrets."""

    async def test_save_erpnext_settings(self, auth_client: AsyncClient):
        payload = {
            "erpnext_url": "https://erp.example.com",
            "erpnext_api_key": "abc123",
            "erpnext_api_secret": "super-secret",
        }
        resp = await auth_client.put("/api/auth/settings", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["erpnext_url"] == "https://erp.example.com"
        assert data["erpnext_api_key"] == "abc123"
        # Secret must NOT be returned in plaintext -- only a boolean flag.
        assert data["erpnext_api_secret_set"] is True
        assert "erpnext_api_secret" not in data

    async def test_save_nextcloud_settings(self, auth_client: AsyncClient):
        payload = {
            "nextcloud_url": "https://cloud.example.com",
            "nextcloud_username": "ncuser",
            "nextcloud_password": "ncpass",
        }
        resp = await auth_client.put("/api/auth/settings", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["nextcloud_url"] == "https://cloud.example.com"
        assert data["nextcloud_username"] == "ncuser"
        assert data["nextcloud_password_set"] is True
        assert "nextcloud_password" not in data

    async def test_partial_update_preserves_existing(self, auth_client: AsyncClient):
        """Sending only one field should not clear the others."""
        # First, set ERPNext fields.
        await auth_client.put(
            "/api/auth/settings",
            json={
                "erpnext_url": "https://erp.example.com",
                "erpnext_api_key": "key1",
                "erpnext_api_secret": "secret1",
            },
        )
        # Now update only the Nextcloud URL.
        resp = await auth_client.put(
            "/api/auth/settings",
            json={"nextcloud_url": "https://cloud.example.com"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # ERPNext values should still be intact.
        assert data["erpnext_url"] == "https://erp.example.com"
        assert data["erpnext_api_key"] == "key1"
        assert data["erpnext_api_secret_set"] is True

    async def test_clear_secret_with_empty_string(self, auth_client: AsyncClient):
        """Sending an empty string for a secret should clear it."""
        # Set a secret first.
        await auth_client.put(
            "/api/auth/settings",
            json={"erpnext_api_secret": "something"},
        )
        # Clear it.
        resp = await auth_client.put(
            "/api/auth/settings",
            json={"erpnext_api_secret": ""},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["erpnext_api_secret_set"] is False

    async def test_get_reflects_put(self, auth_client: AsyncClient):
        """A subsequent GET should reflect what was saved by PUT."""
        await auth_client.put(
            "/api/auth/settings",
            json={
                "erpnext_url": "https://erp.example.com",
                "erpnext_api_key": "mykey",
                "erpnext_api_secret": "mysecret",
            },
        )
        resp = await auth_client.get("/api/auth/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["erpnext_url"] == "https://erp.example.com"
        assert data["erpnext_api_key"] == "mykey"
        assert data["erpnext_api_secret_set"] is True


# ---------------------------------------------------------------------------
# POST /api/auth/settings/erpnext/test
# ---------------------------------------------------------------------------

class TestErpnextTestEndpoint:
    """POST /api/auth/settings/erpnext/test should return 400 when no
    credentials are stored."""

    async def test_no_credentials_returns_400(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/auth/settings/erpnext/test")
        assert resp.status_code == 400
        data = resp.json()
        assert "not configured" in data["detail"].lower()

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.post("/api/auth/settings/erpnext/test")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/auth/settings/nextcloud/test
# ---------------------------------------------------------------------------

class TestNextcloudTestEndpoint:
    """POST /api/auth/settings/nextcloud/test should return 400 when no
    credentials are stored."""

    async def test_no_credentials_returns_400(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/auth/settings/nextcloud/test")
        assert resp.status_code == 400
        data = resp.json()
        assert "not configured" in data["detail"].lower()

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.post("/api/auth/settings/nextcloud/test")
        assert resp.status_code in (401, 403)

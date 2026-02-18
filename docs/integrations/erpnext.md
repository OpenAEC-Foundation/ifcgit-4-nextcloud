# ERPNext Integration

## Overview

The ERPNext integration connects OpenAEC (IfcGit Server) to your ERPNext instance, enabling cost tracking, quantity takeoff synchronisation, and project linking between BIM models and ERP workflows. Once configured, the system can bridge the gap between design data locked inside IFC files and the financial and procurement data managed in ERPNext.

Key capabilities:

- Link BIM projects to ERPNext projects for centralised tracking
- Sync Bill of Materials (BOM) quantities extracted from IFC models
- Validate connectivity between the two systems with a single click

## Prerequisites

- A running ERPNext instance (v14 or v15) accessible over HTTPS
- An ERPNext user account with API access permissions
- An OpenAEC user account (admin or editor role)

## Setup

### 1. Generate API Credentials in ERPNext

1. Log in to your ERPNext instance.
2. Navigate to your **User** page (click your avatar, then **My Settings**).
3. Scroll down to the **API Access** section.
4. Click **Generate Keys**.
5. Copy the **API Key** displayed on the page.
6. Copy the **API Secret** shown in the dialog -- this is only shown once. Store it securely.

### 2. Configure the Integration in OpenAEC

1. Log in to OpenAEC.
2. Navigate to the **Settings** page (user menu > Settings).
3. In the **ERPNext** section, fill in:
   - **ERPNext URL** -- the base URL of your ERPNext instance (e.g. `https://erp.example.com`)
   - **API Key** -- the key generated in step 1
   - **API Secret** -- the secret generated in step 1
4. Click **Save**.

### 3. Test the Connection

1. After saving, click **Test Connection** in the ERPNext section.
2. A successful test returns the logged-in ERPNext username.
3. If the test fails, verify:
   - The URL is reachable from the OpenAEC server
   - The API key and secret are correct
   - The ERPNext user has the necessary roles and permissions

## Security

### Credential Storage

Integration credentials are stored per-user in the PostgreSQL database with the following security model:

| Field | Storage Method |
|-------|---------------|
| `erpnext_url` | Plaintext (not sensitive) |
| `erpnext_api_key` | Plaintext (acts as a username) |
| `erpnext_api_secret` | **Fernet encrypted** using the application `secret_key` |

The encryption uses Python's `cryptography` library:

1. A Fernet-compatible key is derived from the application `SECRET_KEY` using SHA-256.
2. The API secret is encrypted with `Fernet.encrypt()` before being written to the database.
3. On retrieval, the secret is decrypted server-side only when needed (e.g. to test the connection or make API calls).
4. The API secret is **never returned in plaintext** to the frontend. The `GET /api/auth/settings` endpoint returns only a boolean `erpnext_api_secret_set` flag indicating whether a secret has been configured.

### Production Recommendations

- Set a strong, unique `SECRET_KEY` environment variable. The default development key must not be used in production.
- Use HTTPS for both the OpenAEC server and the ERPNext instance.
- Create a dedicated ERPNext user with the minimum required permissions for the integration.

## API Reference

All endpoints require JWT authentication via the `Authorization: Bearer <token>` header.

### GET /api/auth/settings

Retrieve the current user's integration settings.

**Response (200):**

```json
{
  "username": "maarten",
  "email": "maarten@example.com",
  "role": "admin",
  "erpnext_url": "https://erp.example.com",
  "erpnext_api_key": "abc123def456",
  "erpnext_api_secret_set": true,
  "nextcloud_url": null,
  "nextcloud_username": null,
  "nextcloud_password_set": false
}
```

Note: `erpnext_api_secret_set` is a boolean indicating whether the secret is configured. The actual secret value is never returned.

### PUT /api/auth/settings

Update integration settings. Only the fields provided in the request body are updated; omitted fields are left unchanged.

**Request body:**

```json
{
  "erpnext_url": "https://erp.example.com",
  "erpnext_api_key": "abc123def456",
  "erpnext_api_secret": "supersecretvalue"
}
```

**Response (200):** Same shape as `GET /api/auth/settings`.

To clear a field, send an empty string:

```json
{
  "erpnext_url": "",
  "erpnext_api_key": "",
  "erpnext_api_secret": ""
}
```

### POST /api/auth/settings/erpnext/test

Test the stored ERPNext connection. Calls the ERPNext `frappe.auth.get_logged_user` method using the stored credentials.

**Preconditions:** ERPNext URL, API key, and API secret must all be configured.

**Response (200) -- success:**

```json
{
  "success": true,
  "user": "administrator@example.com"
}
```

**Response (200) -- failure:**

```json
{
  "success": false,
  "error": "HTTP 401: {\"exc_type\":\"AuthenticationError\"}"
}
```

**Response (400):**

```json
{
  "detail": "ERPNext credentials not configured"
}
```

## Database Schema

The integration fields are stored on the `users` table, added by migration `001_add_integration_fields`:

| Column | Type | Notes |
|--------|------|-------|
| `erpnext_url` | `VARCHAR(512)` | Nullable |
| `erpnext_api_key` | `VARCHAR(512)` | Nullable |
| `erpnext_api_secret` | `TEXT` | Nullable, Fernet-encrypted ciphertext |

## Roadmap

The following features are planned for future releases:

- **Project linking** -- Associate OpenAEC projects with ERPNext projects for bidirectional status tracking.
- **BOM quantity sync** -- Extract material quantities from IFC models (via IfcOpenShell property sets and quantity takeoff) and push them to ERPNext BOMs.
- **Auto-create purchase orders** -- Generate ERPNext purchase orders directly from quantity takeoff data extracted from IFC models.
- **Cost dashboard** -- Display ERPNext project costs and budget status within the OpenAEC project view.

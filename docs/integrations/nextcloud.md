# Nextcloud Integration

## Overview

The Nextcloud integration enables OpenAEC (IfcGit Server) to use Nextcloud as a file storage backend for IFC models. Nextcloud provides a familiar, self-hosted file management layer with sharing, access control, and desktop/mobile sync clients, while OpenAEC handles Git-based version control and BIM-specific processing on top of the stored files.

Key capabilities:

- Store and retrieve IFC models from Nextcloud via WebDAV
- Leverage Nextcloud's sharing and group permissions for team collaboration
- Maintain version history through Git while files remain accessible in Nextcloud
- Validate connectivity with a one-click connection test

## Prerequisites

- A running Nextcloud instance (v25 or later recommended) accessible over HTTPS
- A Nextcloud user account
- An OpenAEC user account (admin or editor role)

## Setup

### 1. Create an App Password in Nextcloud

Using an app password is recommended over your main account password. App passwords can be revoked individually and do not expose your primary credentials.

1. Log in to your Nextcloud instance.
2. Navigate to **Settings** (click your avatar in the top-right corner).
3. Go to **Security** in the left sidebar.
4. Scroll to the **Devices & sessions** section.
5. Enter a name for the app (e.g. `OpenAEC`) in the text field.
6. Click **Create new app password**.
7. Copy the generated password -- it is only shown once.

### 2. Configure the Integration in OpenAEC

1. Log in to OpenAEC.
2. Navigate to the **Settings** page (user menu > Settings).
3. In the **Nextcloud** section, fill in:
   - **Nextcloud URL** -- the base URL of your Nextcloud instance (e.g. `https://cloud.example.com`)
   - **Username** -- your Nextcloud username
   - **Password** -- the app password generated in step 1
4. Click **Save**.

### 3. Test the Connection

1. After saving, click **Test Connection** in the Nextcloud section.
2. A successful test returns the display name of the authenticated Nextcloud user.
3. If the test fails, verify:
   - The URL is reachable from the OpenAEC server
   - The username and app password are correct
   - The Nextcloud user account is not disabled or locked

## How It Works

### WebDAV-Based File Access

Nextcloud exposes a WebDAV interface at:

```
https://cloud.example.com/remote.php/dav/files/{username}/
```

OpenAEC uses this WebDAV endpoint (via the `httpx` HTTP client) to read and write IFC files. The connection test validates credentials by calling the Nextcloud OCS API:

```
GET /ocs/v1.php/cloud/user
```

This returns the authenticated user's profile, confirming that the credentials are valid.

### Storage Architecture

```
Nextcloud (file storage)
    |
    +-- /OpenAEC/ProjectA/model.ifc
    +-- /OpenAEC/ProjectB/arch.ifc
    |
OpenAEC Server (version control + BIM processing)
    |
    +-- Git bare repos (versioned IFC history)
    +-- Fragment cache (3D viewer data)
    +-- PostgreSQL (metadata, BCF topics, users)
```

Models stored in Nextcloud are pulled into OpenAEC's Git repositories for version control. Each commit in Git tracks the state of the IFC file at a point in time, while Nextcloud provides the user-facing file management interface.

## Security

### Credential Storage

Integration credentials are stored per-user in the PostgreSQL database:

| Field | Storage Method |
|-------|---------------|
| `nextcloud_url` | Plaintext (not sensitive) |
| `nextcloud_username` | Plaintext (acts as an identifier) |
| `nextcloud_password` | **Fernet encrypted** using the application `secret_key` |

The encryption mechanism is identical to the ERPNext integration:

1. A Fernet-compatible key is derived from the application `SECRET_KEY` via SHA-256.
2. The app password is encrypted with `Fernet.encrypt()` before being stored.
3. The password is decrypted server-side only when needed (connection tests, file operations).
4. The password is **never returned in plaintext** to the frontend. The `GET /api/auth/settings` endpoint returns only a boolean `nextcloud_password_set` flag.

### Production Recommendations

- Always use HTTPS for both OpenAEC and Nextcloud.
- Use a dedicated Nextcloud app password rather than the main account password.
- Set a strong, unique `SECRET_KEY` environment variable in production.
- Consider creating a dedicated Nextcloud service account for the integration.

## API Reference

All endpoints require JWT authentication via the `Authorization: Bearer <token>` header.

### GET /api/auth/settings

Retrieve the current user's integration settings (shared with ERPNext settings).

**Response (200):**

```json
{
  "username": "maarten",
  "email": "maarten@example.com",
  "role": "admin",
  "erpnext_url": null,
  "erpnext_api_key": null,
  "erpnext_api_secret_set": false,
  "nextcloud_url": "https://cloud.example.com",
  "nextcloud_username": "maarten",
  "nextcloud_password_set": true
}
```

### PUT /api/auth/settings

Update integration settings. Only provided fields are updated.

**Request body:**

```json
{
  "nextcloud_url": "https://cloud.example.com",
  "nextcloud_username": "maarten",
  "nextcloud_password": "app-password-here"
}
```

**Response (200):** Same shape as `GET /api/auth/settings`.

To clear the Nextcloud configuration, send empty strings:

```json
{
  "nextcloud_url": "",
  "nextcloud_username": "",
  "nextcloud_password": ""
}
```

### POST /api/auth/settings/nextcloud/test

Test the stored Nextcloud connection by calling the OCS user endpoint.

**Preconditions:** Nextcloud URL, username, and password must all be configured.

**Response (200) -- success:**

```json
{
  "success": true,
  "user": "Maarten de Vries"
}
```

**Response (200) -- failure:**

```json
{
  "success": false,
  "error": "HTTP 401: ..."
}
```

**Response (400):**

```json
{
  "detail": "Nextcloud credentials not configured"
}
```

## Database Schema

The integration fields are stored on the `users` table, added by migration `001_add_integration_fields`:

| Column | Type | Notes |
|--------|------|-------|
| `nextcloud_url` | `VARCHAR(512)` | Nullable |
| `nextcloud_username` | `VARCHAR(255)` | Nullable |
| `nextcloud_password` | `TEXT` | Nullable, Fernet-encrypted ciphertext |

## Roadmap

The following features are planned for future releases:

- **Auto-sync project files** -- Automatically pull updated IFC files from a designated Nextcloud folder into the OpenAEC Git repository when changes are detected.
- **Shared access via Nextcloud groups** -- Map Nextcloud group memberships to OpenAEC project permissions, enabling team access management through a single interface.
- **Bidirectional sync** -- Push updated models from OpenAEC back to Nextcloud after merges or model transformations.
- **Nextcloud activity integration** -- Surface OpenAEC commit and review activity in the Nextcloud activity stream.

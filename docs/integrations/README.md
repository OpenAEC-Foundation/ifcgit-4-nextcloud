# Integrations

OpenAEC (IfcGit Server) supports integrations with external systems to extend its BIM version control capabilities into ERP, file storage, and graph analysis workflows.

All integrations are configured per-user through the **Settings** page in the web interface, or programmatically via the `PUT /api/auth/settings` API endpoint. Sensitive credentials (API secrets, passwords) are encrypted at rest using Fernet symmetric encryption and are never returned in plaintext through the API.

## Available Integrations

### ERPNext -- ERP and Cost Management

Connect OpenAEC to [ERPNext](https://erpnext.com) for cost tracking, quantity takeoff synchronisation, and project linking between BIM models and ERP workflows.

- **Status:** Authentication and connection testing implemented
- **Documentation:** [erpnext.md](erpnext.md)

### Nextcloud -- File Storage

Use [Nextcloud](https://nextcloud.com) as a file storage backend for IFC models, combining Nextcloud's sharing and sync capabilities with OpenAEC's Git-based version control.

- **Status:** Authentication and connection testing implemented
- **Documentation:** [nextcloud.md](nextcloud.md)

### Neo4j Graph Database -- Coming Soon

A [Neo4j](https://neo4j.com) integration is planned to enable graph-based querying of IFC model data. This will allow spatial and relational queries across building elements, such as finding all walls connected to a specific slab, or traversing the spatial hierarchy of a building.

- **Status:** Neo4j driver included in dependencies (`neo4j==5.27.0`), integration not yet implemented
- **Planned capabilities:**
  - Import IFC spatial and relational structure into a Neo4j graph
  - Query element relationships using Cypher
  - Cross-model federation queries
  - Dependency analysis for change impact assessment

## Architecture

Integration credentials are stored on the `users` table in PostgreSQL. The relevant fields were added by the database migration `001_add_integration_fields`.

```
User (PostgreSQL)
  +-- erpnext_url           (plaintext)
  +-- erpnext_api_key       (plaintext)
  +-- erpnext_api_secret    (Fernet encrypted)
  +-- nextcloud_url         (plaintext)
  +-- nextcloud_username    (plaintext)
  +-- nextcloud_password    (Fernet encrypted)
```

The encryption key is derived from the application's `SECRET_KEY` environment variable. Changing this key will invalidate all stored encrypted credentials, requiring users to re-enter their integration secrets.

## Common API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/auth/settings` | Retrieve all integration settings (secrets masked) |
| PUT | `/api/auth/settings` | Update integration settings |
| POST | `/api/auth/settings/erpnext/test` | Test ERPNext connection |
| POST | `/api/auth/settings/nextcloud/test` | Test Nextcloud connection |

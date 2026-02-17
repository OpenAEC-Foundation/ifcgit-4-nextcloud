# IfcGit Server

Open-source IFC version control and collaboration server for the AEC industry.

Built on **Git + ifcmerge** for true version control, **That Open Company** (@thatopen/components) for browser-based 3D viewing, and **IfcOpenShell** for server-side IFC processing.

## Features

- **Version Control** — Git-backed IFC versioning with branching, merging (ifcmerge), and semantic diffing
- **3D Viewer** — Browser-based 60fps IFC viewing with spatial tree, properties panel, and element selection
- **Fragment Caching** — Server-side IFC-to-Fragment conversion cached per commit hash
- **BCF Support** — BCF-API 3.0 compliant issue tracking with viewpoints and comments
- **WebDAV** — Open/save IFC files directly from Revit, Bonsai/BlenderBIM, FreeCAD
- **REST API** — Full OpenAPI-documented API for all operations
- **Self-Hosted** — Single `docker compose up` deployment

## Architecture

| Container | Technology | Purpose |
|-----------|-----------|---------|
| `gateway` | Caddy | Reverse proxy, TLS, routing |
| `api` | Python 3.12 + FastAPI | REST API, business logic |
| `worker` | Same as api | Background jobs (fragments, clash detection) |
| `frontend` | Vue.js 3 + That Open Company | 3D viewer web application |
| `redis` | Redis 7 | Job queue, caching |
| `db` | PostgreSQL 16 | Metadata, users, BCF topics |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Setup

```bash
# Clone the repository
git clone <repo-url> ifcgit-server
cd ifcgit-server

# Create environment file
cp .env.example .env
# Edit .env and set a secure SECRET_KEY

# Start all services
docker compose up -d

# The server is available at http://localhost
# API docs at http://localhost/api/docs
```

### First Steps

1. Open `http://localhost/app/` in your browser
2. Register the first user (automatically gets admin role)
3. Create a project
4. Upload an IFC file
5. View the model in the 3D viewer

### Development

**Backend:**

```bash
cd server
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, get JWT token |
| GET | `/api/auth/me` | Current user info |
| POST | `/api/auth/tokens` | Create API token |

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List projects |
| POST | `/api/projects` | Create project |
| GET | `/api/projects/{slug}` | Project details |

### Files & Git
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/{slug}/files` | List files |
| POST | `/api/projects/{slug}/files` | Upload file (auto-commits) |
| GET | `/api/projects/{slug}/files/{path}` | Download file |
| GET | `/api/projects/{slug}/git/log` | Commit history |
| GET | `/api/projects/{slug}/git/branches` | List branches |
| POST | `/api/projects/{slug}/git/branches` | Create branch |
| POST | `/api/projects/{slug}/git/branches/{name}/merge` | Merge branch |
| GET | `/api/projects/{slug}/git/diff` | Diff between commits |

### Fragments (Viewer)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/{slug}/fragments/{path}` | Get .frag file |
| GET | `/api/projects/{slug}/fragments/{path}/properties` | Properties JSON |
| GET | `/api/projects/{slug}/fragments/{path}/spatial` | Spatial tree JSON |

### BCF (BCF-API 3.0)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/bcf/3.0/projects/{id}/topics` | List topics |
| POST | `/api/bcf/3.0/projects/{id}/topics` | Create topic |
| GET | `/api/bcf/3.0/projects/{id}/topics/{guid}/comments` | List comments |

### WebDAV
```
/dav/projects/{slug}/files/    — WebDAV access for external tools
```

## External Tool Integration

### Revit / Bonsai / FreeCAD
Connect via WebDAV at `http://your-server/dav/projects/{slug}/files/`

### API Token Authentication
```bash
# Create a token via the API
curl -X POST http://localhost/api/auth/tokens \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-tool"}'

# Use the token
curl http://localhost/api/projects \
  -H "Authorization: Bearer ifcgit_<token>"
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| API Server | Python 3.12, FastAPI |
| IFC Processing | IfcOpenShell 0.8+ |
| Git Operations | pygit2 (libgit2) |
| IFC Merging | ifcmerge (Rust) |
| Fragment Generation | @thatopen/fragments (Node.js) |
| 3D Viewer | @thatopen/components + Three.js |
| Frontend | Vue.js 3, Pinia, TypeScript |
| Database | PostgreSQL 16 |
| Job Queue | Redis 7 + arq |
| WebDAV | WsgiDAV |
| Reverse Proxy | Caddy |

## Roadmap

- **Phase 1** (current): Upload, view, version control, WebDAV, API
- **Phase 2**: Model federation, BCF with viewpoints, branching/merging UI, clash detection, Nextcloud integration
- **Phase 3**: IDS model checking, streaming tiles for large models, LOD, SSO, webhooks
- **Phase 4**: Bonsai/FreeCAD addons, ERPNext integration, WebGPU renderer

## License

AGPL-3.0 — see [LICENSE](LICENSE)

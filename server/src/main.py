import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.db.database import init_db
from src.auth.routes import router as auth_router
from src.projects.routes import router as projects_router
from src.git.routes import router as git_router
from src.fragments.routes import router as fragments_router
from src.bcf.routes import router as bcf_router
from src.clash.routes import router as clash_router
from src.check.routes import router as check_router
from src.graph.routes import router as graph_router

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting IfcGit Server...")
    await init_db()
    # Ensure data directories exist
    import os
    for d in [settings.repos_dir, settings.cache_dir, settings.working_dir]:
        os.makedirs(d, exist_ok=True)
    # Initialize Neo4j if enabled
    if settings.neo4j_enabled:
        try:
            from src.graph.service import ensure_indexes, close_driver
            await ensure_indexes()
            logger.info("Neo4j graph database connected and indexes ensured.")
        except Exception as e:
            logger.warning(f"Neo4j not available: {e}")

    logger.info("IfcGit Server ready.")
    yield

    # Cleanup Neo4j
    if settings.neo4j_enabled:
        try:
            from src.graph.service import close_driver
            await close_driver()
        except Exception:
            pass
    logger.info("Shutting down IfcGit Server.")


app = FastAPI(
    title="IfcGit Server",
    description="Open-source IFC version control and collaboration server",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(projects_router, prefix="/api/projects", tags=["Projects"])
app.include_router(git_router, prefix="/api/projects", tags=["Git"])
app.include_router(fragments_router, prefix="/api/projects", tags=["Fragments"])
app.include_router(bcf_router, prefix="/api/bcf/3.0", tags=["BCF"])
app.include_router(clash_router, prefix="/api/projects", tags=["Clash Detection"])
app.include_router(check_router, prefix="/api/projects", tags=["Model Checking"])
app.include_router(graph_router, prefix="/api/projects", tags=["Graph Database"])


@app.get("/api/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/api/metrics", tags=["System"])
async def metrics():
    """Prometheus-compatible metrics endpoint (placeholder)."""
    return {"status": "ok"}

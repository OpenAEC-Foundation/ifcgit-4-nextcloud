import logging

from arq import create_pool
from arq.connections import RedisSettings, ArqRedis

from src.config import settings

logger = logging.getLogger(__name__)

_redis_pool: ArqRedis | None = None


def parse_redis_url(url: str) -> RedisSettings:
    """Parse a Redis URL into ArqRedis settings."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
    )


async def get_redis_pool() -> ArqRedis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = await create_pool(parse_redis_url(settings.redis_url))
    return _redis_pool


async def enqueue_fragment_generation(
    project_id: str, file_path: str, commit_hash: str
):
    """Queue a fragment generation job."""
    pool = await get_redis_pool()
    await pool.enqueue_job(
        "generate_fragment_job",
        project_id,
        file_path,
        commit_hash,
    )
    logger.info(f"Queued fragment generation for {file_path} at {commit_hash[:8]}")


async def enqueue_clash_detection(
    project_id: str, clash_set_id: str
):
    """Queue a clash detection job."""
    pool = await get_redis_pool()
    await pool.enqueue_job("run_clash_detection_job", project_id, clash_set_id)


async def enqueue_model_validation(
    project_id: str, ids_file_path: str, ifc_file_path: str, commit_hash: str
):
    """Queue a model validation job."""
    pool = await get_redis_pool()
    await pool.enqueue_job(
        "run_validation_job", project_id, ids_file_path, ifc_file_path, commit_hash
    )


async def enqueue_graph_import(
    project_id: str, ifc_path: str, job_id: str,
):
    """Queue an IFC-to-graph import job (background, for large files)."""
    pool = await get_redis_pool()
    await pool.enqueue_job("run_graph_import_job", project_id, ifc_path, job_id)
    logger.info(f"Queued graph import job {job_id} for {ifc_path}")


# --- Worker functions ---

async def generate_fragment_job(ctx, project_id: str, file_path: str, commit_hash: str):
    """Background job: generate fragments for an IFC file."""
    from sqlalchemy import select
    from src.db.database import async_session
    from src.projects.models import Project
    from src.fragments.service import generate_fragment

    logger.info(f"Generating fragment for {file_path} at {commit_hash[:8]}")

    async with async_session() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            logger.error(f"Project {project_id} not found")
            return

        frag_path = await generate_fragment(
            project_slug=project.slug,
            repo_path=project.git_repo_path,
            file_path=file_path,
            commit_hash=commit_hash,
        )

        if frag_path:
            from src.fragments.models import FragmentCache
            import os

            cache_entry = FragmentCache(
                project_id=project.id,
                file_path=file_path,
                commit_hash=commit_hash,
                fragment_path=frag_path,
                file_size=os.path.getsize(frag_path),
            )
            db.add(cache_entry)
            await db.commit()
            logger.info(f"Fragment generated: {frag_path}")
        else:
            logger.warning(f"Fragment generation failed for {file_path}")


async def run_clash_detection_job(ctx, project_id: str, clash_set_id: str):
    """Background job: run clash detection."""
    logger.info(f"Running clash detection for set {clash_set_id}")
    # Placeholder for Phase 2


async def run_validation_job(
    ctx, project_id: str, ids_file_path: str, ifc_file_path: str, commit_hash: str
):
    """Background job: run model validation."""
    logger.info(f"Running validation for {ifc_file_path} at {commit_hash[:8]}")
    # Placeholder for Phase 3


async def run_graph_import_job(ctx, project_id: str, ifc_path: str, job_id: str):
    """Background job: import IFC file into Neo4j graph database.

    Runs in the ARQ worker process. The heavy IFC parsing is further
    offloaded to a ProcessPoolExecutor so the worker stays responsive.
    """
    logger.info(f"Starting graph import job {job_id} for {ifc_path}")
    from src.graph.service import import_ifc_to_graph, set_import_progress

    try:
        result = await import_ifc_to_graph(project_id, ifc_path, job_id=job_id)
        if not result.get("success"):
            logger.error(f"Graph import failed: {result.get('error')}")
        else:
            logger.info(
                f"Graph import {job_id} done: "
                f"{result['nodes_created']} nodes, "
                f"{result['relationships_created']} rels in "
                f"{result['total_time_s']}s"
            )
    except Exception as e:
        logger.exception(f"Graph import job {job_id} crashed: {e}")
        await set_import_progress(job_id, {
            "status": "failed",
            "error": str(e),
            "progress": 0,
        })


class WorkerSettings:
    """arq worker settings."""
    functions = [
        generate_fragment_job,
        run_clash_detection_job,
        run_validation_job,
        run_graph_import_job,
    ]
    redis_settings = parse_redis_url(settings.redis_url)
    max_jobs = 4
    job_timeout = 7200  # 2 hours (large IFC imports)

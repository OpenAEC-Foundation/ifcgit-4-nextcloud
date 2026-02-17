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


class WorkerSettings:
    """arq worker settings."""
    functions = [generate_fragment_job, run_clash_detection_job, run_validation_job]
    redis_settings = parse_redis_url(settings.redis_url)
    max_jobs = 4
    job_timeout = 1800  # 30 minutes

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.db.database import get_db
from src.fragments.service import get_or_generate_fragment, get_fragment_cache_dir
from src.git.service import get_commit_log
from src.projects.routes import require_project_access

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{slug}/fragments/{file_path:path}")
async def get_fragment(
    slug: str,
    file_path: str,
    branch: str = Query("main"),
    commit: str = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the .frag file for an IFC file (cached per commit)."""
    project = await require_project_access(slug, user, db)

    # Resolve commit hash
    if not commit:
        commits = get_commit_log(project.git_repo_path, branch, limit=1)
        if not commits:
            raise HTTPException(status_code=404, detail="No commits found")
        commit = commits[0].hash

    frag_path = await get_or_generate_fragment(
        db=db,
        project_id=project.id,
        project_slug=project.slug,
        repo_path=project.git_repo_path,
        file_path=file_path,
        commit_hash=commit,
        branch=branch,
    )

    if not frag_path or not os.path.exists(frag_path):
        raise HTTPException(status_code=404, detail="Fragment not available. Generation may be in progress.")

    return FileResponse(frag_path, media_type="application/octet-stream")


@router.get("/{slug}/fragments/{file_path:path}/properties")
async def get_properties(
    slug: str,
    file_path: str,
    branch: str = Query("main"),
    commit: str = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the properties JSON for an IFC file."""
    project = await require_project_access(slug, user, db)

    if not commit:
        commits = get_commit_log(project.git_repo_path, branch, limit=1)
        if not commits:
            raise HTTPException(status_code=404, detail="No commits found")
        commit = commits[0].hash

    cache_dir = get_fragment_cache_dir(project.slug, commit)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    props_path = os.path.join(cache_dir, f"{base_name}.properties.json")

    if not os.path.exists(props_path):
        raise HTTPException(status_code=404, detail="Properties not available")

    return FileResponse(props_path, media_type="application/json")


@router.get("/{slug}/fragments/{file_path:path}/spatial")
async def get_spatial_tree(
    slug: str,
    file_path: str,
    branch: str = Query("main"),
    commit: str = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the spatial tree JSON for an IFC file."""
    project = await require_project_access(slug, user, db)

    if not commit:
        commits = get_commit_log(project.git_repo_path, branch, limit=1)
        if not commits:
            raise HTTPException(status_code=404, detail="No commits found")
        commit = commits[0].hash

    cache_dir = get_fragment_cache_dir(project.slug, commit)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    spatial_path = os.path.join(cache_dir, f"{base_name}.spatial-tree.json")

    if not os.path.exists(spatial_path):
        raise HTTPException(status_code=404, detail="Spatial tree not available")

    return FileResponse(spatial_path, media_type="application/json")


@router.post("/{slug}/fragments/{file_path:path}/generate")
async def regenerate_fragment(
    slug: str,
    file_path: str,
    branch: str = Query("main"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Force regeneration of fragments for an IFC file."""
    project = await require_project_access(slug, user, db, required_role="editor")

    commits = get_commit_log(project.git_repo_path, branch, limit=1)
    if not commits:
        raise HTTPException(status_code=404, detail="No commits found")

    try:
        from src.workers.queue import enqueue_fragment_generation
        await enqueue_fragment_generation(str(project.id), file_path, commits[0].hash)
        return {"status": "queued", "message": "Fragment regeneration queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue regeneration: {e}")

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.db.database import get_db
from src.git import service as git_svc
from src.git.diff_service import get_diff_between_commits, get_semantic_ifc_diff
from src.git.merge_service import merge_branches
from src.projects.routes import require_project_access

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Schemas ---

class FileUploadResponse(BaseModel):
    commit_hash: str
    file_path: str
    message: str


class BranchCreate(BaseModel):
    name: str
    source: str = "main"


class MergeRequest(BaseModel):
    message: str | None = None


class CommitResponse(BaseModel):
    hash: str
    message: str
    author_name: str
    author_email: str
    timestamp: int


# --- File Endpoints ---

@router.get("/{slug}/files")
async def list_files(
    slug: str,
    branch: str = Query("main"),
    path: str = Query(""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await require_project_access(slug, user, db)
    files = git_svc.list_files(project.git_repo_path, branch, path)
    return {"files": files, "branch": branch, "path": path}


@router.post("/{slug}/files", response_model=FileUploadResponse)
async def upload_file(
    slug: str,
    file: UploadFile = File(...),
    path: str = Query("", description="Subdirectory path"),
    branch: str = Query("main"),
    message: str = Query("", description="Commit message"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await require_project_access(slug, user, db, required_role="editor")

    file_data = await file.read()
    file_path = f"{path}/{file.filename}".strip("/") if path else file.filename

    if not message:
        message = f"Upload {file_path}"

    commit_hash = git_svc.commit_file(
        repo_path=project.git_repo_path,
        file_path=file_path,
        file_data=file_data,
        message=message,
        author_name=user.username,
        author_email=user.email,
        branch=branch,
    )

    # Queue fragment generation if it's an IFC file
    if file_path.lower().endswith(".ifc"):
        try:
            from src.workers.queue import enqueue_fragment_generation
            await enqueue_fragment_generation(str(project.id), file_path, commit_hash)
        except Exception as e:
            logger.warning(f"Failed to queue fragment generation: {e}")

    return FileUploadResponse(commit_hash=commit_hash, file_path=file_path, message=message)


@router.get("/{slug}/files/{file_path:path}")
async def download_file(
    slug: str,
    file_path: str,
    branch: str = Query("main"),
    commit: str = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await require_project_access(slug, user, db)

    if commit:
        content = git_svc.get_file_content_at_commit(project.git_repo_path, file_path, commit)
    else:
        content = git_svc.get_file_content(project.git_repo_path, file_path, branch)

    if content is None:
        raise HTTPException(status_code=404, detail="File not found")

    media_type = "application/octet-stream"
    if file_path.lower().endswith(".ifc"):
        media_type = "application/x-step"

    filename = file_path.split("/")[-1]
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.put("/{slug}/files/{file_path:path}", response_model=FileUploadResponse)
async def update_file(
    slug: str,
    file_path: str,
    file: UploadFile = File(...),
    branch: str = Query("main"),
    message: str = Query(""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await require_project_access(slug, user, db, required_role="editor")

    file_data = await file.read()

    if not message:
        message = f"Update {file_path}"

    commit_hash = git_svc.commit_file(
        repo_path=project.git_repo_path,
        file_path=file_path,
        file_data=file_data,
        message=message,
        author_name=user.username,
        author_email=user.email,
        branch=branch,
    )

    if file_path.lower().endswith(".ifc"):
        try:
            from src.workers.queue import enqueue_fragment_generation
            await enqueue_fragment_generation(str(project.id), file_path, commit_hash)
        except Exception as e:
            logger.warning(f"Failed to queue fragment generation: {e}")

    return FileUploadResponse(commit_hash=commit_hash, file_path=file_path, message=message)


@router.delete("/{slug}/files/{file_path:path}")
async def remove_file(
    slug: str,
    file_path: str,
    branch: str = Query("main"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await require_project_access(slug, user, db, required_role="editor")

    commit_hash = git_svc.delete_file(
        repo_path=project.git_repo_path,
        file_path=file_path,
        message=f"Delete {file_path}",
        author_name=user.username,
        author_email=user.email,
        branch=branch,
    )

    if not commit_hash:
        raise HTTPException(status_code=404, detail="File not found")

    return {"commit_hash": commit_hash, "message": f"Deleted {file_path}"}


# --- Git Endpoints ---

@router.get("/{slug}/git/log", response_model=list[CommitResponse])
async def get_log(
    slug: str,
    branch: str = Query("main"),
    limit: int = Query(50, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await require_project_access(slug, user, db)
    commits = git_svc.get_commit_log(project.git_repo_path, branch, limit)
    return [
        CommitResponse(
            hash=c.hash,
            message=c.message,
            author_name=c.author_name,
            author_email=c.author_email,
            timestamp=c.timestamp,
        )
        for c in commits
    ]


@router.get("/{slug}/git/branches")
async def get_branches(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await require_project_access(slug, user, db)
    branches = git_svc.list_branches(project.git_repo_path)
    return {"branches": branches}


@router.post("/{slug}/git/branches")
async def create_new_branch(
    slug: str,
    req: BranchCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await require_project_access(slug, user, db, required_role="editor")
    result = git_svc.create_branch(project.git_repo_path, req.name, req.source)
    if not result:
        raise HTTPException(status_code=400, detail="Source branch not found")
    return result


@router.post("/{slug}/git/branches/{branch_name}/merge")
async def merge_branch(
    slug: str,
    branch_name: str,
    req: MergeRequest,
    target: str = Query("main"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await require_project_access(slug, user, db, required_role="editor")
    result = merge_branches(
        repo_path=project.git_repo_path,
        source_branch=branch_name,
        target_branch=target,
        author_name=user.username,
        author_email=user.email,
        message=req.message,
    )
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/{slug}/git/diff")
async def get_diff(
    slug: str,
    from_commit: str = Query(..., alias="from"),
    to_commit: str = Query(..., alias="to"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await require_project_access(slug, user, db)
    return get_diff_between_commits(project.git_repo_path, from_commit, to_commit)


@router.get("/{slug}/git/diff/semantic")
async def get_semantic_diff(
    slug: str,
    from_commit: str = Query(..., alias="from"),
    to_commit: str = Query(..., alias="to"),
    file_path: str = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await require_project_access(slug, user, db)
    return get_semantic_ifc_diff(project.git_repo_path, from_commit, to_commit, file_path)

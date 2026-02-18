import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.db.database import get_db
from src.projects.models import Project, ProjectMember
from src.projects.service import (
    create_project,
    get_project_by_slug,
    list_projects_for_user,
    update_project,
    delete_project,
    add_project_member,
    check_project_access,
)

router = APIRouter()


# --- Schemas ---

class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    engine: str = "git"
    modules: list[str] | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    engine: str | None = None
    modules: list[str] | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    engine: str
    modules: list[str] | None
    owner_id: uuid.UUID
    created_at: str

    model_config = {"from_attributes": True}


class MemberAdd(BaseModel):
    user_id: uuid.UUID
    role: str = "viewer"


class MemberResponse(BaseModel):
    user_id: uuid.UUID
    role: str

    model_config = {"from_attributes": True}


# --- Helpers ---

async def get_project_or_404(slug: str, db: AsyncSession) -> Project:
    project = await get_project_by_slug(db, slug)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def require_project_access(
    slug: str,
    user: User,
    db: AsyncSession,
    required_role: str | None = None,
) -> Project:
    project = await get_project_or_404(slug, db)
    # Admin users bypass project-level checks
    if user.role == "admin":
        return project
    has_access = await check_project_access(db, project.id, user.id, required_role)
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")
    return project


# --- Endpoints ---

@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    projects = await list_projects_for_user(db, user.id)
    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            slug=p.slug,
            description=p.description,
            engine=p.engine,
            modules=p.modules,
            owner_id=p.owner_id,
            created_at=p.created_at.isoformat(),
        )
        for p in projects
    ]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_new_project(
    req: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await create_project(
        db, req.name, req.description, user.id,
        engine=req.engine, modules=req.modules,
    )
    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        engine=project.engine,
        modules=project.modules,
        owner_id=project.owner_id,
        created_at=project.created_at.isoformat(),
    )


@router.get("/{slug}", response_model=ProjectResponse)
async def get_project(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await require_project_access(slug, user, db)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        engine=project.engine,
        modules=project.modules,
        owner_id=project.owner_id,
        created_at=project.created_at.isoformat(),
    )


@router.put("/{slug}", response_model=ProjectResponse)
async def update_existing_project(
    slug: str,
    req: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await require_project_access(slug, user, db, required_role="admin")
    project = await update_project(
        db, project, req.name, req.description,
        engine=req.engine, modules=req.modules,
    )
    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        engine=project.engine,
        modules=project.modules,
        owner_id=project.owner_id,
        created_at=project.created_at.isoformat(),
    )


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_project(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await require_project_access(slug, user, db, required_role="admin")
    await delete_project(db, project)


@router.post("/{slug}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    slug: str,
    req: MemberAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await require_project_access(slug, user, db, required_role="admin")
    member = await add_project_member(db, project.id, req.user_id, req.role)
    return MemberResponse(user_id=member.user_id, role=member.role)

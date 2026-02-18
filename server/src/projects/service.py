import uuid

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import settings
from src.git.service import init_bare_repo
from src.projects.models import Project, ProjectMember


async def create_project(
    db: AsyncSession, name: str, description: str | None, owner_id: uuid.UUID,
    engine: str = "git", modules: list[str] | None = None,
) -> Project:
    slug = slugify(name)

    # Ensure unique slug
    base_slug = slug
    counter = 1
    while True:
        existing = await db.execute(select(Project).where(Project.slug == slug))
        if not existing.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    git_repo_path = f"{settings.repos_dir}/{slug}.git"
    init_bare_repo(git_repo_path)

    project = Project(
        name=name,
        slug=slug,
        description=description,
        git_repo_path=git_repo_path,
        engine=engine,
        modules=modules,
        owner_id=owner_id,
    )
    db.add(project)

    # Add owner as admin member
    member = ProjectMember(project_id=project.id, user_id=owner_id, role="admin")
    db.add(member)

    await db.commit()
    await db.refresh(project)
    return project


async def get_project_by_slug(db: AsyncSession, slug: str) -> Project | None:
    result = await db.execute(
        select(Project).options(selectinload(Project.members)).where(Project.slug == slug)
    )
    return result.scalar_one_or_none()


async def list_projects_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[Project]:
    result = await db.execute(
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user_id)
        .order_by(Project.created_at.desc())
    )
    return list(result.scalars().all())


async def update_project(
    db: AsyncSession, project: Project, name: str | None = None, description: str | None = None,
    engine: str | None = None, modules: list[str] | None = None,
) -> Project:
    if name is not None:
        project.name = name
    if description is not None:
        project.description = description
    if engine is not None:
        project.engine = engine
    if modules is not None:
        project.modules = modules
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project: Project) -> None:
    await db.delete(project)
    await db.commit()


async def add_project_member(
    db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID, role: str = "viewer"
) -> ProjectMember:
    member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def check_project_access(
    db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID, required_role: str | None = None
) -> bool:
    query = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    )
    result = await db.execute(query)
    member = result.scalar_one_or_none()
    if not member:
        return False
    if required_role:
        role_hierarchy = {"admin": 3, "editor": 2, "viewer": 1}
        return role_hierarchy.get(member.role, 0) >= role_hierarchy.get(required_role, 0)
    return True

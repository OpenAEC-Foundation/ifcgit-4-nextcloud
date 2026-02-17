"""BCF-API 3.0 compliant REST endpoints. Phase 2 implementation."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.middleware import get_current_user
from src.auth.models import User
from src.bcf.models import BcfTopic, BcfViewpoint, BcfComment
from src.db.database import get_db
from src.projects.models import Project

router = APIRouter()


# --- Schemas ---

class TopicCreate(BaseModel):
    title: str
    description: str | None = None
    status: str = "Open"
    type: str | None = None
    priority: str | None = None
    assignee_id: uuid.UUID | None = None


class TopicUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    type: str | None = None
    priority: str | None = None
    assignee_id: uuid.UUID | None = None


class TopicResponse(BaseModel):
    guid: str
    title: str
    description: str | None
    status: str
    type: str | None
    priority: str | None
    author_id: uuid.UUID
    assignee_id: uuid.UUID | None
    created_at: str
    modified_at: str

    model_config = {"from_attributes": True}


class ViewpointCreate(BaseModel):
    camera: dict | None = None
    components: dict | None = None
    clipping_planes: dict | None = None


class CommentCreate(BaseModel):
    body: str
    viewpoint_guid: str | None = None


class CommentResponse(BaseModel):
    guid: str
    body: str
    author_id: uuid.UUID
    viewpoint_id: uuid.UUID | None
    created_at: str

    model_config = {"from_attributes": True}


# --- Helpers ---

async def get_bcf_project(project_id: str, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# --- Endpoints ---

@router.get("/projects/{project_id}/topics", response_model=list[TopicResponse])
async def list_topics(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BcfTopic)
        .where(BcfTopic.project_id == project_id)
        .order_by(BcfTopic.modified_at.desc())
    )
    topics = result.scalars().all()
    return [
        TopicResponse(
            guid=t.guid,
            title=t.title,
            description=t.description,
            status=t.status,
            type=t.type,
            priority=t.priority,
            author_id=t.author_id,
            assignee_id=t.assignee_id,
            created_at=t.created_at.isoformat(),
            modified_at=t.modified_at.isoformat(),
        )
        for t in topics
    ]


@router.post("/projects/{project_id}/topics", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
async def create_topic(
    project_id: uuid.UUID,
    req: TopicCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    topic = BcfTopic(
        project_id=project_id,
        guid=str(uuid.uuid4()),
        title=req.title,
        description=req.description,
        status=req.status,
        type=req.type,
        priority=req.priority,
        assignee_id=req.assignee_id,
        author_id=user.id,
    )
    db.add(topic)
    await db.commit()
    await db.refresh(topic)

    return TopicResponse(
        guid=topic.guid,
        title=topic.title,
        description=topic.description,
        status=topic.status,
        type=topic.type,
        priority=topic.priority,
        author_id=topic.author_id,
        assignee_id=topic.assignee_id,
        created_at=topic.created_at.isoformat(),
        modified_at=topic.modified_at.isoformat(),
    )


@router.get("/projects/{project_id}/topics/{guid}", response_model=TopicResponse)
async def get_topic(
    project_id: uuid.UUID,
    guid: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BcfTopic).where(BcfTopic.project_id == project_id, BcfTopic.guid == guid)
    )
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    return TopicResponse(
        guid=topic.guid,
        title=topic.title,
        description=topic.description,
        status=topic.status,
        type=topic.type,
        priority=topic.priority,
        author_id=topic.author_id,
        assignee_id=topic.assignee_id,
        created_at=topic.created_at.isoformat(),
        modified_at=topic.modified_at.isoformat(),
    )


@router.put("/projects/{project_id}/topics/{guid}", response_model=TopicResponse)
async def update_topic(
    project_id: uuid.UUID,
    guid: str,
    req: TopicUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BcfTopic).where(BcfTopic.project_id == project_id, BcfTopic.guid == guid)
    )
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(topic, field, value)

    await db.commit()
    await db.refresh(topic)

    return TopicResponse(
        guid=topic.guid,
        title=topic.title,
        description=topic.description,
        status=topic.status,
        type=topic.type,
        priority=topic.priority,
        author_id=topic.author_id,
        assignee_id=topic.assignee_id,
        created_at=topic.created_at.isoformat(),
        modified_at=topic.modified_at.isoformat(),
    )


@router.get("/projects/{project_id}/topics/{guid}/comments", response_model=list[CommentResponse])
async def list_comments(
    project_id: uuid.UUID,
    guid: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BcfTopic).where(BcfTopic.project_id == project_id, BcfTopic.guid == guid)
    )
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    result = await db.execute(
        select(BcfComment).where(BcfComment.topic_id == topic.id).order_by(BcfComment.created_at)
    )
    comments = result.scalars().all()
    return [
        CommentResponse(
            guid=c.guid,
            body=c.body,
            author_id=c.author_id,
            viewpoint_id=c.viewpoint_id,
            created_at=c.created_at.isoformat(),
        )
        for c in comments
    ]


@router.post("/projects/{project_id}/topics/{guid}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    project_id: uuid.UUID,
    guid: str,
    req: CommentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BcfTopic).where(BcfTopic.project_id == project_id, BcfTopic.guid == guid)
    )
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    comment = BcfComment(
        topic_id=topic.id,
        guid=str(uuid.uuid4()),
        body=req.body,
        author_id=user.id,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return CommentResponse(
        guid=comment.guid,
        body=comment.body,
        author_id=comment.author_id,
        viewpoint_id=comment.viewpoint_id,
        created_at=comment.created_at.isoformat(),
    )

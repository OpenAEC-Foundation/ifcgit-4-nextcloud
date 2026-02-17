import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class ClashSet(Base):
    __tablename__ = "clash_sets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_a_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    model_b_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tolerance: Mapped[float] = mapped_column(Float, default=0.01)
    filters_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClashResult(Base):
    __tablename__ = "clash_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clash_set_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clash_sets.id"), nullable=False)
    commit_hash: Mapped[str | None] = mapped_column(String(40), nullable=True)
    total_clashes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    results_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

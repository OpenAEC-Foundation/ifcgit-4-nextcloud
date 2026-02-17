import uuid
from datetime import datetime

from sqlalchemy import String, BigInteger, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class FragmentCache(Base):
    __tablename__ = "fragment_cache"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    commit_hash: Mapped[str] = mapped_column(String(40), nullable=False)
    fragment_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("project_id", "file_path", "commit_hash", name="uq_fragment_cache"),
    )

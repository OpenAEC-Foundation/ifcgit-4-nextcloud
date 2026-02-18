"""Add engine and modules fields to projects

Revision ID: 002_project_engine
Revises: 001_integrations
Create Date: 2026-02-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_project_engine"
down_revision: Union[str, None] = "001_integrations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("engine", sa.String(50), server_default="git", nullable=False))
    op.add_column("projects", sa.Column("modules", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "modules")
    op.drop_column("projects", "engine")

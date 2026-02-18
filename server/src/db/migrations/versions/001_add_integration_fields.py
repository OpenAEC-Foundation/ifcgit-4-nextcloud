"""Add ERPNext and Nextcloud integration fields to users

Revision ID: 001_integrations
Revises:
Create Date: 2026-02-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_integrations"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("erpnext_url", sa.String(512), nullable=True))
    op.add_column("users", sa.Column("erpnext_api_key", sa.String(512), nullable=True))
    op.add_column("users", sa.Column("erpnext_api_secret", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("nextcloud_url", sa.String(512), nullable=True))
    op.add_column("users", sa.Column("nextcloud_username", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("nextcloud_password", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "nextcloud_password")
    op.drop_column("users", "nextcloud_username")
    op.drop_column("users", "nextcloud_url")
    op.drop_column("users", "erpnext_api_secret")
    op.drop_column("users", "erpnext_api_key")
    op.drop_column("users", "erpnext_url")

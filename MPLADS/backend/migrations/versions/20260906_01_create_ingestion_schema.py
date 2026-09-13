"""Create staged and canonical ingestion schema.

Revision ID: 20260906_01
Revises:
Create Date: 2026-09-06
"""
from alembic import op

from app.db.base import Base
import app.models  # noqa: F401

revision = "20260906_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(op.get_bind())

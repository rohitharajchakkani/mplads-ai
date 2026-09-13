"""Add release lifecycle and financial year indexing.

Revision ID: 20260906_02
Revises: 20260906_01
Create Date: 2026-09-06
"""
from alembic import op
import sqlalchemy as sa

revision = "20260906_02"
down_revision = "20260906_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dataset_releases",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("batch_id", sa.String(length=64), sa.ForeignKey("ingestion_batches.id"), nullable=False, unique=True),
        sa.Column("release_version", sa.String(length=96), nullable=False, unique=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("approved_by", sa.String(length=100), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validation_version", sa.String(length=64), nullable=False),
        sa.Column("approval_notes", sa.Text(), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_dataset_releases_status", "dataset_releases", ["status"])
    op.create_index("ix_dataset_releases_batch_id", "dataset_releases", ["batch_id"])
    op.execute("CREATE UNIQUE INDEX uq_one_active_dataset_release ON dataset_releases(status) WHERE status = 'ACTIVE'")
    op.create_table(
        "dataset_lifecycle_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("release_id", sa.String(length=64), sa.ForeignKey("dataset_releases.id"), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_dataset_lifecycle_events_release_id", "dataset_lifecycle_events", ["release_id"])
    op.create_index("ix_dataset_lifecycle_events_event_type", "dataset_lifecycle_events", ["event_type"])
    with op.batch_alter_table("works") as batch:
        batch.add_column(sa.Column("financial_year", sa.String(length=16), nullable=True))
        batch.create_index("ix_works_financial_year", ["financial_year"])


def downgrade() -> None:
    with op.batch_alter_table("works") as batch:
        batch.drop_index("ix_works_financial_year")
        batch.drop_column("financial_year")
    op.drop_table("dataset_lifecycle_events")
    op.drop_table("dataset_releases")

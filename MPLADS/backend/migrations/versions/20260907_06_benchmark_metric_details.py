"""retain per-entity benchmark calculation details

Revision ID: 20260907_06
Revises: 20260907_05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260907_06"
down_revision = "20260907_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("benchmark_results", sa.Column("metric_details", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("benchmark_results", "metric_details")

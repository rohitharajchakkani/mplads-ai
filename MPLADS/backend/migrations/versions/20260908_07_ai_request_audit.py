"""Add read-only Ask AI audit records.

Revision ID: 20260908_07
Revises: 20260907_06
"""
from alembic import op
import sqlalchemy as sa

revision = "20260908_07"
down_revision = "20260907_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("ai_request_audits", sa.Column("request_id", sa.String(80), primary_key=True), sa.Column("actor", sa.String(160)), sa.Column("role", sa.String(32), nullable=False), sa.Column("scope_json", sa.JSON(), nullable=False), sa.Column("intent", sa.String(40), nullable=False), sa.Column("tool_name", sa.String(80)), sa.Column("result_metadata", sa.JSON(), nullable=False), sa.Column("response_status", sa.String(24), nullable=False), sa.Column("dataset_version", sa.String(96)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    for name in ("actor", "role", "intent", "tool_name", "response_status", "dataset_version", "created_at"):
        op.create_index(f"ix_ai_request_audits_{name}", "ai_request_audits", [name])


def downgrade() -> None:
    op.drop_table("ai_request_audits")

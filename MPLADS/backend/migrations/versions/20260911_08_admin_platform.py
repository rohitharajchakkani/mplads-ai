"""Add real platform-administration records and append-only admin audit events.

Revision ID: 20260911_08
Revises: 20260908_07
"""
from alembic import op
import sqlalchemy as sa


revision = "20260911_08"
down_revision = "20260908_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authorized_users",
        sa.Column("user_id", sa.String(80), primary_key=True),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("designation", sa.String(160)),
        sa.Column("office", sa.String(240)),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("state_scope", sa.String(150)),
        sa.Column("district_scope", sa.String(500)),
        sa.Column("mp_scope", sa.String(300)),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("source_access_request_id", sa.String(80), unique=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed_by", sa.String(160), nullable=False),
        sa.Column("disabled_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "access_requests",
        sa.Column("request_id", sa.String(80), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("designation", sa.String(160)),
        sa.Column("office", sa.String(240)),
        sa.Column("state_name", sa.String(150)),
        sa.Column("district_or_ida", sa.String(500)),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decided_by", sa.String(160)),
        sa.Column("decision_note", sa.Text()),
        sa.Column("approved_user_id", sa.String(80), sa.ForeignKey("authorized_users.user_id"), unique=True),
    )
    op.create_table(
        "admin_audit_events",
        sa.Column("event_id", sa.String(80), primary_key=True),
        sa.Column("actor", sa.String(160), nullable=False),
        sa.Column("event_type", sa.String(48), nullable=False),
        sa.Column("entity_type", sa.String(48), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
    )
    for table, columns in {
        "authorized_users": ["display_name", "role", "state_scope", "district_scope", "mp_scope", "status", "source_access_request_id", "created_at", "updated_at", "changed_by"],
        "access_requests": ["name", "state_name", "district_or_ida", "status", "created_at", "decided_at", "decided_by", "approved_user_id"],
        "admin_audit_events": ["actor", "event_type", "entity_type", "entity_id", "occurred_at"],
    }.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    op.drop_table("admin_audit_events")
    op.drop_table("access_requests")
    op.drop_table("authorized_users")

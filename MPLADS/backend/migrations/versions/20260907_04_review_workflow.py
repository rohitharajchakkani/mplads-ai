"""Add persisted human review cases, immutable evidence, and in-app notifications.

Revision ID: 20260907_04
Revises: 20260907_03
"""
from alembic import op
import sqlalchemy as sa

revision = "20260907_04"
down_revision = "20260907_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("review_cases", sa.Column("case_id", sa.String(80), primary_key=True), sa.Column("source_alert_id", sa.String(80), sa.ForeignKey("analytical_alerts.alert_id")), sa.Column("source_signal_id", sa.String(80), sa.ForeignKey("monitoring_signals.signal_id")), sa.Column("canonical_work_key", sa.String(110), sa.ForeignKey("works.canonical_work_key")), sa.Column("house", sa.String(20)), sa.Column("state_name", sa.String(150)), sa.Column("district_or_ida", sa.String(500)), sa.Column("mp_source_name", sa.String(300)), sa.Column("status", sa.String(24), nullable=False), sa.Column("priority", sa.String(16), nullable=False), sa.Column("assignee", sa.String(160)), sa.Column("dataset_version", sa.String(96), nullable=False), sa.Column("evidence_snapshot_id", sa.String(80), nullable=False, unique=True), sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.Column("created_by", sa.String(160), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("closed_at", sa.DateTime(timezone=True)))
    op.create_table("review_case_evidence_snapshots", sa.Column("snapshot_id", sa.String(80), primary_key=True), sa.Column("case_id", sa.String(80), sa.ForeignKey("review_cases.case_id"), nullable=False, unique=True), sa.Column("dataset_version", sa.String(96), nullable=False), sa.Column("analytics_run_id", sa.String(64)), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("content_hash", sa.String(64), nullable=False, unique=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("review_case_events", sa.Column("event_id", sa.String(80), primary_key=True), sa.Column("case_id", sa.String(80), sa.ForeignKey("review_cases.case_id"), nullable=False), sa.Column("actor", sa.String(160), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False), sa.Column("action", sa.String(32), nullable=False), sa.Column("metadata_json", sa.JSON(), nullable=False), sa.Column("comment", sa.Text()))
    op.create_table("review_notifications", sa.Column("notification_id", sa.String(80), primary_key=True), sa.Column("event_id", sa.String(80), sa.ForeignKey("review_case_events.event_id"), nullable=False), sa.Column("case_id", sa.String(80), sa.ForeignKey("review_cases.case_id"), nullable=False), sa.Column("recipient", sa.String(160), nullable=False), sa.Column("state", sa.String(16), nullable=False, server_default="UNREAD"), sa.Column("message", sa.String(500), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("read_at", sa.DateTime(timezone=True)), sa.Column("acknowledged_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("event_id", "recipient", name="uq_review_notification_event_recipient"))
    op.create_table("review_escalations", sa.Column("escalation_id", sa.String(80), primary_key=True), sa.Column("case_id", sa.String(80), sa.ForeignKey("review_cases.case_id"), nullable=False), sa.Column("reason", sa.Text(), nullable=False), sa.Column("requested_by", sa.String(160), nullable=False), sa.Column("status", sa.String(24), nullable=False, server_default="OPEN"), sa.Column("priority", sa.String(16), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    for table, columns in {"review_cases": ["canonical_work_key", "status", "priority", "assignee", "house", "state_name", "district_or_ida", "mp_source_name", "created_at"], "review_case_evidence_snapshots": ["case_id", "dataset_version", "analytics_run_id", "content_hash", "created_at"], "review_case_events": ["case_id", "actor", "occurred_at", "action"], "review_notifications": ["event_id", "case_id", "recipient", "state", "created_at"], "review_escalations": ["case_id", "requested_by", "status", "priority", "created_at"]}.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    op.drop_table("review_escalations")
    op.drop_table("review_notifications")
    op.drop_table("review_case_events")
    op.drop_table("review_case_evidence_snapshots")
    op.drop_table("review_cases")

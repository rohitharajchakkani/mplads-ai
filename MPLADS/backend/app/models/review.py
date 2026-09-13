"""Immutable evidence and auditable human-review workflow persistence."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReviewCaseEvidenceSnapshot(Base):
    __tablename__ = "review_case_evidence_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(80), ForeignKey("review_cases.case_id"), unique=True, index=True)
    dataset_version: Mapped[str] = mapped_column(String(96), index=True)
    analytics_run_id: Mapped[str | None] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ReviewCase(Base):
    __tablename__ = "review_cases"

    case_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    source_alert_id: Mapped[str | None] = mapped_column(String(80), ForeignKey("analytical_alerts.alert_id"), index=True)
    source_signal_id: Mapped[str | None] = mapped_column(String(80), ForeignKey("monitoring_signals.signal_id"), index=True)
    canonical_work_key: Mapped[str | None] = mapped_column(String(110), ForeignKey("works.canonical_work_key"), index=True)
    house: Mapped[str | None] = mapped_column(String(20), index=True)
    state_name: Mapped[str | None] = mapped_column(String(150), index=True)
    district_or_ida: Mapped[str | None] = mapped_column(String(500), index=True)
    mp_source_name: Mapped[str | None] = mapped_column(String(300), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    priority: Mapped[str] = mapped_column(String(16), index=True)
    assignee: Mapped[str | None] = mapped_column(String(160), index=True)
    dataset_version: Mapped[str] = mapped_column(String(96), index=True)
    evidence_snapshot_id: Mapped[str] = mapped_column(String(80), ForeignKey("review_case_evidence_snapshots.snapshot_id"), unique=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[str] = mapped_column(String(160), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class ReviewCaseEvent(Base):
    __tablename__ = "review_case_events"

    event_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(80), ForeignKey("review_cases.case_id"), index=True)
    actor: Mapped[str] = mapped_column(String(160), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    action: Mapped[str] = mapped_column(String(32), index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    comment: Mapped[str | None] = mapped_column(Text)


class ReviewNotification(Base):
    __tablename__ = "review_notifications"
    __table_args__ = (UniqueConstraint("event_id", "recipient", name="uq_review_notification_event_recipient"),)

    notification_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(80), ForeignKey("review_case_events.event_id"), index=True)
    case_id: Mapped[str] = mapped_column(String(80), ForeignKey("review_cases.case_id"), index=True)
    recipient: Mapped[str] = mapped_column(String(160), index=True)
    state: Mapped[str] = mapped_column(String(16), index=True, default="UNREAD")
    message: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewEscalation(Base):
    __tablename__ = "review_escalations"

    escalation_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(80), ForeignKey("review_cases.case_id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    requested_by: Mapped[str] = mapped_column(String(160), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True, default="OPEN")
    priority: Mapped[str] = mapped_column(String(16), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

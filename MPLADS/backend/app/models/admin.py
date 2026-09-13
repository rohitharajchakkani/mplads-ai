"""Persisted platform-administration records; never MPLADS source facts."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccessRequest(Base):
    """A real request awaiting a platform-administrator decision."""

    __tablename__ = "access_requests"

    request_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    designation: Mapped[str | None] = mapped_column(String(160))
    office: Mapped[str | None] = mapped_column(String(240))
    state_name: Mapped[str | None] = mapped_column(String(150), index=True)
    district_or_ida: Mapped[str | None] = mapped_column(String(500), index=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), index=True, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    decided_by: Mapped[str | None] = mapped_column(String(160), index=True)
    decision_note: Mapped[str | None] = mapped_column(Text)
    approved_user_id: Mapped[str | None] = mapped_column(
        String(80), ForeignKey("authorized_users.user_id"), unique=True, index=True
    )


class AuthorizedUser(Base):
    """An approved platform user and the exact scope assigned by an administrator."""

    __tablename__ = "authorized_users"

    user_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(160), index=True)
    designation: Mapped[str | None] = mapped_column(String(160))
    office: Mapped[str | None] = mapped_column(String(240))
    role: Mapped[str] = mapped_column(String(32), index=True)
    state_scope: Mapped[str | None] = mapped_column(String(150), index=True)
    district_scope: Mapped[str | None] = mapped_column(String(500), index=True)
    mp_scope: Mapped[str | None] = mapped_column(String(300), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True, default="ACTIVE")
    source_access_request_id: Mapped[str | None] = mapped_column(
        String(80), ForeignKey("access_requests.request_id"), unique=True, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    changed_by: Mapped[str] = mapped_column(String(160), index=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdminAuditEvent(Base):
    """Append-only record of consequential platform-administration actions."""

    __tablename__ = "admin_audit_events"

    event_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    actor: Mapped[str] = mapped_column(String(160), index=True)
    event_type: Mapped[str] = mapped_column(String(48), index=True)
    entity_type: Mapped[str] = mapped_column(String(48), index=True)
    entity_id: Mapped[str] = mapped_column(String(100), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON)

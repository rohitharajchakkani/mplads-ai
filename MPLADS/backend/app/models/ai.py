"""Privacy-minimized audit records for read-only Ask AI requests."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AiRequestAudit(Base):
    __tablename__ = "ai_request_audits"
    request_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    actor: Mapped[str | None] = mapped_column(String(160), index=True)
    role: Mapped[str] = mapped_column(String(32), index=True)
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    intent: Mapped[str] = mapped_column(String(40), index=True)
    tool_name: Mapped[str | None] = mapped_column(String(80), index=True)
    result_metadata: Mapped[dict[str, Any]] = mapped_column(JSON)
    response_status: Mapped[str] = mapped_column(String(24), index=True)
    dataset_version: Mapped[str | None] = mapped_column(String(96), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

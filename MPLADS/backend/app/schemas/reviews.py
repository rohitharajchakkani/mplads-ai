from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.intelligence import ProtectedProvenance


class CaseCreateRequest(BaseModel):
    alert_id: str | None = None
    signal_id: str | None = None


class CaseActionRequest(BaseModel):
    version: int = Field(ge=1)
    assignee: str | None = Field(default=None, max_length=160)
    comment: str | None = Field(default=None, max_length=4000)
    reason: str | None = Field(default=None, max_length=4000)
    resolution_type: str | None = None
    resolution_note: str | None = Field(default=None, max_length=4000)


class ReviewCaseItem(BaseModel):
    case_id: str
    source_alert_id: str | None
    source_signal_id: str | None
    canonical_work_key: str | None
    house: str | None
    state_name: str | None
    district_or_ida: str | None
    mp_source_name: str | None
    status: str
    priority: str
    assignee: str | None
    dataset_version: str
    version: int
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None


class ReviewEventResponse(BaseModel):
    event_id: str
    actor: str
    occurred_at: datetime
    action: str
    metadata: dict[str, Any]
    comment: str | None


class ReviewCaseDetail(ReviewCaseItem):
    evidence_snapshot_id: str
    evidence_snapshot: dict[str, Any]
    evidence_hash: str
    events: list[ReviewEventResponse]
    provenance: ProtectedProvenance


class ReviewPage(BaseModel):
    items: list[ReviewCaseItem]
    pagination: dict[str, int]
    provenance: ProtectedProvenance


class ReviewSummary(BaseModel):
    by_status: dict[str, int]
    active_escalations: int
    provenance: ProtectedProvenance


class NotificationResponse(BaseModel):
    notification_id: str
    case_id: str
    event_id: str
    recipient: str
    state: str
    message: str
    created_at: datetime

"""Strict contracts for the protected administration surface."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


AdminRole = Literal[
    "MP",
    "DISTRICT_AUTHORITY",
    "STATE_NODAL_AUTHORITY",
    "MINISTRY",
    "PLATFORM_ADMINISTRATOR",
]


class ScopeAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: AdminRole
    state_scope: str | None = Field(default=None, max_length=150)
    district_scope: str | None = Field(default=None, max_length=500)
    mp_scope: str | None = Field(default=None, max_length=300)


class AccessRequestDecision(ScopeAssignment):
    confirmation: Literal["APPROVE"]
    decision_note: str | None = Field(default=None, max_length=1000)


class AccessRequestRejection(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    confirmation: Literal["REJECT"]
    decision_note: str = Field(min_length=1, max_length=1000)


class UserAccessUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: AdminRole | None = None
    state_scope: str | None = Field(default=None, max_length=150)
    district_scope: str | None = Field(default=None, max_length=500)
    mp_scope: str | None = Field(default=None, max_length=300)
    expected_version: int = Field(ge=1)
    confirmation: Literal["UPDATE_ACCESS"]


class UserStatusAction(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    expected_version: int = Field(ge=1)
    confirmation: Literal["DISABLE", "REVOKE"]
    reason: str = Field(min_length=1, max_length=1000)


class DatasetActionConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    confirmation: Literal["APPROVE", "PROMOTE", "ROLLBACK"]
    notes: str | None = Field(default=None, max_length=1000)


class AccessRequestItem(BaseModel):
    request_id: str
    name: str
    designation: str | None
    office: str | None
    state_name: str | None
    district_or_ida: str | None
    reason: str
    status: str
    created_at: datetime
    decided_at: datetime | None
    decided_by: str | None
    decision_note: str | None
    approved_user_id: str | None


class AuthorizedUserItem(BaseModel):
    user_id: str
    display_name: str
    designation: str | None
    office: str | None
    role: str
    state_scope: str | None
    district_scope: str | None
    mp_scope: str | None
    status: str
    source_access_request_id: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    changed_by: str
    disabled_at: datetime | None


class AdminPage(BaseModel):
    items: list[Any]
    pagination: dict[str, int]


class DatasetAsset(BaseModel):
    dataset_type: str
    house: str
    status: str
    source_filename: str
    source_sheet: str
    source_checksum: str
    source_row_count: int
    staged_row_count: int
    valid_row_count: int
    warning_row_count: int
    rejected_row_count: int


class DatasetReleaseItem(BaseModel):
    release_id: str
    batch_id: str
    release_version: str
    status: str
    approved_by: str
    approved_at: datetime
    validation_version: str
    approval_notes: str | None
    promoted_at: datetime | None
    rolled_back_at: datetime | None
    datasets: list[DatasetAsset]
    lifecycle_events: list[dict[str, Any]]


class AdminDataQuality(BaseModel):
    dataset_version: str
    generated_at: datetime
    metrics: dict[str, int | bool]


class AdminSystemStatus(BaseModel):
    api_status: str
    database_status: str
    active_dataset_status: str
    active_release_version: str | None
    migration_version: str | None
    application_version: str
    app_environment: str
    cors_status: str
    gemini_status: str
    gemini_model: str | None
    latest_analytics_run: dict[str, Any] | None
    checked_at: datetime


class SafeConfigurationStatus(BaseModel):
    database: str
    gemini: str
    cors: str
    active_dataset: str
    environment: str
    migration: str
    checked_at: datetime

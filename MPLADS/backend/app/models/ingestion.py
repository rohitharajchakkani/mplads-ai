from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IngestionBatch(Base):
    __tablename__ = "ingestion_batches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_set_fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    ingestion_version: Mapped[str] = mapped_column(String(32))
    application_version: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24), index=True)
    operator: Mapped[str] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_summary: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class DatasetRelease(Base):
    """An audited, explicitly approved dataset batch eligible for analytical use."""

    __tablename__ = "dataset_releases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("ingestion_batches.id"), unique=True, index=True)
    release_version: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    approved_by: Mapped[str] = mapped_column(String(100))
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    validation_version: Mapped[str] = mapped_column(String(64))
    approval_notes: Mapped[str | None] = mapped_column(Text)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DatasetLifecycleEvent(Base):
    __tablename__ = "dataset_lifecycle_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    release_id: Mapped[str] = mapped_column(ForeignKey("dataset_releases.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    actor: Mapped[str] = mapped_column(String(100))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (UniqueConstraint("dataset_type", "house", "version", name="uq_dataset_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("ingestion_batches.id"), index=True)
    dataset_type: Mapped[str] = mapped_column(String(32), index=True)
    house: Mapped[str] = mapped_column(String(20), index=True)
    version: Mapped[str] = mapped_column(String(64))
    source_filename: Mapped[str] = mapped_column(String(300))
    source_sheet: Mapped[str] = mapped_column(String(100))
    source_checksum: Mapped[str] = mapped_column(String(64), index=True)
    source_row_count: Mapped[int] = mapped_column(Integer)
    staged_row_count: Mapped[int] = mapped_column(Integer, default=0)
    valid_row_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_row_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_row_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), index=True)


class ValidationFinding(Base):
    __tablename__ = "validation_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("ingestion_batches.id"), index=True)
    dataset_version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    source_row_number: Mapped[int] = mapped_column(Integer, index=True)
    severity: Mapped[str] = mapped_column(String(10), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    field_name: Mapped[str | None] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)


class StagingRecord(Base):
    """Shared provenance and validation fields; each domain has its own table."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("ingestion_batches.id"), index=True)
    dataset_version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    source_row_number: Mapped[int] = mapped_column(Integer, index=True)
    source_sequence: Mapped[str | None] = mapped_column(String(64))
    house: Mapped[str] = mapped_column(String(20), index=True)
    source_values: Mapped[dict[str, Any]] = mapped_column(JSON)
    normalized_candidates: Mapped[dict[str, Any]] = mapped_column(JSON)
    validation_status: Mapped[str] = mapped_column(String(32), index=True)
    work_reference_status: Mapped[str | None] = mapped_column(String(48), index=True)


class StagingAllocatedLimit(StagingRecord):
    __tablename__ = "staging_allocated_limits"
    state_name: Mapped[str | None] = mapped_column(String(150), index=True)
    mp_source_name: Mapped[str | None] = mapped_column(String(300), index=True)
    constituency_name: Mapped[str | None] = mapped_column(String(300))
    membership_type: Mapped[str | None] = mapped_column(String(100))
    allocated_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))


class StagingCalamity(StagingRecord):
    __tablename__ = "staging_calamity"
    calamity_type: Mapped[str | None] = mapped_column(String(150))
    calamity_name: Mapped[str | None] = mapped_column(Text)
    mp_source_name: Mapped[str | None] = mapped_column(String(300), index=True)
    consent_date_raw: Mapped[str | None] = mapped_column(String(64))
    consent_date: Mapped[str | None] = mapped_column(String(10))
    consent_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))


class StagingRecommendedWork(StagingRecord):
    __tablename__ = "staging_recommended_works"
    work_category_source: Mapped[str | None] = mapped_column(String(200))
    work_source_label: Mapped[str | None] = mapped_column(Text)
    normalized_work_id: Mapped[str | None] = mapped_column(String(80), index=True)
    state_name: Mapped[str | None] = mapped_column(String(150), index=True)
    district_or_ida: Mapped[str | None] = mapped_column(String(500))
    mp_source_name: Mapped[str | None] = mapped_column(String(300), index=True)
    constituency_name: Mapped[str | None] = mapped_column(String(300))
    membership_type: Mapped[str | None] = mapped_column(String(100))
    work_description: Mapped[str | None] = mapped_column(Text)
    recommended_date_raw: Mapped[str | None] = mapped_column(String(64))
    recommended_date: Mapped[str | None] = mapped_column(String(10))
    recommended_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    sanction_date_raw: Mapped[str | None] = mapped_column(String(64))
    sanction_date: Mapped[str | None] = mapped_column(String(10))


class StagingSanctionedWork(StagingRecord):
    __tablename__ = "staging_sanctioned_works"
    work_category_source: Mapped[str | None] = mapped_column(String(200))
    work_source_label: Mapped[str | None] = mapped_column(Text)
    normalized_work_id: Mapped[str | None] = mapped_column(String(80), index=True)
    state_name: Mapped[str | None] = mapped_column(String(150), index=True)
    district_or_ida: Mapped[str | None] = mapped_column(String(500))
    mp_source_name: Mapped[str | None] = mapped_column(String(300), index=True)
    constituency_name: Mapped[str | None] = mapped_column(String(300))
    membership_type: Mapped[str | None] = mapped_column(String(100))
    work_description: Mapped[str | None] = mapped_column(Text)
    recommended_date_raw: Mapped[str | None] = mapped_column(String(64))
    recommended_date: Mapped[str | None] = mapped_column(String(10))
    sanction_date_raw: Mapped[str | None] = mapped_column(String(64))
    sanction_date: Mapped[str | None] = mapped_column(String(10))
    sanction_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    work_status_source: Mapped[str | None] = mapped_column(String(200))


class StagingExpenditure(StagingRecord):
    __tablename__ = "staging_expenditure"
    work_source_label: Mapped[str | None] = mapped_column(Text)
    normalized_work_id: Mapped[str | None] = mapped_column(String(80), index=True)
    state_name: Mapped[str | None] = mapped_column(String(150), index=True)
    district_or_ida: Mapped[str | None] = mapped_column(String(500))
    mp_source_name: Mapped[str | None] = mapped_column(String(300), index=True)
    constituency_name: Mapped[str | None] = mapped_column(String(300))
    membership_type: Mapped[str | None] = mapped_column(String(100))
    expenditure_date_raw: Mapped[str | None] = mapped_column(String(64))
    expenditure_date: Mapped[str | None] = mapped_column(String(10))
    vendor_name: Mapped[str | None] = mapped_column(String(500))
    payment_status_source: Mapped[str | None] = mapped_column(String(200))
    disbursed_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))


class StagingCompletedWork(StagingRecord):
    __tablename__ = "staging_completed_works"
    work_category_source: Mapped[str | None] = mapped_column(String(200))
    work_source_label: Mapped[str | None] = mapped_column(Text)
    normalized_work_id: Mapped[str | None] = mapped_column(String(80), index=True)
    state_name: Mapped[str | None] = mapped_column(String(150), index=True)
    district_or_ida: Mapped[str | None] = mapped_column(String(500))
    work_description: Mapped[str | None] = mapped_column(Text)
    mp_source_name: Mapped[str | None] = mapped_column(String(300), index=True)
    constituency_name: Mapped[str | None] = mapped_column(String(300))
    membership_type: Mapped[str | None] = mapped_column(String(100))
    image_availability_source: Mapped[str | None] = mapped_column(String(100))
    completion_date_raw: Mapped[str | None] = mapped_column(String(64))
    completion_date: Mapped[str | None] = mapped_column(String(10))
    completed_reported_disbursed_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))

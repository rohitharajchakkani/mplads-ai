from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CanonicalWork(Base):
    __tablename__ = "works"

    canonical_work_key: Mapped[str] = mapped_column(String(110), primary_key=True)
    house: Mapped[str] = mapped_column(String(20), index=True)
    normalized_work_id: Mapped[str] = mapped_column(String(80), index=True)
    financial_year: Mapped[str | None] = mapped_column(String(16), index=True)
    state_name: Mapped[str | None] = mapped_column(String(150), index=True)
    district_or_ida: Mapped[str | None] = mapped_column(String(500))
    mp_source_name: Mapped[str | None] = mapped_column(String(300), index=True)
    constituency_name: Mapped[str | None] = mapped_column(String(300))
    membership_type: Mapped[str | None] = mapped_column(String(100))
    work_category_source: Mapped[str | None] = mapped_column(String(200))
    work_description: Mapped[str | None] = mapped_column(Text)
    first_dataset_version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"))
    __table_args__ = (UniqueConstraint("house", "normalized_work_id", name="uq_work_house_source_id"),)


class CanonicalLifecycleRecord(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    staging_id: Mapped[int] = mapped_column(unique=True, index=True)
    canonical_work_key: Mapped[str | None] = mapped_column(ForeignKey("works.canonical_work_key"), index=True)
    house: Mapped[str] = mapped_column(String(20), index=True)
    source_dataset_version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"), index=True)


class RecommendedWorkRecord(CanonicalLifecycleRecord):
    __tablename__ = "recommended_work_records"
    recommended_date: Mapped[str | None] = mapped_column(String(10))
    recommended_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    work_reference_status: Mapped[str] = mapped_column(String(48), index=True)


class SanctionedWorkRecord(CanonicalLifecycleRecord):
    __tablename__ = "sanctioned_work_records"
    recommended_date: Mapped[str | None] = mapped_column(String(10))
    sanction_date: Mapped[str | None] = mapped_column(String(10))
    sanction_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    work_status_source: Mapped[str | None] = mapped_column(String(200))
    work_reference_status: Mapped[str] = mapped_column(String(48), index=True)


class CompletedWorkRecord(CanonicalLifecycleRecord):
    __tablename__ = "completed_work_records"
    completion_date: Mapped[str | None] = mapped_column(String(10))
    completed_reported_disbursed_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    work_reference_status: Mapped[str] = mapped_column(String(48), index=True)


class ExpenditureTransaction(CanonicalLifecycleRecord):
    __tablename__ = "expenditure_transactions"
    expenditure_date: Mapped[str | None] = mapped_column(String(10), index=True)
    vendor_name: Mapped[str | None] = mapped_column(String(500))
    payment_status_source: Mapped[str | None] = mapped_column(String(200))
    disbursed_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    work_reference_status: Mapped[str] = mapped_column(String(48), index=True)


class AllocatedLimitRecord(Base):
    __tablename__ = "allocated_limit_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    staging_id: Mapped[int] = mapped_column(unique=True, index=True)
    house: Mapped[str] = mapped_column(String(20), index=True)
    source_dataset_version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    state_name: Mapped[str | None] = mapped_column(String(150), index=True)
    mp_source_name: Mapped[str | None] = mapped_column(String(300), index=True)
    constituency_name: Mapped[str | None] = mapped_column(String(300))
    membership_type: Mapped[str | None] = mapped_column(String(100))
    allocated_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))


class CalamityRecord(Base):
    __tablename__ = "calamity_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    staging_id: Mapped[int] = mapped_column(unique=True, index=True)
    house: Mapped[str] = mapped_column(String(20), index=True)
    source_dataset_version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    calamity_type: Mapped[str | None] = mapped_column(String(150))
    calamity_name: Mapped[str | None] = mapped_column(Text)
    mp_source_name: Mapped[str | None] = mapped_column(String(300), index=True)
    consent_date: Mapped[str | None] = mapped_column(String(10))
    consent_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))

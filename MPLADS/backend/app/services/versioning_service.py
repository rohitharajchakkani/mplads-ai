"""Explicit dataset approval, promotion, active-version resolution, and rollback."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import CanonicalWork, DatasetLifecycleEvent, DatasetRelease, DatasetVersion, IngestionBatch

EXPECTED_DOMAINS = {"ALLOCATED_LIMIT", "CALAMITY", "WORKS_RECOMMENDED", "WORKS_SANCTIONED", "EXPENDITURE", "WORKS_COMPLETED"}
FINANCIAL_YEAR_PATTERN = re.compile(r"WS/MP\d+/(\d{4}-\d{4})/\d+", re.IGNORECASE)


class LifecycleError(RuntimeError):
    pass


@dataclass(frozen=True)
class ActiveDatasetScope:
    release_id: str
    release_version: str
    batch_id: str
    dataset_version_ids: tuple[int, ...]


def resolve_active_scope(session: Session) -> ActiveDatasetScope:
    releases = session.scalars(select(DatasetRelease).where(DatasetRelease.status == "ACTIVE")).all()
    if not releases:
        raise LifecycleError("No ACTIVE dataset release exists.")
    if len(releases) != 1:
        raise LifecycleError("Dataset release integrity failure: more than one ACTIVE release exists.")
    release = releases[0]
    versions = tuple(session.scalars(select(DatasetVersion.id).where(DatasetVersion.batch_id == release.batch_id)).all())
    if len(versions) != 12:
        raise LifecycleError("ACTIVE release does not contain all twelve required dataset versions.")
    return ActiveDatasetScope(release.id, release.release_version, release.batch_id, versions)


def _event(session: Session, release_id: str, event_type: str, actor: str, notes: str | None = None) -> None:
    session.add(DatasetLifecycleEvent(release_id=release_id, event_type=event_type, actor=actor, occurred_at=datetime.now(UTC), notes=notes))


def _backfill_financial_years(session: Session, batch_id: str) -> None:
    for work in session.scalars(select(CanonicalWork).join(DatasetVersion, CanonicalWork.first_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == batch_id, CanonicalWork.financial_year.is_(None))).yield_per(2000):
        match = FINANCIAL_YEAR_PATTERN.search(work.normalized_work_id)
        work.financial_year = match.group(1) if match else None


def verify_approval_gate(session: Session, batch_id: str) -> list[str]:
    batch = session.get(IngestionBatch, batch_id)
    if batch is None:
        return ["Batch does not exist."]
    if batch.status not in {"VALIDATED", "APPROVED", "ACTIVE"}:
        return [f"Batch is {batch.status}, not VALIDATED, APPROVED, or ACTIVE."]
    versions = session.scalars(select(DatasetVersion).where(DatasetVersion.batch_id == batch_id)).all()
    errors: list[str] = []
    if len(versions) != 12:
        errors.append(f"Expected 12 dataset versions; found {len(versions)}.")
    for house in ("LOK_SABHA", "RAJYA_SABHA"):
        domains = {version.dataset_type for version in versions if version.house == house}
        if domains != EXPECTED_DOMAINS:
            errors.append(f"{house} domains do not match the required intake manifest.")
    if any(version.status not in {"VALIDATED", "APPROVED", "ACTIVE"} for version in versions):
        errors.append("Not every dataset version completed validation.")
    if any(version.source_row_count != version.staged_row_count for version in versions):
        errors.append("Source-to-staging row reconciliation failed.")
    if any(not version.source_checksum for version in versions):
        errors.append("A dataset version is missing source checksum provenance.")
    canonical_count = session.scalar(select(func.count()).select_from(CanonicalWork).join(DatasetVersion, CanonicalWork.first_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == batch_id)) or 0
    if canonical_count == 0:
        errors.append("Canonicalization produced no works.")
    if session.bind and session.bind.dialect.name == "sqlite":
        foreign_key_errors = session.execute(text("PRAGMA foreign_key_check")).all()
        if foreign_key_errors:
            errors.append("SQLite foreign-key integrity check failed.")
    return errors


def approve_batch(session: Session, batch_id: str, *, approved_by: str, notes: str | None = None) -> DatasetRelease:
    errors = verify_approval_gate(session, batch_id)
    if errors:
        raise LifecycleError("Approval gate failed: " + " ".join(errors))
    release = session.scalar(select(DatasetRelease).where(DatasetRelease.batch_id == batch_id))
    if release:
        if release.status in {"APPROVED", "PROMOTED", "ACTIVE", "HISTORICAL"}:
            return release
        raise LifecycleError(f"Existing release is {release.status}; create a new validated batch for re-approval.")
    batch = session.get(IngestionBatch, batch_id)
    assert batch is not None
    _backfill_financial_years(session, batch_id)
    release = DatasetRelease(
        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"release:{batch_id}")),
        batch_id=batch_id,
        release_version=f"{batch.ingestion_version}:{batch_id[:8]}",
        status="APPROVED",
        approved_by=approved_by,
        approved_at=datetime.now(UTC),
        validation_version=batch.ingestion_version,
        approval_notes=notes,
        promoted_at=None,
        rolled_back_at=None,
    )
    session.add(release)
    batch.status = "APPROVED"
    for version in session.scalars(select(DatasetVersion).where(DatasetVersion.batch_id == batch_id)):
        version.status = "APPROVED"
    _event(session, release.id, "APPROVED", approved_by, notes)
    session.commit()
    return release


def promote_release(session: Session, release_id: str, *, actor: str, notes: str | None = None) -> DatasetRelease:
    release = session.get(DatasetRelease, release_id)
    if release is None:
        raise LifecycleError("Release does not exist.")
    if release.status == "ACTIVE":
        return release
    if release.status != "APPROVED":
        raise LifecycleError(f"Release is {release.status}; only APPROVED releases can be promoted.")
    if verify_approval_gate(session, release.batch_id):
        raise LifecycleError("Release no longer meets the approval gate.")
    try:
        old = session.scalars(select(DatasetRelease).where(DatasetRelease.status == "ACTIVE")).all()
        if len(old) > 1:
            raise LifecycleError("Cannot promote while more than one ACTIVE release exists.")
        for previous in old:
            previous.status = "HISTORICAL"
            previous_batch = session.get(IngestionBatch, previous.batch_id)
            if previous_batch:
                previous_batch.status = "HISTORICAL"
            for version in session.scalars(select(DatasetVersion).where(DatasetVersion.batch_id == previous.batch_id)):
                version.status = "HISTORICAL"
            _event(session, previous.id, "HISTORICAL", actor, f"Superseded by {release.release_version}")
        release.status = "ACTIVE"
        release.promoted_at = datetime.now(UTC)
        batch = session.get(IngestionBatch, release.batch_id)
        assert batch is not None
        batch.status = "ACTIVE"
        for version in session.scalars(select(DatasetVersion).where(DatasetVersion.batch_id == release.batch_id)):
            version.status = "ACTIVE"
        _event(session, release.id, "PROMOTED", actor, notes)
        _event(session, release.id, "ACTIVE", actor, notes)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return release


def rollback_active_release(session: Session, *, actor: str, notes: str | None = None) -> DatasetRelease:
    current = session.scalar(select(DatasetRelease).where(DatasetRelease.status == "ACTIVE"))
    if current is None:
        raise LifecycleError("No ACTIVE release exists to roll back.")
    previous = session.scalars(select(DatasetRelease).where(DatasetRelease.status == "HISTORICAL").order_by(DatasetRelease.promoted_at.desc())).first()
    if previous is None:
        raise LifecycleError("No prior promoted HISTORICAL release exists for rollback.")
    try:
        current.status = "ROLLED_BACK"
        current.rolled_back_at = datetime.now(UTC)
        current_batch = session.get(IngestionBatch, current.batch_id)
        if current_batch:
            current_batch.status = "ROLLED_BACK"
        for version in session.scalars(select(DatasetVersion).where(DatasetVersion.batch_id == current.batch_id)):
            version.status = "ROLLED_BACK"
        previous.status = "ACTIVE"
        restored_batch = session.get(IngestionBatch, previous.batch_id)
        if restored_batch:
            restored_batch.status = "ACTIVE"
        for version in session.scalars(select(DatasetVersion).where(DatasetVersion.batch_id == previous.batch_id)):
            version.status = "ACTIVE"
        _event(session, current.id, "ROLLED_BACK", actor, notes)
        _event(session, previous.id, "ACTIVE", actor, f"Rollback restoration from {current.release_version}")
        session.commit()
    except Exception:
        session.rollback()
        raise
    return previous

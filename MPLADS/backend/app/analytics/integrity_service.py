"""Database integrity checks for promoted, source-traceable analytical releases."""

from __future__ import annotations

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import CanonicalWork, DatasetVersion, ExpenditureTransaction
from app.services.versioning_service import resolve_active_scope


def active_release_integrity(session: Session) -> dict[str, int | bool]:
    scope = resolve_active_scope(session)
    versions = session.scalars(select(DatasetVersion).where(DatasetVersion.batch_id == scope.batch_id)).all()
    source_loss = sum(version.source_row_count - version.staged_row_count for version in versions)
    key_mismatch = session.scalar(select(func.count()).select_from(CanonicalWork).join(DatasetVersion, CanonicalWork.first_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id, CanonicalWork.canonical_work_key != (CanonicalWork.house + ":" + CanonicalWork.normalized_work_id))) or 0
    cross_house_collision = session.execute(select(CanonicalWork.normalized_work_id).join(DatasetVersion, CanonicalWork.first_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id).group_by(CanonicalWork.normalized_work_id).having(func.count(func.distinct(CanonicalWork.house)) > 1)).all()
    orphan_expenditure = session.scalar(select(func.count()).select_from(ExpenditureTransaction).join(DatasetVersion, ExpenditureTransaction.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id, ExpenditureTransaction.canonical_work_key.is_(None))) or 0
    foreign_key_violations = len(session.execute(text("PRAGMA foreign_key_check")).all()) if session.bind and session.bind.dialect.name == "sqlite" else 0
    return {
        "expected_dataset_versions_present": len(versions) == 12,
        "source_to_staging_row_loss": int(source_loss),
        "canonical_key_mismatch_count": int(key_mismatch),
        "cross_house_work_id_collision_count": len(cross_house_collision),
        "unmatched_valid_expenditure_transaction_count": int(orphan_expenditure),
        "foreign_key_violation_count": foreign_key_violations,
        "passed": len(versions) == 12 and source_loss == 0 and key_mismatch == 0 and not cross_house_collision and orphan_expenditure == 0 and foreign_key_violations == 0,
    }

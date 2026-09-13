"""Controlled public metadata for active and historical dataset releases."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DatasetRelease, DatasetVersion
from app.services.versioning_service import resolve_active_scope


def active_metadata(session: Session) -> dict:
    scope = resolve_active_scope(session)
    release = session.get(DatasetRelease, scope.release_id)
    versions = session.scalars(select(DatasetVersion).where(DatasetVersion.batch_id == scope.batch_id).order_by(DatasetVersion.house, DatasetVersion.dataset_type)).all()
    return {"release_version": scope.release_version, "status": release.status if release else None, "promoted_at": release.promoted_at.isoformat() if release and release.promoted_at else None, "datasets": [_version_payload(version) for version in versions]}


def list_versions(session: Session) -> dict:
    releases = session.scalars(select(DatasetRelease).order_by(DatasetRelease.approved_at.desc())).all()
    return {"releases": [{"release_version": release.release_version, "status": release.status, "approved_at": release.approved_at.isoformat(), "promoted_at": release.promoted_at.isoformat() if release.promoted_at else None, "dataset_count": len(session.scalars(select(DatasetVersion.id).where(DatasetVersion.batch_id == release.batch_id)).all())} for release in releases]}


def _version_payload(version: DatasetVersion) -> dict:
    return {"dataset_type": version.dataset_type, "house": version.house, "status": version.status, "source_filename": version.source_filename, "source_sheet": version.source_sheet, "source_checksum": version.source_checksum, "source_row_count": version.source_row_count, "staged_row_count": version.staged_row_count, "valid_row_count": version.valid_row_count, "warning_row_count": version.warning_row_count, "rejected_row_count": version.rejected_row_count}

import json
from pathlib import Path

from sqlalchemy import func, select

from app.db.session import create_session_factory
from app.core.config import get_settings
from app.models import (
    AllocatedLimitRecord, CalamityRecord, CanonicalWork, DatasetVersion, ExpenditureTransaction,
    IngestionBatch, StagingCompletedWork, StagingExpenditure, StagingRecommendedWork,
    StagingSanctionedWork, ValidationFinding,
)
from app.services.ingestion_service import ingest_sources

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data"


def current_batch_id(session):
    return session.scalar(select(IngestionBatch.id).where(IngestionBatch.status.in_(["VALIDATED", "APPROVED", "ACTIVE"])))


def audited_dataset_rows() -> dict[tuple[str, str], int]:
    source_audit = json.loads((ROOT / "docs" / "generated" / "source_audit.json").read_text(encoding="utf-8"))
    return {(record["house"], record["dataset_type"]): record["data_row_count"] for record in source_audit["datasets"]}


def test_real_manifest_has_exact_house_assignment() -> None:
    manifest = json.loads((DATA_ROOT / "dataset_assignments.json").read_text(encoding="utf-8"))
    assert len(manifest["datasets"]) == 12
    assert [item["house"] for item in manifest["datasets"][:6]] == ["LOK_SABHA"] * 6
    assert [item["house"] for item in manifest["datasets"][6:]] == ["RAJYA_SABHA"] * 6


def test_real_batch_retains_every_audited_source_row() -> None:
    factory = create_session_factory(get_settings().database_url)
    with factory() as session:
        batch_id = current_batch_id(session)
        versions = session.scalars(select(DatasetVersion).where(DatasetVersion.batch_id == batch_id)).all()
        assert len(versions) == 12
        expected_rows = audited_dataset_rows()
        assert {(version.house, version.dataset_type): version.source_row_count for version in versions} == expected_rows
        assert sum(version.staged_row_count for version in versions) == sum(expected_rows.values())
        assert all(version.status in {"VALIDATED", "APPROVED", "ACTIVE"} for version in versions)
        assert all(version.source_checksum for version in versions)


def test_database_provenance_checksums_match_the_raw_source_audit() -> None:
    source_audit = json.loads((ROOT / "docs" / "generated" / "source_audit.json").read_text(encoding="utf-8"))
    expected = {record["sha256"] for record in source_audit["datasets"]}
    factory = create_session_factory(get_settings().database_url)
    with factory() as session:
        batch_id = current_batch_id(session)
        stored = set(session.scalars(select(DatasetVersion.source_checksum).where(DatasetVersion.batch_id == batch_id)).all())
    assert stored == expected


def test_real_unresolved_and_blank_source_records_are_retained() -> None:
    factory = create_session_factory(get_settings().database_url)
    with factory() as session:
        batch_id = current_batch_id(session)
        unresolved = session.scalar(select(func.count()).select_from(StagingRecommendedWork).where(StagingRecommendedWork.batch_id == batch_id, StagingRecommendedWork.work_reference_status == "UNRESOLVED_SOURCE_WORK_REFERENCE"))
        blank = sum(session.scalar(select(func.count()).select_from(model).where(model.batch_id == batch_id, model.work_reference_status == "BLANK_OR_UNRESOLVED_SOURCE_RECORD")) for model in [StagingRecommendedWork, StagingSanctionedWork, StagingExpenditure, StagingCompletedWork])
        expected_unresolved = session.scalar(select(func.count()).select_from(ValidationFinding).where(ValidationFinding.batch_id == batch_id, ValidationFinding.code == "UNRESOLVED_SOURCE_WORK_REFERENCE"))
        expected_blank = session.scalar(select(func.count()).select_from(ValidationFinding).where(ValidationFinding.batch_id == batch_id, ValidationFinding.code == "BLANK_SOURCE_WORK_REFERENCE"))
        assert unresolved == expected_unresolved
        assert blank == expected_blank


def test_real_canonical_work_identity_is_house_safe() -> None:
    factory = create_session_factory(get_settings().database_url)
    with factory() as session:
        batch_id = current_batch_id(session)
        expected = session.get(IngestionBatch, batch_id).summary["canonical"]["canonical_works"]
        assert session.scalar(select(func.count()).select_from(CanonicalWork)) == expected
        collisions = session.execute(select(CanonicalWork.normalized_work_id).group_by(CanonicalWork.normalized_work_id).having(func.count(func.distinct(CanonicalWork.house)) > 1)).all()
        assert collisions == []
        assert session.scalar(select(func.count()).select_from(CanonicalWork).where(~CanonicalWork.canonical_work_key.contains(":"))) == 0


def test_expenditure_is_transaction_level_and_other_domains_remain_separate() -> None:
    factory = create_session_factory(get_settings().database_url)
    with factory() as session:
        batch_id = current_batch_id(session)
        staged_transactions = session.scalar(select(func.count()).select_from(StagingExpenditure).where(StagingExpenditure.batch_id == batch_id, StagingExpenditure.validation_status != "REJECTED"))
        assert staged_transactions == session.scalar(select(func.count()).select_from(ExpenditureTransaction))
        summary = session.get(IngestionBatch, batch_id).summary["canonical"]
        assert session.scalar(select(func.count()).select_from(AllocatedLimitRecord)) == summary["allocated_limit_records"]
        assert session.scalar(select(func.count()).select_from(CalamityRecord)) == summary["calamity_records"]


def test_reingestion_is_idempotent_for_the_same_sources_and_code() -> None:
    manifest = json.loads((DATA_ROOT / "dataset_assignments.json").read_text(encoding="utf-8"))
    factory = create_session_factory(get_settings().database_url)
    with factory() as session:
        summary = ingest_sources(session, manifest, DATA_ROOT)
    assert summary["idempotent_reuse"] is True
    assert summary["staged_rows"] == sum(audited_dataset_rows().values())


def test_validation_findings_are_traceable_to_source_rows() -> None:
    factory = create_session_factory(get_settings().database_url)
    with factory() as session:
        batch_id = current_batch_id(session)
        findings = session.scalars(select(ValidationFinding).where(ValidationFinding.batch_id == batch_id)).all()
        assert findings
        assert all(finding.source_row_number >= 3 for finding in findings)
        assert {finding.severity for finding in findings} == {"ERROR", "WARNING"}

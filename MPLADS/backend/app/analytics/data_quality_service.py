"""Data-quality metrics remain separate from monitoring/risk analytics."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.types import AnalyticsFilters, AnalyticsResult, provenance
from app.models import (
    CompletedWorkRecord, DatasetVersion, ExpenditureTransaction, StagingCompletedWork,
    StagingExpenditure, StagingRecommendedWork, StagingSanctionedWork, ValidationFinding,
)
from app.services.versioning_service import resolve_active_scope


def data_quality_metrics(session: Session, filters: AnalyticsFilters = AnalyticsFilters()) -> AnalyticsResult:
    if any(value is not None for key, value in filters.as_dict().items() if key not in {"house"}):
        raise ValueError("Data-quality metrics currently support House filtering only because unresolved rows may not have canonical work identity.")
    scope = resolve_active_scope(session)
    stage_models = [StagingRecommendedWork, StagingSanctionedWork, StagingExpenditure, StagingCompletedWork]
    def staged_count(condition):
        count = 0
        for model in stage_models:
            statement = select(func.count()).select_from(model).where(model.batch_id == scope.batch_id, condition(model))
            if filters.house:
                statement = statement.where(model.house == filters.house)
            count += session.scalar(statement) or 0
        return int(count)
    warning_statement = select(func.count()).select_from(ValidationFinding).where(ValidationFinding.batch_id == scope.batch_id, ValidationFinding.severity == "WARNING")
    error_statement = select(func.count()).select_from(ValidationFinding).where(ValidationFinding.batch_id == scope.batch_id, ValidationFinding.severity == "ERROR")
    if filters.house:
        version_ids = select(DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id, DatasetVersion.house == filters.house)
        warning_statement = warning_statement.where(ValidationFinding.dataset_version_id.in_(version_ids))
        error_statement = error_statement.where(ValidationFinding.dataset_version_id.in_(version_ids))
    orphan_expenditure = select(func.count()).select_from(ExpenditureTransaction).join(DatasetVersion, ExpenditureTransaction.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id, ExpenditureTransaction.canonical_work_key.is_(None))
    orphan_completion = select(func.count()).select_from(CompletedWorkRecord).join(DatasetVersion, CompletedWorkRecord.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id, CompletedWorkRecord.canonical_work_key.is_(None))
    if filters.house:
        orphan_expenditure = orphan_expenditure.where(ExpenditureTransaction.house == filters.house)
        orphan_completion = orphan_completion.where(CompletedWorkRecord.house == filters.house)
    return AnalyticsResult({
        "unresolved_work_references": staged_count(lambda model: model.work_reference_status == "UNRESOLVED_SOURCE_WORK_REFERENCE"),
        "blank_work_references": staged_count(lambda model: model.work_reference_status == "BLANK_OR_UNRESOLVED_SOURCE_RECORD"),
        "orphan_expenditure_transactions": int(session.scalar(orphan_expenditure) or 0),
        "orphan_completed_records": int(session.scalar(orphan_completion) or 0),
        "missing_mp": staged_count(lambda model: model.mp_source_name.is_(None)),
        "missing_state": staged_count(lambda model: model.state_name.is_(None)),
        "missing_district_or_ida": staged_count(lambda model: model.district_or_ida.is_(None)),
        "validation_warnings": int(session.scalar(warning_statement) or 0),
        "rejected_canonical_records": int(session.scalar(error_statement) or 0),
        "physical_progress_available": False,
    }, provenance("data_quality_service.data_quality_metrics", scope, filters))

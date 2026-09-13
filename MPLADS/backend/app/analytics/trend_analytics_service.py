"""Date-backed trends. No dates are fabricated when source coverage is absent."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.query import active_works_statement
from app.analytics.types import AnalyticsFilters, AnalyticsResult, provenance
from app.models import CanonicalWork, CompletedWorkRecord, DatasetVersion, ExpenditureTransaction, RecommendedWorkRecord
from app.services.versioning_service import resolve_active_scope


def _trend(session: Session, model, date_column, value_column, scope, filters, service_name: str) -> AnalyticsResult:
    work_keys = active_works_statement(scope, filters).with_only_columns(CanonicalWork.canonical_work_key).subquery()
    period = func.substr(date_column, 1, 7)
    columns = [period.label("period"), func.count().label("record_count")]
    if value_column is not None:
        columns.append(func.coalesce(func.sum(value_column), 0).label("amount"))
    rows = session.execute(select(*columns).join(DatasetVersion, model.source_dataset_version_id == DatasetVersion.id).join(work_keys, model.canonical_work_key == work_keys.c.canonical_work_key).where(DatasetVersion.batch_id == scope.batch_id, date_column.is_not(None)).group_by(period).order_by(period)).all()
    if not rows:
        return AnalyticsResult({"data_available": False, "message": "Not available from the current source data.", "rows": []}, provenance(service_name, scope, filters))
    return AnalyticsResult({"data_available": True, "rows": [{"period": row.period, "record_count": int(row.record_count), **({"amount": str(row.amount)} if value_column is not None else {})} for row in rows]}, provenance(service_name, scope, filters))


def works_trend(session: Session, filters: AnalyticsFilters = AnalyticsFilters()) -> AnalyticsResult:
    scope = resolve_active_scope(session)
    return _trend(session, RecommendedWorkRecord, RecommendedWorkRecord.recommended_date, None, scope, filters, "trend_analytics_service.works_trend")


def expenditure_trend(session: Session, filters: AnalyticsFilters = AnalyticsFilters()) -> AnalyticsResult:
    scope = resolve_active_scope(session)
    return _trend(session, ExpenditureTransaction, ExpenditureTransaction.expenditure_date, ExpenditureTransaction.disbursed_amount, scope, filters, "trend_analytics_service.expenditure_trend")


def completion_trend(session: Session, filters: AnalyticsFilters = AnalyticsFilters()) -> AnalyticsResult:
    scope = resolve_active_scope(session)
    return _trend(session, CompletedWorkRecord, CompletedWorkRecord.completion_date, None, scope, filters, "trend_analytics_service.completion_trend")

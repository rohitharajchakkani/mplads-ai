"""Core dashboard metrics calculated from the centralized ACTIVE release scope."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.analytics.query import active_works_statement, assert_domain_filter_supported
from app.analytics.normalization import normalized_equals
from app.analytics.types import AnalyticsFilters, AnalyticsResult, provenance
from app.models import (
    AllocatedLimitRecord, AnalyticalAlert, CalamityRecord, CanonicalWork, CompletedWorkRecord,
    DatasetVersion, DuplicateCandidate, ExpenditureTransaction, MonitoringSignal,
    Recommendation, RecommendedWorkRecord, ReviewCase, SanctionedWorkRecord,
)
from app.services.versioning_service import resolve_active_scope

_CACHE: dict[tuple, tuple[float, AnalyticsResult]] = {}
_CACHE_TTL = 60.0


def _count(statement, column) -> int:
    return int(statement.session.scalar(select(func.count(distinct(column)).select_from(statement.subquery()))))


def _metric_count(session: Session, record_model, scope, works_statement, has_work_filters: bool) -> int:
    if not has_work_filters:
        return int(session.scalar(
            select(func.count(distinct(record_model.canonical_work_key)))
            .join(DatasetVersion, record_model.source_dataset_version_id == DatasetVersion.id)
            .where(DatasetVersion.batch_id == scope.batch_id)
        ) or 0)
    work_keys = works_statement.with_only_columns(CanonicalWork.canonical_work_key).subquery()
    return int(session.scalar(
        select(func.count(distinct(record_model.canonical_work_key)))
        .join(DatasetVersion, record_model.source_dataset_version_id == DatasetVersion.id)
        .join(work_keys, record_model.canonical_work_key == work_keys.c.canonical_work_key)
        .where(DatasetVersion.batch_id == scope.batch_id)
    ) or 0)


def _metric_sum(session: Session, record_model, amount_column, scope, works_statement, has_work_filters: bool) -> Decimal:
    if not has_work_filters:
        return session.scalar(
            select(func.coalesce(func.sum(amount_column), 0))
            .join(DatasetVersion, record_model.source_dataset_version_id == DatasetVersion.id)
            .where(DatasetVersion.batch_id == scope.batch_id)
        ) or Decimal("0")
    work_keys = works_statement.with_only_columns(CanonicalWork.canonical_work_key).subquery()
    return session.scalar(
        select(func.coalesce(func.sum(amount_column), 0))
        .join(DatasetVersion, record_model.source_dataset_version_id == DatasetVersion.id)
        .join(work_keys, record_model.canonical_work_key == work_keys.c.canonical_work_key)
        .where(DatasetVersion.batch_id == scope.batch_id)
    ) or Decimal("0")


def _domain_sum(session: Session, model, amount_column, scope, filters: AnalyticsFilters, domain: str) -> Decimal:
    supported = {"house"}
    for filter_name, field_name in {"state": "state_name", "mp": "mp_source_name", "constituency": "constituency_name"}.items():
        if hasattr(model, field_name):
            supported.add(filter_name)
    assert_domain_filter_supported(filters, supported, domain)
    statement = select(func.coalesce(func.sum(amount_column), 0)).join(DatasetVersion, model.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id)
    if filters.house:
        statement = statement.where(model.house == filters.house)
    if filters.state and hasattr(model, "state_name"):
        statement = statement.where(normalized_equals(model.state_name, filters.state))
    if filters.mp and hasattr(model, "mp_source_name"):
        statement = statement.where(normalized_equals(model.mp_source_name, filters.mp))
    if filters.constituency and hasattr(model, "constituency_name"):
        statement = statement.where(normalized_equals(model.constituency_name, filters.constituency))
    return session.scalar(statement) or Decimal("0")


def _monitoring_count(session: Session, model, scope, filters: AnalyticsFilters) -> int:
    statement = select(func.count()).select_from(model)
    if hasattr(model, "dataset_version"):
        statement = statement.where(model.dataset_version == scope.release_version)
    if filters.house and hasattr(model, "house"):
        statement = statement.where(model.house == filters.house)
    if filters.state and hasattr(model, "state_name"):
        statement = statement.where(normalized_equals(model.state_name, filters.state))
    if filters.district_or_ida and hasattr(model, "district_or_ida"):
        statement = statement.where(normalized_equals(model.district_or_ida, filters.district_or_ida))
    if filters.mp and hasattr(model, "mp_source_name"):
        statement = statement.where(normalized_equals(model.mp_source_name, filters.mp))
    return int(session.scalar(statement) or 0)


def _review_workload_count(session: Session, scope, filters: AnalyticsFilters) -> int:
    statement = select(func.count()).select_from(ReviewCase).where(ReviewCase.status.in_(("OPEN", "ASSIGNED", "UNDER_REVIEW", "FOLLOW_UP_REQUIRED")))
    if filters.house:
        statement = statement.where(ReviewCase.house == filters.house)
    if filters.state:
        statement = statement.where(normalized_equals(ReviewCase.state_name, filters.state))
    if filters.district_or_ida:
        statement = statement.where(normalized_equals(ReviewCase.district_or_ida, filters.district_or_ida))
    if filters.mp:
        statement = statement.where(normalized_equals(ReviewCase.mp_source_name, filters.mp))
    return int(session.scalar(statement) or 0)


def core_metrics(session: Session, filters: AnalyticsFilters = AnalyticsFilters()) -> AnalyticsResult:
    scope = resolve_active_scope(session)
    filter_dict = filters.as_dict()
    cache_key = (scope.release_version, tuple(sorted(filter_dict.items())))
    import time
    now = time.time()
    if cache_key in _CACHE:
        ts, cached = _CACHE[cache_key]
        if now - ts < _CACHE_TTL:
            return cached

    has_work_filters = any(v is not None for v in filter_dict.values())
    works_statement = active_works_statement(scope, filters)
    works_subquery = works_statement.subquery()
    total_works = int(session.scalar(select(func.count()).select_from(works_subquery)) or 0)

    data = {
        "total_canonical_works": total_works,
        "monitored_works": total_works,
        "risk_signals_count": _monitoring_count(session, MonitoringSignal, scope, filters),
        "alerts_count": _monitoring_count(session, AnalyticalAlert, scope, filters),
        "potential_duplicates_count": _monitoring_count(session, DuplicateCandidate, scope, filters),
        "open_reviews_count": _review_workload_count(session, scope, filters),
        "recommendations_count": _monitoring_count(session, Recommendation, scope, filters),
        "recommended_works": _metric_count(session, RecommendedWorkRecord, scope, works_statement, has_work_filters),
        "sanctioned_works": _metric_count(session, SanctionedWorkRecord, scope, works_statement, has_work_filters),
        "completed_works": _metric_count(session, CompletedWorkRecord, scope, works_statement, has_work_filters),
        "total_sanction_amount": str(_metric_sum(session, SanctionedWorkRecord, SanctionedWorkRecord.sanction_amount, scope, works_statement, has_work_filters)),
        "total_expenditure": str(_metric_sum(session, ExpenditureTransaction, ExpenditureTransaction.disbursed_amount, scope, works_statement, has_work_filters)),
        "mp_count": int(session.scalar(select(func.count(distinct(works_subquery.c.mp_source_name))).select_from(works_subquery)) or 0),
        "state_count": int(session.scalar(select(func.count(distinct(works_subquery.c.state_name))).select_from(works_subquery)) or 0),
        "district_or_ida_count": int(session.scalar(select(func.count(distinct(works_subquery.c.district_or_ida))).select_from(works_subquery)) or 0),
        "sector": {"available": False, "message": "Not available from the current source data; the source contains work categories, not a verified sector field."},
        "physical_progress": {"available": False, "message": "Physical progress percentage is not available in the supplied source data."},
    }
    try:
        data["allocation"] = str(_domain_sum(session, AllocatedLimitRecord, AllocatedLimitRecord.allocated_amount, scope, filters, "Allocation"))
    except ValueError as exc:
        data["allocation"] = {"available": False, "message": str(exc)}
    try:
        data["calamity_amount"] = str(_domain_sum(session, CalamityRecord, CalamityRecord.consent_amount, scope, filters, "Calamity"))
    except ValueError as exc:
        data["calamity_amount"] = {"available": False, "message": str(exc)}

    result = AnalyticsResult(data, provenance("dashboard_service.core_metrics", scope, filters))
    _CACHE[cache_key] = (now, result)
    return result


def house_comparison(session: Session, filters: AnalyticsFilters = AnalyticsFilters()) -> AnalyticsResult:
    scope = resolve_active_scope(session)
    if filters.house:
        raise ValueError("House comparison requires no House filter; omit House to compare both Houses.")
    rows = []
    for house in ("LOK_SABHA", "RAJYA_SABHA"):
        metrics = core_metrics(session, AnalyticsFilters(**{**filters.as_dict(), "house": house})).data
        rows.append({"house": house, "total_canonical_works": metrics["total_canonical_works"], "sanctioned_works": metrics["sanctioned_works"], "completed_works": metrics["completed_works"], "total_sanction_amount": metrics["total_sanction_amount"], "total_expenditure": metrics["total_expenditure"]})
    return AnalyticsResult({"rows": rows}, provenance("dashboard_service.house_comparison", scope, filters))

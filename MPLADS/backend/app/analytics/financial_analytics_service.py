"""Transaction-grain expenditure analytics from the ACTIVE dataset release."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.query import active_works_statement
from app.analytics.types import AnalyticsFilters, AnalyticsResult, provenance
from app.models import CanonicalWork, DatasetVersion, ExpenditureTransaction
from app.services.versioning_service import resolve_active_scope


def expenditure_summary(session: Session, filters: AnalyticsFilters = AnalyticsFilters()) -> AnalyticsResult:
    scope = resolve_active_scope(session)
    works = active_works_statement(scope, filters).with_only_columns(CanonicalWork.canonical_work_key).subquery()
    statement = select(func.coalesce(func.sum(ExpenditureTransaction.disbursed_amount), 0), func.count(ExpenditureTransaction.id)).join(DatasetVersion, ExpenditureTransaction.source_dataset_version_id == DatasetVersion.id).join(works, ExpenditureTransaction.canonical_work_key == works.c.canonical_work_key).where(DatasetVersion.batch_id == scope.batch_id)
    total, transaction_count = session.execute(statement).one()
    unmatched = session.scalar(select(func.count()).select_from(ExpenditureTransaction).join(DatasetVersion, ExpenditureTransaction.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id, ExpenditureTransaction.canonical_work_key.is_(None))) or 0
    return AnalyticsResult({"total_expenditure": str(total or Decimal("0")), "transaction_count": int(transaction_count), "unmatched_expenditure_transactions": int(unmatched)}, provenance("financial_analytics_service.expenditure_summary", scope, filters))


def expenditure_by(session: Session, dimension: str, filters: AnalyticsFilters = AnalyticsFilters()) -> AnalyticsResult:
    allowed = {"house": CanonicalWork.house, "state": CanonicalWork.state_name, "district_or_ida": CanonicalWork.district_or_ida, "mp": CanonicalWork.mp_source_name, "work": CanonicalWork.canonical_work_key}
    if dimension not in allowed:
        raise ValueError(f"Unsupported expenditure dimension: {dimension}")
    scope = resolve_active_scope(session)
    works = active_works_statement(scope, filters).subquery()
    field = works.c[allowed[dimension].key]
    rows = session.execute(select(field.label("dimension"), func.coalesce(func.sum(ExpenditureTransaction.disbursed_amount), 0).label("amount"), func.count(ExpenditureTransaction.id).label("transaction_count")).join(DatasetVersion, ExpenditureTransaction.source_dataset_version_id == DatasetVersion.id).join(works, ExpenditureTransaction.canonical_work_key == works.c.canonical_work_key).where(DatasetVersion.batch_id == scope.batch_id).group_by(field).order_by(func.sum(ExpenditureTransaction.disbursed_amount).desc())).all()
    return AnalyticsResult({"dimension": dimension, "rows": [{"value": row.dimension, "expenditure": str(row.amount), "transaction_count": int(row.transaction_count)} for row in rows]}, provenance("financial_analytics_service.expenditure_by", scope, filters))

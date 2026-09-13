"""Small, scoped option lists for the cascading public filter controls."""
from __future__ import annotations

from sqlalchemy import distinct, func, or_, select
from sqlalchemy.orm import Session

from app.analytics.normalization import normalized_contains, normalized_equals
from app.analytics.query import active_works_statement
from app.analytics.types import AnalyticsFilters, AnalyticsResult, provenance
from app.models import DatasetVersion, SanctionedWorkRecord
from app.services.versioning_service import resolve_active_scope


_WORK_COLUMNS = {
    "house": "house",
    "state": "state_name",
    "district_or_ida": "district_or_ida",
    "mp": "mp_source_name",
    "financial_year": "financial_year",
}
_ALLOWED = {*_WORK_COLUMNS, "work", "work_status"}


def _without_current_field(filters: AnalyticsFilters, field: str) -> AnalyticsFilters:
    values = filters.as_dict()
    values[field] = None
    return AnalyticsFilters(**values)


def _matching(expression, query: str | None):
    return normalized_contains(expression, query) if query else None


def filter_options(
    session: Session,
    field: str,
    filters: AnalyticsFilters = AnalyticsFilters(),
    query: str | None = None,
    limit: int = 50,
) -> AnalyticsResult:
    """Return at most ``limit`` real values from the active filtered release."""
    if field not in _ALLOWED:
        raise ValueError("Unsupported filter option field.")
    scope = resolve_active_scope(session)
    current_filters = _without_current_field(filters, field)
    works = active_works_statement(scope, current_filters).subquery()

    if field == "work_status":
        value = SanctionedWorkRecord.work_status_source
        statement = (
            select(value.label("value"), func.count(distinct(SanctionedWorkRecord.canonical_work_key)).label("count"))
            .join(DatasetVersion, SanctionedWorkRecord.source_dataset_version_id == DatasetVersion.id)
            .join(works, SanctionedWorkRecord.canonical_work_key == works.c.canonical_work_key)
            .where(DatasetVersion.batch_id == scope.batch_id, value.is_not(None))
            .group_by(value)
            .order_by(func.count(distinct(SanctionedWorkRecord.canonical_work_key)).desc(), value.asc())
        )
        match = _matching(value, query)
        if match is not None:
            statement = statement.where(match)
        rows = session.execute(statement.limit(limit)).all()
        options = [{"value": row.value, "label": row.value, "count": int(row.count)} for row in rows]
    elif field == "work":
        key, label = works.c.canonical_work_key, works.c.normalized_work_id
        statement = select(key.label("value"), label.label("label"), func.count().label("count")).where(key.is_not(None)).group_by(key, label).order_by(label.asc())
        if query:
            statement = statement.where(or_(normalized_contains(key, query), normalized_contains(label, query)))
        rows = session.execute(statement.limit(limit)).all()
        options = [{"value": row.value, "label": row.label or row.value, "count": int(row.count)} for row in rows]
    else:
        value = works.c[_WORK_COLUMNS[field]]
        statement = select(value.label("value"), func.count().label("count")).where(value.is_not(None)).group_by(value).order_by(func.count().desc(), value.asc())
        match = _matching(value, query)
        if match is not None:
            statement = statement.where(match)
        rows = session.execute(statement.limit(limit)).all()
        options = [{"value": row.value, "label": row.value.replace("_", " ") if field == "house" else row.value, "count": int(row.count)} for row in rows]

    return AnalyticsResult(
        {"field": field, "options": options, "query": query, "limited": len(options) == limit},
        provenance("filter_options_service.filter_options", scope, filters),
    )

"""Observed lifecycle-duration analytics; no policy deadline is inferred."""

from __future__ import annotations

from statistics import mean, median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.query import active_works_statement
from app.analytics.types import AnalyticsFilters, AnalyticsResult, provenance
from app.models import CanonicalWork, CompletedWorkRecord, DatasetVersion, SanctionedWorkRecord
from app.services.versioning_service import resolve_active_scope


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    position = (len(values) - 1) * percentile
    lower, upper = int(position), min(int(position) + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def _summary(values: list[float]) -> dict:
    values = sorted(values)
    if not values:
        return {"count_with_both_dates": 0, "median_days": None, "mean_days": None, "p25_days": None, "p50_days": None, "p75_days": None, "p90_days": None, "min_days": None, "max_days": None}
    return {"count_with_both_dates": len(values), "median_days": median(values), "mean_days": mean(values), "p25_days": _percentile(values, .25), "p50_days": _percentile(values, .5), "p75_days": _percentile(values, .75), "p90_days": _percentile(values, .9), "min_days": min(values), "max_days": max(values)}


from time import time

_LIFECYCLE_CACHE: dict[tuple, tuple[AnalyticsResult, float]] = {}
_CACHE_TTL_SECONDS = 300.0


def lifecycle_summary(session: Session, filters: AnalyticsFilters = AnalyticsFilters()) -> AnalyticsResult:
    scope = resolve_active_scope(session)
    cache_key = (scope.batch_id, tuple(sorted((filters.as_dict() or {}).items())))
    cached = _LIFECYCLE_CACHE.get(cache_key)
    if cached and (time() - cached[1]) < _CACHE_TTL_SECONDS:
        return cached[0]

    work_keys = active_works_statement(scope, filters).with_only_columns(CanonicalWork.canonical_work_key).subquery()
    recommendation_statement = (
        select((func.julianday(SanctionedWorkRecord.sanction_date) - func.julianday(SanctionedWorkRecord.recommended_date)).label("duration"))
        .join(DatasetVersion, SanctionedWorkRecord.source_dataset_version_id == DatasetVersion.id)
        .join(work_keys, SanctionedWorkRecord.canonical_work_key == work_keys.c.canonical_work_key)
        .where(DatasetVersion.batch_id == scope.batch_id, SanctionedWorkRecord.recommended_date.is_not(None), SanctionedWorkRecord.sanction_date.is_not(None))
    )
    recommendation_to_sanction = [float(row.duration) for row in session.execute(recommendation_statement) if row.duration is not None and row.duration >= 0]
    sanction_dates = select(SanctionedWorkRecord.canonical_work_key.label("key"), func.min(SanctionedWorkRecord.sanction_date).label("sanction_date")).join(DatasetVersion, SanctionedWorkRecord.source_dataset_version_id == DatasetVersion.id).join(work_keys, SanctionedWorkRecord.canonical_work_key == work_keys.c.canonical_work_key).where(DatasetVersion.batch_id == scope.batch_id, SanctionedWorkRecord.sanction_date.is_not(None)).group_by(SanctionedWorkRecord.canonical_work_key).subquery()
    completion_dates = select(CompletedWorkRecord.canonical_work_key.label("key"), func.min(CompletedWorkRecord.completion_date).label("completion_date")).join(DatasetVersion, CompletedWorkRecord.source_dataset_version_id == DatasetVersion.id).join(work_keys, CompletedWorkRecord.canonical_work_key == work_keys.c.canonical_work_key).where(DatasetVersion.batch_id == scope.batch_id, CompletedWorkRecord.completion_date.is_not(None)).group_by(CompletedWorkRecord.canonical_work_key).subquery()
    completion_statement = select((func.julianday(completion_dates.c.completion_date) - func.julianday(sanction_dates.c.sanction_date)).label("duration")).select_from(sanction_dates.join(completion_dates, completion_dates.c.key == sanction_dates.c.key))
    sanction_to_completion = [float(row.duration) for row in session.execute(completion_statement) if row.duration is not None and row.duration >= 0]
    completed_after_sanction = len(sanction_to_completion)
    sanctioned_count = session.scalar(select(func.count()).select_from(sanction_dates)) or 0
    result = AnalyticsResult({"terminology": "Observed lifecycle duration", "recommendation_to_sanction": _summary(recommendation_to_sanction), "sanction_to_completion": _summary(sanction_to_completion), "right_censored_sanctioned_work_count": int(sanctioned_count - completed_after_sanction), "completion_ratio": (completed_after_sanction / sanctioned_count) if sanctioned_count else None}, provenance("lifecycle_analytics_service.lifecycle_summary", scope, filters))
    _LIFECYCLE_CACHE[cache_key] = (result, time())
    return result

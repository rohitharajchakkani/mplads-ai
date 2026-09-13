"""Source-status and observed work-category analytical services."""

from __future__ import annotations

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.analytics.query import active_works_statement
from app.analytics.types import AnalyticsFilters, AnalyticsResult, provenance
from app.models import CanonicalWork, DatasetVersion, SanctionedWorkRecord
from app.services.versioning_service import resolve_active_scope


def status_distribution(session: Session, filters: AnalyticsFilters = AnalyticsFilters()) -> AnalyticsResult:
    scope = resolve_active_scope(session)
    works = active_works_statement(scope, filters).with_only_columns(CanonicalWork.canonical_work_key).subquery()
    rows = session.execute(select(SanctionedWorkRecord.work_status_source.label("source_status"), func.count(distinct(SanctionedWorkRecord.canonical_work_key)).label("work_count")).join(DatasetVersion, SanctionedWorkRecord.source_dataset_version_id == DatasetVersion.id).join(works, SanctionedWorkRecord.canonical_work_key == works.c.canonical_work_key).where(DatasetVersion.batch_id == scope.batch_id).group_by(SanctionedWorkRecord.work_status_source).order_by(func.count(distinct(SanctionedWorkRecord.canonical_work_key)).desc())).all()
    return AnalyticsResult({"rows": [{"source_status": row.source_status, "normalized_status": None, "work_count": int(row.work_count)} for row in rows], "normalization": "Not available from the current source mapping; source status is preserved without semantic remapping."}, provenance("work_analytics_service.status_distribution", scope, filters))


def source_work_category_distribution(session: Session, filters: AnalyticsFilters = AnalyticsFilters()) -> AnalyticsResult:
    scope = resolve_active_scope(session)
    works = active_works_statement(scope, filters).subquery()
    rows = session.execute(select(works.c.work_category_source.label("source_work_category"), func.count(distinct(works.c.canonical_work_key)).label("work_count")).group_by(works.c.work_category_source).order_by(func.count(distinct(works.c.canonical_work_key)).desc())).all()
    return AnalyticsResult({"rows": [{"source_work_category": row.source_work_category, "work_count": int(row.work_count)} for row in rows], "availability": "Source work categories are available; verified sector/subsector fields are not."}, provenance("work_analytics_service.source_work_category_distribution", scope, filters))

"""State, district/IDA, MP, and constituency aggregations from canonical works."""

from __future__ import annotations

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.analytics.query import active_works_statement
from app.analytics.types import AnalyticsFilters, AnalyticsResult, provenance
from app.models import CanonicalWork, DatasetVersion, ExpenditureTransaction, SanctionedWorkRecord
from app.services.versioning_service import resolve_active_scope


def summarize_by(session: Session, dimension: str, filters: AnalyticsFilters = AnalyticsFilters()) -> AnalyticsResult:
    dimensions = {"state": CanonicalWork.state_name, "district_or_ida": CanonicalWork.district_or_ida, "mp": CanonicalWork.mp_source_name, "constituency": CanonicalWork.constituency_name}
    if dimension not in dimensions:
        raise ValueError(f"Unsupported geography dimension: {dimension}")
    scope = resolve_active_scope(session)
    filtered = active_works_statement(scope, filters).subquery()
    field = filtered.c[dimensions[dimension].key]
    work_rows = session.execute(select(field.label("dimension"), func.count(distinct(filtered.c.canonical_work_key)).label("work_count")).group_by(field)).all()
    expenditure_rows = session.execute(select(field.label("dimension"), func.coalesce(func.sum(ExpenditureTransaction.disbursed_amount), 0).label("expenditure")).join(ExpenditureTransaction, ExpenditureTransaction.canonical_work_key == filtered.c.canonical_work_key).join(DatasetVersion, ExpenditureTransaction.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id).group_by(field)).all()
    sanction_rows = session.execute(select(field.label("dimension"), func.coalesce(func.sum(SanctionedWorkRecord.sanction_amount), 0).label("sanction_amount"), func.count(distinct(SanctionedWorkRecord.canonical_work_key)).label("sanctioned_work_count")).join(SanctionedWorkRecord, SanctionedWorkRecord.canonical_work_key == filtered.c.canonical_work_key).join(DatasetVersion, SanctionedWorkRecord.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id).group_by(field)).all()
    output = {row.dimension: {"value": row.dimension, "work_count": int(row.work_count), "expenditure": "0", "sanction_amount": "0", "sanctioned_work_count": 0} for row in work_rows}
    for row in expenditure_rows:
        output[row.dimension]["expenditure"] = str(row.expenditure)
    for row in sanction_rows:
        output[row.dimension]["sanction_amount"] = str(row.sanction_amount)
        output[row.dimension]["sanctioned_work_count"] = int(row.sanctioned_work_count)
    return AnalyticsResult({"dimension": dimension, "rows": sorted(output.values(), key=lambda row: row["work_count"], reverse=True), "notes": "Status and source-work-category distributions are available through their dedicated services."}, provenance("geography_analytics_service.summarize_by", scope, filters))

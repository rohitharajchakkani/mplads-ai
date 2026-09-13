from __future__ import annotations

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from app.analytics.types import AnalyticsFilters
from app.analytics.normalization import normalized_equals
from app.models import CanonicalWork, DatasetVersion, SanctionedWorkRecord
from app.services.versioning_service import ActiveDatasetScope


class FilterError(ValueError):
    pass


def active_works_statement(scope: ActiveDatasetScope, filters: AnalyticsFilters):
    if filters.sector or filters.subsector:
        raise FilterError("Sector and subsector are not available in the supplied source data.")
    statement = select(CanonicalWork).join(DatasetVersion, CanonicalWork.first_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id)
    if filters.house:
        if filters.house not in {"LOK_SABHA", "RAJYA_SABHA"}:
            raise FilterError("House must be LOK_SABHA or RAJYA_SABHA.")
        statement = statement.where(CanonicalWork.house == filters.house)
    if filters.state:
        statement = statement.where(normalized_equals(CanonicalWork.state_name, filters.state))
    if filters.district_or_ida:
        statement = statement.where(normalized_equals(CanonicalWork.district_or_ida, filters.district_or_ida))
    if filters.mp:
        statement = statement.where(normalized_equals(CanonicalWork.mp_source_name, filters.mp))
    if filters.work:
        statement = statement.where(or_(
            normalized_equals(CanonicalWork.canonical_work_key, filters.work),
            normalized_equals(CanonicalWork.normalized_work_id, filters.work),
        ))
    if filters.constituency:
        statement = statement.where(normalized_equals(CanonicalWork.constituency_name, filters.constituency))
    if filters.financial_year:
        statement = statement.where(normalized_equals(CanonicalWork.financial_year, filters.financial_year))
    if filters.work_status:
        statement = statement.where(
            exists(
                select(SanctionedWorkRecord.id).join(DatasetVersion, SanctionedWorkRecord.source_dataset_version_id == DatasetVersion.id).where(
                    SanctionedWorkRecord.canonical_work_key == CanonicalWork.canonical_work_key,
                    DatasetVersion.batch_id == scope.batch_id,
                    normalized_equals(SanctionedWorkRecord.work_status_source, filters.work_status),
                )
            )
        )
    return statement


def assert_domain_filter_supported(filters: AnalyticsFilters, supported: set[str], domain: str) -> None:
    requested = {name for name, value in filters.as_dict().items() if value is not None}
    unsupported = requested - supported
    if unsupported:
        joined = ", ".join(sorted(unsupported))
        raise FilterError(f"{domain} has no source-supported field for filter(s): {joined}.")

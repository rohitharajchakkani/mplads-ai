from pathlib import Path

import pytest
from sqlalchemy import distinct, func, select

from app.analytics.dashboard_service import core_metrics
from app.analytics.data_quality_service import data_quality_metrics
from app.analytics.financial_analytics_service import expenditure_summary
from app.analytics.geography_analytics_service import summarize_by
from app.analytics.integrity_service import active_release_integrity
from app.analytics.lifecycle_analytics_service import lifecycle_summary
from app.analytics.types import AnalyticsFilters
from app.analytics.work_analytics_service import status_distribution
from app.db.session import create_session_factory
from app.core.config import get_settings
from app.models import (
    AllocatedLimitRecord, CalamityRecord, CanonicalWork, DatasetLifecycleEvent, DatasetRelease,
    DatasetVersion, ExpenditureTransaction, StagingRecommendedWork,
)
from app.services.versioning_service import LifecycleError, resolve_active_scope, rollback_active_release, verify_approval_gate

def session():
    return create_session_factory(get_settings().database_url)()


def test_active_release_resolves_one_complete_dataset_scope() -> None:
    with session() as db:
        scope = resolve_active_scope(db)
        assert len(scope.dataset_version_ids) == 12
        assert db.scalar(select(func.count()).select_from(DatasetRelease).where(DatasetRelease.status == "ACTIVE")) == 1


def test_active_release_still_satisfies_the_approval_gate() -> None:
    with session() as db:
        assert verify_approval_gate(db, resolve_active_scope(db).batch_id) == []
        assert active_release_integrity(db)["passed"] is True


def test_promotion_is_audited_and_one_active_invariant_holds() -> None:
    with session() as db:
        scope = resolve_active_scope(db)
        events = db.scalars(select(DatasetLifecycleEvent.event_type).where(DatasetLifecycleEvent.release_id == scope.release_id)).all()
        assert "APPROVED" in events and "PROMOTED" in events and "ACTIVE" in events
        assert db.scalar(select(func.count()).select_from(DatasetRelease).where(DatasetRelease.status == "ACTIVE")) == 1


def test_rollback_without_a_historical_release_preserves_active_release() -> None:
    with session() as db:
        active_before = resolve_active_scope(db).release_id
        with pytest.raises(LifecycleError, match="No prior promoted HISTORICAL release"):
            rollback_active_release(db, actor="test")
        assert resolve_active_scope(db).release_id == active_before


def test_distinct_work_and_financial_metrics_match_independent_database_aggregates() -> None:
    with session() as db:
        scope = resolve_active_scope(db)
        result = core_metrics(db).data
        expected_works = db.scalar(select(func.count(distinct(CanonicalWork.canonical_work_key))).join(DatasetVersion, CanonicalWork.first_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id))
        expected_expenditure = db.scalar(select(func.coalesce(func.sum(ExpenditureTransaction.disbursed_amount), 0)).join(DatasetVersion, ExpenditureTransaction.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id))
        expected_allocation = db.scalar(select(func.coalesce(func.sum(AllocatedLimitRecord.allocated_amount), 0)).join(DatasetVersion, AllocatedLimitRecord.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id))
        expected_calamity = db.scalar(select(func.coalesce(func.sum(CalamityRecord.consent_amount), 0)).join(DatasetVersion, CalamityRecord.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id))
        assert result["total_canonical_works"] == expected_works
        assert result["total_expenditure"] == str(expected_expenditure)
        assert result["allocation"] == str(expected_allocation)
        assert result["calamity_amount"] == str(expected_calamity)


def test_house_state_district_mp_and_combined_filters_recalculate_from_database() -> None:
    with session() as db:
        scope = resolve_active_scope(db)
        sample = db.execute(select(CanonicalWork.house, CanonicalWork.state_name, CanonicalWork.district_or_ida, CanonicalWork.mp_source_name).join(DatasetVersion, CanonicalWork.first_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id, CanonicalWork.state_name.is_not(None), CanonicalWork.district_or_ida.is_not(None), CanonicalWork.mp_source_name.is_not(None)).limit(1)).one()
        filters = AnalyticsFilters(house=sample.house, state=sample.state_name, district_or_ida=sample.district_or_ida, mp=sample.mp_source_name)
        result = core_metrics(db, filters).data
        expected = db.scalar(select(func.count()).select_from(CanonicalWork).join(DatasetVersion, CanonicalWork.first_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id, CanonicalWork.house == sample.house, CanonicalWork.state_name == sample.state_name, CanonicalWork.district_or_ida == sample.district_or_ida, CanonicalWork.mp_source_name == sample.mp_source_name))
        assert result["total_canonical_works"] == expected


def test_expenditure_is_transaction_grain_and_unmatched_are_reported() -> None:
    with session() as db:
        scope = resolve_active_scope(db)
        result = expenditure_summary(db).data
        expected_count = db.scalar(select(func.count()).select_from(ExpenditureTransaction).join(DatasetVersion, ExpenditureTransaction.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id))
        expected_unmatched = db.scalar(select(func.count()).select_from(ExpenditureTransaction).join(DatasetVersion, ExpenditureTransaction.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id, ExpenditureTransaction.canonical_work_key.is_(None)))
        assert result["transaction_count"] == expected_count
        assert result["unmatched_expenditure_transactions"] == expected_unmatched


def test_unresolved_source_references_are_visible_in_quality_metrics() -> None:
    with session() as db:
        scope = resolve_active_scope(db)
        expected = db.scalar(select(func.count()).select_from(StagingRecommendedWork).where(StagingRecommendedWork.batch_id == scope.batch_id, StagingRecommendedWork.work_reference_status == "UNRESOLVED_SOURCE_WORK_REFERENCE"))
        assert data_quality_metrics(db).data["unresolved_work_references"] == expected


def test_lifecycle_uses_available_dates_without_inventing_deadline() -> None:
    with session() as db:
        result = lifecycle_summary(db).data
        assert result["terminology"] == "Observed lifecycle duration"
        assert result["recommendation_to_sanction"]["count_with_both_dates"] >= 0
        assert result["sanction_to_completion"]["count_with_both_dates"] >= 0
        assert result["right_censored_sanctioned_work_count"] >= 0


def test_geography_status_and_provenance_are_database_backed_and_deterministic() -> None:
    with session() as db:
        first = core_metrics(db)
        second = core_metrics(db)
        assert first.data == second.data
        assert first.provenance.batch_id == resolve_active_scope(db).batch_id
        assert summarize_by(db, "state").data["rows"]
        assert status_distribution(db).data["normalization"].startswith("Not available")

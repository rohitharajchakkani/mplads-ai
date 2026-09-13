"""Registered read-only tool handlers; no handler accepts SQL or table names."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from math import ceil, sqrt
from typing import Callable

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.ai.authorization import apply_scope, authorized_scope
from app.ai.registry import ToolArguments, ToolResult, get_tool
from app.api.deps import IntelligencePrincipal
from app.models import (
    AnalyticalAlert,
    AllocatedLimitRecord,
    CanonicalWork,
    CompletedWorkRecord,
    DatasetVersion,
    DuplicateCandidate,
    ExpenditureTransaction,
    MonitoringSignal,
    RecommendedWorkRecord,
    RiskAssessment,
    SanctionedWorkRecord,
)
from app.models.benchmarking import BenchmarkResult, Recommendation
from app.models.review import ReviewCase
from app.services.versioning_service import ActiveDatasetScope


@dataclass(frozen=True)
class _RawToolResult:
    data: dict
    result_count: int
    truncated: bool
    navigation_links: list[dict[str, str]]
    warnings: list[str]


def _work_key_column(model):
    if hasattr(model, "work_key"):
        return model.work_key
    if hasattr(model, "canonical_work_key"):
        return model.canonical_work_key
    raise ValueError("Approved AI tool cannot apply this verified work filter.")


def _apply_filters(statement, model, arguments: ToolArguments):
    """Apply only validated equality filters, deriving unavailable fields from works."""
    requested = arguments.model_dump(exclude_none=True, exclude={"limit", "view"})
    direct = {
        "house": "house",
        "state": "state_name",
        "district_or_ida": "district_or_ida",
        "mp": "mp_source_name",
        "work_key": "work_key",
    }
    unresolved: dict[str, str] = {}
    for name, value in requested.items():
        attribute = direct.get(name)
        if attribute and hasattr(model, attribute):
            statement = statement.where(getattr(model, attribute) == value)
        elif name == "work_key" and hasattr(model, "canonical_work_key"):
            statement = statement.where(model.canonical_work_key == value)
        else:
            unresolved[name] = value
    if unresolved:
        works = select(CanonicalWork.canonical_work_key)
        for name, value in unresolved.items():
            attribute = {"house": "house", "state": "state_name", "district_or_ida": "district_or_ida", "mp": "mp_source_name", "constituency": "constituency_name", "work_key": "canonical_work_key"}[name]
            works = works.where(getattr(CanonicalWork, attribute) == value)
        statement = statement.where(_work_key_column(model).in_(works))
    return statement


def _filtered(statement, model, arguments: ToolArguments, principal: IntelligencePrincipal):
    return _apply_filters(apply_scope(statement, principal, model), model, arguments)


def _dashboard(arguments: ToolArguments, session: Session, principal: IntelligencePrincipal, scope: ActiveDatasetScope) -> _RawToolResult:
    rows = _filtered(select(RiskAssessment).where(RiskAssessment.dataset_version == scope.release_version), RiskAssessment, arguments, principal)
    total = int(session.scalar(select(func.count()).select_from(rows.subquery())) or 0)
    return _RawToolResult({"monitored_works": total}, 1 if total else 0, False, [{"label": "Works Explorer", "href": "/works"}], [])


def _active_works(arguments: ToolArguments, principal: IntelligencePrincipal, scope: ActiveDatasetScope):
    """Return active-release canonical works under the existing server scope filter."""
    return _filtered(
        select(CanonicalWork).where(CanonicalWork.first_dataset_version_id.in_(scope.dataset_version_ids)),
        CanonicalWork,
        arguments,
        principal,
    )


def _linked_work_count(session: Session, works, model, scope: ActiveDatasetScope) -> int:
    return int(session.scalar(
        select(func.count(distinct(model.canonical_work_key)))
        .select_from(model)
        .join(works, model.canonical_work_key == works.c.canonical_work_key)
        .where(model.source_dataset_version_id.in_(scope.dataset_version_ids))
    ) or 0)


def _work_status_rows(session: Session, works, scope: ActiveDatasetScope, dimension: str, limit: int) -> tuple[list[dict], bool]:
    field = works.c.house if dimension == "house" else works.c.state_name
    selected_groups = select(field).select_from(works).group_by(field).order_by(func.count(distinct(works.c.canonical_work_key)).desc()).limit(limit).subquery()
    total_groups = int(session.scalar(select(func.count()).select_from(select(field).select_from(works).group_by(field).subquery())) or 0)
    rows = session.execute(
        select(field.label("group"), SanctionedWorkRecord.work_status_source.label("status"), func.count(distinct(SanctionedWorkRecord.canonical_work_key)).label("work_count"))
        .select_from(works.join(SanctionedWorkRecord, SanctionedWorkRecord.canonical_work_key == works.c.canonical_work_key))
        .where(
            SanctionedWorkRecord.source_dataset_version_id.in_(scope.dataset_version_ids),
            field.in_(select(selected_groups.c[0])),
        )
        .group_by(field, SanctionedWorkRecord.work_status_source)
        .order_by(field, SanctionedWorkRecord.work_status_source)
    ).all()
    key = "house" if dimension == "house" else "state"
    truncated = total_groups > limit or len(rows) > 25
    return [{key: row.group or "Not available", "status": row.status or "Not available", "work_count": int(row.work_count)} for row in rows[:25]], truncated


def _sanctioned_completed_rows(session: Session, works, scope: ActiveDatasetScope, dimension: str, limit: int) -> tuple[list[dict], bool]:
    field = works.c.house if dimension == "house" else works.c.state_name
    group_rows = session.execute(
        select(field.label("group"), func.count(distinct(works.c.canonical_work_key)).label("work_count"))
        .select_from(works)
        .group_by(field)
        .order_by(func.count(distinct(works.c.canonical_work_key)).desc())
        .limit(limit)
    ).all()
    total_groups = int(session.scalar(select(func.count()).select_from(select(field).select_from(works).group_by(field).subquery())) or 0)

    def counts(model) -> dict[str | None, int]:
        rows = session.execute(
            select(field.label("group"), func.count(distinct(model.canonical_work_key)).label("count"))
            .select_from(works.join(model, model.canonical_work_key == works.c.canonical_work_key))
            .where(model.source_dataset_version_id.in_(scope.dataset_version_ids))
            .group_by(field)
        ).all()
        return {row.group: int(row.count) for row in rows}

    sanctioned, completed = counts(SanctionedWorkRecord), counts(CompletedWorkRecord)
    key = "house" if dimension == "house" else "state"
    return [
        {key: row.group or "Not available", "sanctioned": sanctioned.get(row.group, 0), "completed": completed.get(row.group, 0), "work_count": int(row.work_count)}
        for row in group_rows
    ], total_groups > limit


def _lifecycle_histogram_rows(session: Session, works, scope: ActiveDatasetScope) -> list[dict]:
    """Bin only observed sanction-to-completion durations; no dates are filled in."""
    sanction_dates = (
        select(SanctionedWorkRecord.canonical_work_key.label("key"), func.min(SanctionedWorkRecord.sanction_date).label("sanction_date"))
        .join(works, SanctionedWorkRecord.canonical_work_key == works.c.canonical_work_key)
        .where(SanctionedWorkRecord.source_dataset_version_id.in_(scope.dataset_version_ids), SanctionedWorkRecord.sanction_date.is_not(None))
        .group_by(SanctionedWorkRecord.canonical_work_key)
        .subquery()
    )
    completion_dates = (
        select(CompletedWorkRecord.canonical_work_key.label("key"), func.min(CompletedWorkRecord.completion_date).label("completion_date"))
        .join(works, CompletedWorkRecord.canonical_work_key == works.c.canonical_work_key)
        .where(CompletedWorkRecord.source_dataset_version_id.in_(scope.dataset_version_ids), CompletedWorkRecord.completion_date.is_not(None))
        .group_by(CompletedWorkRecord.canonical_work_key)
        .subquery()
    )
    values = [
        float(row.duration)
        for row in session.execute(
            select((func.julianday(completion_dates.c.completion_date) - func.julianday(sanction_dates.c.sanction_date)).label("duration"))
            .select_from(sanction_dates.join(completion_dates, completion_dates.c.key == sanction_dates.c.key))
        )
        if row.duration is not None and row.duration >= 0
    ]
    if not values:
        return []
    minimum, maximum = min(values), max(values)
    if minimum == maximum:
        return [{"bin_start": minimum, "bin_end": maximum, "work_count": len(values)}]
    bin_count = min(12, max(2, ceil(sqrt(len(values)))))
    width, counts = (maximum - minimum) / bin_count, [0] * bin_count
    for value in values:
        counts[min(int((value - minimum) / width), bin_count - 1)] += 1
    return [
        {"bin_start": minimum + index * width, "bin_end": maximum if index == bin_count - 1 else minimum + (index + 1) * width, "work_count": count}
        for index, count in enumerate(counts)
    ]


def _work_summary(arguments: ToolArguments, session: Session, principal: IntelligencePrincipal, scope: ActiveDatasetScope) -> _RawToolResult:
    works = _active_works(arguments, principal, scope).subquery()
    total_works = int(session.scalar(select(func.count()).select_from(works)) or 0)
    view = arguments.view or "SUMMARY"
    if view == "WORKS_BY_HOUSE":
        rows = session.execute(select(works.c.house, func.count(distinct(works.c.canonical_work_key)).label("work_count")).group_by(works.c.house).order_by(func.count(distinct(works.c.canonical_work_key)).desc())).all()
        data = {"works_by_house": [{"house": row.house, "work_count": int(row.work_count)} for row in rows]}
        return _RawToolResult(data, len(rows), False, [{"label": "Works Explorer", "href": "/works"}], [])
    if view == "WORKS_BY_STATE":
        total_groups = int(session.scalar(select(func.count()).select_from(select(works.c.state_name).group_by(works.c.state_name).subquery())) or 0)
        rows = session.execute(select(works.c.state_name, func.count(distinct(works.c.canonical_work_key)).label("work_count")).group_by(works.c.state_name).order_by(func.count(distinct(works.c.canonical_work_key)).desc()).limit(arguments.limit)).all()
        data = {"works_by_state": [{"state": row.state_name or "Not available", "work_count": int(row.work_count)} for row in rows]}
        return _RawToolResult(data, len(rows), total_groups > len(rows), [{"label": "Works Explorer", "href": "/works"}], [])
    if view in {"WORK_STATUS_BY_HOUSE", "WORK_STATUS_BY_STATE"}:
        dimension = "house" if view.endswith("HOUSE") else "state"
        rows, truncated = _work_status_rows(session, works, scope, dimension, arguments.limit)
        data = {"work_status_by_house" if dimension == "house" else "work_status_by_state": rows}
        warnings = ["The verified status result is bounded to the approved maximum."] if truncated else []
        return _RawToolResult(data, len(rows), truncated, [{"label": "Works Explorer", "href": "/works"}], warnings)
    if view == "WORK_STATUS_DISTRIBUTION":
        rows = session.execute(
            select(SanctionedWorkRecord.work_status_source.label("status"), func.count(distinct(SanctionedWorkRecord.canonical_work_key)).label("work_count"))
            .select_from(works.join(SanctionedWorkRecord, SanctionedWorkRecord.canonical_work_key == works.c.canonical_work_key))
            .where(SanctionedWorkRecord.source_dataset_version_id.in_(scope.dataset_version_ids))
            .group_by(SanctionedWorkRecord.work_status_source)
            .order_by(func.count(distinct(SanctionedWorkRecord.canonical_work_key)).desc())
            .limit(arguments.limit)
        ).all()
        data = {"work_status_distribution": [{"status": row.status or "Not available", "work_count": int(row.work_count)} for row in rows]}
        return _RawToolResult(data, len(rows), len(rows) == arguments.limit, [{"label": "Works Explorer", "href": "/works"}], [])
    if view in {"SANCTIONED_COMPLETED_BY_HOUSE", "SANCTIONED_COMPLETED_BY_STATE"}:
        dimension = "house" if view.endswith("HOUSE") else "state"
        rows, truncated = _sanctioned_completed_rows(session, works, scope, dimension, arguments.limit)
        data = {"sanctioned_completed_by_house" if dimension == "house" else "sanctioned_completed_by_state": rows}
        return _RawToolResult(data, len(rows), truncated, [{"label": "Works Explorer", "href": "/works"}], [])
    if view == "LIFECYCLE_DURATION_DISTRIBUTION":
        rows = _lifecycle_histogram_rows(session, works, scope)
        return _RawToolResult({"sanction_to_completion_duration_distribution": rows}, len(rows), False, [{"label": "Lifecycle monitoring", "href": "/monitoring/lifecycle"}], [])

    recommended = _linked_work_count(session, works, RecommendedWorkRecord, scope)
    sanctioned = _linked_work_count(session, works, SanctionedWorkRecord, scope)
    completed = _linked_work_count(session, works, CompletedWorkRecord, scope)
    data = {
        "total_works": total_works,
        "recommended_works": recommended,
        "sanctioned_works": sanctioned,
        "completed_works": completed,
        "completion_ratio": completed / sanctioned if sanctioned else None,
    }
    return _RawToolResult(data, 1 if total_works else 0, False, [{"label": "Works Explorer", "href": "/works"}], [])


def _risk(arguments: ToolArguments, session: Session, principal: IntelligencePrincipal, scope: ActiveDatasetScope) -> _RawToolResult:
    rows = _filtered(select(RiskAssessment).where(RiskAssessment.dataset_version == scope.release_version), RiskAssessment, arguments, principal)
    counts = {str(band): int(count) for band, count in session.execute(rows.with_only_columns(RiskAssessment.risk_band, func.count()).group_by(RiskAssessment.risk_band)).all()}
    data = {"risk_distribution": counts, "higher_monitoring_priority": counts.get("HIGH", 0) + counts.get("VERY_HIGH", 0)}
    return _RawToolResult(data, len(counts), False, [{"label": "Risk-ranked works", "href": "/monitoring/risk"}], [])


def _duplicates(arguments: ToolArguments, session: Session, principal: IntelligencePrincipal, scope: ActiveDatasetScope) -> _RawToolResult:
    """Count only candidates whose two works are inside the authorized scope."""
    allowed = apply_scope(
        select(RiskAssessment.work_key).where(RiskAssessment.dataset_version == scope.release_version),
        principal,
        RiskAssessment,
    )
    statement = select(DuplicateCandidate).where(
        DuplicateCandidate.dataset_version == scope.release_version,
        DuplicateCandidate.work_a_key.in_(allowed),
        DuplicateCandidate.work_b_key.in_(allowed),
    )
    count = int(session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    return _RawToolResult({"potential_duplicate_candidates": count}, 1 if count else 0, False, [{"label": "Potential duplicates", "href": "/monitoring/duplicates"}], [])


def _alerts(arguments: ToolArguments, session: Session, principal: IntelligencePrincipal, scope: ActiveDatasetScope) -> _RawToolResult:
    rows = _filtered(select(AnalyticalAlert).where(AnalyticalAlert.dataset_version == scope.release_version), AnalyticalAlert, arguments, principal)
    counts = {str(severity): int(count) for severity, count in session.execute(rows.with_only_columns(AnalyticalAlert.severity, func.count()).group_by(AnalyticalAlert.severity)).all()}
    return _RawToolResult({"alert_severity_distribution": counts}, len(counts), False, [{"label": "Alerts", "href": "/monitoring/alerts"}], [])


def _recommendations(arguments: ToolArguments, session: Session, principal: IntelligencePrincipal, scope: ActiveDatasetScope) -> _RawToolResult:
    rows = _filtered(select(Recommendation).where(Recommendation.dataset_version == scope.release_version), Recommendation, arguments, principal)
    counts = {str(status): int(count) for status, count in session.execute(rows.with_only_columns(Recommendation.status, func.count()).group_by(Recommendation.status)).all()}
    return _RawToolResult({"recommendations_by_status": counts}, len(counts), False, [{"label": "Recommendations", "href": "/monitoring/recommendations"}], [])


def _reviews(arguments: ToolArguments, session: Session, principal: IntelligencePrincipal, scope: ActiveDatasetScope) -> _RawToolResult:
    rows = _filtered(select(ReviewCase).where(ReviewCase.dataset_version == scope.release_version), ReviewCase, arguments, principal)
    counts = {str(status): int(count) for status, count in session.execute(rows.with_only_columns(ReviewCase.status, func.count()).group_by(ReviewCase.status)).all()}
    return _RawToolResult({"review_cases_by_status": counts}, len(counts), False, [{"label": "Review queue", "href": "/monitoring/reviews"}], [])


def _benchmarks(arguments: ToolArguments, session: Session, principal: IntelligencePrincipal, scope: ActiveDatasetScope) -> _RawToolResult:
    rows = _filtered(select(BenchmarkResult).where(BenchmarkResult.dataset_version == scope.release_version), BenchmarkResult, arguments, principal)
    available = int(session.scalar(select(func.count()).select_from(rows.where(BenchmarkResult.benchmark_available.is_(True)).subquery())) or 0)
    bottlenecks = int(session.scalar(select(func.count()).select_from(rows.where(BenchmarkResult.bottleneck_flag.is_(True)).subquery())) or 0)
    return _RawToolResult({"available_comparisons": available, "potential_bottlenecks": bottlenecks}, int(bool(available or bottlenecks)), False, [{"label": "Peer benchmarking", "href": "/monitoring/benchmarking"}], [])


def _financial_by_state(arguments: ToolArguments, session: Session, principal: IntelligencePrincipal, scope: ActiveDatasetScope) -> _RawToolResult:
    statement = select(ExpenditureTransaction).join(CanonicalWork, ExpenditureTransaction.canonical_work_key == CanonicalWork.canonical_work_key).where(
        ExpenditureTransaction.canonical_work_key.is_not(None),
        ExpenditureTransaction.source_dataset_version_id.in_(scope.dataset_version_ids),
    )
    statement = _apply_filters(apply_scope(statement, principal, CanonicalWork), CanonicalWork, arguments)
    grouped = statement.with_only_columns(CanonicalWork.state_name, func.sum(ExpenditureTransaction.disbursed_amount).label("expenditure")).group_by(CanonicalWork.state_name)
    total = int(session.scalar(select(func.count()).select_from(grouped.subquery())) or 0)
    values = session.execute(grouped.order_by(func.sum(ExpenditureTransaction.disbursed_amount).desc()).limit(arguments.limit)).all()
    data = {"top_states_by_expenditure": [{"state": state or "Not available", "expenditure": str(amount or Decimal(0))} for state, amount in values]}
    return _RawToolResult(data, len(values), total > len(values), [{"label": "Financial monitoring", "href": "/monitoring/financial"}], [])


def _financial_by_house(arguments: ToolArguments, session: Session, principal: IntelligencePrincipal, scope: ActiveDatasetScope) -> _RawToolResult:
    statement = select(ExpenditureTransaction).join(CanonicalWork, ExpenditureTransaction.canonical_work_key == CanonicalWork.canonical_work_key).where(
        ExpenditureTransaction.canonical_work_key.is_not(None),
        ExpenditureTransaction.source_dataset_version_id.in_(scope.dataset_version_ids),
    )
    statement = _apply_filters(apply_scope(statement, principal, CanonicalWork), CanonicalWork, arguments)
    grouped = statement.with_only_columns(CanonicalWork.house, func.sum(ExpenditureTransaction.disbursed_amount).label("expenditure")).group_by(CanonicalWork.house)
    total = int(session.scalar(select(func.count()).select_from(grouped.subquery())) or 0)
    values = session.execute(grouped.order_by(func.sum(ExpenditureTransaction.disbursed_amount).desc()).limit(arguments.limit)).all()
    data = {"expenditure_by_house": [{"house": house, "expenditure": str(amount or Decimal(0))} for house, amount in values]}
    return _RawToolResult(data, len(values), total > len(values), [{"label": "Financial monitoring", "href": "/monitoring/financial"}], [])


def _linked_amounts_by_house(session: Session, works, model, amount_column, scope: ActiveDatasetScope) -> tuple[Decimal, dict[str, Decimal]]:
    total = session.scalar(
        select(func.coalesce(func.sum(amount_column), 0))
        .select_from(model)
        .join(works, model.canonical_work_key == works.c.canonical_work_key)
        .where(model.source_dataset_version_id.in_(scope.dataset_version_ids))
    ) or Decimal(0)
    rows = session.execute(
        select(works.c.house, func.coalesce(func.sum(amount_column), 0).label("amount"))
        .select_from(works.join(model, model.canonical_work_key == works.c.canonical_work_key))
        .where(model.source_dataset_version_id.in_(scope.dataset_version_ids))
        .group_by(works.c.house)
    ).all()
    return total, {str(row.house): row.amount or Decimal(0) for row in rows}


def _financial_summary(arguments: ToolArguments, session: Session, principal: IntelligencePrincipal, scope: ActiveDatasetScope) -> _RawToolResult:
    works = _active_works(arguments, principal, scope).subquery()
    matching_works = int(session.scalar(select(func.count()).select_from(works)) or 0)
    expenditure, expenditure_by_house = _linked_amounts_by_house(session, works, ExpenditureTransaction, ExpenditureTransaction.disbursed_amount, scope)
    sanctioned, sanctioned_by_house = _linked_amounts_by_house(session, works, SanctionedWorkRecord, SanctionedWorkRecord.sanction_amount, scope)
    allocation_statement = _filtered(
        select(AllocatedLimitRecord).where(AllocatedLimitRecord.source_dataset_version_id.in_(scope.dataset_version_ids)),
        AllocatedLimitRecord,
        arguments,
        principal,
    )
    allocation_scope = allocation_statement.subquery()
    allocation = session.scalar(select(func.coalesce(func.sum(allocation_scope.c.allocated_amount), 0))) or Decimal(0)
    allocation_rows = session.execute(
        select(
            allocation_scope.c.house,
            func.coalesce(func.sum(allocation_scope.c.allocated_amount), 0).label("amount"),
        ).group_by(allocation_scope.c.house)
    ).all()
    allocation_by_house = {str(row.house): row.amount or Decimal(0) for row in allocation_rows}
    view = arguments.view or "FINANCIAL_SUMMARY"
    if view == "SANCTIONED_AMOUNT_BY_HOUSE":
        rows = [{"house": house, "sanction_amount": str(amount)} for house, amount in sorted(sanctioned_by_house.items())]
        return _RawToolResult({"sanctioned_amount_by_house": rows}, len(rows), False, [{"label": "Financial monitoring", "href": "/monitoring/financial"}], [])
    if view == "ALLOCATION_BY_HOUSE":
        rows = [{"house": house, "allocation": str(amount)} for house, amount in sorted(allocation_by_house.items())]
        return _RawToolResult({"allocation_by_house": rows}, len(rows), False, [{"label": "Financial monitoring", "href": "/monitoring/financial"}], [])
    if view == "ALLOCATION_VS_EXPENDITURE_BY_HOUSE":
        houses = sorted(set(allocation_by_house) | set(expenditure_by_house))
        rows = [{"house": house, "allocation": str(allocation_by_house.get(house, Decimal(0))), "expenditure": str(expenditure_by_house.get(house, Decimal(0)))} for house in houses]
        return _RawToolResult({"allocation_vs_expenditure_by_house": rows}, len(rows), False, [{"label": "Financial monitoring", "href": "/monitoring/financial"}], [])
    data = {
        "financial_summary": {
            "total_recorded_expenditure": str(expenditure),
            "total_sanction_amount": str(sanctioned),
            "total_allocation": str(allocation),
        }
    }
    return _RawToolResult(data, 1 if matching_works else 0, False, [{"label": "Financial monitoring", "href": "/monitoring/financial"}], [])


def _lifecycle(arguments: ToolArguments, session: Session, principal: IntelligencePrincipal, scope: ActiveDatasetScope) -> _RawToolResult:
    statement = select(CompletedWorkRecord).join(CanonicalWork, CompletedWorkRecord.canonical_work_key == CanonicalWork.canonical_work_key).where(
        CompletedWorkRecord.canonical_work_key.is_not(None),
        CompletedWorkRecord.source_dataset_version_id.in_(scope.dataset_version_ids),
    )
    statement = _apply_filters(apply_scope(statement, principal, CanonicalWork), CanonicalWork, arguments)
    completed_rows = statement.subquery()
    completed_works = int(session.scalar(select(func.count(func.distinct(completed_rows.c.canonical_work_key)))) or 0)
    return _RawToolResult({"completed_works": completed_works}, 1 if completed_works else 0, False, [{"label": "Works Explorer", "href": "/works"}], [])


def _monitoring_signal_detail(arguments: ToolArguments, session: Session, principal: IntelligencePrincipal, scope: ActiveDatasetScope) -> _RawToolResult:
    if not arguments.work_key:
        return _RawToolResult({}, 0, False, [{"label": "Risk-ranked works", "href": "/monitoring/risk"}], ["Select an authorized work before requesting work-specific monitoring signals."])
    statement = _filtered(select(MonitoringSignal).where(MonitoringSignal.dataset_version == scope.release_version), MonitoringSignal, arguments, principal)
    total = int(session.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = session.scalars(statement.order_by(MonitoringSignal.generated_at.desc()).limit(arguments.limit)).all()
    data = {"monitoring_signals": [{"signal_id": row.signal_id, "category": row.category, "severity": row.severity, "title": row.title, "explanation": row.explanation} for row in rows]}
    return _RawToolResult(data, len(rows), total > len(rows), [{"label": "Risk-ranked works", "href": "/monitoring/risk"}], [])


def _executive(arguments: ToolArguments, session: Session, principal: IntelligencePrincipal, scope: ActiveDatasetScope) -> _RawToolResult:
    # The protected executive service already implements evidence-backed counts
    # and its own scope filter. Only its declared equality filters are supplied.
    from app.api.executive import _summary

    values = _summary(
        session,
        principal,
        scope,
        **{key: value for key, value in arguments.model_dump(exclude_none=True).items() if key in {"house", "state", "district_or_ida", "mp"}},
    )
    data = values.model_dump(exclude={"provenance"})
    result_count = sum(1 for value in data.values() if value not in ({}, 0, None))
    return _RawToolResult(data, result_count, False, [{"label": "Executive command center", "href": "/monitoring/executive"}], [])


TOOL_HANDLERS: dict[str, Callable[[ToolArguments, Session, IntelligencePrincipal, ActiveDatasetScope], _RawToolResult]] = {
    "get_dashboard_summary": _dashboard,
    "get_work_summary": _work_summary,
    "get_financial_by_state": _financial_by_state,
    "get_financial_by_house": _financial_by_house,
    "get_financial_summary": _financial_summary,
    "get_lifecycle_summary": _lifecycle,
    "get_duplicate_summary": _duplicates,
    "get_risk_summary": _risk,
    "get_monitoring_signal_detail": _monitoring_signal_detail,
    "get_alert_summary": _alerts,
    "get_recommendations": _recommendations,
    "get_review_summary": _reviews,
    "get_benchmark_result": _benchmarks,
    "get_executive_summary": _executive,
}


def execute_tool(tool_name: str, arguments: ToolArguments, session: Session, principal: IntelligencePrincipal, scope: ActiveDatasetScope) -> ToolResult:
    """Execute one registered, read-only handler and normalize its verified output."""
    spec = get_tool(tool_name)
    if principal.role not in spec.allowed_roles:
        raise ValueError("Your role is not authorized for this AI tool.")
    handler = TOOL_HANDLERS.get(tool_name)
    if handler is None:
        raise ValueError("Approved AI tool handler is unavailable.")
    raw = handler(arguments, session, principal, scope)
    return ToolResult(
        tool_name=tool_name,
        success=raw.result_count > 0,
        data=raw.data,
        result_count=raw.result_count,
        truncated=raw.truncated,
        filters_applied=arguments.model_dump(exclude_none=True),
        scope=authorized_scope(principal),
        dataset_version=scope.release_version,
        generated_at=datetime.now(UTC).isoformat(),
        warnings=raw.warnings,
        navigation_links=raw.navigation_links,
    )

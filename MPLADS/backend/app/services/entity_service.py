"""Database-backed entity browsing, detail, and search services for API use."""

from __future__ import annotations

import base64
from math import ceil
from typing import Any

from sqlalchemy import case, distinct, func, literal, or_, select, union_all
from sqlalchemy.orm import Session

from app.analytics.dashboard_service import core_metrics
from app.analytics.normalization import normalize_house, normalize_text, normalized_contains
from app.analytics.query import active_works_statement
from app.analytics.types import AnalyticsFilters, AnalyticsResult, provenance
from app.models import (
    CanonicalWork, CompletedWorkRecord, DatasetVersion, ExpenditureTransaction, RecommendedWorkRecord,
    SanctionedWorkRecord,
)
from app.services.versioning_service import ActiveDatasetScope, resolve_active_scope


def _encode(*values: str | None) -> str:
    joined = "\x1f".join(value or "" for value in values)
    return base64.urlsafe_b64encode(joined.encode()).decode().rstrip("=")


def _decode(identifier: str, fields: int) -> tuple[str, ...]:
    try:
        decoded = base64.urlsafe_b64decode(identifier + "=" * (-len(identifier) % 4)).decode().split("\x1f")
    except Exception as exc:
        raise ValueError("Invalid entity identifier.") from exc
    if len(decoded) != fields:
        raise ValueError("Invalid entity identifier.")
    return tuple(decoded)


def _page(statement, page: int, page_size: int, session: Session):
    if page < 1 or page_size < 1 or page_size > 100:
        raise ValueError("page must be at least 1 and page_size must be between 1 and 100.")
    total = int(session.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0)
    rows = session.execute(statement.limit(page_size).offset((page - 1) * page_size)).all()
    return rows, {"total": total, "page": page, "page_size": page_size, "total_pages": ceil(total / page_size) if total else 0}


def list_mps(session: Session, filters: AnalyticsFilters, search: str | None, page: int, page_size: int, sort: str = "name") -> AnalyticsResult:
    scope = resolve_active_scope(session)
    works = active_works_statement(scope, filters).subquery()
    statement = select(works.c.house, works.c.mp_source_name, func.min(works.c.state_name).label("state_name"), func.min(works.c.constituency_name).label("constituency_name"), func.count(distinct(works.c.canonical_work_key)).label("work_count")).where(works.c.mp_source_name.is_not(None)).group_by(works.c.house, works.c.mp_source_name)
    if search:
        statement = statement.where(normalized_contains(works.c.mp_source_name, search))
    if sort not in {"name", "work_count"}:
        raise ValueError("Unsupported sort field.")
    statement = statement.order_by(func.count(distinct(works.c.canonical_work_key)).desc() if sort == "work_count" else works.c.mp_source_name.asc())
    rows, pagination = _page(statement, page, page_size, session)
    return AnalyticsResult({"items": [{"mp_id": _encode(row.house, row.mp_source_name), "name": row.mp_source_name, "house": row.house, "state": row.state_name, "constituency": row.constituency_name, "work_count": int(row.work_count)} for row in rows], "pagination": pagination}, provenance("entity_service.list_mps", scope, filters))


def mp_detail(session: Session, mp_id: str) -> AnalyticsResult | None:
    house, mp = _decode(mp_id, 2)
    filters = AnalyticsFilters(house=house, mp=mp)
    scope = resolve_active_scope(session)
    identity = session.execute(active_works_statement(scope, filters).with_only_columns(CanonicalWork.house, CanonicalWork.mp_source_name, func.min(CanonicalWork.state_name).label("state"), func.min(CanonicalWork.constituency_name).label("constituency")).group_by(CanonicalWork.house, CanonicalWork.mp_source_name)).first()
    if identity is None:
        return None
    metrics = core_metrics(session, filters).data
    from app.analytics.trend_analytics_service import expenditure_trend
    from app.analytics.work_analytics_service import status_distribution
    return AnalyticsResult({"mp_id": mp_id, "name": identity.mp_source_name, "house": identity.house, "state": identity.state, "constituency": identity.constituency, "metrics": metrics, "status_distribution": status_distribution(session, filters).data, "expenditure_trend": expenditure_trend(session, filters).data}, provenance("entity_service.mp_detail", scope, filters))


def list_states(session: Session, filters: AnalyticsFilters, page: int, page_size: int) -> AnalyticsResult:
    scope = resolve_active_scope(session)
    works = active_works_statement(scope, filters).subquery()
    statement = select(works.c.state_name, func.count(distinct(works.c.canonical_work_key)).label("work_count")).where(works.c.state_name.is_not(None)).group_by(works.c.state_name).order_by(func.count(distinct(works.c.canonical_work_key)).desc())
    rows, pagination = _page(statement, page, page_size, session)
    return AnalyticsResult({"items": [{"state_id": _encode(row.state_name), "name": row.state_name, "work_count": int(row.work_count)} for row in rows], "pagination": pagination}, provenance("entity_service.list_states", scope, filters))


def state_detail(session: Session, state_id: str) -> AnalyticsResult | None:
    (state,) = _decode(state_id, 1)
    filters = AnalyticsFilters(state=state)
    scope = resolve_active_scope(session)
    if session.scalar(active_works_statement(scope, filters).with_only_columns(CanonicalWork.canonical_work_key).limit(1)) is None:
        return None
    from app.analytics.trend_analytics_service import expenditure_trend
    from app.analytics.work_analytics_service import status_distribution
    return AnalyticsResult({"state_id": state_id, "name": state, "metrics": core_metrics(session, filters).data, "status_distribution": status_distribution(session, filters).data, "expenditure_trend": expenditure_trend(session, filters).data}, provenance("entity_service.state_detail", scope, filters))


def list_districts(session: Session, filters: AnalyticsFilters, page: int, page_size: int) -> AnalyticsResult:
    scope = resolve_active_scope(session)
    works = active_works_statement(scope, filters).subquery()
    statement = select(works.c.state_name, works.c.district_or_ida, func.count(distinct(works.c.canonical_work_key)).label("work_count")).where(works.c.district_or_ida.is_not(None)).group_by(works.c.state_name, works.c.district_or_ida).order_by(func.count(distinct(works.c.canonical_work_key)).desc())
    rows, pagination = _page(statement, page, page_size, session)
    return AnalyticsResult({"items": [{"district_id": _encode(row.state_name, row.district_or_ida), "state": row.state_name, "district_or_ida": row.district_or_ida, "work_count": int(row.work_count)} for row in rows], "pagination": pagination}, provenance("entity_service.list_districts", scope, filters))


def district_detail(session: Session, district_id: str) -> AnalyticsResult | None:
    state, district = _decode(district_id, 2)
    filters = AnalyticsFilters(state=state or None, district_or_ida=district)
    scope = resolve_active_scope(session)
    if session.scalar(active_works_statement(scope, filters).with_only_columns(CanonicalWork.canonical_work_key).limit(1)) is None:
        return None
    from app.analytics.trend_analytics_service import expenditure_trend
    from app.analytics.work_analytics_service import status_distribution
    return AnalyticsResult({"district_id": district_id, "state": state or None, "district_or_ida": district, "metrics": core_metrics(session, filters).data, "status_distribution": status_distribution(session, filters).data, "expenditure_trend": expenditure_trend(session, filters).data}, provenance("entity_service.district_detail", scope, filters))


def list_works(session: Session, filters: AnalyticsFilters, search: str | None, page: int, page_size: int, sort: str = "work_id") -> AnalyticsResult:
    scope = resolve_active_scope(session)
    statement = active_works_statement(scope, filters)
    if search:
        statement = statement.where(or_(*[
            normalized_contains(column, search) for column in (CanonicalWork.normalized_work_id, CanonicalWork.work_description, CanonicalWork.mp_source_name, CanonicalWork.state_name, CanonicalWork.district_or_ida, CanonicalWork.constituency_name)
        ]))
    sorts = {"work_id": CanonicalWork.normalized_work_id.asc(), "state": CanonicalWork.state_name.asc(), "mp": CanonicalWork.mp_source_name.asc(), "financial_year": CanonicalWork.financial_year.desc()}
    if sort not in sorts:
        raise ValueError("Unsupported sort field.")
    statement = statement.order_by(sorts[sort])
    rows, pagination = _page(statement, page, page_size, session)
    return AnalyticsResult({"items": [_work_payload(row[0]) for row in rows], "pagination": pagination}, provenance("entity_service.list_works", scope, filters))


def _work_payload(work: CanonicalWork) -> dict[str, Any]:
    return {"canonical_work_key": work.canonical_work_key, "work_id": work.normalized_work_id, "house": work.house, "financial_year": work.financial_year, "mp": work.mp_source_name, "state": work.state_name, "district_or_ida": work.district_or_ida, "constituency": work.constituency_name, "work_description": work.work_description, "source_work_category": work.work_category_source, "sector": None, "subsector": None}


def work_detail(session: Session, work_key: str) -> AnalyticsResult | None:
    scope = resolve_active_scope(session)
    work = session.scalar(active_works_statement(scope, AnalyticsFilters()).where(CanonicalWork.canonical_work_key == work_key))
    if work is None:
        return None
    active_versions = select(DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id)
    recommended = session.scalars(select(RecommendedWorkRecord).where(RecommendedWorkRecord.canonical_work_key == work_key, RecommendedWorkRecord.source_dataset_version_id.in_(active_versions))).all()
    sanctioned = session.scalars(select(SanctionedWorkRecord).where(SanctionedWorkRecord.canonical_work_key == work_key, SanctionedWorkRecord.source_dataset_version_id.in_(active_versions))).all()
    completed = session.scalars(select(CompletedWorkRecord).where(CompletedWorkRecord.canonical_work_key == work_key, CompletedWorkRecord.source_dataset_version_id.in_(active_versions))).all()
    transaction_summary = session.execute(select(func.coalesce(func.sum(ExpenditureTransaction.disbursed_amount), 0).label("total"), func.count(ExpenditureTransaction.id).label("count"), func.min(ExpenditureTransaction.expenditure_date).label("first_date"), func.max(ExpenditureTransaction.expenditure_date).label("latest_date")).where(ExpenditureTransaction.canonical_work_key == work_key, ExpenditureTransaction.source_dataset_version_id.in_(active_versions))).one()
    transactions = session.scalars(select(ExpenditureTransaction).where(ExpenditureTransaction.canonical_work_key == work_key, ExpenditureTransaction.source_dataset_version_id.in_(active_versions)).order_by(ExpenditureTransaction.expenditure_date).limit(100)).all()
    data = {"work": _work_payload(work), "recommendations": [{"date": row.recommended_date, "amount": str(row.recommended_amount), "work_reference_status": row.work_reference_status} for row in recommended], "sanctions": [{"recommended_date": row.recommended_date, "sanction_date": row.sanction_date, "amount": str(row.sanction_amount), "source_status": row.work_status_source} for row in sanctioned], "completions": [{"completion_date": row.completion_date, "reported_disbursed_amount": str(row.completed_reported_disbursed_amount)} for row in completed], "expenditure": {"total": str(transaction_summary.total), "transaction_count": int(transaction_summary.count), "first_expenditure_date": transaction_summary.first_date, "latest_expenditure_date": transaction_summary.latest_date, "transactions": [{"date": row.expenditure_date, "vendor_name": row.vendor_name, "payment_status": row.payment_status_source, "amount": str(row.disbursed_amount)} for row in transactions], "transactions_truncated": int(transaction_summary.count) > len(transactions)}, "provenance": {"release_version": scope.release_version, "batch_id": scope.batch_id, "source_dataset_versions": sorted({row.source_dataset_version_id for row in [*recommended, *sanctioned, *completed, *transactions]})}}
    return AnalyticsResult(data, provenance("entity_service.work_detail", scope, AnalyticsFilters()))


def search(session: Session, query: str, page: int, page_size: int) -> AnalyticsResult:
    scope = resolve_active_scope(session)
    cleaned_query = normalize_text(query)
    if cleaned_query is None:
        raise ValueError("Search query cannot be blank.")

    q_lower = cleaned_query.lower()
    pattern = f"%{q_lower}%"
    normalized_house = normalize_house(cleaned_query)

    base = select(CanonicalWork).join(DatasetVersion, CanonicalWork.first_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id)

    work_conditions = [
        func.lower(CanonicalWork.normalized_work_id).like(pattern),
        func.lower(CanonicalWork.work_description).like(pattern),
    ]
    if normalized_house:
        work_conditions.append(CanonicalWork.house == normalized_house)

    works = base.with_only_columns(
        literal("WORK").label("entity_type"),
        CanonicalWork.canonical_work_key.label("identifier"),
        CanonicalWork.normalized_work_id.label("label"),
        func.coalesce(CanonicalWork.work_description, CanonicalWork.normalized_work_id).label("title"),
        CanonicalWork.work_description.label("description"),
        CanonicalWork.house.label("house"),
        CanonicalWork.state_name.label("state"),
        CanonicalWork.district_or_ida.label("district"),
        CanonicalWork.mp_source_name.label("mp"),
        CanonicalWork.constituency_name.label("constituency"),
    ).where(or_(*work_conditions))

    mps = base.with_only_columns(
        literal("MP").label("entity_type"),
        literal(None).label("identifier"),
        CanonicalWork.mp_source_name.label("label"),
        CanonicalWork.mp_source_name.label("title"),
        func.coalesce(CanonicalWork.constituency_name, CanonicalWork.state_name).label("description"),
        CanonicalWork.house.label("house"),
        CanonicalWork.state_name.label("state"),
        literal(None).label("district"),
        CanonicalWork.mp_source_name.label("mp"),
        CanonicalWork.constituency_name.label("constituency"),
    ).where(func.lower(CanonicalWork.mp_source_name).like(pattern)).distinct()

    states = base.with_only_columns(
        literal("STATE").label("entity_type"),
        literal(None).label("identifier"),
        CanonicalWork.state_name.label("label"),
        CanonicalWork.state_name.label("title"),
        literal("State / Union Territory").label("description"),
        literal(None).label("house"),
        CanonicalWork.state_name.label("state"),
        literal(None).label("district"),
        literal(None).label("mp"),
        literal(None).label("constituency"),
    ).where(func.lower(CanonicalWork.state_name).like(pattern)).distinct()

    districts = base.with_only_columns(
        literal("DISTRICT_OR_IDA").label("entity_type"),
        literal(None).label("identifier"),
        CanonicalWork.district_or_ida.label("label"),
        CanonicalWork.district_or_ida.label("title"),
        CanonicalWork.state_name.label("description"),
        literal(None).label("house"),
        CanonicalWork.state_name.label("state"),
        CanonicalWork.district_or_ida.label("district"),
        literal(None).label("mp"),
        literal(None).label("constituency"),
    ).where(func.lower(CanonicalWork.district_or_ida).like(pattern)).distinct()

    constituencies = base.with_only_columns(
        literal("CONSTITUENCY").label("entity_type"),
        literal(None).label("identifier"),
        CanonicalWork.constituency_name.label("label"),
        CanonicalWork.constituency_name.label("title"),
        CanonicalWork.state_name.label("description"),
        CanonicalWork.house.label("house"),
        CanonicalWork.state_name.label("state"),
        literal(None).label("district"),
        literal(None).label("mp"),
        CanonicalWork.constituency_name.label("constituency"),
    ).where(func.lower(CanonicalWork.constituency_name).like(pattern)).distinct()

    union_query = union_all(states, districts, mps, works, constituencies).subquery()
    type_priority = case(
        (union_query.c.entity_type == "STATE", 1),
        (union_query.c.entity_type == "DISTRICT_OR_IDA", 2),
        (union_query.c.entity_type == "MP", 3),
        (union_query.c.entity_type == "WORK", 4),
        else_=5,
    )
    statement = select(union_query).order_by(type_priority, union_query.c.label)
    rows, pagination = _page(statement, page, page_size, session)
    items = []
    for row in rows:
        item = row._mapping
        identifier = item["identifier"]
        if item["entity_type"] == "MP":
            identifier = _encode(item["house"], item["label"])
        elif item["entity_type"] == "STATE":
            identifier = _encode(item["state"])
        elif item["entity_type"] == "DISTRICT_OR_IDA":
            identifier = _encode(item["state"], item["district"])
        elif item["entity_type"] == "CONSTITUENCY":
            identifier = _encode(item["house"], item["constituency"])
        items.append({
            "entity_type": item["entity_type"],
            "identifier": identifier,
            "label": item["label"],
            "title": item["title"] or item["label"],
            "description": item["description"],
            "house": item["house"],
            "state": item["state"],
            "district": item["district"],
            "mp": item["mp"],
            "constituency": item["constituency"],
        })
    return AnalyticsResult({"items": items, "pagination": pagination}, provenance("entity_service.search", scope, AnalyticsFilters()))

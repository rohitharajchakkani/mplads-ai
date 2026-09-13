"""Safe, database-backed entity and page-context resolution for Ask AI."""
from __future__ import annotations

import base64
import re
from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.ai.authorization import apply_scope
from app.analytics.normalization import normalize_text, normalized_column
from app.api.deps import IntelligencePrincipal
from app.models import CanonicalWork, ReviewCase, RiskAssessment


ALLOWED_CONTEXT_KEYS = frozenset({"current_work_key", "current_mp_id", "current_state_id", "current_district_id", "current_case_id"})


class EntityChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: str
    label: str
    filters: dict[str, str]
    navigation_link: dict[str, str] | None = None


class EntityResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["NONE", "RESOLVED", "AMBIGUOUS", "NOT_FOUND"] = "NONE"
    filters: dict[str, str] = Field(default_factory=dict)
    choices: list[EntityChoice] = Field(default_factory=list)
    message: str | None = None


def _decode(identifier: str, expected_fields: int) -> tuple[str, ...]:
    """Decode only the opaque identifiers emitted by the public entity APIs."""
    try:
        values = base64.urlsafe_b64decode(identifier + "=" * (-len(identifier) % 4)).decode().split("\x1f")
    except Exception as exc:
        raise ValueError("Invalid page context identifier.") from exc
    if len(values) != expected_fields or any(not value for value in values):
        raise ValueError("Invalid page context identifier.")
    return tuple(values)


def _encode(*values: str) -> str:
    return base64.urlsafe_b64encode("\x1f".join(values).encode()).decode().rstrip("=")


def _authorized_risks(principal: IntelligencePrincipal, dataset_version: str):
    return apply_scope(
        select(RiskAssessment).where(RiskAssessment.dataset_version == dataset_version),
        principal,
        RiskAssessment,
    )


def _authorized_works(principal: IntelligencePrincipal, dataset_version: str):
    work_keys = _authorized_risks(principal, dataset_version).with_only_columns(RiskAssessment.work_key)
    return select(CanonicalWork).where(CanonicalWork.canonical_work_key.in_(work_keys))


def _first_or_not_found(statement, session: Session) -> bool:
    return session.scalar(statement.limit(1)) is not None


def resolve_page_context(context: dict[str, str], session: Session, principal: IntelligencePrincipal, dataset_version: str) -> EntityResolution:
    """Validate opaque page context and ensure every referenced entity is in scope."""
    unknown = set(context) - ALLOWED_CONTEXT_KEYS
    if unknown:
        raise ValueError("Unsupported Ask AI context field.")
    if not context:
        return EntityResolution()

    filters: dict[str, str] = {}
    def add(values: dict[str, str]) -> None:
        for key, value in values.items():
            if key in filters and filters[key] != value:
                raise ValueError("Conflicting page context cannot be used.")
            filters[key] = value

    if work_key := context.get("current_work_key"):
        allowed = _authorized_risks(principal, dataset_version).where(RiskAssessment.work_key == work_key)
        if not _first_or_not_found(allowed, session):
            return EntityResolution(status="NOT_FOUND", message="The current work is not available in your authorized monitoring scope.")
        add({"work_key": work_key})
    if mp_id := context.get("current_mp_id"):
        house, mp = _decode(mp_id, 2)
        allowed = _authorized_risks(principal, dataset_version).where(RiskAssessment.house == house, RiskAssessment.mp_source_name == mp)
        if not _first_or_not_found(allowed, session):
            return EntityResolution(status="NOT_FOUND", message="The current MP is not available in your authorized monitoring scope.")
        add({"house": house, "mp": mp})
    if state_id := context.get("current_state_id"):
        (state,) = _decode(state_id, 1)
        allowed = _authorized_risks(principal, dataset_version).where(RiskAssessment.state_name == state)
        if not _first_or_not_found(allowed, session):
            return EntityResolution(status="NOT_FOUND", message="The current State is not available in your authorized monitoring scope.")
        add({"state": state})
    if district_id := context.get("current_district_id"):
        state, district = _decode(district_id, 2)
        allowed = _authorized_risks(principal, dataset_version).where(RiskAssessment.state_name == state, RiskAssessment.district_or_ida == district)
        if not _first_or_not_found(allowed, session):
            return EntityResolution(status="NOT_FOUND", message="The current District/IDA is not available in your authorized monitoring scope.")
        add({"state": state, "district_or_ida": district})
    if case_id := context.get("current_case_id"):
        allowed = apply_scope(
            select(ReviewCase).where(ReviewCase.case_id == case_id, ReviewCase.dataset_version == dataset_version),
            principal,
            ReviewCase,
        )
        case = session.scalar(allowed.limit(1))
        if case is None:
            return EntityResolution(status="NOT_FOUND", message="The current review case is not available in your authorized monitoring scope.")
        add({key: value for key, value in {"house": case.house, "state": case.state_name, "district_or_ida": case.district_or_ida, "mp": case.mp_source_name, "work_key": case.canonical_work_key}.items() if value})
    return EntityResolution(status="RESOLVED", filters=filters)


def _choice(entity_type: str, label: str, filters: dict[str, str], href: str | None) -> EntityChoice:
    return EntityChoice(entity_type=entity_type, label=label, filters=filters, navigation_link={"label": f"Open {label}", "href": href} if href else None)


def resolve_question_entities(question: str, session: Session, principal: IntelligencePrincipal, dataset_version: str) -> EntityResolution:
    """Resolve only exact database labels found in the question; never guess an entity."""
    normalized = normalize_text(question.casefold()) or ""
    if len(normalized.strip()) < 3:
        return EntityResolution()
    works = _authorized_works(principal, dataset_version).subquery()
    choices: dict[tuple[str, str, tuple[tuple[str, str], ...]], EntityChoice] = {}

    def add(entity_type: str, label: str | None, filters: dict[str, str], href: str | None) -> None:
        normalized_label = normalize_text(label.casefold()) if label else None
        if not normalized_label or len(normalized_label) < 3 or not re.search(rf"(?<!\w){re.escape(normalized_label)}(?!\w)", normalized):
            return
        key = (entity_type, label, tuple(sorted(filters.items())))
        choices[key] = _choice(entity_type, label, filters, href)

    contains_state = func.instr(normalized, normalized_column(works.c.state_name)) > 0
    for state in session.scalars(select(distinct(works.c.state_name)).where(works.c.state_name.is_not(None), contains_state).limit(6)):
        add("STATE", state, {"state": state}, f"/states/{_encode(state)}")
    contains_district = func.instr(normalized, normalized_column(works.c.district_or_ida)) > 0
    for state, district in session.execute(select(works.c.state_name, works.c.district_or_ida).where(works.c.state_name.is_not(None), works.c.district_or_ida.is_not(None), contains_district).distinct().limit(6)).all():
        add("DISTRICT", district, {"state": state, "district_or_ida": district}, f"/districts/{_encode(state, district)}")
    contains_mp = func.instr(normalized, normalized_column(works.c.mp_source_name)) > 0
    for house, mp in session.execute(select(works.c.house, works.c.mp_source_name).where(works.c.mp_source_name.is_not(None), contains_mp).distinct().limit(6)).all():
        add("MP", mp, {"house": house, "mp": mp}, f"/mps/{_encode(house, mp)}")
    contains_constituency = func.instr(normalized, normalized_column(works.c.constituency_name)) > 0
    for house, constituency in session.execute(select(works.c.house, works.c.constituency_name).where(works.c.constituency_name.is_not(None), contains_constituency).distinct().limit(6)).all():
        add("CONSTITUENCY", constituency, {"house": house, "constituency": constituency}, None)
    contains_work = func.instr(normalized, normalized_column(works.c.normalized_work_id)) > 0
    for work_key, work_id in session.execute(select(works.c.canonical_work_key, works.c.normalized_work_id).where(contains_work).limit(6)).all():
        add("WORK", work_id, {"work_key": work_key}, f"/works/{quote(work_key, safe='')}")

    matched = list(choices.values())
    if not matched:
        return EntityResolution()
    if len(matched) == 1:
        return EntityResolution(status="RESOLVED", filters=matched[0].filters, choices=matched)
    return EntityResolution(
        status="AMBIGUOUS",
        choices=matched[:5],
        message="I found multiple matching entities in your authorized data. Please specify the State, District/IDA, House, or MP.",
    )


def merge_filters(*filter_sets: dict[str, str]) -> dict[str, str]:
    """Page context is authoritative; conflicting natural-language filters are rejected."""
    merged: dict[str, str] = {}
    for values in filter_sets:
        for key, value in values.items():
            if key in merged and merged[key] != value:
                raise ValueError("The question conflicts with the authorized page context.")
            merged[key] = value
    return merged

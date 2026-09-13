"""Protected, append-only human review workflow over persisted monitoring evidence."""
from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import IntelligencePrincipal, get_db, require_intelligence_principal, require_review_actor
from app.models import AnalyticalAlert, AnalyticsRun, DuplicateCandidate, MonitoringSignal, RiskAssessment
from app.models.review import ReviewCase, ReviewCaseEvent, ReviewCaseEvidenceSnapshot, ReviewEscalation, ReviewNotification
from app.schemas.intelligence import ProtectedProvenance
from app.schemas.reviews import CaseActionRequest, CaseCreateRequest, NotificationResponse, ReviewCaseDetail, ReviewCaseItem, ReviewEventResponse, ReviewPage, ReviewSummary
from app.services.versioning_service import resolve_active_scope

router = APIRouter(dependencies=[Depends(require_intelligence_principal)])

STATUSES = {"OPEN", "ASSIGNED", "UNDER_REVIEW", "FOLLOW_UP_REQUIRED", "RESOLVED", "CLOSED", "REOPENED"}
RESOLUTION_TYPES = {"INFORMATION_VERIFIED", "NO_FURTHER_ACTION", "CORRECTION_REQUIRED", "FOLLOW_UP_COMPLETED", "REFERRED"}


def _now() -> datetime:
    return datetime.now(UTC)


def _provenance(case: ReviewCase) -> ProtectedProvenance:
    return ProtectedProvenance(dataset_version=case.dataset_version, generated_at=case.updated_at)


def _scope(statement, principal: IntelligencePrincipal):
    if principal.role in {"MINISTRY", "PLATFORM_ADMINISTRATOR"}:
        return statement
    if principal.role == "MP":
        return statement.where(ReviewCase.mp_source_name == principal.mp_scope)
    if principal.role == "DISTRICT_AUTHORITY":
        return statement.where(ReviewCase.district_or_ida == principal.district_scope)
    return statement.where(ReviewCase.state_name == principal.state_scope)


def _assert_context_scope(principal: IntelligencePrincipal, *, mp: str | None, district: str | None, state: str | None) -> None:
    if principal.role in {"MINISTRY", "PLATFORM_ADMINISTRATOR"}:
        return
    allowed = (principal.role == "MP" and mp == principal.mp_scope) or (principal.role == "DISTRICT_AUTHORITY" and district == principal.district_scope) or (principal.role == "STATE_NODAL_AUTHORITY" and state == principal.state_scope)
    if not allowed:
        raise HTTPException(status_code=404, detail={"code": "REVIEW_SOURCE_NOT_FOUND", "message": "No reviewable monitoring record exists in the authorized scope."})


def _priority(severity: str) -> str:
    return {"VERY_HIGH": "VERY_HIGH", "HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW", "INFO": "LOW"}.get(severity, "LOW")


def _item(case: ReviewCase) -> ReviewCaseItem:
    return ReviewCaseItem(case_id=case.case_id, source_alert_id=case.source_alert_id, source_signal_id=case.source_signal_id, canonical_work_key=case.canonical_work_key, house=case.house, state_name=case.state_name, district_or_ida=case.district_or_ida, mp_source_name=case.mp_source_name, status=case.status, priority=case.priority, assignee=case.assignee, dataset_version=case.dataset_version, version=case.version, created_at=case.created_at, updated_at=case.updated_at, closed_at=case.closed_at)


def _event(case: ReviewCase, actor: str, action: str, *, metadata: dict | None = None, comment: str | None = None) -> ReviewCaseEvent:
    return ReviewCaseEvent(event_id=f"rev_evt_{uuid4().hex}", case_id=case.case_id, actor=actor, occurred_at=_now(), action=action, metadata_json=metadata or {}, comment=comment)


def _notification(event: ReviewCaseEvent, case: ReviewCase, recipient: str | None, message: str) -> ReviewNotification | None:
    if not recipient or recipient == event.actor:
        return None
    return ReviewNotification(notification_id=f"rev_ntf_{uuid4().hex}", event_id=event.event_id, case_id=case.case_id, recipient=recipient, state="UNREAD", message=message, created_at=event.occurred_at, read_at=None, acknowledged_at=None)


def _case_or_404(case_id: str, principal: IntelligencePrincipal, db: Session) -> ReviewCase:
    case = db.scalar(_scope(select(ReviewCase).where(ReviewCase.case_id == case_id), principal))
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "REVIEW_CASE_NOT_FOUND", "message": "No review case exists in the authorized scope."})
    return case


def _assert_version(case: ReviewCase, version: int) -> None:
    if case.version != version:
        raise HTTPException(status_code=409, detail={"code": "REVIEW_CASE_VERSION_CONFLICT", "message": "This review case changed. Refresh it before applying another action."})


def _commit_action(case: ReviewCase, event: ReviewCaseEvent, db: Session, notification: ReviewNotification | None = None) -> ReviewCaseItem:
    case.version += 1
    case.updated_at = event.occurred_at
    db.add(event)
    if notification:
        db.add(notification)
    db.commit()
    db.refresh(case)
    return _item(case)


@router.post("/reviews/cases", response_model=ReviewCaseItem, status_code=201)
def create_case(payload: CaseCreateRequest, principal: IntelligencePrincipal = Depends(require_review_actor), db: Session = Depends(get_db)):
    if bool(payload.alert_id) == bool(payload.signal_id):
        raise HTTPException(status_code=422, detail={"code": "REVIEW_SOURCE_REQUIRED", "message": "Provide exactly one alert_id or signal_id."})
    scope = resolve_active_scope(db)
    alert = db.scalar(select(AnalyticalAlert).where(AnalyticalAlert.alert_id == payload.alert_id, AnalyticalAlert.dataset_version == scope.release_version)) if payload.alert_id else None
    signal = db.scalar(select(MonitoringSignal).where(MonitoringSignal.signal_id == payload.signal_id, MonitoringSignal.dataset_version == scope.release_version)) if payload.signal_id else None
    if payload.alert_id and alert is None or payload.signal_id and signal is None:
        raise HTTPException(status_code=404, detail={"code": "REVIEW_SOURCE_NOT_FOUND", "message": "No reviewable monitoring record exists in the active release."})
    work_key = alert.work_key if alert else signal.work_key
    risk = db.scalar(select(RiskAssessment).where(RiskAssessment.dataset_version == scope.release_version, RiskAssessment.work_key == work_key))
    state, district, mp, house = (risk.state_name, risk.district_or_ida, risk.mp_source_name, risk.house) if risk else (signal.state_name if signal else None, signal.district_or_ida if signal else None, signal.mp_source_name if signal else None, alert.house if alert else signal.house)
    _assert_context_scope(principal, mp=mp, district=district, state=state)
    related_signals = db.scalars(select(MonitoringSignal).where(MonitoringSignal.dataset_version == scope.release_version, MonitoringSignal.work_key == work_key)).all()
    duplicates = db.scalars(select(DuplicateCandidate).where(DuplicateCandidate.dataset_version == scope.release_version, or_(DuplicateCandidate.work_a_key == work_key, DuplicateCandidate.work_b_key == work_key))).all()
    run_id = alert.run_id if alert else signal.run_id
    run = db.scalar(select(AnalyticsRun).where(AnalyticsRun.run_id == run_id))
    serialize = lambda item: {column.name: (getattr(item, column.name).isoformat() if isinstance(getattr(item, column.name), datetime) else getattr(item, column.name)) for column in item.__table__.columns if column.name not in {"fingerprint"}}
    evidence = {"source_alert": serialize(alert) if alert else None, "source_signal": serialize(signal) if signal else None, "risk_assessment": serialize(risk) if risk else None, "related_signals": [serialize(item) for item in related_signals], "duplicate_candidates": [serialize(item) for item in duplicates], "analytics_run": serialize(run) if run else None, "dataset_version": scope.release_version, "captured_at": _now().isoformat()}
    content_hash = sha256(json.dumps(evidence, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()
    created_at = _now()
    case_id, snapshot_id = f"rev_case_{uuid4().hex}", f"rev_evd_{uuid4().hex}"
    case = ReviewCase(case_id=case_id, source_alert_id=alert.alert_id if alert else None, source_signal_id=signal.signal_id if signal else None, canonical_work_key=work_key, house=house, state_name=state, district_or_ida=district, mp_source_name=mp, status="OPEN", priority=_priority(alert.severity if alert else signal.severity), assignee=None, dataset_version=scope.release_version, evidence_snapshot_id=snapshot_id, version=1, created_by=principal.actor or "", created_at=created_at, updated_at=created_at, closed_at=None)
    snapshot = ReviewCaseEvidenceSnapshot(snapshot_id=snapshot_id, case_id=case_id, dataset_version=scope.release_version, analytics_run_id=run_id, payload=evidence, content_hash=content_hash, created_at=created_at)
    db.add_all([case, snapshot, _event(case, principal.actor or "", "CREATED", metadata={"source_alert_id": case.source_alert_id, "source_signal_id": case.source_signal_id, "evidence_snapshot_id": snapshot_id})])
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return _item(case)


@router.get("/reviews/cases", response_model=ReviewPage)
def cases(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), status: str | None = None, priority: str | None = None, house: str | None = None, state: str | None = None, district_or_ida: str | None = None, mp: str | None = None, assignee: str | None = None, created_from: datetime | None = None, created_to: datetime | None = None, search: str | None = None, principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    statement = _scope(select(ReviewCase), principal)
    for column, value in [(ReviewCase.status, status), (ReviewCase.priority, priority), (ReviewCase.house, house), (ReviewCase.state_name, state), (ReviewCase.district_or_ida, district_or_ida), (ReviewCase.mp_source_name, mp), (ReviewCase.assignee, assignee)]:
        if value: statement = statement.where(column == value)
    if created_from: statement = statement.where(ReviewCase.created_at >= created_from)
    if created_to: statement = statement.where(ReviewCase.created_at <= created_to)
    if search: statement = statement.where(or_(ReviewCase.case_id.ilike(f"%{search}%"), ReviewCase.canonical_work_key.ilike(f"%{search}%"), ReviewCase.assignee.ilike(f"%{search}%")))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(statement.order_by(ReviewCase.updated_at.desc()).limit(page_size).offset((page - 1) * page_size)).all()
    version = rows[0].dataset_version if rows else resolve_active_scope(db).release_version
    return ReviewPage(items=[_item(row) for row in rows], pagination={"total": total, "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size if total else 0}, provenance=ProtectedProvenance(dataset_version=version, generated_at=_now()))


@router.get("/reviews/summary", response_model=ReviewSummary)
def review_summary(principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    statement = _scope(select(ReviewCase), principal)
    counts = {status: int(count) for status, count in db.execute(statement.with_only_columns(ReviewCase.status, func.count()).group_by(ReviewCase.status)).all()}
    escalations = _scope(select(ReviewEscalation).join(ReviewCase, ReviewEscalation.case_id == ReviewCase.case_id), principal)
    active = db.scalar(select(func.count()).select_from(escalations.where(ReviewEscalation.status == "OPEN").subquery())) or 0
    return ReviewSummary(by_status=counts, active_escalations=active, provenance=ProtectedProvenance(dataset_version=resolve_active_scope(db).release_version, generated_at=_now()))


@router.get("/reviews/cases/{case_id}", response_model=ReviewCaseDetail)
def case_detail(case_id: str, principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    case = _case_or_404(case_id, principal, db)
    snapshot = db.scalar(select(ReviewCaseEvidenceSnapshot).where(ReviewCaseEvidenceSnapshot.snapshot_id == case.evidence_snapshot_id))
    events = db.scalars(select(ReviewCaseEvent).where(ReviewCaseEvent.case_id == case.case_id).order_by(ReviewCaseEvent.occurred_at)).all()
    if snapshot is None:
        raise HTTPException(status_code=500, detail={"code": "REVIEW_EVIDENCE_MISSING", "message": "The review case evidence snapshot is unavailable."})
    return ReviewCaseDetail(**_item(case).model_dump(), evidence_snapshot_id=snapshot.snapshot_id, evidence_snapshot=snapshot.payload, evidence_hash=snapshot.content_hash, events=[ReviewEventResponse(event_id=item.event_id, actor=item.actor, occurred_at=item.occurred_at, action=item.action, metadata=item.metadata_json, comment=item.comment) for item in events], provenance=_provenance(case))


def _action(case_id: str, payload: CaseActionRequest, principal: IntelligencePrincipal, db: Session, *, action: str, from_statuses: set[str], to_status: str | None = None, assignee_required: bool = False, resolution: bool = False) -> ReviewCaseItem:
    case = _case_or_404(case_id, principal, db)
    _assert_version(case, payload.version)
    if case.status not in from_statuses:
        raise HTTPException(status_code=422, detail={"code": "REVIEW_INVALID_TRANSITION", "message": f"{action} is not allowed while this case is {case.status}."})
    if assignee_required and not payload.assignee:
        raise HTTPException(status_code=422, detail={"code": "REVIEW_ASSIGNEE_REQUIRED", "message": "An assignee is required."})
    if resolution and (payload.resolution_type not in RESOLUTION_TYPES or not payload.resolution_note):
        raise HTTPException(status_code=422, detail={"code": "REVIEW_RESOLUTION_REQUIRED", "message": "A supported resolution type and resolution note are required."})
    previous_assignee, previous_status = case.assignee, case.status
    if payload.assignee: case.assignee = payload.assignee
    if to_status: case.status = to_status
    if to_status == "CLOSED": case.closed_at = _now()
    if to_status == "REOPENED": case.closed_at = None
    metadata = {"from_status": previous_status, "to_status": to_status, "previous_assignee": previous_assignee, "assignee": case.assignee}
    if resolution: metadata.update({"resolution_type": payload.resolution_type, "resolution_note": payload.resolution_note})
    event = _event(case, principal.actor or "", action, metadata=metadata, comment=payload.comment or payload.reason or payload.resolution_note)
    return _commit_action(case, event, db, _notification(event, case, case.assignee, f"Review case {case.case_id}: {action.replace('_', ' ').lower()}"))


@router.post("/reviews/cases/{case_id}/assign", response_model=ReviewCaseItem)
def assign(case_id: str, payload: CaseActionRequest, principal: IntelligencePrincipal = Depends(require_review_actor), db: Session = Depends(get_db)):
    return _action(case_id, payload, principal, db, action="ASSIGNED", from_statuses={"OPEN"}, to_status="ASSIGNED", assignee_required=True)


@router.post("/reviews/cases/{case_id}/reassign", response_model=ReviewCaseItem)
def reassign(case_id: str, payload: CaseActionRequest, principal: IntelligencePrincipal = Depends(require_review_actor), db: Session = Depends(get_db)):
    return _action(case_id, payload, principal, db, action="REASSIGNED", from_statuses={"ASSIGNED", "UNDER_REVIEW", "FOLLOW_UP_REQUIRED", "REOPENED"}, assignee_required=True)


@router.post("/reviews/cases/{case_id}/start-review", response_model=ReviewCaseItem)
def start_review(case_id: str, payload: CaseActionRequest, principal: IntelligencePrincipal = Depends(require_review_actor), db: Session = Depends(get_db)):
    return _action(case_id, payload, principal, db, action="UNDER_REVIEW_STARTED", from_statuses={"ASSIGNED", "FOLLOW_UP_REQUIRED", "REOPENED"}, to_status="UNDER_REVIEW")


@router.post("/reviews/cases/{case_id}/comment", response_model=ReviewCaseItem)
def comment(case_id: str, payload: CaseActionRequest, principal: IntelligencePrincipal = Depends(require_review_actor), db: Session = Depends(get_db)):
    if not payload.comment or not payload.comment.strip():
        raise HTTPException(status_code=422, detail={"code": "REVIEW_COMMENT_REQUIRED", "message": "A comment is required."})
    return _action(case_id, payload, principal, db, action="COMMENTED", from_statuses=STATUSES)


@router.post("/reviews/cases/{case_id}/request-follow-up", response_model=ReviewCaseItem)
def request_follow_up(case_id: str, payload: CaseActionRequest, principal: IntelligencePrincipal = Depends(require_review_actor), db: Session = Depends(get_db)):
    if not payload.reason or not payload.reason.strip():
        raise HTTPException(status_code=422, detail={"code": "REVIEW_FOLLOW_UP_REASON_REQUIRED", "message": "A follow-up reason is required."})
    return _action(case_id, payload, principal, db, action="FOLLOW_UP_REQUESTED", from_statuses={"UNDER_REVIEW"}, to_status="FOLLOW_UP_REQUIRED")


@router.post("/reviews/cases/{case_id}/resolve", response_model=ReviewCaseItem)
def resolve(case_id: str, payload: CaseActionRequest, principal: IntelligencePrincipal = Depends(require_review_actor), db: Session = Depends(get_db)):
    return _action(case_id, payload, principal, db, action="RESOLVED", from_statuses={"UNDER_REVIEW"}, to_status="RESOLVED", resolution=True)


@router.post("/reviews/cases/{case_id}/close", response_model=ReviewCaseItem)
def close(case_id: str, payload: CaseActionRequest, principal: IntelligencePrincipal = Depends(require_review_actor), db: Session = Depends(get_db)):
    return _action(case_id, payload, principal, db, action="CLOSED", from_statuses={"RESOLVED"}, to_status="CLOSED")


@router.post("/reviews/cases/{case_id}/reopen", response_model=ReviewCaseItem)
def reopen(case_id: str, payload: CaseActionRequest, principal: IntelligencePrincipal = Depends(require_review_actor), db: Session = Depends(get_db)):
    return _action(case_id, payload, principal, db, action="REOPENED", from_statuses={"CLOSED"}, to_status="REOPENED")


@router.get("/notifications", response_model=list[NotificationResponse])
def notifications(limit: int = Query(20, ge=1, le=100), principal: IntelligencePrincipal = Depends(require_review_actor), db: Session = Depends(get_db)):
    rows = db.scalars(select(ReviewNotification).where(ReviewNotification.recipient == principal.actor).order_by(ReviewNotification.created_at.desc()).limit(limit)).all()
    return [NotificationResponse(notification_id=row.notification_id, case_id=row.case_id, event_id=row.event_id, recipient=row.recipient, state=row.state, message=row.message, created_at=row.created_at) for row in rows]


def _notification_action(notification_id: str, state: str, principal: IntelligencePrincipal, db: Session) -> NotificationResponse:
    row = db.scalar(select(ReviewNotification).where(ReviewNotification.notification_id == notification_id, ReviewNotification.recipient == principal.actor))
    if row is None: raise HTTPException(status_code=404, detail={"code": "NOTIFICATION_NOT_FOUND", "message": "No notification exists for the authorized actor."})
    now = _now(); row.state = state
    if state == "READ": row.read_at = now
    else: row.acknowledged_at = now
    db.commit()
    return NotificationResponse(notification_id=row.notification_id, case_id=row.case_id, event_id=row.event_id, recipient=row.recipient, state=row.state, message=row.message, created_at=row.created_at)


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_read(notification_id: str, principal: IntelligencePrincipal = Depends(require_review_actor), db: Session = Depends(get_db)):
    return _notification_action(notification_id, "READ", principal, db)


@router.post("/notifications/{notification_id}/acknowledge", response_model=NotificationResponse)
def acknowledge(notification_id: str, principal: IntelligencePrincipal = Depends(require_review_actor), db: Session = Depends(get_db)):
    return _notification_action(notification_id, "ACKNOWLEDGED", principal, db)

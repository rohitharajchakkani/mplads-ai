"""Protected administration APIs for real platform state and governed changes."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import tomllib
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.ai.gemini_provider import provider_status
from app.analytics.data_quality_service import data_quality_metrics
from app.api.deps import (
    IntelligencePrincipal,
    get_db,
    require_admin_actor,
    require_platform_administrator,
)
from app.core.config import get_settings
from app.models import (
    AiRequestAudit,
    AnalyticsRun,
    CompletedWorkRecord,
    DatasetLifecycleEvent,
    DatasetRelease,
    DatasetVersion,
    RecommendationEvent,
    ReviewCaseEvent,
    ValidationFinding,
)
from app.models.admin import AccessRequest, AdminAuditEvent, AuthorizedUser
from app.schemas.admin import (
    AccessRequestDecision,
    AccessRequestItem,
    AccessRequestRejection,
    AdminDataQuality,
    AdminPage,
    AdminSystemStatus,
    AuthorizedUserItem,
    DatasetActionConfirmation,
    DatasetAsset,
    DatasetReleaseItem,
    SafeConfigurationStatus,
    ScopeAssignment,
    UserAccessUpdate,
    UserStatusAction,
)
from app.services.versioning_service import (
    LifecycleError,
    approve_batch,
    promote_release,
    resolve_active_scope,
    rollback_active_release,
)


router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(require_platform_administrator)],
    tags=["administration"],
)

ADMIN_ROLES = {
    "MP",
    "DISTRICT_AUTHORITY",
    "STATE_NODAL_AUTHORITY",
    "MINISTRY",
    "PLATFORM_ADMINISTRATOR",
}


def _now() -> datetime:
    return datetime.now(UTC)


def _page(total: int, page: int, page_size: int) -> dict[str, int]:
    return {
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    }


def _actor(principal: IntelligencePrincipal) -> str:
    if not principal.actor or not principal.actor.strip():
        raise HTTPException(
            status_code=403,
            detail={"code": "ADMIN_ACTOR_REQUIRED", "message": "An administrator actor identity is required."},
        )
    return principal.actor.strip()


def _scope_values(
    role: str,
    state_scope: str | None,
    district_scope: str | None,
    mp_scope: str | None,
) -> tuple[str | None, str | None, str | None]:
    """Validate the same explicit scope model used by protected monitoring APIs."""
    if role not in ADMIN_ROLES:
        raise HTTPException(status_code=422, detail={"code": "ADMIN_ROLE_INVALID", "message": "Unsupported role."})
    state = state_scope.strip() if state_scope and state_scope.strip() else None
    district = district_scope.strip() if district_scope and district_scope.strip() else None
    mp = mp_scope.strip() if mp_scope and mp_scope.strip() else None
    values = {"state_scope": state, "district_scope": district, "mp_scope": mp}
    required = {
        "MP": "mp_scope",
        "DISTRICT_AUTHORITY": "district_scope",
        "STATE_NODAL_AUTHORITY": "state_scope",
    }.get(role)
    if required is None:
        if any(values.values()):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "ADMIN_SCOPE_INVALID",
                    "message": "National and system roles must not receive a narrower monitoring scope.",
                },
            )
        return None, None, None
    if not values[required] or any(value for key, value in values.items() if key != required):
        label = required.replace("_scope", "").replace("_", " ")
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ADMIN_SCOPE_INVALID",
                "message": f"{role.replace('_', ' ')} requires exactly one {label} scope.",
            },
        )
    return state, district, mp


def _admin_event(
    db: Session,
    *,
    actor: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    metadata: dict[str, str | int | None],
) -> None:
    db.add(
        AdminAuditEvent(
            event_id=f"adm_evt_{uuid4().hex}",
            actor=actor,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            occurred_at=_now(),
            metadata_json=metadata,
        )
    )


def _access_request(row: AccessRequest) -> AccessRequestItem:
    return AccessRequestItem(
        request_id=row.request_id,
        name=row.name,
        designation=row.designation,
        office=row.office,
        state_name=row.state_name,
        district_or_ida=row.district_or_ida,
        reason=row.reason,
        status=row.status,
        created_at=row.created_at,
        decided_at=row.decided_at,
        decided_by=row.decided_by,
        decision_note=row.decision_note,
        approved_user_id=row.approved_user_id,
    )


def _user(row: AuthorizedUser) -> AuthorizedUserItem:
    return AuthorizedUserItem(
        user_id=row.user_id,
        display_name=row.display_name,
        designation=row.designation,
        office=row.office,
        role=row.role,
        state_scope=row.state_scope,
        district_scope=row.district_scope,
        mp_scope=row.mp_scope,
        status=row.status,
        source_access_request_id=row.source_access_request_id,
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        changed_by=row.changed_by,
        disabled_at=row.disabled_at,
    )


@router.get("/access-requests", response_model=AdminPage)
def access_requests(
    status: str | None = Query(None, pattern="^(PENDING|APPROVED|REJECTED)$"),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    state: str | None = Query(None, max_length=150),
    district: str | None = Query(None, max_length=500),
    search: str | None = Query(None, max_length=160),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AdminPage:
    statement = select(AccessRequest)
    for column, value in ((AccessRequest.status, status), (AccessRequest.state_name, state), (AccessRequest.district_or_ida, district)):
        if value:
            statement = statement.where(column == value)
    if created_from:
        statement = statement.where(AccessRequest.created_at >= created_from)
    if created_to:
        statement = statement.where(AccessRequest.created_at <= created_to)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(or_(AccessRequest.name.ilike(pattern), AccessRequest.office.ilike(pattern), AccessRequest.designation.ilike(pattern)))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(statement.order_by(AccessRequest.created_at.desc()).limit(page_size).offset((page - 1) * page_size)).all()
    return AdminPage(items=[_access_request(row).model_dump() for row in rows], pagination=_page(total, page, page_size))


@router.post("/access-requests/{request_id}/approve", response_model=AuthorizedUserItem)
def approve_access_request(
    request_id: str,
    payload: AccessRequestDecision,
    principal: IntelligencePrincipal = Depends(require_admin_actor),
    db: Session = Depends(get_db),
) -> AuthorizedUserItem:
    actor = _actor(principal)
    request = db.get(AccessRequest, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail={"code": "ACCESS_REQUEST_NOT_FOUND", "message": "Access request not found."})
    if request.status != "PENDING":
        raise HTTPException(status_code=409, detail={"code": "ACCESS_REQUEST_FINALIZED", "message": "Only pending access requests can be approved."})
    state, district, mp = _scope_values(payload.role, payload.state_scope, payload.district_scope, payload.mp_scope)
    now = _now()
    user = AuthorizedUser(
        user_id=f"usr_{uuid4().hex}",
        display_name=request.name,
        designation=request.designation,
        office=request.office,
        role=payload.role,
        state_scope=state,
        district_scope=district,
        mp_scope=mp,
        status="ACTIVE",
        source_access_request_id=request.request_id,
        version=1,
        created_at=now,
        updated_at=now,
        changed_by=actor,
        disabled_at=None,
    )
    request.status, request.decided_at, request.decided_by = "APPROVED", now, actor
    request.decision_note, request.approved_user_id = payload.decision_note, user.user_id
    db.add(user)
    _admin_event(
        db,
        actor=actor,
        event_type="ACCESS_REQUEST_APPROVED",
        entity_type="ACCESS_REQUEST",
        entity_id=request.request_id,
        metadata={"assigned_role": payload.role, "state_scope": state, "district_scope": district, "mp_scope": mp},
    )
    db.commit()
    return _user(user)


@router.post("/access-requests/{request_id}/reject", response_model=AccessRequestItem)
def reject_access_request(
    request_id: str,
    payload: AccessRequestRejection,
    principal: IntelligencePrincipal = Depends(require_admin_actor),
    db: Session = Depends(get_db),
) -> AccessRequestItem:
    actor = _actor(principal)
    request = db.get(AccessRequest, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail={"code": "ACCESS_REQUEST_NOT_FOUND", "message": "Access request not found."})
    if request.status != "PENDING":
        raise HTTPException(status_code=409, detail={"code": "ACCESS_REQUEST_FINALIZED", "message": "Only pending access requests can be rejected."})
    request.status, request.decided_at, request.decided_by = "REJECTED", _now(), actor
    request.decision_note = payload.decision_note
    _admin_event(
        db,
        actor=actor,
        event_type="ACCESS_REQUEST_REJECTED",
        entity_type="ACCESS_REQUEST",
        entity_id=request.request_id,
        metadata={"decision_recorded": "REJECTED"},
    )
    db.commit()
    return _access_request(request)


@router.get("/users", response_model=AdminPage)
def users(
    status: str | None = Query(None, pattern="^(ACTIVE|DISABLED|REVOKED)$"),
    role: str | None = Query(None, pattern="^(MP|DISTRICT_AUTHORITY|STATE_NODAL_AUTHORITY|MINISTRY|PLATFORM_ADMINISTRATOR)$"),
    state: str | None = Query(None, max_length=150),
    district: str | None = Query(None, max_length=500),
    search: str | None = Query(None, max_length=160),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AdminPage:
    statement = select(AuthorizedUser)
    for column, value in ((AuthorizedUser.status, status), (AuthorizedUser.role, role), (AuthorizedUser.state_scope, state), (AuthorizedUser.district_scope, district)):
        if value:
            statement = statement.where(column == value)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(or_(AuthorizedUser.display_name.ilike(pattern), AuthorizedUser.office.ilike(pattern), AuthorizedUser.designation.ilike(pattern)))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(statement.order_by(AuthorizedUser.updated_at.desc()).limit(page_size).offset((page - 1) * page_size)).all()
    return AdminPage(items=[_user(row).model_dump() for row in rows], pagination=_page(total, page, page_size))


def _user_or_404(user_id: str, db: Session) -> AuthorizedUser:
    user = db.get(AuthorizedUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail={"code": "ADMIN_USER_NOT_FOUND", "message": "Authorized user not found."})
    return user


@router.patch("/users/{user_id}", response_model=AuthorizedUserItem)
def update_user_access(
    user_id: str,
    payload: UserAccessUpdate,
    principal: IntelligencePrincipal = Depends(require_admin_actor),
    db: Session = Depends(get_db),
) -> AuthorizedUserItem:
    actor, user = _actor(principal), _user_or_404(user_id, db)
    if user.version != payload.expected_version:
        raise HTTPException(status_code=409, detail={"code": "ADMIN_USER_VERSION_CONFLICT", "message": "User access changed. Refresh before updating."})
    role = payload.role or user.role
    fields = payload.model_fields_set
    state = payload.state_scope if "state_scope" in fields else user.state_scope
    district = payload.district_scope if "district_scope" in fields else user.district_scope
    mp = payload.mp_scope if "mp_scope" in fields else user.mp_scope
    state, district, mp = _scope_values(role, state, district, mp)
    previous = {"role": user.role, "state_scope": user.state_scope, "district_scope": user.district_scope, "mp_scope": user.mp_scope}
    user.role, user.state_scope, user.district_scope, user.mp_scope = role, state, district, mp
    user.version += 1
    user.updated_at, user.changed_by = _now(), actor
    _admin_event(
        db,
        actor=actor,
        event_type="USER_ACCESS_UPDATED",
        entity_type="AUTHORIZED_USER",
        entity_id=user.user_id,
        metadata={"previous_role": previous["role"], "assigned_role": role, "state_scope": state, "district_scope": district, "mp_scope": mp},
    )
    db.commit()
    return _user(user)


def _set_user_status(
    user_id: str,
    payload: UserStatusAction,
    principal: IntelligencePrincipal,
    db: Session,
    *,
    target_status: str,
) -> AuthorizedUserItem:
    actor, user = _actor(principal), _user_or_404(user_id, db)
    if user.version != payload.expected_version:
        raise HTTPException(status_code=409, detail={"code": "ADMIN_USER_VERSION_CONFLICT", "message": "User access changed. Refresh before updating."})
    if user.status != "ACTIVE":
        raise HTTPException(status_code=409, detail={"code": "ADMIN_USER_NOT_ACTIVE", "message": "Only active users can be disabled or revoked."})
    user.status, user.disabled_at = target_status, _now()
    user.version += 1
    user.updated_at, user.changed_by = user.disabled_at, actor
    _admin_event(
        db,
        actor=actor,
        event_type=f"USER_{target_status}",
        entity_type="AUTHORIZED_USER",
        entity_id=user.user_id,
        metadata={"reason_recorded": "YES", "previous_status": "ACTIVE", "new_status": target_status},
    )
    db.commit()
    return _user(user)


@router.post("/users/{user_id}/disable", response_model=AuthorizedUserItem)
def disable_user(
    user_id: str,
    payload: UserStatusAction,
    principal: IntelligencePrincipal = Depends(require_admin_actor),
    db: Session = Depends(get_db),
) -> AuthorizedUserItem:
    if payload.confirmation != "DISABLE":
        raise HTTPException(status_code=422, detail={"code": "ADMIN_CONFIRMATION_REQUIRED", "message": "DISABLE confirmation is required."})
    return _set_user_status(user_id, payload, principal, db, target_status="DISABLED")


@router.post("/users/{user_id}/revoke", response_model=AuthorizedUserItem)
def revoke_user(
    user_id: str,
    payload: UserStatusAction,
    principal: IntelligencePrincipal = Depends(require_admin_actor),
    db: Session = Depends(get_db),
) -> AuthorizedUserItem:
    if payload.confirmation != "REVOKE":
        raise HTTPException(status_code=422, detail={"code": "ADMIN_CONFIRMATION_REQUIRED", "message": "REVOKE confirmation is required."})
    return _set_user_status(user_id, payload, principal, db, target_status="REVOKED")


def _asset(row: DatasetVersion) -> DatasetAsset:
    return DatasetAsset(
        dataset_type=row.dataset_type,
        house=row.house,
        status=row.status,
        source_filename=row.source_filename,
        source_sheet=row.source_sheet,
        source_checksum=row.source_checksum,
        source_row_count=row.source_row_count,
        staged_row_count=row.staged_row_count,
        valid_row_count=row.valid_row_count,
        warning_row_count=row.warning_row_count,
        rejected_row_count=row.rejected_row_count,
    )


def _release(row: DatasetRelease, db: Session) -> DatasetReleaseItem:
    versions = db.scalars(select(DatasetVersion).where(DatasetVersion.batch_id == row.batch_id).order_by(DatasetVersion.house, DatasetVersion.dataset_type)).all()
    events = db.scalars(select(DatasetLifecycleEvent).where(DatasetLifecycleEvent.release_id == row.id).order_by(DatasetLifecycleEvent.occurred_at)).all()
    return DatasetReleaseItem(
        release_id=row.id,
        batch_id=row.batch_id,
        release_version=row.release_version,
        status=row.status,
        approved_by=row.approved_by,
        approved_at=row.approved_at,
        validation_version=row.validation_version,
        approval_notes=row.approval_notes,
        promoted_at=row.promoted_at,
        rolled_back_at=row.rolled_back_at,
        datasets=[_asset(version) for version in versions],
        lifecycle_events=[{"event_type": event.event_type, "actor": event.actor, "occurred_at": event.occurred_at, "has_notes": bool(event.notes)} for event in events],
    )


@router.get("/datasets/versions", response_model=AdminPage)
def dataset_versions(
    status: str | None = Query(None, max_length=24),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AdminPage:
    statement = select(DatasetRelease)
    if status:
        statement = statement.where(DatasetRelease.status == status)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(statement.order_by(DatasetRelease.approved_at.desc()).limit(page_size).offset((page - 1) * page_size)).all()
    return AdminPage(items=[_release(row, db).model_dump() for row in rows], pagination=_page(total, page, page_size))


@router.get("/datasets/active", response_model=DatasetReleaseItem)
def active_dataset(db: Session = Depends(get_db)) -> DatasetReleaseItem:
    try:
        scope = resolve_active_scope(db)
    except LifecycleError as exc:
        raise HTTPException(status_code=503, detail={"code": "NO_ACTIVE_DATASET", "message": str(exc)}) from exc
    release = db.get(DatasetRelease, scope.release_id)
    if release is None:
        raise HTTPException(status_code=503, detail={"code": "ACTIVE_RELEASE_MISSING", "message": "The active dataset release is unavailable."})
    return _release(release, db)


@router.post("/datasets/batches/{batch_id}/approve", response_model=DatasetReleaseItem)
def approve_dataset_batch(
    batch_id: str,
    payload: DatasetActionConfirmation,
    principal: IntelligencePrincipal = Depends(require_admin_actor),
    db: Session = Depends(get_db),
) -> DatasetReleaseItem:
    if payload.confirmation != "APPROVE":
        raise HTTPException(status_code=422, detail={"code": "ADMIN_CONFIRMATION_REQUIRED", "message": "APPROVE confirmation is required."})
    actor = _actor(principal)
    existing = db.scalar(select(DatasetRelease).where(DatasetRelease.batch_id == batch_id))
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={"code": "DATASET_RELEASE_EXISTS", "message": "This dataset batch already has a release decision."},
        )
    try:
        release = approve_batch(db, batch_id, approved_by=actor, notes=payload.notes)
    except LifecycleError as exc:
        raise HTTPException(status_code=422, detail={"code": "DATASET_APPROVAL_REJECTED", "message": str(exc)}) from exc
    _admin_event(db, actor=actor, event_type="DATASET_APPROVED", entity_type="DATASET_RELEASE", entity_id=release.id, metadata={"batch_id": batch_id, "release_version": release.release_version})
    db.commit()
    return _release(release, db)


@router.post("/datasets/releases/{release_id}/promote", response_model=DatasetReleaseItem)
def promote_dataset_release(
    release_id: str,
    payload: DatasetActionConfirmation,
    principal: IntelligencePrincipal = Depends(require_admin_actor),
    db: Session = Depends(get_db),
) -> DatasetReleaseItem:
    if payload.confirmation != "PROMOTE":
        raise HTTPException(status_code=422, detail={"code": "ADMIN_CONFIRMATION_REQUIRED", "message": "PROMOTE confirmation is required."})
    actor = _actor(principal)
    existing = db.get(DatasetRelease, release_id)
    if existing is None:
        raise HTTPException(status_code=404, detail={"code": "DATASET_RELEASE_NOT_FOUND", "message": "Dataset release not found."})
    if existing.status == "ACTIVE":
        raise HTTPException(status_code=409, detail={"code": "DATASET_ALREADY_ACTIVE", "message": "The dataset release is already active."})
    try:
        release = promote_release(db, release_id, actor=actor, notes=payload.notes)
    except LifecycleError as exc:
        raise HTTPException(status_code=422, detail={"code": "DATASET_PROMOTION_REJECTED", "message": str(exc)}) from exc
    _admin_event(db, actor=actor, event_type="DATASET_PROMOTED", entity_type="DATASET_RELEASE", entity_id=release.id, metadata={"release_version": release.release_version})
    db.commit()
    return _release(release, db)


@router.post("/datasets/rollback", response_model=DatasetReleaseItem)
def rollback_dataset_release(
    payload: DatasetActionConfirmation,
    principal: IntelligencePrincipal = Depends(require_admin_actor),
    db: Session = Depends(get_db),
) -> DatasetReleaseItem:
    if payload.confirmation != "ROLLBACK":
        raise HTTPException(status_code=422, detail={"code": "ADMIN_CONFIRMATION_REQUIRED", "message": "ROLLBACK confirmation is required."})
    actor = _actor(principal)
    try:
        release = rollback_active_release(db, actor=actor, notes=payload.notes)
    except LifecycleError as exc:
        raise HTTPException(status_code=422, detail={"code": "DATASET_ROLLBACK_REJECTED", "message": str(exc)}) from exc
    _admin_event(db, actor=actor, event_type="DATASET_ROLLED_BACK", entity_type="DATASET_RELEASE", entity_id=release.id, metadata={"restored_release_version": release.release_version})
    db.commit()
    return _release(release, db)


@router.get("/data-quality", response_model=AdminDataQuality)
def admin_data_quality(db: Session = Depends(get_db)) -> AdminDataQuality:
    try:
        scope = resolve_active_scope(db)
    except LifecycleError as exc:
        raise HTTPException(status_code=503, detail={"code": "NO_ACTIVE_DATASET", "message": str(exc)}) from exc
    metrics = dict(data_quality_metrics(db).data)
    completed_missing_date = db.scalar(
        select(func.count()).select_from(CompletedWorkRecord).where(
            CompletedWorkRecord.source_dataset_version_id.in_(scope.dataset_version_ids),
            CompletedWorkRecord.completion_date.is_(None),
        )
    ) or 0
    metrics["completed_records_missing_completion_date"] = int(completed_missing_date)
    return AdminDataQuality(dataset_version=scope.release_version, generated_at=_now(), metrics=metrics)


@router.get("/data-quality/findings", response_model=AdminPage)
def quality_findings(
    severity: str | None = Query(None, pattern="^(WARNING|ERROR)$"),
    code: str | None = Query(None, max_length=80),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AdminPage:
    try:
        scope = resolve_active_scope(db)
    except LifecycleError as exc:
        raise HTTPException(status_code=503, detail={"code": "NO_ACTIVE_DATASET", "message": str(exc)}) from exc
    statement = select(ValidationFinding).where(ValidationFinding.batch_id == scope.batch_id)
    if severity:
        statement = statement.where(ValidationFinding.severity == severity)
    if code:
        statement = statement.where(ValidationFinding.code == code)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(statement.order_by(ValidationFinding.severity.desc(), ValidationFinding.id).limit(page_size).offset((page - 1) * page_size)).all()
    return AdminPage(
        items=[
            {
                "finding_id": row.id,
                "dataset_version_id": row.dataset_version_id,
                "source_row_number": row.source_row_number,
                "severity": row.severity,
                "code": row.code,
                "field_name": row.field_name,
                "message": row.message,
            }
            for row in rows
        ],
        pagination=_page(total, page, page_size),
    )


def _audit_records(db: Session) -> list[dict]:
    records: list[dict] = []
    records.extend(
        {
            "audit_id": row.event_id,
            "source": "ADMIN",
            "event_type": row.event_type,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "actor": row.actor,
            "occurred_at": row.occurred_at,
            "metadata": row.metadata_json,
        }
        for row in db.scalars(select(AdminAuditEvent)).all()
    )
    records.extend(
        {
            "audit_id": f"dataset_{row.id}",
            "source": "DATASET",
            "event_type": row.event_type,
            "entity_type": "DATASET_RELEASE",
            "entity_id": row.release_id,
            "actor": row.actor,
            "occurred_at": row.occurred_at,
            "metadata": {"notes_recorded": bool(row.notes)},
        }
        for row in db.scalars(select(DatasetLifecycleEvent)).all()
    )
    records.extend(
        {
            "audit_id": row.event_id,
            "source": "REVIEW",
            "event_type": row.action,
            "entity_type": "REVIEW_CASE",
            "entity_id": row.case_id,
            "actor": row.actor,
            "occurred_at": row.occurred_at,
            "metadata": {"metadata_keys": sorted(row.metadata_json)},
        }
        for row in db.scalars(select(ReviewCaseEvent)).all()
    )
    records.extend(
        {
            "audit_id": row.event_id,
            "source": "RECOMMENDATION",
            "event_type": row.action,
            "entity_type": "RECOMMENDATION",
            "entity_id": row.recommendation_id,
            "actor": row.actor,
            "occurred_at": row.occurred_at,
            "metadata": {"metadata_keys": sorted(row.metadata_json)},
        }
        for row in db.scalars(select(RecommendationEvent)).all()
    )
    records.extend(
        {
            "audit_id": row.request_id,
            "source": "ASK_AI",
            "event_type": row.response_status,
            "entity_type": "AI_REQUEST",
            "entity_id": row.request_id,
            "actor": row.actor or "Not recorded",
            "occurred_at": row.created_at,
            "metadata": {"intent": row.intent, "tool_name": row.tool_name, "dataset_version": row.dataset_version},
        }
        for row in db.scalars(select(AiRequestAudit)).all()
    )
    return records


@router.get("/audit-logs", response_model=AdminPage)
def audit_logs(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    actor: str | None = Query(None, max_length=160),
    event_type: str | None = Query(None, max_length=48),
    entity: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AdminPage:
    rows = _audit_records(db)
    if date_from:
        rows = [row for row in rows if row["occurred_at"] >= date_from]
    if date_to:
        rows = [row for row in rows if row["occurred_at"] <= date_to]
    if actor:
        rows = [row for row in rows if row["actor"] == actor]
    if event_type:
        rows = [row for row in rows if row["event_type"] == event_type]
    if entity:
        rows = [row for row in rows if row["entity_id"] == entity or row["entity_type"] == entity]
    rows.sort(key=lambda row: row["occurred_at"], reverse=True)
    start, end = (page - 1) * page_size, page * page_size
    return AdminPage(items=rows[start:end], pagination=_page(len(rows), page, page_size))


def _application_version() -> str:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        return str(tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"])
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "Not available"


@router.get("/system", response_model=AdminSystemStatus)
def system_health(db: Session = Depends(get_db)) -> AdminSystemStatus:
    settings = get_settings()
    db.execute(text("SELECT 1"))
    try:
        scope = resolve_active_scope(db)
        active_status, release_version = "AVAILABLE", scope.release_version
    except LifecycleError:
        active_status, release_version = "UNAVAILABLE", None
    migration = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    latest = db.scalar(select(AnalyticsRun).order_by(AnalyticsRun.started_at.desc()).limit(1))
    gemini = provider_status(settings)
    return AdminSystemStatus(
        api_status="OK",
        database_status="OK",
        active_dataset_status=active_status,
        active_release_version=release_version,
        migration_version=migration,
        application_version=_application_version(),
        app_environment=settings.app_env,
        cors_status="CONFIGURED" if settings.cors_origins.strip() else "NOT_CONFIGURED",
        gemini_status="CONFIGURED" if gemini.configured else "NOT_CONFIGURED",
        gemini_model=gemini.model,
        latest_analytics_run=(
            {
                "run_id": latest.run_id,
                "status": latest.status,
                "dataset_version": latest.dataset_version,
                "started_at": latest.started_at,
                "completed_at": latest.completed_at,
            }
            if latest
            else None
        ),
        checked_at=_now(),
    )


@router.get("/configuration", response_model=SafeConfigurationStatus)
def configuration_status(db: Session = Depends(get_db)) -> SafeConfigurationStatus:
    system = system_health(db)
    return SafeConfigurationStatus(
        database="CONFIGURED" if system.database_status == "OK" else "UNAVAILABLE",
        gemini=system.gemini_status,
        cors=system.cors_status,
        active_dataset=system.active_dataset_status,
        environment=system.app_environment,
        migration="CURRENT" if system.migration_version else "UNAVAILABLE",
        checked_at=system.checked_at,
    )

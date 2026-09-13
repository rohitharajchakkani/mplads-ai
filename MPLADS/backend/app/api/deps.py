from collections.abc import Generator

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import create_session_factory
from app.services.versioning_service import LifecycleError, resolve_active_scope


def get_db() -> Generator[Session, None, None]:
    factory = create_session_factory(get_settings().database_url)
    session = factory()
    try:
        yield session
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(status_code=503, detail={"code": "DATABASE_UNAVAILABLE", "message": "Database is unavailable."}) from exc
    finally:
        session.close()


def require_active_dataset(db: Session = Depends(get_db)):
    try:
        return resolve_active_scope(db)
    except LifecycleError as exc:
        raise HTTPException(status_code=503, detail={"code": "NO_ACTIVE_DATASET", "message": str(exc)}) from exc


def database_ready(db: Session) -> bool:
    db.execute(text("SELECT 1"))
    return True


@dataclass(frozen=True)
class IntelligencePrincipal:
    """Server-side authorization boundary prepared for future identity integration."""
    role: str
    state_scope: str | None = None
    district_scope: str | None = None
    mp_scope: str | None = None
    actor: str | None = None


def require_intelligence_principal(
    role: str | None = Header(None, alias="X-MPLADS-Role"),
    state_scope: str | None = Header(None, alias="X-MPLADS-State-Scope"),
    district_scope: str | None = Header(None, alias="X-MPLADS-District-Scope"),
    mp_scope: str | None = Header(None, alias="X-MPLADS-MP-Scope"),
    actor: str | None = Header(None, alias="X-MPLADS-Actor"),
) -> IntelligencePrincipal:
    if role not in {"MP", "DISTRICT_AUTHORITY", "STATE_NODAL_AUTHORITY", "MINISTRY", "PLATFORM_ADMINISTRATOR"}:
        raise HTTPException(status_code=401, detail={"code": "INTELLIGENCE_AUTH_REQUIRED", "message": "A valid protected intelligence role is required."})
    if role == "MP" and not mp_scope:
        raise HTTPException(status_code=403, detail={"code": "INTELLIGENCE_SCOPE_REQUIRED", "message": "MP scope is required for this role."})
    if role == "DISTRICT_AUTHORITY" and not district_scope:
        raise HTTPException(status_code=403, detail={"code": "INTELLIGENCE_SCOPE_REQUIRED", "message": "District scope is required for this role."})
    if role == "STATE_NODAL_AUTHORITY" and not state_scope:
        raise HTTPException(status_code=403, detail={"code": "INTELLIGENCE_SCOPE_REQUIRED", "message": "State scope is required for this role."})
    return IntelligencePrincipal(role, state_scope, district_scope, mp_scope, actor)


def require_review_actor(principal: IntelligencePrincipal = Depends(require_intelligence_principal)) -> IntelligencePrincipal:
    if not principal.actor or not principal.actor.strip():
        raise HTTPException(status_code=403, detail={"code": "REVIEW_ACTOR_REQUIRED", "message": "An authorized review actor is required for this action."})
    return principal


def require_platform_administrator(
    principal: IntelligencePrincipal = Depends(require_intelligence_principal),
) -> IntelligencePrincipal:
    """Server-side boundary for system-wide platform administration."""
    if principal.role != "PLATFORM_ADMINISTRATOR":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ADMIN_ACCESS_REQUIRED",
                "message": "Platform Administrator access is required for administration.",
            },
        )
    return principal


def require_admin_actor(
    principal: IntelligencePrincipal = Depends(require_platform_administrator),
) -> IntelligencePrincipal:
    if not principal.actor or not principal.actor.strip():
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ADMIN_ACTOR_REQUIRED",
                "message": "An administrator actor identity is required for consequential actions.",
            },
        )
    return principal

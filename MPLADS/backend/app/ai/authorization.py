"""Shared server-side authorization filters for read-only Ask AI tools."""
from __future__ import annotations

from sqlalchemy import select

from app.api.deps import IntelligencePrincipal
from app.models import RiskAssessment


def authorized_scope(principal: IntelligencePrincipal) -> dict[str, str | None]:
    """Return the scope supplied by the authenticated intelligence principal."""
    return {
        "role": principal.role,
        "state": principal.state_scope,
        "district_or_ida": principal.district_scope,
        "mp": principal.mp_scope,
    }


def apply_scope(statement, principal: IntelligencePrincipal, model):
    """Apply an authority filter; unscoped models are restricted by allowed works."""
    if principal.role in {"MINISTRY", "PLATFORM_ADMINISTRATOR"}:
        return statement
    if not hasattr(model, "mp_source_name"):
        allowed_work_keys = apply_scope(select(RiskAssessment.work_key), principal, RiskAssessment)
        return statement.where(model.work_key.in_(allowed_work_keys))
    if principal.role == "MP":
        return statement.where(model.mp_source_name == principal.mp_scope)
    if principal.role == "DISTRICT_AUTHORITY":
        return statement.where(model.district_or_ida == principal.district_scope)
    return statement.where(model.state_name == principal.state_scope)

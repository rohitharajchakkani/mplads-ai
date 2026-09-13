"""Protected monitoring endpoints. They are intentionally separate from public APIs."""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.analytics.financial_analytics_service import expenditure_by, expenditure_summary
from app.analytics.lifecycle_analytics_service import lifecycle_summary
from app.analytics.types import AnalyticsFilters
from app.api.deps import IntelligencePrincipal, get_db, require_intelligence_principal
from app.intelligence.engine import MODEL_VERSION
from app.models import AnalyticalAlert, DuplicateCandidate, MonitoringSignal, RiskAssessment
from app.schemas.intelligence import AlertResponse, AlertSummaryResponse, AnomalySummaryResponse, DuplicateCandidateResponse, MonitoringCategoryResponse, ProtectedPage, ProtectedProvenance, RiskSummaryResponse, RiskWorkResponse
from app.services.versioning_service import resolve_active_scope

router = APIRouter(dependencies=[Depends(require_intelligence_principal)])


def _scope(statement, principal: IntelligencePrincipal, model):
    if principal.role in {"MINISTRY", "PLATFORM_ADMINISTRATOR"}:
        return statement
    if not hasattr(model, "mp_source_name"):
        allowed = _scope(select(RiskAssessment.work_key), principal, RiskAssessment)
        return statement.where(model.work_key.in_(allowed))
    if principal.role == "MP":
        return statement.where(model.mp_source_name == principal.mp_scope)
    if principal.role == "DISTRICT_AUTHORITY":
        return statement.where(model.district_or_ida == principal.district_scope)
    return statement.where(model.state_name == principal.state_scope)


def _provenance(scope, rules_version: str | None = None, model_version: str | None = None) -> ProtectedProvenance:
    return ProtectedProvenance(dataset_version=scope.release_version, generated_at=datetime.now(UTC), rules_version=rules_version, model_version=model_version)


def _pagination(page: int, page_size: int, total: int) -> dict[str, int]:
    return {"total": total, "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size if total else 0}


def _grouped_count(statement, column, db: Session) -> dict[str, int]:
    rows = db.execute(statement.with_only_columns(column, func.count()).group_by(column)).all()
    return {str(value or "Not available"): int(count) for value, count in rows}


def _risk_filters(statement, *, house: str | None, state: str | None, district_or_ida: str | None, mp: str | None, risk_band: str | None, signal_category: str | None, search: str | None):
    if house: statement = statement.where(RiskAssessment.house == house)
    if state: statement = statement.where(RiskAssessment.state_name == state)
    if district_or_ida: statement = statement.where(RiskAssessment.district_or_ida == district_or_ida)
    if mp: statement = statement.where(RiskAssessment.mp_source_name == mp)
    if risk_band: statement = statement.where(RiskAssessment.risk_band == risk_band)
    if signal_category: statement = statement.where(RiskAssessment.work_key.in_(select(MonitoringSignal.work_key).where(MonitoringSignal.dataset_version == RiskAssessment.dataset_version, MonitoringSignal.category == signal_category)))
    if search: statement = statement.where(or_(RiskAssessment.work_key.ilike(f"%{search}%"), RiskAssessment.mp_source_name.ilike(f"%{search}%"), RiskAssessment.state_name.ilike(f"%{search}%"), RiskAssessment.district_or_ida.ilike(f"%{search}%")))
    return statement


def _alert_filters(statement, *, house: str | None, state: str | None, district_or_ida: str | None, mp: str | None, category: str | None, severity: str | None, search: str | None):
    if house: statement = statement.where(AnalyticalAlert.house == house)
    if category: statement = statement.where(AnalyticalAlert.category == category)
    if severity: statement = statement.where(AnalyticalAlert.severity == severity)
    if state or district_or_ida or mp:
        assessment = select(RiskAssessment.assessment_id).where(
            RiskAssessment.dataset_version == AnalyticalAlert.dataset_version,
            RiskAssessment.work_key == AnalyticalAlert.work_key,
        )
        if state: assessment = assessment.where(RiskAssessment.state_name == state)
        if district_or_ida: assessment = assessment.where(RiskAssessment.district_or_ida == district_or_ida)
        if mp: assessment = assessment.where(RiskAssessment.mp_source_name == mp)
        statement = statement.where(exists(assessment))
    if search: statement = statement.where(or_(AnalyticalAlert.work_key.ilike(f"%{search}%"), AnalyticalAlert.title.ilike(f"%{search}%"), AnalyticalAlert.category.ilike(f"%{search}%")))
    return statement


@router.get("/risk/summary", response_model=RiskSummaryResponse)
def risk_summary(principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    scope = resolve_active_scope(db)
    assessments = _scope(select(RiskAssessment).where(RiskAssessment.dataset_version == scope.release_version), principal, RiskAssessment)
    signals = _scope(select(MonitoringSignal).where(MonitoringSignal.dataset_version == scope.release_version), principal, MonitoringSignal)
    alerts = _scope(select(AnalyticalAlert).where(AnalyticalAlert.dataset_version == scope.release_version), principal, AnalyticalAlert)
    return RiskSummaryResponse(
        total_assessments=db.scalar(select(func.count()).select_from(assessments.subquery())) or 0,
        risk_distribution=_grouped_count(assessments, RiskAssessment.risk_band, db),
        signals_by_category=_grouped_count(signals, MonitoringSignal.category, db),
        alerts_by_severity=_grouped_count(alerts, AnalyticalAlert.severity, db),
        high_priority_works=db.scalar(select(func.count()).select_from(assessments.where(RiskAssessment.normalized_score >= 60).subquery())) or 0,
        provenance=_provenance(scope),
    )


@router.get("/risk/works", response_model=None)
def risk_works(limit: int = Query(50, ge=1, le=100), page: int | None = Query(None, ge=1), page_size: int = Query(25, ge=1, le=100), house: str | None = None, state: str | None = None, district_or_ida: str | None = None, mp: str | None = None, risk_band: str | None = None, signal_category: str | None = None, search: str | None = None, principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    scope = resolve_active_scope(db)
    statement = _risk_filters(_scope(select(RiskAssessment).where(RiskAssessment.dataset_version == scope.release_version), principal, RiskAssessment), house=house, state=state, district_or_ida=district_or_ida, mp=mp, risk_band=risk_band, signal_category=signal_category, search=search).order_by(RiskAssessment.normalized_score.desc())
    if page is None:
        return [_risk(row, scope) for row in db.scalars(statement.limit(limit)).all()]
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    rows = db.scalars(statement.limit(page_size).offset((page - 1) * page_size)).all()
    return ProtectedPage(items=[_risk(row, scope) for row in rows], pagination=_pagination(page, page_size, total), provenance=_provenance(scope))


def _risk(row: RiskAssessment, scope) -> RiskWorkResponse:
    return RiskWorkResponse(work_key=row.work_key, house=row.house, state_name=row.state_name, district_or_ida=row.district_or_ida, mp_source_name=row.mp_source_name, raw_score=row.raw_score, normalized_score=row.normalized_score, risk_band=row.risk_band, component_scores=row.component_scores, evidence=row.evidence, data_quality_context=row.data_quality_context, provenance=_provenance(scope, row.rules_version, row.model_version))


@router.get("/risk/works/{work_key:path}", response_model=RiskWorkResponse)
def risk_work(work_key: str, principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    scope = resolve_active_scope(db)
    row = db.scalar(_scope(select(RiskAssessment).where(RiskAssessment.dataset_version == scope.release_version, RiskAssessment.work_key == work_key), principal, RiskAssessment))
    if row is None:
        raise HTTPException(404, detail={"code": "RISK_ASSESSMENT_NOT_FOUND", "message": "No protected risk assessment exists for this work in the active release or authorized scope."})
    return _risk(row, scope)


@router.get("/alerts/summary", response_model=AlertSummaryResponse)
def alert_summary(principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    scope = resolve_active_scope(db)
    statement = _scope(select(AnalyticalAlert).where(AnalyticalAlert.dataset_version == scope.release_version), principal, AnalyticalAlert)
    return AlertSummaryResponse(total_alerts=db.scalar(select(func.count()).select_from(statement.subquery())) or 0, by_category=_grouped_count(statement, AnalyticalAlert.category, db), by_severity=_grouped_count(statement, AnalyticalAlert.severity, db), provenance=_provenance(scope))


def _alert(row: AnalyticalAlert, scope, context: RiskAssessment | None = None) -> AlertResponse:
    return AlertResponse(alert_id=row.alert_id, work_key=row.work_key, house=row.house, state_name=context.state_name if context else None, district_or_ida=context.district_or_ida if context else None, mp_source_name=context.mp_source_name if context else None, category=row.category, severity=row.severity, title=row.title, explanation=row.explanation, evidence=row.evidence, status=row.status, generated_at=row.generated_at, provenance=_provenance(scope))


def _alert_payloads(rows: list[AnalyticalAlert], scope, db: Session) -> list[AlertResponse]:
    if not rows:
        return []
    contexts = {
        row.work_key: row
        for row in db.scalars(
            select(RiskAssessment).where(
                RiskAssessment.dataset_version == scope.release_version,
                RiskAssessment.work_key.in_([item.work_key for item in rows]),
            )
        ).all()
    }
    return [_alert(row, scope, contexts.get(row.work_key)) for row in rows]


@router.get("/alerts", response_model=None)
def alerts(limit: int = Query(50, ge=1, le=100), page: int | None = Query(None, ge=1), page_size: int = Query(25, ge=1, le=100), house: str | None = None, state: str | None = None, district_or_ida: str | None = None, mp: str | None = None, category: str | None = None, severity: str | None = None, search: str | None = None, principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    scope = resolve_active_scope(db)
    statement = _alert_filters(_scope(select(AnalyticalAlert).where(AnalyticalAlert.dataset_version == scope.release_version), principal, AnalyticalAlert), house=house, state=state, district_or_ida=district_or_ida, mp=mp, category=category, severity=severity, search=search).order_by(AnalyticalAlert.generated_at.desc())
    if page is None:
        return _alert_payloads(db.scalars(statement.limit(limit)).all(), scope, db)
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    rows = db.scalars(statement.limit(page_size).offset((page - 1) * page_size)).all()
    return ProtectedPage(items=_alert_payloads(rows, scope, db), pagination=_pagination(page, page_size, total), provenance=_provenance(scope))


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
def alert(alert_id: str, principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    scope = resolve_active_scope(db)
    row = db.scalar(_scope(select(AnalyticalAlert).where(AnalyticalAlert.dataset_version == scope.release_version, AnalyticalAlert.alert_id == alert_id), principal, AnalyticalAlert))
    if row is None:
        raise HTTPException(404, detail={"code": "ALERT_NOT_FOUND", "message": "No protected alert exists for this identifier in the authorized scope."})
    context = db.scalar(select(RiskAssessment).where(RiskAssessment.dataset_version == scope.release_version, RiskAssessment.work_key == row.work_key))
    return _alert(row, scope, context)


@router.get("/duplicates/candidates", response_model=None)
def duplicates(limit: int = Query(50, ge=1, le=100), page: int | None = Query(None, ge=1), page_size: int = Query(25, ge=1, le=100), house: str | None = None, state: str | None = None, district_or_ida: str | None = None, mp: str | None = None, search: str | None = None, review_priority: str | None = None, similarity_min: float | None = Query(None, ge=0, le=1), principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    scope = resolve_active_scope(db)
    statement = select(DuplicateCandidate).where(DuplicateCandidate.dataset_version == scope.release_version)
    if review_priority: statement = statement.where(DuplicateCandidate.review_priority == review_priority)
    if similarity_min is not None: statement = statement.where(DuplicateCandidate.similarity_score >= similarity_min)
    # Both records must fall in server-authorized scope; optional filters apply to work A.
    allowed = _scope(select(RiskAssessment.work_key).where(RiskAssessment.dataset_version == scope.release_version), principal, RiskAssessment)
    filtered = _risk_filters(
        _scope(select(RiskAssessment.work_key).where(RiskAssessment.dataset_version == scope.release_version), principal, RiskAssessment),
        house=house, state=state, district_or_ida=district_or_ida, mp=mp, risk_band=None, signal_category=None, search=None,
    )
    statement = statement.where(DuplicateCandidate.work_a_key.in_(filtered), DuplicateCandidate.work_b_key.in_(allowed))
    if search:
        statement = statement.where(or_(DuplicateCandidate.work_a_key.ilike(f"%{search}%"), DuplicateCandidate.work_b_key.ilike(f"%{search}%")))
    statement = statement.order_by(DuplicateCandidate.similarity_score.desc())
    def payload(row): return DuplicateCandidateResponse(candidate_id=row.candidate_id, work_a_key=row.work_a_key, work_b_key=row.work_b_key, similarity_score=row.similarity_score, review_priority=row.review_priority, contextual_comparison=row.contextual_comparison, reason=row.reason, generated_at=row.generated_at, provenance=_provenance(scope))
    if page is None: return [payload(row) for row in db.scalars(statement.limit(limit)).all()]
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    return ProtectedPage(items=[payload(row) for row in db.scalars(statement.limit(page_size).offset((page - 1) * page_size)).all()], pagination=_pagination(page, page_size, total), provenance=_provenance(scope))


@router.get("/anomalies/summary", response_model=AnomalySummaryResponse)
def anomalies_summary(principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    scope = resolve_active_scope(db)
    statement = _scope(select(MonitoringSignal).where(MonitoringSignal.dataset_version == scope.release_version, MonitoringSignal.category == "ML_ANOMALY"), principal, MonitoringSignal)
    return AnomalySummaryResponse(total_ml_anomaly_signals=db.scalar(select(func.count()).select_from(statement.subquery())) or 0, model_version=MODEL_VERSION, dataset_version=scope.release_version, generated_at=datetime.now(UTC))


def _category_summary(category: str, principal: IntelligencePrincipal, db: Session) -> MonitoringCategoryResponse:
    scope = resolve_active_scope(db)
    statement = _scope(select(MonitoringSignal).where(MonitoringSignal.dataset_version == scope.release_version, MonitoringSignal.category == category), principal, MonitoringSignal)
    return MonitoringCategoryResponse(category=category, total_signals=db.scalar(select(func.count()).select_from(statement.subquery())) or 0, by_severity=_grouped_count(statement, MonitoringSignal.severity, db), by_house=_grouped_count(statement, MonitoringSignal.house, db), by_state=_grouped_count(statement, MonitoringSignal.state_name, db), provenance=_provenance(scope))


def _analytics_filters(principal: IntelligencePrincipal) -> AnalyticsFilters:
    if principal.role == "MP":
        return AnalyticsFilters(mp=principal.mp_scope)
    if principal.role == "DISTRICT_AUTHORITY":
        return AnalyticsFilters(district_or_ida=principal.district_scope)
    if principal.role == "STATE_NODAL_AUTHORITY":
        return AnalyticsFilters(state=principal.state_scope)
    return AnalyticsFilters()


@router.get("/monitoring/financial", response_model=MonitoringCategoryResponse)
def financial_monitoring(principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    summary = _category_summary("FINANCIAL", principal, db)
    payment = _category_summary("PAYMENT", principal, db)
    filters = _analytics_filters(principal)
    summary.related_category_counts = {"PAYMENT": payment.total_signals}
    summary.financial_patterns = {
        "expenditure_summary": expenditure_summary(db, filters).data,
        "expenditure_by_house": expenditure_by(db, "house", filters).data["rows"],
        "expenditure_by_state": expenditure_by(db, "state", filters).data["rows"],
    }
    return summary


@router.get("/monitoring/lifecycle", response_model=MonitoringCategoryResponse)
def lifecycle_monitoring(principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    summary = _category_summary("LIFECYCLE", principal, db)
    summary.observed_lifecycle = lifecycle_summary(db, _analytics_filters(principal)).data
    return summary

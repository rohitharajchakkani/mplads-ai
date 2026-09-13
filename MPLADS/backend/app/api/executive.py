"""Protected executive summaries over persisted monitoring evidence."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from app.api.deps import IntelligencePrincipal, get_db, require_intelligence_principal
from app.models import AnalyticalAlert, AnalyticsRun, MonitoringSignal, RiskAssessment
from app.models.benchmarking import BenchmarkResult, BenchmarkRun, Recommendation
from app.models.review import ReviewCase, ReviewEscalation
from app.schemas.executive import ExecutiveAttention, ExecutiveComparison, ExecutiveDrilldown, ExecutiveGeography, ExecutiveSummary, ExecutiveTrend, ExecutiveTrends
from app.schemas.intelligence import ProtectedProvenance
from app.services.versioning_service import resolve_active_scope

router = APIRouter(dependencies=[Depends(require_intelligence_principal)])
HIGH = {"HIGH", "VERY_HIGH"}


def _scope(statement, principal: IntelligencePrincipal, model):
    if principal.role in {"MINISTRY", "PLATFORM_ADMINISTRATOR"}: return statement
    if not hasattr(model, "mp_source_name"):
        allowed_work_keys = _scope(select(RiskAssessment.work_key), principal, RiskAssessment)
        return statement.where(model.work_key.in_(allowed_work_keys))
    if principal.role == "MP": return statement.where(model.mp_source_name == principal.mp_scope)
    if principal.role == "DISTRICT_AUTHORITY": return statement.where(model.district_or_ida == principal.district_scope)
    return statement.where(model.state_name == principal.state_scope)


def _count(db: Session, statement) -> int:
    return int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)


def _group(db: Session, statement, column) -> dict[str, int]:
    return {str(key or "Not available"): int(value) for key, value in db.execute(statement.with_only_columns(column, func.count()).group_by(column)).all()}


def _provenance(scope) -> ProtectedProvenance:
    return ProtectedProvenance(dataset_version=scope.release_version, generated_at=datetime.now(UTC), rules_version="executive-v1")


def _filtered(principal: IntelligencePrincipal, scope, *, house: str | None = None, state: str | None = None, district_or_ida: str | None = None, mp: str | None = None):
    def apply(statement, model):
        statement = _scope(statement.where(model.dataset_version == scope.release_version), principal, model)
        for column, value in ((model.house, house), (model.state_name, state), (model.district_or_ida, district_or_ida), (model.mp_source_name, mp)):
            if value: statement = statement.where(column == value)
        return statement
    return apply


def _summary(db: Session, principal: IntelligencePrincipal, scope, **filters) -> ExecutiveSummary:
    apply = _filtered(principal, scope, **filters)
    risks = apply(select(RiskAssessment), RiskAssessment); signals = apply(select(MonitoringSignal), MonitoringSignal)
    recs = apply(select(Recommendation), Recommendation); benches = apply(select(BenchmarkResult), BenchmarkResult)
    cases = apply(select(ReviewCase), ReviewCase)
    alerts = _scope(select(AnalyticalAlert).where(AnalyticalAlert.dataset_version == scope.release_version), principal, AnalyticalAlert)
    if filters.get("house"): alerts = alerts.where(AnalyticalAlert.house == filters["house"])
    if any(filters.get(key) for key in ("state", "district_or_ida", "mp")):
        work_keys = risks.with_only_columns(RiskAssessment.work_key)
        alerts = alerts.where(AnalyticalAlert.work_key.in_(work_keys))
    high_alerts = _count(db, alerts.where(AnalyticalAlert.severity.in_(HIGH)))
    backlog = _group(db, cases, ReviewCase.status)
    escalations = _count(db, _scope(select(ReviewEscalation).join(ReviewCase, ReviewEscalation.case_id == ReviewCase.case_id).where(ReviewCase.dataset_version == scope.release_version, ReviewEscalation.status == "OPEN"), principal, ReviewCase))
    return ExecutiveSummary(total_monitored_works=_count(db, risks), total_signals=_count(db, signals), total_alerts=_count(db, alerts), high_priority_alerts=high_alerts, high_priority_risk_works=_count(db, risks.where(RiskAssessment.risk_band.in_(HIGH))), review_backlog=backlog, active_escalations=escalations, available_benchmarks=_count(db, benches.where(BenchmarkResult.benchmark_available.is_(True))), benchmark_bottlenecks=_count(db, benches.where(BenchmarkResult.bottleneck_flag.is_(True))), active_recommendations=_count(db, recs.where(Recommendation.status != "RESOLVED")), recommendations_by_priority=_group(db, recs, Recommendation.priority), recommendations_by_status=_group(db, recs, Recommendation.status), provenance=_provenance(scope))


def _attention(summary: ExecutiveSummary, db: Session, principal: IntelligencePrincipal, scope, **filters) -> ExecutiveAttention:
    open_cases = sum(summary.review_backlog.get(key, 0) for key in ("OPEN", "ASSIGNED", "UNDER_REVIEW", "REOPENED")); followup = summary.review_backlog.get("FOLLOW_UP_REQUIRED", 0)
    signal_count = open_cases + followup + summary.active_escalations + summary.high_priority_alerts + summary.high_priority_risk_works
    if signal_count >= 10 or summary.active_escalations >= 2 or (open_cases >= 5 and summary.high_priority_alerts >= 5): level = "HIGH"
    elif 3 <= signal_count <= 9 or summary.active_escalations == 1 or open_cases >= 2: level = "MODERATE"
    else: level = "LOWER"
    drivers = [{"label": label, "count": count, "href": href} for label, count, href in [("High-priority alerts", summary.high_priority_alerts, "/monitoring/alerts"), ("High-priority risk works", summary.high_priority_risk_works, "/monitoring/risk"), ("Open review cases", open_cases, "/monitoring/reviews"), ("Follow-up cases", followup, "/monitoring/reviews"), ("Active escalations", summary.active_escalations, "/monitoring/reviews"), ("Benchmark bottlenecks", summary.benchmark_bottlenecks, "/monitoring/benchmarking"), ("Active recommendations", summary.active_recommendations, "/monitoring/recommendations")] if count]
    categories = _group(db, _filtered(principal, scope, **filters)(select(MonitoringSignal).where(MonitoringSignal.severity.in_(HIGH)), MonitoringSignal), MonitoringSignal.category)
    return ExecutiveAttention(level=level, signal_count=signal_count, drivers=drivers, high_priority_categories=categories, scope={"role": principal.role, "state": principal.state_scope, "district_or_ida": principal.district_scope, "mp": principal.mp_scope}, provenance=_provenance(scope))


@router.get("/executive/summary", response_model=ExecutiveSummary)
def summary(principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    return _summary(db, principal, resolve_active_scope(db))


@router.get("/executive/attention", response_model=ExecutiveAttention)
def attention(house: str | None = None, state: str | None = None, district_or_ida: str | None = None, mp: str | None = None, principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    scope = resolve_active_scope(db); values = _summary(db, principal, scope, house=house, state=state, district_or_ida=district_or_ida, mp=mp)
    return _attention(values, db, principal, scope, house=house, state=state, district_or_ida=district_or_ida, mp=mp)


@router.get("/executive/trends", response_model=ExecutiveTrends)
def trends(principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    scope = resolve_active_scope(db); runs = db.scalars(select(AnalyticsRun).where(AnalyticsRun.status == "COMPLETED").order_by(AnalyticsRun.completed_at.desc()).limit(2)).all()
    if len(runs) < 2: return ExecutiveTrends(available=False, message="Historical trend unavailable: only one completed analytical run is available.", rows=[], provenance=_provenance(scope))
    current, previous = runs[0], runs[1]; rows = []
    for category, current_value, previous_value in [("alerts", current.alert_count, previous.alert_count), ("signals", sum(current.signal_counts.values()), sum(previous.signal_counts.values())), ("risk_assessments", current.record_counts.get("risk_assessments", 0), previous.record_counts.get("risk_assessments", 0))]:
        change = current_value - previous_value; rows.append(ExecutiveTrend(category=category, current_value=current_value, previous_value=previous_value, absolute_change=change, percentage_change=round(change / previous_value * 100, 2) if previous_value else None))
    return ExecutiveTrends(available=True, message=None, rows=rows, provenance=_provenance(scope))


@router.get("/executive/geography", response_model=ExecutiveGeography)
def geography(limit: int = Query(12, ge=1, le=50), principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    scope = resolve_active_scope(db); risks = _filtered(principal, scope)(select(RiskAssessment), RiskAssessment)
    rows = db.execute(risks.with_only_columns(RiskAssessment.state_name, func.count(), func.sum(RiskAssessment.risk_band.in_(HIGH).cast(Integer))).group_by(RiskAssessment.state_name).order_by(func.count().desc()).limit(limit)).all()
    data = [{"state": state or "Not available", "monitored_works": int(total), "high_priority_risk_works": int(high or 0), "high_priority_risk_rate": round((high or 0) / total, 4) if total else None} for state, total, high in rows]
    return ExecutiveGeography(rows=data, material_concentration=bool(data and data[0]["high_priority_risk_works"] > 0), message=None if data else "No material concentration identified from the current data.", provenance=_provenance(scope))


@router.get("/executive/comparison", response_model=ExecutiveComparison)
def comparison(principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    scope = resolve_active_scope(db); risks = _filtered(principal, scope)(select(RiskAssessment), RiskAssessment); bench = _filtered(principal, scope)(select(BenchmarkResult), BenchmarkResult)
    risk_rows = {house: (int(total), int(high or 0)) for house, total, high in db.execute(risks.with_only_columns(RiskAssessment.house, func.count(), func.sum(RiskAssessment.risk_band.in_(HIGH).cast(Integer))).group_by(RiskAssessment.house)).all()}
    bench_rows = {house: int(total) for house, total in db.execute(bench.where(BenchmarkResult.benchmark_available.is_(True)).with_only_columns(BenchmarkResult.house, func.count()).group_by(BenchmarkResult.house)).all()}
    return ExecutiveComparison(rows=[{"house": house, "monitored_works": total, "high_priority_risk_works": high, "available_benchmarks": bench_rows.get(house, 0)} for house, (total, high) in sorted(risk_rows.items())], provenance=_provenance(scope))


@router.get("/executive/drilldown", response_model=ExecutiveDrilldown)
def drilldown(house: str | None = None, state: str | None = None, district_or_ida: str | None = None, mp: str | None = None, signal_category: str | None = None, risk_band: str | None = None, alert_severity: str | None = None, review_status: str | None = None, benchmark_status: bool | None = None, recommendation_status: str | None = None, principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    scope = resolve_active_scope(db); filters = {"house": house, "state": state, "district_or_ida": district_or_ida, "mp": mp}; values = _summary(db, principal, scope, **filters)
    alerts = _scope(select(AnalyticalAlert).where(AnalyticalAlert.dataset_version == scope.release_version), principal, AnalyticalAlert)
    if house: alerts = alerts.where(AnalyticalAlert.house == house)
    if alert_severity: alerts = alerts.where(AnalyticalAlert.severity == alert_severity)
    if signal_category: alerts = alerts.where(AnalyticalAlert.category == signal_category)
    queue = [{"alert_id": row.alert_id, "work_key": row.work_key, "category": row.category, "severity": row.severity, "title": row.title, "generated_at": row.generated_at, "reason": "Ordered by severity then recency from persisted alerts."} for row in db.scalars(alerts.order_by(AnalyticalAlert.severity.desc(), AnalyticalAlert.generated_at.desc()).limit(25)).all()]
    return ExecutiveDrilldown(summary=values, priority_queue=queue, links={"risk": "/monitoring/risk", "alerts": "/monitoring/alerts", "reviews": "/monitoring/reviews", "benchmarking": "/monitoring/benchmarking", "recommendations": "/monitoring/recommendations"}, provenance=_provenance(scope))

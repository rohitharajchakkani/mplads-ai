"""Protected persisted peer benchmarks and deterministic review recommendations."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import IntelligencePrincipal, get_db, require_intelligence_principal, require_review_actor
from app.api.reviews import create_case
from app.benchmarking.engine import ensure_benchmark_run, ensure_recommendations
from app.models.benchmarking import BenchmarkCohort, BenchmarkResult, BenchmarkRun, Recommendation, RecommendationEvent
from app.schemas.benchmarking import BenchmarkPage, BenchmarkPeers, BenchmarkResultResponse, BenchmarkSummary, RecommendationPage, RecommendationResponse, RecommendationStatusRequest
from app.schemas.intelligence import ProtectedProvenance
from app.schemas.reviews import CaseCreateRequest, ReviewCaseItem
from app.models import AnalyticalAlert, MonitoringSignal

router = APIRouter(dependencies=[Depends(require_intelligence_principal)])
RECOMMENDATION_STATUSES = {"NOTED", "UNDER_REVIEW", "ACTION_INITIATED", "RESOLVED"}


def _now() -> datetime:
    return datetime.now(UTC)


def _scope(statement, principal: IntelligencePrincipal, model):
    if principal.role in {"MINISTRY", "PLATFORM_ADMINISTRATOR"}:
        return statement
    if principal.role == "MP": return statement.where(model.mp_source_name == principal.mp_scope)
    if principal.role == "DISTRICT_AUTHORITY": return statement.where(model.district_or_ida == principal.district_scope)
    return statement.where(model.state_name == principal.state_scope)


def _pagination(page: int, size: int, total: int) -> dict[str, int]:
    return {"total": total, "page": page, "page_size": size, "total_pages": (total + size - 1) // size if total else 0}


def _benchmark(row: BenchmarkResult) -> BenchmarkResultResponse:
    return BenchmarkResultResponse(result_id=row.result_id, entity_type=row.entity_type, entity_id=row.entity_id, house=row.house, state_name=row.state_name, district_or_ida=row.district_or_ida, mp_source_name=row.mp_source_name, metric=row.metric, formula=row.formula, metric_details=row.metric_details, value=row.value, peer_median=row.peer_median, p25=row.p25, p75=row.p75, p90=row.p90, iqr=row.iqr, peer_count=row.peer_count, valid_work_count=row.valid_work_count, benchmark_available=row.benchmark_available, unavailable_reason=row.unavailable_reason, directionality=row.directionality, bottleneck_flag=row.bottleneck_flag, interpretation=row.interpretation, dataset_version=row.dataset_version, benchmark_version=row.benchmark_version, provenance_hash=row.provenance_hash, generated_at=row.generated_at)


def _recommendation(row: Recommendation) -> RecommendationResponse:
    return RecommendationResponse(recommendation_id=row.recommendation_id, canonical_work_key=row.canonical_work_key, entity_type=row.entity_type, entity_id=row.entity_id, house=row.house, state_name=row.state_name, district_or_ida=row.district_or_ida, mp_source_name=row.mp_source_name, recommendation_type=row.recommendation_type, reason=row.reason, evidence_references=row.evidence_references, priority=row.priority, dataset_version=row.dataset_version, status=row.status, generated_at=row.generated_at, updated_at=row.updated_at, version=row.version)


@router.get("/benchmarking/summary", response_model=BenchmarkSummary)
def summary(principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    run = ensure_benchmark_run(db)
    statement = _scope(select(BenchmarkResult).where(BenchmarkResult.run_id == run.run_id), principal, BenchmarkResult)
    by_metric = {metric: int(count) for metric, count in db.execute(statement.with_only_columns(BenchmarkResult.metric, func.count()).group_by(BenchmarkResult.metric)).all()}
    bottlenecks = db.scalar(select(func.count()).select_from(statement.where(BenchmarkResult.bottleneck_flag.is_(True)).subquery())) or 0
    return BenchmarkSummary(run_id=run.run_id, entity_count=run.entity_count, result_count=sum(by_metric.values()), by_metric=by_metric, bottleneck_count=bottlenecks, benchmark_version=run.benchmark_version, dataset_version=run.dataset_version, generated_at=run.completed_at or run.started_at)


@router.get("/benchmarking/results", response_model=BenchmarkPage)
def results(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), house: str | None = None, state: str | None = None, district_or_ida: str | None = None, mp: str | None = None, metric: str | None = None, bottleneck: bool | None = None, entity_id: str | None = None, principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    run = ensure_benchmark_run(db)
    statement = _scope(select(BenchmarkResult).where(BenchmarkResult.run_id == run.run_id), principal, BenchmarkResult)
    for column, value in [(BenchmarkResult.house, house), (BenchmarkResult.state_name, state), (BenchmarkResult.district_or_ida, district_or_ida), (BenchmarkResult.mp_source_name, mp), (BenchmarkResult.metric, metric), (BenchmarkResult.entity_id, entity_id)]:
        if value: statement = statement.where(column == value)
    if bottleneck is not None: statement = statement.where(BenchmarkResult.bottleneck_flag == bottleneck)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(statement.order_by(BenchmarkResult.bottleneck_flag.desc(), BenchmarkResult.metric, BenchmarkResult.entity_id).limit(page_size).offset((page - 1) * page_size)).all()
    return BenchmarkPage(items=[_benchmark(row) for row in rows], pagination=_pagination(page, page_size, total), provenance=ProtectedProvenance(dataset_version=run.dataset_version, generated_at=run.completed_at or run.started_at, rules_version=run.benchmark_version))


@router.get("/benchmarking/{entity_type}/{entity_id}", response_model=list[BenchmarkResultResponse])
def entity_benchmarks(entity_type: str, entity_id: str, principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    run = ensure_benchmark_run(db)
    rows = db.scalars(_scope(select(BenchmarkResult).where(BenchmarkResult.run_id == run.run_id, BenchmarkResult.entity_type == entity_type, BenchmarkResult.entity_id == entity_id), principal, BenchmarkResult)).all()
    if not rows:
        raise HTTPException(status_code=404, detail={"code": "BENCHMARK_NOT_FOUND", "message": "No benchmark result exists in the authorized scope."})
    return [_benchmark(row) for row in rows]


@router.get("/benchmarking/peers", response_model=BenchmarkPeers)
def peers(result_id: str = Query(...), principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    row = db.scalar(_scope(select(BenchmarkResult).where(BenchmarkResult.result_id == result_id), principal, BenchmarkResult))
    if row is None: raise HTTPException(status_code=404, detail={"code": "BENCHMARK_NOT_FOUND", "message": "No benchmark result exists in the authorized scope."})
    cohort = db.scalar(select(BenchmarkCohort).where(BenchmarkCohort.cohort_id == row.cohort_id))
    if cohort is None: raise HTTPException(status_code=500, detail={"code": "BENCHMARK_COHORT_MISSING", "message": "The persisted benchmark cohort is unavailable."})
    scoped_peers = db.scalars(
        _scope(
            select(BenchmarkResult).where(
                BenchmarkResult.run_id == row.run_id,
                BenchmarkResult.entity_type == "MP",
                BenchmarkResult.entity_id.in_(cohort.peer_ids),
            ),
            principal,
            BenchmarkResult,
        )
    ).all()
    return BenchmarkPeers(result_id=row.result_id, cohort_definition=cohort.definition, peer_ids=sorted({peer.entity_id for peer in scoped_peers if peer.entity_id != row.entity_id}), peer_count=row.peer_count, provenance=ProtectedProvenance(dataset_version=row.dataset_version, generated_at=row.generated_at, rules_version=row.benchmark_version))


@router.get("/recommendations", response_model=RecommendationPage)
def recommendations(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), house: str | None = None, state: str | None = None, district_or_ida: str | None = None, mp: str | None = None, priority: str | None = None, status: str | None = None, search: str | None = None, principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    run = ensure_benchmark_run(db); ensure_recommendations(db, run)
    statement = _scope(select(Recommendation).where(Recommendation.dataset_version == run.dataset_version), principal, Recommendation)
    for column, value in [(Recommendation.house, house), (Recommendation.state_name, state), (Recommendation.district_or_ida, district_or_ida), (Recommendation.mp_source_name, mp), (Recommendation.priority, priority), (Recommendation.status, status)]:
        if value: statement = statement.where(column == value)
    if search: statement = statement.where(or_(Recommendation.entity_id.ilike(f"%{search}%"), Recommendation.reason.ilike(f"%{search}%"), Recommendation.recommendation_type.ilike(f"%{search}%")))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(statement.order_by(Recommendation.priority.desc(), Recommendation.generated_at.desc()).limit(page_size).offset((page - 1) * page_size)).all()
    return RecommendationPage(items=[_recommendation(row) for row in rows], pagination=_pagination(page, page_size, total), provenance=ProtectedProvenance(dataset_version=run.dataset_version, generated_at=run.completed_at or run.started_at, rules_version=run.benchmark_version))


@router.get("/recommendations/{recommendation_id}", response_model=RecommendationResponse)
def recommendation(recommendation_id: str, principal: IntelligencePrincipal = Depends(require_intelligence_principal), db: Session = Depends(get_db)):
    row = db.scalar(_scope(select(Recommendation).where(Recommendation.recommendation_id == recommendation_id), principal, Recommendation))
    if row is None: raise HTTPException(status_code=404, detail={"code": "RECOMMENDATION_NOT_FOUND", "message": "No recommendation exists in the authorized scope."})
    return _recommendation(row)


@router.post("/recommendations/{recommendation_id}/status", response_model=RecommendationResponse)
def update_recommendation_status(recommendation_id: str, payload: RecommendationStatusRequest, principal: IntelligencePrincipal = Depends(require_review_actor), db: Session = Depends(get_db)):
    row = db.scalar(_scope(select(Recommendation).where(Recommendation.recommendation_id == recommendation_id), principal, Recommendation))
    if row is None: raise HTTPException(status_code=404, detail={"code": "RECOMMENDATION_NOT_FOUND", "message": "No recommendation exists in the authorized scope."})
    if row.version != payload.version: raise HTTPException(status_code=409, detail={"code": "RECOMMENDATION_VERSION_CONFLICT", "message": "This recommendation changed. Refresh before updating it."})
    if payload.status not in RECOMMENDATION_STATUSES: raise HTTPException(status_code=422, detail={"code": "RECOMMENDATION_INVALID_STATUS", "message": "Unsupported recommendation status."})
    if payload.status == "NOTED" and row.status != "NOTED": raise HTTPException(status_code=422, detail={"code": "RECOMMENDATION_INVALID_TRANSITION", "message": "Recommendations cannot return to NOTED."})
    previous = row.status; row.status = payload.status; row.version += 1; row.updated_at = _now()
    db.add(RecommendationEvent(event_id=f"rec_evt_{uuid4().hex}", recommendation_id=row.recommendation_id, actor=principal.actor or "", action="STATUS_CHANGED", occurred_at=row.updated_at, metadata_json={"from_status": previous, "to_status": row.status}))
    db.commit(); db.refresh(row)
    return _recommendation(row)


@router.post("/recommendations/{recommendation_id}/review-case", response_model=ReviewCaseItem, status_code=201)
def recommendation_review_case(recommendation_id: str, principal: IntelligencePrincipal = Depends(require_review_actor), db: Session = Depends(get_db)):
    row = db.scalar(_scope(select(Recommendation).where(Recommendation.recommendation_id == recommendation_id), principal, Recommendation))
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "RECOMMENDATION_NOT_FOUND", "message": "No recommendation exists in the authorized scope."})
    signal_id = row.evidence_references.get("signal_id")
    if signal_id:
        return create_case(CaseCreateRequest(signal_id=str(signal_id)), principal, db)
    if row.canonical_work_key:
        alert = db.scalar(select(AnalyticalAlert).where(AnalyticalAlert.dataset_version == row.dataset_version, AnalyticalAlert.work_key == row.canonical_work_key).order_by(AnalyticalAlert.generated_at.desc()))
        if alert:
            return create_case(CaseCreateRequest(alert_id=alert.alert_id), principal, db)
        signal = db.scalar(select(MonitoringSignal).where(MonitoringSignal.dataset_version == row.dataset_version, MonitoringSignal.work_key == row.canonical_work_key).order_by(MonitoringSignal.generated_at.desc()))
        if signal:
            return create_case(CaseCreateRequest(signal_id=signal.signal_id), principal, db)
    raise HTTPException(status_code=422, detail={"code": "RECOMMENDATION_REVIEW_SOURCE_UNAVAILABLE", "message": "This recommendation has no reviewable alert or signal evidence in the active release."})

"""Deterministic same-House MP benchmarks, persisted for the active dataset."""
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from hashlib import sha256
import json
from statistics import median
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CanonicalWork, CompletedWorkRecord, DatasetVersion, ExpenditureTransaction, MonitoringSignal, RiskAssessment, SanctionedWorkRecord
from app.models.benchmarking import BenchmarkCohort, BenchmarkResult, BenchmarkRun, Recommendation
from app.services.versioning_service import resolve_active_scope

BENCHMARK_VERSION = "benchmark-v2"
MIN_PEERS, MIN_VALID_WORKS = 5, 10
METRICS = {
    "SANCTION_LATENCY_DAYS": ("HIGHER_IS_CONCERN", "Observed days from recommendation to sanction for works with both valid source dates."),
    "COMPLETION_RATIO": ("LOWER_IS_CONCERN", "Completed works divided by works with a linked sanction record."),
    "EXPENDITURE_PACING_RATIO": ("LOWER_IS_CONCERN", "Linked expenditure divided by linked sanction amount for works having both source record types."),
}


def _now() -> datetime: return datetime.now(UTC)
def _hash(value: object) -> str: return sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()
def _percentile(values: list[float], q: float) -> float:
    values = sorted(values); position = (len(values) - 1) * q; lower, upper = int(position), min(int(position) + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)
def _duration(start: str | None, end: str | None) -> float | None:
    try: return float((datetime.fromisoformat(end or "").date() - datetime.fromisoformat(start or "").date()).days)
    except ValueError: return None


def _observations(db: Session):
    scope = resolve_active_scope(db)
    rows = db.execute(select(CanonicalWork.canonical_work_key, CanonicalWork.house, CanonicalWork.mp_source_name, CanonicalWork.state_name, CanonicalWork.district_or_ida).join(DatasetVersion, CanonicalWork.first_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id, CanonicalWork.mp_source_name.is_not(None))).all()
    entities, work_owner = {}, {}
    for key, house, mp, state, district in rows:
        owner = (house, mp); work_owner[key] = owner
        entities.setdefault(owner, {"house": house, "entity_id": mp, "state": state, "district": district, "works": set(), "latency": {}, "sanctioned": set(), "completed": set(), "sanction": defaultdict(float), "expenditure": defaultdict(float)})["works"].add(key)
    sanctions = db.execute(select(SanctionedWorkRecord.canonical_work_key, SanctionedWorkRecord.recommended_date, SanctionedWorkRecord.sanction_date, SanctionedWorkRecord.sanction_amount).join(DatasetVersion, SanctionedWorkRecord.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id, SanctionedWorkRecord.canonical_work_key.is_not(None))).all()
    for key, recommended, sanctioned, amount in sanctions:
        owner = work_owner.get(key)
        if not owner: continue
        item = entities[owner]; item["sanctioned"].add(key)
        if amount is not None: item["sanction"][key] += float(amount)
        days = _duration(recommended, sanctioned)
        if days is not None and days >= 0: item["latency"][key] = min(item["latency"].get(key, days), days)
    for key in db.execute(select(CompletedWorkRecord.canonical_work_key).join(DatasetVersion, CompletedWorkRecord.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id, CompletedWorkRecord.canonical_work_key.is_not(None))).scalars():
        if owner := work_owner.get(key): entities[owner]["completed"].add(key)
    expenses = db.execute(select(ExpenditureTransaction.canonical_work_key, ExpenditureTransaction.disbursed_amount).join(DatasetVersion, ExpenditureTransaction.source_dataset_version_id == DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id, ExpenditureTransaction.canonical_work_key.is_not(None))).all()
    for key, amount in expenses:
        if (owner := work_owner.get(key)) and amount is not None: entities[owner]["expenditure"][key] += float(amount)
    return scope, entities


def _metrics(item: dict) -> dict[str, tuple[float | None, int, dict]]:
    latency, eligible = list(item["latency"].values()), item["sanctioned"]
    pacing = set(item["sanction"]) & set(item["expenditure"])
    sanction_total = sum(item["sanction"][key] for key in pacing)
    completed = len(item["completed"] & eligible)
    expenditure_total = sum(item["expenditure"][key] for key in pacing)
    return {
        "SANCTION_LATENCY_DAYS": (float(median(latency)) if latency else None, len(latency), {"valid_work_count": len(latency), "mean_days": sum(latency) / len(latency) if latency else None, "min_days": min(latency) if latency else None, "max_days": max(latency) if latency else None}),
        "COMPLETION_RATIO": (completed / len(eligible) if eligible else None, len(eligible), {"numerator_completed_works": completed, "denominator_sanctioned_works": len(eligible), "ratio": completed / len(eligible) if eligible else None}),
        "EXPENDITURE_PACING_RATIO": (expenditure_total / sanction_total if pacing and sanction_total else None, len(pacing), {"matched_work_count": len(pacing), "expenditure_total": expenditure_total, "sanction_total": sanction_total, "ratio": expenditure_total / sanction_total if pacing and sanction_total else None}),
    }


def ensure_benchmark_run(db: Session) -> BenchmarkRun:
    scope = resolve_active_scope(db); configuration = {"entity_type": "MP", "same_house": True, "minimum_peers": MIN_PEERS, "minimum_valid_works": MIN_VALID_WORKS, "metrics": list(METRICS)}; configuration_hash = _hash(configuration)
    if run := db.scalar(select(BenchmarkRun).where(BenchmarkRun.dataset_version == scope.release_version, BenchmarkRun.benchmark_version == BENCHMARK_VERSION, BenchmarkRun.configuration_hash == configuration_hash, BenchmarkRun.status == "COMPLETED")): return run
    started = _now(); run = BenchmarkRun(run_id=f"bench_run_{uuid4().hex}", dataset_version=scope.release_version, benchmark_version=BENCHMARK_VERSION, configuration_hash=configuration_hash, started_at=started, completed_at=None, status="STARTED", entity_count=0, result_count=0, configuration=configuration, error_summary=None); db.add(run); db.flush()
    try:
        _, entities = _observations(db); computed = {key: _metrics(item) for key, item in entities.items()}; cohorts = {}
        for house in sorted({item["house"] for item in entities.values()}):
            for metric in METRICS:
                ids = sorted(key[1] for key, values in computed.items() if key[0] == house and values[metric][0] is not None and values[metric][1] >= MIN_VALID_WORKS)
                cohort = BenchmarkCohort(cohort_id=f"bench_cohort_{uuid4().hex}", run_id=run.run_id, entity_type="MP", house=house, metric=metric, definition={"same_house": True, "minimum_peers": MIN_PEERS, "minimum_valid_works": MIN_VALID_WORKS, "metric": metric}, peer_ids=ids, peer_count=len(ids), valid_entities=len(ids), fingerprint=_hash({"run": run.run_id, "house": house, "metric": metric, "peers": ids}), created_at=started); db.add(cohort); cohorts[(house, metric)] = cohort
        db.flush(); results = []
        for entity, item in entities.items():
            house, entity_id = entity
            for metric, (value, valid_count, metric_details) in computed[entity].items():
                peer_values = [(key[1], float(values[metric][0])) for key, values in computed.items() if key[0] == house and key != entity and values[metric][0] is not None and values[metric][1] >= MIN_VALID_WORKS]
                available = value is not None and valid_count >= MIN_VALID_WORKS and len(peer_values) >= MIN_PEERS
                p25 = p75 = p90 = peer_median = iqr = None; bottleneck = False
                if available:
                    values = [peer for _, peer in peer_values]; p25, p75, p90, peer_median = _percentile(values, .25), _percentile(values, .75), _percentile(values, .90), float(median(values)); iqr = p75 - p25
                    if METRICS[metric][0] == "HIGHER_IS_CONCERN": bottleneck, interpretation = value > p90 or value > p75 + 1.5 * iqr, "Potential bottleneck: longer-than-peer observed duration." if value > p90 or value > p75 + 1.5 * iqr else ("Above peer benchmark." if value > peer_median else "At or below peer benchmark.")
                    else: bottleneck, interpretation = value < p25 - 1.5 * iqr, "Potential bottleneck: below peer benchmark." if value < p25 - 1.5 * iqr else ("Below peer benchmark." if value < peer_median else "At or above peer benchmark.")
                else: interpretation = "Benchmark unavailable: insufficient comparable data."
                provenance = {"dataset_version": scope.release_version, "benchmark_version": BENCHMARK_VERSION, "run_id": run.run_id, "entity_id": entity_id, "house": house, "metric": metric, "value": value, "metric_details": metric_details, "peer_ids": [peer for peer, _ in peer_values], "valid_work_count": valid_count}
                results.append(BenchmarkResult(result_id=f"bench_result_{uuid4().hex}", run_id=run.run_id, cohort_id=cohorts[(house, metric)].cohort_id, entity_type="MP", entity_id=entity_id, house=house, state_name=item["state"], district_or_ida=item["district"], mp_source_name=entity_id, metric=metric, formula=METRICS[metric][1], metric_details=metric_details, value=value, peer_median=peer_median, p25=p25, p75=p75, p90=p90, iqr=iqr, peer_count=len(peer_values), valid_work_count=valid_count, benchmark_available=available, unavailable_reason=None if available else ("Insufficient peer data" if len(peer_values) < MIN_PEERS else "Insufficient valid work observations"), directionality=METRICS[metric][0], bottleneck_flag=bottleneck, interpretation=interpretation, dataset_version=scope.release_version, benchmark_version=BENCHMARK_VERSION, provenance_hash=_hash(provenance), generated_at=started))
        db.add_all(results); run.entity_count, run.result_count, run.status, run.completed_at = len(entities), len(results), "COMPLETED", _now(); db.commit()
    except Exception as exc:
        db.rollback(); db.add(BenchmarkRun(run_id=run.run_id, dataset_version=scope.release_version, benchmark_version=BENCHMARK_VERSION, configuration_hash=configuration_hash, started_at=started, completed_at=_now(), status="FAILED", entity_count=0, result_count=0, configuration=configuration, error_summary=str(exc)[:4000])); db.commit(); raise
    return run


def ensure_recommendations(db: Session, run: BenchmarkRun) -> None:
    if db.scalar(select(func.count()).select_from(Recommendation).where(Recommendation.dataset_version == run.dataset_version)): return
    now = _now(); rows = []
    def add(work, entity_type, entity_id, house, state, district, mp, kind, reason, evidence, priority):
        rows.append(Recommendation(recommendation_id=f"rec_{uuid4().hex}", canonical_work_key=work, entity_type=entity_type, entity_id=entity_id, house=house, state_name=state, district_or_ida=district, mp_source_name=mp, recommendation_type=kind, reason=reason, evidence_references=evidence, priority=priority, dataset_version=run.dataset_version, status="NOTED", fingerprint=_hash({"dataset": run.dataset_version, "entity": entity_id, "type": kind, "evidence": evidence}), generated_at=now, updated_at=now, version=1))
    signals = db.scalars(select(MonitoringSignal).where(MonitoringSignal.dataset_version == run.dataset_version)).all()
    signal_actions = {"FINANCIAL": ("EXPENDITURE_PAYMENT_REVIEW", "Review supporting expenditure and payment records for this work."), "PAYMENT": ("EXPENDITURE_PAYMENT_REVIEW", "Review supporting expenditure and payment records for this work."), "LIFECYCLE": ("LIFECYCLE_SOURCE_REVIEW", "Review the available lifecycle timeline and supporting source records."), "DUPLICATE_CANDIDATE": ("DUPLICATE_CONTEXT_COMPARISON", "Compare this work with linked similar works using available contextual evidence."), "ML_ANOMALY": ("ANOMALY_EVIDENCE_REVIEW", "Review the analytical evidence and supporting source records for this differing record pattern.")}
    for signal in signals:
        if action := signal_actions.get(signal.category): add(signal.work_key, "WORK", signal.work_key, signal.house, signal.state_name, signal.district_or_ida, signal.mp_source_name, action[0], action[1], {"signal_id": signal.signal_id, "category": signal.category, "rule_id": signal.rule_id}, signal.severity)
    for risk in db.scalars(select(RiskAssessment).where(RiskAssessment.dataset_version == run.dataset_version, RiskAssessment.risk_band.in_(["HIGH", "VERY_HIGH"]))).all(): add(risk.work_key, "WORK", risk.work_key, risk.house, risk.state_name, risk.district_or_ida, risk.mp_source_name, "COMBINED_EVIDENCE_REVIEW", "Review the combined monitoring evidence and available supporting records.", {"risk_assessment_id": risk.assessment_id, "risk_band": risk.risk_band}, risk.risk_band)
    for result in db.scalars(select(BenchmarkResult).where(BenchmarkResult.run_id == run.run_id, BenchmarkResult.bottleneck_flag.is_(True))).all(): add(None, result.entity_type, result.entity_id, result.house, result.state_name, result.district_or_ida, result.mp_source_name, "PEER_COMPARISON_REVIEW", "Compare the observed metric with same-House peers and review supporting documentation.", {"benchmark_result_id": result.result_id, "metric": result.metric, "provenance_hash": result.provenance_hash}, "MEDIUM")
    db.add_all(rows); db.commit()

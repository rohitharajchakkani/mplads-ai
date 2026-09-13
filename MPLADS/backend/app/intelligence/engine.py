"""Deterministic feature extraction, signals, ML evidence, risk, and alerts.

This module is deliberately an explicit execution target. Importing it never runs
analytics; ``run_monitoring_engine`` is invoked only by the CLI or an authorized
operator process.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from math import log1p
from statistics import quantiles
from typing import Any, Iterable
from uuid import uuid4

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AnalyticalAlert, AnalyticsRun, CanonicalWork, CompletedWorkRecord, DatasetVersion,
    DuplicateCandidate, ExpenditureTransaction, MonitoringSignal, RiskAssessment,
    SanctionedWorkRecord,
)
from app.services.versioning_service import resolve_active_scope

RULES_VERSION = "monitoring-rules-v1"
MODEL_VERSION = "isolation-forest-v1"
DUPLICATE_ENGINE_VERSION = "tfidf-cosine-v1"
FEATURE_VERSION = "work-features-v1"
RISK_MAXIMUM = 95

# Every configured threshold is documented in docs/RISK_METHODOLOGY.md.
CONFIG: dict[str, Any] = {
    "expenditure_ratio_threshold": 1.0,
    "payment_concentration_threshold": 0.80,
    "transaction_count_quantile": 0.95,
    "short_period_days": 30,
    "short_period_transaction_count": 5,
    "lifecycle_peer_quantile": 0.90,
    "lifecycle_min_peer_count": 20,
    "duplicate_similarity_threshold": 0.88,
    "duplicate_high_priority_threshold": 0.95,
    "duplicate_max_neighbors": 3,
    "duplicate_max_block_size": 2000,
    "ml_contamination": 0.05,
    "ml_random_seed": 9047,
    "ml_min_records": 100,
}


@dataclass(frozen=True)
class WorkFeature:
    work_key: str
    house: str
    state: str | None
    district: str | None
    mp: str | None
    constituency: str | None
    description: str | None
    sanction: float | None
    expenditure: float | None
    transaction_count: int
    max_transaction: float | None
    transaction_dates: tuple[date, ...]
    recommended_date: date | None
    sanction_date: date | None
    completion_date: date | None

    @property
    def expenditure_ratio(self) -> float | None:
        return self.expenditure / self.sanction if self.sanction and self.sanction > 0 and self.expenditure is not None else None

    @property
    def payment_concentration(self) -> float | None:
        return self.max_transaction / self.expenditure if self.expenditure and self.expenditure > 0 and self.max_transaction is not None else None

    @property
    def lifecycle_days(self) -> int | None:
        return (self.completion_date - self.sanction_date).days if self.completion_date and self.sanction_date and self.completion_date >= self.sanction_date else None

    @property
    def data_quality(self) -> dict[str, bool]:
        return {
            "missing_work_description": not bool(self.description and self.description.strip()),
            "missing_sanction_amount": self.sanction is None,
            "missing_expenditure_amount": self.expenditure is None,
            "missing_state": self.state is None,
            "missing_district_or_ida": self.district is None,
        }


def _fingerprint(*parts: object) -> str:
    return sha256("\x1f".join(str(part) for part in parts).encode("utf-8")).hexdigest()


def _identifier(prefix: str, fingerprint: str) -> str:
    return f"{prefix}_{fingerprint[:28]}"


def _date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _percentile(values: Iterable[float], percentile: float) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * percentile
    lower, upper = int(position), min(int(position) + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def extract_features(session: Session) -> tuple[object, list[WorkFeature]]:
    """Read only the active release and return work-level supported features."""
    scope = resolve_active_scope(session)
    works = session.scalars(
        select(CanonicalWork).join(DatasetVersion, CanonicalWork.first_dataset_version_id == DatasetVersion.id)
        .where(DatasetVersion.batch_id == scope.batch_id)
    ).all()
    versions = select(DatasetVersion.id).where(DatasetVersion.batch_id == scope.batch_id)
    sanctions = {
        row.work_key: row for row in session.execute(
            select(SanctionedWorkRecord.canonical_work_key.label("work_key"), func.sum(SanctionedWorkRecord.sanction_amount).label("amount"), func.min(SanctionedWorkRecord.recommended_date).label("recommended"), func.min(SanctionedWorkRecord.sanction_date).label("sanction"))
            .where(SanctionedWorkRecord.source_dataset_version_id.in_(versions), SanctionedWorkRecord.canonical_work_key.is_not(None))
            .group_by(SanctionedWorkRecord.canonical_work_key)
        )
    }
    completions = {
        row.work_key: row.completion for row in session.execute(
            select(CompletedWorkRecord.canonical_work_key.label("work_key"), func.min(CompletedWorkRecord.completion_date).label("completion"))
            .where(CompletedWorkRecord.source_dataset_version_id.in_(versions), CompletedWorkRecord.canonical_work_key.is_not(None))
            .group_by(CompletedWorkRecord.canonical_work_key)
        )
    }
    transactions: dict[str, list[tuple[float | None, date | None]]] = defaultdict(list)
    for row in session.execute(
        select(ExpenditureTransaction.canonical_work_key, ExpenditureTransaction.disbursed_amount, ExpenditureTransaction.expenditure_date)
        .where(ExpenditureTransaction.source_dataset_version_id.in_(versions), ExpenditureTransaction.canonical_work_key.is_not(None))
    ):
        transactions[row.canonical_work_key].append((float(row.disbursed_amount) if row.disbursed_amount is not None else None, _date(row.expenditure_date)))
    features = []
    for work in works:
        sanction = sanctions.get(work.canonical_work_key)
        txs = transactions.get(work.canonical_work_key, [])
        amounts = [amount for amount, _ in txs if amount is not None]
        features.append(WorkFeature(
            work_key=work.canonical_work_key, house=work.house, state=work.state_name, district=work.district_or_ida,
            mp=work.mp_source_name, constituency=work.constituency_name, description=work.work_description,
            sanction=float(sanction.amount) if sanction and sanction.amount is not None else None,
            expenditure=sum(amounts) if amounts else None, transaction_count=len(txs), max_transaction=max(amounts) if amounts else None,
            transaction_dates=tuple(sorted(d for _, d in txs if d)),
            recommended_date=_date(sanction.recommended) if sanction else None, sanction_date=_date(sanction.sanction) if sanction else None,
            completion_date=_date(completions.get(work.canonical_work_key)),
        ))
    return scope, features


def _signal(feature: WorkFeature, dataset_version: str, category: str, rule_id: str, severity: str, points: int, title: str, explanation: str, evidence: dict[str, Any]) -> dict[str, Any]:
    fingerprint = _fingerprint(dataset_version, feature.work_key, rule_id)
    return {"signal_id": _identifier("sig", fingerprint), "dataset_version": dataset_version, "work_key": feature.work_key, "house": feature.house, "state_name": feature.state, "district_or_ida": feature.district, "mp_source_name": feature.mp, "category": category, "rule_id": rule_id, "severity": severity, "points": points, "title": title, "explanation": explanation, "evidence": evidence, "fingerprint": fingerprint}


def deterministic_signals(features: list[WorkFeature], dataset_version: str) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    tx_threshold = _percentile((float(feature.transaction_count) for feature in features if feature.transaction_count), CONFIG["transaction_count_quantile"])
    peer_values: dict[str, list[float]] = defaultdict(list)
    for feature in features:
        if feature.state and feature.lifecycle_days is not None:
            peer_values[feature.state].append(float(feature.lifecycle_days))
    peer_thresholds = {state: _percentile(values, CONFIG["lifecycle_peer_quantile"]) for state, values in peer_values.items() if len(values) >= CONFIG["lifecycle_min_peer_count"]}
    for feature in features:
        ratio = feature.expenditure_ratio
        if ratio is not None and ratio > CONFIG["expenditure_ratio_threshold"]:
            signals.append(_signal(feature, dataset_version, "FINANCIAL", "FIN_EXPENDITURE_EXCEEDS_SANCTION", "HIGH", 25, "Expenditure exceeds recorded sanction", "Recorded linked expenditure is greater than the linked source sanction total; this is a financial monitoring signal requiring review of source context.", {"expenditure": feature.expenditure, "sanction": feature.sanction, "expenditure_to_sanction_ratio": ratio, "threshold": CONFIG["expenditure_ratio_threshold"]}))
        concentration = feature.payment_concentration
        if concentration is not None and concentration >= CONFIG["payment_concentration_threshold"]:
            signals.append(_signal(feature, dataset_version, "PAYMENT", "PAY_HIGH_CONCENTRATION", "MEDIUM", 10, "Concentrated recorded expenditure", "A single recorded transaction accounts for a high share of linked expenditure. This is a payment pattern for monitoring attention, not a conclusion about cause.", {"largest_transaction": feature.max_transaction, "total_expenditure": feature.expenditure, "concentration_ratio": concentration, "threshold": CONFIG["payment_concentration_threshold"]}))
        if tx_threshold is not None and feature.transaction_count > tx_threshold:
            signals.append(_signal(feature, dataset_version, "PAYMENT", "PAY_HIGH_TRANSACTION_COUNT", "LOW", 10, "High transaction count relative to active-release peers", "The linked transaction count is above the active-release configured peer percentile. Review is warranted only alongside source context.", {"transaction_count": feature.transaction_count, "peer_percentile_threshold": tx_threshold, "percentile": CONFIG["transaction_count_quantile"]}))
        if len(feature.transaction_dates) >= CONFIG["short_period_transaction_count"] and (feature.transaction_dates[-1] - feature.transaction_dates[0]).days <= CONFIG["short_period_days"]:
            signals.append(_signal(feature, dataset_version, "PAYMENT", "PAY_MANY_TRANSACTIONS_SHORT_PERIOD", "MEDIUM", 10, "Multiple recorded payments in a short observed period", "Multiple linked expenditure transactions occur within the configured observed-date window. The source dates support this timing signal.", {"transaction_count": len(feature.transaction_dates), "first_date": feature.transaction_dates[0].isoformat(), "last_date": feature.transaction_dates[-1].isoformat(), "observed_span_days": (feature.transaction_dates[-1] - feature.transaction_dates[0]).days, "threshold_days": CONFIG["short_period_days"]}))
        lifecycle = feature.lifecycle_days
        peer_threshold = peer_thresholds.get(feature.state or "")
        if lifecycle is not None and peer_threshold is not None and lifecycle > peer_threshold:
            signals.append(_signal(feature, dataset_version, "LIFECYCLE", "LIFE_LONGER_THAN_STATE_PEER", "MEDIUM", 15, "Longer-than-peer observed lifecycle pattern", "The observed sanction-to-completion duration is above the configured state-peer percentile. This is not a government deadline and requires contextual review.", {"observed_sanction_to_completion_days": lifecycle, "state_peer_p90_days": peer_threshold, "peer_count": len(peer_values[feature.state or ""]), "percentile": CONFIG["lifecycle_peer_quantile"]}))
        # Data quality is kept in each risk assessment's interpretation context,
        # rather than creating a substantive-looking alert for every sparse record.
    return signals


def duplicate_candidates(features: list[WorkFeature], dataset_version: str) -> list[dict[str, Any]]:
    """Bounded, district-blocked TF-IDF cosine candidates; never self-pairs."""
    blocks: dict[tuple[str | None, str | None], list[WorkFeature]] = defaultdict(list)
    for feature in features:
        if feature.description and len(feature.description.split()) >= 4:
            blocks[(feature.state, feature.district)].append(feature)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for block in blocks.values():
        if len(block) < 2 or len(block) > CONFIG["duplicate_max_block_size"]:
            continue
        descriptions = [feature.description or "" for feature in block]
        try:
            matrix = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_df=0.95, sublinear_tf=True).fit_transform(descriptions)
        except ValueError:
            continue
        neighbors = NearestNeighbors(metric="cosine", algorithm="brute", n_neighbors=min(len(block), CONFIG["duplicate_max_neighbors"] + 1), n_jobs=1).fit(matrix)
        distances, indices = neighbors.kneighbors(matrix)
        for index, (row_distances, row_indices) in enumerate(zip(distances, indices, strict=True)):
            for distance, other_index in zip(row_distances, row_indices, strict=True):
                if index == other_index:
                    continue
                first, second = sorted((block[index], block[other_index]), key=lambda value: value.work_key)
                fingerprint = _fingerprint(dataset_version, first.work_key, second.work_key, DUPLICATE_ENGINE_VERSION)
                if fingerprint in seen:
                    continue
                similarity = float(1 - distance)
                if similarity < CONFIG["duplicate_similarity_threshold"]:
                    continue
                seen.add(fingerprint)
                amounts = [value.sanction for value in (first, second)]
                amount_similarity = None if not all(amount and amount > 0 for amount in amounts) else 1 - abs(amounts[0] - amounts[1]) / max(amounts)
                high = similarity >= CONFIG["duplicate_high_priority_threshold"] and first.district == second.district and (amount_similarity is None or amount_similarity >= 0.80)
                context = {"same_house": first.house == second.house, "same_state": first.state == second.state, "same_district_or_ida": first.district == second.district, "same_mp": first.mp == second.mp, "amount_similarity": amount_similarity, "location_block": {"state": first.state, "district_or_ida": first.district}}
                candidates.append({"candidate_id": _identifier("dup", fingerprint), "dataset_version": dataset_version, "work_a_key": first.work_key, "work_b_key": second.work_key, "similarity_score": similarity, "review_priority": "HIGH" if high else "MEDIUM", "contextual_comparison": context, "reason": "High TF-IDF cosine similarity within the same source location block; this is a potential duplicate candidate, not a confirmed duplicate.", "fingerprint": fingerprint})
    return candidates


def duplicate_signals(candidates: list[dict[str, Any]], by_key: dict[str, WorkFeature], dataset_version: str) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        for key in (candidate["work_a_key"], candidate["work_b_key"]):
            if key not in best or candidate["similarity_score"] > best[key]["similarity_score"]:
                best[key] = candidate
    signals = []
    for key, candidate in best.items():
        feature = by_key[key]
        points = 20 if candidate["review_priority"] == "HIGH" else 10
        signals.append(_signal(feature, dataset_version, "DUPLICATE_CANDIDATE", "DUP_TFIDF_COSINE", candidate["review_priority"], points, "Potential duplicate candidate", "This work has a high textual-similarity candidate in a bounded same-location comparison. Similarity is analytical evidence for review, not confirmation of duplication.", {"candidate_id": candidate["candidate_id"], "other_work_key": candidate["work_b_key"] if candidate["work_a_key"] == key else candidate["work_a_key"], "similarity_score": candidate["similarity_score"], "review_priority": candidate["review_priority"], "contextual_comparison": candidate["contextual_comparison"]}))
    return signals


def ml_anomaly_signals(features: list[WorkFeature], dataset_version: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    eligible = [feature for feature in features if feature.sanction is not None and feature.expenditure is not None and feature.expenditure_ratio is not None and feature.payment_concentration is not None]
    metadata = {"version": MODEL_VERSION, "random_seed": CONFIG["ml_random_seed"], "contamination": CONFIG["ml_contamination"], "feature_list": ["log_sanction_amount", "log_expenditure", "expenditure_to_sanction_ratio", "transaction_count", "payment_concentration"], "eligible_record_count": len(eligible)}
    if len(eligible) < CONFIG["ml_min_records"]:
        metadata["status"] = "UNAVAILABLE_INSUFFICIENT_ELIGIBLE_RECORDS"
        return [], metadata
    matrix = np.array([[log1p(feature.sanction or 0), log1p(feature.expenditure or 0), feature.expenditure_ratio or 0, feature.transaction_count, feature.payment_concentration or 0] for feature in eligible], dtype=float)
    model = IsolationForest(contamination=CONFIG["ml_contamination"], random_state=CONFIG["ml_random_seed"], n_estimators=200, n_jobs=1).fit(matrix)
    labels, scores = model.predict(matrix), model.decision_function(matrix)
    metadata["status"] = "COMPLETED"
    signals = []
    for feature, label, score in zip(eligible, labels, scores, strict=True):
        if label != -1:
            continue
        signals.append(_signal(feature, dataset_version, "ML_ANOMALY", "ML_ISOLATION_FOREST", "MEDIUM", 15, "ML anomaly signal", "This observation differs from the learned active-release feature distribution. It is an analytical signal for review, not a finding of wrongdoing.", {"anomaly_score": float(score), "model": metadata, "feature_values": {"sanction_amount": feature.sanction, "expenditure": feature.expenditure, "expenditure_to_sanction_ratio": feature.expenditure_ratio, "transaction_count": feature.transaction_count, "payment_concentration": feature.payment_concentration}}))
    return signals, metadata


def risk_band(score: float) -> str:
    if score < 30:
        return "LOW"
    if score < 60:
        return "MEDIUM"
    if score < 80:
        return "HIGH"
    return "VERY_HIGH"


def _persist_signals(session: Session, run_id: str, signals: list[dict[str, Any]], now: datetime) -> list[MonitoringSignal]:
    existing = set(session.scalars(select(MonitoringSignal.fingerprint).where(MonitoringSignal.dataset_version == signals[0]["dataset_version"])).all()) if signals else set()
    created = []
    for item in signals:
        if item["fingerprint"] in existing:
            continue
        created.append(MonitoringSignal(run_id=run_id, generated_at=now, **item))
    session.add_all(created)
    session.flush()
    return created


def _persist_candidates(session: Session, run_id: str, candidates: list[dict[str, Any]], now: datetime) -> list[DuplicateCandidate]:
    existing = set(session.scalars(select(DuplicateCandidate.fingerprint).where(DuplicateCandidate.dataset_version == candidates[0]["dataset_version"])).all()) if candidates else set()
    created = [DuplicateCandidate(run_id=run_id, generated_at=now, **item) for item in candidates if item["fingerprint"] not in existing]
    session.add_all(created)
    session.flush()
    return created


def _persist_risks(session: Session, run_id: str, dataset_version: str, by_key: dict[str, WorkFeature], signals: list[MonitoringSignal], now: datetime) -> list[RiskAssessment]:
    signal_map: dict[str, list[MonitoringSignal]] = defaultdict(list)
    for signal in signals:
        signal_map[signal.work_key].append(signal)
    existing = set(session.scalars(select(RiskAssessment.work_key).where(RiskAssessment.dataset_version == dataset_version)).all())
    created = []
    category_names = {"FINANCIAL": "financial", "PAYMENT": "payment", "LIFECYCLE": "lifecycle", "DUPLICATE_CANDIDATE": "duplicate", "ML_ANOMALY": "ml"}
    caps = {"financial": 25, "payment": 20, "lifecycle": 15, "duplicate": 20, "ml": 15}
    for key, feature in by_key.items():
        if key in existing:
            continue
        relevant = signal_map.get(key, [])
        components = {name: min(cap, sum(signal.points for signal in relevant if category_names.get(signal.category) == name)) for name, cap in caps.items()}
        raw = sum(components.values())
        normalized = raw / RISK_MAXIMUM * 100
        quality = feature.data_quality
        fingerprint = _fingerprint(dataset_version, key, "risk", RULES_VERSION, MODEL_VERSION)
        created.append(RiskAssessment(assessment_id=_identifier("risk", fingerprint), run_id=run_id, dataset_version=dataset_version, work_key=key, house=feature.house, state_name=feature.state, district_or_ida=feature.district, mp_source_name=feature.mp, raw_score=raw, normalized_score=normalized, risk_band=risk_band(normalized), component_scores=components, evidence={"signal_ids": [signal.signal_id for signal in relevant if signal.category != "DATA_QUALITY"], "formula": "raw_score / 95 * 100"}, data_quality_context=quality, rules_version=RULES_VERSION, model_version=MODEL_VERSION, generated_at=now))
    session.add_all(created)
    session.flush()
    return created


def _persist_alerts(session: Session, run_id: str, dataset_version: str, signals: list[MonitoringSignal], risks: list[RiskAssessment], now: datetime) -> list[AnalyticalAlert]:
    candidates: list[dict[str, Any]] = []
    for signal in signals:
        fingerprint = _fingerprint(dataset_version, signal.work_key, "alert", signal.rule_id)
        candidates.append({"alert_id": _identifier("alert", fingerprint), "dataset_version": dataset_version, "work_key": signal.work_key, "house": signal.house, "category": signal.category, "severity": signal.severity, "title": signal.title, "explanation": signal.explanation, "evidence": {"signal_id": signal.signal_id, **signal.evidence}, "fingerprint": fingerprint})
    for risk in risks:
        if risk.normalized_score >= 60:
            fingerprint = _fingerprint(dataset_version, risk.work_key, "alert", "combined")
            candidates.append({"alert_id": _identifier("alert", fingerprint), "dataset_version": dataset_version, "work_key": risk.work_key, "house": risk.house, "category": "COMBINED", "severity": risk.risk_band, "title": "Combined monitoring attention", "explanation": "Multiple separate analytical evidence families produce a higher monitoring-priority score. Human review is required for interpretation.", "evidence": {"assessment_id": risk.assessment_id, "raw_score": risk.raw_score, "normalized_score": risk.normalized_score, "components": risk.component_scores}, "fingerprint": fingerprint})
    existing = set(session.scalars(select(AnalyticalAlert.fingerprint).where(AnalyticalAlert.dataset_version == dataset_version)).all()) if candidates else set()
    created = [AnalyticalAlert(run_id=run_id, generated_at=now, status="OPEN", **item) for item in candidates if item["fingerprint"] not in existing]
    session.add_all(created)
    session.flush()
    return created


def run_monitoring_engine(session: Session) -> dict[str, Any]:
    """Execute one reproducible run against the current active release."""
    scope = resolve_active_scope(session)
    now = datetime.now(UTC)
    run = AnalyticsRun(run_id=f"run_{uuid4().hex}", dataset_version=scope.release_version, batch_id=scope.batch_id, started_at=now, completed_at=None, status="STARTED", rules_version=RULES_VERSION, model_version=MODEL_VERSION, duplicate_engine_version=DUPLICATE_ENGINE_VERSION, feature_version=FEATURE_VERSION, model_config=CONFIG, record_counts={}, signal_counts={}, alert_count=0, error_summary=None)
    session.add(run)
    session.flush()
    try:
        _, features = extract_features(session)
        by_key = {feature.work_key: feature for feature in features}
        rule_signals = deterministic_signals(features, scope.release_version)
        candidates = duplicate_candidates(features, scope.release_version)
        duplicate_rule_signals = duplicate_signals(candidates, by_key, scope.release_version)
        anomaly_signals, model_metadata = ml_anomaly_signals(features, scope.release_version)
        created_candidates = _persist_candidates(session, run.run_id, candidates, now)
        created_signals = _persist_signals(session, run.run_id, [*rule_signals, *duplicate_rule_signals, *anomaly_signals], now)
        # Include idempotent historical signals in risk calculations for this dataset.
        all_signals = session.scalars(select(MonitoringSignal).where(MonitoringSignal.dataset_version == scope.release_version)).all()
        created_risks = _persist_risks(session, run.run_id, scope.release_version, by_key, all_signals, now)
        all_risks = session.scalars(select(RiskAssessment).where(RiskAssessment.dataset_version == scope.release_version)).all()
        created_alerts = _persist_alerts(session, run.run_id, scope.release_version, all_signals, all_risks, now)
        run.completed_at = datetime.now(UTC)
        run.status = "COMPLETED"
        run.record_counts = {"work_features": len(features), "duplicate_candidates_generated": len(candidates), "duplicate_candidates_created": len(created_candidates), "ml": model_metadata}
        run.signal_counts = dict(Counter(signal.category for signal in created_signals))
        run.alert_count = len(created_alerts)
        session.commit()
        return {"run_id": run.run_id, "dataset_version": scope.release_version, "status": run.status, "record_counts": run.record_counts, "signal_counts": run.signal_counts, "alert_count": run.alert_count}
    except Exception as exc:
        session.rollback()
        failed = AnalyticsRun(run_id=f"run_{uuid4().hex}", dataset_version=scope.release_version, batch_id=scope.batch_id, started_at=now, completed_at=datetime.now(UTC), status="FAILED", rules_version=RULES_VERSION, model_version=MODEL_VERSION, duplicate_engine_version=DUPLICATE_ENGINE_VERSION, feature_version=FEATURE_VERSION, model_config=CONFIG, record_counts={}, signal_counts={}, alert_count=0, error_summary=str(exc))
        session.add(failed)
        session.commit()
        raise

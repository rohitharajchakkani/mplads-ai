"""Persisted, protected monitoring outputs derived from an active release."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalyticsRun(Base):
    __tablename__ = "analytics_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_version: Mapped[str] = mapped_column(String(96), index=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), index=True)
    rules_version: Mapped[str] = mapped_column(String(32))
    model_version: Mapped[str] = mapped_column(String(32))
    duplicate_engine_version: Mapped[str] = mapped_column(String(32))
    feature_version: Mapped[str] = mapped_column(String(32))
    model_config: Mapped[dict[str, Any]] = mapped_column(JSON)
    record_counts: Mapped[dict[str, Any]] = mapped_column(JSON)
    signal_counts: Mapped[dict[str, Any]] = mapped_column(JSON)
    alert_count: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)


class MonitoringSignal(Base):
    __tablename__ = "monitoring_signals"
    __table_args__ = (UniqueConstraint("fingerprint", name="uq_monitoring_signal_fingerprint"),)

    signal_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("analytics_runs.run_id"), index=True)
    dataset_version: Mapped[str] = mapped_column(String(96), index=True)
    work_key: Mapped[str] = mapped_column(ForeignKey("works.canonical_work_key"), index=True)
    house: Mapped[str] = mapped_column(String(20), index=True)
    state_name: Mapped[str | None] = mapped_column(String(150), index=True)
    district_or_ida: Mapped[str | None] = mapped_column(String(500), index=True)
    mp_source_name: Mapped[str | None] = mapped_column(String(300), index=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    rule_id: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    points: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(240))
    explanation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class DuplicateCandidate(Base):
    __tablename__ = "duplicate_candidates"
    __table_args__ = (UniqueConstraint("fingerprint", name="uq_duplicate_candidate_fingerprint"),)

    candidate_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("analytics_runs.run_id"), index=True)
    dataset_version: Mapped[str] = mapped_column(String(96), index=True)
    work_a_key: Mapped[str] = mapped_column(ForeignKey("works.canonical_work_key"), index=True)
    work_b_key: Mapped[str] = mapped_column(ForeignKey("works.canonical_work_key"), index=True)
    similarity_score: Mapped[float] = mapped_column(Float)
    review_priority: Mapped[str] = mapped_column(String(16), index=True)
    contextual_comparison: Mapped[dict[str, Any]] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (UniqueConstraint("dataset_version", "work_key", name="uq_risk_assessment_dataset_work"),)

    assessment_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("analytics_runs.run_id"), index=True)
    dataset_version: Mapped[str] = mapped_column(String(96), index=True)
    work_key: Mapped[str] = mapped_column(ForeignKey("works.canonical_work_key"), index=True)
    house: Mapped[str] = mapped_column(String(20), index=True)
    state_name: Mapped[str | None] = mapped_column(String(150), index=True)
    district_or_ida: Mapped[str | None] = mapped_column(String(500), index=True)
    mp_source_name: Mapped[str | None] = mapped_column(String(300), index=True)
    raw_score: Mapped[int] = mapped_column(Integer)
    normalized_score: Mapped[float] = mapped_column(Float)
    risk_band: Mapped[str] = mapped_column(String(16), index=True)
    component_scores: Mapped[dict[str, Any]] = mapped_column(JSON)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON)
    data_quality_context: Mapped[dict[str, Any]] = mapped_column(JSON)
    rules_version: Mapped[str] = mapped_column(String(32))
    model_version: Mapped[str] = mapped_column(String(32))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AnalyticalAlert(Base):
    __tablename__ = "analytical_alerts"
    __table_args__ = (UniqueConstraint("fingerprint", name="uq_analytical_alert_fingerprint"),)

    alert_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("analytics_runs.run_id"), index=True)
    dataset_version: Mapped[str] = mapped_column(String(96), index=True)
    work_key: Mapped[str] = mapped_column(ForeignKey("works.canonical_work_key"), index=True)
    house: Mapped[str] = mapped_column(String(20), index=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(String(240))
    explanation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24), default="OPEN", index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

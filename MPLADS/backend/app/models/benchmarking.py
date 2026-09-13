"""Persisted, reproducible peer benchmarks and evidence-backed recommendations."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"
    run_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    dataset_version: Mapped[str] = mapped_column(String(96), index=True)
    benchmark_version: Mapped[str] = mapped_column(String(32), index=True)
    configuration_hash: Mapped[str] = mapped_column(String(64), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), index=True)
    entity_count: Mapped[int] = mapped_column(Integer, default=0)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON)
    error_summary: Mapped[str | None] = mapped_column(Text)


class BenchmarkCohort(Base):
    __tablename__ = "benchmark_cohorts"
    cohort_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), ForeignKey("benchmark_runs.run_id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    house: Mapped[str] = mapped_column(String(20), index=True)
    metric: Mapped[str] = mapped_column(String(48), index=True)
    definition: Mapped[dict[str, Any]] = mapped_column(JSON)
    peer_ids: Mapped[list[str]] = mapped_column(JSON)
    peer_count: Mapped[int] = mapped_column(Integer)
    valid_entities: Mapped[int] = mapped_column(Integer)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"
    __table_args__ = (UniqueConstraint("run_id", "entity_type", "entity_id", "metric", name="uq_benchmark_result_run_entity_metric"),)
    result_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), ForeignKey("benchmark_runs.run_id"), index=True)
    cohort_id: Mapped[str | None] = mapped_column(String(80), ForeignKey("benchmark_cohorts.cohort_id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_id: Mapped[str] = mapped_column(String(300), index=True)
    house: Mapped[str] = mapped_column(String(20), index=True)
    state_name: Mapped[str | None] = mapped_column(String(150), index=True)
    district_or_ida: Mapped[str | None] = mapped_column(String(500), index=True)
    mp_source_name: Mapped[str | None] = mapped_column(String(300), index=True)
    metric: Mapped[str] = mapped_column(String(48), index=True)
    formula: Mapped[str] = mapped_column(Text)
    metric_details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    value: Mapped[float | None] = mapped_column(Float)
    peer_median: Mapped[float | None] = mapped_column(Float)
    p25: Mapped[float | None] = mapped_column(Float)
    p75: Mapped[float | None] = mapped_column(Float)
    p90: Mapped[float | None] = mapped_column(Float)
    iqr: Mapped[float | None] = mapped_column(Float)
    peer_count: Mapped[int] = mapped_column(Integer, default=0)
    valid_work_count: Mapped[int] = mapped_column(Integer, default=0)
    benchmark_available: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    unavailable_reason: Mapped[str | None] = mapped_column(String(240))
    directionality: Mapped[str] = mapped_column(String(32))
    bottleneck_flag: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    interpretation: Mapped[str] = mapped_column(String(240))
    dataset_version: Mapped[str] = mapped_column(String(96), index=True)
    benchmark_version: Mapped[str] = mapped_column(String(32))
    provenance_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class BenchmarkPeer(Base):
    __tablename__ = "benchmark_peers"
    __table_args__ = (UniqueConstraint("result_id", "peer_entity_id", name="uq_benchmark_peer_result_entity"),)
    peer_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    result_id: Mapped[str] = mapped_column(String(80), ForeignKey("benchmark_results.result_id"), index=True)
    peer_entity_id: Mapped[str] = mapped_column(String(300), index=True)
    peer_value: Mapped[float] = mapped_column(Float)


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (UniqueConstraint("fingerprint", name="uq_recommendation_fingerprint"),)
    recommendation_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    canonical_work_key: Mapped[str | None] = mapped_column(String(110), ForeignKey("works.canonical_work_key"), index=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_id: Mapped[str] = mapped_column(String(300), index=True)
    house: Mapped[str | None] = mapped_column(String(20), index=True)
    state_name: Mapped[str | None] = mapped_column(String(150), index=True)
    district_or_ida: Mapped[str | None] = mapped_column(String(500), index=True)
    mp_source_name: Mapped[str | None] = mapped_column(String(300), index=True)
    recommendation_type: Mapped[str] = mapped_column(String(64), index=True)
    reason: Mapped[str] = mapped_column(Text)
    evidence_references: Mapped[dict[str, Any]] = mapped_column(JSON)
    priority: Mapped[str] = mapped_column(String(16), index=True)
    dataset_version: Mapped[str] = mapped_column(String(96), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True, default="NOTED")
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class RecommendationEvent(Base):
    __tablename__ = "recommendation_events"
    event_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    recommendation_id: Mapped[str] = mapped_column(String(80), ForeignKey("recommendations.recommendation_id"), index=True)
    actor: Mapped[str] = mapped_column(String(160), index=True)
    action: Mapped[str] = mapped_column(String(32), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON)
